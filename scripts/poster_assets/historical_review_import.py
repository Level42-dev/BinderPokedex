"""Read-only verification of explicitly accepted, archived poster experiments.

This module deliberately does not make an experimental run canonical.  It only
proves that the locally retained bytes still match the narrowly allowlisted
human-review decision and the original render job.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
CANDIDATES_PATH = ROOT / "config/posters/historical_review_candidates.json"


def _read(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid {label}")
    return value


def _digest(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError(f"{label} hash mismatch")
    return digest


def _inside_root(value: str, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError(f"invalid {label} path")
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError(f"unsafe {label} path")
    return path


def _record(record: dict[str, Any], label: str) -> dict[str, str]:
    path = _inside_root(record["path"], label)
    digest = _digest(path, record["sha256"], label)
    return {"path": str(path.relative_to(ROOT.resolve())), "sha256": digest}


def _models(models: list[dict[str, str]], generation: dict[str, Any]) -> None:
    required = {
        f"diffusion_models/{generation['model']}": generation["model_sha256"],
        f"text_encoders/{generation['encoder']}": generation["encoder_sha256"],
        f"vae/{generation['vae']}": generation["vae_sha256"],
    }
    present = {entry["path"]: entry["sha256"] for entry in models}
    if present != required:
        raise ValueError("generation model hashes differ from original job")


def _workflow_generation(workflow: dict[str, Any], generation: dict[str, Any]) -> None:
    nodes = {node.get("class_type"): node.get("inputs", {}) for node in workflow.values()}
    checks = (
        ("RandomNoise", "noise_seed", generation["seed"]),
        ("UNETLoader", "unet_name", generation["model"]),
        ("CLIPLoader", "clip_name", generation["encoder"]),
        ("VAELoader", "vae_name", generation["vae"]),
    )
    if "RandomNoise" not in nodes:
        raise ValueError("generation seed node missing")
    for kind, field, expected in checks:
        if kind in nodes and nodes[kind].get(field) != expected:
            raise ValueError(f"generation {kind}.{field} mismatch")


def verify_historical_trial(scope: str, archive_dir: Path, trial_dir: Path) -> dict[str, Any]:
    """Validate all original bytes and return only portable, public evidence."""
    allowlist = _read(CANDIDATES_PATH, "historical candidate allowlist")
    if allowlist.get("schema_version") != 1:
        raise ValueError("unsupported historical candidate allowlist")
    candidates = [item for item in allowlist.get("candidates", []) if item.get("scope") == scope]
    if len(candidates) != 1:
        raise ValueError("scope is not uniquely allowlisted for historical import")
    allowed = candidates[0]
    archive = _read(archive_dir / "review-provenance.json", "archived review provenance")
    experiment = _read(trial_dir / "experiment.json", "original experiment")
    evidence_record = experiment.get("review")
    evidence_path = (trial_dir / "review/evidence.json").resolve()
    if not evidence_path.is_relative_to(trial_dir.resolve()):
        raise ValueError("unsafe trial evidence path")
    if evidence_record is not None:
        if _inside_root(evidence_record["path"], "trial evidence") != evidence_path:
            raise ValueError("trial evidence path mismatch")
        if evidence_record["sha256"] != allowed["review_evidence_sha256"]:
            raise ValueError("trial evidence hash differs from allowlist")
    _digest(evidence_path, allowed["review_evidence_sha256"], "trial evidence")
    evidence = _read(evidence_path, "trial evidence")
    candidate_id = allowed["candidate_id"]
    if (experiment.get("scope"), experiment.get("variant")) != (scope, candidate_id):
        raise ValueError("scope or candidate does not match allowlist")
    if (evidence.get("scope"), evidence.get("variant")) != (scope, candidate_id):
        raise ValueError("trial evidence scope or candidate mismatch")
    if archive.get("scope") != scope or archive["original_review_decision"].get("candidate") != candidate_id:
        raise ValueError("human review scope or candidate mismatch")
    if archive["original_review_decision"].get("decision") != "visual_candidate_accepted":
        raise ValueError("human review was not an acceptance")
    if experiment.get("canonical_promotion_eligible") is not False or experiment.get("experimental_prompt_override") is not True:
        raise ValueError("historical generation flags were changed")

    master = _record({"path": archive["master"]["file"], "sha256": archive["master"]["sha256"]}, "master")
    if master["sha256"] != allowed["master_sha256"] or master["sha256"] != evidence["master"]["sha256"]:
        raise ValueError("master does not match approved candidate")
    if archive["original_review_decision"].get("accepted_master_sha256") != master["sha256"]:
        raise ValueError("master differs from human review")
    with Image.open(_inside_root(master["path"], "master")) as image:
        if list(image.size) != evidence["print_dimensions"]:
            raise ValueError("master print dimensions differ")
    report = archive["original_review_report"]
    report_path = _inside_root(report["file"], "review report")
    _digest(report_path, report["sha256"], "review report")
    if report["sha256"] != allowed["review_report_sha256"]:
        raise ValueError("review report mismatch")

    job_dir = _inside_root(experiment["returned_job"], "returned job")
    if not job_dir.is_relative_to(trial_dir.resolve()):
        raise ValueError("returned job lies outside the trial")
    package = experiment["jobs"]["oneshot"]["package"]
    for name, expected_hash in package.items():
        path = (job_dir / name).resolve()
        if not path.is_relative_to(job_dir):
            raise ValueError("unsafe job package path")
        _digest(path, expected_hash, f"job {name}")
    if package["job.json"] != experiment["jobs"]["oneshot"]["manifest_sha256"]:
        raise ValueError("job manifest mismatch")
    for name, field in (("job.json", "job_sha256"), ("workflow_api.json", "workflow_sha256"), ("source-detail-prompt.txt", "prompt_sha256")):
        if package[name] != allowed[field]:
            raise ValueError(f"job {name} differs from allowlist")
    job = _read(job_dir / "job.json", "job")
    workflow = _read(job_dir / "workflow_api.json", "workflow")
    run = _read(job_dir / "run.json", "render run")
    if run.get("workflow_sha256") != package["workflow_api.json"]:
        raise ValueError("run workflow mismatch")
    if run.get("models") != job.get("models") or run.get("inputs") != job.get("inputs"):
        raise ValueError("render run differs from job inputs or models")
    for item in job.get("inputs", []):
        name = item["path"]
        if package.get(f"input/{name}") != item["sha256"]:
            raise ValueError("job input differs from package")
    generation = experiment["generation"]
    _models(job["models"], generation)
    _workflow_generation(workflow, generation)
    raw = _record(evidence["raw"], "raw render")
    if raw["sha256"] != allowed["raw_sha256"]:
        raise ValueError("raw render differs from allowlist")
    if archive["original_review_decision"].get("related_raw_sha256") not in (None, raw["sha256"]):
        raise ValueError("raw render differs from human review")
    if not any(item.get("sha256") == raw["sha256"] for item in run.get("outputs", [])):
        raise ValueError("raw render absent from original run")
    sources = [_record(item, "source") for item in experiment["original_sources"]]
    if len(sources) != 3 or sources != evidence["original_sources"] or sources != archive["reviewed_original_sources"]:
        raise ValueError("three original sources differ from review")
    return {
        "scope": scope,
        "candidate_id": candidate_id,
        "historical_flags": {"canonical_promotion_eligible": False, "experimental_prompt_override": True},
        "generation": dict(generation),
        "master": master,
        "raw": raw,
        "sources": sources,
        "job_sha256": package["job.json"],
        "workflow_sha256": package["workflow_api.json"],
        "prompt_sha256": package["source-detail-prompt.txt"],
        "review_report_sha256": report["sha256"],
        "print_dimensions": list(evidence["print_dimensions"]),
    }
