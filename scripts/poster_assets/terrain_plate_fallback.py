"""Validate the reviewed landscape-plate/exact-source fallback provenance.

This deliberately separate contract describes an exceptional, multi-stage
fallback. It never labels its final composite as a FLUX joint-scene one-shot.
The large, ignored render jobs remain local; the promoted record retains their
immutable hashes without machine-specific paths or copied source images.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from PIL import Image

try:
    from .layout import build_print_layout
    from .provenance import image_pixel_record, sha256_file
except ImportError:
    from layout import build_print_layout
    from provenance import image_pixel_record, sha256_file


METHOD = "terrain_plate_exact_source_composite"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
# The exact source files were hash-bound in the tracked 2026-09-14 P16
# source-comparison record, before the terrain-B artwork was generated.
REVIEWED_P16_CUTOUTS = (
    (
        "pokemon_382_artwork_10077_primal_kyogre.png",
        "226507487da40a44b8df44c4fd04ecc6398b8873e792dd2ce31ecfa7a8e3777b",
        "bdc782a89b7fa4936ced73d2fc7fbaac0867103c044194a3bc9578410fe87053",
    ),
    (
        "pokemon_383_artwork_10078_primal_groudon.png",
        "fd0a131143a3289cde178438f5ea0249ff62cacb6dbb6742c95544c7c42aad5a",
        "3097d54d4f86d699df12cfa858dd627517776f0971773c03953fd34e3784a69b",
    ),
)


def _hash(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"Terrain fallback lacks valid {key}")
    return value


def validate_terrain_fallback(
    bundle: Any,
    payload: dict[str, Any],
    expected_subjects: list[dict[str, Any]],
    current_overlay_sha256: str,
) -> dict[str, Any]:
    """Validate a promoted exact-source composite before PDF consumption."""
    if (
        payload.get("schema_version") != 4
        or payload.get("kind") != "promoted_poster"
        or payload.get("scope") != bundle.asset_key
        or payload.get("source_scope") != bundle.scope
        or payload.get("poster_id") != bundle.poster_id
        or payload.get("section_id") != bundle.section_id
        or payload.get("method") != METHOD
        or bundle.manifest.get("artwork", {}).get("fallback_method") != METHOD
        or bundle.asset_key != "ExGen2/sections/primal"
    ):
        raise ValueError("Wrong terrain-fallback identity or method")
    if payload.get("source_subject_ids") != expected_subjects:
        raise ValueError("Terrain-fallback source subjects changed")

    artwork_config = bundle.manifest["artwork"]
    routed_name = artwork_config.get("promoted_file")
    if routed_name != bundle.artwork_file or Path(str(routed_name)).name != routed_name:
        raise ValueError("Terrain-fallback artwork routing changed")
    artwork_path = bundle.asset_dir / routed_name
    output = payload.get("artwork")
    if not isinstance(output, dict) or not artwork_path.is_file():
        raise ValueError("Missing terrain-fallback artwork")
    layout = build_print_layout(bundle.manifest["layout"]["name"], 300)
    if (
        output.get("width") != layout.width_px
        or output.get("height") != layout.height_px
        or output.get("dpi") != 300
        or _hash(output, "sha256") != sha256_file(artwork_path)
        or _hash(output, "pixel_sha256")
        != image_pixel_record(artwork_path)["pixel_sha256"]
    ):
        raise ValueError("Terrain-fallback print master changed")
    with Image.open(artwork_path) as image:
        dpi = image.info.get("dpi")
        if image.size != (layout.width_px, layout.height_px) or not dpi or any(
            abs(float(value) - 300) > 0.1 for value in dpi
        ):
            raise ValueError("Terrain-fallback print geometry or DPI changed")

    sources = payload.get("source_cutouts")
    if not isinstance(sources, list) or len(sources) != len(REVIEWED_P16_CUTOUTS):
        raise ValueError("Terrain fallback lacks the selected source cutouts")
    for source, (reviewed_name, reviewed_hash, reviewed_pixel_hash) in zip(
        sources, REVIEWED_P16_CUTOUTS, strict=True,
    ):
        if not isinstance(source, dict):
            raise ValueError("Invalid terrain-fallback source cutout")
        name = source.get("file")
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".png"):
            raise ValueError("Unsafe terrain-fallback source cutout name")
        _hash(source, "sha256")
        _hash(source, "pixel_sha256")
        if (
            name != reviewed_name
            or source["sha256"] != reviewed_hash
            or source["pixel_sha256"] != reviewed_pixel_hash
        ):
            raise ValueError("Terrain-fallback source differs from reviewed P16 source")
        cached = bundle.source_dir / "cutouts" / name
        if cached.is_file() and (
            sha256_file(cached) != source["sha256"]
            or image_pixel_record(cached)["pixel_sha256"] != source["pixel_sha256"]
        ):
            raise ValueError("Terrain-fallback source cache changed")

    render = payload.get("render")
    if not isinstance(render, dict):
        raise ValueError("Terrain fallback lacks render evidence")
    terrain, upscale = render.get("terrain"), render.get("upscale")
    if not isinstance(terrain, dict) or not isinstance(upscale, dict):
        raise ValueError("Terrain fallback lacks both immutable render stages")
    for key in (
        "workflow_sha256", "run_sha256", "log_sha256", "output_sha256",
        "model_sha256", "encoder_sha256", "vae_sha256",
    ):
        _hash(terrain, key)
    for key in (
        "workflow_sha256", "run_sha256", "log_sha256", "input_sha256",
        "output_sha256", "model_sha256",
    ):
        _hash(upscale, key)
    generation = artwork_config["generation"]
    if any(
        terrain[f"{key}_sha256"] != generation[f"{key}_sha256"]
        for key in ("model", "encoder", "vae")
    ):
        raise ValueError("Terrain-fallback model pins differ from manifest")

    composition = payload.get("composition")
    if not isinstance(composition, dict):
        raise ValueError("Terrain fallback lacks composition evidence")
    for key in (
        "terrain_plate_sha256", "upscaled_terrain_sha256",
        "raw_composite_sha256",
    ):
        _hash(composition, key)
    if (
        terrain["output_sha256"] != composition["terrain_plate_sha256"]
        or upscale["input_sha256"] != terrain["output_sha256"]
        or upscale["output_sha256"] != composition["upscaled_terrain_sha256"]
    ):
        raise ValueError("Terrain-fallback stage hashes do not chain")
    raw_audit = composition.get("source_pixel_audit")
    print_audit = composition.get("print_source_pixel_audit")
    if (
        not isinstance(raw_audit, dict)
        or raw_audit.get("method") != "exact_opaque_source_pixels"
        or type(raw_audit.get("opaque_pixels")) is not int
        or raw_audit["opaque_pixels"] <= 0
        or raw_audit.get("changed_pixels") != 0
        or not isinstance(print_audit, dict)
        or type(print_audit.get("opaque_source_pixels")) is not int
        or print_audit["opaque_source_pixels"] <= 0
        or print_audit.get("changed_opaque_source_pixels") != 0
    ):
        raise ValueError("Terrain fallback lacks passing exact-source pixel audits")
    review = payload.get("review")
    if (
        not isinstance(review, dict)
        or not str(review.get("decision", "")).startswith("operator_accepted_")
        or _hash(review, "artwork_sha256") != output["sha256"]
        or not isinstance(review.get("card_sha256"), list)
        or len(review["card_sha256"]) != layout.rows * layout.columns
        or any(not isinstance(value, str) or not _SHA256.fullmatch(value)
               for value in review["card_sha256"])
    ):
        raise ValueError("Terrain fallback lacks exact-image and nine-card approval")
    if (
        _hash(payload, "overlay_fingerprint_sha256")
        != current_overlay_sha256
    ):
        raise ValueError("Terrain-fallback localized overlay inputs changed")
    return {
        "scope": bundle.asset_key,
        "artwork": artwork_path,
        "cards": layout.rows * layout.columns,
        "dimensions": (layout.width_px, layout.height_px),
        "card_dimensions_by_cell": tuple(
            (layout.cell(row, column).width, layout.cell(row, column).height)
            for row in range(1, layout.rows + 1)
            for column in range(1, layout.columns + 1)
        ),
        "effective_dpi": (300.0, 300.0),
        "identity_validation_method": "exact_source_pixels_reviewed_composite",
        "identity_pixels": print_audit["opaque_source_pixels"],
        "overlay_fingerprint_current": True,
        "localized_overlay_approved": True,
        "composition_kind": METHOD,
    }
