#!/usr/bin/env python3
"""Build a deterministic manifest for release announcement automation."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


LANGUAGES = {
    "de": {"name": "Deutsch", "zip": "binder-pokedex-de.zip"},
    "en": {"name": "English", "zip": "binder-pokedex-en.zip"},
    "fr": {"name": "Francais", "zip": "binder-pokedex-fr.zip"},
    "es": {"name": "Espanol", "zip": "binder-pokedex-es.zip"},
    "it": {"name": "Italiano", "zip": "binder-pokedex-it.zip"},
    "ja": {"name": "Japanese", "zip": "binder-pokedex-ja.zip"},
    "ko": {"name": "Korean", "zip": "binder-pokedex-ko.zip"},
    "zh_hans": {"name": "Simplified Chinese", "zip": "binder-pokedex-zh_hans.zip"},
    "zh_hant": {"name": "Traditional Chinese", "zip": "binder-pokedex-zh_hant.zip"},
}


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def discover_scopes(project_dir: Path) -> list[str]:
    scope_dir = project_dir / "config" / "scopes"
    scopes = sorted(path.stem for path in scope_dir.glob("*.yaml"))
    if "Pokedex" in scopes:
        scopes.remove("Pokedex")
        scopes.insert(0, "Pokedex")
    return scopes


def count_cards(project_dir: Path, scopes: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for scope in scopes:
        path = project_dir / "data" / "output" / f"{scope}.json"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        total = 0
        for section in data.get("sections", {}).values():
            total += len(section.get("cards", []))
        counts[scope] = total
    return counts


def count_pdfs(project_dir: Path) -> dict[str, Any]:
    output_dir = project_dir / "output"
    by_language: dict[str, int] = {}
    total = 0
    for language in LANGUAGES:
        count = len(list((output_dir / language).glob("*.pdf")))
        by_language[language] = count
        total += count
    return {"total": total, "by_language": by_language}


def list_assets(project_dir: Path) -> list[dict[str, Any]]:
    assets = []
    for language, info in LANGUAGES.items():
        path = project_dir / info["zip"]
        assets.append(
            {
                "language": language,
                "name": info["zip"],
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return assets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--release-notes-tag", default=None)
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--output", default="release-manifest.json")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    scopes = discover_scopes(project_dir)
    release_notes_tag = args.release_notes_tag or args.tag
    release_notes = load_yaml(
        project_dir / "config" / "release_notes" / f"{release_notes_tag}.yaml"
    )

    manifest = {
        "schema_version": 1,
        "tag": args.tag,
        "release_notes_tag": release_notes_tag,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "languages": LANGUAGES,
        "scopes": scopes,
        "scope_count": len(scopes),
        "scope_groups": {
            "pokedex": [scope for scope in scopes if scope == "Pokedex"],
            "ex": [scope for scope in scopes if scope.startswith("ExGen")],
            "mega": [scope for scope in scopes if scope.startswith("ME")],
            "scarlet_violet": [scope for scope in scopes if scope.startswith("SV")],
            "anniversary": [scope for scope in scopes if scope in {"30C", "30CClassic"}],
        },
        "card_counts": count_cards(project_dir, scopes),
        "pdfs": count_pdfs(project_dir),
        "assets": list_assets(project_dir),
        "release_notes": release_notes,
    }

    output_path = project_dir / args.output
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
