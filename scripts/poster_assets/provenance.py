"""Reproducible metadata for generated and promoted poster artwork."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

try:
    from .composition import (
        joint_scene_canvas_placements,
        normalized_visible_placement_contract,
    )
    from .fetch_cutouts import (
        select_pokemon,
    )
    from .layout import (
        RASTER_GEOMETRY_CONTRACT_VERSION,
        build_generation_output_layout,
        build_page_layout,
        latent_canvas_dimensions,
    )
    from .generation_contract import (
        CANONICAL_REFERENCE_MODES,
        validate_generation_contract,
    )
    from .poster_config import (
        IDENTITY_LOCK_PROMPT_FILE,
        INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE,
        JOINT_SCENE_PROMPT_FILE,
        REGIONAL_JOINT_SCENE_PROMPT_FILE,
        build_identity_lock_prompt,
        build_individual_spatial_joint_prompt_snapshot,
        build_joint_prompt_snapshot,
        build_regional_joint_prompt_snapshot,
        identity_lock_config,
        joint_scene_conditioning_contract,
    )
    from .poster_io import (
        POSTER_ASSETS,
        SCOPE_DATA,
        PosterBundle,
        load_json,
        load_poster_scope_data,
        poster_bundle,
    )
    from .poster_subject import (
        resolve_poster_subject,
        subject_fingerprint_identity,
    )
except ImportError:
    from composition import (
        joint_scene_canvas_placements,
        normalized_visible_placement_contract,
    )
    from fetch_cutouts import (
        select_pokemon,
    )
    from layout import (
        RASTER_GEOMETRY_CONTRACT_VERSION,
        build_generation_output_layout,
        build_page_layout,
        latent_canvas_dimensions,
    )
    from generation_contract import (
        CANONICAL_REFERENCE_MODES,
        validate_generation_contract,
    )
    from poster_config import (
        IDENTITY_LOCK_PROMPT_FILE,
        INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE,
        JOINT_SCENE_PROMPT_FILE,
        REGIONAL_JOINT_SCENE_PROMPT_FILE,
        build_identity_lock_prompt,
        build_individual_spatial_joint_prompt_snapshot,
        build_joint_prompt_snapshot,
        build_regional_joint_prompt_snapshot,
        identity_lock_config,
        joint_scene_conditioning_contract,
    )
    from poster_io import (
        POSTER_ASSETS,
        SCOPE_DATA,
        PosterBundle,
        load_json,
        load_poster_scope_data,
        poster_bundle,
    )
    from poster_subject import (
        resolve_poster_subject,
        subject_fingerprint_identity,
    )


ROOT = Path(__file__).resolve().parents[2]
FINGERPRINT_SCHEMA_VERSION = 1
GENERATION_PIPELINE_CONTRACT_VERSION = 3
# Cumulative endpoint rasterization changes generation-reference pixels, but
# all promoted overlays already use the same absolute 300-dpi endpoints.
# Therefore it belongs to generation v3 without relabeling pixel-identical
# deterministic overlay v2 outputs.
OVERLAY_PIPELINE_CONTRACT_VERSION = 3
CURRENT_GENERATION_PIPELINE_CONTRACT_VERSIONS = {
    (
        "flux",
        "identity_lock",
        "two_pass_source_pixels",
    ): GENERATION_PIPELINE_CONTRACT_VERSION,
    ("flux", "joint_scene", "spatial_identity_joint"): 7,
    ("flux", "joint_scene", "regional_identity_joint"): 19,
    ("flux", "joint_scene", "individual_spatial_joint"): 9,
}
SUPPORTED_GENERATION_PIPELINE_CONTRACT_VERSIONS = {
    (
        "flux",
        "identity_lock",
        "two_pass_source_pixels",
    ): frozenset({1, 2, 3}),
    ("flux", "joint_scene", "spatial_identity_joint"): frozenset({5, 6, 7}),
    ("flux", "joint_scene", "regional_identity_joint"): frozenset(
        {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19}
    ),
    ("flux", "joint_scene", "individual_spatial_joint"): frozenset({7, 8, 9}),
}
NATURAL_SEPARATION_PIPELINE_MINIMUM = {
    ("flux", "joint_scene", "spatial_identity_joint"): 6,
    ("flux", "joint_scene", "regional_identity_joint"): 7,
    ("flux", "joint_scene", "individual_spatial_joint"): 8,
}
FOREGROUND_AVOIDANCE_PIPELINE_MINIMUM = {
    ("flux", "joint_scene", "spatial_identity_joint"): 7,
    ("flux", "joint_scene", "individual_spatial_joint"): 9,
}
RASTER_GEOMETRY_PIPELINE_MINIMUM = {
    ("flux", "identity_lock"): 3,
    ("flux", "joint_scene"): 4,
}
MODEL_DIRECTORIES = {
    "model": ("diffusion_models", "unet"),
    "encoder": ("text_encoders", "clip"),
    "vae": ("vae",),
    "upscale_model": ("upscale_models",),
}
SOURCE_PIXEL_VALIDATION_KEYS = ("source_pixels", "identity_lock")
JOINT_SCENE_REVIEW_KEY = "joint_scene_visual_review"
JOINT_SCENE_REVIEW_CRITERIA = (
    "exact_cast_count",
    "raw_generation_identity",
    "text_free_output_identity",
    "identity_and_form",
    "silhouette_and_stature",
    "anatomy_and_face",
    "colors_and_markings",
    "placement_and_card_safety",
    "natural_scene_integration",
    "coherent_landscape_occlusion",
)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of a file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_artifact_path(
    comfy_root: Path,
    artifact: str,
    filename: str,
) -> Path:
    """Resolve one model exactly as a standard ComfyUI loader would."""
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe ComfyUI model filename: {filename!r}")
    model_root = (comfy_root / "models").resolve()
    candidates = [
        (model_root / directory / relative).resolve()
        for directory in MODEL_DIRECTORIES[artifact]
        if (model_root / directory / relative).is_file()
    ]
    candidates = [
        path for path in candidates if path.is_relative_to(model_root)
    ]
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"Expected exactly one ComfyUI {artifact} named {filename!r}, "
            f"found {len(candidates)} below {model_root}"
        )
    return candidates[0]


def add_model_artifact_hashes(
    comfy_root: Path,
    generation: dict[str, Any],
) -> dict[str, Any]:
    """Hash the actual local model files selected for one workflow."""
    enriched = dict(generation)
    for artifact in MODEL_DIRECTORIES:
        filename = enriched.get(artifact)
        if filename:
            path = model_artifact_path(comfy_root, artifact, str(filename))
            enriched[f"{artifact}_sha256"] = sha256_file(path)
    return enriched


def required_model_artifact_hashes(
    generation: dict[str, Any],
) -> tuple[str, ...]:
    """Return hash fields for every model artifact the engine selects."""
    return tuple(
        f"{artifact}_sha256"
        for artifact in MODEL_DIRECTORIES
        if generation.get(artifact)
    )


def require_exact_source_pixel_validation(
    run_metadata: dict[str, Any],
    *,
    allow_legacy: bool = False,
) -> dict[str, Any]:
    """Require a successful exact-source audit for every promotable engine.

    ``identity_lock`` is the legacy field used by the already promoted FLUX.2
    bundles. New runs use the engine-neutral ``source_pixels`` key. Callers may
    accept the old field only while validating or refreshing an existing
    promoted FLUX identity-lock bundle.
    """
    validation = run_metadata.get("validation")
    if not isinstance(validation, dict):
        raise ValueError(
            "Poster candidate lacks its exact source-pixel validation record"
        )
    is_current_record = "source_pixels" in validation
    record = (
        validation.get("source_pixels")
        if is_current_record
        else validation.get("identity_lock")
    )
    if not isinstance(record, dict):
        raise ValueError(
            "Poster candidate lacks its exact source-pixel validation record"
        )
    if not is_current_record:
        generation = run_metadata.get("generation")
        if (
            not allow_legacy
            or not isinstance(generation, dict)
            or generation.get("engine") != "flux"
            or generation.get("mode") != "identity_lock"
        ):
            raise ValueError(
                "New poster candidates require the bound source-pixel "
                "validation record"
            )
    opaque_pixels = record.get("opaque_pixels")
    changed_pixels = record.get("changed_pixels")
    if (
        record.get("method") != "exact_opaque_source_pixels"
        or record.get("passed") is not True
        or isinstance(changed_pixels, bool)
        or not isinstance(changed_pixels, int)
        or changed_pixels != 0
        or isinstance(opaque_pixels, bool)
        or not isinstance(opaque_pixels, int)
        or opaque_pixels <= 0
    ):
        raise ValueError(
            "Poster candidate exact source-pixel validation did not pass"
        )
    if is_current_record:
        width = record.get("width")
        height = record.get("height")
        reference_sha256 = record.get("reference_sha256")
        artwork_sha256 = record.get("artwork_sha256")
        valid_sha256 = lambda value: (
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )
        if (
            record.get("stage") != "raw_generation"
            or isinstance(width, bool)
            or not isinstance(width, int)
            or width <= 0
            or isinstance(height, bool)
            or not isinstance(height, int)
            or height <= 0
            or not valid_sha256(reference_sha256)
            or not valid_sha256(artwork_sha256)
        ):
            raise ValueError(
                "Poster candidate source-pixel audit lacks its raw-stage "
                "image binding"
            )
        raw_artwork = run_metadata.get("raw_artwork")
        if (
            not isinstance(raw_artwork, dict)
            or raw_artwork.get("sha256") != artwork_sha256
            or raw_artwork.get("width") != width
            or raw_artwork.get("height") != height
        ):
            raise ValueError(
                "Poster candidate source-pixel audit does not match its raw "
                "artwork record"
            )
        inputs = run_metadata.get("inputs")
        audit_reference = (
            inputs.get("source_pixel_audit_reference")
            if isinstance(inputs, dict)
            else None
        )
        if (
            not isinstance(audit_reference, dict)
            or audit_reference.get("sha256") != reference_sha256
            or audit_reference.get("width") != width
            or audit_reference.get("height") != height
        ):
            raise ValueError(
                "Poster candidate source-pixel audit does not match its "
                "recorded audit reference"
            )
    return record


def _valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_review_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def recorded_repository_path(record: dict[str, Any]) -> Path:
    """Resolve a recorded project file without allowing path traversal."""
    filename = record.get("file")
    if not isinstance(filename, str) or not filename:
        raise ValueError("Recorded file path is missing")
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe recorded file path: {filename!r}")
    resolved = (ROOT / relative).resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError(f"Recorded file escapes repository: {filename!r}")
    return resolved


def _verify_recorded_image(
    record: dict[str, Any],
    path: Path,
    *,
    label: str,
) -> dict[str, Any]:
    """Require a provenance image record to match the actual file."""
    actual = file_record(path, image=True)
    for field in (
        "bytes",
        "sha256",
        "pixel_sha256",
        "width",
        "height",
    ):
        if record.get(field) != actual.get(field):
            raise ValueError(
                f"Joint-scene {label} record does not match {path}: {field}"
            )
    return actual


def _joint_scene_review_inputs(
    run_metadata: dict[str, Any],
    *,
    artwork_path: Path | None = None,
    raw_artwork_path: Path | None = None,
) -> dict[str, Any]:
    """Return fully validated values bound by a joint-scene review."""
    generation = run_metadata.get("generation")
    if not isinstance(generation, dict):
        raise ValueError("Joint-scene candidate lacks generation metadata")
    validate_generation_contract(generation)
    if (
        generation.get("engine") != "flux"
        or generation.get("mode") != "joint_scene"
    ):
        raise ValueError(
            "Joint-scene visual approval applies only to flux/joint_scene"
        )
    artwork = run_metadata.get("source_artwork")
    raw_artwork = run_metadata.get("raw_artwork")
    inputs = run_metadata.get("inputs")
    if (
        not isinstance(artwork, dict)
        or not isinstance(raw_artwork, dict)
        or not isinstance(inputs, dict)
    ):
        raise ValueError(
            "Joint-scene candidate lacks bound artwork or input provenance"
        )
    for label, record in (
        ("text-free artwork", artwork),
        ("raw artwork", raw_artwork),
    ):
        if (
            not _valid_sha256(record.get("sha256"))
            or not _valid_sha256(record.get("pixel_sha256"))
            or not isinstance(record.get("width"), int)
            or record["width"] <= 0
            or not isinstance(record.get("height"), int)
            or record["height"] <= 0
        ):
            raise ValueError(
                f"Joint-scene {label} provenance is incomplete or invalid"
            )
    if (artwork_path is None) != (raw_artwork_path is None):
        raise ValueError(
            "Joint-scene file verification needs both raw and text-free paths"
        )
    if artwork_path is not None and raw_artwork_path is not None:
        _verify_recorded_image(
            artwork,
            artwork_path,
            label="text-free artwork",
        )
        _verify_recorded_image(
            raw_artwork,
            raw_artwork_path,
            label="raw artwork",
        )

    fingerprint = inputs.get("generation_fingerprint")
    if not fingerprint_record_is_valid(fingerprint):
        raise ValueError(
            "Joint-scene candidate requires a valid generation fingerprint"
        )
    components = fingerprint.get("components", {})
    subjects = components.get("source_subject_ids")
    fingerprint_cutouts = components.get("cutouts")
    cutouts = inputs.get("cutouts")
    if (
        not isinstance(subjects, list)
        or not subjects
        or not isinstance(fingerprint_cutouts, list)
        or not isinstance(cutouts, list)
        or len(subjects) != len(fingerprint_cutouts)
        or len(subjects) != len(cutouts)
    ):
        raise ValueError(
            "Joint-scene candidate lacks one source identity per subject"
        )
    source_hashes = []
    source_pixel_hashes = []
    for cutout, fingerprint_cutout in zip(cutouts, fingerprint_cutouts):
        if not isinstance(cutout, dict) or not isinstance(
            fingerprint_cutout, dict
        ):
            raise ValueError("Joint-scene source identity records are invalid")
        source_hash = cutout.get("sha256")
        source_pixel_hash = cutout.get("pixel_sha256")
        fingerprint_pixel_hash = fingerprint_cutout.get("pixel_sha256")
        if (
            not _valid_sha256(source_hash)
            or not _valid_sha256(source_pixel_hash)
            or not _valid_sha256(fingerprint_pixel_hash)
            or source_pixel_hash != fingerprint_pixel_hash
        ):
            raise ValueError(
                "Joint-scene source identities do not match the generation "
                "fingerprint"
            )
        source_hashes.append(source_hash)
        source_pixel_hashes.append(source_pixel_hash)
    return {
        "artwork": artwork,
        "raw_artwork": raw_artwork,
        "subjects": subjects,
        "source_hashes": source_hashes,
        "source_pixel_hashes": source_pixel_hashes,
        "fingerprint_sha256": fingerprint["sha256"],
    }


def approve_joint_scene_visual_review(
    run_metadata: dict[str, Any],
    *,
    artwork_path: Path,
    raw_artwork_path: Path,
    reviewer_kind: str,
) -> dict[str, Any]:
    """Bind explicit review of both raw and output joint-scene artwork."""
    if reviewer_kind not in ("human", "agent"):
        raise ValueError("Joint-scene reviewer kind must be human or agent")
    bound = _joint_scene_review_inputs(
        run_metadata,
        artwork_path=artwork_path,
        raw_artwork_path=raw_artwork_path,
    )
    validation = run_metadata.setdefault("validation", {})
    if not isinstance(validation, dict):
        raise ValueError("Poster validation record must be a mapping")
    artwork = bound["artwork"]
    raw_artwork = bound["raw_artwork"]
    record = {
        "method": f"{reviewer_kind}_identity_and_scene_review",
        "passed": True,
        "stage": "raw_and_text_free_print_artwork",
        "approval_source": "explicit_promotion_flag",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_artwork_sha256": artwork["sha256"],
        "reviewed_artwork_pixel_sha256": artwork["pixel_sha256"],
        "raw_artwork_sha256": raw_artwork["sha256"],
        "raw_artwork_pixel_sha256": raw_artwork["pixel_sha256"],
        "generation_fingerprint_sha256": bound["fingerprint_sha256"],
        "source_subject_ids": bound["subjects"],
        "source_cutout_sha256": bound["source_hashes"],
        "source_cutout_pixel_sha256": bound["source_pixel_hashes"],
        "criteria": list(JOINT_SCENE_REVIEW_CRITERIA),
    }
    validation[JOINT_SCENE_REVIEW_KEY] = record
    return record


def require_joint_scene_visual_review(
    run_metadata: dict[str, Any],
    *,
    artwork_path: Path | None = None,
    raw_artwork_path: Path | None = None,
) -> dict[str, Any]:
    """Require a complete review bound to raw, output, and identity pixels."""
    validation = run_metadata.get("validation")
    record = (
        validation.get(JOINT_SCENE_REVIEW_KEY)
        if isinstance(validation, dict)
        else None
    )
    if not isinstance(record, dict):
        raise ValueError(
            "Joint-scene candidate lacks explicit visual identity approval"
        )
    bound = _joint_scene_review_inputs(
        run_metadata,
        artwork_path=artwork_path,
        raw_artwork_path=raw_artwork_path,
    )
    artwork = bound["artwork"]
    raw_artwork = bound["raw_artwork"]
    if (
        record.get("method") not in (
            "human_identity_and_scene_review",
            "agent_identity_and_scene_review",
        )
        or record.get("passed") is not True
        or record.get("stage") != "raw_and_text_free_print_artwork"
        or record.get("approval_source") != "explicit_promotion_flag"
        or not _valid_review_timestamp(record.get("reviewed_at"))
        or record.get("criteria") != list(JOINT_SCENE_REVIEW_CRITERIA)
        or record.get("reviewed_artwork_sha256") != artwork["sha256"]
        or record.get("reviewed_artwork_pixel_sha256")
        != artwork["pixel_sha256"]
        or record.get("raw_artwork_sha256") != raw_artwork["sha256"]
        or record.get("raw_artwork_pixel_sha256")
        != raw_artwork["pixel_sha256"]
        or record.get("generation_fingerprint_sha256")
        != bound["fingerprint_sha256"]
        or record.get("source_subject_ids") != bound["subjects"]
        or record.get("source_cutout_sha256") != bound["source_hashes"]
        or record.get("source_cutout_pixel_sha256")
        != bound["source_pixel_hashes"]
    ):
        raise ValueError(
            "Joint-scene visual identity approval is incomplete or stale"
        )
    return record


def display_path(path: Path) -> str:
    """Use a repository-relative path without leaking machine-specific roots."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def file_record(path: Path, *, image: bool = False) -> dict[str, Any]:
    """Describe one immutable input or output file."""
    if not path.is_file():
        raise FileNotFoundError(path)
    record: dict[str, Any] = {
        "file": display_path(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if image:
        with Image.open(path) as loaded:
            record["width"] = loaded.width
            record["height"] = loaded.height
            dpi = loaded.info.get("dpi")
            if dpi:
                record["dpi"] = [round(float(value), 4) for value in dpi]
        record.update(image_pixel_record(path))
    return record


def _canonical_value(value: Any) -> Any:
    """Return a JSON-safe value with stable mapping-key semantics."""
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            canonical_key = str(key)
            if canonical_key in normalized:
                raise ValueError(
                    "Canonical fingerprint mapping contains colliding keys: "
                    f"{key!r}"
                )
            normalized[canonical_key] = _canonical_value(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(
        f"Unsupported canonical fingerprint value: {type(value).__name__}"
    )


def fingerprint_record(
    components: dict[str, Any],
    *,
    schema_version: int = FINGERPRINT_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Build one versioned SHA-256 record from semantic components."""
    if not isinstance(schema_version, int) or schema_version <= 0:
        raise ValueError("Fingerprint schema_version must be positive")
    normalized = _canonical_value(components)
    payload = {
        "schema_version": schema_version,
        "components": normalized,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return {
        "schema_version": schema_version,
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "components": normalized,
    }


def fingerprint_record_is_valid(record: object) -> bool:
    """Return whether a stored fingerprint is internally well formed."""
    if not isinstance(record, dict):
        return False
    schema_version = record.get("schema_version")
    components = record.get("components")
    expected = record.get("sha256")
    if (
        not isinstance(schema_version, int)
        or not isinstance(components, dict)
        or not isinstance(expected, str)
    ):
        return False
    try:
        rebuilt = fingerprint_record(
            components,
            schema_version=schema_version,
        )
    except (TypeError, ValueError):
        return False
    return rebuilt["sha256"] == expected


def current_generation_pipeline_contract_version(
    generation: dict[str, Any],
) -> int:
    """Return the current graph contract for the selected engine and mode."""
    family = _generation_pipeline_family(generation)
    return CURRENT_GENERATION_PIPELINE_CONTRACT_VERSIONS.get(family, 1)


def _generation_pipeline_family(
    generation: dict[str, Any],
) -> tuple[str, str, str]:
    """Resolve historical missing reference modes to their canonical topology."""
    engine = str(generation.get("engine", ""))
    mode = str(generation.get("mode", ""))
    reference_mode = generation.get("reference_mode")
    if reference_mode is None:
        reference_mode = CANONICAL_REFERENCE_MODES.get(
            (engine, mode),
            "",
        )
    return engine, mode, str(reference_mode)


def validate_generation_pipeline_contract_version(
    generation: dict[str, Any],
    version: int,
) -> None:
    """Reject contracts outside the explicit compatibility policy."""
    family = _generation_pipeline_family(generation)
    supported = SUPPORTED_GENERATION_PIPELINE_CONTRACT_VERSIONS.get(family)
    if supported is None or version not in supported:
        raise ValueError(
            "Unsupported generation pipeline contract "
            f"{family[0]}/{family[1]}/{family[2]} v{version}"
        )


def generation_fingerprint_pipeline_contract_version(
    record: dict[str, Any],
    generation: dict[str, Any] | None = None,
) -> int:
    """Read the historical graph contract represented by a fingerprint."""
    contract = record.get("components", {}).get("pipeline_contract")
    version = contract.get("version") if isinstance(contract, dict) else None
    if (
        not isinstance(version, int)
        or version <= 0
        or contract.get("name") != "poster_generation"
    ):
        raise ValueError(
            "Generation fingerprint lacks a valid pipeline contract"
        )
    if generation is not None:
        validate_generation_pipeline_contract_version(generation, version)
    return version


def image_pixel_record(
    path: Path,
    *,
    mode: str = "RGBA",
) -> dict[str, Any]:
    """Hash decoded image pixels instead of incidental PNG serialization."""
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as loaded:
        image = loaded.convert(mode)
        width, height = image.size
        pixels = image.tobytes()
    header = json.dumps(
        {
            "height": height,
            "mode": mode,
            "width": width,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    digest = hashlib.sha256(
        b"binder-pokedex-image-pixels-v1\0"
        + header
        + b"\0"
        + pixels
    ).hexdigest()
    return {
        "mode": mode,
        "width": width,
        "height": height,
        "pixel_sha256": digest,
    }


def _bundle_and_scope_data(
    target: str | PosterBundle,
    *,
    poster_assets: Path | None,
    scope_data_dir: Path | None,
) -> tuple[PosterBundle, dict[str, Any]]:
    bundle = (
        target
        if isinstance(target, PosterBundle)
        else poster_bundle(
            target,
            poster_assets=poster_assets or POSTER_ASSETS,
        )
    )
    scope_data = load_poster_scope_data(
        bundle,
        scope_data_dir=scope_data_dir or SCOPE_DATA,
    )
    return bundle, scope_data


def _layout_generation_contract(
    manifest: dict[str, Any],
    generation: dict[str, Any],
    pipeline_contract_version: int,
) -> dict[str, Any]:
    layout_name = str(
        manifest.get("layout", {}).get("name", "standard_3x3")
    )
    layout = build_page_layout(layout_name)
    text_cells = manifest.get("text_cells", {})
    if not isinstance(text_cells, dict):
        raise ValueError("text_cells must be a mapping")
    title = text_cells.get(
        "title",
        {"row": 1, "column": max(1, (layout.columns + 1) // 2)},
    )
    information = text_cells.get(
        "set_info",
        {
            "row": min(2, layout.rows),
            "column": max(1, (layout.columns + 1) // 2),
        },
    )
    if not isinstance(title, dict) or not isinstance(information, dict):
        raise ValueError("Poster text-cell configuration must be mappings")
    contract = {
        "name": layout.name,
        "columns": layout.columns,
        "rows": layout.rows,
        # Only positions condition the generated safe areas. Panel dimensions
        # are deterministic overlay inputs and intentionally live elsewhere.
        "safe_cells": {
            "title": {
                "row": int(title["row"]),
                "column": int(title["column"]),
            },
            "set_info": {
                "row": int(information["row"]),
                "column": int(information["column"]),
            },
        },
    }
    family = (
        str(generation.get("engine", "")),
        str(generation.get("mode", "")),
    )
    geometry_minimum = RASTER_GEOMETRY_PIPELINE_MINIMUM.get(family)
    if (
        geometry_minimum is None
        or pipeline_contract_version < geometry_minimum
    ):
        return contract

    megapixels = float(generation.get("generation_megapixels", 1.0))
    generation_width, generation_height = latent_canvas_dimensions(
        layout_name,
        megapixels,
    )
    generation_layout = build_page_layout(
        layout_name,
        width_px=generation_width,
        height_px=generation_height,
    )
    raster_contract: dict[str, Any] = {
        "name": "cumulative_physical_endpoints",
        "version": RASTER_GEOMETRY_CONTRACT_VERSION,
        "generation_canvas_px": [
            generation_layout.width_px,
            generation_layout.height_px,
        ],
        "generation_column_spans_px": [
            list(span) for span in generation_layout.column_spans
        ],
        "generation_row_spans_px": [
            list(span) for span in generation_layout.row_spans
        ],
    }
    output_layout = build_generation_output_layout(
        layout_name,
        generation,
    )
    raster_contract.update(
        output_canvas_px=[
            output_layout.width_px,
            output_layout.height_px,
        ],
        output_column_spans_px=[
            list(span) for span in output_layout.column_spans
        ],
        output_row_spans_px=[
            list(span) for span in output_layout.row_spans
        ],
    )
    contract["raster_geometry"] = raster_contract
    return contract


def _expected_subject_ids(
    manifest: dict[str, Any],
    scope_data: dict[str, Any],
) -> list[int | dict[str, Any]]:
    pokemon = manifest.get("pokemon", {})
    if not isinstance(pokemon, dict):
        raise ValueError("pokemon must be a mapping")
    strategy = pokemon.get("strategy", "featured_from_scope")
    if strategy != "featured_from_scope":
        raise ValueError(f"Unsupported pokemon.strategy {strategy!r}")
    layout = build_page_layout(
        manifest.get("layout", {}).get("name", "standard_3x3")
    )
    count = pokemon.get("count", "auto_from_layout_columns")
    if count == "auto_from_layout_columns":
        requested = layout.columns
    elif isinstance(count, int) and count > 0:
        requested = count
    else:
        raise ValueError(
            "pokemon.count must be a positive integer or "
            "'auto_from_layout_columns'"
        )
    selected = select_pokemon(
        manifest,
        scope_data,
        requested,
        {},
    )
    return [
        subject_fingerprint_identity(item)
        for item in selected
    ]


def _cutout_components(
    bundle: PosterBundle,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cutout_dir = bundle.source_dir / "cutouts"
    manifest_path = cutout_dir / "manifest.json"
    payload = load_json(manifest_path)
    items = payload.get("items", [])
    if not isinstance(items, list) or not items:
        raise ValueError(f"No cutouts listed in {manifest_path}")
    normalized_items: list[dict[str, Any]] = []
    raw_items: list[dict[str, Any]] = []
    seen_subjects: set[tuple[str, int, int]] = set()
    artwork_species: dict[tuple[str, int], int] = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid cutout item in {manifest_path}")
        pokemon_id = item.get("pokemon_id")
        filename = item.get("file")
        if not isinstance(pokemon_id, int) or not isinstance(filename, str):
            raise ValueError(f"Invalid cutout identity in {manifest_path}")
        subject = resolve_poster_subject(item)
        subject_key = subject.selection_key()
        if subject_key in seen_subjects:
            raise ValueError(
                f"Duplicate poster subject in {manifest_path}: {subject_key}"
            )
        seen_subjects.add(subject_key)
        artwork_key = subject.artwork_key()
        mapped_species = artwork_species.get(artwork_key)
        if mapped_species is not None and mapped_species != subject.species_id:
            raise ValueError(
                f"Official artwork {artwork_key} maps to multiple species in "
                f"{manifest_path}: {mapped_species} and {subject.species_id}"
            )
        artwork_species[artwork_key] = subject.species_id
        if item.get("url") != subject.image_url:
            raise ValueError(
                f"Cutout URL does not match poster subject in {manifest_path}"
            )
        relative = Path(filename)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe cutout file in {manifest_path}: {filename}")
        image_path = (cutout_dir / relative).resolve()
        if not image_path.is_relative_to(cutout_dir.resolve()):
            raise ValueError(f"Cutout escapes its asset directory: {filename}")
        normalized_item = {
            "pokemon_id": pokemon_id,
            **image_pixel_record(image_path),
        }
        if subject.is_special_form:
            normalized_item["poster_subject"] = {
                "source": subject.source,
                "official_artwork_id": subject.official_artwork_id,
            }
        normalized_items.append(normalized_item)
        raw_items.append(item)
    return normalized_items, raw_items


def _effective_generation_prompt(
    bundle: PosterBundle,
    scope_data: dict[str, Any],
    generation: dict[str, Any],
    cutout_items: list[dict[str, Any]],
    pipeline_contract_version: int,
) -> str:
    engine = str(generation.get("engine", ""))
    mode = str(generation.get("mode", ""))
    if engine == "flux" and mode == "identity_lock":
        return build_identity_lock_prompt(bundle.manifest, scope_data)
    if engine == "flux" and mode == "joint_scene":
        generation_megapixels = generation.get("generation_megapixels")
        if (
            not isinstance(generation_megapixels, (int, float))
            or isinstance(generation_megapixels, bool)
            or generation_megapixels <= 0
        ):
            raise ValueError(
                "Joint-scene generation_megapixels must be positive"
            )
        layout_name = str(
            bundle.manifest.get("layout", {}).get(
                "name",
                "standard_3x3",
            )
        )
        width, height = latent_canvas_dimensions(
            layout_name,
            float(generation_megapixels),
        )
        placement_contract = normalized_visible_placement_contract(
            joint_scene_canvas_placements(
                bundle.source_dir,
                layout_name=layout_name,
                canvas_size=(width, height),
            ),
            canvas_size=(width, height),
        )
        reference_mode = generation.get("reference_mode")
        family = _generation_pipeline_family(generation)
        separation_minimum = NATURAL_SEPARATION_PIPELINE_MINIMUM.get(family)
        prefer_natural_separation = (
            separation_minimum is not None
            and pipeline_contract_version >= separation_minimum
        )
        avoidance_minimum = FOREGROUND_AVOIDANCE_PIPELINE_MINIMUM.get(family)
        avoid_foreground_intersections = (
            avoidance_minimum is not None
            and pipeline_contract_version >= avoidance_minimum
        )
        if reference_mode == "individual_spatial_joint":
            return build_individual_spatial_joint_prompt_snapshot(
                bundle.manifest,
                scope_data,
                cutout_items,
                placement_contract=placement_contract,
                prefer_natural_separation=prefer_natural_separation,
                avoid_foreground_intersections=avoid_foreground_intersections,
            )
        if reference_mode == "regional_identity_joint":
            return build_regional_joint_prompt_snapshot(
                bundle.manifest,
                scope_data,
                cutout_items,
                placement_contract=placement_contract,
                prefer_natural_separation=prefer_natural_separation,
                global_scene_everywhere=pipeline_contract_version >= 8,
                repeat_global_scene_in_regions=(
                    pipeline_contract_version >= 10
                ),
                local_scene_continuity=pipeline_contract_version >= 12,
                abstract_region_language=pipeline_contract_version >= 15,
                minimal_local_scene_context=(
                    pipeline_contract_version >= 16
                ),
                identity_only_local_context=(
                    pipeline_contract_version >= 17
                ),
            )
        return build_joint_prompt_snapshot(
            bundle.manifest,
            scope_data,
            cutout_items,
            placement_contract=placement_contract,
            prefer_natural_separation=prefer_natural_separation,
            avoid_foreground_intersections=avoid_foreground_intersections,
        )

    raise ValueError(
        f"Unsupported poster generation contract: {engine}/{mode}"
    )


def build_generation_fingerprint(
    target: str | PosterBundle,
    *,
    poster_assets: Path | None = None,
    scope_data_dir: Path | None = None,
    generation: dict[str, Any] | None = None,
    pipeline_contract_version: int | None = None,
) -> dict[str, Any]:
    """Fingerprint only inputs capable of changing generated poster pixels."""
    bundle, scope_data = _bundle_and_scope_data(
        target,
        poster_assets=poster_assets,
        scope_data_dir=scope_data_dir,
    )
    manifest = bundle.manifest
    artwork = manifest.get("artwork", {})
    if not isinstance(artwork, dict):
        raise ValueError("artwork must be a mapping")
    configured_generation = artwork.get("generation", {})
    effective_generation = (
        generation
        if generation is not None
        else configured_generation
    )
    if not isinstance(effective_generation, dict):
        raise ValueError("artwork.generation must be a mapping")
    validate_generation_contract(effective_generation)
    contract_version = (
        current_generation_pipeline_contract_version(effective_generation)
        if pipeline_contract_version is None
        else pipeline_contract_version
    )
    if not isinstance(contract_version, int) or contract_version <= 0:
        raise ValueError("Pipeline contract version must be positive")
    validate_generation_pipeline_contract_version(
        effective_generation,
        contract_version,
    )
    cutouts, raw_cutout_items = _cutout_components(bundle)
    expected_subjects = _expected_subject_ids(manifest, scope_data)
    actual_subjects = [
        subject_fingerprint_identity(item)
        for item in raw_cutout_items
    ]
    if actual_subjects != expected_subjects:
        raise ValueError(
            f"Cutout subjects {actual_subjects} do not match current source "
            f"subjects {expected_subjects} for {bundle.asset_key}"
        )
    prompt = _effective_generation_prompt(
        bundle,
        scope_data,
        effective_generation,
        raw_cutout_items,
        contract_version,
    )
    components = {
        "pipeline_contract": {
            "name": "poster_generation",
            "version": contract_version,
        },
        "layout": _layout_generation_contract(
            manifest,
            effective_generation,
            contract_version,
        ),
        "scene": artwork.get("scene", {}),
        "generation": effective_generation,
        "pokemon": manifest.get("pokemon", {}),
        "effective_prompt": {
            "encoding": "utf-8",
            "sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        },
        "source_subject_ids": expected_subjects,
        "cutouts": cutouts,
    }
    is_joint_scene = (
        effective_generation.get("engine") == "flux"
        and effective_generation.get("mode") == "joint_scene"
    )
    if not is_joint_scene:
        components["conditioning"] = manifest.get("conditioning", {})
        components["identity_lock"] = identity_lock_config(manifest)
    else:
        components["joint_scene_conditioning"] = (
            joint_scene_conditioning_contract(
                manifest,
                raw_cutout_items,
                reference_mode=str(
                    effective_generation.get("reference_mode", "")
                ),
            )
        )
    return fingerprint_record(components)


def rebuild_generation_fingerprint_from_recorded_sources(
    target: str | PosterBundle,
    recorded: dict[str, Any],
    *,
    poster_assets: Path | None = None,
    scope_data_dir: Path | None = None,
) -> dict[str, Any]:
    """Rebuild current semantics while retaining audited downloaded pixels.

    Promoted provenance owns the immutable cutout pixel hashes. Revalidating a
    promoted master therefore does not need to redownload those source PNGs;
    current configuration, source selection, layout and pipeline contracts are
    still recomputed and compared with the recorded fingerprint.
    """
    if not fingerprint_record_is_valid(recorded):
        raise ValueError("Malformed recorded generation fingerprint")
    bundle, scope_data = _bundle_and_scope_data(
        target,
        poster_assets=poster_assets,
        scope_data_dir=scope_data_dir,
    )
    components = recorded["components"]
    generation = bundle.manifest.get("artwork", {}).get("generation", {})
    if not isinstance(generation, dict):
        raise ValueError("artwork.generation must be a mapping")
    validate_generation_contract(generation)
    contract_version = generation_fingerprint_pipeline_contract_version(
        recorded,
        generation,
    )
    expected_subjects = _expected_subject_ids(bundle.manifest, scope_data)
    if components.get("source_subject_ids") != expected_subjects:
        raise ValueError(
            "Recorded cutout subjects do not match the current source "
            f"selection for {bundle.asset_key}"
        )
    cutouts = components.get("cutouts")
    if not isinstance(cutouts, list) or len(cutouts) != len(expected_subjects):
        raise ValueError("Recorded generation fingerprint has invalid cutouts")
    for cutout in cutouts:
        if (
            not isinstance(cutout, dict)
            or not isinstance(cutout.get("pokemon_id"), int)
            or not isinstance(cutout.get("pixel_sha256"), str)
        ):
            raise ValueError(
                "Recorded generation fingerprint has invalid cutout pixels"
            )

    engine = str(generation.get("engine", ""))
    mode = str(generation.get("mode", ""))
    if engine == "flux" and mode == "identity_lock":
        prompt = build_identity_lock_prompt(bundle.manifest, scope_data)
        effective_prompt = {
            "encoding": "utf-8",
            "sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        }
    else:
        effective_prompt = components.get("effective_prompt")
        if not isinstance(effective_prompt, dict):
            raise ValueError(
                "Recorded generation fingerprint lacks its prompt audit"
            )

    current_components: dict[str, Any] = {
        "pipeline_contract": {
            "name": "poster_generation",
            "version": contract_version,
        },
        "layout": _layout_generation_contract(
            bundle.manifest,
            generation,
            contract_version,
        ),
        "scene": bundle.manifest.get("artwork", {}).get("scene", {}),
        "generation": generation,
        "pokemon": bundle.manifest.get("pokemon", {}),
        "effective_prompt": effective_prompt,
        "source_subject_ids": expected_subjects,
        "cutouts": cutouts,
    }
    if engine == "flux" and mode == "joint_scene":
        current_components["joint_scene_conditioning"] = (
            joint_scene_conditioning_contract(
                bundle.manifest,
                [{} for _subject in expected_subjects],
                reference_mode=str(generation.get("reference_mode", "")),
            )
        )
    else:
        current_components["conditioning"] = bundle.manifest.get(
            "conditioning",
            {},
        )
        current_components["identity_lock"] = identity_lock_config(
            bundle.manifest
        )
    return fingerprint_record(
        current_components,
        schema_version=int(recorded["schema_version"]),
    )


def _safe_overlay_asset(bundle: PosterBundle, filename: str) -> Path:
    relative = Path(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe poster overlay asset: {filename!r}")
    path = (bundle.source_dir / relative).resolve()
    if not path.is_relative_to(bundle.source_dir.resolve()):
        raise ValueError(f"Poster overlay asset escapes its scope: {filename!r}")
    return path


def build_overlay_fingerprint(
    target: str | PosterBundle,
    *,
    poster_assets: Path | None = None,
    scope_data_dir: Path | None = None,
    recorded: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fingerprint cheap deterministic overlay inputs independently."""
    try:
        from .finalize_comfyui_poster import (
            PLAIN_TITLE_RENDERER_CONTRACT,
            SUPPORTED_LANGUAGES,
            info_panel_values,
            inline_title_logo,
            readable_overlay_text,
            resolved_title_text,
            title_logo_file,
        )
    except ImportError:
        from finalize_comfyui_poster import (
            PLAIN_TITLE_RENDERER_CONTRACT,
            SUPPORTED_LANGUAGES,
            info_panel_values,
            inline_title_logo,
            readable_overlay_text,
            resolved_title_text,
            title_logo_file,
        )

    bundle, scope_data = _bundle_and_scope_data(
        target,
        poster_assets=poster_assets,
        scope_data_dir=scope_data_dir,
    )
    manifest = bundle.manifest
    content = manifest.get("text_content", {})
    if not isinstance(content, dict):
        raise ValueError("text_content must be a mapping")
    content_mode = str(content.get("mode", "set_summary"))
    text_cells = manifest.get("text_cells", {})
    if not isinstance(text_cells, dict):
        raise ValueError("text_cells must be a mapping")
    title_config = text_cells.get("title", {})
    if not isinstance(title_config, dict):
        raise ValueError("text_cells.title must be a mapping")
    language_components: dict[str, Any] = {}
    logo_records: dict[str, Any] = {}
    recorded_logo_records = (
        recorded.get("components", {}).get("logo_pixels", {})
        if fingerprint_record_is_valid(recorded)
        else {}
    )
    for language in SUPPORTED_LANGUAGES:
        logo_file = title_logo_file(manifest, language)
        header_text: str | None = None
        if logo_file:
            logo_path = _safe_overlay_asset(bundle, str(logo_file))
            logo_record = (
                image_pixel_record(logo_path)
                if logo_path.is_file()
                else recorded_logo_records.get(language)
            )
            if not isinstance(logo_record, dict):
                raise FileNotFoundError(
                    f"Poster title logo not found: {logo_path}"
                )
            logo_records[language] = logo_record
            title: dict[str, Any] = {
                "kind": "logo",
                "pixel_sha256": logo_record["pixel_sha256"],
            }
        else:
            header_text = resolved_title_text(scope_data, language)
            resolved = inline_title_logo(header_text)
            if resolved is not None:
                token, logo_path = resolved
                logo_record = image_pixel_record(logo_path)
                logo_records[f"inline:{token}"] = logo_record
                title = {
                    "kind": "inline_logo",
                    "value": header_text,
                    "token": token,
                    "pixel_sha256": logo_record["pixel_sha256"],
                }
            else:
                title = {
                    "kind": "text",
                    "renderer": PLAIN_TITLE_RENDERER_CONTRACT,
                    "value": readable_overlay_text(header_text),
                }
        language_components[language] = {
            "title": title,
            "information": list(
                info_panel_values(
                    scope_data,
                    language,
                    content_mode,
                    header_text=header_text,
                )
            ),
        }
    components = {
        "pipeline_contract": {
            "name": "poster_overlay",
            "version": OVERLAY_PIPELINE_CONTRACT_VERSION,
        },
        "layout_name": manifest.get("layout", {}).get(
            "name",
            "standard_3x3",
        ),
        "text_cells": text_cells,
        "text_content": content,
        "languages": language_components,
        "logo_pixels": logo_records,
    }
    return fingerprint_record(components)


def prompt_path_for_generation(
    work_dir: Path,
    generation: dict[str, Any],
    workflow_path: Path | None = None,
) -> Path:
    engine = str(generation.get("engine", ""))
    mode = str(generation.get("mode", ""))
    if engine == "flux" and mode == "identity_lock":
        prompt_dir = workflow_path.parent if workflow_path is not None else work_dir
        return prompt_dir / IDENTITY_LOCK_PROMPT_FILE
    if engine == "flux" and mode == "joint_scene":
        prompt_dir = workflow_path.parent if workflow_path is not None else work_dir
        reference_mode = generation.get("reference_mode")
        if reference_mode == "individual_spatial_joint":
            return prompt_dir / INDIVIDUAL_SPATIAL_JOINT_PROMPT_FILE
        if reference_mode == "regional_identity_joint":
            return prompt_dir / REGIONAL_JOINT_SCENE_PROMPT_FILE
        return prompt_dir / JOINT_SCENE_PROMPT_FILE
    raise ValueError(
        f"Unsupported poster generation contract: {engine}/{mode}"
    )


def generation_input_records(
    scope: str,
    workflow_path: Path,
    generation: dict[str, Any],
) -> dict[str, Any]:
    """Collect the exact lightweight files that conditioned one generation."""
    validate_generation_contract(generation)
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    scope_dir = bundle.source_dir
    work_dir = bundle.work_dir
    cutout_manifest_path = scope_dir / "cutouts" / "manifest.json"
    cutout_manifest = json.loads(cutout_manifest_path.read_text(encoding="utf-8"))
    cutouts = [
        file_record(scope_dir / "cutouts" / str(item["file"]), image=True)
        for item in cutout_manifest.get("items", [])
    ]
    if not cutouts:
        raise ValueError(f"No cutouts listed in {cutout_manifest_path}")

    if (
        generation.get("engine") == "flux"
        and generation.get("mode") == "identity_lock"
    ):
        references = [
            file_record(work_dir / "inpaint_reference.png", image=True),
            file_record(work_dir / "upper_context_mask.png", image=True),
            file_record(
                work_dir / "upper_context_generation_mask.png",
                image=True,
            ),
        ]
    elif (
        generation.get("engine") == "flux"
        and generation.get("mode") == "joint_scene"
    ):
        reference_mode = generation.get("reference_mode")
        if reference_mode == "individual_spatial_joint":
            references = [
                file_record(
                    work_dir / f"individual_spatial_reference_{index}.png",
                    image=True,
                )
                for index in range(1, len(cutouts) + 1)
            ]
        else:
            references = []
        if reference_mode == "spatial_identity_joint":
            references.append(
                file_record(
                    work_dir / "joint_scene_cast_reference.png",
                    image=True,
                )
            )
        if reference_mode != "individual_spatial_joint":
            references.extend(
                file_record(
                    work_dir / f"identity_reference_{index}.png",
                    image=True,
                )
                for index in range(1, len(cutouts) + 1)
            )
    else:
        raise ValueError(
            "Unsupported poster generation contract: "
            f"{generation.get('engine')}/{generation.get('mode')}"
        )

    records = {
        "scope_manifest": file_record(bundle.manifest_path),
        "prompt": file_record(
            prompt_path_for_generation(
                work_dir,
                generation,
                workflow_path,
            ),
        ),
        "cutout_manifest": file_record(cutout_manifest_path),
        "cutouts": cutouts,
        "references": references,
        "workflow": file_record(workflow_path),
    }
    if not (
        generation.get("engine") == "flux"
        and generation.get("mode") == "joint_scene"
    ):
        records["source_pixel_audit_reference"] = file_record(
            work_dir / "inpaint_reference.png",
            image=True,
        )
    return records


def write_run_metadata(
    scope: str,
    artwork_path: Path,
    workflow_path: Path,
    generation: dict[str, Any],
    output_path: Path | None = None,
    *,
    raw_artwork_path: Path | None = None,
    additional_workflows: dict[str, Path] | None = None,
    validation: dict[str, Any] | None = None,
) -> Path:
    """Write a sidecar for one generated, text-free candidate."""
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    output_path = output_path or artwork_path.with_suffix(".run.json")
    inputs = generation_input_records(scope, workflow_path, generation)
    inputs["generation_fingerprint"] = build_generation_fingerprint(
        bundle,
        generation=generation,
    )
    inputs["overlay_fingerprint"] = build_overlay_fingerprint(bundle)
    for label, path in (additional_workflows or {}).items():
        inputs[label] = file_record(path)
    payload = {
        "schema_version": 1,
        "kind": "poster_generation_run",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": scope,
        "source_scope": bundle.scope,
        "poster_id": bundle.poster_id,
        "section_id": bundle.section_id,
        "generation": generation,
        "inputs": inputs,
        "source_artwork": file_record(artwork_path, image=True),
    }
    if raw_artwork_path is not None:
        payload["raw_artwork"] = file_record(raw_artwork_path, image=True)
    if validation:
        payload["validation"] = validation
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def load_run_metadata(path: Path, artwork_path: Path) -> dict[str, Any]:
    """Load run metadata and verify that it belongs to the reviewed artwork.

    A promoted provenance file may be used directly when refreshing a cheap
    deterministic overlay; its embedded generation run remains the source of
    truth for the unchanged text-free artwork.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    is_promoted_container = payload.get("kind") == "promoted_poster"
    promoted_artwork = None
    if is_promoted_container:
        outputs = payload.get("outputs")
        if isinstance(outputs, dict):
            promoted_artwork = outputs.get("artwork")
        payload = payload.get("run")
        if not isinstance(payload, dict):
            raise ValueError(
                f"Promoted poster has no embedded run metadata: {path}"
            )
    if payload.get("schema_version") != 1 or payload.get("kind") != (
        "poster_generation_run"
    ):
        raise ValueError(f"Unsupported poster run metadata: {path}")
    expected_hash = payload.get("source_artwork", {}).get("sha256")
    actual_hash = sha256_file(artwork_path)
    if expected_hash != actual_hash and isinstance(promoted_artwork, dict):
        # Promotion may re-encode a PNG without changing its reviewed pixels.
        # Accept only the registered output bytes and the original pixel hash;
        # a fresh generation run still requires the original byte hash below.
        actual = _verify_recorded_image(
            promoted_artwork, artwork_path, label="promoted artwork",
        )
        if actual["pixel_sha256"] != payload.get("source_artwork", {}).get("pixel_sha256"):
            raise ValueError("Promoted artwork pixels differ from the reviewed source")
        expected_hash = promoted_artwork["sha256"]
    if expected_hash != actual_hash:
        raise ValueError(
            f"Run metadata does not describe {artwork_path}: "
            f"expected {expected_hash}, got {actual_hash}"
        )
    generation = payload.get("generation")
    if (
        isinstance(generation, dict)
        and generation.get("engine") == "flux"
        and generation.get("mode") == "joint_scene"
        and not is_promoted_container
    ):
        source_record = payload.get("source_artwork")
        raw_record = payload.get("raw_artwork")
        if not isinstance(source_record, dict):
            raise ValueError(
                "Joint-scene run lacks its text-free artwork record"
            )
        _verify_recorded_image(
            source_record,
            artwork_path,
            label="text-free artwork",
        )
        if not isinstance(raw_record, dict):
            raise ValueError(
                "Joint-scene run lacks its raw artwork record"
            )
        raw_path = recorded_repository_path(raw_record)
        _verify_recorded_image(
            raw_record,
            raw_path,
            label="raw artwork",
        )
    return payload


def promoted_provenance(
    *,
    scope: str,
    name: str,
    language: str,
    run_metadata: dict[str, Any],
    artwork_path: Path,
    stable_artwork_path: Path | None = None,
) -> dict[str, Any]:
    """Build the stable audit record for one durable text-free master."""
    artwork_record = file_record(artwork_path, image=True)
    if stable_artwork_path is not None:
        artwork_record["file"] = display_path(stable_artwork_path)
    return {
        "schema_version": 2,
        "kind": "promoted_poster",
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "scope": scope,
        "source_scope": run_metadata.get("source_scope", scope),
        "poster_id": run_metadata.get("poster_id", scope),
        "section_id": run_metadata.get("section_id"),
        "asset_name": name,
        "review_language": language,
        "run": run_metadata,
        "storage": {
            "schema_version": 1,
            "durable_outputs": ["artwork"],
            "reproducible_sources": "downloaded_to_ignored_workspace",
            "derivatives": "regenerated_in_ignored_workspace",
        },
        "outputs": {"artwork": artwork_record},
    }
