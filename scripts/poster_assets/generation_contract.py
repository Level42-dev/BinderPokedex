"""Cross-cutting invariants for poster generation metadata."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


CANONICAL_REFERENCE_MODES = {
    ("flux", "identity_lock"): "two_pass_source_pixels",
    ("flux", "joint_scene"): "individual_spatial_joint",
}
SUPPORTED_REFERENCE_MODES = {
    ("flux", "identity_lock"): frozenset(
        {"two_pass_source_pixels", "grounded_source_pixels"}
    ),
    ("flux", "joint_scene"): frozenset(
        {
            "individual_spatial_joint",
            "spatial_identity_joint",
            "regional_identity_joint",
        }
    ),
}
JOINT_SCENE_CAST_MAX_MEGAPIXELS = 0.5
JOINT_SCENE_IDENTITY_CANVAS_PX = 512
INDIVIDUAL_SPATIAL_REFERENCE_MEGAPIXELS = 0.5


def is_joint_scene_generation(
    generation: Mapping[str, Any],
) -> bool:
    """Return whether metadata describes the unified FLUX scene redraw."""
    return (
        generation.get("engine") == "flux"
        and generation.get("mode") == "joint_scene"
    )


def validate_generation_reference_contract(
    generation: Mapping[str, Any],
) -> None:
    """Require each protected FLUX mode's supported reference semantics."""
    key = (generation.get("engine"), generation.get("mode"))
    supported_modes = SUPPORTED_REFERENCE_MODES.get(key)
    if supported_modes is None:
        supported = ", ".join(
            f"{engine}/{mode}"
            for engine, mode in CANONICAL_REFERENCE_MODES
        )
        raise ValueError(
            "Unsupported poster generation contract "
            f"{key[0]}/{key[1]}; expected one of: {supported}"
        )
    actual = generation.get("reference_mode")
    if actual not in supported_modes:
        expected = ", ".join(sorted(repr(mode) for mode in supported_modes))
        raise ValueError(
            "Generation reference contract is incompatible with "
            f"{key[0]}/{key[1]}: expected one of {expected}, got "
            f"{actual!r}"
        )
    if is_grounded_generation(generation) and generation.get("steps", 4) != 4:
        raise ValueError("Grounded source pixels requires four sampling steps")


def is_grounded_generation(generation: Mapping[str, Any]) -> bool:
    """Identify the source-protected ground-edit graph independently of upscale."""
    return (
        generation.get("engine") == "flux"
        and generation.get("mode") == "identity_lock"
        and generation.get("reference_mode") == "grounded_source_pixels"
    )


def requires_visual_review(generation: Mapping[str, Any]) -> bool:
    """Keep visual eligibility separate from joint-scene upscale semantics."""
    return (
        is_joint_scene_generation(generation)
        or is_grounded_generation(generation)
    )


def validate_generation_output_contract(
    generation: Mapping[str, Any],
) -> None:
    """Prevent semantic post-processing after a unified final scene pass."""
    if not is_joint_scene_generation(generation):
        return
    output_method = generation.get("output_method")
    if output_method is None:
        conflicting = tuple(
            field
            for field in (
                "output_dpi",
                "output_megapixels",
                "upscale_model",
                "upscale_model_sha256",
            )
            if generation.get(field) is not None
        )
        if conflicting:
            raise ValueError(
                "flux/joint_scene output fields require output_method: "
                f"{', '.join(conflicting)}"
            )
        return
    if output_method != "lanczos":
        raise ValueError(
            "flux/joint_scene requires deterministic Lanczos output; a "
            "learned model upscaler could alter reviewed character identity"
        )
    output_dpi = generation.get("output_dpi")
    output_megapixels = generation.get("output_megapixels")
    has_dpi = output_dpi is not None
    has_megapixels = output_megapixels is not None
    if has_dpi == has_megapixels:
        raise ValueError(
            "flux/joint_scene Lanczos output requires exactly one of "
            "output_dpi or output_megapixels"
        )
    if has_dpi and (
        not isinstance(output_dpi, int)
        or isinstance(output_dpi, bool)
        or output_dpi <= 0
    ):
        raise ValueError(
            "flux/joint_scene output_dpi must be a positive integer"
        )
    if has_megapixels and (
        not isinstance(output_megapixels, (int, float))
        or isinstance(output_megapixels, bool)
        or output_megapixels <= 0
    ):
        raise ValueError(
            "flux/joint_scene output_megapixels must be positive"
        )
    forbidden = tuple(
        field
        for field in ("upscale_model", "upscale_model_sha256")
        if generation.get(field) is not None
    )
    if forbidden:
        raise ValueError(
            "flux/joint_scene Lanczos output must not select a learned "
            f"upscaler: {', '.join(forbidden)}"
        )


def validate_generation_contract(
    generation: Mapping[str, Any],
) -> None:
    """Validate all generation invariants shared across entry points."""
    if not isinstance(generation, Mapping):
        raise TypeError("generation must be a mapping")
    validate_generation_reference_contract(generation)
    validate_generation_output_contract(generation)


def validate_promotable_generation_contract(
    generation: Mapping[str, Any],
) -> None:
    """Require the exact print contract used by promoted poster assets."""
    validate_generation_contract(generation)
    if generation.get("output_dpi") != 300:
        raise ValueError(
            "Promoted posters require the exact 300-dpi print raster"
        )
    if generation.get("output_megapixels") is not None:
        raise ValueError(
            "Promoted posters cannot use a preview output_megapixels target"
        )

    mode = generation.get("mode")
    expected_method = (
        "lanczos" if mode == "joint_scene" else "model_upscale"
    )
    if generation.get("output_method") != expected_method:
        raise ValueError(
            f"flux/{mode} promotion requires output_method "
            f"{expected_method!r}"
        )
    if mode == "identity_lock":
        for field in ("upscale_model", "upscale_model_sha256"):
            value = generation.get(field)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    "flux/identity_lock promotion requires "
                    f"{field}"
                )
        upscale_hash = str(generation["upscale_model_sha256"])
        if len(upscale_hash) != 64 or any(
            character not in "0123456789abcdef"
            for character in upscale_hash
        ):
            raise ValueError(
                "flux/identity_lock promotion requires "
                "upscale_model_sha256 as a lowercase SHA-256 digest"
            )


def requires_generation_fingerprint(
    generation: Mapping[str, Any],
) -> bool:
    """Return whether legacy, unfingerprinted provenance is impossible."""
    return requires_visual_review(generation)
