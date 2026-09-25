#!/usr/bin/env python3
"""Promote one reviewed text-free ComfyUI artwork into stable poster assets."""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import tempfile
from pathlib import Path

from PIL import Image

try:
    from .generation_contract import is_grounded_generation, requires_visual_review
    from .provenance import require_grounding_pixel_validation
    from .finalize_comfyui_poster import finalize
    from .generation_contract import (
        requires_generation_fingerprint,
        validate_promotable_generation_contract,
    )
    from .layout import build_generation_output_layout
    from .poster_io import POSTER_ASSETS, poster_bundle
    from .provenance import (
        approve_joint_scene_visual_review,
        build_generation_fingerprint,
        build_overlay_fingerprint,
        fingerprint_record_is_valid,
        generation_fingerprint_pipeline_contract_version,
        image_pixel_record,
        load_run_metadata,
        promoted_provenance,
        recorded_repository_path,
        require_exact_source_pixel_validation,
        require_joint_scene_visual_review,
        sha256_file,
    )
    from .slice_poster import slice_poster
except ImportError:
    from generation_contract import is_grounded_generation, requires_visual_review
    from provenance import require_grounding_pixel_validation
    from finalize_comfyui_poster import finalize
    from generation_contract import (
        requires_generation_fingerprint,
        validate_promotable_generation_contract,
    )
    from layout import build_generation_output_layout
    from poster_io import POSTER_ASSETS, poster_bundle
    from provenance import (
        approve_joint_scene_visual_review,
        build_generation_fingerprint,
        build_overlay_fingerprint,
        fingerprint_record_is_valid,
        generation_fingerprint_pipeline_contract_version,
        image_pixel_record,
        load_run_metadata,
        promoted_provenance,
        recorded_repository_path,
        require_exact_source_pixel_validation,
        require_joint_scene_visual_review,
        sha256_file,
    )
    from slice_poster import slice_poster


ROOT = Path(__file__).resolve().parents[2]


def _configured_refresh_paths(
    scope_dir: Path,
    manifest: dict,
) -> tuple[Path, Path]:
    artwork = manifest.get("artwork", {})
    provenance_path = (
        scope_dir
        / str(
            artwork.get(
                "provenance_file",
                "poster-flux2-provenance.json",
            )
        )
    ).resolve()
    artwork_path = (
        scope_dir
        / str(
            artwork.get(
                "promoted_file",
                "poster-flux2-artwork.png",
            )
        )
    ).resolve()
    scope_root = scope_dir.resolve()
    if (
        not provenance_path.is_relative_to(scope_root)
        or not artwork_path.is_relative_to(scope_root)
    ):
        raise ValueError("Configured promoted poster paths leave the scope")
    return provenance_path, artwork_path


def _is_existing_promotion_refresh(
    *,
    scope: str,
    scope_dir: Path,
    manifest: dict,
    metadata_path: Path,
    metadata_container: dict,
    artwork_path: Path,
) -> bool:
    """Bind legacy allowances to the configured stable promotion bundle."""
    if metadata_container.get("kind") != "promoted_poster":
        return False
    expected_metadata, expected_artwork = _configured_refresh_paths(
        scope_dir,
        manifest,
    )
    output_artwork = metadata_container.get("outputs", {}).get("artwork")
    return (
        metadata_container.get("scope") == scope
        and metadata_path.resolve() == expected_metadata
        and expected_metadata.is_file()
        and artwork_path.resolve() == expected_artwork
        and expected_artwork.is_file()
        and isinstance(output_artwork, dict)
        and output_artwork.get("sha256") == sha256_file(expected_artwork)
    )


def _replace_bundle(
    replacements: list[tuple[Path, Path]],
    *,
    force: bool,
    backup_dir: Path,
) -> None:
    """Install staged files/directories and roll back a partial replacement."""
    existing = [destination for _source, destination in replacements if destination.exists()]
    if existing and not force:
        raise FileExistsError(
            f"Promoted asset already exists: {existing[0]} (use --force to replace)"
        )

    backups: list[tuple[Path, Path]] = []
    installed: list[Path] = []
    backup_dir.mkdir(parents=True, exist_ok=True)
    try:
        for _source, destination in replacements:
            if destination.exists():
                backup = backup_dir / destination.name
                os.replace(destination, backup)
                backups.append((backup, destination))
        for source, destination in replacements:
            os.replace(source, destination)
            installed.append(destination)
    except Exception:
        for destination in reversed(installed):
            if destination.is_dir():
                shutil.rmtree(destination)
            else:
                destination.unlink(missing_ok=True)
        for backup, destination in reversed(backups):
            os.replace(backup, destination)
        raise


def promote(
    scope: str,
    artwork: Path,
    *,
    language: str = "en",
    name: str = "flux2",
    force: bool = False,
    approve_joint_scene: bool = False,
    reviewer_kind: str | None = None,
    run_metadata_path: Path,
) -> tuple[Path, Path, list[Path], Path]:
    """Persist a reviewed master; keep reproducible QA derivatives ignored."""
    if not artwork.is_file():
        raise FileNotFoundError(artwork)

    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    scope_dir = bundle.asset_dir
    manifest_path = bundle.manifest_path
    manifest = bundle.manifest

    run_metadata = copy.deepcopy(
        load_run_metadata(run_metadata_path, artwork)
    )
    metadata_container = json.loads(
        run_metadata_path.read_text(encoding="utf-8")
    )
    refreshing_existing_promotion = _is_existing_promotion_refresh(
        scope=scope,
        scope_dir=scope_dir,
        manifest=manifest,
        metadata_path=run_metadata_path,
        metadata_container=metadata_container,
        artwork_path=artwork,
    )
    if (
        metadata_container.get("kind") == "promoted_poster"
        and not refreshing_existing_promotion
    ):
        raise ValueError(
            "Promoted provenance refresh must use the configured existing "
            "provenance and text-free artwork paths"
        )
    if run_metadata.get("scope") != scope:
        raise ValueError(
            f"Run metadata is for scope {run_metadata.get('scope')!r}, not {scope!r}"
        )
    if bundle.section_id is not None and (
        run_metadata.get("source_scope") != bundle.scope
        or run_metadata.get("poster_id") != bundle.poster_id
        or run_metadata.get("section_id") != bundle.section_id
    ):
        raise ValueError(
            "Run metadata does not match the aggregate poster target "
            f"{bundle.scope}/{bundle.section_id}"
        )
    configured_generation = manifest.get("artwork", {}).get("generation")
    recorded_generation = run_metadata.get("generation")
    if not isinstance(configured_generation, dict) or not isinstance(
        recorded_generation, dict
    ):
        raise ValueError("Poster generation metadata must be a mapping")
    validate_promotable_generation_contract(configured_generation)
    validate_promotable_generation_contract(recorded_generation)
    if configured_generation != recorded_generation:
        raise ValueError(
            "Candidate generation metadata does not match "
            f"{manifest_path}. Review and update artwork.generation before "
            "promoting this candidate."
        )
    needs_visual_review = requires_visual_review(recorded_generation)
    if approve_joint_scene and not needs_visual_review:
        raise ValueError(
            "--approve-joint-scene applies only to joint-scene or grounded candidates"
        )
    run_inputs = run_metadata.get("inputs")
    if not isinstance(run_inputs, dict):
        if (
            requires_generation_fingerprint(recorded_generation)
            or not refreshing_existing_promotion
        ):
            raise ValueError(
                "New poster candidate lacks generation input provenance"
            )
    else:
        recorded_fingerprint = run_inputs.get("generation_fingerprint")
        if recorded_fingerprint is None and (
            requires_generation_fingerprint(recorded_generation)
            or not refreshing_existing_promotion
        ):
            raise ValueError(
                "New poster candidate lacks its generation fingerprint"
            )
        if recorded_fingerprint is not None:
            if not fingerprint_record_is_valid(recorded_fingerprint):
                raise ValueError(
                    "Candidate generation fingerprint is malformed"
                )
            recorded_contract_version = None
            if refreshing_existing_promotion:
                recorded_contract_version = (
                    generation_fingerprint_pipeline_contract_version(
                        recorded_fingerprint,
                        recorded_generation,
                    )
                )
            current_fingerprint = build_generation_fingerprint(
                bundle,
                pipeline_contract_version=recorded_contract_version,
            )
            if (
                recorded_fingerprint.get("sha256")
                != current_fingerprint["sha256"]
            ):
                raise ValueError(
                    "Candidate generation inputs have drifted since the "
                    "reviewed artwork was created"
                )
            run_inputs["generation_fingerprint"] = current_fingerprint
        # Overlay inputs are cheap and intentionally may change after the
        # expensive generation. Bind the promotion preview to their current
        # state instead of rejecting the reviewed text-free artwork.
        run_inputs["overlay_fingerprint"] = build_overlay_fingerprint(bundle)
    if is_grounded_generation(recorded_generation):
        require_grounding_pixel_validation(
            run_metadata, verify_files=not refreshing_existing_promotion,
        )
    if needs_visual_review:
        if refreshing_existing_promotion:
            if approve_joint_scene:
                raise ValueError(
                    "An existing promoted joint scene is already bound to its "
                    "visual review"
                )
            require_joint_scene_visual_review(run_metadata)
        else:
            raw_record = run_metadata.get("raw_artwork")
            if not isinstance(raw_record, dict):
                raise ValueError(
                    "Joint-scene candidate lacks its raw artwork record"
                )
            raw_artwork_path = recorded_repository_path(raw_record)
            if approve_joint_scene:
                approve_joint_scene_visual_review(
                    run_metadata,
                    artwork_path=artwork,
                    raw_artwork_path=raw_artwork_path,
                    reviewer_kind=reviewer_kind,
                )
            require_joint_scene_visual_review(
                run_metadata,
                artwork_path=artwork,
                raw_artwork_path=raw_artwork_path,
            )
    else:
        require_exact_source_pixel_validation(
            run_metadata,
            allow_legacy=refreshing_existing_promotion,
        )

    with Image.open(artwork) as loaded_source:
        source = loaded_source.convert("RGB")
    layout = build_generation_output_layout(
        manifest.get("layout", {}).get("name", "standard_3x3"),
        recorded_generation,
    )
    if source.size != (layout.width_px, layout.height_px):
        raise ValueError(
            "Candidate output dimensions do not match generation contract: "
            f"{source.size} vs {(layout.width_px, layout.height_px)}"
        )

    artwork_path = scope_dir / f"poster-{name}-artwork.png"
    qa_dir = bundle.work_dir / "promotion"
    final_path = qa_dir / f"poster-{name}.png"
    cards_dir = qa_dir / f"poster-{name}-cards"
    provenance_path = scope_dir / f"poster-{name}-provenance.json"

    with tempfile.TemporaryDirectory(
        prefix=".poster-promotion-",
        dir=scope_dir,
    ) as temporary:
        stage = Path(temporary)
        staged_artwork = stage / artwork_path.name
        staged_final = stage / final_path.name
        staged_cards = stage / cards_dir.name
        staged_provenance = stage / provenance_path.name

        output_dpi = run_metadata.get("generation", {}).get("output_dpi")
        save_options = {"format": "PNG", "optimize": True}
        if output_dpi:
            save_options["dpi"] = (float(output_dpi), float(output_dpi))
        source.save(staged_artwork, **save_options)
        if needs_visual_review:
            reviewed = require_joint_scene_visual_review(run_metadata)
            stable_pixels = image_pixel_record(
                staged_artwork,
            )["pixel_sha256"]
            if (
                reviewed.get("reviewed_artwork_pixel_sha256")
                != stable_pixels
            ):
                raise ValueError(
                    "Promoted joint-scene artwork is not pixel-identical to "
                    "the reviewed text-free candidate"
                )
        finalize(scope, staged_artwork, staged_final, language)
        staged_card_paths = slice_poster(
            scope,
            staged_final,
            staged_cards,
        )
        expected_cards = layout.rows * layout.columns
        if len(staged_card_paths) != expected_cards:
            raise ValueError(
                f"Promotion produced {len(staged_card_paths)} card crops, "
                f"expected {expected_cards}"
            )
        provenance = promoted_provenance(
            scope=scope,
            name=name,
            language=language,
            run_metadata=run_metadata,
            artwork_path=staged_artwork,
            stable_artwork_path=artwork_path,
        )
        staged_provenance.write_text(
            json.dumps(
                provenance,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        qa_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged_final, final_path)
        if cards_dir.exists():
            shutil.rmtree(cards_dir)
        shutil.copytree(staged_cards, cards_dir)
        _replace_bundle(
            [
                (staged_artwork, artwork_path),
                (staged_provenance, provenance_path),
            ],
            force=force,
            backup_dir=stage / "backups",
        )

    card_paths = [
        cards_dir / f"card_r{row}_c{column}.png"
        for row in range(1, layout.rows + 1)
        for column in range(1, layout.columns + 1)
    ]
    return artwork_path, final_path, card_paths, provenance_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--artwork", required=True, type=Path)
    parser.add_argument("--language", default="en")
    parser.add_argument("--name", default="flux2")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--approve-joint-scene",
        action="store_true",
        help=(
            "Confirm that every subject crop and the integrated scene were "
            "visually reviewed against the source identities"
        ),
    )
    parser.add_argument("--run-metadata", required=True, type=Path)
    parser.add_argument(
        "--reviewer-kind",
        choices=("human", "agent"),
        help="Required with --approve-joint-scene; records who inspected the artwork",
    )
    args = parser.parse_args()

    artwork_path, final_path, cards, provenance_path = promote(
        args.scope,
        args.artwork,
        language=args.language,
        name=args.name,
        force=args.force,
        approve_joint_scene=args.approve_joint_scene,
        reviewer_kind=args.reviewer_kind,
        run_metadata_path=args.run_metadata,
    )
    print(f"Artwork: {artwork_path}")
    print(f"QA preview (ignored): {final_path}")
    print(f"QA card slices (ignored): {cards[0].parent} ({len(cards)})")
    print(f"Provenance: {provenance_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
