#!/usr/bin/env python3
"""Validate a promoted poster bundle against provenance and print geometry."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

try:
    from .generation_contract import is_grounded_generation
    from .poster_config import build_grounded_prompt_snapshot
    from .provenance import require_grounding_pixel_validation
    from .fetch_cutouts import (
        resolve_requested_count,
        select_pokemon,
        scope_featured_elements,
        unique_by_poster_subject,
    )
    from .generation_contract import (
        is_joint_scene_generation,
        requires_generation_fingerprint,
        requires_visual_review,
        validate_promotable_generation_contract,
    )
    from .layout import (
        build_generation_output_layout,
        build_page_layout,
        effective_dpi,
    )
    from .poster_config import build_identity_lock_prompt
    from .provenance import (
        ROOT,
        rebuild_generation_fingerprint_from_recorded_sources,
        build_overlay_fingerprint,
        current_generation_pipeline_contract_version,
        fingerprint_record_is_valid,
        generation_fingerprint_pipeline_contract_version,
        image_pixel_record,
        required_model_artifact_hashes,
        require_exact_source_pixel_validation,
        require_joint_scene_visual_review,
        sha256_file,
    )
    from .poster_io import (
        POSTER_ASSETS,
        POSTER_CONFIGS,
        PosterBundle,
        load_poster_scope_data,
        poster_bundle,
        poster_bundles_for_scope,
    )
    from .poster_subject import (
        resolve_poster_subject,
        subject_fingerprint_identity,
    )
except ImportError:
    from generation_contract import is_grounded_generation
    from poster_config import build_grounded_prompt_snapshot
    from provenance import require_grounding_pixel_validation
    from fetch_cutouts import (
        resolve_requested_count,
        select_pokemon,
        scope_featured_elements,
        unique_by_poster_subject,
    )
    from generation_contract import (
        is_joint_scene_generation,
        requires_generation_fingerprint,
        requires_visual_review,
        validate_promotable_generation_contract,
    )
    from layout import (
        build_generation_output_layout,
        build_page_layout,
        effective_dpi,
    )
    from poster_config import build_identity_lock_prompt
    from provenance import (
        ROOT,
        rebuild_generation_fingerprint_from_recorded_sources,
        build_overlay_fingerprint,
        current_generation_pipeline_contract_version,
        fingerprint_record_is_valid,
        generation_fingerprint_pipeline_contract_version,
        image_pixel_record,
        required_model_artifact_hashes,
        require_exact_source_pixel_validation,
        require_joint_scene_visual_review,
        sha256_file,
    )
    from poster_io import (
        POSTER_ASSETS,
        POSTER_CONFIGS,
        PosterBundle,
        load_poster_scope_data,
        poster_bundle,
        poster_bundles_for_scope,
    )
    from poster_subject import (
        resolve_poster_subject,
        subject_fingerprint_identity,
    )


POSTER_LANGUAGES = (
    "de",
    "en",
    "fr",
    "es",
    "it",
    "ja",
    "ko",
    "zh_hans",
    "zh_hant",
)


def enabled_poster_bundles(
    poster_assets: Path = POSTER_ASSETS,
    poster_configs: Path | None = None,
) -> list[PosterBundle]:
    """Return every PDF-enabled bundle with its resolved routing intact."""
    enabled: list[PosterBundle] = []
    config_root = poster_configs or (
        POSTER_CONFIGS if poster_assets == POSTER_ASSETS else poster_assets
    )
    for scope_dir in sorted(
        (path for path in config_root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    ):
        for bundle in poster_bundles_for_scope(
            scope_dir.name,
            poster_assets=poster_assets,
            poster_configs=config_root,
        ):
            if bundle.pdf_enabled:
                enabled.append(bundle)
    return enabled


def enabled_poster_scopes(
    poster_assets: Path = POSTER_ASSETS,
) -> list[str]:
    """Return stable asset keys for every PDF-enabled poster bundle."""
    return [
        bundle.asset_key
        for bundle in enabled_poster_bundles(poster_assets)
    ]


def _validate_record(
    record: dict[str, Any],
    *,
    expected_path: Path | None = None,
) -> Path:
    path = expected_path or ROOT / str(record["file"])
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_hash = sha256_file(path)
    if actual_hash != record.get("sha256"):
        raise ValueError(
            f"Hash mismatch for {path}: {actual_hash} != {record.get('sha256')}"
        )
    if path.stat().st_size != record.get("bytes"):
        raise ValueError(f"Size mismatch for {path}")
    if "width" in record or "height" in record:
        with Image.open(path) as image:
            if image.size != (record.get("width"), record.get("height")):
                raise ValueError(
                    f"Dimension mismatch for {path}: {image.size} != "
                    f"{(record.get('width'), record.get('height'))}"
                )
    return path


def _image_dpi(path: Path) -> tuple[float, float]:
    with Image.open(path) as image:
        dpi = image.info.get("dpi")
    if not dpi:
        raise ValueError(f"Missing print dpi metadata: {path}")
    return float(dpi[0]), float(dpi[1])


def _validate_source_subjects(
    bundle,
    scope_data: dict[str, Any],
    provenance: dict[str, Any] | None = None,
) -> None:
    """Keep every promoted cutout cast bound to the current source data."""
    sections = scope_data.get("sections", {})
    if not isinstance(sections, dict) or not sections:
        raise ValueError(f"{bundle.asset_key} source sections are invalid")
    section = (
        next(iter(sections.values()))
        if bundle.section_id is not None
        else None
    )
    layout = build_page_layout(
        str(bundle.manifest.get("layout", {}).get("name", "standard_3x3"))
    )
    count = resolve_requested_count(bundle.manifest, layout)
    try:
        selected = select_pokemon(
            bundle.manifest,
            scope_data,
            count,
            {},
        )
        expected_subjects = [
            subject_fingerprint_identity(item) for item in selected
        ]
        expected_subject_keys = {
            resolve_poster_subject(item).selection_key()
            for item in selected
        }
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError(
            f"{bundle.asset_key} source featured_elements are invalid"
        ) from error
    if section is not None:
        featured = section.get("featured_elements")
        if not isinstance(featured, list):
            raise ValueError(
                f"{bundle.asset_key} source section needs featured_elements"
            )
        featured_items = scope_featured_elements(scope_data)
        unique_featured = unique_by_poster_subject(featured_items)
        if len(unique_featured) != len(featured):
            raise ValueError(
                f"{bundle.asset_key} source featured_elements are not unique"
            )
        featured_subjects = {
            resolve_poster_subject(item).selection_key()
            for item in unique_featured
        }
        compact_featured_match = (
            layout.name == "standard_2x2"
            and len(featured_subjects) > count
            and expected_subject_keys.issubset(featured_subjects)
        )
        if not compact_featured_match and (
            len(featured_subjects) > count
            or not featured_subjects.issubset(expected_subject_keys)
        ):
            raise ValueError(
                f"{bundle.asset_key} source featured_elements do not match "
                "the selected Pokemon and fallback candidates"
            )
    actual_subjects = (
        (provenance or {}).get("run", {})
        .get("inputs", {})
        .get("generation_fingerprint", {})
        .get("components", {})
        .get("source_subject_ids")
    )
    if not isinstance(actual_subjects, list):
        legacy_manifest = bundle.source_dir / "cutouts" / "manifest.json"
        if legacy_manifest.is_file():
            legacy_items = json.loads(
                legacy_manifest.read_text(encoding="utf-8")
            ).get("items")
            if isinstance(legacy_items, list):
                actual_subjects = [
                    subject_fingerprint_identity(item)
                    for item in legacy_items
                    if isinstance(item, dict)
                ]
        if not isinstance(actual_subjects, list):
            raise ValueError(
                f"{bundle.asset_key} provenance lacks audited cutout subjects"
            )
    if actual_subjects != expected_subjects:
        raise ValueError(
            f"{bundle.asset_key} audited cutouts {actual_subjects} do not match "
            f"current featured_elements {expected_subjects}"
        )
    if bundle.scope == "Pokedex" and section is not None:
        for field in ("title", "subtitle", "description"):
            localized = section.get(field)
            missing = [
                language
                for language in POSTER_LANGUAGES
                if not isinstance(localized, dict)
                or not localized.get(language)
            ]
            if missing:
                raise ValueError(
                    f"{bundle.asset_key} lacks {field} translations for "
                    f"{', '.join(missing)}"
                )


def validate(target: str | PosterBundle) -> dict[str, Any]:
    bundle = (
        poster_bundle(target, poster_assets=POSTER_ASSETS)
        if isinstance(target, str)
        else target
    )
    scope = bundle.asset_key
    scope_dir = bundle.asset_dir
    manifest_path = bundle.manifest_path
    manifest = bundle.manifest
    artwork_config = manifest.get("artwork", {})
    provenance_file = artwork_config.get(
        "provenance_file",
        "poster-flux2-provenance.json",
    )
    provenance_path = scope_dir / provenance_file
    payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    schema_version = payload.get("schema_version")
    if schema_version not in {1, 2}:
        raise ValueError(
            f"Unsupported promoted provenance version: {provenance_path}"
        )
    if payload.get("kind") != "promoted_poster" or payload.get("scope") != scope:
        raise ValueError(f"Invalid promoted provenance: {provenance_path}")
    if bundle.section_id is not None and (
        payload.get("source_scope") != bundle.scope
        or payload.get("poster_id") != bundle.poster_id
        or payload.get("section_id") != bundle.section_id
    ):
        raise ValueError(
            f"Promoted provenance targets the wrong aggregate section: "
            f"{provenance_path}"
        )
    scope_data = load_poster_scope_data(bundle)
    _validate_source_subjects(bundle, scope_data, payload)

    configured_generation = artwork_config.get("generation", {})
    recorded_generation = payload.get("run", {}).get("generation", {})
    if not isinstance(configured_generation, dict) or not isinstance(
        recorded_generation, dict
    ):
        raise ValueError("Promoted generation metadata must be a mapping")
    validate_promotable_generation_contract(configured_generation)
    validate_promotable_generation_contract(recorded_generation)
    if recorded_generation != configured_generation:
        raise ValueError(
            f"Generation metadata drift between {manifest_path} and "
            f"{provenance_path}"
        )
    run_inputs = payload.get("run", {}).get("inputs", {})
    if not isinstance(run_inputs, dict):
        raise ValueError(
            f"Promoted provenance lacks generation inputs: {provenance_path}"
        )
    recorded_fingerprint = run_inputs.get("generation_fingerprint")
    if (
        recorded_fingerprint is None
        and requires_generation_fingerprint(recorded_generation)
    ):
        raise ValueError(
            "Joint-scene provenance cannot be legacy or unfingerprinted"
        )
    generation_fingerprint_current: bool | None
    generation_pipeline_contract_version: int | None
    generation_pipeline_contract_status: str
    if recorded_fingerprint is not None:
        if not fingerprint_record_is_valid(recorded_fingerprint):
            raise ValueError(
                f"Malformed generation fingerprint in {provenance_path}"
            )
        generation_pipeline_contract_version = (
            generation_fingerprint_pipeline_contract_version(
                recorded_fingerprint,
                recorded_generation,
            )
        )
        current_fingerprint = rebuild_generation_fingerprint_from_recorded_sources(
            bundle,
            recorded_fingerprint,
        )
        if (
            recorded_fingerprint.get("sha256")
            != current_fingerprint["sha256"]
        ):
            raise ValueError(
                "Generation input fingerprint drift between the current "
                f"scope and {provenance_path}"
            )
        generation_fingerprint_current = True
        current_contract = current_generation_pipeline_contract_version(
            recorded_generation
        )
        generation_pipeline_contract_status = (
            "current"
            if generation_pipeline_contract_version == current_contract
            else "accepted_legacy"
        )
    else:
        generation_fingerprint_current = None
        generation_pipeline_contract_version = None
        generation_pipeline_contract_status = "legacy_unfingerprinted"
    recorded_manifest = (
        run_inputs.get("scope_manifest", {})
    )
    if (
        recorded_fingerprint is None
        and recorded_manifest.get("sha256") != sha256_file(manifest_path)
    ):
        raise ValueError(
            f"Scope manifest drift between {manifest_path} and "
            f"{provenance_path}"
        )
    missing_hashes = [
        key
        for key in required_model_artifact_hashes(recorded_generation)
        if not recorded_generation.get(key)
    ]
    if missing_hashes:
        raise ValueError(
            f"Missing promoted model hashes: {', '.join(missing_hashes)}"
        )
    is_joint_scene = is_joint_scene_generation(recorded_generation)
    needs_visual_review = requires_visual_review(recorded_generation)
    visual_validation = (
        require_joint_scene_visual_review(payload.get("run", {}))
        if needs_visual_review else None
    )
    if is_grounded_generation(recorded_generation):
        require_grounding_pixel_validation(payload.get("run", {}))
    if is_joint_scene:
        identity_validation = visual_validation
        identity_pixels = None
    else:
        identity_validation = require_exact_source_pixel_validation(
            payload.get("run", {}),
            allow_legacy=True,
        )
        identity_pixels = int(identity_validation["opaque_pixels"])
    if recorded_generation.get("mode") == "identity_lock":
        prompt_record = (
            payload.get("run", {})
            .get("inputs", {})
            .get("prompt", {})
        )
        current_prompt = (
            (build_grounded_prompt_snapshot(manifest, scope_data)
             if is_grounded_generation(recorded_generation)
             else build_identity_lock_prompt(manifest, scope_data)) + "\n"
        ).encode("utf-8")
        current_prompt_hash = hashlib.sha256(current_prompt).hexdigest()
        if prompt_record.get("sha256") != current_prompt_hash:
            raise ValueError(
                "Generated identity-lock prompt drift between the current "
                f"manifest/code and {provenance_path}"
            )

    recorded_overlay_fingerprint = run_inputs.get("overlay_fingerprint")
    overlay_fingerprint_current: bool | None
    if recorded_overlay_fingerprint is None:
        overlay_fingerprint_current = None
    else:
        if not fingerprint_record_is_valid(recorded_overlay_fingerprint):
            raise ValueError(
                f"Malformed overlay fingerprint in {provenance_path}"
            )
        current_overlay_fingerprint = build_overlay_fingerprint(
            bundle,
            recorded=recorded_overlay_fingerprint,
        )
        overlay_fingerprint_current = (
            recorded_overlay_fingerprint.get("sha256")
            == current_overlay_fingerprint["sha256"]
        )

    layout = build_generation_output_layout(
        manifest.get("layout", {}).get("name", "standard_3x3"),
        recorded_generation,
    )
    output_dpi = recorded_generation.get("output_dpi")
    outputs = payload.get("outputs", {})
    promoted_file = artwork_config.get(
        "promoted_file",
        "poster-flux2-artwork.png",
    )
    promoted_artwork_path = bundle.asset_dir / str(promoted_file)
    artwork_path = _validate_record(
        outputs["artwork"],
        expected_path=promoted_artwork_path,
    )
    if needs_visual_review:
        promoted_pixel_hash = image_pixel_record(
            artwork_path,
        )["pixel_sha256"]
        output_pixel_hash = outputs["artwork"].get("pixel_sha256")
        if (
            output_pixel_hash != promoted_pixel_hash
            or visual_validation.get("reviewed_artwork_pixel_sha256")
            != promoted_pixel_hash
        ):
            raise ValueError(
                "Promoted artwork no longer matches its reviewed "
                "text-free pixels"
            )
    routed_artwork_path = bundle.asset_dir / bundle.artwork_file
    if artwork_path != routed_artwork_path:
        raise ValueError(
            f"{bundle.asset_key} routes PDF artwork to "
            f"{routed_artwork_path}, but promoted provenance validates "
            f"{artwork_path}"
        )
    asset_name = payload.get("asset_name")
    if not isinstance(asset_name, str) or not asset_name:
        raise ValueError(f"Invalid promoted asset name: {asset_name!r}")
    preview_path: Path | None = None
    card_paths: list[Path] = []
    if schema_version == 1:
        preview_path = _validate_record(outputs["preview"])
        configured_preview = artwork_config.get(
            "preview_file",
            f"poster-{asset_name}.png",
        )
        expected_preview_path = (bundle.asset_dir / configured_preview).resolve()
        if preview_path.resolve() != expected_preview_path:
            raise ValueError(
                f"Promoted preview routes to {preview_path}, expected "
                f"{expected_preview_path}"
            )
        card_records = outputs.get("cards", [])
        if len(card_records) != layout.rows * layout.columns:
            raise ValueError(
                f"Expected {layout.rows * layout.columns} card records, "
                f"got {len(card_records)}"
            )
        card_paths = [_validate_record(record) for record in card_records]

    for path in (artwork_path,) + ((preview_path,) if preview_path else ()):
        with Image.open(path) as image:
            if image.size != (layout.width_px, layout.height_px):
                raise ValueError(
                    f"Promoted poster has wrong print dimensions: {path} "
                    f"is {image.size}"
                )
        if isinstance(output_dpi, int):
            dpi_x, dpi_y = _image_dpi(path)
            if (
                abs(dpi_x - output_dpi) > 0.1
                or abs(dpi_y - output_dpi) > 0.1
            ):
                raise ValueError(
                    f"Wrong dpi metadata for {path}: {(dpi_x, dpi_y)}"
                )

    expected_card_sizes = [
        (
            layout.cell(row, column).width,
            layout.cell(row, column).height,
        )
        for row in range(1, layout.rows + 1)
        for column in range(1, layout.columns + 1)
    ]
    if card_paths:
        for path, expected_size in zip(
            card_paths,
            expected_card_sizes,
            strict=True,
        ):
            with Image.open(path) as image:
                if image.size != expected_size:
                    raise ValueError(
                        f"Promoted card has wrong dimensions: {path} is "
                        f"{image.size}, expected {expected_size}"
                    )
        if isinstance(output_dpi, int):
            dpi_x, dpi_y = _image_dpi(path)
            if (
                abs(dpi_x - output_dpi) > 0.1
                or abs(dpi_y - output_dpi) > 0.1
            ):
                raise ValueError(
                    f"Wrong dpi metadata for {path}: {(dpi_x, dpi_y)}"
                )

    dpi_x, dpi_y = effective_dpi(layout)
    distinct_card_sizes = tuple(dict.fromkeys(expected_card_sizes))
    return {
        "scope": scope,
        "artwork": artwork_path,
        "preview": preview_path,
        "cards": layout.rows * layout.columns,
        "dimensions": (layout.width_px, layout.height_px),
        "card_dimensions": (
            distinct_card_sizes[0]
            if len(distinct_card_sizes) == 1
            else None
        ),
        "card_dimensions_by_cell": tuple(expected_card_sizes),
        "effective_dpi": (dpi_x, dpi_y),
        "provenance": provenance_path,
        "identity_pixels": identity_pixels,
        "identity_validation_method": identity_validation["method"],
        "generation_fingerprint_current": generation_fingerprint_current,
        "generation_inputs_current": generation_fingerprint_current,
        "generation_pipeline_contract_version": (
            generation_pipeline_contract_version
        ),
        "generation_pipeline_contract_status": (
            generation_pipeline_contract_status
        ),
        "overlay_fingerprint_current": overlay_fingerprint_current,
    }


def _print_result(result: dict[str, Any]) -> None:
    print(
        f"{result['scope']}: {result['dimensions'][0]}x"
        f"{result['dimensions'][1]}, {result['cards']} cards at "
        f"{result['effective_dpi'][0]:.2f} dpi"
    )
    print(f"Provenance: {result['provenance']}")
    if result.get("generation_pipeline_contract_status") == "accepted_legacy":
        print(
            "Generation inputs match an accepted legacy pipeline contract; "
            "a reviewed rerender can upgrade the graph independently."
        )
    if result.get("overlay_fingerprint_current") is False:
        print(
            "Overlay inputs changed; the text-free artwork remains current "
            "and deterministic overlay derivatives can be refreshed."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--scope")
    target.add_argument(
        "--all-enabled",
        action="store_true",
        help="Validate every poster manifest with pdf.enabled set to true",
    )
    args = parser.parse_args()

    targets: list[str | PosterBundle] = (
        enabled_poster_bundles()
        if args.all_enabled
        else [args.scope]
    )
    for target_value in targets:
        _print_result(validate(target_value))
    if args.all_enabled:
        print(f"Validated {len(targets)} enabled poster bundle(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
