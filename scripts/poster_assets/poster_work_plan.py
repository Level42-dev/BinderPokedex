#!/usr/bin/env python3
"""Report the next safe, read-only work step for configured poster targets.

The planner deliberately does not initialize scopes, download assets, start
ComfyUI, generate candidates, promote artwork, or change PDF routing.  It
compares the current source/configuration/assets with promoted provenance and
returns stable machine-readable states and reason/action codes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from PIL import Image

try:
    from .fetch_cutouts import (
        cutout_filename,
        resolve_requested_count,
        select_pokemon,
        validate_png,
    )
    from .fetch_title_logos import resolve_logo_downloads
    from .generation_contract import (
        requires_generation_fingerprint,
        validate_promotable_generation_contract,
    )
    from .layout import build_page_layout
    from .poster_config import build_identity_lock_prompt, identity_lock_config
    from .poster_io import (
        POSTER_ASSETS,
        POSTER_CONFIGS,
        POSTER_INDEX_NAME,
        POSTER_MANIFEST_NAME,
        SCOPE_DATA,
        PosterBundle,
        load_json,
        load_poster_scope_data,
        poster_bundles_for_scope,
    )
    from .poster_subject import resolve_poster_subject
    from .provenance import (
        MODEL_DIRECTORIES,
        build_generation_fingerprint,
        build_overlay_fingerprint,
        current_generation_pipeline_contract_version,
        fingerprint_record_is_valid,
        generation_fingerprint_pipeline_contract_version,
        prompt_path_for_generation,
        rebuild_generation_fingerprint_from_recorded_sources,
        required_model_artifact_hashes,
        sha256_file,
    )
    from .scene_catalog import (
        SCENE_CATALOG,
        scene_for_scope,
        section_scenes_for_scope,
    )
    from .validate_promoted_poster import (
        POSTER_LANGUAGES,
        validate,
    )
except ImportError:  # Direct script execution
    from fetch_cutouts import (
        cutout_filename,
        resolve_requested_count,
        select_pokemon,
        validate_png,
    )
    from fetch_title_logos import resolve_logo_downloads
    from generation_contract import (
        requires_generation_fingerprint,
        validate_promotable_generation_contract,
    )
    from layout import build_page_layout
    from poster_config import build_identity_lock_prompt, identity_lock_config
    from poster_io import (
        POSTER_ASSETS,
        POSTER_CONFIGS,
        POSTER_INDEX_NAME,
        POSTER_MANIFEST_NAME,
        SCOPE_DATA,
        PosterBundle,
        load_json,
        load_poster_scope_data,
        poster_bundles_for_scope,
    )
    from poster_subject import resolve_poster_subject
    from provenance import (
        MODEL_DIRECTORIES,
        build_generation_fingerprint,
        build_overlay_fingerprint,
        current_generation_pipeline_contract_version,
        fingerprint_record_is_valid,
        generation_fingerprint_pipeline_contract_version,
        prompt_path_for_generation,
        rebuild_generation_fingerprint_from_recorded_sources,
        required_model_artifact_hashes,
        sha256_file,
    )
    from scene_catalog import (
        SCENE_CATALOG,
        scene_for_scope,
        section_scenes_for_scope,
    )
    from validate_promoted_poster import (
        POSTER_LANGUAGES,
        validate,
    )


SCHEMA_VERSION = 1
STATES = (
    "unconfigured",
    "needs_assets",
    "ready_to_generate",
    "promotion_stale",
    "invalid",
    "promoted_disabled",
    "current",
    "blocked",
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SAFE_ASSET_PART = re.compile(r"[A-Za-z0-9._-]+")

PromotionValidator = Callable[[PosterBundle], dict[str, Any]]
ENGINE_REQUIRED_ARTIFACTS = {
    "flux": ("model", "encoder", "vae"),
}


@dataclass(frozen=True)
class WorkItem:
    """One poster target's current state and deterministic next action."""

    asset_key: str
    source_scope: str | None
    poster_id: str | None
    section_id: str | None
    pdf_enabled: bool | None
    state: str
    reason_codes: tuple[str, ...]
    next_actions: tuple[str, ...]
    commands: tuple[str, ...] = ()
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "asset_key": self.asset_key,
            "source_scope": self.source_scope,
            "poster_id": self.poster_id,
            "section_id": self.section_id,
            "pdf_enabled": self.pdf_enabled,
            "state": self.state,
            "reason_codes": list(self.reason_codes),
            "next_actions": list(self.next_actions),
            "commands": list(self.commands),
        }
        if self.detail:
            result["detail"] = self.detail
        return result


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _detail(error: BaseException) -> str:
    text = " ".join(str(error).split())
    return f"{type(error).__name__}: {text}" if text else type(error).__name__


def _safe_local_asset(scope_dir: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty relative path")
    relative = Path(value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not relative.parts
        or any(not _SAFE_ASSET_PART.fullmatch(part) for part in relative.parts)
    ):
        raise ValueError(f"Unsafe {label}: {value!r}")
    result = (scope_dir / relative).resolve()
    if not result.is_relative_to(scope_dir.resolve()):
        raise ValueError(f"{label} escapes the poster scope: {value!r}")
    return result


def _configured_roots(poster_configs: Path) -> list[str]:
    if not poster_configs.is_dir():
        return []
    return [
        path.name
        for path in sorted(poster_configs.iterdir(), key=lambda item: item.name)
        if path.is_dir()
        and (
            (path / POSTER_MANIFEST_NAME).is_file()
            or (path / POSTER_INDEX_NAME).is_file()
        )
    ]


def _unconfigured_item(
    scope: str,
    *,
    scope_data_dir: Path,
) -> WorkItem:
    root_scope = scope.split("/", 1)[0]
    source_path = scope_data_dir / f"{root_scope}.json"
    source_error: BaseException | None = None
    try:
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        source = load_json(source_path)
    except (OSError, ValueError, TypeError) as error:
        source = {}
        source_error = error
    aggregate = "/" in scope or bool(
        source.get("type") != "tcg_set" and source.get("sections")
    )
    initialize_command = (
        (
            "python scripts/poster_assets/init_poster_scope.py "
            f"--scope {root_scope} --all-sections --fetch"
        )
        if aggregate
        else (
            "python scripts/poster_assets/init_poster_scope.py "
            f"--scope {root_scope} --fetch"
        )
    )
    reasons = ["poster_not_configured"]
    actions = [
        (
            "initialize_aggregate_posters"
            if aggregate
            else "initialize_poster"
        )
    ]
    commands = [initialize_command]
    if source_error is not None:
        reasons.append("scope_data_missing_or_invalid")
        actions.insert(0, "fetch_scope_data")
        commands.insert(
            0,
            "python scripts/fetcher/fetch.py "
            f"--scope {root_scope}",
        )
    return WorkItem(
        asset_key=scope,
        source_scope=root_scope,
        poster_id=None,
        section_id=None,
        pdf_enabled=None,
        state="unconfigured",
        reason_codes=tuple(reasons),
        next_actions=tuple(actions),
        commands=tuple(commands),
        detail=_detail(source_error) if source_error else None,
    )


def _blocked_item(
    asset_key: str,
    *,
    reason_code: str,
    error: BaseException,
    bundle: PosterBundle | None = None,
) -> WorkItem:
    return WorkItem(
        asset_key=asset_key,
        source_scope=bundle.scope if bundle else asset_key.split("/", 1)[0],
        poster_id=bundle.poster_id if bundle else None,
        section_id=bundle.section_id if bundle else None,
        pdf_enabled=bundle.pdf_enabled if bundle else None,
        state="blocked",
        reason_codes=(reason_code,),
        next_actions=("repair_configuration",),
        detail=_detail(error),
    )


def _resolve_targets(
    requested_scope: str,
    *,
    poster_assets: Path,
    poster_configs: Path,
    scope_data_dir: Path,
) -> list[PosterBundle] | WorkItem:
    scope_parts = requested_scope.split("/")
    if (
        not scope_parts
        or any(
            part in {"", ".", ".."}
            or not _SAFE_ASSET_PART.fullmatch(part)
            for part in scope_parts
        )
    ):
        return _blocked_item(
            requested_scope,
            reason_code="scope_invalid",
            error=ValueError(f"Unsafe poster scope: {requested_scope!r}"),
        )
    root_scope = requested_scope.split("/", 1)[0]
    root_dir = poster_configs / root_scope
    if not (
        (root_dir / POSTER_MANIFEST_NAME).is_file()
        or (root_dir / POSTER_INDEX_NAME).is_file()
    ):
        return _unconfigured_item(
            requested_scope,
            scope_data_dir=scope_data_dir,
        )
    try:
        bundles = poster_bundles_for_scope(
            root_scope,
            poster_assets=poster_assets,
            poster_configs=poster_configs,
        )
    except Exception as error:
        return _blocked_item(
            requested_scope,
            reason_code="routing_invalid",
            error=error,
        )
    if requested_scope == root_scope:
        return bundles
    matching = [
        bundle for bundle in bundles if bundle.asset_key == requested_scope
    ]
    if not matching:
        return _blocked_item(
            requested_scope,
            reason_code="routing_target_not_indexed",
            error=ValueError(
                f"{requested_scope!r} is not routed by "
                f"{root_dir / POSTER_INDEX_NAME}"
            ),
        )
    return matching


def _expected_scene(
    bundle: PosterBundle,
    *,
    scene_catalog_path: Path,
) -> dict[str, Any]:
    if bundle.section_id is None:
        return scene_for_scope(
            bundle.scope,
            catalog_path=scene_catalog_path,
        )
    sections = section_scenes_for_scope(
        bundle.scope,
        catalog_path=scene_catalog_path,
    )
    try:
        return sections[bundle.section_id]
    except KeyError as error:
        raise KeyError(
            f"No scene brief for {bundle.asset_key}"
        ) from error


def _contains_catalog_contract(
    configured: object,
    expected: object,
) -> bool:
    """Allow reviewed manifest overrides while requiring every catalog field."""
    if isinstance(expected, dict):
        return isinstance(configured, dict) and all(
            key in configured
            and _contains_catalog_contract(configured[key], value)
            for key, value in expected.items()
        )
    return configured == expected


def _validate_source_contract(
    bundle: PosterBundle,
    scope_data: dict[str, Any],
) -> None:
    if not isinstance(scope_data, dict) or not scope_data:
        raise ValueError(f"{bundle.asset_key} source data must be a mapping")
    sections = scope_data.get("sections")
    if not isinstance(sections, dict) or not sections:
        raise ValueError(f"{bundle.asset_key} source data has no sections")
    content_mode = bundle.manifest.get("text_content", {}).get(
        "mode",
        "set_summary",
    )
    if content_mode == "set_summary":
        if not scope_data.get("release_date"):
            raise ValueError(
                f"{bundle.asset_key} source data has no release_date"
            )
    elif content_mode == "section_summary":
        if len(sections) != 1:
            raise ValueError(
                f"{bundle.asset_key} must resolve exactly one source section"
            )
        section = next(iter(sections.values()))
        if not isinstance(section, dict):
            raise ValueError(
                f"{bundle.asset_key} selected section must be a mapping"
            )
        if bundle.scope == "Pokedex":
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
    else:
        raise ValueError(
            f"Unsupported text_content.mode: {content_mode!r}"
        )


def _validate_generation_contract(manifest: dict[str, Any]) -> None:
    layout_name = manifest.get("layout", {}).get(
        "name",
        "standard_3x3",
    )
    build_page_layout(str(layout_name))
    artwork = manifest.get("artwork")
    if not isinstance(artwork, dict):
        raise ValueError("artwork must be a mapping")
    generation = artwork.get("generation")
    if not isinstance(generation, dict) or not generation:
        raise ValueError("artwork.generation must be a non-empty mapping")
    validate_promotable_generation_contract(generation)
    if (
        generation.get("engine") == "flux"
        and generation.get("mode") == "identity_lock"
    ):
        identity_lock_config(manifest)
    for field in ("engine", "mode", "output_method"):
        if not isinstance(generation.get(field), str) or not generation[field]:
            raise ValueError(
                f"artwork.generation.{field} must be non-empty text"
            )
    engine = generation["engine"]
    if engine not in ENGINE_REQUIRED_ARTIFACTS:
        raise ValueError(f"Unsupported artwork.generation.engine: {engine!r}")
    for field in ("steps",):
        if not isinstance(generation.get(field), int) or generation[field] <= 0:
            raise ValueError(
                f"artwork.generation.{field} must be a positive integer"
            )
    megapixels = generation.get("generation_megapixels")
    if not isinstance(megapixels, (int, float)) or megapixels <= 0:
        raise ValueError(
            "artwork.generation.generation_megapixels must be positive"
        )
    artifact_fields = list(ENGINE_REQUIRED_ARTIFACTS[engine])
    output_method = generation["output_method"]
    if output_method == "model_upscale":
        if (
            not isinstance(generation.get("output_dpi"), int)
            or generation["output_dpi"] <= 0
        ):
            raise ValueError(
                "artwork.generation.output_dpi must be a positive integer"
            )
        artifact_fields.append("upscale_model")
    elif output_method == "lanczos":
        output_dpi = generation.get("output_dpi")
        output_megapixels = generation.get("output_megapixels")
        has_dpi = output_dpi is not None
        has_megapixels = output_megapixels is not None
        if has_dpi == has_megapixels:
            raise ValueError(
                "artwork.generation with Lanczos output must define exactly "
                "one of output_dpi or output_megapixels"
            )
        if has_dpi and (
            not isinstance(output_dpi, int)
            or isinstance(output_dpi, bool)
            or output_dpi <= 0
        ):
            raise ValueError(
                "artwork.generation.output_dpi must be a positive integer"
            )
        if has_megapixels and (
            not isinstance(output_megapixels, (int, float))
            or isinstance(output_megapixels, bool)
            or output_megapixels <= 0
        ):
            raise ValueError(
                "artwork.generation.output_megapixels must be positive"
            )
    else:
        raise ValueError(
            f"Unsupported artwork.generation.output_method: {output_method!r}"
        )
    for artifact in artifact_fields:
        if artifact not in MODEL_DIRECTORIES:
            raise ValueError(f"Unsupported model artifact: {artifact!r}")
        filename = generation.get(artifact)
        if not isinstance(filename, str) or not filename:
            raise ValueError(
                f"artwork.generation.{artifact} must be non-empty text"
            )
    for hash_field in required_model_artifact_hashes(generation):
        value = generation.get(hash_field)
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise ValueError(
                f"artwork.generation.{hash_field} must be a SHA-256 digest"
            )


def _validate_prompt_prerequisites(bundle: PosterBundle) -> None:
    generation = bundle.manifest.get("artwork", {}).get("generation", {})
    if (
        generation.get("engine") == "flux"
        and generation.get("mode") in {"identity_lock", "joint_scene"}
    ):
        return
    raise ValueError(
        "Only flux/joint_scene and flux/identity_lock are supported"
    )


def _expected_subject_identities(
    manifest: dict[str, Any],
    scope_data: dict[str, Any],
) -> tuple[list[tuple[str, int, int]], Any]:
    layout = build_page_layout(
        str(manifest.get("layout", {}).get("name", "standard_3x3"))
    )
    count = resolve_requested_count(manifest, layout)
    selected = select_pokemon(manifest, scope_data, count, {})
    return [
        resolve_poster_subject(item).selection_key()
        for item in selected
    ], layout


def _cutout_asset_issues(
    bundle: PosterBundle,
    scope_data: dict[str, Any],
) -> tuple[list[str], list[tuple[Path, dict[str, Any]]], str | None]:
    expected_subjects, layout = _expected_subject_identities(
        bundle.manifest,
        scope_data,
    )
    path = bundle.source_dir / "cutouts" / "manifest.json"
    if not path.is_file():
        return ["cutout_manifest_missing"], [], None
    try:
        payload = load_json(path)
    except (OSError, ValueError, TypeError) as error:
        return ["cutout_manifest_invalid"], [], _detail(error)
    issues: list[str] = []
    expected_routing = {
        "scope": bundle.asset_key,
        "source_scope": bundle.scope,
        "poster_id": bundle.poster_id,
        "section_id": bundle.section_id,
    }
    legacy_defaults = {
        "source_scope": bundle.scope,
        "poster_id": bundle.poster_id,
        "section_id": None,
    }
    if any(
        payload.get(key, legacy_defaults.get(key)) != value
        for key, value in expected_routing.items()
    ):
        issues.append("cutout_routing_stale")
    source = bundle.manifest.get("pokemon", {}).get(
        "cutout_source",
        "pokeapi_official_artwork",
    )
    if payload.get("source") != source:
        issues.append("cutout_source_stale")
    recorded_layout = payload.get("layout")
    expected_layout = {
        "name": layout.name,
        "columns": layout.columns,
        "rows": layout.rows,
    }
    if not isinstance(recorded_layout, dict) or any(
        recorded_layout.get(key) != value
        for key, value in expected_layout.items()
    ):
        issues.append("cutout_layout_stale")
    items = payload.get("items")
    if not isinstance(items, list):
        return _unique((*issues, "cutout_manifest_invalid")), [], None
    actual_subjects: list[tuple[str, int, int] | None] = []
    seen_subjects: set[tuple[str, int, int]] = set()
    artwork_species: dict[tuple[str, int], int] = {}
    seen_files: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            actual_subjects.append(None)
            continue
        try:
            subject = resolve_poster_subject(item)
        except (TypeError, ValueError):
            actual_subjects.append(None)
            issues.append("cutout_manifest_invalid")
            continue
        identity = subject.selection_key()
        actual_subjects.append(identity)
        if identity in seen_subjects:
            issues.append("cutout_manifest_invalid")
        seen_subjects.add(identity)
        previous_species = artwork_species.get(subject.artwork_key())
        if (
            previous_species is not None
            and previous_species != subject.species_id
        ):
            issues.append("cutout_manifest_invalid")
        artwork_species[subject.artwork_key()] = subject.species_id
        if item.get("url") != subject.image_url:
            issues.append("cutout_manifest_invalid")
        filename = item.get("file")
        if isinstance(filename, str):
            if filename in seen_files:
                issues.append("cutout_manifest_invalid")
            seen_files.add(filename)
        if subject.is_special_form:
            expected_filename = cutout_filename(
                subject.species_id,
                str(item.get("name_en") or f"pokemon-{subject.species_id}"),
                subject.official_artwork_id,
            )
            if filename != expected_filename:
                issues.append("cutout_manifest_invalid")
    if actual_subjects != expected_subjects:
        issues.append("cutout_selection_stale")

    checked: list[tuple[Path, dict[str, Any]]] = []
    for item in items:
        if not isinstance(item, dict):
            issues.append("cutout_manifest_invalid")
            continue
        try:
            file_path = _safe_local_asset(
                bundle.source_dir / "cutouts",
                item.get("file"),
                "cutout file",
            )
        except ValueError:
            issues.append("cutout_manifest_invalid")
            continue
        if not file_path.is_file():
            issues.append("cutout_file_missing")
            continue
        try:
            actual = validate_png(file_path)
        except (OSError, ValueError, TypeError) as error:
            issues.append("cutout_file_invalid")
            return list(_unique(issues)), checked, _detail(error)
        if not actual.get("validated_alpha"):
            issues.append("cutout_file_invalid")
        if item.get("validated_alpha") is not True or item.get("errors") not in (
            [],
            None,
        ):
            issues.append("cutout_manifest_invalid")
        for field in (
            "mode",
            "width",
            "height",
            "alpha_min",
            "alpha_max",
            "transparent_pixels",
            "opaque_pixels",
        ):
            if item.get(field) != actual.get(field):
                issues.append("cutout_manifest_invalid")
                break
        checked.append((file_path, item))
    return list(_unique(issues)), checked, None


def _logo_asset_issues(
    bundle: PosterBundle,
    scope_data: dict[str, Any],
) -> tuple[list[str], str | None]:
    if not bundle.manifest.get("title_logo"):
        return [], None
    try:
        downloads = resolve_logo_downloads(bundle.manifest, scope_data)
    except Exception as error:
        raise ValueError(
            f"Cannot resolve required title logos: {error}"
        ) from error
    issues: list[str] = []
    for _language, relative_file, _url in downloads:
        try:
            path = _safe_local_asset(
                bundle.source_dir,
                relative_file,
                "title-logo file",
            )
        except ValueError as error:
            raise ValueError(str(error)) from error
        if not path.is_file():
            issues.append("title_logo_missing")
            continue
        try:
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                if (
                    image.format != "PNG"
                    or image.width < 32
                    or image.height < 16
                ):
                    issues.append("title_logo_invalid")
        except (OSError, ValueError, TypeError) as error:
            issues.append("title_logo_invalid")
            return list(_unique(issues)), _detail(error)
    return list(_unique(issues)), None


def _promotion_paths(bundle: PosterBundle) -> tuple[Path, Path]:
    artwork = bundle.manifest.get("artwork", {})
    if not isinstance(artwork, dict):
        raise ValueError("artwork must be a mapping")
    provenance = _safe_local_asset(
        bundle.asset_dir,
        artwork.get("provenance_file", "poster-flux2-provenance.json"),
        "provenance file",
    )
    promoted = _safe_local_asset(
        bundle.asset_dir,
        artwork.get("promoted_file", "poster-flux2-artwork.png"),
        "promoted artwork file",
    )
    return provenance, promoted


def _promotion_drift_codes(
    bundle: PosterBundle,
    scope_data: dict[str, Any],
    provenance: dict[str, Any],
    cutouts: list[tuple[Path, dict[str, Any]]],
    *,
    scope_data_dir: Path,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Return generation drift, invalidity, overlay drift, and graph notes."""
    drift: list[str] = []
    invalid: list[str] = []
    overlay_drift: list[str] = []
    pipeline_notes: list[str] = []
    if (
        provenance.get("schema_version") not in {1, 2}
        or provenance.get("kind") != "promoted_poster"
        or provenance.get("scope") != bundle.asset_key
    ):
        invalid.append("provenance_identity_invalid")
        return drift, invalid, overlay_drift, pipeline_notes
    if bundle.section_id is not None and (
        provenance.get("source_scope") != bundle.scope
        or provenance.get("poster_id") != bundle.poster_id
        or provenance.get("section_id") != bundle.section_id
    ):
        invalid.append("provenance_routing_invalid")

    run = provenance.get("run")
    if not isinstance(run, dict):
        invalid.append("provenance_run_missing")
        return drift, invalid, overlay_drift, pipeline_notes
    recorded_generation = run.get("generation")
    configured_generation = bundle.manifest.get("artwork", {}).get(
        "generation"
    )
    if not isinstance(recorded_generation, dict) or not isinstance(
        configured_generation, dict
    ):
        invalid.append("generation_contract_invalid")
        return drift, invalid, overlay_drift, pipeline_notes
    validate_promotable_generation_contract(recorded_generation)
    validate_promotable_generation_contract(configured_generation)
    if recorded_generation != configured_generation:
        drift.append("generation_contract_drift")
    inputs = run.get("inputs")
    if not isinstance(inputs, dict):
        invalid.append("provenance_inputs_missing")
        return drift, invalid, overlay_drift, pipeline_notes
    manifest_record = inputs.get("scope_manifest")
    prompt_record = inputs.get("prompt")
    cutout_records = inputs.get("cutouts")
    stored_generation_fingerprint = inputs.get("generation_fingerprint")
    stored_overlay_fingerprint = inputs.get("overlay_fingerprint")
    if (
        stored_generation_fingerprint is None
        and requires_generation_fingerprint(recorded_generation)
    ):
        invalid.append("generation_fingerprint_required")
    manifest_matches = False
    if not isinstance(manifest_record, dict):
        invalid.append("provenance_manifest_record_missing")
    else:
        manifest_matches = (
            manifest_record.get("sha256")
            == sha256_file(bundle.manifest_path)
        )
    if not isinstance(prompt_record, dict):
        invalid.append("provenance_prompt_record_missing")
    elif stored_generation_fingerprint is None:
        generation = bundle.manifest.get("artwork", {}).get(
            "generation",
            {},
        )
        if (
            generation.get("engine") == "flux"
            and generation.get("mode") == "identity_lock"
        ):
            current_prompt = (
                build_identity_lock_prompt(bundle.manifest, scope_data) + "\n"
            ).encode("utf-8")
            current_prompt_hash = hashlib.sha256(current_prompt).hexdigest()
        else:
            current_prompt_hash = sha256_file(
                prompt_path_for_generation(
                    bundle.work_dir,
                    generation,
                )
            )
        if prompt_record.get("sha256") != current_prompt_hash:
            drift.append("prompt_hash_drift")
    if not isinstance(cutout_records, list):
        invalid.append("provenance_cutout_records_missing")
    elif stored_generation_fingerprint is None:
        # Legacy provenance has byte hashes only. New fingerprints compare
        # decoded RGBA pixels, so a harmless PNG re-encode does not regenerate.
        recorded = [
            (
                Path(str(record.get("file", ""))).name,
                record.get("sha256"),
            )
            for record in cutout_records
            if isinstance(record, dict)
        ]
        current = [
            (path.name, sha256_file(path))
            for path, _item in cutouts
        ]
        if len(recorded) != len(cutout_records):
            invalid.append("provenance_cutout_records_invalid")
        elif recorded != current:
            drift.append("cutout_hash_drift")

    if stored_generation_fingerprint is not None:
        if not fingerprint_record_is_valid(stored_generation_fingerprint):
            invalid.append("generation_fingerprint_invalid")
        else:
            recorded_generation = run.get("generation", {})
            stored_contract = (
                generation_fingerprint_pipeline_contract_version(
                    stored_generation_fingerprint,
                    recorded_generation,
                )
            )
            current_generation_fingerprint = (
                rebuild_generation_fingerprint_from_recorded_sources(
                    bundle,
                    stored_generation_fingerprint,
                    scope_data_dir=scope_data_dir,
                )
            )
            if (
                stored_generation_fingerprint.get("sha256")
                != current_generation_fingerprint["sha256"]
            ):
                drift.append("generation_fingerprint_drift")
            elif stored_contract != (
                current_generation_pipeline_contract_version(
                    recorded_generation
                )
            ):
                pipeline_notes.append("accepted_legacy_pipeline")
    elif not manifest_matches and not drift:
        # A legacy full-manifest mismatch could be only pdf/title/overlay
        # routing, but could equally be an old identity-lock/conditioning
        # change. Without the old semantic components no safe migration or
        # regeneration claim is possible.
        invalid.append("legacy_manifest_drift_unclassifiable")

    if stored_overlay_fingerprint is not None:
        if not fingerprint_record_is_valid(stored_overlay_fingerprint):
            invalid.append("overlay_fingerprint_invalid")
        else:
            current_overlay_fingerprint = build_overlay_fingerprint(
                bundle,
                scope_data_dir=scope_data_dir,
                recorded=stored_overlay_fingerprint,
            )
            if (
                stored_overlay_fingerprint.get("sha256")
                != current_overlay_fingerprint["sha256"]
            ):
                overlay_drift.append("overlay_fingerprint_drift")
    else:
        overlay_drift.append("overlay_fingerprint_required")
    # Intentionally do not compare inputs.cutout_manifest.sha256. Its
    # generated_at field is operational metadata, not a generative input.
    return (
        list(_unique(drift)),
        list(_unique(invalid)),
        list(_unique(overlay_drift)),
        list(_unique(pipeline_notes)),
    )


def _candidate_commands(asset_key: str) -> tuple[str, ...]:
    return (
        "scripts/poster_assets/start_comfyui_poster.sh "
        f"--scope {asset_key}",
        "python scripts/poster_assets/run_comfyui_poster.py "
        f"--scope {asset_key}",
    )


def _plan_bundle(
    bundle: PosterBundle,
    *,
    scope_data_dir: Path,
    scene_catalog_path: Path,
    promotion_validator: PromotionValidator,
) -> WorkItem:
    base = {
        "asset_key": bundle.asset_key,
        "source_scope": bundle.scope,
        "poster_id": bundle.poster_id,
        "section_id": bundle.section_id,
        "pdf_enabled": bundle.pdf_enabled,
    }
    try:
        scope_data = load_poster_scope_data(
            bundle,
            scope_data_dir=scope_data_dir,
        )
        _validate_source_contract(bundle, scope_data)
        _validate_generation_contract(bundle.manifest)
        _validate_prompt_prerequisites(bundle)
        expected_scene = _expected_scene(
            bundle,
            scene_catalog_path=scene_catalog_path,
        )
        configured_scene = bundle.manifest.get("artwork", {}).get("scene")
    except Exception as error:
        return WorkItem(
            **base,
            state="blocked",
            reason_codes=("configuration_or_source_invalid",),
            next_actions=("repair_configuration",),
            detail=_detail(error),
        )

    try:
        provenance_path, artwork_path = _promotion_paths(bundle)
    except Exception as error:
        return WorkItem(
            **base,
            state="blocked",
            reason_codes=("configuration_or_source_invalid",),
            next_actions=("repair_configuration",),
            detail=_detail(error),
        )
    promotion_present = provenance_path.is_file()
    any_promotion_asset = any(
        path.exists() for path in (provenance_path, artwork_path)
    )
    if not _contains_catalog_contract(configured_scene, expected_scene):
        state = "promotion_stale" if promotion_present else "blocked"
        actions = (
            ("regenerate_candidate", "review_and_promote")
            if promotion_present
            else ("refresh_manifest_scene",)
        )
        return WorkItem(
            **base,
            state=state,
            reason_codes=("scene_catalog_drift",),
            next_actions=actions,
            commands=(
                _candidate_commands(bundle.asset_key)
                if promotion_present
                else ()
            ),
        )

    try:
        cutout_issues, checked_cutouts, cutout_detail = _cutout_asset_issues(
            bundle,
            scope_data,
        )
        logo_issues, logo_detail = _logo_asset_issues(bundle, scope_data)
    except Exception as error:
        return WorkItem(
            **base,
            state="blocked",
            reason_codes=("configuration_or_source_invalid",),
            next_actions=("repair_configuration",),
            detail=_detail(error),
        )
    asset_issues = _unique((*cutout_issues, *logo_issues))
    if asset_issues:
        actions: list[str] = []
        commands: list[str] = []
        if cutout_issues:
            actions.append("fetch_cutouts")
            commands.append(
                "python scripts/poster_assets/fetch_cutouts.py "
                f"--scope {bundle.asset_key}"
            )
        if logo_issues:
            actions.append("fetch_title_logos")
            commands.append(
                "python scripts/poster_assets/fetch_title_logos.py "
                f"--scope {bundle.asset_key}"
            )
        return WorkItem(
            **base,
            state="needs_assets",
            reason_codes=asset_issues,
            next_actions=tuple(actions),
            commands=tuple(commands),
            detail=cutout_detail or logo_detail,
        )

    if not promotion_present:
        if any_promotion_asset:
            return WorkItem(
                **base,
                state="invalid",
                reason_codes=("promotion_invalid", "provenance_missing"),
                next_actions=("repair_or_repromote",),
            )
        reason_codes = ["promotion_missing"]
        if bundle.pdf_enabled:
            reason_codes.append("pdf_enabled_without_promotion")
        return WorkItem(
            **base,
            state="ready_to_generate",
            reason_codes=tuple(reason_codes),
            next_actions=("generate_candidate",),
            commands=_candidate_commands(bundle.asset_key),
        )

    try:
        provenance = load_json(provenance_path)
    except Exception as error:
        return WorkItem(
            **base,
            state="invalid",
            reason_codes=("promotion_invalid", "provenance_invalid"),
            next_actions=("repair_or_repromote",),
            detail=_detail(error),
        )
    try:
        (
            drift,
            invalid,
            overlay_drift,
            pipeline_notes,
        ) = _promotion_drift_codes(
            bundle,
            scope_data,
            provenance,
            checked_cutouts,
            scope_data_dir=scope_data_dir,
        )
    except Exception as error:
        return WorkItem(
            **base,
            state="invalid",
            reason_codes=("promotion_invalid", "provenance_invalid"),
            next_actions=("repair_or_repromote",),
            detail=_detail(error),
        )
    if invalid:
        return WorkItem(
            **base,
            state="invalid",
            reason_codes=_unique(("promotion_invalid", *invalid)),
            next_actions=("repair_or_repromote",),
        )
    if drift:
        return WorkItem(
            **base,
            state="promotion_stale",
            reason_codes=_unique((*drift, *overlay_drift)),
            next_actions=("regenerate_candidate", "review_and_promote"),
            commands=_candidate_commands(bundle.asset_key),
        )
    try:
        validation_result = promotion_validator(bundle)
    except Exception as error:
        message = str(error).lower()
        if "drift" in message or (
            "do not match current featured_elements" in message
        ):
            return WorkItem(
                **base,
                state="promotion_stale",
                reason_codes=("validator_input_drift",),
                next_actions=("regenerate_candidate", "review_and_promote"),
                commands=_candidate_commands(bundle.asset_key),
                detail=_detail(error),
            )
        return WorkItem(
            **base,
            state="invalid",
            reason_codes=("promotion_invalid", "promotion_validation_failed"),
            next_actions=("repair_or_repromote",),
            detail=_detail(error),
        )

    overlay_is_current = (
        validation_result.get("overlay_fingerprint_current")
        if isinstance(validation_result, dict)
        else None
    )
    if overlay_is_current is False and not overlay_drift:
        overlay_drift = ["overlay_fingerprint_drift"]
    if (
        isinstance(validation_result, dict)
        and validation_result.get("generation_pipeline_contract_status")
        == "accepted_legacy"
        and not pipeline_notes
    ):
        pipeline_notes = ["accepted_legacy_pipeline"]
    overlay_actions = (
        ("refresh_promoted_overlay",)
        if overlay_drift
        else ()
    )
    pipeline_actions = (
        ("upgrade_generation_pipeline",)
        if pipeline_notes
        else ()
    )
    if bundle.pdf_enabled:
        return WorkItem(
            **base,
            state="current",
            reason_codes=_unique(
                (
                    "promotion_current",
                    "pdf_enabled",
                    *overlay_drift,
                    *pipeline_notes,
                )
            ),
            next_actions=(*overlay_actions, *pipeline_actions),
        )
    return WorkItem(
        **base,
        state="promoted_disabled",
        reason_codes=_unique(
            (
                "promotion_current",
                "pdf_disabled",
                *overlay_drift,
                *pipeline_notes,
            )
        ),
        next_actions=(
            *overlay_actions,
            *pipeline_actions,
            "enable_pdf_after_review",
        ),
    )


def build_work_plan(
    *,
    scope: str | None = None,
    all_configured: bool = False,
    poster_assets: Path = POSTER_ASSETS,
    poster_configs: Path | None = None,
    scope_data_dir: Path = SCOPE_DATA,
    scene_catalog_path: Path = SCENE_CATALOG,
    promotion_validator: PromotionValidator | None = None,
) -> dict[str, Any]:
    """Build a deterministic poster work plan without changing local state."""
    if (scope is None) == (not all_configured):
        raise ValueError("Choose exactly one of scope or all_configured")
    config_root = poster_configs or (
        POSTER_CONFIGS if poster_assets == POSTER_ASSETS else poster_assets
    )
    validator = promotion_validator or validate
    requested = (
        _configured_roots(config_root)
        if all_configured
        else [str(scope)]
    )
    items: list[WorkItem] = []
    for requested_scope in requested:
        resolved = _resolve_targets(
            requested_scope,
            poster_assets=poster_assets,
            poster_configs=config_root,
            scope_data_dir=scope_data_dir,
        )
        if isinstance(resolved, WorkItem):
            items.append(resolved)
            continue
        items.extend(
            _plan_bundle(
                bundle,
                scope_data_dir=scope_data_dir,
                scene_catalog_path=scene_catalog_path,
                promotion_validator=validator,
            )
            for bundle in resolved
        )

    counts = {
        state: sum(item.state == state for item in items)
        for state in STATES
        if any(item.state == state for item in items)
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "all_configured" if all_configured else "scope",
        "requested_scope": None if all_configured else scope,
        "summary": {
            "targets": len(items),
            "states": counts,
        },
        "targets": [item.as_dict() for item in items],
    }


def format_text(plan: dict[str, Any]) -> str:
    """Return a concise human-readable rendering of a work plan."""
    targets = plan.get("targets", [])
    if not targets:
        return "No configured poster targets."
    width = max(
        len("TARGET"),
        *(len(str(target["asset_key"])) for target in targets),
    )
    lines = [
        f"{'STATE':<19} {'PDF':<3} {'TARGET':<{width}}  REASONS -> NEXT",
    ]
    for target in targets:
        enabled = target.get("pdf_enabled")
        pdf = "on" if enabled is True else "off" if enabled is False else "-"
        reasons = ",".join(target.get("reason_codes", [])) or "-"
        actions = ",".join(target.get("next_actions", [])) or "none"
        lines.append(
            f"{target['state']:<19} {pdf:<3} "
            f"{target['asset_key']:<{width}}  {reasons} -> {actions}"
        )
    states = plan.get("summary", {}).get("states", {})
    summary = ", ".join(
        f"{state}={states[state]}"
        for state in STATES
        if state in states
    )
    lines.append(
        f"{plan.get('summary', {}).get('targets', len(targets))} target(s): "
        f"{summary}"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--scope",
        help=(
            "Individual scope, aggregate root, or indexed nested asset key"
        ),
    )
    target.add_argument(
        "--all-configured",
        action="store_true",
        help="Inspect every configured poster target",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
    )
    parser.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="format",
        help="Shortcut for --format json",
    )
    args = parser.parse_args(argv)
    plan = build_work_plan(
        scope=args.scope,
        all_configured=args.all_configured,
    )
    if args.format == "json":
        print(
            json.dumps(
                plan,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    else:
        print(format_text(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
