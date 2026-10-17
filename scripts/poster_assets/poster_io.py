"""Shared paths and structured-file readers for poster assets."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
POSTER_WORKSPACE_ENV = "BINDER_POKEDEX_POSTER_ASSETS"
POSTER_ASSETS_ENV = POSTER_WORKSPACE_ENV


def resolve_poster_assets_root(value: str | None = None) -> Path:
    """Resolve a combined custom workspace or the durable asset root."""
    configured = value if value is not None else os.environ.get(
        POSTER_WORKSPACE_ENV
    )
    if not configured:
        return ROOT / "assets" / "posters"
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


POSTER_WORKSPACE = (
    resolve_poster_assets_root()
    if os.environ.get(POSTER_WORKSPACE_ENV)
    else None
)
POSTER_CONFIGS = POSTER_WORKSPACE or ROOT / "config" / "posters"
POSTER_ASSETS = POSTER_WORKSPACE or ROOT / "assets" / "posters"
POSTER_WORKSPACES = POSTER_WORKSPACE or ROOT / "tmp" / "poster-workspaces"
POSTER_DEFAULTS = ROOT / "config" / "posters" / "defaults.yaml"
SCOPE_DATA = ROOT / "data" / "output"
POSTER_INDEX_NAME = "posters.yaml"
POSTER_MANIFEST_NAME = "poster.yaml"
_SAFE_KEY_PART = re.compile(r"[A-Za-z0-9._-]+")


@dataclass(frozen=True)
class PosterBundle:
    """One independently generated poster and its aggregate-section routing."""

    asset_key: str
    scope: str
    poster_id: str
    section_id: str | None
    asset_dir: Path
    manifest_path: Path
    manifest: dict[str, Any]
    pdf_enabled: bool
    insertion: str
    artwork_file: str
    config_dir: Path | None = None
    source_dir: Path | None = None
    work_dir: Path | None = None

    def __post_init__(self) -> None:
        """Supply combined-root defaults for older callers and test fixtures."""
        if self.config_dir is None:
            object.__setattr__(self, "config_dir", self.manifest_path.parent)
        if self.source_dir is None:
            object.__setattr__(self, "source_dir", self.asset_dir)
        if self.work_dir is None:
            object.__setattr__(
                self,
                "work_dir",
                self.asset_dir / "comfyui_poster",
            )


class _PosterLoader(yaml.SafeLoader):
    """Keep YAML semantics while rejecting ambiguous source-detail bindings."""

    def construct_mapping(self, node, deep=False):
        for key, value in node.value:
            if key.value in {"source_details", "spatial_reference_scales"} and isinstance(value, yaml.MappingNode):
                names = [entry.value for entry, _ in value.value]
                if len(names) != len(set(names)):
                    raise ValueError(f"Duplicate {key.value} canonical subject key")
        return super().construct_mapping(node, deep=deep)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.load(handle, Loader=_PosterLoader) or {}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_cutout_items(scope_dir: Path) -> list[dict[str, Any]]:
    manifest = load_json(scope_dir / "cutouts" / "manifest.json")
    return list(manifest.get("items", []))


def _safe_key(value: object, path: str) -> str:
    if (
        not isinstance(value, str)
        or value in {".", ".."}
        or not _SAFE_KEY_PART.fullmatch(value)
    ):
        raise ValueError(
            f"{path} must contain only letters, digits, '.', '_' or '-'"
        )
    return value


def _safe_relative_asset(value: object, path: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must be a non-empty relative asset path")
    relative = Path(value)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or not relative.parts
        or any(not _SAFE_KEY_PART.fullmatch(part) for part in relative.parts)
    ):
        raise ValueError(f"Unsafe relative poster asset path at {path}: {value!r}")
    return relative


def poster_asset_dir(
    asset_key: str,
    *,
    poster_assets: Path = POSTER_ASSETS,
) -> Path:
    """Resolve a slash-separated poster key below the controlled asset root."""
    relative = _safe_relative_asset(asset_key, "poster asset key")
    return poster_assets.joinpath(*relative.parts)


def poster_config_dir(
    asset_key: str,
    *,
    poster_configs: Path = POSTER_CONFIGS,
) -> Path:
    """Resolve a poster key below the versioned configuration root."""
    relative = _safe_relative_asset(asset_key, "poster asset key")
    return poster_configs.joinpath(*relative.parts)


def poster_work_dir(
    asset_key: str,
    *,
    poster_workspaces: Path = POSTER_WORKSPACES,
) -> Path:
    """Resolve a poster key below the ignored working root."""
    relative = _safe_relative_asset(asset_key, "poster asset key")
    return poster_workspaces.joinpath(*relative.parts, "comfyui_poster")


def poster_source_dir(
    asset_key: str,
    *,
    poster_workspaces: Path = POSTER_WORKSPACES,
) -> Path:
    """Resolve reproducible downloaded inputs below the ignored workspace."""
    relative = _safe_relative_asset(asset_key, "poster asset key")
    return poster_workspaces.joinpath(*relative.parts, "sources")


def _poster_roots(
    poster_assets: Path,
    poster_configs: Path | None,
    poster_workspaces: Path | None,
) -> tuple[Path, Path, Path]:
    """Resolve split production roots or one explicit combined workspace.

    The historical ``poster_assets=...`` test and custom-workspace API remains
    a combined root. The default production asset root selects the split
    configuration, durable-asset, and ignored-workspace directories.
    """
    if poster_configs is None and poster_workspaces is None:
        if poster_assets == POSTER_ASSETS:
            return POSTER_CONFIGS, POSTER_ASSETS, POSTER_WORKSPACES
        return poster_assets, poster_assets, poster_assets
    if (
        poster_workspaces is None
        and poster_configs == poster_assets
        and poster_assets != POSTER_ASSETS
    ):
        return poster_configs, poster_assets, poster_assets
    return (
        poster_configs or POSTER_CONFIGS,
        poster_assets,
        poster_workspaces or POSTER_WORKSPACES,
    )


def poster_asset_slug(asset_key: str) -> str:
    """Return a filename-safe, readable form of a possibly nested asset key."""
    relative = _safe_relative_asset(asset_key, "poster asset key")
    return "__".join(part.lower() for part in relative.parts)


def poster_bundle(
    asset_key: str,
    *,
    scope: str | None = None,
    poster_id: str | None = None,
    section_id: str | None = None,
    pdf_config: dict[str, Any] | None = None,
    poster_assets: Path = POSTER_ASSETS,
    poster_configs: Path | None = None,
    poster_workspaces: Path | None = None,
) -> PosterBundle:
    """Load one normal poster manifest from a stable asset key."""
    config_root, asset_root, workspace_root = _poster_roots(
        poster_assets,
        poster_configs,
        poster_workspaces,
    )
    config_dir = poster_config_dir(asset_key, poster_configs=config_root)
    asset_dir = poster_asset_dir(asset_key, poster_assets=asset_root)
    work_dir = poster_work_dir(asset_key, poster_workspaces=workspace_root)
    source_dir = (
        asset_dir
        if config_root == asset_root == workspace_root
        else poster_source_dir(
            asset_key,
            poster_workspaces=workspace_root,
        )
    )
    manifest_path = config_dir / POSTER_MANIFEST_NAME
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = load_yaml(manifest_path)
    manifest_key = manifest.get("asset_key") or manifest.get("scope")
    if manifest_key is not None and manifest_key != asset_key:
        raise ValueError(
            f"{manifest_path} identifies {manifest_key!r}, expected {asset_key!r}"
        )
    resolved_scope = _safe_key(
        scope or str(asset_key).split("/", 1)[0],
        "poster scope",
    )
    if manifest.get("asset_key") is not None and (
        manifest.get("scope") != resolved_scope
    ):
        raise ValueError(
            f"{manifest_path} must identify source scope {resolved_scope!r}"
        )
    source = manifest.get("source", {})
    if not isinstance(source, dict):
        raise ValueError(f"{manifest_path}: source must be a mapping")
    if source and source.get("scope", resolved_scope) != resolved_scope:
        raise ValueError(
            f"{manifest_path} must source scope {resolved_scope!r}"
        )
    resolved_poster_id = _safe_key(
        poster_id
        or manifest.get("poster_id")
        or str(asset_key).rsplit("/", 1)[-1],
        "poster id",
    )
    configured_section = section_id or source.get("section_id")
    resolved_section = (
        _safe_key(configured_section, "poster section_id")
        if configured_section is not None
        else None
    )
    resolved_pdf = (
        manifest.get("pdf", {})
        if pdf_config is None
        else pdf_config
    )
    if not isinstance(resolved_pdf, dict):
        raise ValueError("poster pdf configuration must be a mapping")
    enabled = resolved_pdf.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("poster pdf.enabled must be a boolean")
    insertion = str(
        resolved_pdf.get("insertion", "after_first_section_cover")
    )
    if insertion not in {
        "after_first_section_cover",
        "after_section_cover",
    }:
        raise ValueError(f"Unsupported poster PDF insertion: {insertion}")
    if insertion == "after_section_cover" and resolved_section is None:
        raise ValueError(
            "after_section_cover requires a poster section_id"
        )
    artwork_file = resolved_pdf.get(
        "artwork_file",
        manifest.get("artwork", {}).get(
            "promoted_file",
            "poster-flux2-artwork.png",
        ),
    )
    artwork_relative = _safe_relative_asset(
        artwork_file,
        "poster pdf.artwork_file",
    )
    return PosterBundle(
        asset_key=asset_key,
        scope=resolved_scope,
        poster_id=resolved_poster_id,
        section_id=resolved_section,
        config_dir=config_dir,
        asset_dir=asset_dir,
        source_dir=source_dir,
        work_dir=work_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        pdf_enabled=enabled,
        insertion=insertion,
        artwork_file=artwork_relative.as_posix(),
    )


def poster_bundles_for_scope(
    scope: str,
    *,
    poster_assets: Path = POSTER_ASSETS,
    poster_configs: Path | None = None,
    poster_workspaces: Path | None = None,
) -> list[PosterBundle]:
    """Discover a legacy single bundle or an aggregate scope's ordered bundles."""
    scope = _safe_key(scope, "poster scope")
    config_root, _asset_root, _workspace_root = _poster_roots(
        poster_assets,
        poster_configs,
        poster_workspaces,
    )
    scope_dir = config_root / scope
    single_manifest = scope_dir / POSTER_MANIFEST_NAME
    index_path = scope_dir / POSTER_INDEX_NAME
    if single_manifest.is_file() and index_path.is_file():
        raise ValueError(
            f"{scope_dir} cannot contain both {POSTER_MANIFEST_NAME} and "
            f"{POSTER_INDEX_NAME}"
        )
    if single_manifest.is_file():
        return [
            poster_bundle(
                scope,
                scope=scope,
                poster_assets=poster_assets,
                poster_configs=config_root,
                poster_workspaces=_workspace_root,
            )
        ]
    if not index_path.is_file():
        return []

    index = load_yaml(index_path)
    index_version = index.get("schema_version", index.get("version"))
    if index_version != 1:
        raise ValueError(f"Unsupported poster index version: {index_path}")
    if index.get("scope") != scope:
        raise ValueError(
            f"{index_path} identifies scope {index.get('scope')!r}, "
            f"expected {scope!r}"
        )
    configured = index.get("posters")
    if not isinstance(configured, list) or not configured:
        raise ValueError(f"{index_path} must contain a non-empty posters list")

    bundles: list[PosterBundle] = []
    seen_poster_ids: set[str] = set()
    seen_sections: set[str] = set()
    seen_assets: set[str] = set()
    for item_index, item in enumerate(configured):
        item_path = f"{index_path}:posters[{item_index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{item_path} must be a mapping")
        poster_id = _safe_key(item.get("id"), f"{item_path}.id")
        section_id = _safe_key(item.get("section_id"), f"{item_path}.section_id")
        relative_manifest = _safe_relative_asset(
            item.get("manifest"),
            f"{item_path}.manifest",
        )
        if relative_manifest.name != POSTER_MANIFEST_NAME:
            raise ValueError(
                f"{item_path}.manifest must end in {POSTER_MANIFEST_NAME}"
            )
        if poster_id in seen_poster_ids:
            raise ValueError(f"Duplicate poster id {poster_id!r}")
        if section_id in seen_sections:
            raise ValueError(f"Duplicate poster section_id {section_id!r}")
        asset_relative = relative_manifest.parent
        asset_key = f"{scope}/{asset_relative.as_posix()}"
        if asset_key in seen_assets:
            raise ValueError(f"Duplicate poster asset {asset_key!r}")
        seen_poster_ids.add(poster_id)
        seen_sections.add(section_id)
        seen_assets.add(asset_key)
        pdf_config = item.get("pdf", {})
        if not isinstance(pdf_config, dict):
            raise ValueError(f"{item_path}.pdf must be a mapping")
        bundle = poster_bundle(
            asset_key,
            scope=scope,
            poster_id=poster_id,
            section_id=section_id,
            pdf_config=pdf_config,
            poster_assets=poster_assets,
            poster_configs=config_root,
            poster_workspaces=_workspace_root,
        )
        if bundle.manifest.get("scope") != scope:
            raise ValueError(
                f"{bundle.manifest_path} must identify scope {scope!r}"
            )
        if bundle.manifest.get("poster_id") != poster_id:
            raise ValueError(
                f"{bundle.manifest_path} must identify poster_id {poster_id!r}"
            )
        if bundle.insertion != "after_section_cover":
            raise ValueError(
                f"{item_path}.pdf.insertion must be after_section_cover"
            )
        promoted_file = bundle.manifest.get("artwork", {}).get(
            "promoted_file",
            "poster-flux2-artwork.png",
        )
        if bundle.artwork_file != promoted_file:
            raise ValueError(
                f"{item_path}.pdf.artwork_file must match the leaf manifest's "
                f"artwork.promoted_file ({promoted_file!r})"
            )
        source = bundle.manifest.get("source", {})
        if not isinstance(source, dict):
            raise ValueError(f"{bundle.manifest_path}: source must be a mapping")
        if source.get("scope", scope) != scope:
            raise ValueError(
                f"{bundle.manifest_path} must source aggregate scope {scope!r}"
            )
        if source.get("section_id") != section_id:
            raise ValueError(
                f"{bundle.manifest_path} must source section {section_id!r}"
            )
        bundles.append(bundle)
    return bundles


def load_poster_scope_data(
    bundle: PosterBundle,
    *,
    scope_data_dir: Path = SCOPE_DATA,
) -> dict[str, Any]:
    """Load only the source section that conditions and labels a poster bundle."""
    source = bundle.manifest.get("source", {})
    if not isinstance(source, dict):
        raise ValueError(f"{bundle.manifest_path}: source must be a mapping")
    source_scope = _safe_key(
        source.get("scope", bundle.scope),
        "poster source.scope",
    )
    source_path = scope_data_dir / f"{source_scope}.json"
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    scope_data = load_json(source_path)
    return select_poster_scope_data(
        bundle,
        scope_data,
        source_name=str(source_path),
    )


def select_poster_scope_data(
    bundle: PosterBundle,
    scope_data: dict[str, Any],
    *,
    source_name: str = "scope data",
) -> dict[str, Any]:
    """Select one bundle's source section from already loaded aggregate data."""
    source = bundle.manifest.get("source", {})
    if not isinstance(source, dict):
        raise ValueError(f"{bundle.manifest_path}: source must be a mapping")
    source_scope = _safe_key(
        source.get("scope", bundle.scope),
        "poster source.scope",
    )

    source_section = source.get("section_id")
    if source_section is None:
        return scope_data
    section_id = _safe_key(source_section, "poster source.section_id")
    sections = scope_data.get("sections")
    section: dict[str, Any] | None = None
    if isinstance(sections, dict):
        candidate = sections.get(section_id)
        if isinstance(candidate, dict):
            section = candidate
    elif isinstance(sections, list):
        section = next(
            (
                candidate
                for candidate in sections
                if isinstance(candidate, dict)
                and candidate.get("section_id") == section_id
            ),
            None,
        )
    if section is None:
        raise KeyError(
            f"Poster source section {section_id!r} not found in {source_name}"
        )

    selected = dict(scope_data)
    selected["sections"] = {section_id: section}
    selected["_poster_source"] = {
        "scope": source_scope,
        "section_id": section_id,
    }
    return selected
