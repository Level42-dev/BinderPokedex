import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from PIL import Image, ImageChops

from scripts.poster_assets.finalize_comfyui_poster import (
    SUPPORTED_LANGUAGES,
    canonical_overlay_text,
    finalize,
    info_panel_values,
    inline_title_logo,
    readable_overlay_text,
    resolved_title_text,
    title_logo_file,
)
from scripts.poster_assets.fetch_title_logos import resolve_logo_downloads
from scripts.poster_assets.typography import load_font, wrap_text
from scripts.poster_assets.init_poster_scope import (
    build_section_manifest,
)
from scripts.poster_assets.poster_io import (
    POSTER_CONFIGS,
    load_poster_scope_data,
    poster_bundle,
    poster_bundles_for_scope,
)
from scripts.poster_assets.poster_config import build_identity_lock_prompt
from scripts.poster_assets.provenance import sha256_file
from scripts.poster_assets.scene_catalog import section_scenes_for_scope
from scripts.poster_assets.validate_promoted_poster import enabled_poster_scopes


ROOT = Path(__file__).resolve().parents[2]


def test_me05_has_an_enabled_poster_target():
    manifest_path = ROOT / "config" / "posters" / "ME05" / "poster.yaml"

    assert manifest_path.is_file()
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["scope"] == "ME05"
    assert manifest["pdf"]["enabled"] is True


def test_sv07_rejects_the_known_three_ear_candidate_seed():
    manifest_path = ROOT / "config" / "posters" / "SV07" / "poster.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    assert manifest["artwork"]["generation"]["seed"] != 260726008
POSTER_CONFIG_ROOT = POSTER_CONFIGS


def test_every_current_poster_target_has_a_checked_in_manifest():
    manifests = list(POSTER_CONFIG_ROOT.glob("*/poster.yaml"))
    manifests.extend(POSTER_CONFIG_ROOT.glob("*/sections/*/poster.yaml"))

    assert len(manifests) == 42


def test_poster_storage_classes_are_separate_and_complete():
    bundles = [
        bundle
        for scope in sorted(
            path.name
            for path in POSTER_CONFIG_ROOT.iterdir()
            if path.is_dir()
        )
        for bundle in poster_bundles_for_scope(scope)
    ]

    assert len(bundles) == 42
    assert all(
        bundle.config_dir.is_relative_to(POSTER_CONFIG_ROOT)
        for bundle in bundles
    )
    assert all(
        bundle.asset_dir.is_relative_to(ROOT / "assets" / "posters")
        for bundle in bundles
    )
    assert all(
        bundle.work_dir.is_relative_to(ROOT / "tmp" / "poster-workspaces")
        for bundle in bundles
    )
    assert all(
        bundle.source_dir.is_relative_to(
            ROOT / "tmp" / "poster-workspaces"
        )
        for bundle in bundles
    )
    assert not (ROOT / "data" / "poster_assets").exists()
    assert not list((ROOT / "assets" / "posters").rglob("poster-flux2.png"))
    assert not list(
        (ROOT / "assets" / "posters").rglob(
            "poster-flux2-cards/card_r*_c*.png"
        )
    )
    assert not list((ROOT / "assets" / "posters").rglob("cutouts/*"))
    assert not list((ROOT / "assets" / "posters").rglob("logos/*"))
    assert not list((ROOT / "assets" / "posters").rglob("logo.png"))


@pytest.mark.parametrize(
    ("scope", "expected_ids"),
    [
        ("Base3", [141, 131, 94]),
        ("SV07", [1, 7, 813]),
    ],
)
def test_curated_posters_use_three_card_safe_subjects(scope, expected_ids):
    bundle = poster_bundle(scope)
    source = load_poster_scope_data(bundle)
    featured = source["sections"]["all"]["featured_elements"]
    provenance = json.loads(
        (
            bundle.asset_dir / "poster-flux2-provenance.json"
        ).read_text(
            encoding="utf-8"
        )
    )
    approved_subjects = (
        provenance["run"]["inputs"]["generation_fingerprint"]
        ["components"]["source_subject_ids"]
    )

    assert [item["pokemon_id"] for item in featured] == expected_ids
    assert [
        item if isinstance(item, int) else item["pokemon_id"]
        for item in approved_subjects
    ] == expected_ids


def test_every_generated_pdf_language_has_complete_poster_copy():
    checked = []
    configured_scopes = {
        path.parent.name
        for pattern in ("*/poster.yaml", "*/posters.yaml")
        for path in POSTER_CONFIG_ROOT.glob(pattern)
    }
    for scope in sorted(configured_scopes):
        for bundle in poster_bundles_for_scope(scope):
            scope_data = load_poster_scope_data(bundle)
            languages = scope_data.get(
                "available_languages",
                SUPPORTED_LANGUAGES,
            )
            content_mode = bundle.manifest.get("text_content", {}).get(
                "mode",
                "set_summary",
            )
            for language in languages:
                logo_file = title_logo_file(bundle.manifest, language)
                if logo_file:
                    downloads = {
                        relative_file: url
                        for _logo_language, relative_file, url in (
                            resolve_logo_downloads(
                                bundle.manifest,
                                scope_data,
                            )
                        )
                    }
                    assert downloads.get(logo_file)
                    header_text = None
                else:
                    header_text = resolved_title_text(scope_data, language)
                    assert readable_overlay_text(header_text).strip()

                complete_values = info_panel_values(
                    scope_data,
                    language,
                    content_mode,
                )
                visible_values = info_panel_values(
                    scope_data,
                    language,
                    content_mode,
                    header_text=header_text,
                )
                assert all(visible_values)

                visible_texts = list(visible_values)
                if header_text is not None:
                    visible_texts.insert(0, readable_overlay_text(header_text))
                for expected in complete_values:
                    assert sum(
                        canonical_overlay_text(value)
                        == canonical_overlay_text(expected)
                        for value in visible_texts
                    ) == 1
                checked.append(f"{bundle.asset_key}/{language}")

    assert len(checked) == 267


def test_standalone_poster_manifests_remain_isolated_single_bundles():
    expected_hashes = {
        "Base1": "30fe44df5f2e99596d9b80a879371ed7549299a9e7e192e26f6cb066f94cf36b",
        "SV03.5": "30fcaeaa7b80f2cc5709461afc7f9178451940e0c8b911bedacbae8c030d2173",
    }

    for scope, expected_hash in expected_hashes.items():
        bundles = poster_bundles_for_scope(scope)
        assert len(bundles) == 1
        assert bundles[0].asset_key == scope
        assert bundles[0].section_id is None
        assert bundles[0].insertion == "after_first_section_cover"
        assert sha256_file(bundles[0].manifest_path) == expected_hash


def test_pokedex_index_routes_all_nine_enabled_section_bundles():
    expected_starters = {
        "gen1": [1, 4, 7],
        "gen2": [152, 155, 158],
        "gen3": [252, 255, 258],
        "gen4": [387, 390, 393],
        "gen5": [495, 498, 501],
        "gen6": [650, 653, 656],
        "gen7": [722, 725, 728],
        "gen8": [810, 813, 816],
        "gen9": [906, 909, 912],
    }

    bundles = poster_bundles_for_scope("Pokedex")

    assert [bundle.poster_id for bundle in bundles] == list(expected_starters)
    assert len({bundle.manifest_path for bundle in bundles}) == 9
    assert [
        bundle.poster_id for bundle in bundles if bundle.pdf_enabled
    ] == [
        "gen1",
        "gen2",
        "gen3",
        "gen4",
        "gen5",
        "gen6",
        "gen7",
        "gen8",
        "gen9",
    ]
    assert [
        bundle.poster_id for bundle in bundles if not bundle.pdf_enabled
    ] == []
    assert all(bundle.insertion == "after_section_cover" for bundle in bundles)
    assert len(
        {
            bundle.manifest["artwork"]["generation"]["seed"]
            for bundle in bundles
        }
    ) == 9
    for bundle in bundles:
        selected = load_poster_scope_data(bundle)
        assert list(selected["sections"]) == [bundle.section_id]
        section = selected["sections"][bundle.section_id]
        assert [
            item["pokemon_id"]
            for item in section["featured_elements"]
        ] == expected_starters[bundle.section_id]


def test_pokedex_leaf_scenes_match_the_reviewed_section_catalog():
    scenes = section_scenes_for_scope("Pokedex")

    for bundle in poster_bundles_for_scope("Pokedex"):
        assert bundle.manifest["artwork"]["scene"] == scenes[bundle.section_id]
        prompt_opening = build_identity_lock_prompt(
            bundle.manifest,
            load_poster_scope_data(bundle),
        ).split("\n\n", 1)[0].lower()
        assert "pokédex" not in prompt_opening
        assert "pokedex" not in prompt_opening
        assert "pokémon" not in prompt_opening
        assert "pokemon" not in prompt_opening


def test_exgen3_leaf_scenes_cover_both_variant_sections_exactly():
    scenes = section_scenes_for_scope("ExGen3")

    assert set(scenes) == {"normal", "mega"}
    assert "Paldea-inspired valley" in scenes["normal"]["setting"]
    assert "distant blue coast" in scenes["normal"]["setting"]
    assert "expansive highland basin" in scenes["mega"]["setting"]
    assert "refracted energy" in scenes["mega"]["setting"]
    assert all("safe_areas" not in scene for scene in scenes.values())


def test_checked_in_pokedex_output_has_localized_section_overlay_values():
    bundle = next(
        bundle
        for bundle in poster_bundles_for_scope("Pokedex")
        if bundle.section_id == "gen1"
    )
    source_data = load_poster_scope_data(bundle)

    assert info_panel_values(
        source_data,
        "fr",
        "section_summary",
    ) == (
        "Génération I",
        "Kanto",
        "151 Pokémon",
        "Pokédex #001 – #151",
    )
    assert info_panel_values(
        source_data,
        "ja",
        "section_summary",
    ) == (
        "1世代",
        "カントー",
        "151 ポケモン",
        "ポケモン図鑑 #001 – #151",
    )


def test_section_overlay_uses_localized_title_count_and_description():
    values = info_panel_values(
        {
            "sections": {
                "gen1": {
                    "title": {"en": "Generation I", "fr": "Génération I"},
                    "subtitle": {"en": "Kanto", "ja": "カントー"},
                    "description": {
                        "en": "Pokédex #001 – #151",
                        "ja": "ポケモン図鑑 #001 – #151",
                    },
                    "cards": [{}, {}],
                }
            }
        },
        "ja",
        "section_summary",
    )

    assert values == (
        "Generation I",
        "カントー",
        "2 ポケモン",
        "ポケモン図鑑 #001 – #151",
    )


def test_section_manifest_preserves_title_logo_token_but_info_hides_tokens():
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
    section = {
        "title": {
            language: "Mega-Pokémon [EX_NEW]"
            for language in languages
        },
        "subtitle": {
            language: "[EX_NEW] Series"
            for language in languages
        },
        "description": {
            language: "[M] Evolution with [EX_TERA] and [EX]"
            for language in languages
        },
        "featured_elements": [
            {"pokemon_id": pokemon_id}
            for pokemon_id in (25, 150, 151)
        ],
        "cards": [{}, {}, {}],
    }
    source = deepcopy(section)
    manifest = build_section_manifest(
        "ExGen3/sections/mega",
        "ExGen3",
        "mega",
        section,
        "standard_3x3",
        {"engine": "flux"},
        {
            "concept": "example",
            "setting": "example",
            "lighting": "example",
            "rendering": "example",
            "ground_noun": "grass",
        },
    )

    assert "title_text" not in manifest
    assert inline_title_logo(
        resolved_title_text({"sections": {"mega": section}}, "en")
    ) is not None
    assert info_panel_values(
        {"sections": {"mega": section}},
        "en",
        "section_summary",
    ) == (
        "Mega-Pokémon ex",
        "ex Series",
        "3 Pokémon",
        "Mega Evolution with Tera ex and EX",
    )
    assert info_panel_values(
        {"sections": {"mega": section}},
        "en",
        "section_summary",
        header_text="Mega-Pokémon [EX_NEW]",
    ) == (
        "ex Series",
        "3 Pokémon",
        "Mega Evolution with Tera ex and EX",
    )
    assert section == source


def test_section_title_with_multiple_logo_tokens_uses_plain_text_panel():
    assert inline_title_logo("[M] Pokémon [EX]") is None


def test_exgen2_sections_keep_one_logo_header_and_distinct_info_copy():
    source_data = json.loads(
        (ROOT / "data" / "output" / "ExGen2.json").read_text(
            encoding="utf-8",
        )
    )

    for section_id in ("normal", "mega", "primal"):
        section = source_data["sections"][section_id]
        for language in SUPPORTED_LANGUAGES:
            assert inline_title_logo(section["title"][language]) is not None

    assert source_data["sections"]["normal"]["title"]["en"] == (
        "Pokémon [EX]"
    )
    assert source_data["sections"]["normal"]["subtitle"]["en"] == (
        "Generation 2"
    )


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
def test_section_poster_finalizes_in_every_pdf_language(tmp_path, language):
    raw_path = tmp_path / f"raw-{language}.png"
    final_path = tmp_path / f"final-{language}.png"
    Image.new("RGB", (432, 608), (70, 130, 90)).save(raw_path)

    finalize(
        "Pokedex/sections/gen1",
        raw_path,
        final_path,
        language,
    )

    assert final_path.is_file()
    assert Image.open(final_path).size == (432, 608)
    assert (
        ImageChops.difference(
            Image.open(raw_path).convert("RGB"),
            Image.open(final_path).convert("RGB"),
        ).getbbox()
        is not None
    )


@pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
@pytest.mark.parametrize(
    "scope",
    (
        "ExGen3/sections/normal",
        "ExGen3/sections/mega",
    ),
)
def test_exgen3_posters_finalize_real_copy_in_every_language(
    tmp_path,
    language,
    scope,
):
    leaf = scope.rsplit("/", 1)[-1]
    raw_path = tmp_path / f"raw-{leaf}-{language}.png"
    final_path = tmp_path / f"final-{leaf}-{language}.png"
    Image.new("RGB", (432, 608), (70, 130, 90)).save(raw_path)

    finalize(scope, raw_path, final_path, language)

    assert final_path.is_file()
    assert Image.open(final_path).size == (432, 608)


def test_poster_wrapping_only_splits_unspaced_cjk_text_inside_words():
    font = load_font(48, language="ja")
    max_width = 100

    assert wrap_text("Pokémon ex", font, max_width) == [
        "Pokémon",
        "ex",
    ]
    cjk_lines = wrap_text("現代のポケモン時代", font, max_width)
    assert len(cjk_lines) > 1
    assert all(
        font.getbbox(line)[2] - font.getbbox(line)[0] <= max_width
        for line in cjk_lines
    )


def test_aggregate_index_rejects_unsafe_manifest_paths(tmp_path):
    scope_dir = tmp_path / "Aggregate"
    scope_dir.mkdir()
    (scope_dir / "posters.yaml").write_text(
        (
            "schema_version: 1\n"
            "scope: Aggregate\n"
            "posters:\n"
            "  - id: first\n"
            "    section_id: first\n"
            "    manifest: ../poster.yaml\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsafe relative poster asset path"):
        poster_bundles_for_scope("Aggregate", poster_assets=tmp_path)


@pytest.mark.parametrize("scope", [".", ".."])
def test_poster_scope_rejects_path_traversal_segments(tmp_path, scope):
    with pytest.raises(ValueError, match="poster scope"):
        poster_bundles_for_scope(scope, poster_assets=tmp_path)


def test_aggregate_index_rejects_duplicate_section_bindings(tmp_path):
    scope_dir = tmp_path / "Aggregate"
    target_dir = scope_dir / "first"
    target_dir.mkdir(parents=True)
    (target_dir / "poster.yaml").write_text(
        (
            "asset_key: Aggregate/first\n"
            "scope: Aggregate\n"
            "poster_id: first\n"
            "source:\n"
            "  scope: Aggregate\n"
            "  section_id: first\n"
        ),
        encoding="utf-8",
    )
    (scope_dir / "posters.yaml").write_text(
        (
            "schema_version: 1\n"
            "scope: Aggregate\n"
            "posters:\n"
            "  - id: first\n"
            "    section_id: first\n"
            "    manifest: first/poster.yaml\n"
            "    pdf:\n"
            "      insertion: after_section_cover\n"
            "  - id: second\n"
            "    section_id: first\n"
            "    manifest: second/poster.yaml\n"
            "    pdf:\n"
            "      insertion: after_section_cover\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate poster section_id"):
        poster_bundles_for_scope("Aggregate", poster_assets=tmp_path)


def test_section_source_must_exist_in_aggregate_data(tmp_path):
    assets = tmp_path / "assets"
    data = tmp_path / "data"
    target_dir = assets / "Aggregate" / "missing"
    target_dir.mkdir(parents=True)
    data.mkdir()
    (target_dir / "poster.yaml").write_text(
        (
            "asset_key: Aggregate/missing\n"
            "scope: Aggregate\n"
            "poster_id: missing\n"
            "source:\n"
            "  scope: Aggregate\n"
            "  section_id: missing\n"
        ),
        encoding="utf-8",
    )
    (data / "Aggregate.json").write_text(
        json.dumps({"sections": {"known": {"cards": []}}}),
        encoding="utf-8",
    )
    bundle = poster_bundle(
        "Aggregate/missing",
        scope="Aggregate",
        section_id="missing",
        poster_assets=assets,
    )

    with pytest.raises(KeyError, match="missing"):
        load_poster_scope_data(bundle, scope_data_dir=data)


def test_enabled_discovery_includes_nested_aggregate_targets(tmp_path):
    legacy = tmp_path / "Legacy"
    nested = tmp_path / "Aggregate" / "first"
    legacy.mkdir()
    nested.mkdir(parents=True)
    (legacy / "poster.yaml").write_text(
        (
            "scope: Legacy\n"
            "pdf:\n"
            "  enabled: true\n"
        ),
        encoding="utf-8",
    )
    (nested / "poster.yaml").write_text(
        (
            "asset_key: Aggregate/first\n"
            "scope: Aggregate\n"
            "poster_id: first\n"
            "source:\n"
            "  scope: Aggregate\n"
            "  section_id: first\n"
        ),
        encoding="utf-8",
    )
    (tmp_path / "Aggregate" / "posters.yaml").write_text(
        (
            "schema_version: 1\n"
            "scope: Aggregate\n"
            "posters:\n"
            "  - id: first\n"
            "    section_id: first\n"
            "    manifest: first/poster.yaml\n"
            "    pdf:\n"
            "      enabled: true\n"
            "      insertion: after_section_cover\n"
        ),
        encoding="utf-8",
    )

    assert enabled_poster_scopes(tmp_path) == [
        "Aggregate/first",
        "Legacy",
    ]
