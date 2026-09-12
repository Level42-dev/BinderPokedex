"""Explicit, source-locked ground masks for poster identity workflows."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

try:
    from .poster_subject import resolve_poster_subject
except ImportError:
    from poster_subject import resolve_poster_subject


_GROUNDING_FIELDS = {"schema_version", "prompt", "feather_ratio", "regions"}
_REGION_FIELDS = {"subject_key", "contact", "polygon", "anchors"}
_CONTACTS = {"grounded", "hover"}


def _require_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping")
    return value


def _normalized_point(value: object, field: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{field} must be a normalized [x, y] coordinate")
    result: list[float] = []
    for coordinate in value:
        if (
            isinstance(coordinate, bool)
            or not isinstance(coordinate, (int, float))
            or not math.isfinite(coordinate)
        ):
            raise ValueError(f"{field} coordinate must be a finite number")
        if not 0 <= coordinate <= 1:
            raise ValueError(f"{field} coordinate must be in the range [0, 1]")
        result.append(float(coordinate))
    return result


def _polygon_area_twice(points: list[list[float]]) -> float:
    return sum(
        point[0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * point[1]
        for index, point in enumerate(points)
    )


def _point_on_segment(
    point: list[float],
    start: list[float],
    end: list[float],
) -> bool:
    cross = (
        (point[1] - start[1]) * (end[0] - start[0])
        - (point[0] - start[0]) * (end[1] - start[1])
    )
    if abs(cross) > 1e-12:
        return False
    return (
        min(start[0], end[0]) - 1e-12
        <= point[0]
        <= max(start[0], end[0]) + 1e-12
        and min(start[1], end[1]) - 1e-12
        <= point[1]
        <= max(start[1], end[1]) + 1e-12
    )


def _point_in_polygon(point: list[float], polygon: list[list[float]]) -> bool:
    inside = False
    previous = polygon[-1]
    for current in polygon:
        if _point_on_segment(point, previous, current):
            return True
        if (current[1] > point[1]) != (previous[1] > point[1]):
            crossing_x = (
                (previous[0] - current[0])
                * (point[1] - current[1])
                / (previous[1] - current[1])
                + current[0]
            )
            if point[0] < crossing_x:
                inside = not inside
        previous = current
    return inside


def grounding_config(manifest: dict) -> dict:
    """Validate and normalize ``artwork.identity_lock.grounding``."""
    manifest_mapping = _require_mapping(manifest, "manifest")
    artwork = _require_mapping(manifest_mapping.get("artwork"), "artwork")
    identity_lock = _require_mapping(
        artwork.get("identity_lock"),
        "artwork.identity_lock",
    )
    raw = _require_mapping(
        identity_lock.get("grounding"),
        "artwork.identity_lock.grounding",
    )
    unknown = set(raw) - _GROUNDING_FIELDS
    if unknown:
        raise ValueError(
            "artwork.identity_lock.grounding has unknown fields: "
            + ", ".join(sorted(unknown))
        )
    if type(raw.get("schema_version")) is not int or raw["schema_version"] != 1:
        raise ValueError("grounding.schema_version must be 1")
    prompt = raw.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("grounding.prompt must be nonempty text")
    feather_ratio = raw.get("feather_ratio")
    if (
        isinstance(feather_ratio, bool)
        or not isinstance(feather_ratio, (int, float))
        or not math.isfinite(feather_ratio)
        or not 0 <= feather_ratio <= 0.02
    ):
        raise ValueError("grounding.feather_ratio must be in the range [0, 0.02]")
    raw_regions = raw.get("regions")
    if not isinstance(raw_regions, list) or not raw_regions:
        raise ValueError("grounding.regions must be a nonempty list")

    regions = []
    seen_subjects: set[str] = set()
    for index, raw_region in enumerate(raw_regions):
        field = f"grounding.regions[{index}]"
        region = _require_mapping(raw_region, field)
        unknown = set(region) - _REGION_FIELDS
        if unknown:
            raise ValueError(
                f"{field} has unknown fields: " + ", ".join(sorted(unknown))
            )
        subject_key = region.get("subject_key")
        if not isinstance(subject_key, str) or not subject_key.strip():
            raise ValueError(f"{field}.subject_key must be nonempty text")
        subject_key = subject_key.strip()
        if subject_key in seen_subjects:
            raise ValueError(f"Duplicate grounding subject_key: {subject_key}")
        seen_subjects.add(subject_key)
        contact = region.get("contact")
        if contact not in _CONTACTS:
            raise ValueError(
                f"{field}.contact must be 'grounded' or 'hover'"
            )
        raw_polygon = region.get("polygon")
        if not isinstance(raw_polygon, list) or len(raw_polygon) < 3:
            raise ValueError(f"{field}.polygon must contain at least 3 vertices")
        polygon = [
            _normalized_point(point, f"{field}.polygon[{point_index}]")
            for point_index, point in enumerate(raw_polygon)
        ]
        if abs(_polygon_area_twice(polygon)) <= 1e-12:
            raise ValueError(f"{field}.polygon is degenerate")
        raw_anchors = region.get("anchors")
        if not isinstance(raw_anchors, list) or not raw_anchors:
            raise ValueError(f"{field}.anchors must be a nonempty list")
        anchors = [
            _normalized_point(anchor, f"{field}.anchors[{anchor_index}]")
            for anchor_index, anchor in enumerate(raw_anchors)
        ]
        if any(not _point_in_polygon(anchor, polygon) for anchor in anchors):
            raise ValueError(f"{field}.anchors must be inside its polygon")
        regions.append(
            {
                "subject_key": subject_key,
                "contact": contact,
                "polygon": polygon,
                "anchors": anchors,
            }
        )
    return {
        "schema_version": 1,
        "prompt": prompt.strip(),
        "feather_ratio": float(feather_ratio),
        "regions": regions,
    }


def _pixel_coordinate(value: float, dimension: int) -> int:
    return min(dimension - 1, round(value * dimension))


def _pixel_point(point: list[float], width: int, height: int) -> tuple[int, int]:
    return (
        _pixel_coordinate(point[0], width),
        _pixel_coordinate(point[1], height),
    )


def _binary_alpha(image: Image.Image) -> Image.Image:
    return image.convert("RGBA").getchannel("A").point(
        lambda alpha: 255 if alpha else 0
    )


def _paste_source_support(
    destination: Image.Image,
    source: Image.Image,
    x: int,
    y: int,
) -> None:
    left = max(0, x)
    top = max(0, y)
    right = min(destination.width, x + source.width)
    bottom = min(destination.height, y + source.height)
    if left >= right or top >= bottom:
        return
    crop = source.crop((left - x, top - y, right - x, bottom - y))
    layer = Image.new("L", destination.size, 0)
    layer.paste(crop, (left, top))
    destination.paste(ImageChops.lighter(destination, layer))


def _nonzero_pixels(image: Image.Image) -> int:
    return sum(count for value, count in enumerate(image.histogram()) if value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inverse_alpha_rgba(editable: Image.Image) -> Image.Image:
    result = Image.new("RGBA", editable.size, (0, 0, 0, 255))
    result.putalpha(ImageChops.invert(editable))
    return result


def _erode_binary(image: Image.Image) -> Image.Image:
    padded = ImageOps.expand(image, border=1, fill=0)
    eroded = padded.filter(ImageFilter.MinFilter(3))
    return eroded.crop((1, 1, image.width + 1, image.height + 1))


def build_grounding_masks(
    width: int,
    height: int,
    placements: list[dict],
    manifest: dict,
    output_dir: Path,
) -> dict:
    """Build source-excluding feather and sampling masks plus metadata."""
    if (
        type(width) is not int
        or type(height) is not int
        or width <= 0
        or height <= 0
    ):
        raise ValueError("Grounding mask dimensions must be positive integers")
    if not isinstance(placements, list) or not placements:
        raise ValueError("Grounding masks need at least one subject placement")
    config = grounding_config(manifest)

    source_support = Image.new("L", (width, height), 0)
    source_identities = []
    placement_subjects: set[str] = set()
    for placement in placements:
        if not isinstance(placement, dict):
            raise ValueError("Grounding placements must be mappings")
        subject = resolve_poster_subject(placement.get("item"))
        if subject.subject_key in placement_subjects:
            raise ValueError(
                f"Duplicate grounding placement subject: {subject.subject_key}"
            )
        placement_subjects.add(subject.subject_key)
        source_identities.append(subject.as_mapping())
        image = placement.get("image")
        if not isinstance(image, Image.Image):
            raise ValueError("Grounding placement image must be a Pillow image")
        support = _binary_alpha(image)
        if support.getbbox() is None:
            raise ValueError(
                f"Grounding subject {subject.subject_key} has no visible pixels"
            )
        x = placement.get("x")
        y = placement.get("y")
        if type(x) is not int or type(y) is not int:
            raise ValueError("Grounding placement x and y must be integers")
        _paste_source_support(source_support, support, x, y)

    region_subjects = {region["subject_key"] for region in config["regions"]}
    if region_subjects != placement_subjects:
        missing = sorted(placement_subjects - region_subjects)
        unmatched = sorted(region_subjects - placement_subjects)
        raise ValueError(
            "Grounding regions do not match placement subjects; "
            f"missing={missing}, unmatched={unmatched}"
        )

    polygon_union = Image.new("L", (width, height), 0)
    anchor_pixels = []
    for region in config["regions"]:
        polygon_pixels = [
            _pixel_point(point, width, height) for point in region["polygon"]
        ]
        region_raster = Image.new("L", (width, height), 0)
        ImageDraw.Draw(region_raster).polygon(polygon_pixels, fill=255)
        region_anchor_pixels = [
            _pixel_point(anchor, width, height) for anchor in region["anchors"]
        ]
        if any(
            region_raster.getpixel(anchor) == 0
            for anchor in region_anchor_pixels
        ):
            raise ValueError(
                f"Grounding anchor for {region['subject_key']} lies outside "
                "its region raster after coordinate rounding"
            )
        polygon_union = ImageChops.lighter(polygon_union, region_raster)
        anchor_pixels.append(
            {
                "subject_key": region["subject_key"],
                "pixels": [
                    list(anchor) for anchor in region_anchor_pixels
                ],
            }
        )
    polygon_union_pixels = _nonzero_pixels(polygon_union)
    if polygon_union_pixels > width * height * 0.12:
        raise ValueError("Grounding polygon union exceeds 12% of the canvas")

    inverse_source = ImageChops.invert(source_support)
    allowed = ImageChops.multiply(polygon_union, inverse_source)
    if allowed.getbbox() is None:
        raise ValueError("Grounding masks leave no editable ground")
    radius = min(width, height) * config["feather_ratio"]
    feathered = polygon_union.copy()
    if radius > 0:
        feathered = Image.new("L", polygon_union.size, 0)
        inner = polygon_union.copy()
        steps = max(1, math.ceil(radius))
        for step in range(1, steps + 1):
            inner = _erode_binary(inner)
            level = round(255 * step / steps)
            layer = inner.point(lambda value: level if value else 0)
            feathered = ImageChops.lighter(feathered, layer)
    editable = ImageChops.multiply(feathered, inverse_source)
    if editable.getbbox() is None:
        raise ValueError("Grounding masks leave no editable ground")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    mask_path = output_path / "grounding_mask.png"
    sampling_path = output_path / "grounding_sampling_mask.png"
    _inverse_alpha_rgba(editable).save(mask_path, format="PNG", optimize=True)
    _inverse_alpha_rgba(allowed).save(sampling_path, format="PNG", optimize=True)

    record = {
        "schema_version": 1,
        "configuration": config,
        "dimensions": {"width": width, "height": height},
        "grounding_mask_sha256": _sha256_file(mask_path),
        "grounding_sampling_mask_sha256": _sha256_file(sampling_path),
        "source_identities": source_identities,
        "anchor_pixels": anchor_pixels,
        "counts": {
            "polygon_union_pixels": polygon_union_pixels,
            "editable_pixels": _nonzero_pixels(editable),
            "sampling_editable_pixels": _nonzero_pixels(allowed),
            "source_visible_pixels": _nonzero_pixels(source_support),
            "anchor_pixels": sum(
                len(region["pixels"]) for region in anchor_pixels
            ),
        },
    }
    (output_path / "grounding_mask.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return record


def _load_rgba(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGBA")


def audit_grounding_pixels(
    reference_path: Path,
    baseline_path: Path,
    artwork_path: Path,
    mask_path: Path,
) -> dict:
    """Prove exact source/outside-mask equality and real editable changes."""
    paths = [
        Path(reference_path),
        Path(baseline_path),
        Path(artwork_path),
        Path(mask_path),
    ]
    reference, baseline, artwork, mask = [_load_rgba(path) for path in paths]
    if len({image.size for image in (reference, baseline, artwork, mask)}) != 1:
        raise ValueError("Grounding audit input dimensions do not match")

    source_alpha = reference.getchannel("A")
    mask_alpha = mask.getchannel("A")
    source_flags = [alpha > 0 for alpha in source_alpha.tobytes()]
    editable_flags = [alpha < 255 for alpha in mask_alpha.tobytes()]
    if any(
        source and editable
        for source, editable in zip(source_flags, editable_flags)
    ):
        raise ValueError("Grounding mask overlaps visible source pixels")

    baseline_bytes = baseline.tobytes()
    artwork_bytes = artwork.tobytes()
    changed_flags = [
        baseline_bytes[offset : offset + 4] != artwork_bytes[offset : offset + 4]
        for offset in range(0, len(baseline_bytes), 4)
    ]
    source_visible_pixels = sum(source_flags)
    changed_source_pixels = sum(
        changed and source
        for changed, source in zip(changed_flags, source_flags)
    )
    editable_pixels = sum(editable_flags)
    changed_editable_pixels = sum(
        changed and editable
        for changed, editable in zip(changed_flags, editable_flags)
    )
    outside_flags = [not editable for editable in editable_flags]
    outside_mask_pixels = sum(outside_flags)
    changed_outside_mask_pixels = sum(
        changed and outside
        for changed, outside in zip(changed_flags, outside_flags)
    )

    if changed_source_pixels:
        raise ValueError(
            f"Grounding source pixels changed: {changed_source_pixels}"
        )
    if changed_outside_mask_pixels:
        raise ValueError(
            "Grounding artwork changed pixels outside the editable mask: "
            f"{changed_outside_mask_pixels}"
        )
    if changed_editable_pixels == 0:
        raise ValueError("Grounding editable region is unchanged")

    width, height = reference.size
    return {
        "method": "exact_grounding_protected_pixels",
        "passed": True,
        "dimensions": {"width": width, "height": height},
        "reference_sha256": _sha256_file(paths[0]),
        "baseline_sha256": _sha256_file(paths[1]),
        "artwork_sha256": _sha256_file(paths[2]),
        "mask_sha256": _sha256_file(paths[3]),
        "editable_pixels": editable_pixels,
        "changed_editable_pixels": changed_editable_pixels,
        "source_visible_pixels": source_visible_pixels,
        "changed_source_pixels": changed_source_pixels,
        "outside_mask_pixels": outside_mask_pixels,
        "changed_outside_mask_pixels": changed_outside_mask_pixels,
    }
