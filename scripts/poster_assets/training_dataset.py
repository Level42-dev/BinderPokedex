#!/usr/bin/env python3
"""Audit and materialize paired poster artwork edit-training data."""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, ImageChops, ImageStat

try:
    from .poster_io import POSTER_ASSETS, poster_bundle
    from .prepare_comfyui_poster import build_identity_lock_references
    from .provenance import image_pixel_record, sha256_file
    from .source_pixel_audit import audit_exact_source_pixels
except ImportError:
    from poster_io import POSTER_ASSETS, poster_bundle
    from prepare_comfyui_poster import build_identity_lock_references
    from provenance import image_pixel_record, sha256_file
    from source_pixel_audit import audit_exact_source_pixels


ROOT = Path(__file__).resolve().parents[2]
AUDIT_FORMAT_VERSION = 1
PAIR_STATUSES = frozenset(
    {
        "candidate_pair_review",
        "needs_fresh_exact_input",
        "needs_target_review",
        "blocked_missing_target",
        "excluded_target",
        "rejected_input",
        "rejected_pair",
        "gold",
    }
)


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def safe_repo_path(value: object, *, root: Path, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty repository-relative path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"{field} must be a safe repository-relative path")
    path = root.joinpath(*pure.parts).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"{field} leaves the repository")
    return path


def relative_path(path: Path, *, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def immutable_image_record(path: Path, *, root: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as loaded:
        rgb = loaded.convert("RGB")
        stddev = [round(float(value), 4) for value in ImageStat.Stat(rgb).stddev]
    return {
        "file": relative_path(path, root=root),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        **image_pixel_record(path),
        "channel_stddev": stddev,
    }


def compose_aligned_teacher_target(
    edited_scene_path: Path,
    source_reference_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Restore exact positioned subjects over an AI-integrated teacher scene."""
    edited_scene_path = edited_scene_path.resolve()
    source_reference_path = source_reference_path.resolve()
    output_path = output_path.resolve()
    if output_path.exists():
        raise FileExistsError(
            f"Immutable teacher target already exists: {output_path}"
        )

    with Image.open(edited_scene_path) as opened_scene:
        scene = opened_scene.convert("RGBA")
    with Image.open(source_reference_path) as opened_reference:
        if "A" not in opened_reference.getbands():
            raise ValueError("Source reference must contain an alpha channel")
        source = opened_reference.convert("RGBA")
    if scene.size != source.size:
        raise ValueError(
            "Teacher scene and source reference dimensions differ: "
            f"{scene.size} != {source.size}"
        )
    if source.getchannel("A").getbbox() is None:
        raise ValueError("Source reference contains no visible subject pixels")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(scene, source).convert("RGB").save(
        output_path,
        format="PNG",
        optimize=True,
    )
    source_audit = audit_exact_source_pixels(
        source_reference_path,
        output_path,
        require_match=True,
    )
    return {
        "kind": "aligned_teacher_target",
        "edited_scene_sha256": sha256_file(edited_scene_path),
        "source_reference_sha256": sha256_file(source_reference_path),
        "output_sha256": sha256_file(output_path),
        "width": scene.width,
        "height": scene.height,
        "source_pixel_audit": source_audit,
    }


def compose_foreground_occlusion_target(
    edited_scene_path: Path,
    source_reference_path: Path,
    foreground_layer_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Restore exact subjects, then apply one explicit foreground layer."""
    edited_scene_path = edited_scene_path.resolve()
    source_reference_path = source_reference_path.resolve()
    foreground_layer_path = foreground_layer_path.resolve()
    output_path = output_path.resolve()
    if output_path.exists():
        raise FileExistsError(
            f"Immutable occlusion target already exists: {output_path}"
        )

    with Image.open(edited_scene_path) as opened_scene:
        scene = opened_scene.convert("RGBA")
    with Image.open(source_reference_path) as opened_reference:
        if "A" not in opened_reference.getbands():
            raise ValueError("Source reference must contain an alpha channel")
        source = opened_reference.convert("RGBA")
    with Image.open(foreground_layer_path) as opened_foreground:
        if "A" not in opened_foreground.getbands():
            raise ValueError("Foreground layer must contain an alpha channel")
        foreground = opened_foreground.convert("RGBA")
    if len({scene.size, source.size, foreground.size}) != 1:
        raise ValueError("Scene, source reference, and foreground dimensions differ")
    if source.getchannel("A").getbbox() is None:
        raise ValueError("Source reference contains no visible subject pixels")
    if foreground.getchannel("A").getbbox() is None:
        raise ValueError("Foreground layer contains no visible pixels")

    restored = Image.alpha_composite(scene, source)
    output = Image.alpha_composite(restored, foreground).convert("RGB")
    source_rgb = source.convert("RGB")
    difference = ImageChops.difference(output, source_rgb)
    source_alpha = source.getchannel("A")
    foreground_alpha = foreground.getchannel("A")
    opaque_source_pixels = 0
    intentionally_covered_pixels = 0
    changed_uncovered_pixels = 0
    source_alpha_bytes = source_alpha.tobytes()
    foreground_alpha_bytes = foreground_alpha.tobytes()
    difference_bytes = difference.tobytes()
    for index, (source_a, foreground_a) in enumerate(
        zip(source_alpha_bytes, foreground_alpha_bytes, strict=True)
    ):
        if source_a != 255:
            continue
        opaque_source_pixels += 1
        if foreground_a:
            intentionally_covered_pixels += 1
        elif difference_bytes[index * 3 : index * 3 + 3] != b"\0\0\0":
            changed_uncovered_pixels += 1
    if intentionally_covered_pixels == 0:
        raise ValueError("Foreground layer does not cover an opaque source pixel")
    if changed_uncovered_pixels:
        raise ValueError(
            "Uncovered opaque source pixels changed: "
            f"{changed_uncovered_pixels}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path, format="PNG", optimize=True)
    uncovered_pixels = opaque_source_pixels - intentionally_covered_pixels
    return {
        "kind": "foreground_occlusion_target",
        "edited_scene_sha256": sha256_file(edited_scene_path),
        "source_reference_sha256": sha256_file(source_reference_path),
        "foreground_layer_sha256": sha256_file(foreground_layer_path),
        "output_sha256": sha256_file(output_path),
        "width": scene.width,
        "height": scene.height,
        "source_pixel_audit": {
            "passed": True,
            "opaque_source_pixels": opaque_source_pixels,
            "intentionally_covered_opaque_pixels": intentionally_covered_pixels,
            "uncovered_opaque_pixels": uncovered_pixels,
            "exact_uncovered_opaque_pixels": uncovered_pixels,
            "changed_uncovered_opaque_pixels": 0,
        },
    }


def validate_image_contract(
    record: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    contract = config["image_contract"]
    errors = []
    width = record.get("width")
    height = record.get("height")
    if (width, height) != (contract["width"], contract["height"]):
        errors.append(
            f"expected {contract['width']}x{contract['height']}, got {width}x{height}"
        )
    divisor = int(contract["divisible_by"])
    if (
        not isinstance(width, int)
        or not isinstance(height, int)
        or width % divisor
        or height % divisor
    ):
        errors.append(f"dimensions must be divisible by {divisor}")
    stddev = record.get("channel_stddev", [])
    minimum = float(contract["minimum_channel_stddev"])
    if not isinstance(stddev, list) or max(stddev, default=0.0) < minimum:
        errors.append("image is blank or effectively constant")
    return errors


def asset_key_for_provenance(path: Path, *, poster_assets: Path) -> str:
    return path.parent.resolve().relative_to(poster_assets.resolve()).as_posix()


def target_path_from_provenance(provenance: dict[str, Any], *, root: Path) -> Path:
    run = provenance.get("run")
    if not isinstance(run, dict):
        raise ValueError("Promoted provenance has no generation run")
    raw = run.get("raw_artwork")
    if not isinstance(raw, dict):
        raise ValueError("Promoted provenance has no raw artwork record")
    return safe_repo_path(raw.get("file"), root=root, field="raw target file")


def target_review_passed(provenance: dict[str, Any]) -> bool:
    run = provenance.get("run", {})
    validation = run.get("validation", {}) if isinstance(run, dict) else {}
    review = (
        validation.get("joint_scene_visual_review", {})
        if isinstance(validation, dict)
        else {}
    )
    return isinstance(review, dict) and review.get("passed") is True


def target_subject_ids(provenance: dict[str, Any]) -> list[Any]:
    run = provenance.get("run", {})
    validation = run.get("validation", {}) if isinstance(run, dict) else {}
    review = (
        validation.get("joint_scene_visual_review", {})
        if isinstance(validation, dict)
        else {}
    )
    values = review.get("source_subject_ids", []) if isinstance(review, dict) else []
    if not isinstance(values, list):
        raise ValueError("Target review source_subject_ids must be a list")
    # Form-aware promotions bind a small mapping containing both species and
    # Official Artwork identity; ordinary base forms retain their integer ID.
    return values


def proposed_split(asset_key: str, config: dict[str, Any]) -> str:
    holdouts = set(config["split_policy"]["holdout_scopes"])
    return "holdout" if asset_key in holdouts else "train_candidate"


def pair_status(
    *,
    target_exists: bool,
    target_review: bool,
    target_excluded: bool,
    input_errors: list[str],
    source_pixel_match: bool,
) -> str:
    if not target_exists:
        return "blocked_missing_target"
    if input_errors:
        return "rejected_input"
    if target_excluded:
        return "excluded_target"
    if not source_pixel_match:
        return "needs_fresh_exact_input"
    if not target_review:
        return "needs_target_review"
    return "candidate_pair_review"


def audit_promoted_pairs(
    config_path: Path,
    *,
    root: Path = ROOT,
    poster_assets: Path = POSTER_ASSETS,
) -> dict[str, Any]:
    config = load_json_object(config_path)
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported poster training config schema_version")
    excluded = config["split_policy"]["excluded_training_targets"]
    samples: list[dict[str, Any]] = []
    scopes: list[dict[str, Any]] = []

    provenance_paths = sorted(
        poster_assets.rglob("poster-flux2-provenance.json")
    )
    with tempfile.TemporaryDirectory(prefix="binder-pokedex-training-audit-") as temp:
        temporary_root = Path(temp)
        for provenance_path in provenance_paths:
            provenance = load_json_object(provenance_path)
            if provenance.get("kind") != "promoted_poster":
                continue
            # A masked composite is not a raw one-shot training target.
            if (
                provenance.get("schema_version") == 3
                and isinstance(provenance.get("composition"), dict)
                and provenance["composition"].get("kind") == "masked_fallback"
            ):
                continue
            asset_key = asset_key_for_provenance(
                provenance_path,
                poster_assets=poster_assets,
            )
            bundle = poster_bundle(
                asset_key,
                poster_assets=poster_assets,
            )
            target_path = target_path_from_provenance(provenance, root=root)
            target_exists = target_path.is_file()
            target_record = (
                immutable_image_record(target_path, root=root)
                if target_exists
                else {"file": relative_path(target_path, root=root)}
            )
            target_errors = (
                validate_image_contract(target_record, config)
                if target_exists
                else ["raw reviewed target is missing"]
            )
            target_ok = target_exists and not target_errors
            visual_review = target_review_passed(provenance)
            input_paths = sorted(
                bundle.work_dir.glob(
                    "output/*identity_lock*scene*.png"
                )
            )
            source_reference: Path | None = None
            reference_error: str | None = None
            try:
                source_reference = build_identity_lock_references(
                    asset_key,
                    1.0,
                    temporary_root / asset_key.replace("/", "__"),
                )
            except Exception as error:  # audit records local legacy drift
                reference_error = str(error)

            accepted_input_count = 0
            for index, input_path in enumerate(input_paths, start=1):
                input_record = immutable_image_record(input_path, root=root)
                input_errors = validate_image_contract(input_record, config)
                source_audit: dict[str, Any]
                if source_reference is None:
                    source_audit = {
                        "method": "exact_opaque_source_pixels",
                        "passed": False,
                        "error": reference_error or "reference unavailable",
                    }
                else:
                    try:
                        source_audit = audit_exact_source_pixels(
                            source_reference,
                            input_path,
                        )
                        source_audit.update(
                            {
                                "stage": "raw_training_input",
                                "reference_sha256": sha256_file(
                                    source_reference
                                ),
                                "input_sha256": input_record["sha256"],
                                "width": input_record["width"],
                                "height": input_record["height"],
                            }
                        )
                    except Exception as error:
                        source_audit = {
                            "method": "exact_opaque_source_pixels",
                            "passed": False,
                            "error": str(error),
                        }
                status = pair_status(
                    target_exists=target_ok,
                    target_review=visual_review,
                    target_excluded=asset_key in excluded,
                    input_errors=input_errors + target_errors,
                    source_pixel_match=source_audit.get("passed") is True,
                )
                if status not in {"rejected_input", "blocked_missing_target"}:
                    accepted_input_count += 1
                samples.append(
                    {
                        "id": f"{asset_key.replace('/', '__').lower()}__input{index:02d}",
                        "scene_key": asset_key,
                        "scope": asset_key,
                        "proposed_split": proposed_split(asset_key, config),
                        "review_status": status,
                        "subjects": target_subject_ids(provenance),
                        "occlusion_class": "unreviewed",
                        "input": input_record,
                        "target": target_record,
                        "target_provenance": relative_path(provenance_path, root=root),
                        "target_visual_review_passed": visual_review,
                        "source_pixel_audit": source_audit,
                        "validation_errors": input_errors + target_errors,
                        "exclusion_reason": excluded.get(asset_key),
                        "review": {},
                    }
                )

            scopes.append(
                {
                    "scope": asset_key,
                    "target_available": target_exists,
                    "target_visual_review_passed": visual_review,
                    "input_candidates": len(input_paths),
                    "non_rejected_inputs": accepted_input_count,
                    "proposed_split": proposed_split(asset_key, config),
                    "exclusion_reason": excluded.get(asset_key),
                }
            )

    counts = Counter(sample["review_status"] for sample in samples)
    return {
        "format_version": AUDIT_FORMAT_VERSION,
        "kind": "poster_edit_training_audit",
        "profile": config["profile"],
        "config": {
            "file": relative_path(config_path, root=root),
            "sha256": sha256_file(config_path),
        },
        "summary": {
            "promoted_scenes": len(scopes),
            "pair_candidates": len(samples),
            "scopes_without_input": sum(
                item["input_candidates"] == 0 for item in scopes
            ),
            "status_counts": dict(sorted(counts.items())),
        },
        "scopes": scopes,
        "samples": samples,
    }


def validate_recorded_image(
    record: dict[str, Any],
    *,
    root: Path,
    config: dict[str, Any],
    require_contract: bool = True,
) -> None:
    path = safe_repo_path(record.get("file"), root=root, field="image file")
    actual = immutable_image_record(path, root=root)
    for field in ("sha256", "pixel_sha256", "width", "height"):
        if actual.get(field) != record.get(field):
            raise ValueError(f"Stale {field} for {record.get('file')}")
    errors = validate_image_contract(actual, config)
    if require_contract and errors:
        raise ValueError(f"Invalid training image {record.get('file')}: {errors}")


def validate_audit_manifest(
    manifest_path: Path,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    manifest = load_json_object(manifest_path)
    if manifest.get("format_version") != AUDIT_FORMAT_VERSION:
        raise ValueError("Unsupported training audit format_version")
    if manifest.get("kind") != "poster_edit_training_audit":
        raise ValueError("Not a poster edit-training audit")
    config_record = manifest.get("config", {})
    config_path = safe_repo_path(
        config_record.get("file"),
        root=root,
        field="training config",
    )
    if sha256_file(config_path) != config_record.get("sha256"):
        raise ValueError("Training config changed after the audit")
    config = load_json_object(config_path)
    if manifest.get("profile") != config.get("profile"):
        raise ValueError("Training profile does not match its config")

    scene_splits: dict[str, str] = {}
    sample_ids: set[str] = set()
    required_gates = config["dataset_contract"]["required_review_gates"]
    for sample in manifest.get("samples", []):
        sample_id = sample.get("id")
        if not isinstance(sample_id, str) or not sample_id or sample_id in sample_ids:
            raise ValueError(f"Invalid or duplicate training sample id: {sample_id!r}")
        sample_ids.add(sample_id)
        status = sample.get("review_status")
        if status not in PAIR_STATUSES:
            raise ValueError(f"Unsupported review_status for {sample_id}: {status}")
        split = sample.get("proposed_split")
        scene_key = sample.get("scene_key")
        if not isinstance(scene_key, str) or split not in {
            "train_candidate",
            "validation",
            "holdout",
        }:
            raise ValueError(f"Invalid scene split for {sample_id}")
        previous = scene_splits.setdefault(scene_key, split)
        if previous != split:
            raise ValueError(f"Scene {scene_key} leaks across splits")
        validate_recorded_image(
            sample["input"],
            root=root,
            config=config,
            require_contract=status != "rejected_input",
        )
        if status != "blocked_missing_target":
            validate_recorded_image(sample["target"], root=root, config=config)
        if status == "gold":
            source_audit = sample.get("source_pixel_audit", {})
            if source_audit.get("passed") is not True:
                raise ValueError(f"Gold sample lacks exact source pixels: {sample_id}")
            if source_audit.get("input_sha256") != sample["input"].get("sha256"):
                raise ValueError(f"Gold sample has an unbound source audit: {sample_id}")
            if sample.get("target_visual_review_passed") is not True:
                raise ValueError(f"Gold sample lacks target visual review: {sample_id}")
            review = sample.get("review", {})
            missing = [gate for gate in required_gates if review.get(gate) is not True]
            if missing:
                raise ValueError(f"Gold sample lacks review gates {missing}: {sample_id}")
            if sample.get("occlusion_class") not in {"avoid", "front", "behind", "mixed"}:
                raise ValueError(f"Gold sample lacks an occlusion class: {sample_id}")
    return manifest


def materialize_gold_dataset(
    manifest_path: Path,
    output_dir: Path,
    *,
    root: Path = ROOT,
) -> Path:
    manifest = validate_audit_manifest(manifest_path, root=root)
    config_path = safe_repo_path(
        manifest["config"]["file"],
        root=root,
        field="training config",
    )
    config = load_json_object(config_path)
    gold = [
        sample
        for sample in manifest["samples"]
        if sample["review_status"] == "gold"
    ]
    training_gold = [
        sample
        for sample in gold
        if sample["proposed_split"] == "train_candidate"
    ]
    if not training_gold:
        raise ValueError("No gold training samples are ready to materialize")
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Immutable dataset output already exists: {output_dir}")
    reference_dir = output_dir / "reference"
    target_dir = output_dir / "target"
    reference_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    captions = config["caption_variants"]
    materialized = []
    for index, sample in enumerate(sorted(gold, key=lambda item: item["id"])):
        stem = sample["id"]
        input_path = safe_repo_path(sample["input"]["file"], root=root, field="input")
        target_path = safe_repo_path(sample["target"]["file"], root=root, field="target")
        split = (
            "train"
            if sample["proposed_split"] == "train_candidate"
            else sample["proposed_split"]
        )
        if split == "train":
            split_reference_dir = reference_dir
            split_target_dir = target_dir
        else:
            split_reference_dir = (
                output_dir / "evaluation" / split / "reference"
            )
            split_target_dir = output_dir / "evaluation" / split / "target"
            split_reference_dir.mkdir(parents=True, exist_ok=True)
            split_target_dir.mkdir(parents=True, exist_ok=True)
        reference_output = split_reference_dir / f"{stem}.png"
        target_output = split_target_dir / f"{stem}.png"
        shutil.copy2(input_path, reference_output)
        shutil.copy2(target_path, target_output)
        caption = captions[index % len(captions)]
        (split_target_dir / f"{stem}.txt").write_text(
            caption + "\n",
            encoding="utf-8",
        )
        materialized.append(
            {
                "id": stem,
                "scene_key": sample["scene_key"],
                "split": split,
                "caption_variant": index % len(captions),
                "reference_sha256": sha256_file(reference_output),
                "target_sha256": sha256_file(target_output),
            }
        )
    dataset_manifest = {
        "format_version": 1,
        "kind": "materialized_poster_edit_dataset",
        "profile": manifest["profile"],
        "source_audit_sha256": sha256_file(manifest_path),
        "ai_toolkit": {
            "folder_path": "target",
            "control_path": "reference",
            "caption_ext": "txt",
            "match_target_res": True,
        },
        "samples": materialized,
    }
    output_manifest = output_dir / "dataset.json"
    output_manifest.write_text(
        json.dumps(dataset_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser(
        "audit",
        help="Audit local promoted seed pairs",
    )
    audit_parser.add_argument("--config", type=Path, required=True)
    audit_parser.add_argument("--output", type=Path, required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate an immutable audit",
    )
    validate_parser.add_argument("--manifest", type=Path, required=True)

    materialize_parser = subparsers.add_parser(
        "materialize",
        help="Copy reviewed gold pairs",
    )
    materialize_parser.add_argument("--manifest", type=Path, required=True)
    materialize_parser.add_argument("--output", type=Path, required=True)

    compose_parser = subparsers.add_parser(
        "compose-target",
        help="Restore exact subjects over an AI-integrated teacher scene",
    )
    compose_parser.add_argument("--edited-scene", type=Path, required=True)
    compose_parser.add_argument("--source-reference", type=Path, required=True)
    compose_parser.add_argument("--output", type=Path, required=True)

    occlusion_parser = subparsers.add_parser(
        "compose-occlusion-target",
        help="Restore exact subjects and apply a reviewed foreground layer",
    )
    occlusion_parser.add_argument("--edited-scene", type=Path, required=True)
    occlusion_parser.add_argument("--source-reference", type=Path, required=True)
    occlusion_parser.add_argument("--foreground-layer", type=Path, required=True)
    occlusion_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "audit":
        result = audit_promoted_pairs(args.config.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
    elif args.command == "validate":
        result = validate_audit_manifest(args.manifest.resolve())
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
    elif args.command == "materialize":
        output = materialize_gold_dataset(
            args.manifest.resolve(),
            args.output,
        )
        print(output)
    elif args.command == "compose-target":
        result = compose_aligned_teacher_target(
            args.edited_scene,
            args.source_reference,
            args.output,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        result = compose_foreground_occlusion_target(
            args.edited_scene,
            args.source_reference,
            args.foreground_layer,
            args.output,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
