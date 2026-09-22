#!/usr/bin/env python3
"""Prepare the reviewed references for one FLUX.2 poster mode."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

try:
    from .source_detail import spatial_reference_scales
    from .grounding import build_grounding_masks
    from .poster_config import GROUNDED_PROMPT_FILE, build_grounded_prompt_snapshot
    from .composition import (
        cutout_placements,
        joint_scene_canvas_placements,
        validate_visible_placements,
    )
    from .create_comfyui_poster_workflow import output_dimensions
    from .generation_contract import (
        CANONICAL_REFERENCE_MODES,
        INDIVIDUAL_SPATIAL_REFERENCE_MEGAPIXELS,
        JOINT_SCENE_CAST_MAX_MEGAPIXELS,
        JOINT_SCENE_IDENTITY_CANVAS_PX,
        SUPPORTED_REFERENCE_MODES,
    )
    from .layout import build_source_layout
    from .poster_config import (
        IDENTITY_LOCK_PROMPT_FILE,
        INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE,
        JOINT_SCENE_PROMPT_FILE,
        REGIONAL_JOINT_SCENE_PROMPT_FILE,
        build_identity_lock_prompt,
        identity_lock_config,
    )
    from .poster_io import POSTER_ASSETS, load_poster_scope_data, poster_bundle
except ImportError:
    from source_detail import spatial_reference_scales
    from grounding import build_grounding_masks
    from poster_config import GROUNDED_PROMPT_FILE, build_grounded_prompt_snapshot
    from composition import (
        cutout_placements,
        joint_scene_canvas_placements,
        validate_visible_placements,
    )
    from create_comfyui_poster_workflow import output_dimensions
    from generation_contract import (
        CANONICAL_REFERENCE_MODES,
        INDIVIDUAL_SPATIAL_REFERENCE_MEGAPIXELS,
        JOINT_SCENE_CAST_MAX_MEGAPIXELS,
        JOINT_SCENE_IDENTITY_CANVAS_PX,
        SUPPORTED_REFERENCE_MODES,
    )
    from layout import build_source_layout
    from poster_config import (
        IDENTITY_LOCK_PROMPT_FILE,
        INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE,
        JOINT_SCENE_PROMPT_FILE,
        REGIONAL_JOINT_SCENE_PROMPT_FILE,
        build_identity_lock_prompt,
        identity_lock_config,
    )
    from poster_io import POSTER_ASSETS, load_poster_scope_data, poster_bundle
ROOT = Path(__file__).resolve().parents[2]


def build_upper_context_mask(
    width: int,
    height: int,
    placements: list[dict[str, object]],
    manifest: dict[str, Any],
    output_dir: Path,
) -> tuple[int, int]:
    """Write separate sampling and feather masks for identity-lock pass two."""
    config = identity_lock_config(manifest)
    subject_tops = []
    for placement in placements:
        visible_box = placement["image"].getchannel("A").getbbox()
        if visible_box is None:
            raise ValueError("Identity-lock placement has no visible pixels")
        subject_tops.append(int(placement["y"]) + visible_box[1])

    if not subject_tops:
        raise ValueError("Identity lock needs at least one subject placement")
    subject_top = min(subject_tops)
    clearance = round(height * config["subject_clearance_ratio"])
    configured_limit = round(
        height * config["max_protected_start_ratio"]
    )
    protected_start = min(configured_limit, subject_top - clearance)
    transition_height = max(
        1,
        round(height * config["transition_ratio"]),
    )
    transition_start = protected_start - transition_height
    if transition_start < 0 or protected_start <= transition_start:
        raise ValueError(
            "Identity-lock subjects leave no safe upper context region; "
            "reduce their size or artwork.identity_lock transition/clearance"
        )
    if subject_top < protected_start + clearance:
        raise ValueError(
            "Identity-lock subject clearance could not be preserved"
        )

    alpha = Image.new("L", (width, height), 255)
    alpha_draw = ImageDraw.Draw(alpha)
    alpha_draw.rectangle((0, 0, width, transition_start), fill=0)
    for y in range(transition_start, protected_start):
        value = round(255 * (y - transition_start) / transition_height)
        alpha_draw.line((0, y, width, y), fill=value)
    mask_image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    mask_image.putalpha(alpha)
    mask_image.save(
        output_dir / "upper_context_mask.png",
        format="PNG",
        optimize=True,
    )

    # Keep the latent sampling boundary below the visible RGB feather so the
    # second pass cannot expose a straight VAE transition seam.
    latent_overlap = max(16, round(height * 0.02))
    aligned_generation_end = (
        (protected_start + latent_overlap + 15) // 16
    ) * 16
    generation_end = min(
        height - 1,
        subject_top - 1,
        aligned_generation_end,
    )
    generation_alpha = Image.new("L", (width, height), 255)
    ImageDraw.Draw(generation_alpha).rectangle(
        (0, 0, width, generation_end),
        fill=0,
    )
    generation_mask = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 255),
    )
    generation_mask.putalpha(generation_alpha)
    generation_mask.save(
        output_dir / "upper_context_generation_mask.png",
        format="PNG",
        optimize=True,
    )
    return transition_start, protected_start


def build_identity_lock_references(
    scope: str,
    megapixels: float,
    output_dir: Path | None = None,
    *,
    reference_mode: str = "two_pass_source_pixels",
) -> Path:
    """Write only the assets consumed by the identity-lock workflow."""
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    scope_dir = bundle.source_dir
    manifest = bundle.manifest
    reference_dir = output_dir or bundle.work_dir
    reference_dir.mkdir(parents=True, exist_ok=True)
    width, height = output_dimensions(scope, megapixels)
    layout = build_source_layout(
        manifest.get("layout", {}).get("name", "standard_3x3"),
        width_px=width,
        height_px=height,
    )
    placements = cutout_placements(layout, scope_dir)
    validate_visible_placements(
        placements,
        canvas_size=(width, height),
    )

    reference = Image.new(
        "RGBA",
        (width, height),
        (226, 224, 211, 0),
    )
    for placement in placements:
        reference.alpha_composite(
            placement["image"],
            (placement["x"], placement["y"]),
        )
    path = reference_dir / "inpaint_reference.png"
    reference.save(path, format="PNG", optimize=True)
    mask_builder = (
        build_grounding_masks if reference_mode == "grounded_source_pixels"
        else build_upper_context_mask
    )
    mask_builder(
        width,
        height,
        placements,
        manifest,
        reference_dir,
    )
    scope_data = load_poster_scope_data(bundle)
    grounded = reference_mode == "grounded_source_pixels"
    prompt_file = GROUNDED_PROMPT_FILE if grounded else IDENTITY_LOCK_PROMPT_FILE
    prompt = (
        build_grounded_prompt_snapshot(manifest, scope_data)
        if grounded else build_identity_lock_prompt(manifest, scope_data)
    )
    (reference_dir / prompt_file).write_text(
        prompt + "\n",
        encoding="utf-8",
    )
    return path


def _joint_scene_neutral_rgb(manifest: dict[str, Any]) -> tuple[int, int, int]:
    """Return the validated neutral reference-field color."""
    defaults = manifest.get("conditioning", {}).get(
        "identity_defaults",
        {},
    )
    neutral = defaults.get("neutral_rgb", [226, 224, 211])
    if (
        not isinstance(neutral, list)
        or len(neutral) != 3
        or not all(
            isinstance(value, int) and 0 <= value <= 255
            for value in neutral
        )
    ):
        raise ValueError(
            "conditioning.identity_defaults.neutral_rgb must contain "
            "3 RGB integers"
        )
    return tuple(neutral)


def build_joint_scene_references(
    scope: str,
    output_dir: Path | None = None,
    *,
    megapixels: float = 1.0,
    include_cast: bool = True,
    subject_scales: dict[str, float] | None = None,
) -> None:
    """Write unscaled identities and, when requested, the spatial cast."""
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    scope_dir = bundle.source_dir
    manifest = bundle.manifest
    reference_dir = output_dir or bundle.work_dir
    reference_dir.mkdir(parents=True, exist_ok=True)
    cast_megapixels = min(
        megapixels,
        JOINT_SCENE_CAST_MAX_MEGAPIXELS,
    )
    width, height = output_dimensions(bundle.asset_key, cast_megapixels)
    placements = joint_scene_canvas_placements(
        scope_dir,
        layout_name=manifest.get("layout", {}).get(
            "name",
            "standard_3x3",
        ),
        canvas_size=(width, height),
        subject_scales=subject_scales,
    )
    neutral = _joint_scene_neutral_rgb(manifest)
    cast_path = reference_dir / "joint_scene_cast_reference.png"
    if include_cast:
        reference = Image.new(
            "RGBA",
            (width, height),
            (*neutral, 255),
        )
        for placement in placements:
            reference.alpha_composite(
                placement["image"],
                (placement["x"], placement["y"]),
            )
        reference.convert("RGB").save(
            cast_path,
            format="PNG",
            optimize=True,
        )
    else:
        cast_path.unlink(missing_ok=True)
    _write_unscaled_identity_references(
        scope_dir,
        placements,
        reference_dir,
        neutral=neutral,
    )


def build_individual_spatial_joint_references(
    scope: str,
    output_dir: Path | None = None,
) -> list[Path]:
    """Write one poster-shaped identity-and-position image per subject."""
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    scope_dir = bundle.source_dir
    manifest = bundle.manifest
    reference_dir = output_dir or bundle.work_dir
    reference_dir.mkdir(parents=True, exist_ok=True)
    width, height = output_dimensions(
        bundle.asset_key,
        INDIVIDUAL_SPATIAL_REFERENCE_MEGAPIXELS,
    )
    placements = joint_scene_canvas_placements(
        scope_dir,
        layout_name=manifest.get("layout", {}).get(
            "name",
            "standard_3x3",
        ),
        canvas_size=(width, height),
    )
    neutral = _joint_scene_neutral_rgb(manifest)
    outputs = []
    for index, placement in enumerate(placements, start=1):
        reference = Image.new(
            "RGBA",
            (width, height),
            (*neutral, 255),
        )
        reference.alpha_composite(
            placement["image"],
            (int(placement["x"]), int(placement["y"])),
        )
        path = reference_dir / f"individual_spatial_reference_{index}.png"
        reference.convert("RGB").save(path, format="PNG", optimize=True)
        outputs.append(path)
    return outputs


def _write_unscaled_identity_references(
    scope_dir: Path,
    placements: list[dict[str, object]],
    reference_dir: Path,
    *,
    neutral: tuple[int, int, int],
) -> None:
    """Write unscaled source artwork on neutral square RGB canvases."""
    for index, placement in enumerate(placements, start=1):
        source_path = (
            scope_dir
            / "cutouts"
            / str(placement["item"]["file"])
        )
        source = Image.open(source_path).convert("RGBA")
        if (
            source.width > JOINT_SCENE_IDENTITY_CANVAS_PX
            or source.height > JOINT_SCENE_IDENTITY_CANVAS_PX
        ):
            raise ValueError(
                f"Joint-scene identity source {source_path} exceeds the "
                f"{JOINT_SCENE_IDENTITY_CANVAS_PX}px unscaled canvas"
            )
        detail = Image.new(
            "RGB",
            (
                JOINT_SCENE_IDENTITY_CANVAS_PX,
                JOINT_SCENE_IDENTITY_CANVAS_PX,
            ),
            neutral,
        )
        detail.paste(
            source.convert("RGB"),
            (
                (detail.width - source.width) // 2,
                (detail.height - source.height) // 2,
            ),
            source.getchannel("A"),
        )
        detail.save(
            reference_dir / f"identity_reference_{index}.png",
            format="PNG",
            optimize=True,
        )


def _remove_stale(work_dir: Path, patterns: tuple[str, ...]) -> None:
    for pattern in patterns:
        for path in work_dir.glob(pattern):
            path.unlink()


def prepare(
    scope: str,
    megapixels: float = 1.0,
    *,
    generation_mode: str = "joint_scene",
    reference_mode: str | None = None,
) -> Path:
    """Prepare exactly one supported FLUX.2 reference topology."""
    if generation_mode not in {"joint_scene", "identity_lock"}:
        raise ValueError(f"Unsupported FLUX generation mode: {generation_mode}")
    key = ("flux", generation_mode)
    effective_reference_mode = (
        reference_mode
        if reference_mode is not None
        else CANONICAL_REFERENCE_MODES[key]
    )
    if effective_reference_mode not in SUPPORTED_REFERENCE_MODES[key]:
        expected = ", ".join(sorted(SUPPORTED_REFERENCE_MODES[key]))
        raise ValueError(
            f"Unsupported reference mode for {generation_mode}: "
            f"{effective_reference_mode!r}; expected one of {expected}"
        )
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    scope_dir = bundle.source_dir
    work_dir = bundle.work_dir
    required = (
        bundle.manifest_path,
        scope_dir / "cutouts" / "manifest.json",
    )
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)

    cutout_manifest = json.loads(required[-1].read_text(encoding="utf-8"))
    subject_scales = spatial_reference_scales(
        bundle.manifest, cutout_manifest.get("items", []),
        reference_mode=effective_reference_mode,
    )
    if effective_reference_mode == "spatial_source_detail_joint":
        try:
            from .source_detail import validate_source_details
            from .generation_contract import validate_generation_contract
        except ImportError:
            from source_detail import validate_source_details
            from generation_contract import validate_generation_contract
        if megapixels != 2.0:
            raise ValueError("Source detail requires exactly 2 MP")
        validate_generation_contract({
            **bundle.manifest.get("artwork", {}).get("generation", {}),
            "engine": "flux", "mode": "joint_scene",
            "reference_mode": effective_reference_mode,
            "generation_megapixels": megapixels,
        })
        validate_source_details(bundle.manifest, cutout_manifest.get("items", []), scope_dir)
    cutout_files = [
        scope_dir / "cutouts" / item["file"]
        for item in cutout_manifest.get("items", [])
    ]
    if not cutout_files:
        raise ValueError(f"No cutouts listed in {required[-1]}")
    for path in cutout_files:
        if not path.is_file():
            raise FileNotFoundError(path)

    work_dir.mkdir(parents=True, exist_ok=True)
    # Remove both current opposite-mode inputs and old experimental residue.
    _remove_stale(
        work_dir,
        (
            "pokemon_*.png",
            "structure_guide.png",
            "scene_reference.png",
            "structure_reference.png",
            "qwen_identity_reference_*.png",
            "anima_scene_reference.png",
            "identity_core.png",
        ),
    )
    if generation_mode == "joint_scene":
        _remove_stale(
            work_dir,
            (
                "inpaint_reference.png",
                "upper_context_mask.png",
                "upper_context_generation_mask.png",
                "identity_reference_*.png",
                "individual_spatial_reference_*.png",
                "joint_scene_cast_reference.png",
                IDENTITY_LOCK_PROMPT_FILE,
                INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE,
                JOINT_SCENE_PROMPT_FILE,
                REGIONAL_JOINT_SCENE_PROMPT_FILE,
            ),
        )
        if effective_reference_mode == "individual_spatial_joint":
            build_individual_spatial_joint_references(scope, work_dir)
        else:
            build_joint_scene_references(
                scope,
                work_dir,
                megapixels=megapixels,
                subject_scales=subject_scales,
                include_cast=(
                    effective_reference_mode in {"spatial_identity_joint", "spatial_source_detail_joint"}
                ),
            )
    else:
        _remove_stale(
            work_dir,
            (
                "joint_scene_cast_reference.png",
                "identity_reference_*.png",
                "individual_spatial_reference_*.png",
                INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE,
                JOINT_SCENE_PROMPT_FILE,
                REGIONAL_JOINT_SCENE_PROMPT_FILE,
            ),
        )
        _remove_stale(
            work_dir,
            (
                "upper_context_mask.png", "upper_context_generation_mask.png",
                IDENTITY_LOCK_PROMPT_FILE,
            ) if effective_reference_mode == "grounded_source_pixels" else (
                "grounding_mask.png", "grounding_sampling_mask.png",
                "grounding_mask.json", GROUNDED_PROMPT_FILE,
            ),
        )
        build_identity_lock_references(
            scope, megapixels, work_dir,
            reference_mode=effective_reference_mode,
        )
    return work_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", default="Base1")
    parser.add_argument("--megapixels", type=float, default=1.0)
    parser.add_argument(
        "--mode",
        choices=("joint_scene", "identity_lock"),
        default="joint_scene",
    )
    parser.add_argument(
        "--reference-mode",
        choices=(
            "spatial_source_detail_joint",
            "individual_spatial_joint",
            "spatial_identity_joint",
            "regional_identity_joint",
            "two_pass_source_pixels",
            "grounded_source_pixels",
        ),
    )
    args = parser.parse_args()
    print(
        prepare(
            args.scope,
            args.megapixels,
            generation_mode=args.mode,
            reference_mode=args.reference_mode,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
