import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from PIL import Image

from scripts.poster_assets import finalize_comfyui_poster as finalizer
from scripts.poster_assets import promote_comfyui_poster as promotion
from scripts.poster_assets import provenance
from scripts.poster_assets import validate_promoted_poster as validator
from scripts.poster_assets.layout import (
    build_generation_output_layout,
    build_print_layout,
)
from scripts.poster_assets.poster_config import (
    IDENTITY_LOCK_PROMPT_FILE,
    build_identity_lock_prompt,
)
from scripts.poster_assets.poster_io import load_json, poster_bundle
from scripts.poster_assets.poster_subject import PosterSubject
from scripts.poster_assets.provenance import (
    JOINT_SCENE_REVIEW_CRITERIA,
    JOINT_SCENE_REVIEW_KEY,
    approve_joint_scene_visual_review,
    build_generation_fingerprint,
    build_overlay_fingerprint,
    current_generation_pipeline_contract_version,
    file_record,
    fingerprint_record_is_valid,
    generation_fingerprint_pipeline_contract_version,
    load_run_metadata,
    required_model_artifact_hashes,
    require_joint_scene_visual_review,
    sha256_file,
    write_run_metadata,
)


def _manifest() -> dict:
    digest = "1" * 64
    return {
        "schema_version": 2,
        "scope": "Example",
        "layout": {"name": "standard_3x3"},
        "text_cells": {
            "title": {"row": 1, "column": 2},
            "set_info": {
                "row": 2,
                "column": 2,
                "max_width_ratio": 0.92,
                "max_height_ratio": 0.68,
            },
        },
        "text_content": {"mode": "section_summary"},
        "pdf": {
            "enabled": True,
            "artwork_file": "poster-flux2-artwork.png",
            "insertion": "after_first_section_cover",
        },
        "artwork": {
            "promoted_file": "poster-flux2-artwork.png",
            "preview_file": "poster-flux2.png",
            "provenance_file": "poster-flux2-provenance.json",
            "identity_lock": {
                "overscan_ratio": 0.04,
                "max_protected_start_ratio": 0.70,
                "transition_ratio": 0.10,
                "subject_clearance_ratio": 0.02,
            },
            "scene": {
                "concept": "a quiet example collection",
                "setting": "The artwork contains a broad green valley.",
                "lighting": "Soft daylight enters from the upper left.",
                "rendering": "Use restrained hand-painted cel linework.",
                "ground_noun": "meadow",
            },
            "generation": {
                "engine": "flux",
                "model": "model.safetensors",
                "model_sha256": digest,
                "encoder": "encoder.safetensors",
                "encoder_sha256": digest,
                "vae": "vae.safetensors",
                "vae_sha256": digest,
                "mode": "identity_lock",
                "reference_mode": "two_pass_source_pixels",
                "seed": 123,
                "steps": 4,
                "generation_megapixels": 1.0,
                "output_dpi": 10,
                "output_method": "model_upscale",
                "upscale_model": "upscale.pth",
                "upscale_model_sha256": digest,
            },
        },
        "pokemon": {
            "strategy": "featured_from_scope",
            "count": "auto_from_layout_columns",
            "row": "bottom",
            "cutout_source": "pokeapi_official_artwork",
            "fallback_candidates": [],
        },
        "conditioning": {
            "identity_defaults": {
                "neutral_rgb": [226, 224, 211],
                "canvas_px": 512,
                "min_subject_px": 150,
                "max_subject_px": 350,
                "bottom_padding_px": 24,
            }
        },
    }


def _scope_data() -> dict:
    return {
        "name": "Example",
        "sections": {
            "main": {
                "title": {"de": "Beispielsammlung", "en": "Example Collection"},
                "subtitle": {"de": "Tal", "en": "Valley"},
                "description": {
                    "de": "Nummern #001 – #007",
                    "en": "Numbers #001 – #007",
                },
                "featured_elements": [
                    {"pokemon_id": 1},
                    {"pokemon_id": 4},
                    {"pokemon_id": 7},
                ],
                "cards": [],
            }
        },
    }


def _write_fixture(tmp_path: Path):
    repository = tmp_path / "repository"
    assets = repository / "data" / "poster_assets"
    output = repository / "data" / "output"
    scope_dir = assets / "Example"
    cutout_dir = scope_dir / "cutouts"
    cutout_dir.mkdir(parents=True)
    output.mkdir(parents=True)

    manifest = _manifest()
    manifest_path = scope_dir / "poster.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (output / "Example.json").write_text(
        json.dumps(_scope_data(), ensure_ascii=False),
        encoding="utf-8",
    )
    items = []
    for pokemon_id, color in (
        (1, (80, 180, 90, 255)),
        (4, (235, 120, 50, 255)),
        (7, (80, 150, 220, 255)),
    ):
        filename = f"pokemon_{pokemon_id:03d}.png"
        Image.new("RGBA", (18, 18), color).save(cutout_dir / filename)
        items.append(
            {
                "pokemon_id": pokemon_id,
                "url": PosterSubject(pokemon_id, pokemon_id).image_url,
                "file": filename,
            }
        )
    (cutout_dir / "manifest.json").write_text(
        json.dumps(
            {
                "scope": "Example",
                "generated_at": "2026-01-01T00:00:00Z",
                "items": items,
            }
        ),
        encoding="utf-8",
    )
    Image.new("RGBA", (48, 24), (240, 210, 70, 255)).save(
        scope_dir / "logo.png"
    )
    bundle = poster_bundle("Example", poster_assets=assets)
    return repository, assets, output, scope_dir, bundle


def _with_manifest(bundle, manifest):
    return replace(bundle, manifest=manifest)


def _with_slotted_wide_fallback(scope_dir, bundle):
    manifest = copy.deepcopy(bundle.manifest)
    manifest["layout"] = {"name": "wide_4x3"}
    manifest["pokemon"]["fallback_candidates"] = [
        {"pokemon_id": 25, "slot": 2}
    ]

    cutout_dir = scope_dir / "cutouts"
    filename = "pokemon_025.png"
    Image.new("RGBA", (18, 18), (240, 205, 55, 255)).save(
        cutout_dir / filename
    )
    cutouts = load_json(cutout_dir / "manifest.json")
    cutouts["items"].insert(
        1,
        {
            "pokemon_id": 25,
            "url": PosterSubject(25, 25).image_url,
            "file": filename,
        },
    )
    (cutout_dir / "manifest.json").write_text(
        json.dumps(cutouts),
        encoding="utf-8",
    )
    return replace(
        bundle,
        asset_key="Example/sections/main",
        poster_id="main",
        section_id="main",
        manifest=manifest,
    )


def test_slotted_fallback_order_is_shared_by_fingerprint_and_validation(
    tmp_path,
):
    _repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    bundle = _with_slotted_wide_fallback(scope_dir, bundle)

    fingerprint = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )

    assert fingerprint["components"]["source_subject_ids"] == [1, 25, 4, 7]
    validator._validate_source_subjects(bundle, _scope_data())


def test_promoted_provenance_records_custom_workspace_master_path(
    tmp_path,
    monkeypatch,
):
    repository = tmp_path / "repository"
    asset_dir = (
        repository
        / "tmp"
        / "custom-poster-layouts"
        / "example"
        / "Example"
    )
    asset_dir.mkdir(parents=True)
    artwork = asset_dir / ".stage-artwork.png"
    Image.new("RGB", (8, 8), (40, 120, 80)).save(artwork)
    monkeypatch.setattr(provenance, "ROOT", repository)
    stable_artwork = asset_dir / "poster-flux2-artwork.png"

    payload = provenance.promoted_provenance(
        scope="Example",
        name="flux2",
        language="de",
        run_metadata={},
        artwork_path=artwork,
        stable_artwork_path=stable_artwork,
    )

    prefix = "tmp/custom-poster-layouts/example/Example"
    assert payload["outputs"]["artwork"]["file"] == (
        f"{prefix}/poster-flux2-artwork.png"
    )
    assert set(payload["outputs"]) == {"artwork"}


def test_generation_fingerprint_excludes_routing_and_overlay_only_inputs(
    tmp_path,
):
    _repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    original = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )

    changed = copy.deepcopy(bundle.manifest)
    changed["pdf"]["enabled"] = False
    changed["pdf"]["artwork_file"] = "another-promoted-artwork.png"
    changed["title_logo"] = {"file": "another-logo.png"}
    changed["text_content"] = {"mode": "set_summary"}
    changed["text_cells"]["set_info"]["max_width_ratio"] = 0.74
    changed["text_cells"]["set_info"]["max_height_ratio"] = 0.51
    changed["artwork"]["promoted_file"] = "another-promoted-artwork.png"
    changed["artwork"]["preview_file"] = "another-preview.png"
    changed["artwork"]["provenance_file"] = "another-provenance.json"
    overlay_changed = build_generation_fingerprint(
        _with_manifest(bundle, changed),
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert overlay_changed["sha256"] == original["sha256"]

    cutout_manifest = scope_dir / "cutouts" / "manifest.json"
    cutouts = load_json(cutout_manifest)
    cutouts["generated_at"] = "2099-12-31T23:59:59Z"
    cutout_manifest.write_text(json.dumps(cutouts), encoding="utf-8")
    timestamp_changed = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert timestamp_changed["sha256"] == original["sha256"]


def test_generation_fingerprint_changes_for_generation_inputs(tmp_path):
    _repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    original = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )

    mutations = []
    scene = copy.deepcopy(bundle.manifest)
    scene["artwork"]["scene"]["concept"] = "a changed generated scene"
    mutations.append(scene)
    model = copy.deepcopy(bundle.manifest)
    model["artwork"]["generation"]["model"] = "another-model.safetensors"
    mutations.append(model)
    safe_cell = copy.deepcopy(bundle.manifest)
    safe_cell["text_cells"]["title"]["column"] = 1
    mutations.append(safe_cell)
    identity_lock = copy.deepcopy(bundle.manifest)
    identity_lock["artwork"]["identity_lock"]["overscan_ratio"] = 0.08
    mutations.append(identity_lock)
    pokemon = copy.deepcopy(bundle.manifest)
    pokemon["pokemon"]["fallback_candidates"] = [{"pokemon_id": 25}]
    mutations.append(pokemon)
    conditioning = copy.deepcopy(bundle.manifest)
    conditioning["conditioning"]["identity_defaults"]["canvas_px"] = 768
    mutations.append(conditioning)

    for changed in mutations:
        fingerprint = build_generation_fingerprint(
            _with_manifest(bundle, changed),
            poster_assets=assets,
            scope_data_dir=output,
        )
        assert fingerprint["sha256"] != original["sha256"]

    Image.new("RGBA", (18, 18), (1, 2, 3, 255)).save(
        scope_dir / "cutouts" / "pokemon_001.png"
    )
    pixels_changed = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert pixels_changed["sha256"] != original["sha256"]


def test_generation_fingerprint_is_base_compatible_and_form_sensitive(
    tmp_path,
):
    _repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    original = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    source_path = output / "Example.json"
    cutout_manifest_path = scope_dir / "cutouts" / "manifest.json"
    source = load_json(source_path)
    cutouts = load_json(cutout_manifest_path)

    source["sections"]["main"]["featured_elements"][0][
        "poster_subject"
    ] = PosterSubject(1, 1).as_mapping()
    cutouts["items"][0]["poster_subject"] = PosterSubject(
        1,
        1,
    ).as_mapping()
    source_path.write_text(json.dumps(source), encoding="utf-8")
    cutout_manifest_path.write_text(json.dumps(cutouts), encoding="utf-8")

    explicit_base = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert explicit_base["sha256"] == original["sha256"]
    assert explicit_base["components"]["source_subject_ids"][0] == 1
    assert "poster_subject" not in explicit_base["components"]["cutouts"][0]

    source["sections"]["main"]["featured_elements"][0] = {
        "pokemon_id": 6,
        "poster_subject": PosterSubject(6, 10034).as_mapping(),
    }
    cutouts["items"][0]["pokemon_id"] = 6
    cutouts["items"][0]["url"] = PosterSubject(6, 10034).image_url
    cutouts["items"][0]["poster_subject"] = PosterSubject(
        6,
        10034,
    ).as_mapping()
    source_path.write_text(json.dumps(source), encoding="utf-8")
    cutout_manifest_path.write_text(json.dumps(cutouts), encoding="utf-8")
    first_form = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )

    source["sections"]["main"]["featured_elements"][0][
        "poster_subject"
    ] = PosterSubject(6, 10035).as_mapping()
    cutouts["items"][0]["url"] = PosterSubject(6, 10035).image_url
    cutouts["items"][0]["poster_subject"] = PosterSubject(
        6,
        10035,
    ).as_mapping()
    source_path.write_text(json.dumps(source), encoding="utf-8")
    cutout_manifest_path.write_text(json.dumps(cutouts), encoding="utf-8")
    second_form = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )

    assert first_form["sha256"] != original["sha256"]
    assert second_form["sha256"] != first_form["sha256"]
    assert first_form["components"]["source_subject_ids"][0] == {
        "pokemon_id": 6,
        "poster_subject": {
            "source": "pokeapi_official_artwork",
            "official_artwork_id": 10034,
        },
    }
    assert first_form["components"]["cutouts"][0]["poster_subject"] == {
        "source": "pokeapi_official_artwork",
        "official_artwork_id": 10034,
    }


def test_generation_fingerprint_rejects_stale_form_cutout_selection(tmp_path):
    _repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    source_path = output / "Example.json"
    manifest_path = scope_dir / "cutouts" / "manifest.json"
    source = load_json(source_path)
    cutouts = load_json(manifest_path)

    source["sections"]["main"]["featured_elements"][0] = {
        "pokemon_id": 6,
        "poster_subject": PosterSubject(6, 10034).as_mapping(),
    }
    cutouts["items"][0]["pokemon_id"] = 6
    cutouts["items"][0]["url"] = PosterSubject(6, 6).image_url
    source_path.write_text(json.dumps(source), encoding="utf-8")
    manifest_path.write_text(json.dumps(cutouts), encoding="utf-8")

    with pytest.raises(ValueError, match="do not match current source"):
        build_generation_fingerprint(
            bundle,
            poster_assets=assets,
            scope_data_dir=output,
        )


def test_generation_fingerprint_rejects_duplicate_cutout_subjects(tmp_path):
    _repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    manifest_path = scope_dir / "cutouts" / "manifest.json"
    original = load_json(manifest_path)

    duplicate = copy.deepcopy(original)
    duplicate["items"].append(copy.deepcopy(duplicate["items"][0]))
    manifest_path.write_text(json.dumps(duplicate), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate poster subject"):
        build_generation_fingerprint(
            bundle,
            poster_assets=assets,
            scope_data_dir=output,
        )

    wrong_url = copy.deepcopy(original)
    wrong_url["items"][0]["url"] = PosterSubject(4, 4).image_url
    manifest_path.write_text(json.dumps(wrong_url), encoding="utf-8")
    with pytest.raises(ValueError, match="URL does not match poster subject"):
        build_generation_fingerprint(
            bundle,
            poster_assets=assets,
            scope_data_dir=output,
        )


def test_required_model_hashes_follow_the_selected_engine_artifacts():
    assert required_model_artifact_hashes(
        {
            "model": "model.safetensors",
            "encoder": "clip.safetensors",
            "vae": "vae.safetensors",
            "upscale_model": "upscale.pth",
        }
    ) == (
        "model_sha256",
        "encoder_sha256",
        "vae_sha256",
        "upscale_model_sha256",
    )


def test_pipeline_contract_versions_are_family_specific_and_strict():
    identity_generation = {"engine": "flux", "mode": "identity_lock"}
    joint_generation = {"engine": "flux", "mode": "joint_scene"}
    regional_generation = {
        "engine": "flux",
        "mode": "joint_scene",
        "reference_mode": "regional_identity_joint",
    }

    assert current_generation_pipeline_contract_version(
        identity_generation
    ) == 3
    assert current_generation_pipeline_contract_version(joint_generation) == 9
    assert (
        current_generation_pipeline_contract_version(regional_generation)
        == 19
    )
    accepted_legacy = provenance.fingerprint_record(
        {
            "pipeline_contract": {
                "name": "poster_generation",
                "version": 1,
            }
        }
    )
    assert generation_fingerprint_pipeline_contract_version(
        accepted_legacy,
        identity_generation,
    ) == 1
    unsupported = provenance.fingerprint_record(
        {
            "pipeline_contract": {
                "name": "poster_generation",
                "version": 4,
            }
        }
    )
    with pytest.raises(ValueError, match="Unsupported generation pipeline"):
        generation_fingerprint_pipeline_contract_version(
            unsupported,
            identity_generation,
        )
    with pytest.raises(ValueError, match="Unsupported generation pipeline"):
        generation_fingerprint_pipeline_contract_version(
            accepted_legacy,
            joint_generation,
        )
    spatial_v5 = provenance.fingerprint_record(
        {
            "pipeline_contract": {
                "name": "poster_generation",
                "version": 5,
            }
        }
    )
    with pytest.raises(ValueError, match="Unsupported generation pipeline"):
        generation_fingerprint_pipeline_contract_version(
            spatial_v5,
            regional_generation,
        )


def test_joint_scene_fingerprint_enforces_reference_and_ignores_identity_lock(
    tmp_path,
):
    _repository, assets, output, _scope_dir, bundle = _write_fixture(
        tmp_path
    )
    manifest = copy.deepcopy(bundle.manifest)
    generation = manifest["artwork"]["generation"]
    generation.update(
        mode="joint_scene",
        reference_mode="spatial_identity_joint",
        output_method="lanczos",
        output_megapixels=0.25,
    )
    for key in ("output_dpi", "upscale_model", "upscale_model_sha256"):
        generation.pop(key, None)
    joint_bundle = _with_manifest(bundle, manifest)
    original = build_generation_fingerprint(
        joint_bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert "identity_lock" not in original["components"]

    changed = copy.deepcopy(manifest)
    changed["artwork"]["identity_lock"] = {
        "overscan_ratio": 999,
    }
    unchanged = build_generation_fingerprint(
        _with_manifest(bundle, changed),
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert unchanged["sha256"] == original["sha256"]

    changed = copy.deepcopy(manifest)
    changed["conditioning"]["subjects"] = {
        "1": {"composition": {"scale": 999}}
    }
    composition_only = build_generation_fingerprint(
        _with_manifest(bundle, changed),
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert composition_only["sha256"] == original["sha256"]

    changed = copy.deepcopy(manifest)
    changed["conditioning"]["identity_defaults"]["canvas_px"] = 640
    unused_identity_canvas_change = build_generation_fingerprint(
        _with_manifest(bundle, changed),
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert unused_identity_canvas_change["sha256"] == original["sha256"]

    changed = copy.deepcopy(manifest)
    changed["conditioning"]["identity_defaults"]["neutral_rgb"] = [
        220,
        220,
        220,
    ]
    cast_reference_change = build_generation_fingerprint(
        _with_manifest(bundle, changed),
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert cast_reference_change["sha256"] != original["sha256"]

    changed = copy.deepcopy(manifest)
    changed["artwork"]["generation"]["reference_mode"] = "identity"
    with pytest.raises(ValueError, match="reference contract"):
        build_generation_fingerprint(
            _with_manifest(bundle, changed),
            poster_assets=assets,
            scope_data_dir=output,
        )


def test_joint_scene_rejects_a_learned_post_generation_upscaler(tmp_path):
    _repository, assets, output, _scope_dir, bundle = _write_fixture(
        tmp_path
    )
    manifest = copy.deepcopy(bundle.manifest)
    manifest["artwork"]["generation"].update(
        mode="joint_scene",
        reference_mode="spatial_identity_joint",
    )

    with pytest.raises(ValueError, match="deterministic Lanczos"):
        build_generation_fingerprint(
            _with_manifest(bundle, manifest),
            poster_assets=assets,
            scope_data_dir=output,
        )


def test_regional_joint_scene_fingerprint_uses_v19_without_cast_contract(
    tmp_path,
):
    _repository, assets, output, _scope_dir, bundle = _write_fixture(
        tmp_path
    )
    manifest = copy.deepcopy(bundle.manifest)
    generation = manifest["artwork"]["generation"]
    generation.update(
        mode="joint_scene",
        reference_mode="regional_identity_joint",
        output_method="lanczos",
        output_megapixels=0.25,
    )
    for key in ("output_dpi", "upscale_model", "upscale_model_sha256"):
        generation.pop(key, None)

    fingerprint = build_generation_fingerprint(
        _with_manifest(bundle, manifest),
        poster_assets=assets,
        scope_data_dir=output,
    )

    assert (
        fingerprint["components"]["pipeline_contract"]["version"]
            == 19
    )
    conditioning = fingerprint["components"][
        "joint_scene_conditioning"
    ]
    assert conditioning["reference_strategy"] == (
        "regional_identity_per_physical_card"
    )
    assert "cast_max_megapixels" not in conditioning


def test_joint_scene_input_records_follow_reference_order(
    tmp_path,
    monkeypatch,
):
    repository, assets, _output, scope_dir, _bundle = _write_fixture(
        tmp_path
    )
    work_dir = scope_dir / "comfyui_poster"
    work_dir.mkdir()
    workflow_path = work_dir / "workflow.json"
    workflow_path.write_text("{}\n", encoding="utf-8")
    (work_dir / provenance.JOINT_SCENE_PROMPT_FILE).write_text(
        "draft\n\nfinal\n",
        encoding="utf-8",
    )
    Image.new("RGB", (32, 44), (226, 224, 211)).save(
        work_dir / "joint_scene_cast_reference.png"
    )
    for index in range(1, 4):
        Image.new("RGB", (32, 32), (226, 224, 211)).save(
            work_dir / f"identity_reference_{index}.png"
        )
    monkeypatch.setattr(provenance, "POSTER_ASSETS", assets)
    monkeypatch.setattr(provenance, "ROOT", repository)

    records = provenance.generation_input_records(
        "Example",
        workflow_path,
        {
            "engine": "flux",
            "mode": "joint_scene",
            "reference_mode": "spatial_identity_joint",
            "output_method": "lanczos",
            "output_megapixels": 0.25,
        },
    )

    assert [
        Path(record["file"]).name for record in records["references"]
    ] == [
        "joint_scene_cast_reference.png",
        "identity_reference_1.png",
        "identity_reference_2.png",
        "identity_reference_3.png",
    ]
    assert "internal_references" not in records
    assert "source_pixel_audit_reference" not in records


def test_regional_joint_scene_input_records_do_not_include_a_cast(
    tmp_path,
    monkeypatch,
):
    repository, assets, _output, scope_dir, _bundle = _write_fixture(
        tmp_path
    )
    work_dir = scope_dir / "comfyui_poster"
    work_dir.mkdir()
    workflow_path = work_dir / "workflow.json"
    workflow_path.write_text("{}\n", encoding="utf-8")
    (
        work_dir / provenance.REGIONAL_JOINT_SCENE_PROMPT_FILE
    ).write_text(
        "regional prompt\n",
        encoding="utf-8",
    )
    for index in range(1, 4):
        Image.new("RGB", (32, 32), (226, 224, 211)).save(
            work_dir / f"identity_reference_{index}.png"
        )
    monkeypatch.setattr(provenance, "POSTER_ASSETS", assets)
    monkeypatch.setattr(provenance, "ROOT", repository)

    records = provenance.generation_input_records(
        "Example",
        workflow_path,
        {
            "engine": "flux",
            "mode": "joint_scene",
            "reference_mode": "regional_identity_joint",
            "output_method": "lanczos",
            "output_megapixels": 0.25,
        },
    )

    assert [
        Path(record["file"]).name for record in records["references"]
    ] == [
        "identity_reference_1.png",
        "identity_reference_2.png",
        "identity_reference_3.png",
    ]
    assert Path(records["prompt"]["file"]).name == (
        provenance.REGIONAL_JOINT_SCENE_PROMPT_FILE
    )
    assert "source_pixel_audit_reference" not in records


@pytest.mark.parametrize("reviewer_kind", ["human", "agent"])
def test_joint_scene_review_is_bound_to_artwork_and_source_identities(
    tmp_path, reviewer_kind,
):
    artwork_path = tmp_path / "artwork.png"
    raw_artwork_path = tmp_path / "raw.png"
    Image.new("RGB", (100, 140), (40, 120, 80)).save(artwork_path)
    Image.new("RGB", (80, 112), (50, 130, 90)).save(raw_artwork_path)
    artwork_record = file_record(artwork_path, image=True)
    raw_artwork_record = file_record(raw_artwork_path, image=True)
    source_digests = ["c" * 64, "d" * 64, "e" * 64]
    source_pixel_digests = ["3" * 64, "4" * 64, "5" * 64]
    fingerprint = provenance.fingerprint_record(
        {
            "source_subject_ids": [722, 725, 728],
            "cutouts": [
                {
                    "pokemon_id": pokemon_id,
                    "pixel_sha256": source_pixel_digest,
                }
                for pokemon_id, source_pixel_digest in zip(
                    (722, 725, 728),
                    source_pixel_digests,
                    strict=True,
                )
            ],
        }
    )
    run = {
        "generation": {
            "engine": "flux",
            "mode": "joint_scene",
            "reference_mode": "spatial_identity_joint",
        },
        "source_artwork": artwork_record,
        "raw_artwork": raw_artwork_record,
        "inputs": {
            "cutouts": [
                {
                    "sha256": source_digest,
                    "pixel_sha256": source_pixel_digest,
                }
                for source_digest, source_pixel_digest in zip(
                    source_digests,
                    source_pixel_digests,
                    strict=True,
                )
            ],
            "generation_fingerprint": fingerprint,
        },
        "validation": {
            "source_pixels": {
                "method": "exact_opaque_source_pixels",
                "passed": False,
                "changed_pixels": 100,
            }
        },
    }

    record = approve_joint_scene_visual_review(
        run,
        artwork_path=artwork_path,
        raw_artwork_path=raw_artwork_path,
        reviewer_kind=reviewer_kind,
    )

    assert record["method"] == f"{reviewer_kind}_identity_and_scene_review"
    assert record["passed"] is True
    assert record["criteria"] == list(JOINT_SCENE_REVIEW_CRITERIA)
    assert record["reviewed_artwork_sha256"] == artwork_record["sha256"]
    assert (
        record["reviewed_artwork_pixel_sha256"]
        == artwork_record["pixel_sha256"]
    )
    assert record["source_cutout_sha256"] == source_digests
    assert record["source_cutout_pixel_sha256"] == source_pixel_digests
    assert run["validation"][JOINT_SCENE_REVIEW_KEY] == record
    assert (
        require_joint_scene_visual_review(
            run,
            artwork_path=artwork_path,
            raw_artwork_path=raw_artwork_path,
        )
        == record
    )

    missing_raw_digest = copy.deepcopy(run)
    missing_raw_digest["raw_artwork"] = {}
    with pytest.raises(ValueError, match="raw artwork provenance"):
        approve_joint_scene_visual_review(
            missing_raw_digest,
            artwork_path=artwork_path,
            raw_artwork_path=raw_artwork_path,
            reviewer_kind=reviewer_kind,
        )

    stale_cutout_pixels = copy.deepcopy(run)
    stale_cutout_pixels["inputs"]["cutouts"][0]["pixel_sha256"] = "6" * 64
    with pytest.raises(ValueError, match="do not match"):
        approve_joint_scene_visual_review(
            stale_cutout_pixels,
            artwork_path=artwork_path,
            raw_artwork_path=raw_artwork_path,
            reviewer_kind=reviewer_kind,
        )

    for invalid_kind in (None, "", "automated"):
        with pytest.raises(ValueError, match="reviewer kind"):
            approve_joint_scene_visual_review(
                copy.deepcopy(run),
                artwork_path=artwork_path,
                raw_artwork_path=raw_artwork_path,
                reviewer_kind=invalid_kind,
            )

    unknown_review = copy.deepcopy(run)
    unknown_review["validation"][JOINT_SCENE_REVIEW_KEY]["method"] = (
        "automated_identity_and_scene_review"
    )
    with pytest.raises(ValueError, match="incomplete or stale"):
        require_joint_scene_visual_review(unknown_review)

    run["source_artwork"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="incomplete or stale"):
        require_joint_scene_visual_review(run)

    run["source_artwork"] = file_record(artwork_path, image=True)
    Image.new("RGB", (80, 112), (200, 40, 40)).save(raw_artwork_path)
    with pytest.raises(ValueError, match="raw artwork record does not match"):
        require_joint_scene_visual_review(
            run,
            artwork_path=artwork_path,
            raw_artwork_path=raw_artwork_path,
        )


def test_joint_scene_cannot_promote_without_explicit_visual_review():
    with pytest.raises(ValueError, match="lacks explicit visual identity"):
        require_joint_scene_visual_review(
            {
                "generation": {
                    "engine": "flux",
                    "mode": "joint_scene",
                },
                "validation": {
                    "source_pixels": {
                        "method": "exact_opaque_source_pixels",
                        "passed": False,
                    }
                },
            }
        )


def test_reaccepted_joint_scene_requires_hash_bound_historical_decision():
    root = Path(__file__).resolve().parents[2]
    run = json.loads(
        (
            root
            / "assets/posters/Pokedex/sections/gen3/poster-flux2-provenance.json"
        ).read_text(encoding="utf-8")
    )["run"]
    require_joint_scene_visual_review(run)

    for change in ("missing_reacceptance", "wrong_master", "wrong_report", "wrong_history"):
        damaged = copy.deepcopy(run)
        review = damaged["validation"][JOINT_SCENE_REVIEW_KEY]
        if change == "missing_reacceptance":
            del review["reacceptance"]
        elif change == "wrong_master":
            review["reacceptance"]["accepted_master_sha256"] = "0" * 64
        elif change == "wrong_report":
            review["reacceptance"]["report_sha256"] = "0" * 64
        else:
            review["historical_reaudit_revocation"]["master_sha256"] = "0" * 64
        with pytest.raises(ValueError, match="reacceptance"):
            require_joint_scene_visual_review(damaged)


@pytest.mark.parametrize(
    ("engine", "mode", "reference_mode", "current_version"),
    (
        ("flux", "identity_lock", "two_pass_source_pixels", 3),
        ("flux", "joint_scene", "spatial_identity_joint", 7),
        ("flux", "joint_scene", "regional_identity_joint", 19),
        ("flux", "joint_scene", "individual_spatial_joint", 9),
    ),
)
def test_every_engine_family_versions_the_shared_raster_contract(
    engine,
    mode,
    reference_mode,
    current_version,
):
    generation = {
        "engine": engine,
        "mode": mode,
        "reference_mode": reference_mode,
        "generation_megapixels": 1.0,
        "output_dpi": 300,
    }

    assert (
        current_generation_pipeline_contract_version(generation)
        == current_version
    )
    current = provenance._layout_generation_contract(
        _manifest(),
        generation,
        current_version,
    )
    legacy = provenance._layout_generation_contract(
        _manifest(),
        generation,
        provenance.RASTER_GEOMETRY_PIPELINE_MINIMUM[(engine, mode)] - 1,
    )

    assert current["raster_geometry"]["version"] == 2
    assert "raster_geometry" not in legacy


def test_current_generation_contract_records_exact_raster_geometry(
    tmp_path,
):
    _repository, assets, output, _scope_dir, bundle = _write_fixture(
        tmp_path
    )

    current = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    geometry = current["components"]["layout"]["raster_geometry"]

    assert current["components"]["pipeline_contract"]["version"] == 3
    assert geometry == {
        "name": "cumulative_physical_endpoints",
        "version": 2,
        "generation_canvas_px": [848, 1168],
        "generation_column_spans_px": [
            [0, 269],
            [290, 558],
            [579, 848],
        ],
        "generation_row_spans_px": [
            [0, 375],
            [396, 772],
            [793, 1168],
        ],
        "output_canvas_px": [79, 109],
        "output_column_spans_px": [
            [0, 25],
            [27, 52],
            [54, 79],
        ],
        "output_row_spans_px": [
            [0, 35],
            [37, 72],
            [74, 109],
        ],
    }

    legacy = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
        pipeline_contract_version=2,
    )
    assert "raster_geometry" not in legacy["components"]["layout"]


def test_run_metadata_records_generation_and_overlay_fingerprints(
    tmp_path,
    monkeypatch,
):
    repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    work_dir = scope_dir / "comfyui_poster"
    work_dir.mkdir()
    Image.new("RGBA", (18, 18), (10, 20, 30, 255)).save(
        work_dir / "inpaint_reference.png"
    )
    Image.new("RGBA", (18, 18), (0, 0, 0, 0)).save(
        work_dir / "upper_context_mask.png"
    )
    Image.new("RGBA", (18, 18), (0, 0, 0, 0)).save(
        work_dir / "upper_context_generation_mask.png"
    )
    scope_data = load_json(output / "Example.json")
    (work_dir / IDENTITY_LOCK_PROMPT_FILE).write_text(
        build_identity_lock_prompt(bundle.manifest, scope_data) + "\n",
        encoding="utf-8",
    )
    workflow = work_dir / "workflow.json"
    workflow.write_text("{}\n", encoding="utf-8")
    artwork = tmp_path / "artwork.png"
    Image.new("RGB", (79, 109), (40, 120, 80)).save(artwork)
    monkeypatch.setattr(provenance, "POSTER_ASSETS", assets)
    monkeypatch.setattr(provenance, "SCOPE_DATA", output)
    monkeypatch.setattr(provenance, "ROOT", repository)

    metadata_path = write_run_metadata(
        "Example",
        artwork,
        workflow,
        bundle.manifest["artwork"]["generation"],
    )
    metadata = load_json(metadata_path)

    assert fingerprint_record_is_valid(
        metadata["inputs"]["generation_fingerprint"]
    )
    assert fingerprint_record_is_valid(
        metadata["inputs"]["overlay_fingerprint"]
    )


def test_overlay_fingerprint_tracks_text_and_logo_but_not_pdf_routing(
    tmp_path,
):
    _repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    original = build_overlay_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )

    routing = copy.deepcopy(bundle.manifest)
    routing["pdf"]["enabled"] = False
    routing_changed = build_overlay_fingerprint(
        _with_manifest(bundle, routing),
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert routing_changed["sha256"] == original["sha256"]

    layout = copy.deepcopy(bundle.manifest)
    layout["text_cells"]["set_info"]["max_width_ratio"] = 0.8
    layout_changed = build_overlay_fingerprint(
        _with_manifest(bundle, layout),
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert layout_changed["sha256"] != original["sha256"]

    source_path = output / "Example.json"
    source = load_json(source_path)
    source["sections"]["main"]["description"]["en"] = "Changed range text"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    localized_changed = build_overlay_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert localized_changed["sha256"] != original["sha256"]

    logo_manifest = copy.deepcopy(bundle.manifest)
    logo_manifest["title_logo"] = {"file": "logo.png"}
    logo_bundle = _with_manifest(bundle, logo_manifest)
    logo_original = build_overlay_fingerprint(
        logo_bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    Image.new("RGBA", (48, 24), (20, 40, 220, 255)).save(
        scope_dir / "logo.png"
    )
    logo_changed = build_overlay_fingerprint(
        logo_bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    assert logo_changed["sha256"] != logo_original["sha256"]


def test_overlay_fingerprint_tracks_the_rendering_contract(
    tmp_path,
    monkeypatch,
):
    _repository, assets, output, _scope_dir, bundle = _write_fixture(
        tmp_path
    )
    current = build_overlay_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )

    assert current["components"]["pipeline_contract"] == {
        "name": "poster_overlay",
        "version": 3,
    }
    monkeypatch.setattr(
        provenance,
        "OVERLAY_PIPELINE_CONTRACT_VERSION",
        1,
    )
    legacy = build_overlay_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )

    assert legacy["sha256"] != current["sha256"]


def test_overlay_fingerprint_tracks_plain_title_renderer_contract(
    tmp_path,
    monkeypatch,
):
    _repository, assets, output, _scope_dir, bundle = _write_fixture(
        tmp_path
    )
    current = build_overlay_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )

    assert {
        component["title"]["renderer"]
        for component in current["components"]["languages"].values()
    } == {"direct_outlined_v1"}

    monkeypatch.setattr(
        finalizer,
        "PLAIN_TITLE_RENDERER_CONTRACT",
        "direct_outlined_v2",
    )
    changed = build_overlay_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )

    assert changed["sha256"] != current["sha256"]


def test_load_run_metadata_accepts_promoted_provenance_for_overlay_refresh(
    tmp_path,
):
    artwork = tmp_path / "artwork.png"
    Image.new("RGB", (10, 10), (20, 30, 40)).save(artwork)
    run = {
        "schema_version": 1,
        "kind": "poster_generation_run",
        "source_artwork": {"sha256": sha256_file(artwork)},
    }
    provenance_path = tmp_path / "poster-provenance.json"
    provenance_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "promoted_poster",
                "run": run,
            }
        ),
        encoding="utf-8",
    )

    assert load_run_metadata(provenance_path, artwork) == run


@pytest.mark.parametrize(
    "case",
    ["same_pixels", "changed_pixels", "wrong_output_hash", "missing_output", "new_run"],
)
def test_overlay_refresh_accepts_only_registered_pixel_identical_reencoding(
    tmp_path, case,
):
    original = tmp_path / "original.png"
    promoted = tmp_path / "promoted.png"
    image = Image.new("RGB", (10, 10), (20, 30, 40))
    image.save(original, compress_level=0)
    if case == "changed_pixels":
        image.putpixel((0, 0), (200, 30, 40))
    image.save(promoted, compress_level=9)
    assert sha256_file(original) != sha256_file(promoted)
    run = {
        "schema_version": 1,
        "kind": "poster_generation_run",
        "source_artwork": file_record(original, image=True),
    }
    output = file_record(promoted, image=True)
    if case == "wrong_output_hash":
        output["sha256"] = "0" * 64
    payload = {
        "schema_version": 1,
        "kind": "promoted_poster",
        "run": run,
        "outputs": {"artwork": output},
    }
    if case == "missing_output":
        payload.pop("outputs")
    elif case == "new_run":
        payload = run
    path = tmp_path / "provenance.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    if case == "same_pixels":
        assert load_run_metadata(path, promoted) == run
    else:
        with pytest.raises(ValueError):
            load_run_metadata(path, promoted)


def _promotion_fixture(
    tmp_path: Path,
    monkeypatch,
    *,
    output_megapixels: float | None = None,
    generation_override: dict | None = None,
):
    repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    if output_megapixels is not None and generation_override is not None:
        raise ValueError(
            "output_megapixels and generation_override are mutually exclusive"
        )
    if generation_override is not None:
        manifest = yaml.safe_load(
            bundle.manifest_path.read_text(encoding="utf-8")
        )
        manifest["artwork"]["generation"] = copy.deepcopy(
            generation_override
        )
        bundle.manifest_path.write_text(
            yaml.safe_dump(
                manifest,
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        bundle = poster_bundle("Example", poster_assets=assets)
    elif output_megapixels is None:
        manifest = yaml.safe_load(
            bundle.manifest_path.read_text(encoding="utf-8")
        )
        manifest["artwork"]["generation"]["output_dpi"] = 300
        bundle.manifest_path.write_text(
            yaml.safe_dump(
                manifest,
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        bundle = poster_bundle("Example", poster_assets=assets)
    if output_megapixels is not None:
        manifest = yaml.safe_load(
            bundle.manifest_path.read_text(encoding="utf-8")
        )
        generation = manifest["artwork"]["generation"]
        generation.pop("output_dpi")
        generation.pop("upscale_model")
        generation.pop("upscale_model_sha256")
        generation["output_method"] = "lanczos"
        generation["output_megapixels"] = output_megapixels
        bundle.manifest_path.write_text(
            yaml.safe_dump(
                manifest,
                sort_keys=False,
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
        bundle = poster_bundle("Example", poster_assets=assets)
    generation = bundle.manifest["artwork"]["generation"]
    layout = build_print_layout("standard_3x3", 10)
    candidate = repository / "candidate.png"
    Image.new(
        "RGB",
        (layout.width_px, layout.height_px),
        (40, 120, 80),
    ).save(candidate)

    work_dir = scope_dir / "comfyui_poster"
    workflow_path = work_dir / "workflow_api.json"

    monkeypatch.setattr(provenance, "POSTER_ASSETS", assets)
    monkeypatch.setattr(provenance, "SCOPE_DATA", output)
    monkeypatch.setattr(provenance, "ROOT", repository)
    generation_fingerprint = build_generation_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    overlay_fingerprint = build_overlay_fingerprint(
        bundle,
        poster_assets=assets,
        scope_data_dir=output,
    )
    scope_data = load_json(output / "Example.json")
    prompt_hash = hashlib.sha256(
        (build_identity_lock_prompt(bundle.manifest, scope_data) + "\n").encode(
            "utf-8"
        )
    ).hexdigest()
    run_metadata = tmp_path / "candidate.run.json"
    candidate_hash = sha256_file(candidate)
    cutout_payload = load_json(
        scope_dir / "cutouts" / "manifest.json"
    )
    cutout_records = [
        file_record(
            scope_dir / "cutouts" / item["file"],
            image=True,
        )
        for item in cutout_payload["items"]
    ]
    artwork_record = file_record(candidate, image=True)
    run_metadata.write_text(
        json.dumps(
            {
                    "schema_version": 1,
                    "kind": "poster_generation_run",
                    "scope": "Example",
                    "source_scope": "Example",
                    "poster_id": "Example",
                    "section_id": None,
                    "generation": bundle.manifest["artwork"]["generation"],
                    "inputs": {
                        "scope_manifest": file_record(
                            scope_dir / "poster.yaml"
                        ),
                        "prompt": {"sha256": prompt_hash},
                        "cutouts": cutout_records,
                        "generation_fingerprint": generation_fingerprint,
                        "overlay_fingerprint": overlay_fingerprint,
                        "source_pixel_audit_reference": {
                            "sha256": candidate_hash,
                            "width": layout.width_px,
                            "height": layout.height_px,
                        },
                    },
                    "source_artwork": artwork_record,
                    "raw_artwork": artwork_record,
                    "validation": {
                        "source_pixels": {
                            "method": "exact_opaque_source_pixels",
                            "opaque_pixels": 123,
                            "changed_pixels": 0,
                            "passed": True,
                            "stage": "raw_generation",
                            "reference_sha256": candidate_hash,
                            "artwork_sha256": candidate_hash,
                            "width": layout.width_px,
                            "height": layout.height_px,
                        }
                    },
            },
        ),
        encoding="utf-8",
    )

    def fake_finalize(_scope, source, destination, _language):
        save_options = {"format": "PNG"}
        if generation.get("output_dpi"):
            save_options["dpi"] = (
                generation["output_dpi"],
                generation["output_dpi"],
            )
        Image.open(source).convert("RGB").save(destination, **save_options)
        return destination

    def fake_slice(_scope, _source, output_dir):
        output_dir.mkdir(parents=True)
        paths = []
        for row in range(1, 4):
            for column in range(1, 4):
                cell = layout.cell(row, column)
                path = output_dir / f"card_r{row}_c{column}.png"
                card = Image.new(
                    "RGB",
                    (cell.width, cell.height),
                    (40, 120, 80),
                )
                save_options = {"format": "PNG"}
                if generation.get("output_dpi"):
                    save_options["dpi"] = (
                        generation["output_dpi"],
                        generation["output_dpi"],
                    )
                card.save(path, **save_options)
                paths.append(path)
        return paths

    monkeypatch.setattr(promotion, "POSTER_ASSETS", assets)
    monkeypatch.setattr(
        promotion,
        "build_generation_output_layout",
        lambda *_args, **_kwargs: layout,
    )
    monkeypatch.setattr(promotion, "finalize", fake_finalize)
    monkeypatch.setattr(promotion, "slice_poster", fake_slice)
    monkeypatch.setattr(validator, "POSTER_ASSETS", assets)
    monkeypatch.setattr(validator, "ROOT", repository)
    monkeypatch.setattr(
        validator,
        "build_generation_output_layout",
        lambda *_args, **_kwargs: layout,
    )
    monkeypatch.setattr(
        validator,
        "load_poster_scope_data",
        lambda _bundle: load_json(output / "Example.json"),
    )
    return (
        repository,
        assets,
        output,
        scope_dir,
        candidate,
        run_metadata,
        overlay_fingerprint,
    )


@pytest.mark.parametrize("reviewer_kind", ["human", "agent"])
def test_joint_scene_requires_review_then_promotes_and_validates(
    tmp_path,
    monkeypatch,
    reviewer_kind,
):
    generation = copy.deepcopy(_manifest()["artwork"]["generation"])
    generation.update(
        mode="joint_scene",
        reference_mode="spatial_identity_joint",
        output_method="lanczos",
        output_dpi=300,
    )
    for key in (
        "output_megapixels",
        "upscale_model",
        "upscale_model_sha256",
    ):
        generation.pop(key, None)
    (
        _repository,
        _assets,
        _output,
        _scope_dir,
        candidate,
        run_metadata,
        _overlay_fingerprint,
    ) = _promotion_fixture(
        tmp_path,
        monkeypatch,
        generation_override=generation,
    )

    with pytest.raises(ValueError, match="lacks explicit visual identity"):
        promotion.promote(
            "Example",
            candidate,
            run_metadata_path=run_metadata,
        )

    with pytest.raises(ValueError, match="reviewer kind"):
        promotion.promote(
            "Example", candidate, approve_joint_scene=True,
            run_metadata_path=run_metadata,
        )

    artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example",
        candidate,
        approve_joint_scene=True,
        reviewer_kind=reviewer_kind,
        run_metadata_path=run_metadata,
    )
    promoted = load_json(provenance_path)
    review = promoted["run"]["validation"][JOINT_SCENE_REVIEW_KEY]
    assert review["passed"] is True
    assert review["stage"] == "raw_and_text_free_print_artwork"

    result = validator.validate("Example")
    assert result["generation_fingerprint_current"] is True
    assert result["identity_validation_method"] == (
        f"{reviewer_kind}_identity_and_scene_review"
    )

    promoted["run"]["inputs"].pop("generation_fingerprint")
    promoted["run"]["source_artwork"]["sha256"] = sha256_file(artwork)
    provenance_path.write_text(json.dumps(promoted), encoding="utf-8")
    with pytest.raises(ValueError, match="cannot be legacy or unfingerprinted"):
        validator.validate("Example")
    with pytest.raises(ValueError, match="lacks its generation fingerprint"):
        promotion.promote(
            "Example",
            artwork,
            force=True,
            run_metadata_path=provenance_path,
        )


def test_promotion_rebinds_overlay_and_validator_prefers_fingerprints(
    tmp_path,
    monkeypatch,
):
    (
        _repository,
        _assets,
        _output,
        scope_dir,
        candidate,
        run_metadata,
        old_overlay,
    ) = _promotion_fixture(tmp_path, monkeypatch)

    manifest_path = scope_dir / "poster.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["text_cells"]["set_info"]["max_width_ratio"] = 0.81
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    _artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example",
        candidate,
        language="en",
        run_metadata_path=run_metadata,
    )
    promoted = load_json(provenance_path)
    generation_record = promoted["run"]["inputs"]["generation_fingerprint"]
    overlay_record = promoted["run"]["inputs"]["overlay_fingerprint"]
    assert fingerprint_record_is_valid(generation_record)
    assert fingerprint_record_is_valid(overlay_record)
    assert overlay_record["sha256"] != old_overlay["sha256"]

    current = validator.validate("Example")
    assert current["generation_fingerprint_current"] is True
    assert current["overlay_fingerprint_current"] is True

    manifest["pdf"]["enabled"] = False
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    routing_only = validator.validate("Example")
    assert routing_only["generation_fingerprint_current"] is True
    assert routing_only["overlay_fingerprint_current"] is True

    manifest["text_cells"]["set_info"]["max_width_ratio"] = 0.79
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    overlay_stale = validator.validate("Example")
    assert overlay_stale["generation_fingerprint_current"] is True
    assert overlay_stale["overlay_fingerprint_current"] is False

    manifest["text_cells"]["set_info"]["max_width_ratio"] = 0.81
    manifest["artwork"]["scene"]["concept"] = "a different generated scene"
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Generation input fingerprint drift"):
        validator.validate("Example")




def test_promotion_rejects_preview_output_without_300dpi_metadata(
    tmp_path,
    monkeypatch,
):
    (
        _repository,
        _assets,
        _output,
        _scope_dir,
        candidate,
        run_metadata,
        _old_overlay,
    ) = _promotion_fixture(
        tmp_path,
        monkeypatch,
        output_megapixels=0.01,
    )

    with pytest.raises(ValueError, match="exact 300-dpi print raster"):
        promotion.promote(
            "Example",
            candidate,
            language="en",
            run_metadata_path=run_metadata,
        )


def test_promotion_rejects_output_size_outside_generation_contract(
    tmp_path,
    monkeypatch,
):
    (
        _repository,
        _assets,
        _output,
        _scope_dir,
        candidate,
        run_metadata,
        _old_overlay,
    ) = _promotion_fixture(tmp_path, monkeypatch)
    Image.new("RGB", (79, 108), (40, 120, 80)).save(
        candidate,
        format="PNG",
        dpi=(10, 10),
    )
    payload = load_json(run_metadata)
    payload["source_artwork"]["sha256"] = sha256_file(candidate)
    run_metadata.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="Candidate output dimensions do not match",
    ):
        promotion.promote(
            "Example",
            candidate,
            language="en",
            run_metadata_path=run_metadata,
        )


def test_validator_accepts_audited_v1_inputs_without_calling_them_v2(
    tmp_path,
    monkeypatch,
):
    (
        _repository,
        assets,
        output,
        scope_dir,
        candidate,
        run_metadata,
        _old_overlay,
    ) = _promotion_fixture(tmp_path, monkeypatch)
    _artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example",
        candidate,
        language="en",
        run_metadata_path=run_metadata,
    )
    promoted = load_json(provenance_path)
    bundle = poster_bundle("Example", poster_assets=assets)
    promoted["run"]["inputs"]["generation_fingerprint"] = (
        build_generation_fingerprint(
            bundle,
            poster_assets=assets,
            scope_data_dir=output,
            pipeline_contract_version=1,
        )
    )
    provenance_path.write_text(json.dumps(promoted), encoding="utf-8")

    result = validator.validate("Example")

    assert result["generation_inputs_current"] is True
    assert result["generation_pipeline_contract_version"] == 1
    assert (
        result["generation_pipeline_contract_status"]
        == "accepted_legacy"
    )


def test_validator_rejects_an_unknown_pipeline_contract(
    tmp_path,
    monkeypatch,
):
    (
        _repository,
        assets,
        output,
        scope_dir,
        candidate,
        run_metadata,
        _old_overlay,
    ) = _promotion_fixture(tmp_path, monkeypatch)
    _artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example",
        candidate,
        language="en",
        run_metadata_path=run_metadata,
    )
    promoted = load_json(provenance_path)
    bundle = poster_bundle("Example", poster_assets=assets)
    unsupported_components = copy.deepcopy(
        promoted["run"]["inputs"]["generation_fingerprint"]["components"]
    )
    unsupported_components["pipeline_contract"]["version"] = 4
    promoted["run"]["inputs"]["generation_fingerprint"] = (
        provenance.fingerprint_record(unsupported_components)
    )
    provenance_path.write_text(json.dumps(promoted), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported generation pipeline"):
        validator.validate("Example")


def test_validator_rejects_durable_artwork_hash_drift(
    tmp_path,
    monkeypatch,
):
    (
        _repository,
        _assets,
        _output,
        _scope_dir,
        candidate,
        run_metadata,
        _old_overlay,
    ) = _promotion_fixture(tmp_path, monkeypatch)
    _artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example",
        candidate,
        language="en",
        run_metadata_path=run_metadata,
    )
    promoted = load_json(provenance_path)
    promoted["outputs"]["artwork"]["sha256"] = "0" * 64
    provenance_path.write_text(json.dumps(promoted), encoding="utf-8")

    with pytest.raises(ValueError, match="Hash mismatch"):
        validator.validate("Example")


def test_validator_keeps_legacy_full_manifest_fallback(tmp_path, monkeypatch):
    (
        _repository,
        _assets,
        _output,
        scope_dir,
        candidate,
        run_metadata,
        _old_overlay,
    ) = _promotion_fixture(tmp_path, monkeypatch)
    _artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example",
        candidate,
        language="en",
        run_metadata_path=run_metadata,
    )
    promoted = load_json(provenance_path)
    del promoted["run"]["inputs"]["generation_fingerprint"]
    del promoted["run"]["inputs"]["overlay_fingerprint"]
    provenance_path.write_text(json.dumps(promoted), encoding="utf-8")

    manifest_path = scope_dir / "poster.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["pdf"]["enabled"] = False
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Scope manifest drift"):
        validator.validate("Example")
