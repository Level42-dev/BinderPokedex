"""The reviewed landscape-plate fallback must never masquerade as a one-shot."""
from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from scripts.poster_assets.provenance import image_pixel_record, sha256_file
from scripts.poster_assets.terrain_plate_fallback import (
    REVIEWED_P16_CUTOUTS,
    validate_terrain_fallback,
)


HASH = "a" * 64
OTHER_HASH = "b" * 64
SUBJECTS = [{"pokemon_id": 382}, {"pokemon_id": 383}]


def _fixture(tmp_path: Path):
    asset = tmp_path / "poster-flux2-artwork.png"
    Image.new("RGB", (2368, 3268), "#223344").save(asset, dpi=(300, 300))
    config = {
        "artwork": {
            "promoted_file": asset.name,
            "fallback_method": "terrain_plate_exact_source_composite",
            "generation": {
                "model_sha256": HASH,
                "encoder_sha256": HASH,
                "vae_sha256": HASH,
                "output_dpi": 300,
            },
        },
        "layout": {"name": "standard_3x3"},
    }
    bundle = SimpleNamespace(
        asset_key="ExGen2/sections/primal", scope="ExGen2",
        poster_id="primal", section_id="primal", asset_dir=tmp_path,
        source_dir=tmp_path / "sources", manifest=config, pdf_enabled=True,
        artwork_file=asset.name,
    )
    record = {
        "schema_version": 4, "kind": "promoted_poster",
        "scope": bundle.asset_key, "source_scope": bundle.scope,
        "poster_id": bundle.poster_id, "section_id": bundle.section_id,
        "method": "terrain_plate_exact_source_composite",
        "artwork": {
            "sha256": sha256_file(asset),
            "pixel_sha256": image_pixel_record(asset)["pixel_sha256"],
            "width": 2368, "height": 3268, "dpi": 300,
        },
        "source_subject_ids": SUBJECTS,
        "source_cutouts": [
            {"file": name, "sha256": digest, "pixel_sha256": pixels}
            for name, digest, pixels in REVIEWED_P16_CUTOUTS
        ],
        "render": {
            "terrain": {"workflow_sha256": HASH, "run_sha256": HASH,
                        "log_sha256": HASH, "output_sha256": HASH,
                        "model_sha256": HASH, "encoder_sha256": HASH,
                        "vae_sha256": HASH},
            "upscale": {"workflow_sha256": HASH, "run_sha256": HASH,
                        "log_sha256": HASH, "input_sha256": HASH,
                        "output_sha256": OTHER_HASH, "model_sha256": HASH},
        },
        "composition": {
            "terrain_plate_sha256": HASH,
            "upscaled_terrain_sha256": OTHER_HASH,
            "raw_composite_sha256": HASH,
            "source_pixel_audit": {"method": "exact_opaque_source_pixels",
                                   "opaque_pixels": 24992, "changed_pixels": 0},
            "print_source_pixel_audit": {"opaque_source_pixels": 188227,
                                         "changed_opaque_source_pixels": 0},
        },
        "review": {"decision": "operator_accepted_2026-10-16",
                   "artwork_sha256": sha256_file(asset),
                   "card_sha256": [HASH] * 9},
        "overlay_fingerprint_sha256": HASH,
    }
    return bundle, record


def test_terrain_fallback_accepts_exact_reviewed_master(tmp_path):
    bundle, record = _fixture(tmp_path)
    result = validate_terrain_fallback(bundle, record, SUBJECTS, HASH)
    assert result["composition_kind"] == "terrain_plate_exact_source_composite"


@pytest.mark.parametrize("field,value", [
    ("method", "joint_scene"),
    ("source_subject_ids", [{"pokemon_id": 382}]),
    ("overlay_fingerprint_sha256", OTHER_HASH),
])
def test_terrain_fallback_rejects_contract_drift(tmp_path, field, value):
    bundle, record = _fixture(tmp_path)
    record[field] = value
    with pytest.raises(ValueError):
        validate_terrain_fallback(bundle, record, SUBJECTS, HASH)


def test_terrain_fallback_rejects_altered_master_or_fake_source_audit(tmp_path):
    bundle, record = _fixture(tmp_path)
    record["artwork"]["sha256"] = OTHER_HASH
    with pytest.raises(ValueError):
        validate_terrain_fallback(bundle, record, SUBJECTS, HASH)


def test_terrain_fallback_rejects_a_different_source_cutout_even_without_cache(tmp_path):
    bundle, record = _fixture(tmp_path)
    record["source_cutouts"][0]["sha256"] = "c" * 64
    with pytest.raises(ValueError):
        validate_terrain_fallback(bundle, record, SUBJECTS, HASH)
    record["artwork"]["sha256"] = record["review"]["artwork_sha256"]
    record["composition"]["print_source_pixel_audit"]["changed_opaque_source_pixels"] = 1
    with pytest.raises(ValueError):
        validate_terrain_fallback(bundle, record, SUBJECTS, HASH)
