import copy
import json
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from PIL import Image, ImageChops, ImageDraw

from scripts.poster_assets import fetch_cutouts
from scripts.poster_assets import fetch_poster_sources
from scripts.poster_assets import (
    create_comfyui_poster_workflow as poster_workflow,
)
from scripts.poster_assets import promote_comfyui_poster as poster_promotion
from scripts.poster_assets import run_comfyui_poster as poster_runner
from scripts.poster_assets import slice_poster as poster_slicer
from scripts.poster_assets.fetch_title_logos import resolve_logo_downloads
from scripts.poster_assets.create_comfyui_poster_workflow import (
    build_workflow,
    output_dimensions,
)
from scripts.poster_assets.create_comfyui_upscale_workflow import (
    build_workflow as build_upscale_workflow,
)
from scripts.poster_assets.create_custom_poster_layout import (
    _copy_inputs,
    _custom_manifest,
    _parse_section_fallbacks,
    create_custom_layout_workspace,
)
from scripts.poster_assets.finalize_comfyui_poster import (
    draw_inline_logo_title,
    draw_title_text,
    finalize,
    fitted_font,
    info_panel_box,
    title_logo_file,
)
from scripts.poster_assets.layout import (
    build_generation_output_layout,
    build_image_layout,
    build_page_layout,
    build_print_layout,
    build_source_layout,
    default_text_cells,
    effective_dpi,
    latent_canvas_dimensions,
    pdf_page_hint,
    proportional_height_px,
)
from scripts.poster_assets.init_poster_scope import (
    available_tcg_scopes,
    build_default_manifest,
    build_section_manifest,
    init_scope,
    stable_scope_seed,
)
from scripts.poster_assets.poster_io import (
    load_cutout_items,
    load_poster_scope_data,
    poster_bundle,
    poster_bundles_for_scope,
    resolve_poster_assets_root,
)
from scripts.poster_assets.poster_subject import (
    PosterSubject,
    official_artwork_id_from_url,
    poster_subject_from_card,
    resolve_poster_subject,
)
from scripts.poster_assets.poster_config import (
    IDENTITY_LOCK_PROMPT_FILE,
    INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE,
    JOINT_SCENE_PROMPT_FILE,
    REGIONAL_JOINT_SCENE_PROMPT_FILE,
    build_identity_lock_prompt,
    build_joint_prompt_snapshot,
    build_joint_scene_prompt,
    identity_lock_config,
    identity_lock_overscan,
)
from scripts.poster_assets.provenance import (
    add_model_artifact_hashes,
    generation_input_records,
    sha256_file,
)
from scripts.poster_assets.queue_comfyui_workflow import (
    request_json,
    server_comfyui_root,
    server_input_directory,
    validate_server_input_directory,
)
from scripts.poster_assets.prepare_comfyui_poster import (
    build_individual_spatial_joint_references,
    build_joint_scene_references,
    build_identity_lock_references,
    build_upper_context_mask,
)
from scripts.poster_assets.composition import cutout_placements
from scripts.poster_assets.composition import (
    joint_scene_canvas_placements,
    joint_scene_cutout_placements,
    normalized_visible_placement_contract,
)
from scripts.poster_assets.typography import wrap_text
from scripts.poster_assets.run_comfyui_poster import (
    configured_generation,
    resize_artwork,
    resize_artwork_to_dpi,
    validate_identity_lock_pixels,
    validate_raw_artwork,
    write_engine_workflow,
)
from scripts.poster_assets.slice_poster import slice_poster
from scripts.poster_assets import upscale_comfyui_poster as poster_upscale
from scripts.poster_assets.scene_catalog import (
    load_scene_catalog,
    scene_for_scope,
    section_scenes_for_scope,
    validate_catalog_coverage,
    validate_section_catalog_coverage,
)
from scripts.poster_assets.validate_promoted_poster import (
    enabled_poster_scopes,
    validate as validate_promoted_poster,
)
from scripts.poster_assets import validate_promoted_poster as poster_validator


def test_fetch_poster_sources_can_limit_ci_to_pdf_logos(monkeypatch):
    calls = []
    bundle = SimpleNamespace(
        asset_key="Example",
        manifest={"title_logo": {"file": "logo.png"}},
    )
    monkeypatch.setattr(
        fetch_poster_sources,
        "poster_bundle",
        lambda *_args, **_kwargs: bundle,
    )
    monkeypatch.setattr(
        fetch_poster_sources,
        "fetch_cutouts",
        lambda *args, **kwargs: calls.append(("cutouts", args, kwargs)),
    )
    monkeypatch.setattr(
        fetch_poster_sources,
        "fetch_title_logos",
        lambda *args, **kwargs: calls.append(("logos", args, kwargs)),
    )

    assert fetch_poster_sources.fetch_sources(
        ["Example"],
        kind="logos",
    ) == 0
    assert calls == [("logos", ("Example",), {"force": False})]


def test_auto_count_uses_layout_columns():
    manifest = {"pokemon": {"count": "auto_from_layout_columns"}}
    assert fetch_cutouts.resolve_requested_count(manifest, build_page_layout("wide_4x3")) == 4


def test_2x2_layout_uses_requested_overlay_cells_and_two_subjects():
    layout = build_print_layout("standard_2x2", 300)

    assert (layout.columns, layout.rows) == (2, 2)
    assert (layout.width_px, layout.height_px) == (1559, 2159)
    assert pdf_page_hint("standard_2x2") == ("A4", "portrait")
    assert default_text_cells("standard_2x2") == {
        "title": {"row": 1, "column": 1},
        "set_info": {
            "row": 1,
            "column": 2,
            "max_width_ratio": 0.92,
            "max_height_ratio": 0.68,
        },
    }

    manifest = _custom_manifest(
        {
            "layout": {"name": "standard_3x3"},
            "text_cells": {
                "title": {"row": 1, "column": 2},
                "set_info": {"row": 2, "column": 2},
            },
            "pokemon": {"count": "auto_from_layout_columns"},
        },
        "standard_2x2",
        2,
        enable_pdf=True,
    )
    assert manifest["text_cells"] == default_text_cells("standard_2x2")
    assert manifest["pdf"]["enabled"] is True

    fixed_count_manifest = _custom_manifest(
        {
            "layout": {"name": "standard_3x3"},
            "pokemon": {"count": 3},
        },
        "standard_2x2",
        2,
        enable_pdf=False,
    )
    assert (
        fixed_count_manifest["pokemon"]["count"]
        == "auto_from_layout_columns"
    )


def test_custom_2x2_inputs_retain_the_first_two_curated_cutouts(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    (source / "cutouts").mkdir(parents=True)
    items = []
    for index in range(1, 4):
        file_name = f"pokemon-{index}.png"
        (source / "cutouts" / file_name).write_bytes(bytes([index]))
        items.append({"pokemon_id": index, "file": file_name})
    (source / "cutouts" / "manifest.json").write_text(
        json.dumps({"items": items}),
        encoding="utf-8",
    )

    count = _copy_inputs(source, target, {}, max_cutouts=2)

    retained = json.loads(
        (target / "cutouts" / "manifest.json").read_text(encoding="utf-8")
    )
    assert count == 2
    assert [item["pokemon_id"] for item in retained["items"]] == [1, 2]
    assert (target / "cutouts" / "pokemon-1.png").is_file()
    assert (target / "cutouts" / "pokemon-2.png").is_file()
    assert not (target / "cutouts" / "pokemon-3.png").exists()


@pytest.mark.parametrize("scope", [".", ".."])
def test_poster_initializer_rejects_path_traversal_scope(scope):
    with pytest.raises(ValueError, match="Unsafe scope name"):
        init_scope(scope)


def test_standard_print_layout_is_300_dpi_at_physical_card_size():
    layout = build_print_layout("standard_3x3", 300)

    assert (layout.width_px, layout.height_px) == (2368, 3268)
    assert (layout.card_width_px, layout.card_height_px) == (750, 1050)
    dpi_x, dpi_y = effective_dpi(layout)
    assert abs(dpi_x - 300) < 0.1
    assert abs(dpi_y - 300) < 0.1


def test_print_cells_rasterize_absolute_mm_endpoints_before_page_rounding():
    layout = build_print_layout("standard_3x3", 150)

    assert (layout.width_px, layout.height_px) == (1184, 1634)
    assert layout.card_widths_px == (375, 375, 375)
    assert layout.card_heights_px == (525, 525, 525)
    assert layout.gap_widths_px == (30, 29)
    assert layout.gap_heights_px == (30, 29)


def test_proportional_height_uses_exact_decimal_physical_dimensions():
    assert proportional_height_px("wide_4x3", 4035) == 4150
    assert proportional_height_px("wide_4x3", 9415) == 9684


def test_uniform_extent_compatibility_properties_fail_on_uneven_rasters():
    latent = build_source_layout(
        "standard_3x3",
        width_px=848,
        height_px=1168,
    )
    odd_dpi = build_print_layout("standard_3x3", 150)

    with pytest.raises(ValueError, match="Card widths vary"):
        _ = latent.card_width_px
    with pytest.raises(ValueError, match="Card heights vary"):
        _ = latent.card_height_px
    with pytest.raises(ValueError, match="Horizontal gaps vary"):
        _ = odd_dpi.gap_x_px
    with pytest.raises(ValueError, match="Vertical gaps vary"):
        _ = odd_dpi.gap_y_px


@pytest.mark.parametrize("dpi", (72, 150, 299, 300, 301, 600))
@pytest.mark.parametrize(
    "name",
    ("standard_2x2", "standard_3x3", "wide_4x3", "wide_4x4"),
)
def test_dpi_aware_image_layout_reconstructs_print_endpoints(name, dpi):
    expected = build_print_layout(name, dpi)
    actual = build_image_layout(
        name,
        width_px=expected.width_px,
        height_px=expected.height_px,
        dpi=(float(dpi), float(dpi)),
    )

    assert actual.column_spans == expected.column_spans
    assert actual.row_spans == expected.row_spans


def test_wide_layouts_keep_full_page_a3_hints():
    layout_4x3 = build_print_layout("wide_4x3", 300)
    layout_4x4 = build_print_layout("wide_4x4", 300)

    assert (layout_4x3.columns, layout_4x3.rows) == (4, 3)
    assert (layout_4x4.columns, layout_4x4.rows) == (4, 4)
    assert pdf_page_hint("wide_4x3") == ("A3", "landscape")
    assert pdf_page_hint("wide_4x4") == ("A3", "portrait")


def test_pokedex_custom_layout_workspace_is_isolated_and_pdf_enabled():
    root = Path(__file__).resolve().parents[2]
    temp_root = root / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    parent = Path(tempfile.mkdtemp(prefix="custom-layout-test-", dir=temp_root))
    target = parent / "poster-assets"
    try:
        workspace = create_custom_layout_workspace(
            "Pokedex",
            "wide_4x3",
            sections=("gen1",),
            output_root=target,
            fallback_pokemon=(25,),
        )

        bundles = poster_bundles_for_scope(
            "Pokedex",
            poster_assets=workspace,
        )
        assert len(bundles) == 1
        assert bundles[0].poster_id == "gen1"
        assert bundles[0].pdf_enabled is True
        assert bundles[0].manifest["layout"] == {"name": "wide_4x3"}
        assert (
            bundles[0].manifest["pokemon"]["count"]
            == "auto_from_layout_columns"
        )
        assert bundles[0].manifest["pokemon"]["fallback_candidates"] == [
            {"pokemon_id": 25, "slot": 2}
        ]
        assert bundles[0].manifest["text_cells"]["title"] == {
            "row": 2,
            "column": 2,
        }
        assert bundles[0].manifest["text_cells"]["set_info"] == {
            "row": 2,
            "column": 3,
            "max_width_ratio": 0.92,
            "max_height_ratio": 0.68,
        }
        assert not (bundles[0].asset_dir / bundles[0].artwork_file).exists()

        cutouts = json.loads(
            (bundles[0].asset_dir / "cutouts" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        assert cutouts["layout"] == {
            "name": "wide_4x3",
            "columns": 4,
            "rows": 3,
        }
        assert (workspace / "workspace.yaml").is_file()
    finally:
        shutil.rmtree(parent)


def test_partial_custom_workspace_can_retain_other_promoted_artworks():
    root = Path(__file__).resolve().parents[2]
    temp_root = root / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    parent = Path(tempfile.mkdtemp(prefix="custom-layout-hybrid-", dir=temp_root))
    source_assets = parent / "source-assets"
    target = parent / "poster-assets"
    try:
        index_items = []
        for poster_id in ("section-a", "section-b"):
            asset_dir = source_assets / "Aggregate" / "sections" / poster_id
            (asset_dir / "cutouts").mkdir(parents=True)
            manifest = {
                "schema_version": 2,
                "asset_key": f"Aggregate/sections/{poster_id}",
                "scope": "Aggregate",
                "poster_id": poster_id,
                "source": {
                    "scope": "Aggregate",
                    "section_id": poster_id,
                },
                "layout": {"name": "standard_3x3"},
                "artwork": {"promoted_file": "poster-artwork.png"},
                "pokemon": {
                    "strategy": "featured_from_scope",
                    "count": "auto_from_layout_columns",
                    "fallback_candidates": [],
                },
            }
            (asset_dir / "poster.yaml").write_text(
                yaml.safe_dump(manifest, sort_keys=False),
                encoding="utf-8",
            )
            (asset_dir / "poster-artwork.png").write_bytes(b"promoted")
            (asset_dir / "cutouts" / "manifest.json").write_text(
                json.dumps(
                    {
                        "items": [
                            {"pokemon_id": 1},
                            {"pokemon_id": 4},
                            {"pokemon_id": 7},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            index_items.append(
                {
                    "id": poster_id,
                    "section_id": poster_id,
                    "manifest": f"sections/{poster_id}/poster.yaml",
                    "pdf": {
                        "enabled": True,
                        "artwork_file": "poster-artwork.png",
                        "insertion": "after_section_cover",
                    },
                }
            )
        index_path = source_assets / "Aggregate" / "posters.yaml"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(
            yaml.safe_dump(
                {
                    "schema_version": 1,
                    "scope": "Aggregate",
                    "posters": index_items,
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        workspace = create_custom_layout_workspace(
            "Aggregate",
            "wide_4x3",
            sections=("section-a",),
            output_root=target,
            source_assets=source_assets,
            fallback_pokemon=(25,),
            include_unselected_promotions=True,
        )

        bundles = poster_bundles_for_scope(
            "Aggregate",
            poster_assets=workspace,
        )
        assert [bundle.poster_id for bundle in bundles] == [
            "section-a",
            "section-b",
        ]
        assert bundles[0].manifest["layout"] == {"name": "wide_4x3"}
        assert not (bundles[0].asset_dir / bundles[0].artwork_file).exists()
        assert bundles[1].manifest["layout"] == {"name": "standard_3x3"}
        assert (bundles[1].asset_dir / bundles[1].artwork_file).read_bytes() == (
            b"promoted"
        )
        workspace_meta = yaml.safe_load(
            (workspace / "workspace.yaml").read_text(encoding="utf-8")
        )
        assert workspace_meta["included_unselected_promotions"] is True
    finally:
        shutil.rmtree(parent)


def test_complete_pokedex_custom_workspace_uses_section_fallbacks():
    root = Path(__file__).resolve().parents[2]
    temp_root = root / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    parent = Path(tempfile.mkdtemp(prefix="custom-layout-complete-", dir=temp_root))
    target = parent / "poster-assets"
    section_fallbacks = {
        "gen1": (25,),
        "gen2": (175,),
        "gen3": (280,),
        "gen4": (447,),
        "gen5": (570,),
        "gen6": (700,),
        "gen7": (778,),
        "gen8": (831,),
        "gen9": (921,),
    }
    try:
        workspace = create_custom_layout_workspace(
            "Pokedex",
            "wide_4x3",
            output_root=target,
            section_fallback_pokemon=section_fallbacks,
        )

        bundles = poster_bundles_for_scope(
            "Pokedex",
            poster_assets=workspace,
        )
        assert [bundle.poster_id for bundle in bundles] == [
            f"gen{generation}" for generation in range(1, 10)
        ]
        for bundle in bundles:
            expected_id = section_fallbacks[bundle.poster_id][0]
            assert bundle.manifest["layout"] == {"name": "wide_4x3"}
            assert bundle.manifest["pokemon"]["fallback_candidates"] == [
                {"pokemon_id": expected_id, "slot": 2}
            ]
            assert not (bundle.asset_dir / bundle.artwork_file).exists()

        workspace_meta = yaml.safe_load(
            (workspace / "workspace.yaml").read_text(encoding="utf-8")
        )
        assert workspace_meta["section_fallback_pokemon"] == {
            section: list(pokemon_ids)
            for section, pokemon_ids in section_fallbacks.items()
        }
    finally:
        shutil.rmtree(parent)


def test_section_fallback_parser_groups_repeated_sections():
    assert _parse_section_fallbacks(
        ["gen1=25", "gen2=175", "gen2=172"]
    ) == {
        "gen1": (25,),
        "gen2": (175, 172),
    }


@pytest.mark.parametrize("value", ("gen1", "=25", "gen1=", "gen1=nope", "gen1=0"))
def test_section_fallback_parser_rejects_invalid_assignments(value):
    with pytest.raises(ValueError):
        _parse_section_fallbacks([value])


def test_slotted_fallback_fills_the_missing_wide_poster_card():
    root = Path(__file__).resolve().parents[2]
    scope_data = json.loads(
        (root / "data" / "output" / "Pokedex.json").read_text(
            encoding="utf-8"
        )
    )
    selected = fetch_cutouts.select_pokemon(
        {
            "pokemon": {
                "strategy": "featured_from_scope",
                "fallback_candidates": [
                    {"pokemon_id": 25, "slot": 2}
                ],
            }
        },
        {"sections": {"gen1": scope_data["sections"]["gen1"]}},
        4,
        {25: {"en": "Pikachu", "de": "Pikachu"}},
    )

    assert [item["pokemon_id"] for item in selected] == [1, 25, 4, 7]


def test_poster_assets_root_accepts_repo_relative_local_workspace(monkeypatch):
    monkeypatch.setenv(
        "BINDER_POKEDEX_POSTER_ASSETS",
        "tmp/custom-poster-layouts/example",
    )

    assert resolve_poster_assets_root() == (
        Path(__file__).resolve().parents[2]
        / "tmp"
        / "custom-poster-layouts"
        / "example"
    ).resolve()


@pytest.mark.parametrize(
    ("name", "expected_canvas"),
    (
        ("standard_3x3", (848, 1168)),
        ("wide_4x3", (992, 1008)),
        ("wide_4x4", (848, 1168)),
    ),
)
def test_latent_layout_cells_close_exactly_on_real_canvas(
    name,
    expected_canvas,
):
    assert latent_canvas_dimensions(name, 1.0) == expected_canvas
    layout = build_source_layout(
        name,
        width_px=expected_canvas[0],
        height_px=expected_canvas[1],
    )

    assert layout.column_spans[0][0] == 0
    assert layout.column_spans[-1][1] == layout.width_px
    assert layout.row_spans[0][0] == 0
    assert layout.row_spans[-1][1] == layout.height_px
    for row in range(1, layout.rows + 1):
        for column in range(1, layout.columns + 1):
            cell = layout.cell(row, column)
            assert 0 <= cell.x < cell.x + cell.width <= layout.width_px
            assert 0 <= cell.y < cell.y + cell.height <= layout.height_px


def test_standard_latent_layout_has_cumulative_endpoint_geometry():
    layout = build_source_layout(
        "standard_3x3",
        width_px=848,
        height_px=1168,
    )

    assert layout.column_spans == (
        (0, 269),
        (290, 558),
        (579, 848),
    )
    assert layout.row_spans == (
        (0, 375),
        (396, 772),
        (793, 1168),
    )


@pytest.mark.parametrize("dpi", (72, 150, 299, 300, 301, 600))
@pytest.mark.parametrize(
    "name",
    ("standard_2x2", "standard_3x3", "wide_4x3", "wide_4x4"),
)
def test_print_layout_rasterization_never_accumulates_past_page(
    name,
    dpi,
):
    layout = build_print_layout(name, dpi)

    assert layout.column_spans[0][0] == 0
    assert layout.column_spans[-1][1] == layout.width_px
    assert layout.row_spans[0][0] == 0
    assert layout.row_spans[-1][1] == layout.height_px
    assert all(
        0 <= cell.x < cell.x + cell.width <= layout.width_px
        and 0 <= cell.y < cell.y + cell.height <= layout.height_px
        for row in range(1, layout.rows + 1)
        for column in range(1, layout.columns + 1)
        for cell in (layout.cell(row, column),)
    )


def test_source_layout_rejects_a_wrong_physical_aspect_ratio():
    with pytest.raises(
        ValueError,
        match="does not match card-layout aspect ratio",
    ):
        build_source_layout(
            "standard_3x3",
            width_px=848,
            height_px=1000,
        )


@pytest.mark.parametrize(
    "megapixels",
    (0.02, 0.25, 0.42, 0.7, 1.0, 1.17, 1.91, 2.0, 6.11),
)
@pytest.mark.parametrize(
    "name",
    ("standard_2x2", "standard_3x3", "wide_4x3", "wide_4x4"),
)
def test_every_latent_aligned_canvas_is_accepted_by_source_layout(
    name,
    megapixels,
):
    width, height = latent_canvas_dimensions(name, megapixels)

    layout = build_source_layout(
        name,
        width_px=width,
        height_px=height,
    )

    assert (layout.width_px, layout.height_px) == (width, height)


def test_select_pokemon_uses_fallback_candidates():
    manifest = {
        "pokemon": {
            "strategy": "featured_from_scope",
            "fallback_candidates": [{"pokemon_id": 25}],
        }
    }
    scope_data = {
        "sections": {
            "all": {
                "featured_elements": [
                    {"pokemon_id": 150, "pokemon_name": "Mewtwo"},
                    {"pokemon_id": 1, "pokemon_name": "Bulbasaur"},
                    {"pokemon_id": 4, "pokemon_name": "Charmander"},
                ]
            }
        }
    }
    names = {25: {"en": "Pikachu", "de": "Pikachu"}}

    selected = fetch_cutouts.select_pokemon(manifest, scope_data, 4, names)

    assert [item["pokemon_id"] for item in selected] == [150, 1, 4, 25]


def test_select_pokemon_keeps_distinct_forms_of_one_species():
    scope_data = {
        "sections": {
            "mega": {
                "featured_elements": [
                    {
                        "pokemon_id": 6,
                        "pokemon_name": "Mega Charizard X",
                        "poster_subject": PosterSubject(6, 10034).as_mapping(),
                    },
                    {
                        "pokemon_id": 6,
                        "pokemon_name": "Mega Charizard Y",
                        "poster_subject": PosterSubject(6, 10035).as_mapping(),
                    },
                    {
                        "pokemon_id": 380,
                        "pokemon_name": "Mega Latias",
                        "poster_subject": PosterSubject(
                            380,
                            10062,
                        ).as_mapping(),
                    },
                ]
            }
        }
    }
    selected = fetch_cutouts.select_pokemon(
        {
            "pokemon": {
                "strategy": "featured_from_scope",
                "fallback_candidates": [],
            }
        },
        scope_data,
        3,
        {},
    )

    assert [
        resolve_poster_subject(item).official_artwork_id
        for item in selected
    ] == [10034, 10035, 10062]
    assert (
        fetch_cutouts.cutout_filename(6, "Mega Charizard X", 10034)
        == "pokemon_006_artwork_10034_mega_charizard_x.png"
    )


def test_legacy_featured_element_recovers_form_from_its_source_card():
    scope_data = {
        "sections": {
            "mega": {
                "cards": [
                    {
                        "pokemon_id": 380,
                        "image_url": PosterSubject(380, 10062).image_url,
                        "prefix": "Mega",
                        "tcg_card": {"id": "me01-100"},
                    }
                ],
                "featured_elements": [
                    {
                        "pokemon_id": 380,
                        "pokemon_name": "Latias",
                        "card_id": "me01-100",
                        "image_url": (
                            "https://assets.tcgdex.net/en/me/me01/100/high.png"
                        ),
                    }
                ],
            }
        }
    }

    featured = fetch_cutouts.scope_featured_elements(scope_data)

    assert featured[0]["image_url"].startswith(
        "https://assets.tcgdex.net/"
    )
    assert featured[0]["pokemon_name"] == "Mega Latias"
    subject = resolve_poster_subject(featured[0])
    assert (subject.species_id, subject.official_artwork_id) == (380, 10062)


def test_explicit_featured_subject_must_match_its_source_card():
    scope_data = {
        "sections": {
            "mega": {
                "cards": [
                    {
                        "pokemon_id": 380,
                        "image_url": PosterSubject(380, 10062).image_url,
                        "prefix": "Mega",
                        "tcg_card": {"id": "me01-100"},
                    }
                ],
                "featured_elements": [
                    {
                        "pokemon_id": 380,
                        "card_id": "me01-100",
                        "poster_subject": PosterSubject(
                            380,
                            380,
                        ).as_mapping(),
                    }
                ],
            }
        }
    }

    with pytest.raises(ValueError, match="does not match its source card"):
        fetch_cutouts.scope_featured_elements(scope_data)


def test_poster_subject_rejects_mismatched_or_untrusted_artwork_urls():
    subject = PosterSubject(380, 10062).as_mapping()
    subject["image_url"] = PosterSubject(380, 380).image_url

    with pytest.raises(ValueError, match="does not match"):
        resolve_poster_subject(
            {"pokemon_id": 380, "poster_subject": subject}
        )
    with pytest.raises(ValueError, match="canonical"):
        official_artwork_id_from_url(
            "https://example.test/official-artwork/10062.png"
        )
    with pytest.raises(ValueError, match="belongs to Pokemon #719"):
        PosterSubject(380, 10075)
    with pytest.raises(ValueError, match="not present in the pinned"):
        PosterSubject(380, 10999)
    with pytest.raises(ValueError, match="without an exact"):
        poster_subject_from_card(
            {
                "pokemon_id": 380,
                "prefix": "Mega",
                "image_url": "https://assets.tcgdex.net/card.png",
            }
        )
    with pytest.raises(ValueError, match="without an exact"):
        poster_subject_from_card(
            {
                "pokemon_id": 150,
                "prefix": "[M]",
                "image_url": "https://assets.tcgdex.net/card.png",
            }
        )
    for pokemon_id, marker in ((380, "Mega"), (150, "[M]")):
        with pytest.raises(ValueError, match="without an exact"):
            poster_subject_from_card(
                {
                    "pokemon_id": pokemon_id,
                    "prefix": marker,
                    "image_url": PosterSubject(
                        pokemon_id,
                        pokemon_id,
                    ).image_url,
                }
            )


def test_featured_card_link_must_resolve_before_base_fallback():
    with pytest.raises(ValueError, match="does not exist"):
        fetch_cutouts.scope_featured_elements(
            {
                "sections": {
                    "mega": {
                        "cards": [
                            {
                                "pokemon_id": 380,
                                "image_url": PosterSubject(
                                    380,
                                    10062,
                                ).image_url,
                                "tcg_card": {"id": "me01-100"},
                            }
                        ],
                        "featured_elements": [
                            {
                                "pokemon_id": 380,
                                "card_id": "me01-typo",
                            }
                        ],
                    }
                }
            }
        )


def test_fetch_cutouts_downloads_exact_form_artwork_without_base_fallback(
    tmp_path: Path,
    monkeypatch,
):
    asset_dir = tmp_path / "ExGen3" / "sections" / "mega"
    bundle = SimpleNamespace(
        asset_dir=asset_dir,
        source_dir=asset_dir,
        asset_key="ExGen3/sections/mega",
        scope="ExGen3",
        poster_id="mega",
        section_id="mega",
        manifest={
            "layout": {"name": "standard_3x3"},
            "pokemon": {
                "strategy": "featured_from_scope",
                "count": "auto_from_layout_columns",
                "fallback_candidates": [],
            },
        },
    )
    scope_data = {
        "sections": {
            "mega": {
                "featured_elements": [
                    {
                        "pokemon_id": 380,
                        "pokemon_name": "Mega Latias",
                        "poster_subject": PosterSubject(
                            380,
                            10062,
                        ).as_mapping(),
                    },
                    {
                        "pokemon_id": 719,
                        "pokemon_name": "Mega Diancie",
                        "poster_subject": PosterSubject(
                            719,
                            10075,
                        ).as_mapping(),
                    },
                    {
                        "pokemon_id": 448,
                        "pokemon_name": "Mega Lucario",
                        "poster_subject": PosterSubject(
                            448,
                            10059,
                        ).as_mapping(),
                    },
                ]
            }
        }
    }
    requested_urls = []

    monkeypatch.setattr(
        fetch_cutouts,
        "poster_bundle",
        lambda *_args, **_kwargs: bundle,
    )
    monkeypatch.setattr(
        fetch_cutouts,
        "load_poster_scope_data",
        lambda *_args, **_kwargs: scope_data,
    )
    monkeypatch.setattr(fetch_cutouts, "collect_pokedex_names", lambda: {})

    def fake_download(url):
        requested_urls.append(url)
        return b"fixture"

    def fake_save(_payload, path):
        image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
        for x in range(100, 300):
            for y in range(100, 300):
                image.putpixel((x, y), (30, 120, 220, 255))
        image.save(path)
        return fetch_cutouts.validate_png(path)

    monkeypatch.setattr(fetch_cutouts, "download_bytes", fake_download)
    monkeypatch.setattr(fetch_cutouts, "save_cutout", fake_save)

    assert fetch_cutouts.fetch_cutouts("ExGen3/sections/mega") == 0

    assert requested_urls == [
        PosterSubject(380, 10062).image_url,
        PosterSubject(719, 10075).image_url,
        PosterSubject(448, 10059).image_url,
    ]
    assert PosterSubject(380, 380).image_url not in requested_urls
    payload = json.loads(
        (asset_dir / "cutouts" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["items"][0]["poster_subject"] == PosterSubject(
        380,
        10062,
    ).as_mapping()
    assert (
        payload["items"][0]["file"]
        == "pokemon_380_artwork_10062_mega_latias.png"
    )


def test_individual_promotion_rejects_source_form_cutout_mismatch(
    tmp_path: Path,
):
    asset_dir = tmp_path / "ME03"
    cutout_dir = asset_dir / "cutouts"
    cutout_dir.mkdir(parents=True)
    bundle = SimpleNamespace(
        asset_key="ME03",
        scope="ME03",
        section_id=None,
        asset_dir=asset_dir,
        source_dir=asset_dir,
        manifest={
            "layout": {"name": "standard_3x3"},
            "pokemon": {
                "strategy": "featured_from_scope",
                "count": "auto_from_layout_columns",
                "fallback_candidates": [],
            },
        },
    )
    scope_data = {
        "sections": {
            "all": {
                "featured_elements": [
                    {
                        "pokemon_id": 718,
                        "poster_subject": PosterSubject(
                            718,
                            10301,
                        ).as_mapping(),
                    },
                    {"pokemon_id": 495},
                    {"pokemon_id": 722},
                ]
            }
        }
    }
    (cutout_dir / "manifest.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "pokemon_id": 718,
                        "url": PosterSubject(718, 718).image_url,
                        "file": "pokemon_718_zygarde.png",
                    },
                    {
                        "pokemon_id": 495,
                        "url": PosterSubject(495, 495).image_url,
                        "file": "pokemon_495_snivy.png",
                    },
                    {
                        "pokemon_id": 722,
                        "url": PosterSubject(722, 722).image_url,
                        "file": "pokemon_722_rowlet.png",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="do not match"):
        poster_validator._validate_source_subjects(bundle, scope_data)


def test_2x2_promotion_accepts_first_two_of_three_curated_subjects(
    tmp_path: Path,
):
    asset_dir = tmp_path / "Pokedex" / "sections" / "gen1"
    cutout_dir = asset_dir / "cutouts"
    cutout_dir.mkdir(parents=True)
    bundle = SimpleNamespace(
        asset_key="Pokedex/sections/gen1",
        scope="Pokedex",
        section_id="gen1",
        asset_dir=asset_dir,
        source_dir=asset_dir,
        manifest={
            "layout": {"name": "standard_2x2"},
            "pokemon": {
                "strategy": "featured_from_scope",
                "count": "auto_from_layout_columns",
                "fallback_candidates": [],
            },
        },
    )
    featured = [
        {"pokemon_id": 1},
        {"pokemon_id": 4},
        {"pokemon_id": 7},
    ]
    scope_data = {
        "sections": {
            "gen1": {
                "featured_elements": featured,
                "title": {
                    language: "Generation I"
                    for language in poster_validator.POSTER_LANGUAGES
                },
                "subtitle": {
                    language: "Kanto"
                    for language in poster_validator.POSTER_LANGUAGES
                },
                "description": {
                    language: "#001 - #151"
                    for language in poster_validator.POSTER_LANGUAGES
                },
            }
        }
    }
    selected = featured[:2]
    (cutout_dir / "manifest.json").write_text(
        json.dumps({"items": selected}),
        encoding="utf-8",
    )

    poster_validator._validate_source_subjects(bundle, scope_data)


def test_validate_png_requires_transparency(tmp_path: Path):
    transparent = tmp_path / "transparent.png"
    img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    for x in range(100, 300):
        for y in range(100, 300):
            img.putpixel((x, y), (255, 0, 0, 255))
    img.save(transparent)

    validation = fetch_cutouts.validate_png(transparent)

    assert validation["validated_alpha"] is True
    assert validation["alpha_min"] == 0
    assert validation["alpha_max"] == 255


def test_validate_png_rejects_flattened_image(tmp_path: Path):
    flattened = tmp_path / "flattened.png"
    Image.new("RGBA", (400, 400), (255, 255, 255, 255)).save(flattened)

    validation = fetch_cutouts.validate_png(flattened)

    assert validation["validated_alpha"] is False
    assert "image has no transparent pixels" in validation["errors"]


def test_cutout_placements_share_one_foot_baseline():
    scope_dir = poster_bundle("Base1").source_dir
    placements = cutout_placements(build_page_layout("standard_3x3"), scope_dir)

    foot_positions = []
    for placement in placements:
        alpha_box = placement["image"].getchannel("A").getbbox()
        assert alpha_box is not None
        foot_positions.append(placement["y"] + alpha_box[3])

    assert len(set(foot_positions)) == 1


def test_cutout_placements_stay_inside_bottom_card_cells():
    scope_dir = poster_bundle("Base1").source_dir
    placements = cutout_placements(build_page_layout("standard_3x3"), scope_dir)

    for placement in placements:
        alpha_box = placement["image"].getchannel("A").getbbox()
        assert alpha_box is not None
        left = placement["x"] + alpha_box[0]
        top = placement["y"] + alpha_box[1]
        right = placement["x"] + alpha_box[2]
        bottom = placement["y"] + alpha_box[3]
        cell = placement["cell"]
        assert cell.x <= left < right <= cell.x + cell.width
        assert cell.y <= top < bottom <= cell.y + cell.height


def test_two_cutouts_use_the_outer_bottom_cards(tmp_path: Path):
    scope_dir = tmp_path / "scope"
    cutout_dir = scope_dir / "cutouts"
    cutout_dir.mkdir(parents=True)
    items = []
    for index in range(2):
        filename = f"pokemon_{index}.png"
        Image.new("RGBA", (200, 300), (40 + index, 80, 120, 255)).save(
            cutout_dir / filename
        )
        items.append({"file": filename, "pokemon_id": index + 1})
    (cutout_dir / "manifest.json").write_text(
        json.dumps({"items": items}),
        encoding="utf-8",
    )

    placements = cutout_placements(
        build_page_layout("standard_3x3"),
        scope_dir,
    )

    assert [placement["cell"].column for placement in placements] == [1, 3]


def test_joint_scene_placements_reuse_canonical_card_fit():
    scope_dir = poster_bundle("Base1").source_dir
    layout = build_page_layout("standard_3x3")
    exact = cutout_placements(layout, scope_dir)
    joint = joint_scene_cutout_placements(layout, scope_dir)

    for exact_item, joint_item in zip(exact, joint, strict=True):
        assert joint_item["cell"] == exact_item["cell"]
        assert joint_item["item"] == exact_item["item"]
        assert joint_item["x"] == exact_item["x"]
        assert joint_item["y"] == exact_item["y"]
        assert ImageChops.difference(
            joint_item["image"],
            exact_item["image"],
        ).getbbox() is None




def test_inpaint_reference_uses_exact_final_placements(tmp_path: Path):
    scope_dir = poster_bundle("Base1").source_dir
    build_identity_lock_references("Base1", 0.25, tmp_path)

    actual = Image.open(tmp_path / "inpaint_reference.png").convert("RGBA")
    layout = build_source_layout(
        "standard_3x3",
        width_px=actual.width,
        height_px=actual.height,
    )
    expected = Image.new("RGBA", actual.size, (226, 224, 211, 0))
    for placement in cutout_placements(layout, scope_dir):
        expected.alpha_composite(
            placement["image"],
            (placement["x"], placement["y"]),
        )

    assert ImageChops.difference(actual, expected).getbbox() is None
    assert not (tmp_path / "scene_reference.png").exists()


def test_joint_scene_preparation_writes_spatial_and_unscaled_identity_refs(
    tmp_path: Path,
):
    joint_dir = tmp_path / "joint"
    build_joint_scene_references(
        "Base1",
        joint_dir,
        megapixels=1.0,
    )

    assert not (joint_dir / "upper_context_mask.png").exists()
    assert not (joint_dir / "upper_context_generation_mask.png").exists()
    assert not (joint_dir / IDENTITY_LOCK_PROMPT_FILE).exists()
    assert not (joint_dir / "inpaint_reference.png").exists()
    assert not (joint_dir / "scene_reference.png").exists()
    assert not (joint_dir / "structure_reference.png").exists()
    assert not (joint_dir / "anima_scene_reference.png").exists()
    identity_paths = sorted(
        joint_dir.glob("identity_reference_*.png")
    )
    assert len(identity_paths) == 3

    actual = Image.open(
        joint_dir / "joint_scene_cast_reference.png"
    ).convert("RGBA")
    assert actual.size == output_dimensions("Base1", 0.5)
    layout = build_source_layout(
        "standard_3x3",
        width_px=actual.width,
        height_px=actual.height,
    )
    expected = Image.new("RGBA", actual.size, (226, 224, 211, 255))
    for placement in joint_scene_cutout_placements(
        layout,
        poster_bundle("Base1").source_dir,
    ):
        expected.alpha_composite(
            placement["image"],
            (placement["x"], placement["y"]),
        )
    assert ImageChops.difference(actual, expected).getbbox() is None

    source_dir = poster_bundle("Base1").source_dir
    items = load_cutout_items(source_dir)
    for item, identity_path in zip(items, identity_paths, strict=True):
        source = Image.open(
            source_dir / "cutouts" / item["file"]
        ).convert("RGBA")
        detail = Image.open(identity_path).convert("RGB")
        assert detail.size == (512, 512)
        x = (detail.width - source.width) // 2
        y = (detail.height - source.height) // 2
        difference = ImageChops.difference(
            detail.crop((x, y, x + source.width, y + source.height)),
            source.convert("RGB"),
        )
        opaque = source.getchannel("A").point(
            lambda value: 255 if value == 255 else 0
        )
        masked_difference = Image.composite(
            difference,
            Image.new("RGB", difference.size),
            opaque,
        )
        assert masked_difference.getbbox() is None


def test_regional_joint_scene_preparation_writes_only_identity_refs(
    tmp_path: Path,
):
    (tmp_path / "joint_scene_cast_reference.png").write_bytes(b"stale")
    build_joint_scene_references(
        "Base1",
        tmp_path,
        megapixels=1.0,
        include_cast=False,
    )

    assert not (tmp_path / "joint_scene_cast_reference.png").exists()
    assert [
        path.name
        for path in sorted(tmp_path.glob("identity_reference_*.png"))
    ] == [
        "identity_reference_1.png",
        "identity_reference_2.png",
        "identity_reference_3.png",
    ]


def test_individual_spatial_references_apply_opt_in_scales_without_changing_default(tmp_path: Path):
    bundle = poster_bundle("Base1")
    items = load_cutout_items(bundle.source_dir)
    first_key = resolve_poster_subject(items[0]).subject_key
    normal = build_individual_spatial_joint_references("Base1", tmp_path / "normal")
    scaled = build_individual_spatial_joint_references(
        "Base1", tmp_path / "scaled", subject_scales={first_key: 0.55},
    )
    with Image.open(normal[0]) as original, Image.open(scaled[0]) as smaller:
        assert ImageChops.difference(original, smaller).getbbox() is not None
        assert smaller.size == original.size
    with Image.open(normal[1]) as original, Image.open(scaled[1]) as unchanged:
        assert ImageChops.difference(original, unchanged).getbbox() is None




def test_identity_lock_mask_generates_only_above_the_bottom_subject_band(
    tmp_path: Path,
):
    build_identity_lock_references("Base1", 0.25, tmp_path)

    mask = Image.open(tmp_path / "upper_context_mask.png").convert("RGBA")
    alpha = mask.getchannel("A")
    generation_alpha = Image.open(
        tmp_path / "upper_context_generation_mask.png"
    ).convert("RGBA").getchannel("A")

    assert alpha.getpixel((mask.width // 2, 0)) == 0
    assert 0 < alpha.getpixel((mask.width // 2, round(mask.height * 0.65))) < 255
    assert alpha.getpixel((mask.width // 2, mask.height - 1)) == 255
    assert generation_alpha.getpixel((mask.width // 2, 0)) == 0
    assert generation_alpha.getpixel(
        (mask.width // 2, round(mask.height * 0.70))
    ) == 0
    assert generation_alpha.getpixel(
        (mask.width // 2, mask.height - 1)
    ) == 255


def test_identity_lock_mask_moves_up_for_an_unusually_tall_subject(
    tmp_path: Path,
):
    subject = Image.new("RGBA", (20, 30), (40, 80, 120, 255))
    transition_start, protected_start = build_upper_context_mask(
        100,
        100,
        [{"image": subject, "x": 40, "y": 55}],
        {"artwork": {"identity_lock": {"subject_clearance_ratio": 0.02}}},
        tmp_path,
    )

    assert protected_start == 53
    assert transition_start == 43
    alpha = Image.open(
        tmp_path / "upper_context_mask.png"
    ).convert("RGBA").getchannel("A")
    assert alpha.getpixel((50, transition_start - 1)) == 0
    assert alpha.getpixel((50, protected_start)) == 255
    generation_alpha = Image.open(
        tmp_path / "upper_context_generation_mask.png"
    ).convert("RGBA").getchannel("A")
    assert generation_alpha.getpixel((50, protected_start)) == 0
    assert generation_alpha.getpixel((50, 55)) == 255




def test_identity_lock_scene_prompt_is_scope_and_layout_driven():
    manifest = {
        "scope": "Example",
        "layout": {"name": "wide_4x4"},
        "text_cells": {
            "title": {"row": 1, "column": 3},
            "set_info": {"row": 2, "column": 3},
        },
        "artwork": {
            "scene": {
                "ground_noun": "shore",
                "constraints": [
                    "Distant basalt arches echo the expansion theme.",
                ],
            }
        },
    }
    scope_data = {
        "name": "Aurora Archive",
        "serie_name": "Example Series",
        "release_date": "2024-02-03",
    }

    prompt = build_identity_lock_prompt(manifest, scope_data)

    assert "Aurora Archive expansion" in prompt
    assert "from the Example Series" in prompt
    assert "released in 2024" in prompt
    assert "upper-column-3" in prompt
    assert "row-2-column-3" in prompt
    assert "uninterrupted, low-detail atmosphere" in prompt
    assert "later exact set logo" not in prompt
    assert "later deterministic set information" not in prompt
    assert "continuous low shore surface" in prompt
    assert "basalt arches" in prompt
    assert "source pixel as immutable" in prompt
    assert "landing pads" in prompt
    assert "Mewtwo" not in prompt


def test_identity_lock_geometry_defaults_scale_with_output_size():
    manifest: dict = {}

    assert identity_lock_config(manifest) == {
        "overscan_ratio": 0.04,
        "max_protected_start_ratio": 0.70,
        "transition_ratio": 0.10,
        "subject_clearance_ratio": 0.02,
    }
    assert identity_lock_overscan(848, 1168, manifest) == (880, 1216)
    assert identity_lock_overscan(1696, 2336, manifest) == (1760, 2432)


def test_new_tcg_set_manifest_bootstraps_the_joint_scene_flow():
    scope_data = {
        "type": "tcg_set",
        "name": "Aurora Archive",
        "release_date": "2024-02-03",
        "available_languages": ["de", "en", "fr"],
        "logo_urls": {
            "de": "https://example.test/de.png",
            "en": "https://example.test/en.png",
            "fr": "https://example.test/fr.png",
        },
    }
    generation_template = {
        "engine": "flux",
        "model": "model.safetensors",
        "model_sha256": "model-hash",
        "encoder": "encoder.safetensors",
        "encoder_sha256": "encoder-hash",
        "vae": "vae.safetensors",
        "vae_sha256": "vae-hash",
        "upscale_model": "upscale.pth",
        "upscale_model_sha256": "upscale-hash",
    }

    manifest = build_default_manifest(
        "EX42",
        scope_data,
        "wide_4x3",
        generation_template,
    )

    assert manifest["scope"] == "EX42"
    assert manifest["layout"]["name"] == "wide_4x3"
    assert manifest["pokemon"]["count"] == "auto_from_layout_columns"
    assert manifest["artwork"]["generation"]["mode"] == "joint_scene"
    assert (
        manifest["artwork"]["generation"]["reference_mode"]
            == "individual_spatial_joint"
    )
    assert manifest["artwork"]["generation"]["output_method"] == "lanczos"
    assert manifest["artwork"]["generation"]["output_dpi"] == 300
    assert "upscale_model" not in manifest["artwork"]["generation"]
    assert "upscale_model_sha256" not in manifest["artwork"]["generation"]
    assert manifest["artwork"]["generation"]["seed"] == stable_scope_seed(
        "EX42"
    )
    assert manifest["pdf"]["enabled"] is False
    assert manifest["title_logo"]["files"] == {
        "de": "logos/logo-de.png",
        "en": "logos/logo-en.png",
        "fr": "logos/logo-fr.png",
    }
    prompt = build_identity_lock_prompt(manifest, scope_data)
    assert "Aurora Archive expansion" in prompt
    assert "upper-column-2" in prompt
    assert "middle-column-2" in prompt


def test_new_tcg_set_manifest_keeps_every_advertised_pdf_language_logo():
    languages = (
        "de",
        "en",
        "fr",
        "es",
        "it",
        "ja",
        "ko",
        "zh_hans",
        "zh_hant",
    )
    scope_data = {
        "type": "tcg_set",
        "name": "Worldwide Archive",
        "release_date": "2026-08-03",
        "available_languages": list(languages),
        "logo_urls": {
            language: f"https://example.test/{language}.png"
            for language in languages
        },
    }

    manifest = build_default_manifest(
        "WW01",
        scope_data,
        "standard_3x3",
        {"engine": "flux"},
    )

    assert manifest["title_logo"]["files"] == {
        language: f"logos/logo-{language}.png"
        for language in languages
    }


def test_2x2_section_manifest_selects_two_of_three_curated_subjects():
    root = Path(__file__).resolve().parents[2]
    scope_data = fetch_cutouts.load_json(
        root / "data" / "output" / "Pokedex.json"
    )
    section = scope_data["sections"]["gen1"]
    generation = fetch_cutouts.load_yaml(
        root / "config" / "posters" / "Base1" / "poster.yaml"
    )["artwork"]["generation"]
    scene = section_scenes_for_scope("Pokedex")["gen1"]

    manifest = build_section_manifest(
        "Pokedex/sections/gen1",
        "Pokedex",
        "gen1",
        section,
        "standard_2x2",
        generation,
        scene,
    )

    assert manifest["pokemon"]["count"] == "auto_from_layout_columns"
    assert manifest["text_cells"] == default_text_cells("standard_2x2")


def test_every_current_tcg_set_bootstraps_without_set_specific_python():
    root = Path(__file__).resolve().parents[2]
    generation_template = fetch_cutouts.load_yaml(
        root / "config" / "posters" / "Base1" / "poster.yaml"
    )["artwork"]["generation"]
    checked = []
    for scope_path in sorted((root / "data" / "output").glob("*.json")):
        scope_data = fetch_cutouts.load_json(scope_path)
        if scope_data.get("type") != "tcg_set":
            continue
        scene = scene_for_scope(scope_path.stem)
        manifest = build_default_manifest(
            scope_path.stem,
            scope_data,
            "standard_3x3",
            generation_template,
            scene,
        )
        selected = fetch_cutouts.select_pokemon(
            manifest,
            scope_data,
            3,
            {},
        )
        prompt = build_identity_lock_prompt(manifest, scope_data)

        assert len(selected) == 3
        assert len({item["pokemon_id"] for item in selected}) == 3
        assert scene["concept"] in prompt
        assert manifest["artwork"]["scene"]["setting"] in prompt
        assert "source pixel as immutable" in prompt
        checked.append(scope_path.stem)

    assert set(checked) == set(load_scene_catalog())
    assert "Base1" in checked
    assert "SV03.5" in checked


def test_scene_catalog_covers_every_current_individual_tcg_set_exactly():
    missing, stale = validate_catalog_coverage()
    scenes = load_scene_catalog()

    assert missing == set()
    assert stale == set()
    assert set(available_tcg_scopes()) == set(scenes)
    assert all(scene["setting"] for scene in scenes.values())
    assert all("safe_areas" not in scene for scene in scenes.values())


def test_scene_catalog_covers_every_current_aggregate_section_exactly():
    missing, stale = validate_section_catalog_coverage()

    assert missing == set()
    assert stale == set()


def test_every_current_aggregate_section_bootstraps_from_shared_code():
    root = Path(__file__).resolve().parents[2]
    generation = fetch_cutouts.load_yaml(
        root / "config" / "posters" / "Base1" / "poster.yaml"
    )["artwork"]["generation"]
    checked = []
    for path in sorted((root / "data" / "output").glob("*.json")):
        scope_data = fetch_cutouts.load_json(path)
        if scope_data.get("type") == "tcg_set":
            continue
        scenes = section_scenes_for_scope(path.stem)
        for section_id, section in scope_data.get("sections", {}).items():
            manifest = build_section_manifest(
                f"{path.stem}/sections/{section_id}",
                path.stem,
                section_id,
                section,
                "standard_3x3",
                generation,
                scenes[section_id],
            )
            count = fetch_cutouts.resolve_requested_count(
                manifest,
                build_page_layout("standard_3x3"),
            )
            selected = fetch_cutouts.select_pokemon(
                manifest,
                {"set_id": path.stem, "sections": {section_id: section}},
                count,
                {},
            )

            assert len(selected) == count
            checked.append(f"{path.stem}/{section_id}")

    assert len(checked) == 15


def test_primal_section_uses_its_two_canonical_subjects_without_duplication():
    root = Path(__file__).resolve().parents[2]
    scope_data = fetch_cutouts.load_json(root / "data" / "output" / "ExGen2.json")
    section = scope_data["sections"]["primal"]
    generation = fetch_cutouts.load_yaml(
        root / "config" / "posters" / "Base1" / "poster.yaml"
    )["artwork"]["generation"]
    scene = fetch_cutouts.load_yaml(root / "config" / "posters" / "scenes.yaml")[
        "section_scopes"
    ]["ExGen2"]["primal"]

    manifest = build_section_manifest(
        "ExGen2/sections/primal",
        "ExGen2",
        "primal",
        section,
        "standard_3x3",
        generation,
        scene,
    )

    assert manifest["pokemon"]["count"] == 2
    assert [
        item["pokemon_name"] for item in section["featured_elements"]
    ] == ["Primal Kyogre", "Primal Groudon"]


def test_runner_uses_the_scope_generation_contract_as_its_defaults():
    root = Path(__file__).resolve().parents[2]
    manifest = fetch_cutouts.load_yaml(
        root / "config" / "posters" / "Base1" / "poster.yaml"
    )

    assert configured_generation("Base1") == manifest["artwork"]["generation"]


def test_runner_cli_resolves_production_defaults_from_the_scope(
    monkeypatch,
    tmp_path,
):
    captured = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return (
            tmp_path / "raw.png",
            tmp_path / "artwork.png",
            tmp_path / "final.png",
            tmp_path / "run.json",
        )

    monkeypatch.setattr(poster_runner, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_comfyui_poster.py", "--scope", "Base1"],
    )

    assert poster_runner.main() == 0

    generation = configured_generation("Base1")
    assert captured["args"][1] == generation["seed"]
    assert captured["args"][2] == generation["generation_megapixels"]
    assert captured["kwargs"]["engine"] == generation["engine"]
    assert captured["kwargs"]["flux_mode"] == generation["mode"]
    assert captured["kwargs"]["flux_model"] == generation["model"]
    assert captured["kwargs"]["flux_steps"] == generation["steps"]
    assert captured["kwargs"]["flux_clip"] == generation["encoder"]
    assert captured["kwargs"]["flux_vae"] == generation["vae"]
    assert captured["kwargs"]["output_dpi"] == generation["output_dpi"]
    assert captured["kwargs"]["upscale_model"] == generation.get(
        "upscale_model",
        poster_runner.DEFAULT_UPSCALE_MODEL,
    )


def test_localized_title_logo_requires_an_exact_language_file():
    manifest = {
        "title_logo": {
            "files": {
                "en": "logo-en.png",
                "de": "logo-de.png",
            }
        }
    }

    assert title_logo_file(manifest, "de") == "logo-de.png"
    assert title_logo_file(manifest, "fr") is None


def test_title_logo_downloads_use_scope_language_urls():
    manifest = {
        "title_logo": {
            "files": {
                "de": "logos/logo-de.png",
                "en": "logos/logo-en.png",
            }
        }
    }
    scope_data = {
        "logo_urls": {
            "de": "https://example.test/de.png",
            "en": "https://example.test/en.png",
        }
    }

    assert resolve_logo_downloads(manifest, scope_data) == [
        ("de", "logos/logo-de.png", "https://example.test/de.png"),
        ("en", "logos/logo-en.png", "https://example.test/en.png"),
    ]


def test_info_panel_is_centered_and_height_limited():
    cell = build_page_layout("standard_3x3", width_px=848).cell(2, 2)

    box = info_panel_box(
        cell,
        {"max_width_ratio": 0.92, "max_height_ratio": 0.68},
    )

    assert abs((box[0] + box[2]) / 2 - cell.center[0]) <= 0.5
    assert abs((box[1] + box[3]) / 2 - cell.center[1]) <= 0.5
    assert box[3] - box[1] <= round(cell.height * 0.68)


def test_info_panel_shrinks_long_set_names_to_their_row():
    box = (0, 0, 180, 52)
    text = "A Very Long Localized Trading Card Expansion Name"

    font = fitted_font(
        text,
        box,
        preferred_size=28,
        minimum_size=10,
        bold=True,
    )
    lines = wrap_text(text, font, box[2] - box[0])
    line_heights = [
        bounds[3] - bounds[1]
        for bounds in (font.getbbox(line) for line in lines)
    ]
    total_height = sum(line_heights) + max(0, len(lines) - 1) * round(
        font.size * 0.28
    )

    assert font.size < 28
    assert total_height <= box[3] - box[1]


def test_long_localized_title_stays_inside_its_cell_without_panel():
    canvas = Image.new("RGBA", (848, 1168), (74, 151, 211, 255))
    title_cell = build_page_layout(
        "standard_3x3",
        width_px=canvas.width,
    ).cell(1, 2)

    text_box = draw_title_text(
        canvas,
        title_cell,
        "Mega Pokémon ex",
        "en",
    )

    pixels = canvas.load()
    text_points = [
        (x, y)
        for y in range(canvas.height)
        for x in range(canvas.width)
        if pixels[x, y][:3] == (255, 248, 215)
        and pixels[x, y][3] == 255
    ]
    assert text_points
    assert min(x for x, _y in text_points) >= text_box[0]
    assert max(x for x, _y in text_points) < text_box[2]
    assert min(y for _x, y in text_points) >= text_box[1]
    assert max(y for _x, y in text_points) < text_box[3]
    assert all(
        pixel[:3] != (253, 244, 202)
        for pixel in canvas.get_flattened_data()
    )


def test_title_font_avoids_short_orphan_line():
    canvas = Image.new("RGBA", (2368, 3268), (74, 151, 211, 255))
    title_cell = build_page_layout(
        "standard_3x3",
        width_px=canvas.width,
    ).cell(1, 2)
    text_box = title_cell.inset(0.05, 0.31)
    title = "Pokémon ex - Generation 1"

    font = fitted_font(
        title,
        text_box,
        preferred_size=max(14, title_cell.height // 7),
        minimum_size=max(10, title_cell.height // 24),
        bold=True,
        language="de",
        avoid_short_last_line=True,
    )

    assert wrap_text(title, font, text_box[2] - text_box[0]) == [
        "Pokémon ex -",
        "Generation 1",
    ]


@pytest.mark.parametrize(
    ("language", "title"),
    (
        ("de", "Pokémon [EX_NEW]"),
        ("en", "Pokémon [EX_NEW]"),
        ("fr", "Pokémon [EX_NEW]"),
        ("es", "Pokémon [EX_NEW]"),
        ("it", "Pokémon [EX_NEW]"),
        ("ja", "ポケモン [EX_NEW]"),
        ("ko", "포켓몬 [EX_NEW]"),
        ("zh_hans", "宝可梦 [EX_NEW]"),
        ("zh_hant", "寶可夢 [EX_NEW]"),
    ),
)
def test_inline_logo_title_stays_inside_its_cell_without_panel(language, title):
    canvas = Image.new("RGBA", (848, 1168), (74, 151, 211, 255))
    title_cell = build_page_layout(
        "standard_3x3",
        width_px=canvas.width,
    ).cell(1, 2)

    title_box = draw_inline_logo_title(
        canvas,
        title_cell,
        title,
        language,
    )

    assert title_box[0] >= title_cell.x
    assert title_box[1] >= title_cell.y
    assert title_box[2] <= title_cell.x + title_cell.width
    assert title_box[3] <= title_cell.y + title_cell.height
    cell_pixels = canvas.crop(
        (
            title_cell.x,
            title_cell.y,
            title_cell.x + title_cell.width,
            title_cell.y + title_cell.height,
        )
    ).get_flattened_data()
    assert all(pixel[:3] != (253, 244, 202) for pixel in cell_pixels)




def test_comfyui_identity_lock_uses_clean_ground_then_upper_context_pass():
    workflow = build_workflow(
        "Base1",
        seed=123,
        megapixels=0.25,
        generation_mode="identity_lock",
    )

    assert {
        node["inputs"]["image"]
        for node in workflow.values()
        if node["class_type"] == "LoadImage"
    } == {
        "inpaint_reference.png",
        "upper_context_generation_mask.png",
        "upper_context_mask.png",
    }
    assert workflow["15"]["class_type"] == "EmptySD3LatentImage"
    assert workflow["15"]["inputs"]["width"] > workflow["27"]["inputs"]["width"]
    assert workflow["15"]["inputs"]["height"] > workflow["27"]["inputs"]["height"]
    assert workflow["11"]["inputs"]["latent_image"] == ["15", 0]
    assert workflow["26"]["class_type"] == "Flux2Scheduler"
    assert workflow["26"]["inputs"]["width"] == workflow["27"]["inputs"]["width"]
    assert workflow["26"]["inputs"]["height"] == workflow["27"]["inputs"]["height"]
    assert workflow["27"]["class_type"] == "ImageCrop"
    assert workflow["27"]["inputs"]["image"] == ["12", 0]
    assert workflow["19"]["class_type"] == "ImageCompositeMasked"
    assert workflow["19"]["inputs"]["destination"] == ["27", 0]
    assert workflow["19"]["inputs"]["source"] == ["14", 0]
    assert workflow["21"]["class_type"] == "VAEEncodeForInpaint"
    assert workflow["21"]["inputs"]["pixels"] == ["19", 0]
    assert workflow["21"]["inputs"]["mask"] == ["28", 1]
    assert workflow["22"]["inputs"]["noise_seed"] == 124
    assert workflow["23"]["inputs"]["latent_image"] == ["21", 0]
    assert workflow["23"]["inputs"]["sigmas"] == ["26", 0]
    assert workflow["25"]["inputs"]["destination"] == ["19", 0]
    assert workflow["25"]["inputs"]["source"] == ["24", 0]
    assert workflow["25"]["inputs"]["mask"] == ["20", 1]
    assert workflow["13"]["inputs"]["images"] == ["25", 0]
    assert not any(
        node["class_type"] == "ReferenceLatent"
        for node in workflow.values()
    )






def test_joint_scene_synthesizes_landscape_and_subjects_in_one_shot():
    workflow = build_workflow(
        "Base1",
        seed=123,
        megapixels=0.25,
        generation_mode="joint_scene",
        reference_mode="spatial_identity_joint",
    )

    assert [
        node["inputs"]["image"]
        for node in workflow.values()
        if node["class_type"] == "LoadImage"
    ] == [
        "joint_scene_cast_reference.png",
        "identity_reference_1.png",
        "identity_reference_2.png",
        "identity_reference_3.png",
    ]
    assert sum(
        node["class_type"] == "EmptyFlux2LatentImage"
        for node in workflow.values()
    ) == 1
    assert sum(
        node["class_type"] == "SamplerCustomAdvanced"
        for node in workflow.values()
    ) == 1
    assert sum(
        node["class_type"] == "ReferenceLatent"
        for node in workflow.values()
    ) == 8
    assert sum(
        node["class_type"] == "VAEEncode"
        for node in workflow.values()
    ) == 4
    previous_positive = ["4", 0]
    previous_negative = ["5", 0]
    for index in range(4):
        encode_id = str(31 + index * 4)
        positive_id = str(32 + index * 4)
        negative_id = str(33 + index * 4)
        assert workflow[positive_id]["inputs"] == {
            "conditioning": previous_positive,
            "latent": [encode_id, 0],
        }
        assert workflow[negative_id]["inputs"] == {
            "conditioning": previous_negative,
            "latent": [encode_id, 0],
        }
        previous_positive = [positive_id, 0]
        previous_negative = [negative_id, 0]
    assert workflow["70"]["inputs"]["positive"] == previous_positive
    assert workflow["70"]["inputs"]["negative"] == previous_negative

    assert not any(
        node["class_type"] == "ImageCompositeMasked"
        for node in workflow.values()
    )
    assert not any(
        node["class_type"] in {
            "ImageCompositeMasked",
            "VAEEncodeForInpaint",
        }
        for node in workflow.values()
    )

    prompt = workflow["4"]["inputs"]["text"]
    assert "Generate the complete final image in one unified denoising pass" in prompt
    assert "There is no later character overlay" in prompt
    assert "There is no supplied landscape image" in prompt
    assert "no pre-generated background plate" in prompt
    assert "IMAGE 1 is the sole spatial cast-layout reference" in prompt
    assert "IMAGE 2 is the exact identity and anatomy reference" in prompt
    assert "not additional subjects" in prompt
    assert "mandatory placement and scale contract" in prompt
    assert "invisible no-crossing volume" in prompt
    assert "Avoid landscape-character intersections" in prompt
    assert "Do not conceal any character part" in prompt
    assert "Mewtwo" in prompt
    assert "Bulbasaur" in prompt
    assert "Charmander" in prompt


def test_regional_joint_scene_binds_each_identity_to_its_physical_card():
    workflow = build_workflow(
        "Base1",
        seed=123,
        megapixels=0.25,
        generation_mode="joint_scene",
        reference_mode="regional_identity_joint",
    )

    assert [
        node["inputs"]["image"]
        for node in workflow.values()
        if node["class_type"] == "LoadImage"
    ] == [
        "identity_reference_1.png",
        "identity_reference_2.png",
        "identity_reference_3.png",
    ]
    assert sum(
        node["class_type"] == "CLIPTextEncode"
        for node in workflow.values()
    ) == 4
    assert sum(
        node["class_type"] == "ReferenceLatent"
        for node in workflow.values()
    ) == 3
    assert sum(
        node["class_type"] == "ConditioningSetMask"
        for node in workflow.values()
    ) == 3
    assert sum(
        node["class_type"] == "SolidMask"
        for node in workflow.values()
    ) == 4
    assert sum(
        node["class_type"] == "FeatherMask"
        for node in workflow.values()
    ) == 3
    assert sum(
        node["class_type"] == "MaskComposite"
        for node in workflow.values()
    ) == 3
    assert sum(
        node["class_type"] == "EmptyFlux2LatentImage"
        for node in workflow.values()
    ) == 1
    assert sum(
        node["class_type"] == "SamplerCustomAdvanced"
        for node in workflow.values()
    ) == 1
    assert sum(
        node["class_type"] == "VAEDecode"
        for node in workflow.values()
    ) == 1

    width = workflow["6"]["inputs"]["width"]
    height = workflow["6"]["inputs"]["height"]
    layout = build_source_layout(
        "standard_3x3",
        width_px=width,
        height_px=height,
    )
    placements = joint_scene_canvas_placements(
        poster_bundle("Base1").source_dir,
        layout_name="standard_3x3",
        canvas_size=(width, height),
    )
    contracts = normalized_visible_placement_contract(
        placements,
        canvas_size=(width, height),
    )
    for index, contract in enumerate(contracts, start=1):
        base = 20 + (index - 1) * 10
        area = poster_workflow.regional_conditioning_area(contract)
        mask = poster_workflow.regional_conditioning_mask(
            area,
            canvas_size=(width, height),
        )
        assert workflow[str(base + 3)]["inputs"] == {
            "conditioning": [str(base), 0],
            "latent": [str(base + 2), 0],
        }
        assert workflow[str(base + 4)]["inputs"] == {
            "value": 1.0,
            "width": mask["width"],
            "height": mask["height"],
        }
        assert workflow[str(base + 5)]["inputs"] == {
            "mask": [str(base + 4), 0],
            "left": mask["left"],
            "top": mask["top"],
            "right": mask["right"],
            "bottom": mask["bottom"],
        }
        assert workflow[str(base + 6)]["inputs"] == {
            "destination": ["11", 0],
            "source": [str(base + 5), 0],
            "x": mask["x"],
            "y": mask["y"],
            "operation": "add",
        }
        assert workflow[str(base + 7)]["inputs"] == {
            "conditioning": [str(base + 3), 0],
            "mask": [str(base + 6), 0],
            "set_cond_area": "mask bounds",
            "strength": 1.0,
        }

    assert workflow["69"] == {
        "class_type": "ConditioningCombine",
        "inputs": {
            "conditioning_1": ["61", 0],
            "conditioning_2": ["9", 0],
        },
    }
    assert workflow["9"] == {
        "class_type": "ConditioningSetAreaStrength",
        "inputs": {
            "conditioning": ["4", 0],
            "strength": 0.2,
        },
    }
    assert workflow["70"]["inputs"]["positive"] == ["69", 0]
    assert workflow["70"]["inputs"]["negative"] == ["5", 0]
    assert "locally conditioned subjects" in workflow["4"]["inputs"]["text"]
    assert "landscape only" not in workflow["4"]["inputs"]["text"]
    assert "Mewtwo" in workflow["20"]["inputs"]["text"]
    assert "Bulbasaur" in workflow["30"]["inputs"]["text"]
    assert "Charmander" in workflow["40"]["inputs"]["text"]
    assert "global landscape conditioning remains active" in workflow["20"][
        "inputs"
    ]["text"]
    assert "only a local subject-identity condition" in workflow["20"]["inputs"]["text"]
    assert "inherit all landscape" in workflow["20"]["inputs"]["text"]
    assert "Match this lighting:" not in workflow["20"]["inputs"]["text"]
    assert "celestial body, rainbow, landmark" not in workflow["20"]["inputs"]["text"]
    assert "shrinking into a distant figure" in workflow["20"]["inputs"]["text"]
    assert "physical card region" not in workflow["20"]["inputs"]["text"]
    assert "protected region" not in workflow["20"]["inputs"]["text"]
    assert "card-shaped zone" not in workflow["20"]["inputs"]["text"]
    assert "uninterrupted and unframed" in workflow["20"]["inputs"]["text"]
    assert "local meadow" not in workflow["20"]["inputs"]["text"]
    assert not any(
        node["class_type"]
        in {
            "ImageCompositeMasked",
            "VAEEncodeForInpaint",
        }
        for node in workflow.values()
    )


def test_regional_joint_scene_places_two_subjects_in_outer_cards():
    workflow = build_workflow(
        "ExGen2/sections/primal",
        seed=123,
        megapixels=0.25,
        generation_mode="joint_scene",
        reference_mode="regional_identity_joint",
    )

    assert [
        node["inputs"]["image"]
        for node in workflow.values()
        if node["class_type"] == "LoadImage"
    ] == [
        "identity_reference_1.png",
        "identity_reference_2.png",
    ]
    assert sum(
        node["class_type"] == "ReferenceLatent"
        for node in workflow.values()
    ) == 2
    assert sum(
        node["class_type"] == "ConditioningSetMask"
        for node in workflow.values()
    ) == 2

    width = workflow["6"]["inputs"]["width"]
    height = workflow["6"]["inputs"]["height"]
    placements = joint_scene_canvas_placements(
        poster_bundle("ExGen2/sections/primal").source_dir,
        layout_name="standard_3x3",
        canvas_size=(width, height),
    )
    contracts = normalized_visible_placement_contract(
        placements,
        canvas_size=(width, height),
    )
    for index, contract in enumerate(contracts, start=1):
        base = 20 + (index - 1) * 10
        area = poster_workflow.regional_conditioning_area(contract)
        mask = poster_workflow.regional_conditioning_mask(
            area,
            canvas_size=(width, height),
        )
        masked_conditioning = workflow[str(base + 7)]["inputs"]
        assert workflow[str(base + 4)]["inputs"]["width"] == mask["width"]
        assert workflow[str(base + 4)]["inputs"]["height"] == mask["height"]
        assert workflow[str(base + 6)]["inputs"]["x"] == mask["x"]
        assert workflow[str(base + 6)]["inputs"]["y"] == mask["y"]
        assert masked_conditioning == {
            "conditioning": [str(base + 3), 0],
            "mask": [str(base + 6), 0],
            "set_cond_area": "mask bounds",
            "strength": 1.0,
        }

    assert "Primal Kyogre" in workflow["20"]["inputs"]["text"]
    assert "Primal Groudon" in workflow["30"]["inputs"]["text"]
    assert sum(
        node["class_type"] == "ConditioningCombine"
        for node in workflow.values()
    ) == 2
    assert sum(
        node["class_type"] == "SamplerCustomAdvanced"
        for node in workflow.values()
    ) == 1


def test_regional_joint_scene_supports_four_physical_card_regions(
    tmp_path: Path,
    monkeypatch,
):
    scope_dir = tmp_path / "Base1"
    cutout_dir = scope_dir / "cutouts"
    cutout_dir.mkdir(parents=True)
    (scope_dir / "poster.yaml").write_text(
        yaml.safe_dump(
            {
                "scope": "Base1",
                "layout": {"name": "wide_4x3"},
                "artwork": {
                    "scene": {
                        "concept": "Four-subject regional workflow test",
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    items = []
    for index in range(1, 5):
        filename = f"subject_{index}.png"
        Image.new(
            "RGBA",
            (64, 64),
            (40 * index, 20 * index, 10 * index, 255),
        ).save(cutout_dir / filename)
        items.append(
            {
                "pokemon_id": index,
                "name_en": f"Subject {index}",
                "file": filename,
            }
        )
    (cutout_dir / "manifest.json").write_text(
        json.dumps({"items": items}),
        encoding="utf-8",
    )
    monkeypatch.setattr(poster_workflow, "POSTER_ASSETS", tmp_path)

    workflow = poster_workflow.build_workflow(
        "Base1",
        seed=123,
        megapixels=0.25,
        generation_mode="joint_scene",
        reference_mode="regional_identity_joint",
    )

    assert [
        workflow[str(21 + index * 10)]["inputs"]["image"]
        for index in range(4)
    ] == [
        "identity_reference_1.png",
        "identity_reference_2.png",
        "identity_reference_3.png",
        "identity_reference_4.png",
    ]
    assert all(
        workflow[str(27 + index * 10)]["class_type"]
        == "ConditioningSetMask"
        for index in range(4)
    )
    assert sum(
        node["class_type"] == "FeatherMask"
        for node in workflow.values()
    ) == 4
    assert sum(
        node["class_type"] == "ConditioningCombine"
        for node in workflow.values()
    ) == 4
    assert not any(
        node["class_type"] == "ConditioningSetDefaultCombine"
        for node in workflow.values()
    )
    assert sum(
        node["class_type"] == "SamplerCustomAdvanced"
        for node in workflow.values()
    ) == 1




def test_joint_scene_prompt_separates_spatial_and_identity_roles():
    bundle = poster_bundle("Pokedex/sections/gen7")
    scope_data = load_poster_scope_data(bundle)
    items = load_cutout_items(bundle.source_dir)
    width, height = latent_canvas_dimensions("standard_3x3", 1.0)
    placement_contract = normalized_visible_placement_contract(
        joint_scene_cutout_placements(
            build_source_layout(
                "standard_3x3",
                width_px=width,
                height_px=height,
            ),
            bundle.source_dir,
        ),
        canvas_size=(width, height),
    )

    final = build_joint_scene_prompt(
        bundle.manifest,
        scope_data,
        items,
        placement_contract=placement_contract,
    )
    legacy = build_joint_scene_prompt(
        bundle.manifest,
        scope_data,
        items,
        placement_contract=placement_contract,
        prefer_natural_separation=False,
        avoid_foreground_intersections=False,
    )
    snapshot = build_joint_prompt_snapshot(
        bundle.manifest,
        scope_data,
        items,
        placement_contract=placement_contract,
    )

    assert "Rowlet" in final
    assert "Litten" in final
    assert "Popplio" in final
    assert "IMAGE 2 is the exact identity and anatomy reference" in final
    assert "IMAGE 1 is the sole spatial cast-layout reference" in final
    assert "neutral field is empty reference space" in final
    assert "mandatory placement and scale contract" in final
    assert "not additional subjects" in final
    assert "small physically plausible edge occlusions" not in final
    assert "invisible no-crossing volume" in final
    assert "Avoid landscape-character intersections" in final
    assert "Do not conceal any character part" in final
    assert "invisible no-crossing volume" not in legacy
    assert "JOINT SCENE - ONE-SHOT FINAL SYNTHESIS" in snapshot
    assert "SUBJECT-FREE LANDSCAPE DRAFT" not in snapshot


def test_joint_scene_scope_constraints_reach_the_one_shot_prompt():
    bundle = poster_bundle("Pokedex/sections/gen7")
    manifest = copy.deepcopy(bundle.manifest)
    constraint = "Keep the distant observatory below the cloud line."
    manifest["artwork"]["scene"]["constraints"] = [constraint]
    scope_data = load_poster_scope_data(bundle)
    items = load_cutout_items(bundle.source_dir)
    width, height = latent_canvas_dimensions("standard_3x3", 1.0)
    placement_contract = normalized_visible_placement_contract(
        joint_scene_cutout_placements(
            build_source_layout(
                "standard_3x3",
                width_px=width,
                height_px=height,
            ),
            bundle.source_dir,
        ),
        canvas_size=(width, height),
    )

    assert constraint in build_joint_scene_prompt(
        manifest,
        scope_data,
        items,
        placement_contract=placement_contract,
    )


def test_joint_scene_workflow_writes_one_shot_prompt_snapshot(
    tmp_path: Path,
):
    workflow_path = write_engine_workflow(
        "flux",
        "Base1",
        123,
        0.25,
        flux_mode="joint_scene",
        workflow_output_dir=tmp_path,
    )

    snapshot = tmp_path / INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE
    assert workflow_path.name == (
        "workflow_api_joint_scene_individual_spatial_joint_0p25mp_123.json"
    )
    assert snapshot.is_file()
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    expected = "\n\n".join(
        (
            "INDIVIDUAL SPATIAL JOINT - ISOLATED PREFLIGHT",
            workflow["4"]["inputs"]["text"],
        )
    )
    assert snapshot.read_text(encoding="utf-8") == expected.strip() + "\n"


def test_regional_joint_scene_writes_distinct_workflow_and_prompt_snapshot(
    tmp_path: Path,
):
    workflow_path = write_engine_workflow(
        "flux",
        "Base1",
        123,
        0.25,
        flux_mode="joint_scene",
        flux_reference_mode="regional_identity_joint",
        workflow_output_dir=tmp_path,
    )

    snapshot = tmp_path / REGIONAL_JOINT_SCENE_PROMPT_FILE
    assert workflow_path.name == (
        "workflow_api_joint_scene_regional_identity_joint_0p25mp_123.json"
    )
    assert snapshot.is_file()
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    assert "Prefer natural placement" in workflow["20"]["inputs"]["text"]
    assert (
        "without halos, artificial gaps"
        in workflow["20"]["inputs"]["text"]
    )
    assert "only a local subject-identity condition" in workflow["20"]["inputs"]["text"]
    assert "Match this lighting:" not in workflow["20"]["inputs"]["text"]
    expected = "\n\n".join(
        (
            "REGIONAL JOINT SCENE - ONE-SHOT FINAL SYNTHESIS",
            f"GLOBAL LANDSCAPE\n\n{workflow['4']['inputs']['text']}",
            f"LOCAL SUBJECT 1 - Mewtwo\n\n{workflow['20']['inputs']['text']}",
            f"LOCAL SUBJECT 2 - Bulbasaur\n\n{workflow['30']['inputs']['text']}",
            f"LOCAL SUBJECT 3 - Charmander\n\n{workflow['40']['inputs']['text']}",
        )
    )
    assert snapshot.read_text(encoding="utf-8") == expected.strip() + "\n"




def test_only_reviewed_flux_workflows_are_selectable(tmp_path: Path):
    joint = write_engine_workflow(
        "flux",
        "Base1",
        123,
        0.25,
        flux_mode="joint_scene",
        workflow_output_dir=tmp_path,
    )
    locked = write_engine_workflow(
        "flux",
        "Base1",
        123,
        0.25,
        flux_mode="identity_lock",
        workflow_output_dir=tmp_path,
    )

    assert joint.name == (
        "workflow_api_joint_scene_individual_spatial_joint_0p25mp_123.json"
    )
    assert locked.name == "workflow_api_identity_lock_0p25mp_123.json"
    with pytest.raises(ValueError, match="only 'flux' is supported"):
        write_engine_workflow(
            "anima",
            "Base1",
            123,
            0.25,
            workflow_output_dir=tmp_path,
        )
    with pytest.raises(ValueError, match="Unsupported FLUX generation mode"):
        write_engine_workflow(
            "flux",
            "Base1",
            123,
            0.25,
            flux_mode="unsupported",
            workflow_output_dir=tmp_path,
        )


def test_flux_workflow_uses_the_selected_vae(tmp_path: Path):
    workflow_path = write_engine_workflow(
        "flux",
        "Base1",
        123,
        0.25,
        flux_vae="reviewed-vae.safetensors",
        workflow_output_dir=tmp_path,
    )

    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    assert workflow["3"]["inputs"]["vae_name"] == "reviewed-vae.safetensors"


def test_flux_workflow_files_are_unique_per_seed(tmp_path: Path):
    first = write_engine_workflow(
        "flux", "Base1", 123, 0.25, workflow_output_dir=tmp_path
    )
    second = write_engine_workflow(
        "flux", "Base1", 124, 0.25, workflow_output_dir=tmp_path
    )
    full_size = write_engine_workflow(
        "flux", "Base1", 123, 1.0, workflow_output_dir=tmp_path
    )

    assert first != second
    assert first != full_size


def test_comfyui_server_scope_is_read_from_input_directory(monkeypatch, tmp_path):
    expected = tmp_path / "scope" / "comfyui_poster"
    main_path = tmp_path / "ComfyUI" / "main.py"
    monkeypatch.setattr(
        "scripts.poster_assets.queue_comfyui_workflow.request_json",
        lambda _url: {
            "system": {
                "argv": [
                    str(main_path),
                    "--input-directory",
                    str(expected),
                ]
            }
        },
    )

    assert server_input_directory("http://example.test") == expected.resolve()
    assert server_comfyui_root("http://example.test") == main_path.parent.resolve()
    validate_server_input_directory("http://example.test", expected)


def test_comfyui_http_error_includes_validation_body(monkeypatch):
    import io
    import urllib.error

    error = urllib.error.HTTPError(
        "http://example.test/prompt",
        400,
        "Bad Request",
        {},
        io.BytesIO(b'{"error":"bad node"}'),
    )

    def reject(*_args, **_kwargs):
        raise error

    monkeypatch.setattr("urllib.request.urlopen", reject)

    with pytest.raises(RuntimeError, match='bad node'):
        request_json("http://example.test/prompt", {"prompt": {}})


def test_comfyui_server_rejects_another_scope(monkeypatch, tmp_path):
    actual = tmp_path / "Base1" / "comfyui_poster"
    expected = tmp_path / "SV03.5" / "comfyui_poster"
    monkeypatch.setattr(
        "scripts.poster_assets.queue_comfyui_workflow.request_json",
        lambda _url: {
            "system": {
                "argv": [f"--input-directory={actual}"],
            }
        },
    )

    try:
        validate_server_input_directory("http://example.test", expected)
    except RuntimeError as error:
        assert "input directory mismatch" in str(error)
        assert "same --scope" in str(error)
    else:
        raise AssertionError("scope mismatch was accepted")


def test_flux_model_and_steps_are_selectable():
    workflow = build_workflow(
        "Base1",
        seed=123,
        megapixels=0.25,
        unet_name="flux-2-klein-base-4b-fp8.safetensors",
        generation_mode="identity_lock",
        steps=24,
        clip_name="qwen_3_8b_fp4mixed.safetensors",
    )

    assert workflow["1"]["inputs"]["unet_name"] == "flux-2-klein-base-4b-fp8.safetensors"
    assert workflow["7"]["inputs"]["steps"] == 24
    assert workflow["2"]["inputs"]["clip_name"] == "qwen_3_8b_fp4mixed.safetensors"


def test_upscale_workflow_uses_model_then_exact_print_dimensions():
    workflow = build_upscale_workflow(
        "Base1",
        "temp/candidate.png",
        dpi=300,
        model_name="example-upscaler.pth",
    )

    assert workflow["1"]["inputs"]["image"] == "temp/candidate.png"
    assert workflow["2"]["inputs"]["model_name"] == "example-upscaler.pth"
    assert workflow["3"]["class_type"] == "ImageUpscaleWithModel"
    assert workflow["4"]["inputs"]["width"] == 2368
    assert workflow["4"]["inputs"]["height"] == 3268
    assert workflow["4"]["inputs"]["crop"] == "disabled"


def test_upscale_input_normalizes_to_physical_aspect_ratio(
    tmp_path: Path,
    monkeypatch,
):
    assets_root = tmp_path / "poster_assets"
    scope_dir = assets_root / "Example"
    scope_dir.mkdir(parents=True)
    (scope_dir / "poster.yaml").write_text(
        "layout:\n  name: standard_3x3\n",
        encoding="utf-8",
    )
    source = tmp_path / "source.png"
    destination = tmp_path / "normalized.png"
    Image.new("RGB", (608, 832), (40, 90, 140)).save(source)
    monkeypatch.setattr(poster_upscale, "POSTER_ASSETS", assets_root)

    poster_upscale.normalize_upscale_input(
        "Example",
        source,
        destination,
    )

    assert Image.open(destination).size == (
        608,
        build_page_layout("standard_3x3", width_px=608).height_px,
    )


def test_print_dpi_survives_finalization_and_card_slicing(tmp_path: Path):
    raw_path = tmp_path / "raw.png"
    final_path = tmp_path / "final.png"
    card_dir = tmp_path / "cards"
    layout = build_print_layout("standard_3x3", 300)
    Image.new(
        "RGB",
        (layout.width_px, layout.height_px),
        (80, 140, 90),
    ).save(raw_path, dpi=(300, 300))

    finalize("Base1", raw_path, final_path)
    cards = slice_poster("Base1", final_path, card_dir)

    assert abs(Image.open(final_path).info["dpi"][0] - 300) < 0.1
    assert len(cards) == 9
    assert all(
        abs(Image.open(path).info["dpi"][0] - 300) < 0.1
        for path in cards
    )


def test_finalizer_preserves_size_and_adds_deterministic_panels(tmp_path: Path):
    raw_path = tmp_path / "raw.png"
    final_path = tmp_path / "final.png"
    Image.new("RGB", (432, 608), (80, 140, 90)).save(raw_path)

    finalize("Base1", raw_path, final_path)

    raw = Image.open(raw_path).convert("RGB")
    final = Image.open(final_path).convert("RGB")
    assert final.size == raw.size
    assert ImageChops.difference(raw, final).getbbox() is not None
    # The lower character area belongs exclusively to the generated artwork.
    assert final.getpixel((raw.width // 4, raw.height * 5 // 6)) == raw.getpixel(
        (raw.width // 4, raw.height * 5 // 6)
    )


def test_raw_artwork_validation_rejects_blank_output(tmp_path: Path):
    blank = tmp_path / "blank.png"
    Image.new("RGB", (64, 64), (0, 0, 0)).save(blank)

    try:
        validate_raw_artwork(blank)
    except RuntimeError as error:
        assert "blank or near-constant" in str(error)
    else:
        raise AssertionError("blank artwork was accepted")


def test_identity_lock_validation_requires_exact_opaque_source_pixels(
    tmp_path: Path,
):
    reference_path = tmp_path / "inpaint_reference.png"
    raw_path = tmp_path / "raw.png"
    reference = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    for y in range(3, 9):
        for x in range(2, 10):
            reference.putpixel((x, y), (40, 120, 210, 255))
    reference.save(reference_path)
    raw = Image.new("RGB", reference.size, (230, 220, 180))
    raw.paste(reference.convert("RGB"), mask=reference.getchannel("A"))
    raw.save(raw_path)

    validation = validate_identity_lock_pixels(
        "Example",
        raw_path,
        reference_path,
    )

    assert validation == {
        "method": "exact_opaque_source_pixels",
        "opaque_pixels": 48,
        "changed_pixels": 0,
        "passed": True,
    }

    raw.putpixel((4, 5), (41, 120, 210))
    raw.save(raw_path)
    try:
        validate_identity_lock_pixels(
            "Example",
            raw_path,
            reference_path,
        )
    except RuntimeError as error:
        assert "fully opaque pixels changed" in str(error)
    else:
        raise AssertionError("Changed identity-lock source pixel was accepted")


def test_resize_artwork_uses_requested_poster_dimensions(tmp_path: Path):
    source = tmp_path / "source.png"
    destination = tmp_path / "resized.png"
    artwork = Image.new("RGB", (64, 96), (40, 120, 80))
    artwork.paste((120, 180, 220), (0, 0, 64, 48))
    artwork.save(source)

    resize_artwork("Base1", source, destination, 0.25)

    assert Image.open(destination).size == (432, 596)


@pytest.mark.parametrize(
    "layout_name",
    ("standard_2x2", "standard_3x3", "wide_4x3", "wide_4x4"),
)
def test_resize_artwork_to_dpi_uses_exact_print_dimensions(
    tmp_path: Path,
    monkeypatch,
    layout_name: str,
):
    source = tmp_path / "source.png"
    destination = tmp_path / f"{layout_name}.png"
    source_image = Image.new("RGB", (64, 96), (40, 120, 80))
    source_image.paste((180, 80, 40), (0, 0, 32, 48))
    source_image.save(source)
    monkeypatch.setattr(
        poster_runner,
        "poster_bundle",
        lambda *_args, **_kwargs: SimpleNamespace(
            manifest={"layout": {"name": layout_name}}
        ),
    )

    resize_artwork_to_dpi("Example", source, destination, 300)

    expected = build_print_layout(layout_name, 300)
    with Image.open(destination) as resized:
        assert resized.size == (expected.width_px, expected.height_px)
        assert resized.info["dpi"] == pytest.approx((300, 300), abs=0.1)


def test_generation_hashes_describe_selected_comfyui_model_files(
    tmp_path: Path,
):
    model = tmp_path / "models" / "diffusion_models" / "matching.safetensors"
    encoder = tmp_path / "models" / "text_encoders" / "encoder.safetensors"
    vae = tmp_path / "models" / "vae" / "vae.safetensors"
    model.parent.mkdir(parents=True)
    encoder.parent.mkdir(parents=True)
    vae.parent.mkdir(parents=True)
    model.write_bytes(b"model")
    encoder.write_bytes(b"encoder")
    vae.write_bytes(b"vae")

    enriched = add_model_artifact_hashes(
        tmp_path,
        {
            "model": "matching.safetensors",
            "encoder": "encoder.safetensors",
            "vae": "vae.safetensors",
        },
    )

    assert enriched["model_sha256"] == sha256_file(model)
    assert enriched["encoder_sha256"] == sha256_file(encoder)
    assert enriched["vae_sha256"] == sha256_file(vae)


def test_identity_lock_provenance_excludes_unused_edit_references(
    tmp_path: Path,
    monkeypatch,
):
    scope_dir = tmp_path / "Example"
    work_dir = scope_dir / "comfyui_poster"
    cutout_dir = scope_dir / "cutouts"
    work_dir.mkdir(parents=True)
    cutout_dir.mkdir()
    (scope_dir / "poster.yaml").write_text("scope: Example\n", encoding="utf-8")
    (cutout_dir / "manifest.json").write_text(
        json.dumps({"items": [{"file": "subject.png"}]}),
        encoding="utf-8",
    )
    Image.new("RGBA", (8, 8), (10, 20, 30, 255)).save(
        cutout_dir / "subject.png"
    )
    Image.new("RGBA", (8, 8), (10, 20, 30, 255)).save(
        work_dir / "inpaint_reference.png"
    )
    Image.new("RGBA", (8, 8), (0, 0, 0, 0)).save(
        work_dir / "upper_context_mask.png"
    )
    Image.new("RGBA", (8, 8), (0, 0, 0, 0)).save(
        work_dir / "upper_context_generation_mask.png"
    )
    Image.new("RGB", (8, 8), (10, 20, 30)).save(
        work_dir / "identity_reference_1.png"
    )
    (work_dir / IDENTITY_LOCK_PROMPT_FILE).write_text(
        "scene",
        encoding="utf-8",
    )
    workflow = work_dir / "workflow.json"
    workflow.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        "scripts.poster_assets.provenance.POSTER_ASSETS",
        tmp_path,
    )

    records = generation_input_records(
        "Example",
        workflow,
        {
            "engine": "flux",
            "mode": "identity_lock",
            "reference_mode": "two_pass_source_pixels",
        },
    )

    assert [record["file"] for record in records["references"]] == [
        "inpaint_reference.png",
        "upper_context_mask.png",
        "upper_context_generation_mask.png",
    ]
    assert records["source_pixel_audit_reference"]["file"] == (
        "inpaint_reference.png"
    )


def test_slice_poster_exports_every_card_without_binder_gaps(tmp_path: Path):
    source = tmp_path / "poster.png"
    layout = build_page_layout("standard_3x3", width_px=848)
    Image.new("RGB", (layout.width_px, layout.height_px), (40, 120, 80)).save(source)

    outputs = slice_poster("Base1", source, tmp_path / "cards")

    assert len(outputs) == 9
    assert [path.name for path in outputs] == [
        f"card_r{row}_c{column}.png"
        for row in range(1, 4)
        for column in range(1, 4)
    ]
    expected_sizes = [
        (
            layout.cell(row, column).width,
            layout.cell(row, column).height,
        )
        for row in range(1, 4)
        for column in range(1, 4)
    ]
    assert [
        Image.open(path).size for path in outputs
    ] == expected_sizes


@pytest.mark.parametrize(
    ("layout_name", "canvas_size"),
    (
        ("wide_4x3", (992, 1008)),
        ("wide_4x4", (848, 1168)),
    ),
)
def test_wide_slicing_uses_every_exact_cell_without_edge_padding(
    tmp_path,
    monkeypatch,
    layout_name,
    canvas_size,
):
    assets = tmp_path / "poster_assets"
    scope_dir = assets / "Example"
    scope_dir.mkdir(parents=True)
    (scope_dir / "poster.yaml").write_text(
        f"scope: Example\nlayout:\n  name: {layout_name}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(poster_slicer, "POSTER_ASSETS", assets)
    layout = build_source_layout(
        layout_name,
        width_px=canvas_size[0],
        height_px=canvas_size[1],
    )
    image = Image.new("RGB", canvas_size, (0, 0, 0))
    expected_colors = []
    for index, (row, column) in enumerate(
        (
            (row, column)
            for row in range(1, layout.rows + 1)
            for column in range(1, layout.columns + 1)
        ),
        start=1,
    ):
        color = (
            (index * 37) % 255 + 1,
            (index * 71) % 255 + 1,
            (index * 109) % 255 + 1,
        )
        expected_colors.append(color)
        cell = layout.cell(row, column)
        tile = Image.new("RGB", (cell.width, cell.height), color)
        image.paste(tile, (cell.x, cell.y))
    source = tmp_path / f"{layout_name}.png"
    image.save(source, format="PNG", dpi=(300, 300))

    outputs = poster_slicer.slice_poster(
        "Example",
        source,
        tmp_path / f"{layout_name}-cards",
    )

    assert len(outputs) == layout.rows * layout.columns
    for index, path in enumerate(outputs):
        row = index // layout.columns + 1
        column = index % layout.columns + 1
        cell = layout.cell(row, column)
        with Image.open(path) as card:
            assert card.size == (cell.width, cell.height)
            assert card.getpixel((0, 0)) == expected_colors[index]
            assert card.getpixel(
                (card.width - 1, card.height - 1)
            ) == expected_colors[index]
            assert card.getbbox() == (0, 0, card.width, card.height)
            assert abs(card.info["dpi"][0] - 300) < 0.1
            assert abs(card.info["dpi"][1] - 300) < 0.1


@pytest.mark.parametrize(
    ("layout_name", "dpi"),
    (
        ("wide_4x3", 299),
        ("wide_4x4", 301),
    ),
)
def test_wide_odd_dpi_slicing_uses_absolute_print_endpoints(
    tmp_path,
    monkeypatch,
    layout_name,
    dpi,
):
    assets = tmp_path / "poster_assets"
    scope_dir = assets / "Example"
    scope_dir.mkdir(parents=True)
    (scope_dir / "poster.yaml").write_text(
        f"scope: Example\nlayout:\n  name: {layout_name}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(poster_slicer, "POSTER_ASSETS", assets)
    layout = build_print_layout(layout_name, dpi)
    image = Image.new(
        "RGB",
        (layout.width_px, layout.height_px),
        (0, 0, 0),
    )
    colors = []
    for index, (row, column) in enumerate(
        (
            (row, column)
            for row in range(1, layout.rows + 1)
            for column in range(1, layout.columns + 1)
        ),
        start=1,
    ):
        color = (
            (index * 31) % 255 + 1,
            (index * 67) % 255 + 1,
            (index * 101) % 255 + 1,
        )
        colors.append(color)
        cell = layout.cell(row, column)
        image.paste(
            Image.new("RGB", (cell.width, cell.height), color),
            (cell.x, cell.y),
        )
    source = tmp_path / f"{layout_name}-{dpi}dpi.png"
    image.save(source, format="PNG", dpi=(dpi, dpi))

    outputs = poster_slicer.slice_poster(
        "Example",
        source,
        tmp_path / f"{layout_name}-{dpi}dpi-cards",
    )

    for index, path in enumerate(outputs):
        row = index // layout.columns + 1
        column = index % layout.columns + 1
        cell = layout.cell(row, column)
        with Image.open(path) as card:
            assert card.size == (cell.width, cell.height)
            assert card.getpixel((0, 0)) == colors[index]
            assert card.getpixel(
                (card.width - 1, card.height - 1)
            ) == colors[index]


def _promotion_fixture(tmp_path: Path, monkeypatch):
    assets_root = tmp_path / "poster_assets"
    scope_dir = assets_root / "Example"
    scope_dir.mkdir(parents=True)
    (scope_dir / "poster.yaml").write_text(
        (
            "scope: Example\n"
            "layout:\n"
            "  name: standard_3x3\n"
            "artwork:\n"
            "  generation:\n"
            "    engine: flux\n"
            "    mode: identity_lock\n"
            "    reference_mode: two_pass_source_pixels\n"
            "    output_method: model_upscale\n"
            "    output_dpi: 300\n"
            "    upscale_model: test-upscaler.pth\n"
            f"    upscale_model_sha256: {'a' * 64}\n"
        ),
        encoding="utf-8",
    )
    layout = build_print_layout("standard_3x3", 10)
    artwork = tmp_path / "candidate.png"
    Image.new(
        "RGB",
        (layout.width_px, layout.height_px),
        (40, 120, 80),
    ).save(artwork)
    run_metadata = tmp_path / "candidate.run.json"
    synthetic_fingerprint = {
        "schema_version": 1,
        "sha256": "synthetic",
        "components": {},
    }
    run_metadata.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "poster_generation_run",
                "scope": "Example",
                "generation": {
                    "engine": "flux",
                    "mode": "identity_lock",
                    "reference_mode": "two_pass_source_pixels",
                    "output_method": "model_upscale",
                    "output_dpi": 300,
                    "upscale_model": "test-upscaler.pth",
                    "upscale_model_sha256": "a" * 64,
                },
                "source_artwork": {"sha256": sha256_file(artwork)},
                "raw_artwork": {
                    "sha256": sha256_file(artwork),
                    "width": layout.width_px,
                    "height": layout.height_px,
                },
                "inputs": {
                    "generation_fingerprint": synthetic_fingerprint,
                    "source_pixel_audit_reference": {
                        "sha256": sha256_file(artwork),
                        "width": layout.width_px,
                        "height": layout.height_px,
                    }
                },
                "validation": {
                    "source_pixels": {
                        "method": "exact_opaque_source_pixels",
                        "opaque_pixels": 1,
                        "changed_pixels": 0,
                        "passed": True,
                        "stage": "raw_generation",
                        "reference_sha256": sha256_file(artwork),
                        "artwork_sha256": sha256_file(artwork),
                        "width": layout.width_px,
                        "height": layout.height_px,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_finalize(_scope, source, destination, _language):
        shutil.copyfile(source, destination)
        return destination

    def fake_slice(_scope, source, output_dir):
        output_dir.mkdir(parents=True)
        image = Image.open(source)
        outputs = []
        for row in range(1, 4):
            for column in range(1, 4):
                path = output_dir / f"card_r{row}_c{column}.png"
                image.crop((0, 0, 32, 32)).save(path)
                outputs.append(path)
        return outputs

    monkeypatch.setattr(poster_promotion, "POSTER_ASSETS", assets_root)
    monkeypatch.setattr(
        poster_promotion,
        "build_generation_output_layout",
        lambda *_args, **_kwargs: layout,
    )
    monkeypatch.setattr(poster_promotion, "finalize", fake_finalize)
    monkeypatch.setattr(poster_promotion, "slice_poster", fake_slice)
    monkeypatch.setattr(
        poster_promotion,
        "fingerprint_record_is_valid",
        lambda record: record == synthetic_fingerprint,
    )
    monkeypatch.setattr(
        poster_promotion,
        "build_generation_fingerprint",
        lambda *_args, **_kwargs: synthetic_fingerprint,
    )
    monkeypatch.setattr(
        poster_promotion,
        "build_overlay_fingerprint",
        lambda *_args, **_kwargs: synthetic_fingerprint,
    )
    return scope_dir, artwork, run_metadata


def test_promotion_installs_complete_bundle_with_stable_provenance(
    tmp_path: Path,
    monkeypatch,
):
    scope_dir, artwork, run_metadata = _promotion_fixture(
        tmp_path,
        monkeypatch,
    )

    promoted, preview, cards, provenance = poster_promotion.promote(
        "Example",
        artwork,
        language="de",
        force=False,
        run_metadata_path=run_metadata,
    )

    assert promoted.is_file()
    assert preview.is_file()
    assert len(cards) == 9 and all(path.is_file() for path in cards)
    payload = json.loads(provenance.read_text(encoding="utf-8"))
    assert payload["scope"] == "Example"
    assert payload["review_language"] == "de"
    assert payload["schema_version"] == 2
    assert payload["storage"] == {
        "schema_version": 1,
        "durable_outputs": ["artwork"],
        "reproducible_sources": "downloaded_to_ignored_workspace",
        "derivatives": "regenerated_in_ignored_workspace",
    }
    assert set(payload["outputs"]) == {"artwork"}
    assert not list(scope_dir.glob(".poster-promotion-*"))


def test_promotion_rejects_generation_metadata_drift(
    tmp_path: Path,
    monkeypatch,
):
    scope_dir, artwork, run_metadata = _promotion_fixture(
        tmp_path,
        monkeypatch,
    )
    payload = json.loads(run_metadata.read_text(encoding="utf-8"))
    payload["generation"] = {"engine": "another-model"}
    run_metadata.write_text(json.dumps(payload), encoding="utf-8")

    try:
        poster_promotion.promote(
            "Example",
            artwork,
            run_metadata_path=run_metadata,
        )
    except ValueError as error:
        assert "Unsupported poster generation contract" in str(error)
    else:
        raise AssertionError("generation metadata drift was accepted")

    assert not (scope_dir / "poster-flux2-artwork.png").exists()
    assert not list(scope_dir.glob(".poster-promotion-*"))


def test_promotion_rejects_failed_source_pixel_audit(
    tmp_path: Path,
    monkeypatch,
):
    scope_dir, artwork, run_metadata = _promotion_fixture(
        tmp_path,
        monkeypatch,
    )
    payload = json.loads(run_metadata.read_text(encoding="utf-8"))
    payload["validation"]["source_pixels"].update(
        changed_pixels=1,
        passed=False,
    )
    run_metadata.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="exact source-pixel validation did not pass",
    ):
        poster_promotion.promote(
            "Example",
            artwork,
            run_metadata_path=run_metadata,
        )

    assert not (scope_dir / "poster-flux2-artwork.png").exists()


def test_new_promotion_rejects_an_unbound_legacy_source_pixel_audit(
    tmp_path: Path,
    monkeypatch,
):
    scope_dir, artwork, run_metadata = _promotion_fixture(
        tmp_path,
        monkeypatch,
    )
    payload = json.loads(run_metadata.read_text(encoding="utf-8"))
    payload["generation"].update(
        engine="flux",
        mode="identity_lock",
        reference_mode="two_pass_source_pixels",
    )
    payload["validation"] = {
        "identity_lock": {
            "method": "exact_opaque_source_pixels",
            "opaque_pixels": 1,
            "changed_pixels": 0,
            "passed": True,
        }
    }
    manifest_path = scope_dir / "poster.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["artwork"]["generation"] = payload["generation"]
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    run_metadata.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="require the bound source-pixel validation record",
    ):
        poster_promotion.promote(
            "Example",
            artwork,
            run_metadata_path=run_metadata,
        )

    assert not (scope_dir / "poster-flux2-artwork.png").exists()


def test_new_run_cannot_gain_legacy_allowances_from_a_promoted_wrapper(
    tmp_path: Path,
    monkeypatch,
):
    scope_dir, artwork, run_metadata = _promotion_fixture(
        tmp_path,
        monkeypatch,
    )
    run = json.loads(run_metadata.read_text(encoding="utf-8"))
    run["generation"].update(engine="flux", mode="identity_lock")
    run["validation"] = {
        "identity_lock": {
            "method": "exact_opaque_source_pixels",
            "opaque_pixels": 1,
            "changed_pixels": 0,
            "passed": True,
        }
    }
    manifest_path = scope_dir / "poster.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["artwork"]["generation"] = run["generation"]
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False),
        encoding="utf-8",
    )
    run_metadata.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "promoted_poster",
                "scope": "Example",
                "run": run,
                "outputs": {
                    "artwork": {
                        "sha256": sha256_file(artwork),
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must use the configured existing provenance",
    ):
        poster_promotion.promote(
            "Example",
            artwork,
            run_metadata_path=run_metadata,
        )

    assert not (scope_dir / "poster-flux2-artwork.png").exists()


def test_legacy_refresh_allowance_binds_to_the_configured_stable_bundle(
    tmp_path: Path,
    monkeypatch,
):
    scope_dir, candidate, _run_metadata = _promotion_fixture(
        tmp_path,
        monkeypatch,
    )
    stable_artwork = scope_dir / "poster-flux2-artwork.png"
    shutil.copyfile(candidate, stable_artwork)
    stable_provenance = scope_dir / "poster-flux2-provenance.json"
    container = {
        "schema_version": 1,
        "kind": "promoted_poster",
        "scope": "Example",
        "outputs": {
            "artwork": {
                "sha256": sha256_file(stable_artwork),
            }
        },
    }
    stable_provenance.write_text(
        json.dumps(container),
        encoding="utf-8",
    )
    manifest = yaml.safe_load(
        (scope_dir / "poster.yaml").read_text(encoding="utf-8")
    )

    assert poster_promotion._is_existing_promotion_refresh(
        scope="Example",
        scope_dir=scope_dir,
        manifest=manifest,
        metadata_path=stable_provenance,
        metadata_container=container,
        artwork_path=stable_artwork,
    )
    assert not poster_promotion._is_existing_promotion_refresh(
        scope="Example",
        scope_dir=scope_dir,
        manifest=manifest,
        metadata_path=tmp_path / "wrapped.json",
        metadata_container=container,
        artwork_path=stable_artwork,
    )


def test_promotion_rejects_a_new_run_without_generation_fingerprint(
    tmp_path: Path,
    monkeypatch,
):
    scope_dir, artwork, run_metadata = _promotion_fixture(
        tmp_path,
        monkeypatch,
    )
    payload = json.loads(run_metadata.read_text(encoding="utf-8"))
    del payload["inputs"]["generation_fingerprint"]
    run_metadata.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="lacks its generation fingerprint",
    ):
        poster_promotion.promote(
            "Example",
            artwork,
            run_metadata_path=run_metadata,
        )

    assert not (scope_dir / "poster-flux2-artwork.png").exists()


def test_failed_promotion_keeps_existing_bundle(
    tmp_path: Path,
    monkeypatch,
):
    scope_dir, artwork, run_metadata = _promotion_fixture(
        tmp_path,
        monkeypatch,
    )
    existing = scope_dir / "poster-flux2-artwork.png"
    Image.new("RGB", (16, 16), (220, 30, 20)).save(existing)
    existing_hash = sha256_file(existing)

    def fail_slice(_scope, _source, _output_dir):
        raise RuntimeError("synthetic crop failure")

    monkeypatch.setattr(poster_promotion, "slice_poster", fail_slice)

    try:
        poster_promotion.promote(
            "Example",
            artwork,
            force=True,
            run_metadata_path=run_metadata,
        )
    except RuntimeError as error:
        assert "synthetic crop failure" in str(error)
    else:
        raise AssertionError("failed promotion unexpectedly succeeded")

    assert sha256_file(existing) == existing_hash
    assert not list(scope_dir.glob(".poster-promotion-*"))


def test_promoted_production_posters_match_provenance_and_print_geometry():
    scopes = enabled_poster_scopes()
    assert scopes

    for scope in scopes:
        bundle = poster_bundle(scope)
        manifest = bundle.manifest
        layout = build_generation_output_layout(
            manifest["layout"]["name"],
            manifest["artwork"]["generation"],
        )
        result = validate_promoted_poster(scope)

        expected_card_sizes = tuple(
            (
                layout.cell(row, column).width,
                layout.cell(row, column).height,
            )
            for row in range(1, layout.rows + 1)
            for column in range(1, layout.columns + 1)
        )
        assert result["dimensions"] == (layout.width_px, layout.height_px)
        assert result["card_dimensions_by_cell"] == expected_card_sizes
        assert result["cards"] == layout.rows * layout.columns


def test_validation_rejects_pdf_artwork_not_named_by_provenance():
    bundle = poster_bundle("ME05")
    mismatched_bundle = replace(
        bundle,
        artwork_file="unreviewed.png",
    )

    with pytest.raises(
        ValueError,
        match="routes PDF artwork.*promoted provenance validates",
    ):
        validate_promoted_poster(mismatched_bundle)


def test_enabled_poster_scopes_only_returns_pdf_enabled_manifests(
    tmp_path: Path,
):
    for scope, enabled in (
        ("EnabledB", True),
        ("Disabled", False),
        ("EnabledA", True),
    ):
        scope_dir = tmp_path / scope
        scope_dir.mkdir()
        (scope_dir / "poster.yaml").write_text(
            f"pdf:\n  enabled: {str(enabled).lower()}\n",
            encoding="utf-8",
        )

    assert enabled_poster_scopes(tmp_path) == ["EnabledA", "EnabledB"]
