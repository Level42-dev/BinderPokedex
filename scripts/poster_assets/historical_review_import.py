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

try:
    from .generation_contract import HISTORICAL_SPATIAL_IDENTITY_JOINT_PIPELINE_VERSION
except ImportError:
    from generation_contract import HISTORICAL_SPATIAL_IDENTITY_JOINT_PIPELINE_VERSION


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


def require_historical_import(
    bundle: Any, run: dict[str, Any], *, verify_original_files: bool = False,
) -> None:
    """Revalidate the durable historical audit without private worker files.

    Only the two archived candidates can enter this path. Other generations
    retain the existing ordinary promotion/fingerprint checks unchanged.
    """
    scope = bundle.asset_key
    allowed_items = [
        item for item in _read(CANDIDATES_PATH, "historical candidate allowlist")["candidates"]
        if item["scope"] == scope
    ]
    if len(allowed_items) > 1:
        raise ValueError("ambiguous historical import allowlist")
    historical = run.get("historical_import")
    generation = bundle.manifest.get("artwork", {}).get("generation")
    if historical is None:
        if allowed_items and (
            generation.get("reference_mode") == "spatial_identity_joint"
            and generation.get("generation_megapixels") == 2.0
        ):
            raise ValueError("historical import is required for this reviewed contract")
        return
    if len(allowed_items) != 1 or not isinstance(historical, dict):
        raise ValueError("historical import is not allowlisted for this scope")
    allowed = allowed_items[0]
    if (historical.get("schema_version") != 1
            or historical.get("contract_name") != "approved_spatial_identity_joint_import"
            or historical.get("pipeline_version") != HISTORICAL_SPATIAL_IDENTITY_JOINT_PIPELINE_VERSION
            or historical.get("scope") != scope):
        raise ValueError("historical import contract or scope mismatch")
    if run.get("scope") != scope or run.get("generation") != generation or historical.get("generation") != generation:
        raise ValueError("historical generation differs from active manifest")
    if historical.get("candidate_id") != allowed["candidate_id"]:
        raise ValueError("historical candidate differs from allowlist")
    if historical.get("historical_flags") != {
        "canonical_promotion_eligible": False,
        "experimental_prompt_override": True,
    }:
        raise ValueError("historical experiment flags were lost")
    for key, allowed_key in (
        ("job_sha256", "job_sha256"),
        ("workflow_sha256", "workflow_sha256"),
        ("prompt_sha256", "prompt_sha256"),
        ("review_report_sha256", "review_report_sha256"),
    ):
        if historical.get(key) != allowed[allowed_key]:
            raise ValueError(f"historical {key} differs from allowlist")
    if historical.get("master") != {
        "path": allowed["master_path"], "sha256": allowed["master_sha256"],
    } or run.get("source_artwork", {}).get("sha256") != allowed["master_sha256"]:
        raise ValueError("historical master differs from accepted artwork")
    if historical.get("raw", {}).get("sha256") != allowed["raw_sha256"]:
        raise ValueError("historical raw render differs from original job")
    sources = historical.get("sources")
    if not isinstance(sources, list) or len(sources) != 3:
        raise ValueError("historical three-source record is incomplete")
    archive_dir = _inside_root(allowed["master_path"], "historical master").parent
    archive = _read(archive_dir / "review-provenance.json", "archived review provenance")
    if sources != archive.get("reviewed_original_sources"):
        raise ValueError("historical source hashes differ from accepted review")
    prompt = run.get("inputs", {}).get("generation_fingerprint", {}).get("components", {}).get("effective_prompt", {})
    if prompt.get("sha256") != allowed["prompt_sha256"]:
        raise ValueError("historical prompt hash differs from original job")
    pipeline = run.get("inputs", {}).get("generation_fingerprint", {}).get("components", {}).get("pipeline_contract", {})
    if pipeline != {"name": "poster_generation", "version": HISTORICAL_SPATIAL_IDENTITY_JOINT_PIPELINE_VERSION}:
        raise ValueError("historical generation fingerprint contract mismatch")
    if verify_original_files:
        original_trial = historical.get("original_trial")
        if not isinstance(original_trial, str):
            raise ValueError("historical original trial path missing")
        current = verify_historical_trial(
            scope, archive_dir, _inside_root(original_trial, "original trial"),
        )
        for key, value in current.items():
            if historical.get(key) != value:
                raise ValueError(f"historical {key} differs from original files")


def write_historical_run_metadata(
    scope: str, archive_dir: Path, trial_dir: Path, output_path: Path,
) -> Path:
    """Write a normal generation sidecar for exactly one verified old trial."""
    try:
        from .poster_io import poster_bundle
        from .provenance import (
            build_generation_fingerprint, build_overlay_fingerprint,
            file_record, fingerprint_record,
        )
    except ImportError:
        from poster_io import poster_bundle
        from provenance import (
            build_generation_fingerprint, build_overlay_fingerprint,
            file_record, fingerprint_record,
        )

    evidence = verify_historical_trial(scope, archive_dir, trial_dir)
    bundle = poster_bundle(scope)
    if bundle.asset_key != scope or bundle.manifest["artwork"]["generation"] != evidence["generation"]:
        raise ValueError("historical generation is not the active scope contract")
    experiment = _read(trial_dir / "experiment.json", "original experiment")
    job_dir = _inside_root(experiment["returned_job"], "returned job")
    master_path = _inside_root(evidence["master"]["path"], "master")
    raw_path = _inside_root(evidence["raw"]["path"], "raw render")
    prompt_path = job_dir / "source-detail-prompt.txt"
    workflow_path = job_dir / "workflow_api.json"
    cutout_dir = bundle.source_dir / "cutouts"
    cutout_manifest = _read(cutout_dir / "manifest.json", "cutout manifest")
    cutouts = [file_record(cutout_dir / item["file"], image=True) for item in cutout_manifest["items"]]
    source_hashes = [item["sha256"] for item in evidence["sources"]]
    if [item["sha256"] for item in cutouts] != source_hashes:
        raise ValueError("current cutout files differ from reviewed original sources")
    job = _read(job_dir / "job.json", "job")
    references = [file_record(job_dir / "input" / item["path"], image=True) for item in job["inputs"]]
    fingerprint = build_generation_fingerprint(
        bundle, generation=evidence["generation"],
        pipeline_contract_version=HISTORICAL_SPATIAL_IDENTITY_JOINT_PIPELINE_VERSION,
    )
    components = fingerprint["components"]
    components["effective_prompt"] = {"encoding": "utf-8", "sha256": evidence["prompt_sha256"]}
    fingerprint = fingerprint_record(components)
    run = {
        "schema_version": 1,
        "kind": "poster_generation_run",
        "scope": scope,
        "source_scope": bundle.scope,
        "poster_id": bundle.poster_id,
        "section_id": bundle.section_id,
        "generation": evidence["generation"],
        "source_artwork": file_record(master_path, image=True),
        "raw_artwork": file_record(raw_path, image=True),
        "inputs": {
            "scope_manifest": file_record(bundle.manifest_path),
            "prompt": file_record(prompt_path),
            "workflow": file_record(workflow_path),
            "cutout_manifest": file_record(cutout_dir / "manifest.json"),
            "cutouts": cutouts,
            "references": references,
            "generation_fingerprint": fingerprint,
            "overlay_fingerprint": build_overlay_fingerprint(bundle),
        },
        "historical_import": {
            "schema_version": 1,
            "contract_name": "approved_spatial_identity_joint_import",
            "pipeline_version": HISTORICAL_SPATIAL_IDENTITY_JOINT_PIPELINE_VERSION,
            "original_trial": str(trial_dir.resolve().relative_to(ROOT.resolve())),
            **evidence,
        },
    }
    require_historical_import(bundle, run, verify_original_files=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(run, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output_path
