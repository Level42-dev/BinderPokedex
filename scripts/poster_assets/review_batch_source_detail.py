"""Build source-bound v11 manifests for review trials, without activating them."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import sys

import yaml

from . import poster_io
from .poster_subject import resolve_poster_subject
from .source_detail import validate_source_details


ROOT = Path(__file__).resolve().parents[2]
TRAITS_PATH = ROOT / "docs/reviews/2026-09-22-panorama-source-traits.yaml"
RETRIAGE_PATH = ROOT / "docs/reviews/2026-09-14-panorama-retriage.json"
SAFE_PART = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
SAFE_VARIANT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def _safe_scope(scope: str) -> Path:
    if not isinstance(scope, str) or not scope or scope.startswith("/"):
        raise ValueError("scope is not listed or safe")
    parts = scope.split("/")
    if any(part in {".", ".."} or not SAFE_PART.fullmatch(part) for part in parts):
        raise ValueError("scope is not listed or safe")
    return Path(*parts)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _existing_traits(config_root: Path, key: str, digest: str) -> str | None:
    for candidate in sorted(config_root.rglob("poster.yaml")):
        record = (yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}).get(
            "artwork", {},
        ).get("source_details", {}).get(key)
        if isinstance(record, dict) and record.get("sha256") == digest:
            text = record.get("traits")
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def build_trial_manifest(
    scope: str,
    variant: str,
    seed: int,
    *,
    repository_root: Path = ROOT,
    traits_path: Path = TRAITS_PATH,
    retriage_path: Path = RETRIAGE_PATH,
) -> Path:
    """Freeze a safe, exactly sourced overlay at ``tmp/review-batch-manifests``."""
    relative = _safe_scope(scope)
    if not isinstance(variant, str) or not SAFE_VARIANT.fullmatch(variant) or ".." in variant:
        raise ValueError("unsafe variant")
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("seed must be a 32-bit unsigned integer")
    root = Path(repository_root).resolve()
    traits_data = yaml.safe_load(Path(traits_path).read_text(encoding="utf-8"))
    report = json.loads(Path(retriage_path).read_text(encoding="utf-8"))
    if not isinstance(traits_data, dict) or traits_data.get("schema_version") != 1:
        raise ValueError("unsupported source-traits inventory")
    scopes = traits_data.get("scopes")
    descriptions = traits_data.get("traits")
    if not isinstance(scopes, dict) or not isinstance(descriptions, dict):
        raise ValueError("invalid source-traits inventory")
    matches = [item for item in report.get("targets", []) if item.get("asset_key") == scope]
    if len(matches) != 1 or scopes.get(matches[0].get("review_id")) != scope:
        raise ValueError("scope is not listed for a review batch")
    target = matches[0]
    config_path = root / "config/posters" / relative / "poster.yaml"
    source_dir = root / "tmp/poster-workspaces" / relative / "sources/cutouts"
    source_manifest = json.loads((source_dir / "manifest.json").read_text(encoding="utf-8"))
    items = source_manifest.get("items")
    reviewed = target.get("subjects")
    if not isinstance(items, list) or not items or not isinstance(reviewed, list) or len(items) != len(reviewed):
        raise ValueError("canonical and reviewed cast lengths differ")
    manifest = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if manifest.get("asset_key", scope) != scope:
        raise ValueError("production manifest identifies another scope")
    details = {}
    for item, review_subject in zip(items, reviewed, strict=True):
        key = resolve_poster_subject(item).subject_key
        if key in details:
            raise ValueError("duplicate canonical source key")
        file_name = item.get("file")
        if not isinstance(file_name, str) or Path(file_name).name != file_name:
            raise ValueError("unsafe source file name")
        path = (source_dir / file_name).resolve()
        if not path.is_relative_to(source_dir.resolve()):
            raise ValueError("source file escapes cutout directory")
        expected_file = path.relative_to(root).as_posix()
        source_record = review_subject.get("source")
        if not isinstance(source_record, dict) or source_record.get("file") != expected_file:
            raise ValueError("source file differs from hash-bound retriage")
        digest = _sha256(path)
        if source_record.get("sha256") != digest:
            raise ValueError("source hash differs from hash-bound retriage")
        traits = descriptions.get(key)
        if traits is None:
            traits = _existing_traits(root / "config/posters", key, digest)
        if not isinstance(traits, str) or not traits.strip():
            raise ValueError(f"source trait missing for {key}")
        details[key] = {"sha256": digest, "traits": traits.strip()}
    manifest.setdefault("artwork", {})["source_details"] = details
    generation = manifest["artwork"]["generation"]
    generation.update(
        mode="joint_scene",
        reference_mode="spatial_source_detail_joint",
        seed=seed,
        steps=4,
        generation_megapixels=2.0,
        output_dpi=300,
        output_method="lanczos",
    )
    validate_source_details(manifest, items, source_dir.parent)
    output = root / "tmp/review-batch-manifests" / variant / "poster.yaml"
    if output.exists():
        raise FileExistsError("trial manifest already exists; refusing overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")
    return output


@contextmanager
def trial_manifest_bundle(
    scope: str,
    trial_manifest: Path,
    *,
    repository_root: Path = ROOT,
    isolated_work_dir: Path | None = None,
):
    """Temporarily route one sequential review process to its ignored overlay."""
    relative = _safe_scope(scope)
    root = Path(repository_root).resolve()
    trial_manifest = Path(trial_manifest).resolve()
    allowed = (root / "tmp/review-batch-manifests").resolve()
    if not trial_manifest.is_relative_to(allowed) or trial_manifest.name != "poster.yaml":
        raise ValueError("trial manifest must stay in ignored review-batch space")
    manifest = yaml.safe_load(trial_manifest.read_text(encoding="utf-8"))
    if manifest.get("asset_key", scope) != scope:
        raise ValueError("trial manifest identifies another scope")
    if isolated_work_dir is not None:
        isolated_work_dir = Path(isolated_work_dir)
        allowed_work_root = root / "tmp/oneshot-trials"
        resolved = isolated_work_dir.resolve()
        relative_work = resolved.relative_to(allowed_work_root) if resolved.is_relative_to(allowed_work_root) else None
        if (
            relative_work is None
            or len(relative_work.parts) != 2
            or not SAFE_VARIANT.fullmatch(relative_work.parts[0])
            or ".." in relative_work.parts[0]
            or relative_work.parts[1] != "prepared"
        ):
            raise ValueError("isolated work dir must stay under one trial's prepared directory")
    original = poster_io.poster_bundle

    def resolve(asset_key, *args, **kwargs):
        if asset_key != scope:
            return original(asset_key, *args, **kwargs)
        bundle = original(
            asset_key,
            poster_assets=root / "assets/posters",
            poster_configs=root / "config/posters",
            poster_workspaces=root / "tmp/poster-workspaces",
        )
        return replace(
            bundle,
            manifest_path=trial_manifest,
            manifest=manifest,
            work_dir=isolated_work_dir if isolated_work_dir is not None else bundle.work_dir,
        )

    modules = [
        module for name, module in list(sys.modules.items())
        if name.startswith("scripts.poster_assets.") and getattr(module, "poster_bundle", None) is original
    ]
    try:
        poster_io.poster_bundle = resolve
        for module in modules:
            module.poster_bundle = resolve
        yield
    finally:
        poster_io.poster_bundle = original
        for module in modules:
            module.poster_bundle = original
