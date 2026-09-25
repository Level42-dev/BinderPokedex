import hashlib
import json
from pathlib import Path

import pytest
import yaml
from PIL import Image, ImageDraw, PngImagePlugin

from scripts.poster_assets import poster_work_plan
from scripts.poster_assets.poster_config import build_identity_lock_prompt
from scripts.poster_assets.poster_io import (
    load_poster_scope_data,
    poster_bundles_for_scope,
)
from scripts.poster_assets.provenance import sha256_file
from scripts.poster_assets.poster_subject import PosterSubject
from scripts.poster_assets.validate_promoted_poster import (
    enabled_poster_bundles,
    validate as validate_promoted_poster,
)


LANGUAGES = (
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
GENERATION = {
    "engine": "flux",
    "model": "model.safetensors",
    "model_sha256": "1" * 64,
    "encoder": "encoder.safetensors",
    "encoder_sha256": "2" * 64,
    "vae": "vae.safetensors",
    "vae_sha256": "3" * 64,
    "mode": "identity_lock",
    "reference_mode": "two_pass_source_pixels",
    "seed": 1234,
    "steps": 4,
    "generation_megapixels": 1.0,
    "output_dpi": 300,
    "output_method": "model_upscale",
    "upscale_model": "upscaler.pth",
    "upscale_model_sha256": "4" * 64,
}


def scene(label):
    return {
        "concept": f"{label} concept",
        "setting": f"{label} setting",
        "lighting": f"{label} lighting",
        "rendering": f"{label} rendering",
        "ground_noun": f"{label} ground",
    }


def localized(value):
    return {language: f"{value}-{language}" for language in LANGUAGES}


def source_section(ids, label="Section"):
    return {
        "title": localized(label),
        "subtitle": localized(f"{label} region"),
        "description": localized(f"{label} range"),
        "featured_elements": [
            {"pokemon_id": pokemon_id}
            for pokemon_id in ids
        ],
        "cards": [],
    }


def manifest(
    scope,
    configured_scene,
    *,
    asset_key=None,
    section_id=None,
    enabled=False,
    title_logo=None,
):
    payload = {
        "scope": scope,
        "layout": {"name": "standard_3x3"},
        "text_content": {
            "mode": "section_summary" if section_id else "set_summary"
        },
        "pdf": {
            "enabled": enabled,
            "artwork_file": "poster-flux2-artwork.png",
            "insertion": (
                "after_section_cover"
                if section_id
                else "after_first_section_cover"
            ),
        },
        "artwork": {
            "promoted_file": "poster-flux2-artwork.png",
            "preview_file": "poster-flux2.png",
            "provenance_file": "poster-flux2-provenance.json",
            "scene": configured_scene,
            "generation": dict(GENERATION),
        },
        "pokemon": {
            "strategy": "featured_from_scope",
            "count": "auto_from_layout_columns",
            "cutout_source": "pokeapi_official_artwork",
            "fallback_candidates": [],
        },
    }
    if asset_key:
        payload.update(
            {
                "schema_version": 2,
                "asset_key": asset_key,
                "poster_id": section_id,
                "source": {
                    "scope": scope,
                    "section_id": section_id,
                },
            }
        )
    if title_logo:
        payload["title_logo"] = title_logo
    return payload


def save_yaml(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def test_planner_subject_selection_honors_explicit_poster_slots():
    configured = manifest("Example", scene("Example"))
    configured["pokemon"]["fallback_candidates"] = [
        {"pokemon_id": 25, "slot": 3},
    ]
    source = {"sections": {"all": source_section([250, 909, 646])}}

    subjects, _layout = poster_work_plan._expected_subject_identities(
        configured, source,
    )

    assert [subject[1] for subject in subjects] == [250, 909, 25]

    configured["pokemon"]["fallback_candidates"][0]["slot"] = 4
    with pytest.raises(ValueError, match="slot must be between"):
        poster_work_plan._expected_subject_identities(configured, source)


def save_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def make_cutout(path, color):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((60, 40, 340, 360), fill=(*color, 255))
    image.save(path)
    return poster_work_plan.validate_png(path)


def write_cutouts(asset_dir, asset_key, source_scope, poster_id, section_id, ids):
    items = []
    for index, pokemon_id in enumerate(ids):
        filename = f"pokemon_{pokemon_id:03d}.png"
        validation = make_cutout(
            asset_dir / "cutouts" / filename,
            (40 + index * 40, 100, 160),
        )
        items.append(
            {
                "pokemon_id": pokemon_id,
                "url": (
                    "https://raw.githubusercontent.com/PokeAPI/sprites/master/"
                    "sprites/pokemon/other/official-artwork/"
                    f"{pokemon_id}.png"
                ),
                "file": filename,
                "validated_alpha": True,
                "errors": [],
                **validation,
            }
        )
    payload = {
        "scope": asset_key,
        "source_scope": source_scope,
        "poster_id": poster_id,
        "section_id": section_id,
        "source": "pokeapi_official_artwork",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "layout": {
            "name": "standard_3x3",
            "columns": 3,
            "rows": 3,
        },
        "items": items,
    }
    save_json(asset_dir / "cutouts" / "manifest.json", payload)
    return payload


def write_scene_catalog(path, *, scopes=None, section_scopes=None):
    save_yaml(
        path,
        {
            "version": 1,
            "scopes": scopes or {"CatalogPlaceholder": scene("placeholder")},
            "section_scopes": section_scopes or {},
        },
    )


def setup_individual(tmp_path, *, enabled=False, title_logo=None):
    assets = tmp_path / "assets"
    output = tmp_path / "output"
    catalog = tmp_path / "scenes.yaml"
    configured_scene = scene("alpha")
    scope_data = {
        "type": "tcg_set",
        "name": "Alpha",
        "release_date": "2020-01-02",
        "logo_urls": {"en": "https://example.invalid/logo.png"},
        "sections": {"main": source_section([1, 2, 3])},
    }
    save_json(output / "Alpha.json", scope_data)
    save_yaml(
        assets / "Alpha" / "poster.yaml",
        manifest(
            "Alpha",
            configured_scene,
            enabled=enabled,
            title_logo=title_logo,
        ),
    )
    write_cutouts(
        assets / "Alpha",
        "Alpha",
        "Alpha",
        "Alpha",
        None,
        [1, 2, 3],
    )
    write_scene_catalog(catalog, scopes={"Alpha": configured_scene})
    return assets, output, catalog


def setup_aggregate(tmp_path):
    assets = tmp_path / "assets"
    output = tmp_path / "output"
    catalog = tmp_path / "scenes.yaml"
    sections = {
        "one": source_section([1, 2, 3], "One"),
        "two": source_section([4, 5, 6], "Two"),
    }
    save_json(output / "Root.json", {"sections": sections})
    scenes = {"one": scene("one"), "two": scene("two")}
    entries = []
    for section_id, ids, enabled in (
        ("one", [1, 2, 3], True),
        ("two", [4, 5, 6], False),
    ):
        asset_key = f"Root/sections/{section_id}"
        asset_dir = assets / asset_key
        save_yaml(
            asset_dir / "poster.yaml",
            manifest(
                "Root",
                scenes[section_id],
                asset_key=asset_key,
                section_id=section_id,
            ),
        )
        write_cutouts(
            asset_dir,
            asset_key,
            "Root",
            section_id,
            section_id,
            ids,
        )
        entries.append(
            {
                "id": section_id,
                "section_id": section_id,
                "manifest": f"sections/{section_id}/poster.yaml",
                "pdf": {
                    "enabled": enabled,
                    "artwork_file": "poster-flux2-artwork.png",
                    "insertion": "after_section_cover",
                },
            }
        )
    save_yaml(
        assets / "Root" / "posters.yaml",
        {"schema_version": 1, "scope": "Root", "posters": entries},
    )
    write_scene_catalog(catalog, section_scopes={"Root": scenes})
    return assets, output, catalog


def write_promotion(
    bundle,
    scope_data_dir,
    *,
    fingerprints=True,
    pipeline_contract_version=None,
):
    scope_data = load_poster_scope_data(
        bundle,
        scope_data_dir=scope_data_dir,
    )
    cutout_payload = json.loads(
        (bundle.asset_dir / "cutouts" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    cutout_records = []
    for item in cutout_payload["items"]:
        path = bundle.asset_dir / "cutouts" / item["file"]
        cutout_records.append(
            {
                "file": f"fixture/{bundle.asset_key}/cutouts/{path.name}",
                "sha256": sha256_file(path),
            }
        )
    generation = bundle.manifest["artwork"]["generation"]
    if (
        generation.get("engine") == "flux"
        and generation.get("mode") == "identity_lock"
    ):
        prompt = (
            build_identity_lock_prompt(bundle.manifest, scope_data) + "\n"
        ).encode("utf-8")
    else:
        prompt = poster_work_plan.prompt_path_for_generation(
            bundle.asset_dir / "comfyui_poster",
            generation,
        ).read_bytes()
    inputs = {
        "scope_manifest": {
            "sha256": sha256_file(bundle.manifest_path)
        },
        "prompt": {"sha256": hashlib.sha256(prompt).hexdigest()},
        "cutout_manifest": {
            "sha256": sha256_file(
                bundle.asset_dir / "cutouts" / "manifest.json"
            )
        },
        "cutouts": cutout_records,
    }
    if fingerprints:
        inputs["generation_fingerprint"] = (
            poster_work_plan.build_generation_fingerprint(
                bundle,
                scope_data_dir=scope_data_dir,
                pipeline_contract_version=pipeline_contract_version,
            )
        )
        inputs["overlay_fingerprint"] = (
            poster_work_plan.build_overlay_fingerprint(
                bundle,
                scope_data_dir=scope_data_dir,
            )
        )
    provenance = {
        "schema_version": 1,
        "kind": "promoted_poster",
        "scope": bundle.asset_key,
        "source_scope": bundle.scope,
        "poster_id": bundle.poster_id,
        "section_id": bundle.section_id,
        "run": {
            "generation": bundle.manifest["artwork"]["generation"],
            "inputs": inputs,
        },
    }
    Image.new("RGB", (32, 32), "navy").save(
        bundle.asset_dir / "poster-flux2-artwork.png"
    )
    Image.new("RGB", (32, 32), "navy").save(
        bundle.asset_dir / "poster-flux2.png"
    )
    save_json(
        bundle.asset_dir / "poster-flux2-provenance.json",
        provenance,
    )


def build(scope, assets, output, catalog, validator=lambda _bundle: {}):
    return poster_work_plan.build_work_plan(
        scope=scope,
        poster_assets=assets,
        scope_data_dir=output,
        scene_catalog_path=catalog,
        promotion_validator=validator,
    )


def target(plan, index=0):
    return plan["targets"][index]


def file_snapshot(root):
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_unconfigured_scope_has_stable_initialization_plan(tmp_path):
    output = tmp_path / "output"
    save_json(
        output / "Missing.json",
        {"type": "tcg_set", "sections": {"main": {}}},
    )

    plan = build(
        "Missing",
        tmp_path / "assets",
        output,
        tmp_path / "missing-catalog.yaml",
    )

    assert target(plan) == {
        "asset_key": "Missing",
        "source_scope": "Missing",
        "poster_id": None,
        "section_id": None,
        "pdf_enabled": None,
        "state": "unconfigured",
        "reason_codes": ["poster_not_configured"],
        "next_actions": ["initialize_poster"],
        "commands": [
            "python scripts/poster_assets/init_poster_scope.py "
            "--scope Missing --fetch"
        ],
    }


def test_unconfigured_nested_leaf_initializes_aggregate_root_not_leaf(tmp_path):
    output = tmp_path / "output"
    save_json(
        output / "Root.json",
        {"sections": {"one": source_section([1, 2, 3])}},
    )

    plan = build(
        "Root/sections/one",
        tmp_path / "assets",
        output,
        tmp_path / "missing-catalog.yaml",
    )

    assert target(plan)["state"] == "unconfigured"
    assert target(plan)["next_actions"] == [
        "initialize_aggregate_posters"
    ]
    assert target(plan)["commands"] == [
        "python scripts/poster_assets/init_poster_scope.py "
        "--scope Root --all-sections --fetch"
    ]


def test_unconfigured_scope_without_source_data_plans_fetch_first(tmp_path):
    plan = build(
        "Missing",
        tmp_path / "assets",
        tmp_path / "output",
        tmp_path / "missing-catalog.yaml",
    )

    assert target(plan)["state"] == "unconfigured"
    assert target(plan)["reason_codes"] == [
        "poster_not_configured",
        "scope_data_missing_or_invalid",
    ]
    assert target(plan)["next_actions"] == [
        "fetch_scope_data",
        "initialize_poster",
    ]
    assert target(plan)["commands"][0].endswith("--scope Missing")


def test_ready_to_generate_requires_valid_config_source_scene_and_assets(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "ready_to_generate"
    assert target(plan)["reason_codes"] == ["promotion_missing"]
    assert target(plan)["next_actions"] == ["generate_candidate"]
    assert "--scope Alpha" in target(plan)["commands"][0]


def test_scene_catalog_is_required_subset_and_allows_reviewed_overrides(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)
    manifest_path = assets / "Alpha" / "poster.yaml"
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["artwork"]["scene"]["safe_areas"] = (
        "Keep the reviewed legacy title region open."
    )
    save_yaml(manifest_path, payload)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "ready_to_generate"
    assert "scene_catalog_drift" not in target(plan)["reason_codes"]






def test_removed_engine_contract_is_blocked(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)
    manifest_path = assets / "Alpha" / "poster.yaml"
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    payload["artwork"]["generation"].update(
        {"engine": "anima", "mode": "edit", "reference_mode": "cosmos"}
    )
    save_yaml(manifest_path, payload)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "blocked"
    assert "Unsupported poster generation contract" in target(plan)["detail"]


def test_nested_leaf_uses_root_pdf_routing_and_root_keeps_index_order(tmp_path):
    assets, output, catalog = setup_aggregate(tmp_path)
    bundles = poster_bundles_for_scope("Root", poster_assets=assets)
    for bundle in bundles:
        write_promotion(bundle, output)

    leaf_plan = build("Root/sections/one", assets, output, catalog)
    root_plan = build("Root", assets, output, catalog)

    assert [item["asset_key"] for item in leaf_plan["targets"]] == [
        "Root/sections/one"
    ]
    assert target(leaf_plan)["pdf_enabled"] is True
    assert target(leaf_plan)["state"] == "current"
    assert [item["asset_key"] for item in root_plan["targets"]] == [
        "Root/sections/one",
        "Root/sections/two",
    ]
    assert [item["state"] for item in root_plan["targets"]] == [
        "current",
        "promoted_disabled",
    ]


def test_all_configured_is_sorted_and_ignores_unconfigured_directories(tmp_path):
    assets, output, catalog = setup_aggregate(tmp_path)
    alpha_assets, alpha_output, alpha_catalog = setup_individual(
        tmp_path / "alpha"
    )
    (assets / "Alpha").mkdir()
    (assets / "Alpha" / "poster.yaml").write_bytes(
        (alpha_assets / "Alpha" / "poster.yaml").read_bytes()
    )
    for path in (alpha_assets / "Alpha" / "cutouts").iterdir():
        destination = assets / "Alpha" / "cutouts" / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    (output / "Alpha.json").write_bytes(
        (alpha_output / "Alpha.json").read_bytes()
    )
    merged_catalog = yaml.safe_load(catalog.read_text(encoding="utf-8"))
    merged_catalog["scopes"]["Alpha"] = yaml.safe_load(
        alpha_catalog.read_text(encoding="utf-8")
    )["scopes"]["Alpha"]
    save_yaml(catalog, merged_catalog)
    (assets / "ZZ-junk").mkdir()

    plan = poster_work_plan.build_work_plan(
        all_configured=True,
        poster_assets=assets,
        scope_data_dir=output,
        scene_catalog_path=catalog,
        promotion_validator=lambda _bundle: {},
    )

    assert [item["asset_key"] for item in plan["targets"]] == [
        "Alpha",
        "Root/sections/one",
        "Root/sections/two",
    ]
    assert plan["summary"] == {
        "targets": 3,
        "states": {"ready_to_generate": 3},
    }


@pytest.mark.parametrize(
    ("mutation", "reason", "action"),
    [
        ("remove_cutout", "cutout_file_missing", "fetch_cutouts"),
        ("corrupt_cutout", "cutout_file_invalid", "fetch_cutouts"),
        ("reorder_cutouts", "cutout_selection_stale", "fetch_cutouts"),
        ("missing_logo", "title_logo_missing", "fetch_title_logos"),
        ("corrupt_logo", "title_logo_invalid", "fetch_title_logos"),
    ],
)
def test_missing_or_invalid_local_assets_have_needs_assets_state(
    tmp_path,
    mutation,
    reason,
    action,
):
    title_logo = (
        {"file": "logo.png"}
        if mutation in {"missing_logo", "corrupt_logo"}
        else None
    )
    assets, output, catalog = setup_individual(
        tmp_path,
        title_logo=title_logo,
    )
    first = assets / "Alpha" / "cutouts" / "pokemon_001.png"
    if mutation == "remove_cutout":
        first.unlink()
    elif mutation == "corrupt_cutout":
        first.write_text("not a PNG", encoding="utf-8")
    elif mutation == "reorder_cutouts":
        manifest_path = assets / "Alpha" / "cutouts" / "manifest.json"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload["items"][0], payload["items"][1] = (
            payload["items"][1],
            payload["items"][0],
        )
        save_json(manifest_path, payload)
    elif mutation == "corrupt_logo":
        (assets / "Alpha" / "logo.png").write_text(
            "not a PNG",
            encoding="utf-8",
        )

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "needs_assets"
    assert reason in target(plan)["reason_codes"]
    assert action in target(plan)["next_actions"]


def test_form_change_with_same_species_marks_cutout_selection_stale(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)
    source_path = output / "Alpha.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["sections"]["main"]["featured_elements"][0] = {
        "pokemon_id": 6,
        "poster_subject": PosterSubject(6, 10034).as_mapping(),
    }
    save_json(source_path, source)
    manifest_path = assets / "Alpha" / "cutouts" / "manifest.json"
    cutouts = json.loads(manifest_path.read_text(encoding="utf-8"))
    cutouts["items"][0]["pokemon_id"] = 6
    cutouts["items"][0]["url"] = PosterSubject(6, 6).image_url
    save_json(manifest_path, cutouts)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "needs_assets"
    assert "cutout_selection_stale" in target(plan)["reason_codes"]
    assert "fetch_cutouts" in target(plan)["next_actions"]


def test_source_or_routing_inconsistency_blocks_a_safe_plan(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)
    (output / "Alpha.json").unlink()

    source_plan = build("Alpha", assets, output, catalog)

    assert target(source_plan)["state"] == "blocked"
    assert target(source_plan)["reason_codes"] == [
        "configuration_or_source_invalid"
    ]

    root = assets / "Broken"
    root.mkdir()
    save_yaml(root / "poster.yaml", {"scope": "Broken"})
    save_yaml(
        root / "posters.yaml",
        {"schema_version": 1, "scope": "Broken", "posters": []},
    )
    routing_plan = build("Broken", assets, output, catalog)
    assert target(routing_plan)["state"] == "blocked"
    assert target(routing_plan)["reason_codes"] == ["routing_invalid"]


def test_scene_catalog_drift_blocks_generation_or_stales_a_promotion(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)
    changed = yaml.safe_load(catalog.read_text(encoding="utf-8"))
    changed["scopes"]["Alpha"] = scene("changed")
    save_yaml(catalog, changed)

    before_promotion = build("Alpha", assets, output, catalog)
    assert target(before_promotion)["state"] == "blocked"
    assert target(before_promotion)["reason_codes"] == ["scene_catalog_drift"]

    bundle = poster_bundles_for_scope(
        "Alpha",
        poster_assets=assets,
    )[0]
    write_promotion(bundle, output)
    after_promotion = build("Alpha", assets, output, catalog)
    assert target(after_promotion)["state"] == "promotion_stale"
    assert target(after_promotion)["reason_codes"] == ["scene_catalog_drift"]


def test_generation_or_manifest_input_drift_stales_existing_promotion(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)
    bundle = poster_bundles_for_scope("Alpha", poster_assets=assets)[0]
    write_promotion(bundle, output)
    payload = yaml.safe_load(bundle.manifest_path.read_text(encoding="utf-8"))
    payload["artwork"]["generation"]["steps"] = 5
    save_yaml(bundle.manifest_path, payload)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "promotion_stale"
    assert target(plan)["reason_codes"] == [
        "generation_contract_drift",
        "generation_fingerprint_drift",
    ]


def test_generation_fingerprint_catches_non_prompt_conditioning_drift(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)
    bundle = poster_bundles_for_scope("Alpha", poster_assets=assets)[0]
    write_promotion(bundle, output)
    payload = yaml.safe_load(bundle.manifest_path.read_text(encoding="utf-8"))
    payload["conditioning"] = {
        "identity_defaults": {"canvas_px": 768}
    }
    save_yaml(bundle.manifest_path, payload)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "promotion_stale"
    assert target(plan)["reason_codes"] == [
        "generation_fingerprint_drift"
    ]
    assert "regenerate_candidate" in target(plan)["next_actions"]


def test_pdf_routing_change_does_not_regenerate_fingerprinted_artwork(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)
    bundle = poster_bundles_for_scope("Alpha", poster_assets=assets)[0]
    write_promotion(bundle, output)
    payload = yaml.safe_load(bundle.manifest_path.read_text(encoding="utf-8"))
    payload["pdf"]["enabled"] = True
    save_yaml(bundle.manifest_path, payload)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "current"
    assert target(plan)["reason_codes"] == [
        "promotion_current",
        "pdf_enabled",
    ]
    assert target(plan)["next_actions"] == []
    assert target(plan)["commands"] == []


def test_accepted_legacy_pipeline_is_current_with_optional_upgrade(tmp_path):
    assets, output, catalog = setup_individual(tmp_path, enabled=True)
    bundle = poster_bundles_for_scope("Alpha", poster_assets=assets)[0]
    write_promotion(
        bundle,
        output,
        pipeline_contract_version=1,
    )

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "current"
    assert target(plan)["reason_codes"] == [
        "promotion_current",
        "pdf_enabled",
        "accepted_legacy_pipeline",
    ]
    assert target(plan)["next_actions"] == [
        "upgrade_generation_pipeline"
    ]
    assert target(plan)["commands"] == []

    payload = yaml.safe_load(bundle.manifest_path.read_text(encoding="utf-8"))
    payload["conditioning"] = {
        "identity_defaults": {"canvas_px": 768}
    }
    save_yaml(bundle.manifest_path, payload)
    stale = build("Alpha", assets, output, catalog)
    assert target(stale)["state"] == "promotion_stale"
    assert "generation_fingerprint_drift" in target(stale)["reason_codes"]


def test_overlay_only_change_requests_refresh_without_regeneration(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)
    bundle = poster_bundles_for_scope("Alpha", poster_assets=assets)[0]
    write_promotion(bundle, output)
    payload = yaml.safe_load(bundle.manifest_path.read_text(encoding="utf-8"))
    payload["text_cells"] = {
        "set_info": {
            "row": 2,
            "column": 2,
            "max_width_ratio": 0.8,
        },
    }
    save_yaml(bundle.manifest_path, payload)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "promoted_disabled"
    assert target(plan)["reason_codes"] == [
        "promotion_current",
        "pdf_disabled",
        "overlay_fingerprint_drift",
    ]
    assert target(plan)["next_actions"] == [
        "refresh_promoted_overlay",
        "enable_pdf_after_review",
    ]
    assert "regenerate_candidate" not in target(plan)["next_actions"]
    assert target(plan)["commands"] == []




def test_legacy_manifest_drift_is_not_misclassified_as_safe_migration(
    tmp_path,
):
    assets, output, catalog = setup_individual(tmp_path)
    bundle = poster_bundles_for_scope("Alpha", poster_assets=assets)[0]
    write_promotion(bundle, output, fingerprints=False)
    payload = yaml.safe_load(bundle.manifest_path.read_text(encoding="utf-8"))
    payload["pdf"]["enabled"] = True
    save_yaml(bundle.manifest_path, payload)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "invalid"
    assert target(plan)["reason_codes"] == [
        "promotion_invalid",
        "legacy_manifest_drift_unclassifiable",
    ]
    assert target(plan)["next_actions"] == [
        "repair_or_repromote"
    ]
    assert target(plan)["commands"] == []


def test_legacy_overlay_without_fingerprint_requests_only_overlay_refresh(
    tmp_path,
):
    assets, output, catalog = setup_individual(tmp_path, enabled=True)
    bundle = poster_bundles_for_scope("Alpha", poster_assets=assets)[0]
    write_promotion(bundle, output, fingerprints=False)
    source_path = output / "Alpha.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source["release_date"] = "2021-02-03"
    save_json(source_path, source)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "current"
    assert "overlay_fingerprint_required" in target(plan)["reason_codes"]
    assert target(plan)["next_actions"] == ["refresh_promoted_overlay"]
    assert target(plan)["commands"] == []


@pytest.mark.parametrize(
    ("failure", "expected_state", "expected_reason"),
    [
        (
            ValueError("Wrong dpi metadata"),
            "invalid",
            "promotion_validation_failed",
        ),
        (
            ValueError("Generation metadata drift"),
            "promotion_stale",
            "validator_input_drift",
        ),
    ],
)
def test_validator_distinguishes_corruption_from_unclassified_input_drift(
    tmp_path,
    failure,
    expected_state,
    expected_reason,
):
    assets, output, catalog = setup_individual(tmp_path)
    bundle = poster_bundles_for_scope("Alpha", poster_assets=assets)[0]
    write_promotion(bundle, output)

    def failing_validator(_bundle):
        raise failure

    plan = build("Alpha", assets, output, catalog, failing_validator)

    assert target(plan)["state"] == expected_state
    assert expected_reason in target(plan)["reason_codes"]


def test_invalid_or_partial_promotion_uses_stable_invalid_state(tmp_path):
    assets, output, catalog = setup_individual(tmp_path)
    scope_dir = assets / "Alpha"
    (scope_dir / "poster-flux2-artwork.png").write_bytes(b"partial")

    partial = build("Alpha", assets, output, catalog)
    assert target(partial)["state"] == "invalid"
    assert target(partial)["reason_codes"] == [
        "promotion_invalid",
        "provenance_missing",
    ]

    (scope_dir / "poster-flux2-provenance.json").write_text(
        "{ broken",
        encoding="utf-8",
    )
    corrupt = build("Alpha", assets, output, catalog)
    assert target(corrupt)["state"] == "invalid"
    assert target(corrupt)["reason_codes"] == [
        "promotion_invalid",
        "provenance_invalid",
    ]


def test_cutout_generated_at_is_ignored_and_planning_does_not_write(tmp_path):
    assets, output, catalog = setup_individual(tmp_path, enabled=True)
    bundle = poster_bundles_for_scope("Alpha", poster_assets=assets)[0]
    write_promotion(bundle, output)
    cutout_manifest = bundle.asset_dir / "cutouts" / "manifest.json"
    payload = json.loads(cutout_manifest.read_text(encoding="utf-8"))
    payload["generated_at"] = "2099-12-31T23:59:59+00:00"
    save_json(cutout_manifest, payload)
    before = file_snapshot(tmp_path)

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "current"
    assert target(plan)["reason_codes"] == [
        "promotion_current",
        "pdf_enabled",
    ]
    assert file_snapshot(tmp_path) == before


def test_fingerprinted_cutout_png_reencoding_does_not_stale_pixels(tmp_path):
    assets, output, catalog = setup_individual(tmp_path, enabled=True)
    bundle = poster_bundles_for_scope("Alpha", poster_assets=assets)[0]
    write_promotion(bundle, output)
    cutout = bundle.asset_dir / "cutouts" / "pokemon_001.png"
    before = sha256_file(cutout)
    with Image.open(cutout) as loaded:
        pixels = loaded.convert("RGBA")
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("operational-note", "same decoded source pixels")
    pixels.save(cutout, pnginfo=metadata, compress_level=9)
    assert sha256_file(cutout) != before

    plan = build("Alpha", assets, output, catalog)

    assert target(plan)["state"] == "current"
    assert "cutout_hash_drift" not in target(plan)["reason_codes"]
    assert "generation_fingerprint_drift" not in target(plan)["reason_codes"]


def test_json_and_text_renderers_expose_stable_codes(monkeypatch, capsys):
    plan = {
        "schema_version": 1,
        "mode": "scope",
        "requested_scope": "Alpha",
        "summary": {
            "targets": 1,
            "states": {"ready_to_generate": 1},
        },
        "targets": [
            {
                "asset_key": "Alpha",
                "source_scope": "Alpha",
                "poster_id": "Alpha",
                "section_id": None,
                "pdf_enabled": False,
                "state": "ready_to_generate",
                "reason_codes": ["promotion_missing"],
                "next_actions": ["generate_candidate"],
                "commands": [],
            }
        ],
    }
    monkeypatch.setattr(
        poster_work_plan,
        "build_work_plan",
        lambda **_kwargs: plan,
    )

    assert poster_work_plan.main(["--scope", "Alpha", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == plan

    assert poster_work_plan.main(["--scope", "Alpha"]) == 0
    text = capsys.readouterr().out
    assert "ready_to_generate" in text
    assert "promotion_missing -> generate_candidate" in text
    assert "1 target(s): ready_to_generate=1" in text


def test_public_state_vocabulary_is_stable():
    assert poster_work_plan.STATES == (
        "unconfigured",
        "needs_assets",
        "ready_to_generate",
        "promotion_stale",
        "invalid",
        "promoted_disabled",
        "current",
        "blocked",
    )


def test_every_release_enabled_poster_passes_production_validation():
    bundles = enabled_poster_bundles()
    accepted = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "docs/reviews/2026-09-23-panorama-batch-user-acceptance.json"
        ).read_text(encoding="utf-8")
    )
    assert {
        bundle.asset_key for bundle in bundles
    } == {
        "ExGen2/sections/mega",
        "ExGen3/sections/normal",
        "ME05",
        "Pokedex/sections/gen1",
        "Pokedex/sections/gen3",
        "Pokedex/sections/gen7",
        "SV08",
    } | {candidate["scope"] for candidate in accepted["candidates"]}

    for bundle in bundles:
        result = validate_promoted_poster(bundle)
        assert result["cards"] == 9, bundle.asset_key
