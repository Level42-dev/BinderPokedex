"""Exact, auditable composition of reviewed card-local poster repairs.

The durable mask is binary L in print-canvas coordinates. Historical repair
jobs used black RGBA images whose alpha below 255 denotes editable pixels;
that source representation is normalized explicitly before mapping.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageChops

from .layout import Cell


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
