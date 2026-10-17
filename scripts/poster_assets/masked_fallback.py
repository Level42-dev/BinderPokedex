"""Exact, auditable composition of reviewed card-local poster repairs.

The durable mask is binary L in print-canvas coordinates. Historical repair
jobs used black RGBA images whose alpha below 255 denotes editable pixels;
that source representation is normalized explicitly before mapping.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from PIL import Image, ImageChops

try:
    from .layout import Cell, build_generation_output_layout
    from .poster_io import PosterBundle
    from .provenance import image_pixel_record, sha256_file
except ImportError:
    from layout import Cell, build_generation_output_layout
    from poster_io import PosterBundle
    from provenance import image_pixel_record, sha256_file


ROOT = Path(__file__).resolve().parents[2]


def _require_binary_mask(mask: Image.Image) -> None:
    if mask.mode != "L" or any(value not in (0, 255) for value in mask.get_flattened_data()):
        raise ValueError("Repair mask must be binary L")


def alpha_edit_mask(source: Image.Image) -> Image.Image:
    """Normalize the historical black-RGBA / alpha-below-255 edit encoding."""
    if source.mode != "RGBA" or any(source.getchannel(channel).getbbox() for channel in "RGB"):
        raise ValueError("Historical edit mask must be black RGBA")
    return source.getchannel("A").point(lambda alpha: 255 if alpha < 255 else 0)


def card_mask_to_canvas(
    mask: Image.Image,
    cell: Cell,
    canvas_size: tuple[int, int],
    *,
    padding_origin: str = "center",
) -> Image.Image:
    """Map a padded card mask using its explicit source padding origin."""
    _require_binary_mask(mask)
    extra_x, extra_y = mask.width - cell.width, mask.height - cell.height
    if extra_x < 0 or extra_y < 0:
        raise ValueError("Repair mask is smaller than the physical card")
    if padding_origin == "center":
        if extra_x % 2 or extra_y % 2:
            raise ValueError("Repair mask cannot center on the physical card")
        pad_x, pad_y = extra_x // 2, extra_y // 2
    elif padding_origin == "top_left":
        pad_x, pad_y = 0, 0
    else:
        raise ValueError(f"Unsupported repair mask padding origin: {padding_origin}")
    bounds = mask.getbbox()
    if bounds and (
        bounds[0] < pad_x or bounds[1] < pad_y
        or bounds[2] > pad_x + cell.width
        or bounds[3] > pad_y + cell.height
    ):
        raise ValueError("Repair mask has editable pixels in removed padding")
    if (
        cell.x < 0 or cell.y < 0 or cell.x + cell.width > canvas_size[0]
        or cell.y + cell.height > canvas_size[1]
    ):
        raise ValueError("Physical card lies outside print canvas")
    canvas = Image.new("L", canvas_size, 0)
    canvas.paste(
        mask.crop((pad_x, pad_y, pad_x + cell.width, pad_y + cell.height)),
        (cell.x, cell.y),
    )
    return canvas


def encode_mask(mask: Image.Image) -> dict:
    """Encode a binary print-canvas mask as sorted row-major RLE spans."""
    _require_binary_mask(mask)
    runs: list[list[int]] = []
    start: int | None = None
    for index, value in enumerate(mask.get_flattened_data()):
        if value == 255 and start is None:
            start = index
        elif value == 0 and start is not None:
            runs.append([start, index - start])
            start = None
    if start is not None:
        runs.append([start, mask.width * mask.height - start])
    return {"width": mask.width, "height": mask.height, "runs": runs}


def decode_mask(record: dict) -> Image.Image:
    """Reject malformed, overlapping or out-of-bounds RLE spans."""
    if not isinstance(record, dict):
        raise ValueError("Encoded mask must be a mapping")
    width, height, runs = record.get("width"), record.get("height"), record.get("runs")
    if (
        type(width) is not int or type(height) is not int
        or width <= 0 or height <= 0 or not isinstance(runs, list)
    ):
        raise ValueError("Encoded mask dimensions or runs are invalid")
    pixels = bytearray(width * height)
    prior_end = 0
    for run in runs:
        if (
            not isinstance(run, list) or len(run) != 2
            or type(run[0]) is not int or type(run[1]) is not int
        ):
            raise ValueError("Encoded mask run is invalid")
        start, length = run
        if start < prior_end or length <= 0:
            raise ValueError("Encoded mask runs overlap or are out of order")
        if start < 0 or start + length > len(pixels):
            raise ValueError("Encoded mask run exceeds dimensions")
        pixels[start:start + length] = b"\xff" * length
        prior_end = start + length
    return Image.frombytes("L", (width, height), bytes(pixels))


def outside_pixel_digest(image: Image.Image, union_mask: Image.Image) -> str:
    """Hash RGB print pixels outside the editable union, independent of PNG bytes."""
    _require_binary_mask(union_mask)
    if image.size != union_mask.size:
        raise ValueError("Outside digest image and mask dimensions differ")
    rgb = image.convert("RGB")
    outside = rgb.copy()
    outside.paste((0, 0, 0), (0, 0), union_mask)
    digest = hashlib.sha256()
    digest.update(f"{rgb.width}x{rgb.height}:RGB\n".encode("ascii"))
    digest.update(outside.tobytes())
    return digest.hexdigest()


def _changed_mask(first: Image.Image, second: Image.Image) -> Image.Image:
    red, green, blue = ImageChops.difference(first, second).split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue).point(
        lambda value: 255 if value else 0
    )


def _pixel_count(mask: Image.Image) -> int:
    return mask.histogram()[255]


def _load_rgb(path: Path) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        if image.mode == "RGBA" and image.getchannel("A").getextrema() != (255, 255):
            raise ValueError(f"Non-opaque poster artwork: {path}")
        return image.convert("RGB")


def audit_masked_merge(
    base: Path, final: Path, repairs: list[tuple[Path, Image.Image]]
) -> dict:
    """Prove independent disjoint repairs reconstruct final print pixels exactly."""
    base_image, final_image = _load_rgb(base), _load_rgb(final)
    if base_image.size != final_image.size:
        raise ValueError("Base and final poster dimensions differ")
    if not repairs:
        raise ValueError("Masked composition has no repairs")
    union = Image.new("L", base_image.size, 0)
    reconstructed = base_image.copy()
    repair_records = []
    for path, mask in repairs:
        _require_binary_mask(mask)
        if mask.size != base_image.size:
            raise ValueError("Repair mask and poster dimensions differ")
        editable = _pixel_count(mask)
        if editable == 0:
            raise ValueError("Repair mask is empty")
        if ImageChops.multiply(union, mask).getbbox():
            raise ValueError("Repair masks overlap")
        repair_image = _load_rgb(path)
        if repair_image.size != base_image.size:
            raise ValueError("Repair artwork dimensions differ")
        changed = _changed_mask(base_image, repair_image)
        changed_inside = _pixel_count(ImageChops.multiply(changed, mask))
        changed_outside = _pixel_count(ImageChops.subtract(changed, mask))
        if changed_outside:
            raise ValueError(f"Repair artwork changed {changed_outside} pixels outside its mask")
        if not changed_inside:
            raise ValueError("Repair artwork is unchanged inside its mask")
        reconstructed.paste(repair_image, (0, 0), mask)
        union = ImageChops.lighter(union, mask)
        repair_records.append({
            "editable_pixels": editable,
            "changed_editable_pixels": changed_inside,
            "changed_outside_mask_pixels": 0,
        })
    final_changed = _changed_mask(base_image, final_image)
    outside_changes = _pixel_count(ImageChops.subtract(final_changed, union))
    if outside_changes:
        raise ValueError(f"Final poster changed {outside_changes} pixels outside repair masks")
    if ImageChops.difference(reconstructed, final_image).getbbox():
        raise ValueError("Masked repairs do not reconstruct final poster pixels")
    outside_hash = outside_pixel_digest(base_image, union)
    if outside_pixel_digest(final_image, union) != outside_hash:
        raise ValueError("Final poster outside-pixel digest differs from base")
    return {
        "dimensions": {"width": base_image.width, "height": base_image.height},
        "editable_pixels": _pixel_count(union),
        "changed_editable_pixels": _pixel_count(ImageChops.multiply(final_changed, union)),
        "changed_outside_mask_pixels": 0,
        "outside_base_pixel_sha256": outside_hash,
        "union_mask": union,
        "repairs": repair_records,
    }


def _repo_path(value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("Composition input path must be a nonempty repository-relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Composition input path must stay inside the repository")
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Composition input path escapes the repository")
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _job_member(directory: Path, subdirectory: str, name: object) -> Path:
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise ValueError("Job component path must be a basename")
    path = directory / subdirectory / name
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _verified_job_records(job_dir: Path, generation: dict) -> tuple[dict, dict, Path]:
    """Verify every returned input/output and the immutable job's graph/models."""
    run_path = job_dir / "run.json"
    job_path = job_dir / "job.json"
    log_path = job_dir / "comfyui.log"
    for path in (run_path, job_path, log_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    if not log_path.stat().st_size:
        raise ValueError("Repair ComfyUI log is empty")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    job = json.loads(job_path.read_text(encoding="utf-8"))
    if not isinstance(run, dict) or not isinstance(job, dict):
        raise ValueError("Repair job and run must be mappings")
    if run.get("inputs") != job.get("inputs") or run.get("models") != job.get("models"):
        raise ValueError("Repair job hash records differ from returned run")
    for key, subdirectory in (("inputs", "input"), ("outputs", "output")):
        records = run.get(key)
        if not isinstance(records, list) or not records:
            raise ValueError(f"Repair run lacks {key}")
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"Invalid repair {key} record")
            path = _job_member(job_dir, subdirectory, record.get("path"))
            if sha256_file(path) != record.get("sha256"):
                raise ValueError(f"Repair {key} job hash mismatch: {path.name}")
    models = run.get("models")
    if not isinstance(models, list) or len(models) != 3:
        raise ValueError("Repair job lacks model hashes")
    expected_model_hashes = {
        generation[f"{key}_sha256"] for key in ("model", "encoder", "vae")
    }
    if {record.get("sha256") for record in models if isinstance(record, dict)} != expected_model_hashes:
        raise ValueError("Repair job model hashes do not match generation")
    workflow = job.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("Repair job lacks workflow record")
    workflow_path = _job_member(job_dir, "", workflow.get("path"))
    if sha256_file(workflow_path) != workflow.get("sha256") or run.get("workflow_sha256") != workflow.get("sha256"):
        raise ValueError("Repair job workflow hash mismatch")
    return run, {
        "run_sha256": sha256_file(run_path),
        "job_sha256": sha256_file(job_path),
        "comfyui_log_sha256": sha256_file(log_path),
        "workflow_sha256": sha256_file(workflow_path),
    }, log_path


def _padded_card_crop(image: Image.Image, cell: Cell, origin: str) -> Image.Image:
    if image.width < cell.width or image.height < cell.height:
        raise ValueError("Padded job card is smaller than physical card")
    if origin == "top_left":
        x, y = 0, 0
    elif origin == "center":
        dx, dy = image.width - cell.width, image.height - cell.height
        if dx % 2 or dy % 2:
            raise ValueError("Padded job card cannot center on physical card")
        x, y = dx // 2, dy // 2
    else:
        raise ValueError("Unsupported repair padding origin")
    return image.crop((x, y, x + cell.width, y + cell.height)).convert("RGB")


def load_and_audit_composition(
    input_path: Path, artwork: Path, bundle: PosterBundle
) -> tuple[dict, Path, Path]:
    """Validate every ignored source before a masked final can be staged."""
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1 or payload.get("kind") != "masked_fallback":
        raise ValueError("Unsupported masked composition input")
    base_run = _repo_path(payload.get("base_run"))
    base_artwork = _repo_path(payload.get("base_artwork"))
    review_path = _repo_path(payload.get("review_provenance"))
    base_evidence_path = _repo_path(payload.get("base_evidence"))
    combined_evidence_path = _repo_path(payload.get("combined_evidence"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if not isinstance(review, dict) or review.get("scope") != bundle.asset_key:
        raise ValueError("Masked artwork review targets a different poster")
    base_hash, final_hash = sha256_file(base_artwork), sha256_file(artwork)
    if review.get("one_shot_master_sha256") != base_hash or review.get("artwork_sha256") != final_hash:
        raise ValueError("Human artwork review is not bound to A and final H")
    if not str(review.get("human_approval", "")).startswith("text_free_artwork_accepted_"):
        raise ValueError("Masked artwork lacks explicit human approval")
    if review.get("one_shot_trial_evidence_sha256") != sha256_file(base_evidence_path):
        raise ValueError("One-shot review evidence hash mismatch")
    if review.get("combined_review_evidence_sha256") != sha256_file(combined_evidence_path):
        raise ValueError("Combined review evidence hash mismatch")
    logo_review = review.get("title_logo_approval")
    logo_file = bundle.manifest.get("title_logo", {}).get("files", {}).get("de")
    if (
        not isinstance(logo_review, dict)
        or not str(logo_review.get("status", "")).startswith("accepted_")
        or not isinstance(logo_file, str)
    ):
        raise ValueError("Masked fallback lacks accepted German title logo")
    logo_path = bundle.source_dir / logo_file
    if not logo_path.is_file() or sha256_file(logo_path) != logo_review.get("logo_sha256"):
        raise ValueError("Accepted German title logo hash mismatch")
    accepted_logo_preview = _repo_path(payload.get("accepted_logo_preview"))
    if sha256_file(accepted_logo_preview) != logo_review.get("german_preview_sha256"):
        raise ValueError("Accepted German logo preview hash mismatch")

    generation = bundle.manifest.get("artwork", {}).get("generation", {})
    layout = build_generation_output_layout(bundle.manifest.get("layout", {}).get("name", "standard_3x3"), generation)
    with Image.open(base_artwork) as source, Image.open(artwork) as final_source:
        if source.size != (layout.width_px, layout.height_px) or final_source.size != source.size:
            raise ValueError("Masked composition print dimensions do not match generation")
        base_image = source.convert("RGB")
    repair_inputs = payload.get("repairs")
    if not isinstance(repair_inputs, list) or not repair_inputs:
        raise ValueError("Masked composition requires repair records")
    repairs: list[tuple[Path, Image.Image]] = []
    repair_records: list[dict] = []
    repair_evidence_audits: list[dict] = []
    for item in repair_inputs:
        if not isinstance(item, dict):
            raise ValueError("Repair input must be a mapping")
        row, column = item.get("row"), item.get("column")
        if type(row) is not int or type(column) is not int:
            raise ValueError("Repair card coordinates must be integers")
        cell = layout.cell(row, column)
        origin = item.get("padding_origin")
        mask_path = _repo_path(item.get("mask"))
        repair_path = _repo_path(item.get("artwork"))
        evidence_path = _repo_path(item.get("evidence"))
        job_dir_value = item.get("job_dir")
        if not isinstance(job_dir_value, str) or not job_dir_value or Path(job_dir_value).is_absolute() or ".." in Path(job_dir_value).parts:
            raise ValueError("Repair job directory must be repository-relative")
        job_dir = (ROOT / job_dir_value).resolve()
        if not job_dir.is_relative_to(ROOT.resolve()):
            raise ValueError("Repair job directory escapes repository")
        expected_hashes = item.get("expected_sha256")
        if not isinstance(expected_hashes, dict) or any(
            not re.fullmatch(r"[0-9a-f]{64}", str(expected_hashes.get(key, "")))
            for key in ("run", "job", "log", "bounded_output", "mask", "artwork", "evidence")
        ):
            raise ValueError("Repair input lacks immutable expected job hashes")
        for key, filename in (("run", "run.json"), ("job", "job.json"), ("log", "comfyui.log")):
            path = job_dir / filename
            if not path.is_file():
                raise FileNotFoundError(path)
            if sha256_file(path) != expected_hashes[key]:
                raise ValueError(f"Repair {key} job hash differs from reviewed input")
        run, job_hashes, _log = _verified_job_records(job_dir, generation)
        named_inputs = {record["path"]: record["sha256"] for record in run["inputs"]}
        if named_inputs.get("repair-mask.png") != sha256_file(mask_path):
            raise ValueError("Repair mask hash differs from returned job")
        mask_key, evidence_key = item.get("approval_mask_key"), item.get("approval_evidence_key")
        if review.get(mask_key) != sha256_file(mask_path) or review.get(evidence_key) != sha256_file(evidence_path):
            raise ValueError("Human review does not bind repair mask and evidence")
        with Image.open(mask_path) as raw_mask:
            normalized = alpha_edit_mask(raw_mask)
        canvas_mask = card_mask_to_canvas(
            normalized, cell, base_image.size, padding_origin=origin,
        )
        original_card_path = _job_member(job_dir, "input", "original-card-padded.png")
        with Image.open(original_card_path) as original_card:
            if ImageChops.difference(
                _padded_card_crop(original_card, cell, origin),
                base_image.crop((cell.x, cell.y, cell.x + cell.width, cell.y + cell.height)),
            ).getbbox():
                raise ValueError("Repair source card differs from one-shot base")
        bounded_name = item.get("bounded_output")
        if not isinstance(bounded_name, str) or bounded_name not in {
            record.get("path") for record in run["outputs"]
        }:
            raise ValueError("Repair bounded output is missing from job")
        bounded_path = _job_member(job_dir, "output", bounded_name)
        for key, path in (
            ("bounded_output", bounded_path), ("mask", mask_path),
            ("artwork", repair_path), ("evidence", evidence_path),
        ):
            if sha256_file(path) != expected_hashes[key]:
                raise ValueError(f"Repair {key} job hash differs from reviewed input")
        with Image.open(bounded_path) as bounded, Image.open(repair_path) as repaired:
            if ImageChops.difference(
                _padded_card_crop(bounded, cell, origin),
                repaired.convert("RGB").crop((cell.x, cell.y, cell.x + cell.width, cell.y + cell.height)),
            ).getbbox():
                raise ValueError("Repair full master differs from returned bounded job output")
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence.get("master", {}).get("sha256") != sha256_file(repair_path):
            raise ValueError("Repair evidence does not bind its full master")
        evidence_audit = evidence.get("pixel_audit")
        if not isinstance(evidence_audit, dict):
            raise ValueError("Repair pixel audit evidence is missing")
        repairs.append((repair_path, canvas_mask))
        repair_evidence_audits.append(evidence_audit)
        repair_records.append({
            "reason": item.get("reason"),
            "row": row, "column": column,
            "padding_origin": origin,
            "mask_sha256": sha256_file(mask_path),
            "mask": encode_mask(canvas_mask),
            "full_artwork_sha256": sha256_file(repair_path),
            "bounded_output_sha256": sha256_file(bounded_path),
            "evidence_sha256": sha256_file(evidence_path),
            **job_hashes,
        })
    audit = audit_masked_merge(base_artwork, artwork, repairs)
    expected = review.get("pixel_audit")
    combined_evidence = json.loads(combined_evidence_path.read_text(encoding="utf-8"))
    if not isinstance(expected, dict) or not isinstance(combined_evidence, dict):
        raise ValueError("Combined masked audit evidence is invalid")
    for key in ("editable_pixels", "changed_editable_pixels", "changed_outside_mask_pixels"):
        if audit[key] != expected.get(key) or audit[key] != combined_evidence.get("combined_pixel_audit", {}).get(key):
            raise ValueError(f"Masked audit differs from human review: {key}")
    if combined_evidence.get("master", {}).get("sha256") != final_hash:
        raise ValueError("Combined review evidence does not bind accepted final")
    for record, repair_audit, evidence_audit in zip(
        repair_records, audit["repairs"], repair_evidence_audits, strict=True,
    ):
        if any(
            repair_audit[key] != evidence_audit.get(key)
            for key in ("editable_pixels", "changed_editable_pixels", "changed_outside_mask_pixels")
        ):
            raise ValueError("Repair pixel audit differs from reviewed evidence")
        record.update(repair_audit)
    record = {
        "kind": "masked_fallback",
        "base_run_sha256": sha256_file(base_run),
        "base_artwork_sha256": base_hash,
        "base_artwork_pixel_sha256": image_pixel_record(base_artwork)["pixel_sha256"],
        "final_artwork_sha256": final_hash,
        "final_artwork_pixel_sha256": image_pixel_record(artwork)["pixel_sha256"],
        "base_review_evidence_sha256": sha256_file(base_evidence_path),
        "combined_review_evidence_sha256": sha256_file(combined_evidence_path),
        "outside_base_pixel_sha256": audit["outside_base_pixel_sha256"],
        "union_mask": encode_mask(audit["union_mask"]),
        "editable_pixels": audit["editable_pixels"],
        "changed_editable_pixels": audit["changed_editable_pixels"],
        "changed_outside_mask_pixels": 0,
        "repairs": repair_records,
        "human_artwork_approval": review["human_approval"],
        "title_logo_approval": {
            "status": logo_review["status"],
            "logo_sha256": logo_review["logo_sha256"],
            "logo_pixel_sha256": image_pixel_record(logo_path)["pixel_sha256"],
            "accepted_preview_sha256": logo_review["german_preview_sha256"],
        },
        "localized_overlay_approval": None,
    }
    return record, base_run, base_artwork
