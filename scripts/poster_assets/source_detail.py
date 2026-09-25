"""Versioned source-bound traits for shared-layout one-shot synthesis."""
from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

try:
    from .poster_subject import resolve_poster_subject
    from .layout import LAYOUTS
except ImportError:
    from poster_subject import resolve_poster_subject
    from layout import LAYOUTS

REFERENCE_MODE = "spatial_source_detail_joint"
PROMPT_FILE = "source_detail_joint_prompt.generated.txt"
CURRENT_PIPELINE_VERSION = 11


def spatial_reference_scales(manifest, items, *, reference_mode):
    """Validate opt-in shrink factors bound to exact canonical artwork IDs."""
    artwork = manifest.get("artwork", {})
    if "spatial_reference_scales" not in artwork:
        return {}
    scales = artwork["spatial_reference_scales"]
    if not isinstance(scales, dict):
        raise ValueError("spatial_reference_scales must be a mapping")
    if scales and reference_mode != REFERENCE_MODE:
        raise ValueError("spatial_reference_scales requires spatial_source_detail_joint")
    keys = {resolve_poster_subject(item).subject_key for item in items}
    if not set(scales) <= keys:
        raise ValueError("spatial_reference_scales must use canonical cast keys")
    for value in scales.values():
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not 0 < value <= 1):
            raise ValueError("spatial_reference_scales factors must be finite numbers in (0, 1]")
    return {key: float(value) for key, value in scales.items()}


def validate_source_details(manifest, items, source_dir: Path | None = None):
    """Bind exact canonical identities to descriptions and optional PNG bytes."""
    keys = [resolve_poster_subject(item).subject_key for item in items]
    if not keys or len(set(keys)) != len(keys):
        raise ValueError("source_details requires a non-empty cast without duplicate keys")
    details = manifest.get("artwork", {}).get("source_details")
    if not isinstance(details, dict) or set(details) != set(keys):
        raise ValueError("source_details must cover exactly the canonical cast keys")
    for key, item in zip(keys, items, strict=True):
        record = details[key]
        if not isinstance(record, dict) or set(record) != {"sha256", "traits"}:
            raise ValueError(f"source_details {key} requires sha256 and traits")
        if not isinstance(record["traits"], str) or not record["traits"].strip():
            raise ValueError(f"source_details {key} requires non-empty English traits")
        if not isinstance(record["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
            raise ValueError(f"source_details {key} has an invalid sha256")
        if source_dir is not None:
            root = (source_dir / "cutouts").resolve()
            path = (root / str(item["file"])).resolve()
            if not path.is_relative_to(root):
                raise ValueError("source_details cutout path escapes source directory")
            if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
                raise ValueError(f"source_details source digest mismatch for {key}")
    return {key: dict(details[key]) for key in keys}


def build_source_detail_prompt(
    manifest, items, *, placement_contract,
    pipeline_contract_version=CURRENT_PIPELINE_VERSION,
):
    if pipeline_contract_version not in {10, 11}:
        raise ValueError("Unsupported source-detail pipeline version")
    details = validate_source_details(manifest, items)
    if len(placement_contract) != len(items):
        raise ValueError("source_details needs one layout placement per subject")
    bounds = []
    for item, box in zip(items, placement_contract, strict=True):
        values = [box[key] for key in ("left_per_mille", "right_per_mille", "top_per_mille", "bottom_per_mille")]
        if any(type(v) is not int or not 0 <= v <= 1000 for v in values):
            raise ValueError("source_details placement coordinates must be per-mille integers")
        left, right, top, bottom = values
        bounds.append(f"{resolve_poster_subject(item).subject_key}: x {left / 10:.1f}–{right / 10:.1f}%, y {top / 10:.1f}–{bottom / 10:.1f}%")
    upper = min(box["top_per_mille"] for box in placement_contract) / 10
    paragraphs = [
        f"COUNT AND LAYOUT FIRST. Render exactly {len(items)} Pokemon, each once, with the exact special forms shown. IMAGE 1 is the sole shared spatial-layout reference for count, pose, orientation, scale, baseline and positions. Target silhouette bounds: {'; '.join(bounds)}. Keep the upper {upper:.1f}% of the canvas subject-free. Preserve these positions and small subject scale before adding scene detail.",
        "The remaining images are individual detail views of this same cast, not extra subjects. Their centered positions and neutral backgrounds carry no scene or placement meaning. Preserve source-specific anatomy, silhouette, face, colors, markings and appendages; each detail reference applies only to its named subject.",
    ]
    if pipeline_contract_version >= 11:
        columns = LAYOUTS[manifest.get("layout", {}).get("name", "standard_3x3")]["columns"]
        inventory = []
        heights = []
        for item, box in zip(items, placement_contract, strict=True):
            name = item.get("name_en") or resolve_poster_subject(item).subject_key
            center = (box["left_per_mille"] + box["right_per_mille"]) / 2
            column = min(columns - 1, int(center * columns / 1000))
            if column == 0:
                position = "bottom-left"
            elif column == columns - 1:
                position = "bottom-right"
            elif columns % 2 and column == columns // 2:
                position = "bottom-center"
            else:
                position = f"bottom column {column + 1} of {columns}"
            inventory.append(f"ONE {name} at {position}")
            height = (box["bottom_per_mille"] - box["top_per_mille"]) / 10
            heights.append(f"{name}: {height:.1f}%")
        lower = max(box["bottom_per_mille"] for box in placement_contract) / 10
        paragraphs = [
            f"COUNT AND LAYOUT FIRST. EXACT SCENE INVENTORY: {', '.join(inventory)}. TOTAL: {len(items)} Pokemon, all in the same single bottom row, with the exact special forms shown. Render exactly {len(items)} Pokemon, each once. Never create a second instance of any named individual anywhere in the landscape. IMAGES 2–{len(items) + 1} show details of these existing bottom-row individuals only; they are not additional individuals to place in the scene. The upper {upper:.1f}% of the picture contains absolutely no Pokemon pixels.",
            f"COMPOSITION HAS FIRST PRIORITY. This is a vast LANDSCAPE POSTER with {len(items)} SMALL characters far down at its bottom edge, exactly matching IMAGE 1. Keep the entire cast inside y{upper:.1f}% to y{lower:.1f}% of the full picture. Individual silhouette heights as percentages of full canvas height: {'; '.join(heights)}. Exact target silhouette bounds: {'; '.join(bounds)}. IMAGE 1 fixes count, pose, orientation, small scale, shared baseline and positions. Do not enlarge characters, move them into the middle, zoom or crop IMAGE 1. The large individual detail references control anatomy, silhouette, face, colors, markings and appendages only; their large scale MUST NOT be transferred into the poster. Their centered positions and neutral backgrounds carry no placement or scene meaning. Preserve broad empty landscape above the cast and natural padding around it. These layout limits remain mandatory while applying the following detail and scene instructions.",
        ]
    for index, item in enumerate(items, 2):
        key = resolve_poster_subject(item).subject_key
        name = item.get("name_en") or key
        paragraphs.append(f"IMAGE {index}: exact individual detail reference for {name} ({key}). {details[key]['traits']}")
    scene = manifest.get("artwork", {}).get("scene", {})
    description = [scene.get(key, "") for key in ("concept", "setting", "lighting", "rendering")]
    constraints = scene.get("constraints", [])
    if not isinstance(constraints, list) or not all(isinstance(v, str) for v in description + constraints):
        raise ValueError("source_details scene descriptions and constraints must be text")
    paragraphs.extend([
        "Generate one cohesive text-free full-bleed landscape and all subjects together from an empty target in one sampling pass. " + " ".join(description + constraints),
        "Use physically consistent depth, shared lighting, contact shadows and scene-appropriate foreground overlaps: grass, rocks, water or other natural foreground elements may plausibly overlap lower subject edges while preserving recognizable source details and anatomy. Keep depth ordering coherent and subject scale fixed. Render no extra creatures, people, text, logos, panels, borders or watermarks.",
    ])
    return "\n\n".join(paragraphs)


def format_prompt_snapshot(prompt, *, pipeline_contract_version=CURRENT_PIPELINE_VERSION):
    if pipeline_contract_version not in {10, 11}:
        raise ValueError("Unsupported source-detail pipeline version")
    return f"SOURCE DETAIL JOINT SCENE - VERSION {pipeline_contract_version}\n\n" + prompt.strip()
