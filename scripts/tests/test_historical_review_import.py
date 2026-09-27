"""Behavioral gates for importing the two accepted historical poster runs."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _png(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (12, 16), color).save(path)


def _fixture(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    from scripts.poster_assets import historical_review_import as importer

    root = tmp_path
    archive = root / "assets/reviewed-candidates/base1-b"
    trial = root / "tmp/oneshot-trials/base1-b"
    job_dir = trial / "retrieved/one-job"
    source_paths = [root / f"tmp/poster-workspaces/Base1/sources/cutouts/source-{n}.png" for n in range(3)]
    for n, path in enumerate(source_paths):
        _png(path, ("red", "green", "blue")[n])
    master = archive / "artwork-300dpi.png"
    raw = job_dir / "output/raw.png"
    _png(master, "white")
    _png(raw, "black")
    prompt = job_dir / "source-detail-prompt.txt"
    workflow = job_dir / "workflow_api.json"
    job = job_dir / "job.json"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("Exact old scene prompt", encoding="utf-8")
    _json(workflow, {
        "1": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 12, "height": 16}},
        "2": {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}},
    })
    models = [
        {"path": f"{directory}/{name}", "sha256": digit * 64}
        for directory, name, digit in (
            ("diffusion_models", "flux.safetensors", "a"),
            ("text_encoders", "qwen.safetensors", "b"),
            ("vae", "vae.safetensors", "c"),
        )
    ]
    _json(job, {"format_version": 1, "models": models, "inputs": []})
    generation = {
        "engine": "flux", "mode": "joint_scene", "reference_mode": "spatial_identity_joint",
        "generation_megapixels": 2.0, "output_dpi": 300, "output_method": "lanczos",
        "seed": 42, "steps": 4,
        "model": "flux.safetensors", "model_sha256": "a" * 64,
        "encoder": "qwen.safetensors", "encoder_sha256": "b" * 64,
        "vae": "vae.safetensors", "vae_sha256": "c" * 64,
    }
    _json(job_dir / "run.json", {
        "format_version": 1,
        "hostname": "secret-worker-host",
        "machine": "private machine details",
        "workflow_sha256": _sha(workflow),
        "models": models,
        "inputs": [],
        "outputs": [{"path": "raw.png", "sha256": _sha(raw)}],
    })
    evidence = {
        "scope": "Base1", "variant": "base1-b",
        "master": {"path": str(master.relative_to(root)), "sha256": _sha(master)},
        "raw": {"path": str(raw.relative_to(root)), "sha256": _sha(raw)},
        "print_dimensions": [12, 16],
        "original_sources": [
            {"path": str(path.relative_to(root)), "sha256": _sha(path)} for path in source_paths
        ],
    }
    evidence_path = trial / "review/evidence.json"
    _json(evidence_path, evidence)
    report = root / "docs/reviews/base1-review.json"
    _json(report, {"scope": "Base1", "status": "accepted"})
    _json(archive / "review-provenance.json", {
        "scope": "Base1",
        "master": {"file": str(master.relative_to(root)), "sha256": _sha(master)},
        "original_review_report": {"file": str(report.relative_to(root)), "sha256": _sha(report)},
        "original_review_decision": {
            "reviewer_kind": "human", "decision": "visual_candidate_accepted",
            "candidate": "base1-b", "accepted_master_sha256": _sha(master),
        },
        "reviewed_original_sources": evidence["original_sources"],
    })
    experiment = {
        "scope": "Base1", "variant": "base1-b",
        "canonical_promotion_eligible": False,
        "experimental_prompt_override": True,
        "generation": generation,
        "review": {"path": str(evidence_path.relative_to(root)), "sha256": _sha(evidence_path)},
        "original_sources": evidence["original_sources"],
        "returned_job": str(job_dir.relative_to(root)),
        "jobs": {"oneshot": {"manifest_sha256": _sha(job), "package": {
            "job.json": _sha(job),
            "workflow_api.json": _sha(workflow),
            "source-detail-prompt.txt": _sha(prompt),
        }}},
    }
    _json(trial / "experiment.json", experiment)
    candidates = root / "config/posters/historical_review_candidates.json"
    _json(candidates, {"schema_version": 1, "candidates": [{
        "scope": "Base1", "candidate_id": "base1-b",
        "generation": generation,
        "master_path": str(master.relative_to(root)),
        "master_sha256": _sha(master),
        "review_report_sha256": _sha(report),
        "job_sha256": _sha(job),
        "workflow_sha256": _sha(workflow),
        "prompt_sha256": _sha(prompt),
        "raw_sha256": _sha(raw),
        "review_evidence_sha256": _sha(evidence_path),
    }]})
    monkeypatch.setattr(importer, "ROOT", root)
    monkeypatch.setattr(importer, "CANDIDATES_PATH", candidates)
    return archive, trial


def test_missing_original_job_is_read_only(tmp_path, monkeypatch):
    from scripts.poster_assets.historical_review_import import verify_historical_trial

    archive, trial = _fixture(tmp_path, monkeypatch)
    (trial / "retrieved/one-job/job.json").unlink()
    before = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
    with pytest.raises((FileNotFoundError, ValueError), match="job"):
        verify_historical_trial("Base1", archive, trial)
    assert sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*")) == before


def test_changed_master_pixels_are_rejected(tmp_path, monkeypatch):
    from scripts.poster_assets.historical_review_import import verify_historical_trial

    archive, trial = _fixture(tmp_path, monkeypatch)
    _png(archive / "artwork-300dpi.png", "yellow")
    with pytest.raises(ValueError, match="master"):
        verify_historical_trial("Base1", archive, trial)


@pytest.mark.parametrize("field,value", [("seed", 43), ("model_sha256", "d" * 64)])
def test_scope_seed_and_model_mismatch_rejected(tmp_path, monkeypatch, field, value):
    from scripts.poster_assets.historical_review_import import verify_historical_trial

    archive, trial = _fixture(tmp_path, monkeypatch)
    experiment_path = trial / "experiment.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    experiment["generation"][field] = value
    _json(experiment_path, experiment)
    with pytest.raises(ValueError, match="generation|seed|model"):
        verify_historical_trial("Base1", archive, trial)


@pytest.mark.parametrize("field,value", [
    ("steps", 7),
    ("reference_mode", "other_mode"),
    ("generation_megapixels", 1.0),
    ("output_dpi", 150),
])
def test_unpinned_historical_generation_settings_are_rejected(tmp_path, monkeypatch, field, value):
    from scripts.poster_assets.historical_review_import import verify_historical_trial

    archive, trial = _fixture(tmp_path, monkeypatch)
    experiment_path = trial / "experiment.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    experiment["generation"][field] = value
    _json(experiment_path, experiment)
    with pytest.raises(ValueError, match="generation"):
        verify_historical_trial("Base1", archive, trial)


def test_verified_evidence_omits_private_run_fields(tmp_path, monkeypatch):
    from scripts.poster_assets.historical_review_import import verify_historical_trial

    archive, trial = _fixture(tmp_path, monkeypatch)
    evidence = verify_historical_trial("Base1", archive, trial)
    assert evidence["candidate_id"] == "base1-b"
    assert evidence["generation"]["seed"] == 42
    assert len(evidence["sources"]) == 3
    assert "secret-worker-host" not in json.dumps(evidence)
    assert "private machine details" not in json.dumps(evidence)


def test_older_trial_without_review_pointer_uses_allowlisted_evidence(tmp_path, monkeypatch):
    from scripts.poster_assets.historical_review_import import verify_historical_trial

    archive, trial = _fixture(tmp_path, monkeypatch)
    experiment_path = trial / "experiment.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    del experiment["review"]
    _json(experiment_path, experiment)
    assert verify_historical_trial("Base1", archive, trial)["candidate_id"] == "base1-b"


def test_historical_contract_is_allowlisted(tmp_path, monkeypatch):
    from scripts.poster_assets.historical_review_import import (
        require_historical_import, verify_historical_trial,
    )

    archive, trial = _fixture(tmp_path, monkeypatch)
    evidence = verify_historical_trial("Base1", archive, trial)
    bundle = SimpleNamespace(asset_key="Base1", manifest={"artwork": {"generation": evidence["generation"]}})
    run = {
        "scope": "Base1", "generation": evidence["generation"],
        "source_artwork": {"sha256": evidence["master"]["sha256"]},
        "historical_import": {"schema_version": 1, "contract_name": "approved_spatial_identity_joint_import", "pipeline_version": 8, **evidence},
        "inputs": {"generation_fingerprint": {"components": {"effective_prompt": {
            "sha256": evidence["prompt_sha256"],
        }, "pipeline_contract": {"name": "poster_generation", "version": 8}}}},
    }
    require_historical_import(bundle, run)
    run["historical_import"]["candidate_id"] = "unreviewed"
    with pytest.raises(ValueError, match="historical|allowlist|candidate"):
        require_historical_import(bundle, run)


def test_historical_generation_cannot_change_in_run_and_manifest_together(tmp_path, monkeypatch):
    from scripts.poster_assets.historical_review_import import (
        require_historical_import, verify_historical_trial,
    )

    archive, trial = _fixture(tmp_path, monkeypatch)
    evidence = verify_historical_trial("Base1", archive, trial)
    altered = deepcopy(evidence["generation"])
    altered["steps"] = 7
    bundle = SimpleNamespace(asset_key="Base1", manifest={"artwork": {"generation": altered}})
    run = {
        "scope": "Base1", "generation": altered,
        "source_artwork": {"sha256": evidence["master"]["sha256"]},
        "historical_import": {
            "schema_version": 1,
            "contract_name": "approved_spatial_identity_joint_import",
            "pipeline_version": 8,
            **evidence,
            "generation": altered,
        },
        "inputs": {"generation_fingerprint": {"components": {
            "effective_prompt": {"sha256": evidence["prompt_sha256"]},
            "pipeline_contract": {"name": "poster_generation", "version": 8},
        }}},
    }
    with pytest.raises(ValueError, match="historical generation"):
        require_historical_import(bundle, run)


def test_original_prompt_hash_is_revalidated(tmp_path, monkeypatch):
    from scripts.poster_assets.historical_review_import import (
        require_historical_import, verify_historical_trial,
    )

    archive, trial = _fixture(tmp_path, monkeypatch)
    evidence = verify_historical_trial("Base1", archive, trial)
    bundle = SimpleNamespace(asset_key="Base1", manifest={"artwork": {"generation": evidence["generation"]}})
    run = {
        "scope": "Base1", "generation": evidence["generation"],
        "source_artwork": {"sha256": evidence["master"]["sha256"]},
        "historical_import": {"schema_version": 1, "contract_name": "approved_spatial_identity_joint_import", "pipeline_version": 8, **evidence},
        "inputs": {"generation_fingerprint": {"components": {"effective_prompt": {
            "sha256": "e" * 64,
        }, "pipeline_contract": {"name": "poster_generation", "version": 8}}}},
    }
    with pytest.raises(ValueError, match="prompt"):
        require_historical_import(bundle, run)


def test_modern_promotion_remains_unchanged(tmp_path, monkeypatch):
    from scripts.poster_assets.historical_review_import import require_historical_import

    _fixture(tmp_path, monkeypatch)
    bundle = SimpleNamespace(asset_key="Other", manifest={"artwork": {"generation": {
        "mode": "joint_scene", "reference_mode": "individual_spatial_joint",
        "generation_megapixels": 1.0,
    }}})
    require_historical_import(bundle, {"scope": "Other", "generation": bundle.manifest["artwork"]["generation"]})


def test_historical_run_promotes_without_claiming_current_graph(tmp_path, monkeypatch):
    from scripts.poster_assets import poster_io, provenance
    from scripts.poster_assets.historical_review_import import write_historical_run_metadata

    archive, trial = _fixture(tmp_path, monkeypatch)
    experiment = json.loads((trial / "experiment.json").read_text(encoding="utf-8"))
    source_dir = tmp_path / "tmp/poster-workspaces/Base1/sources"
    _json(source_dir / "cutouts/manifest.json", {"items": [
        {"file": item["path"].split("/")[-1]} for item in experiment["original_sources"]
    ]})
    manifest_path = tmp_path / "config/posters/Base1/poster.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("scope: Base1\n", encoding="utf-8")
    bundle = SimpleNamespace(
        asset_key="Base1", scope="Base1", poster_id="Base1", section_id=None,
        manifest={"artwork": {"generation": experiment["generation"]}},
        source_dir=source_dir, manifest_path=manifest_path,
    )
    monkeypatch.setattr(poster_io, "poster_bundle", lambda scope: bundle)
    monkeypatch.setattr(provenance, "build_generation_fingerprint", lambda *_args, **_kwargs:
                        provenance.fingerprint_record({"pipeline_contract": {
                            "name": "poster_generation", "version": 8,
                        }, "effective_prompt": {"sha256": "0" * 64}}))
    monkeypatch.setattr(provenance, "build_overlay_fingerprint", lambda *_args, **_kwargs:
                        provenance.fingerprint_record({"overlay": "synthetic"}))
    output = tmp_path / "tmp/historical.run.json"
    write_historical_run_metadata("Base1", archive, trial, output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["kind"] == "poster_generation_run"
    assert payload["historical_import"]["historical_flags"] == {
        "canonical_promotion_eligible": False, "experimental_prompt_override": True,
    }
    assert payload["inputs"]["generation_fingerprint"]["components"]["pipeline_contract"]["version"] == 8
    assert payload["inputs"]["generation_fingerprint"]["components"]["effective_prompt"]["sha256"] == experiment["jobs"]["oneshot"]["package"]["source-detail-prompt.txt"]
