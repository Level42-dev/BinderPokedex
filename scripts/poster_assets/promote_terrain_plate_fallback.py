#!/usr/bin/env python3
"""Promote the operator-approved P16 terrain-plate composite without false one-shot metadata.

Only immutable hashes and the reviewed text-free master enter tracked assets.
The local jobs, source cutouts, and review crops remain in ignored workspaces.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import replace
from pathlib import Path

from PIL import Image

try:
    from .poster_io import poster_bundle, load_poster_scope_data
    from .fetch_cutouts import resolve_requested_count, select_pokemon
    from .layout import build_page_layout, build_source_layout
    from .composition import cutout_placements
    from .poster_subject import subject_fingerprint_identity
    from .provenance import build_overlay_fingerprint, image_pixel_record, sha256_file
    from .source_pixel_audit import audit_exact_source_pixels
    from .terrain_plate_fallback import METHOD, REVIEWED_P16_CUTOUTS
    from .validate_promoted_poster import validate
except ImportError:
    from poster_io import poster_bundle, load_poster_scope_data
    from fetch_cutouts import resolve_requested_count, select_pokemon
    from layout import build_page_layout, build_source_layout
    from composition import cutout_placements
    from poster_subject import subject_fingerprint_identity
    from provenance import build_overlay_fingerprint, image_pixel_record, sha256_file
    from source_pixel_audit import audit_exact_source_pixels
    from terrain_plate_fallback import METHOD, REVIEWED_P16_CUTOUTS
    from validate_promoted_poster import validate


ROOT = Path(__file__).resolve().parents[2]
TRIAL = ROOT / "tmp/isolated-repair-trials/p16-terrain-20261016-b"
EXPECTED_MASTER_SHA256 = "fb123a194a70c54f79e2ce1e247acda36bb97909e8d6a86f0107bee6d5bfa08d"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _stage(job_dir: Path, *, model_fields: tuple[str, ...]) -> dict:
    run_path = job_dir / "run.json"
    log_path = job_dir / "comfyui.log"
    workflow_path = job_dir / "workflow_api.json"
    job_path = job_dir / "job.json"
    run, job = _read_json(run_path), _read_json(job_path)
    if (
        not log_path.is_file() or not log_path.stat().st_size
        or run.get("workflow_sha256") != sha256_file(workflow_path)
        or job.get("workflow", {}).get("sha256") != sha256_file(workflow_path)
        or run.get("models") != job.get("models")
        or run.get("inputs") != job.get("inputs")
        or not isinstance(run.get("outputs"), list)
        or len(run["outputs"]) != 1
    ):
        raise ValueError("Incomplete or altered terrain-composite render job")
    for item in run["inputs"]:
        name = Path(item["path"]).name
        if name != item["path"] or sha256_file(job_dir / "input" / name) != item["sha256"]:
            raise ValueError("Altered terrain-composite render input")
    output = run["outputs"][0]
    output_path = job_dir / "output" / Path(output["path"]).name
    if sha256_file(output_path) != output["sha256"]:
        raise ValueError("Altered terrain-composite render output")
    model_hashes = {Path(item["path"]).name: item["sha256"] for item in run["models"]}
    if len(model_hashes) != len(model_fields):
        raise ValueError("Unexpected terrain-composite model inventory")
    return {
        "workflow_sha256": sha256_file(workflow_path),
        "run_sha256": sha256_file(run_path),
        "log_sha256": sha256_file(log_path),
        "output_sha256": output["sha256"],
        "models": model_hashes,
        "input_sha256": run["inputs"][0]["sha256"] if run["inputs"] else None,
    }


def _audit_exact_sources(bundle, raw_composite: Path, candidate: Path, evidence: dict) -> None:
    """Rebuild the reviewed source layout from pinned cutouts, not audit claims."""
    with Image.open(raw_composite) as image:
        raw_size = image.size
    if raw_size != (848, 1168):
        raise ValueError("P16 raw composite dimensions changed")
    placements = cutout_placements(
        build_source_layout("standard_3x3", width_px=848, height_px=1168),
        bundle.source_dir,
    )
    reference = Image.new("RGBA", raw_size, (226, 224, 211, 0))
    for placement in placements:
        reference.alpha_composite(placement["image"], (placement["x"], placement["y"]))
    with tempfile.TemporaryDirectory(prefix="p16-source-audit-") as temporary:
        source = Path(temporary) / "source.png"
        print_source = Path(temporary) / "print-source.png"
        reference.save(source)
        raw_audit = audit_exact_source_pixels(source, raw_composite, require_match=True)
        with Image.open(candidate) as image:
            print_size = image.size
        reference.resize(print_size, Image.Resampling.LANCZOS).save(print_source)
        print_audit = audit_exact_source_pixels(print_source, candidate, require_match=True)
    if raw_audit != evidence["source_pixel_audit"] or (
        print_audit["opaque_pixels"] != evidence["print_source_pixel_audit"]["opaque_source_pixels"]
        or print_audit["changed_pixels"] != evidence["print_source_pixel_audit"]["changed_opaque_source_pixels"]
    ):
        raise ValueError("P16 source-pixel evidence does not match independently rebuilt sources")


def _install_promoted_pair(bundle, candidate: Path, payload: dict) -> None:
    """Validate staged files and restore the prior pair if active validation fails."""
    output = bundle.asset_dir / bundle.artwork_file
    provenance = bundle.asset_dir / bundle.manifest["artwork"]["provenance_file"]
    bundle.asset_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".p16-promotion-", dir=bundle.asset_dir) as temporary:
        staging = Path(temporary)
        staged_output = staging / output.name
        staged_provenance = staging / provenance.name
        shutil.copy2(candidate, staged_output)
        staged_provenance.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        validate(replace(bundle, asset_dir=staging))
        prior = []
        for target in (output, provenance):
            backup = staging / f"prior-{target.name}"
            exists = target.is_file()
            if exists:
                shutil.copy2(target, backup)
            prior.append((target, backup, exists))
        try:
            os.replace(staged_output, output)
            os.replace(staged_provenance, provenance)
            validate(bundle)
        except Exception:
            for target, backup, exists in prior:
                if exists:
                    os.replace(backup, target)
                elif target.exists():
                    target.unlink()
            raise


def promote() -> dict:
    bundle = poster_bundle("ExGen2/sections/primal")
    if bundle.manifest.get("artwork", {}).get("fallback_method") != METHOD:
        raise ValueError("P16 fallback is not explicitly configured")
    candidate = TRIAL / "review/artwork-300dpi.png"
    evidence = _read_json(TRIAL / "review/evidence.json")
    if (
        sha256_file(candidate) != EXPECTED_MASTER_SHA256
        or evidence["print_master"]["sha256"] != EXPECTED_MASTER_SHA256
        or evidence["source_pixel_audit"].get("changed_pixels") != 0
        or evidence["print_source_pixel_audit"].get("changed_opaque_source_pixels") != 0
        or len(evidence.get("cards", [])) != 9
    ):
        raise ValueError("P16 master or exact-source review evidence changed")
    for card in evidence["cards"]:
        path = ROOT / card["path"]
        if sha256_file(path) != card["sha256"]:
            raise ValueError(f"P16 reviewed card changed: {path.name}")
    terrain_dir = next((TRIAL / "retrieved").glob("terrain-*"))
    upscale_dir = next((TRIAL / "retrieved").glob("upscale-*"))
    terrain = _stage(terrain_dir, model_fields=("model", "encoder", "vae"))
    upscale = _stage(upscale_dir, model_fields=("upscale_model",))
    model_hashes = terrain["models"]
    generation = bundle.manifest["artwork"]["generation"]
    if (
        model_hashes.get(generation["model"]) != generation["model_sha256"]
        or model_hashes.get(generation["encoder"]) != generation["encoder_sha256"]
        or model_hashes.get(generation["vae"]) != generation["vae_sha256"]
        or upscale["input_sha256"] != terrain["output_sha256"]
        or terrain["output_sha256"] != evidence["terrain_plate"]["sha256"]
        or upscale["output_sha256"] != evidence["upscaled_terrain"]["sha256"]
        or sha256_file(ROOT / evidence["raw_composite"]["path"])
        != evidence["raw_composite"]["sha256"]
    ):
        raise ValueError("P16 render stages do not match pinned evidence")

    source_manifest = _read_json(bundle.source_dir / "cutouts/manifest.json")
    scope_data = load_poster_scope_data(bundle)
    layout = build_page_layout(bundle.manifest["layout"]["name"])
    selected = select_pokemon(
        bundle.manifest, scope_data,
        resolve_requested_count(bundle.manifest, layout), {},
    )
    subjects = [subject_fingerprint_identity(item) for item in selected]
    source_items = source_manifest["items"]
    if [subject_fingerprint_identity(item) for item in source_items] != subjects:
        raise ValueError("P16 cached source subjects differ from current selection")
    cutouts = []
    for item, (expected_name, expected_hash, expected_pixels) in zip(
        source_items, REVIEWED_P16_CUTOUTS, strict=True,
    ):
        path = bundle.source_dir / "cutouts" / item["file"]
        if (
            path.name != expected_name
            or sha256_file(path) != expected_hash
            or image_pixel_record(path)["pixel_sha256"] != expected_pixels
        ):
            raise ValueError("P16 source cutout differs from independently reviewed source")
        cutouts.append({
            "file": path.name,
            "sha256": expected_hash,
            "pixel_sha256": expected_pixels,
        })
    _audit_exact_sources(bundle, ROOT / evidence["raw_composite"]["path"], candidate, evidence)

    with Image.open(candidate) as image:
        dpi = image.info.get("dpi")
        if not dpi or any(abs(float(value) - 300) > 0.1 for value in dpi):
            raise ValueError("P16 approved master lacks 300-dpi metadata")
        width, height = image.size
    payload = {
        "schema_version": 4,
        "kind": "promoted_poster",
        "scope": bundle.asset_key,
        "source_scope": bundle.scope,
        "poster_id": bundle.poster_id,
        "section_id": bundle.section_id,
        "method": METHOD,
        "artwork": {
            "sha256": EXPECTED_MASTER_SHA256,
            "pixel_sha256": image_pixel_record(candidate)["pixel_sha256"],
            "width": width, "height": height, "dpi": 300,
        },
        "source_subject_ids": subjects,
        "source_cutouts": cutouts,
        "render": {
            "terrain": {
                "workflow_sha256": terrain["workflow_sha256"],
                "run_sha256": terrain["run_sha256"],
                "log_sha256": terrain["log_sha256"],
                "output_sha256": terrain["output_sha256"],
                "model_sha256": generation["model_sha256"],
                "encoder_sha256": generation["encoder_sha256"],
                "vae_sha256": generation["vae_sha256"],
            },
            "upscale": {
                "workflow_sha256": upscale["workflow_sha256"],
                "run_sha256": upscale["run_sha256"],
                "log_sha256": upscale["log_sha256"],
                "input_sha256": upscale["input_sha256"],
                "output_sha256": upscale["output_sha256"],
                "model_sha256": next(iter(upscale["models"].values())),
            },
        },
        "composition": {
            "terrain_plate_sha256": evidence["terrain_plate"]["sha256"],
            "upscaled_terrain_sha256": evidence["upscaled_terrain"]["sha256"],
            "raw_composite_sha256": evidence["raw_composite"]["sha256"],
            "source_pixel_audit": evidence["source_pixel_audit"],
            "print_source_pixel_audit": evidence["print_source_pixel_audit"],
        },
        "review": {
            "decision": "operator_accepted_2026-10-16",
            "artwork_sha256": EXPECTED_MASTER_SHA256,
            "card_sha256": [item["sha256"] for item in evidence["cards"]],
        },
        "overlay_fingerprint_sha256": build_overlay_fingerprint(bundle)["sha256"],
    }
    _install_promoted_pair(bundle, candidate, payload)
    return payload


if __name__ == "__main__":
    promoted = promote()
    print(f"Promoted {promoted['scope']}: {promoted['artwork']['sha256']}")
