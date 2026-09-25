import copy
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from PIL import Image

from scripts.poster_assets import finalize_comfyui_poster as finalizer
from scripts.poster_assets import masked_fallback
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
    image_pixel_record,
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


def test_month_override_changes_overlay_but_not_generation_fingerprint(tmp_path):
    _repository, assets, output, _scope_dir, bundle = _write_fixture(tmp_path)
    source_path = output / "Example.json"
    source = load_json(source_path)
    source["release_date"] = "1999-06-16"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    original_overlay = build_overlay_fingerprint(bundle, poster_assets=assets, scope_data_dir=output)
    original_generation = build_generation_fingerprint(bundle, poster_assets=assets, scope_data_dir=output)
    manifest = copy.deepcopy(bundle.manifest)
    manifest["text_content"] = {
        "mode": "set_summary",
        "release_date_overrides": {"de": {"value": "2000-06", "precision": "month"}},
    }
    changed = _with_manifest(bundle, manifest)
    changed_overlay = build_overlay_fingerprint(changed, poster_assets=assets, scope_data_dir=output)
    changed_generation = build_generation_fingerprint(changed, poster_assets=assets, scope_data_dir=output)
    assert changed_overlay["sha256"] != original_overlay["sha256"]
    assert changed_overlay["components"]["languages"]["de"]["information"][-1] == "Juni 2000"
    assert changed_overlay["components"]["languages"]["en"]["information"][-1] == "June 16, 1999"
    assert changed_generation["sha256"] == original_generation["sha256"]


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


def _masked_promotion_fixture(tmp_path: Path, monkeypatch):
    generation = copy.deepcopy(_manifest()["artwork"]["generation"])
    generation.update(
        mode="joint_scene", reference_mode="spatial_identity_joint",
        output_method="lanczos", output_dpi=300,
    )
    for key in ("output_megapixels", "upscale_model", "upscale_model_sha256"):
        generation.pop(key, None)
    repository, assets, output, scope_dir, base_artwork, old_run, _ = _promotion_fixture(
        tmp_path, monkeypatch, generation_override=generation,
    )
    monkeypatch.setattr(masked_fallback, "ROOT", repository, raising=False)
    monkeypatch.setattr(masked_fallback, "build_generation_output_layout", lambda *_args: build_print_layout("standard_3x3", 10))
    manifest = yaml.safe_load((scope_dir / "poster.yaml").read_text(encoding="utf-8"))
    manifest["title_logo"] = {"files": {"de": "logo.png"}}
    manifest["pdf"]["enabled"] = False
    (scope_dir / "poster.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    base_run = repository / "base.run.json"
    shutil.copy2(old_run, base_run)
    layout = build_print_layout("standard_3x3", 10)
    base = Image.open(base_artwork).convert("RGB")
    final = base.copy()
    repair_inputs = []
    for name, column, color in (("pikachu", 1, (200, 30, 20)), ("eevee", 3, (20, 30, 200))):
        cell = layout.cell(3, column)
        point = (cell.x + 1, cell.y + 1)
        repair = base.copy()
        repair.putpixel(point, color)
        final.putpixel(point, color)
        job_dir = repository / "tmp" / f"{name}-job"
        (job_dir / "input").mkdir(parents=True)
        (job_dir / "output").mkdir()
        mask = Image.new("RGBA", (cell.width, cell.height), (0, 0, 0, 255))
        mask.putpixel((1, 1), (0, 0, 0, 0))
        mask_path = job_dir / "input" / "repair-mask.png"
        mask.save(mask_path)
        original_path = job_dir / "input" / "original-card-padded.png"
        base.crop((cell.x, cell.y, cell.x + cell.width, cell.y + cell.height)).save(original_path)
        bounded_path = job_dir / "output" / "bounded.png"
        repair.crop((cell.x, cell.y, cell.x + cell.width, cell.y + cell.height)).save(bounded_path)
        workflow_path = job_dir / "workflow_api.json"
        workflow_path.write_text("{}", encoding="utf-8")
        input_records = [
            {"path": "original-card-padded.png", "sha256": sha256_file(original_path)},
            {"path": "repair-mask.png", "sha256": sha256_file(mask_path)},
        ]
        model_records = [
            {"path": generation[key], "sha256": generation[f"{key}_sha256"]}
            for key in ("model", "encoder", "vae")
        ]
        job = {
            "inputs": input_records, "models": model_records,
            "workflow": {"path": "workflow_api.json", "sha256": sha256_file(workflow_path)},
        }
        (job_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")
        run = {
            "inputs": input_records, "models": model_records,
            "workflow_sha256": sha256_file(workflow_path),
            "outputs": [{"path": "bounded.png", "sha256": sha256_file(bounded_path)}],
        }
        (job_dir / "run.json").write_text(json.dumps(run), encoding="utf-8")
        (job_dir / "comfyui.log").write_text("render completed\n", encoding="utf-8")
        repair_path = repository / f"{name}-repair.png"
        repair.save(repair_path, dpi=(300, 300))
        evidence_path = repository / f"{name}-evidence.json"
        evidence_path.write_text(json.dumps({
            "master": {"sha256": sha256_file(repair_path)},
            "pixel_audit": {"editable_pixels": 1, "changed_editable_pixels": 1,
                            "changed_outside_mask_pixels": 0},
        }), encoding="utf-8")
        repair_inputs.append({
            "reason": f"foreground {name}", "row": 3, "column": column,
            "padding_origin": "top_left",
            "bounded_output": "bounded.png",
            "mask": mask_path.relative_to(repository).as_posix(),
            "artwork": repair_path.relative_to(repository).as_posix(),
            "job_dir": job_dir.relative_to(repository).as_posix(),
            "evidence": evidence_path.relative_to(repository).as_posix(),
            "approval_mask_key": f"{name}_repair_mask_sha256",
            "approval_evidence_key": f"{name}_repair_evidence_sha256",
            "expected_sha256": {
                "run": sha256_file(job_dir / "run.json"),
                "job": sha256_file(job_dir / "job.json"),
                "log": sha256_file(job_dir / "comfyui.log"),
                "bounded_output": sha256_file(bounded_path),
                "mask": sha256_file(mask_path),
                "artwork": sha256_file(repair_path),
                "evidence": sha256_file(evidence_path),
            },
        })
    final_path = repository / "accepted-h.png"
    final.save(final_path, dpi=(300, 300))
    old_preview = repository / "old-preview.png"
    final.save(old_preview)
    base_evidence = repository / "base-evidence.json"
    base_evidence.write_text(json.dumps({"master": {"sha256": sha256_file(base_artwork)}}), encoding="utf-8")
    combined_evidence = repository / "combined-evidence.json"
    combined_evidence.write_text(json.dumps({
        "master": {"sha256": sha256_file(final_path)},
        "combined_pixel_audit": {"editable_pixels": 2, "changed_editable_pixels": 2,
                                 "changed_outside_mask_pixels": 0},
    }), encoding="utf-8")
    review_path = repository / "assets" / "review-pending" / "example-h" / "review-provenance.json"
    review_path.parent.mkdir(parents=True)
    review = {
        "scope": "Example", "candidate": "H",
        "artwork_sha256": sha256_file(final_path),
        "one_shot_master_sha256": sha256_file(base_artwork),
        "one_shot_trial_evidence_sha256": sha256_file(base_evidence),
        "combined_review_evidence_sha256": sha256_file(combined_evidence),
        "pixel_audit": {"editable_pixels": 2, "changed_editable_pixels": 2,
                        "changed_outside_mask_pixels": 0},
        "human_approval": "text_free_artwork_accepted_2026-09-25",
        "title_logo_approval": {
            "status": "accepted_2026-09-25",
            "logo_sha256": sha256_file(scope_dir / "logo.png"),
            "german_preview_sha256": sha256_file(old_preview),
        },
        "localized_overlay_approval": "pending",
    }
    for item in repair_inputs:
        review[item["approval_mask_key"]] = sha256_file(repository / item["mask"])
        review[item["approval_evidence_key"]] = sha256_file(repository / item["evidence"])
    review_path.write_text(json.dumps(review), encoding="utf-8")
    input_path = repository / "promotion-input.json"
    input_path.write_text(json.dumps({
        "schema_version": 1, "kind": "masked_fallback",
        "base_run": base_run.relative_to(repository).as_posix(),
        "base_artwork": base_artwork.relative_to(repository).as_posix(),
        "base_evidence": base_evidence.relative_to(repository).as_posix(),
        "combined_evidence": combined_evidence.relative_to(repository).as_posix(),
        "review_provenance": review_path.relative_to(repository).as_posix(),
        "accepted_logo_preview": old_preview.relative_to(repository).as_posix(),
        "repairs": repair_inputs,
    }), encoding="utf-8")
    return SimpleNamespace(
        repository=repository, assets=assets, scope_dir=scope_dir,
        base_run=base_run, base_artwork=base_artwork, final=final_path,
        input=input_path, review=review_path, old_preview=old_preview,
        repair_inputs=repair_inputs,
        base_sha256=sha256_file(base_artwork),
    )


def test_masked_promotion_records_distinct_one_shot_and_accepted_final(tmp_path, monkeypatch):
    fixture = _masked_promotion_fixture(tmp_path, monkeypatch)
    artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example", fixture.final, language="de",
        run_metadata_path=fixture.base_run,
        composition_input_path=fixture.input,
    )
    stored = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert stored["schema_version"] == 3
    assert stored["run"]["source_artwork"]["sha256"] == fixture.base_sha256
    assert stored["composition"]["kind"] == "masked_fallback"
    assert stored["composition"]["final_artwork_sha256"] == sha256_file(fixture.final)
    assert stored["outputs"]["artwork"]["sha256"] == sha256_file(fixture.final)
    assert stored["outputs"]["artwork"]["pixel_sha256"] == image_pixel_record(artwork)["pixel_sha256"]
    result = validator.validate("Example")
    assert result["identity_validation_method"] == "human_masked_fallback_review"
    assert result["localized_overlay_approved"] is False


def test_masked_promotion_rejects_changed_accepted_logo_preview_before_replacement(tmp_path, monkeypatch):
    fixture = _masked_promotion_fixture(tmp_path, monkeypatch)
    artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example", fixture.final, language="de",
        run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
    )
    stable_hash = sha256_file(artwork)
    stable_provenance = provenance_path.read_bytes()
    with Image.open(fixture.old_preview) as loaded:
        changed = loaded.copy()
    changed.putpixel((0, 0), (1, 2, 3))
    changed.save(fixture.old_preview)
    with pytest.raises(ValueError, match="logo preview"):
        promotion.promote(
            "Example", fixture.final, language="de", force=True,
            run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
        )
    assert sha256_file(artwork) == stable_hash
    assert provenance_path.read_bytes() == stable_provenance


def test_masked_validation_and_overlay_refresh_need_no_ignored_render_jobs(tmp_path, monkeypatch):
    fixture = _masked_promotion_fixture(tmp_path, monkeypatch)
    artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example", fixture.final, language="de",
        run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
    )
    accepted_h_sha = sha256_file(artwork)
    original = json.loads(provenance_path.read_text(encoding="utf-8"))
    shutil.rmtree(fixture.repository / "tmp")
    for path in (fixture.base_run, fixture.base_artwork, fixture.final, fixture.old_preview):
        path.unlink()
    assert validator.validate("Example")["localized_overlay_approved"] is False
    manifest_path = fixture.scope_dir / "poster.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["text_cells"]["set_info"]["max_width_ratio"] = 0.85
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    assert validator.validate("Example")["overlay_fingerprint_current"] is False
    promotion.promote(
        "Example", artwork, language="de", force=True,
        run_metadata_path=provenance_path,
    )
    refreshed = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert sha256_file(artwork) == accepted_h_sha
    assert refreshed["run"]["source_artwork"]["sha256"] == fixture.base_sha256
    assert refreshed["composition"]["outside_base_pixel_sha256"] == original["composition"]["outside_base_pixel_sha256"]
    assert refreshed["composition"]["overlay_fingerprint_sha256"] != original["composition"]["overlay_fingerprint_sha256"]
    assert validator.validate("Example")["overlay_fingerprint_current"] is True


def test_masked_promotion_rejects_mutated_job_metadata_before_replacement(tmp_path, monkeypatch):
    fixture = _masked_promotion_fixture(tmp_path, monkeypatch)
    artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example", fixture.final, language="de",
        run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
    )
    stable_provenance = provenance_path.read_bytes()
    job_dir = fixture.repository / fixture.repair_inputs[0]["job_dir"]
    job_path = job_dir / "job.json"
    job = json.loads(job_path.read_text(encoding="utf-8"))
    job["irrelevant_annotation"] = "unreviewed replacement"
    job_path.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ValueError, match="job hash"):
        promotion.promote(
            "Example", fixture.final, language="de", force=True,
            run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
        )
    assert provenance_path.read_bytes() == stable_provenance
    assert sha256_file(artwork) == sha256_file(fixture.final)


def test_masked_promotion_rejects_false_repair_pixel_evidence(tmp_path, monkeypatch):
    fixture = _masked_promotion_fixture(tmp_path, monkeypatch)
    artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example", fixture.final, language="de",
        run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
    )
    stable_provenance = provenance_path.read_bytes()
    repair_input = fixture.repair_inputs[0]
    evidence_path = fixture.repository / repair_input["evidence"]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    evidence["pixel_audit"]["changed_editable_pixels"] = 0
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    promotion_input = json.loads(fixture.input.read_text(encoding="utf-8"))
    promotion_input["repairs"][0]["expected_sha256"]["evidence"] = sha256_file(evidence_path)
    fixture.input.write_text(json.dumps(promotion_input), encoding="utf-8")
    review = json.loads(fixture.review.read_text(encoding="utf-8"))
    review[repair_input["approval_evidence_key"]] = sha256_file(evidence_path)
    fixture.review.write_text(json.dumps(review), encoding="utf-8")
    with pytest.raises(ValueError, match="Repair pixel audit"):
        promotion.promote(
            "Example", fixture.final, language="de", force=True,
            run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
        )
    assert provenance_path.read_bytes() == stable_provenance
    assert sha256_file(artwork) == sha256_file(fixture.final)


@pytest.mark.parametrize(
    ("damage", "message"),
    [
        ("missing_log", "comfyui.log"),
        ("human_approval", "human approval"),
        ("generation_seed", "generation does not match"),
        ("outside_repair", "outside"),
    ],
)
def test_masked_promotion_failures_preserve_existing_master(
    tmp_path, monkeypatch, damage, message,
):
    fixture = _masked_promotion_fixture(tmp_path, monkeypatch)
    artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example", fixture.final, language="de",
        run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
    )
    original_artwork = artwork.read_bytes()
    original_provenance = provenance_path.read_bytes()
    if damage == "missing_log":
        (fixture.repository / fixture.repair_inputs[0]["job_dir"] / "comfyui.log").unlink()
    elif damage == "human_approval":
        review = json.loads(fixture.review.read_text(encoding="utf-8"))
        review["human_approval"] = "pending"
        fixture.review.write_text(json.dumps(review), encoding="utf-8")
    elif damage == "generation_seed":
        manifest_path = fixture.scope_dir / "poster.yaml"
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest["artwork"]["generation"]["seed"] += 1
        manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    else:
        repair_input = fixture.repair_inputs[0]
        repair_path = fixture.repository / repair_input["artwork"]
        with Image.open(repair_path) as loaded:
            changed = loaded.copy()
        changed.putpixel((0, 0), (41, 120, 80))
        changed.save(repair_path, dpi=(300, 300))
        evidence_path = fixture.repository / repair_input["evidence"]
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["master"]["sha256"] = sha256_file(repair_path)
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        promotion_input = json.loads(fixture.input.read_text(encoding="utf-8"))
        promotion_input["repairs"][0]["expected_sha256"]["artwork"] = sha256_file(repair_path)
        promotion_input["repairs"][0]["expected_sha256"]["evidence"] = sha256_file(evidence_path)
        fixture.input.write_text(json.dumps(promotion_input), encoding="utf-8")
        review = json.loads(fixture.review.read_text(encoding="utf-8"))
        review[repair_input["approval_evidence_key"]] = sha256_file(evidence_path)
        fixture.review.write_text(json.dumps(review), encoding="utf-8")
    with pytest.raises((ValueError, FileNotFoundError), match=message):
        promotion.promote(
            "Example", fixture.final, language="de", force=True,
            run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
        )
    assert artwork.read_bytes() == original_artwork
    assert provenance_path.read_bytes() == original_provenance


def test_masked_validator_detects_single_outside_pixel_after_reencoding(tmp_path, monkeypatch):
    fixture = _masked_promotion_fixture(tmp_path, monkeypatch)
    artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example", fixture.final, language="de",
        run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
    )
    with Image.open(artwork) as loaded:
        changed = loaded.convert("RGB")
    changed.putpixel((0, 0), (41, 120, 80))
    changed.save(artwork, dpi=(300, 300), optimize=True)
    stored = json.loads(provenance_path.read_text(encoding="utf-8"))
    current = file_record(artwork, image=True)
    stored["outputs"]["artwork"].update(current)
    stored["composition"]["final_artwork_sha256"] = current["sha256"]
    stored["composition"]["final_artwork_pixel_sha256"] = current["pixel_sha256"]
    provenance_path.write_text(json.dumps(stored), encoding="utf-8")
    with pytest.raises(ValueError, match="outside repair masks"):
        validator.validate("Example")


def test_masked_pdf_gate_needs_exact_human_overlay_hashes(tmp_path, monkeypatch):
    fixture = _masked_promotion_fixture(tmp_path, monkeypatch)
    _artwork, _preview, _cards, provenance_path = promotion.promote(
        "Example", fixture.final, language="de",
        run_metadata_path=fixture.base_run, composition_input_path=fixture.input,
    )
    manifest_path = fixture.scope_dir / "poster.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["pdf"]["enabled"] = True
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="localized overlay approval"):
        validator.validate("Example")
    stored = json.loads(provenance_path.read_text(encoding="utf-8"))
    composition = stored["composition"]
    composition["localized_overlay_approval"] = {
        "status": "accepted", "reviewer_kind": "human",
        "preview_sha256": "0" * 64,
        "overlay_fingerprint_sha256": composition["overlay_fingerprint_sha256"],
    }
    provenance_path.write_text(json.dumps(stored), encoding="utf-8")
    with pytest.raises(ValueError, match="localized overlay approval"):
        validator.validate("Example")
    composition["localized_overlay_approval"]["preview_sha256"] = composition["preview_sha256"]
    provenance_path.write_text(json.dumps(stored), encoding="utf-8")
    assert validator.validate("Example")["localized_overlay_approved"] is True


def test_poster_promotion_direct_script_help_remains_available():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(root / "scripts/poster_assets/promote_comfyui_poster.py"), "--help"],
        cwd=root, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--composition-input" in result.stdout


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
