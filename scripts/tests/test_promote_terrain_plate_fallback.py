"""Promotion must verify inputs and never strand a half-installed asset pair."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from scripts.poster_assets import promote_terrain_plate_fallback as promotion
from scripts.poster_assets.poster_io import poster_bundle
from scripts.poster_assets.provenance import sha256_file


def test_terrain_stage_rejects_a_changed_render_input(tmp_path):
    job = tmp_path / "job"
    (job / "input").mkdir(parents=True)
    (job / "output").mkdir()
    workflow = job / "workflow_api.json"
    workflow.write_text("{}", encoding="utf-8")
    (job / "comfyui.log").write_text("completed", encoding="utf-8")
    input_path = job / "input" / "source.png"
    output_path = job / "output" / "render.png"
    input_path.write_bytes(b"reviewed input")
    output_path.write_bytes(b"rendered output")
    models = [{"path": "model.safetensors", "sha256": "a" * 64}]
    inputs = [{"path": "source.png", "sha256": sha256_file(input_path)}]
    run = {
        "workflow_sha256": sha256_file(workflow), "models": models,
        "inputs": inputs,
        "outputs": [{"path": "render.png", "sha256": sha256_file(output_path)}],
    }
    job_record = {
        "workflow": {"sha256": sha256_file(workflow)},
        "models": models, "inputs": inputs,
    }
    (job / "run.json").write_text(json.dumps(run), encoding="utf-8")
    (job / "job.json").write_text(json.dumps(job_record), encoding="utf-8")
    assert promotion._stage(job, model_fields=("model",))["input_sha256"] == inputs[0]["sha256"]
    input_path.write_bytes(b"tampered input")
    with pytest.raises(ValueError, match="render input"):
        promotion._stage(job, model_fields=("model",))


def test_p16_pair_install_restores_old_files_when_active_validation_fails(tmp_path, monkeypatch):
    bundle = replace(poster_bundle("ExGen2/sections/primal"), asset_dir=tmp_path)
    artwork = tmp_path / bundle.artwork_file
    provenance = tmp_path / bundle.manifest["artwork"]["provenance_file"]
    artwork.write_bytes(b"old artwork")
    provenance.write_bytes(b"old provenance")
    candidate = tmp_path / "candidate.png"
    candidate.write_bytes(b"new artwork")
    calls = []

    def validate_pair(target):
        calls.append(target.asset_dir)
        if target.asset_dir == tmp_path:
            raise ValueError("active validation failed")

    monkeypatch.setattr(promotion, "validate", validate_pair)
    with pytest.raises(ValueError, match="active validation failed"):
        promotion._install_promoted_pair(bundle, candidate, {"new": True})
    assert len(calls) == 2
    assert artwork.read_bytes() == b"old artwork"
    assert provenance.read_bytes() == b"old provenance"
