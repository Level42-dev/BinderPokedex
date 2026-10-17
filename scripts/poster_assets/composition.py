"""Character-placement helpers shared by poster conditioning workflows."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

try:
    from .layout import PageLayout, build_source_layout
    from .poster_io import load_cutout_items
    from .poster_subject import resolve_poster_subject
except ImportError:
    from layout import PageLayout, build_source_layout
    from poster_io import load_cutout_items
    from poster_subject import resolve_poster_subject


def fit_image(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    scale = min(max_width / image.width, max_height / image.height)
    return image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )


def validate_visible_placements(
    placements: list[dict[str, Any]],
    *,
    canvas_size: tuple[int, int] | None = None,
    description: str = "Character",
) -> None:
    """Reject visible pixels outside their card or the real image canvas."""
    if canvas_size is not None:
        canvas_width, canvas_height = canvas_size
        if canvas_width <= 0 or canvas_height <= 0:
            raise ValueError("Placement canvas dimensions must be positive")

    for placement in placements:
        image = placement["image"]
        alpha_box = image.getchannel("A").getbbox()
        if alpha_box is None:
            raise ValueError(f"{description} placement has no visible pixels")
        left = placement["x"] + alpha_box[0]
        top = placement["y"] + alpha_box[1]
        right = placement["x"] + alpha_box[2]
        bottom = placement["y"] + alpha_box[3]
        cell = placement["cell"]
        if not (
            cell.x <= left < right <= cell.x + cell.width
            and cell.y <= top < bottom <= cell.y + cell.height
        ):
            raise ValueError(
                f"{description} for Pokemon "
                f"#{placement['item'].get('pokemon_id')} moves its visible "
                "silhouette outside the assigned print-safe region"
            )
        if canvas_size is not None and not (
            0 <= left < right <= canvas_width
            and 0 <= top < bottom <= canvas_height
        ):
            raise ValueError(
                f"{description} for Pokemon "
                f"#{placement['item'].get('pokemon_id')} moves its visible "
                "silhouette outside the real generation canvas"
            )


def normalized_visible_placement_contract(
    placements: list[dict[str, Any]],
    *,
    canvas_size: tuple[int, int],
) -> list[dict[str, int]]:
    """Describe target silhouettes as stable per-mille canvas coordinates."""
    validate_visible_placements(
        placements,
        canvas_size=canvas_size,
    )
    width, height = canvas_size
    contract: list[dict[str, int]] = []
    for placement in placements:
        alpha_box = placement["image"].getchannel("A").getbbox()
        if alpha_box is None:
            raise ValueError("Character placement has no visible pixels")
        left = int(placement["x"]) + alpha_box[0]
        top = int(placement["y"]) + alpha_box[1]
        right = int(placement["x"]) + alpha_box[2]
        bottom = int(placement["y"]) + alpha_box[3]
        contract.append(
            {
                "left_per_mille": round(left * 1000 / width),
                "top_per_mille": round(top * 1000 / height),
                "right_per_mille": round(right * 1000 / width),
                "bottom_per_mille": round(bottom * 1000 / height),
            }
        )
    return contract


def cutout_placements(
    layout: PageLayout,
    scope_dir: Path,
    *,
    max_width_ratio: float = 0.84,
    max_height_ratio: float = 0.68,
    baseline_ratio: float = 0.80,
    subject_scales: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Place one complete cutout inside each bottom-row physical card."""
    for name, value in (
        ("max_width_ratio", max_width_ratio),
        ("max_height_ratio", max_height_ratio),
        ("baseline_ratio", baseline_ratio),
    ):
        if not 0 < value <= 1:
            raise ValueError(f"{name} must be in the range (0, 1]")
    cells = layout.bottom_row_cells()
    items = load_cutout_items(scope_dir)
    if not 1 <= len(items) <= len(cells):
        raise ValueError(
            f"Layout '{layout.name}' supports 1 to {len(cells)} character "
            f"cutouts, but {scope_dir / 'cutouts' / 'manifest.json'} contains "
            f"{len(items)}"
        )
    if len(items) < len(cells):
        if len(items) == 1:
            cells = [cells[len(cells) // 2]]
        else:
            last = len(cells) - 1
            divisor = len(items) - 1
            cells = [
                cells[(index * last + divisor // 2) // divisor]
                for index in range(len(items))
            ]
    prepared = []
    for cell, item in zip(cells, items):
        cutout_path = scope_dir / "cutouts" / item["file"]
        cutout = Image.open(cutout_path).convert("RGBA")
        target = fit_image(
            cutout,
            round(cell.width * max_width_ratio),
            round(cell.height * max_height_ratio),
        )
        original_target = target
        if subject_scales:
            scale = subject_scales.get(resolve_poster_subject(item).subject_key, 1.0)
            if scale != 1.0:
                size = (round(target.width * scale), round(target.height * scale))
                if min(size) < 1:
                    raise ValueError("spatial_reference_scales produces a zero-sized reference")
                # Resize from the original once, not from the already fitted image.
                target = cutout.resize(size, Image.Resampling.LANCZOS)
        prepared.append((cell, item, target, original_target))

    placements = []
    baseline = cells[0].y + round(cells[0].height * baseline_ratio)
    for cell, item, target, original_target in prepared:
        x = cell.x + (cell.width - original_target.width) // 2
        alpha_box = target.getchannel("A").getbbox()
        if alpha_box is None:
            raise ValueError(f"Cutout has no visible pixels: {item['file']}")
        if target is not original_target:
            original_alpha = original_target.getchannel("A").getbbox()
            if original_alpha is None:
                raise ValueError(f"Cutout has no visible pixels: {item['file']}")
            x += (original_alpha[0] + original_alpha[2] - alpha_box[0] - alpha_box[2]) // 2
        y = baseline - alpha_box[3]
        placements.append(
            {
                "cell": cell,
                "item": item,
                "image": target,
                "x": x,
                "y": y,
            }
        )
    validate_visible_placements(
        placements,
        canvas_size=(layout.width_px, layout.height_px),
    )
    return placements


def joint_scene_cutout_placements(
    layout: PageLayout,
    scope_dir: Path,
    *,
    subject_scales: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Reuse the proven card-safe placement contract for the joint scene."""
    return cutout_placements(layout, scope_dir, subject_scales=subject_scales)


def joint_scene_canvas_placements(
    scope_dir: Path,
    *,
    layout_name: str,
    canvas_size: tuple[int, int],
    subject_scales: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Build the canonical joint-scene placements for one raster canvas."""
    width, height = canvas_size
    layout = build_source_layout(
        layout_name,
        width_px=width,
        height_px=height,
    )
    return joint_scene_cutout_placements(layout, scope_dir, subject_scales=subject_scales)
