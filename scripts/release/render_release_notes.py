#!/usr/bin/env python3
"""Render a GitHub Release body from the verified release manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPOSITORY = "Level42-dev/BinderPokedex"
LANGUAGE_LABELS = {
    "de": ("🇩🇪", "Deutsch"),
    "en": ("🇬🇧", "English"),
    "fr": ("🇫🇷", "Français"),
    "es": ("🇪🇸", "Español"),
    "it": ("🇮🇹", "Italiano"),
    "ja": ("🇯🇵", "日本語"),
    "ko": ("🇰🇷", "한국어"),
    "zh_hans": ("🇨🇳", "简体中文"),
    "zh_hant": ("🇹🇼", "繁體中文"),
}


def _raw_url(tag: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{REPOSITORY}/{tag}/{path}"


def _asset_url(tag: str, name: str) -> str:
    return f"https://github.com/{REPOSITORY}/releases/download/{tag}/{name}"


def _localized_section(title: str, notes: dict[str, Any]) -> list[str]:
    lines = [f"## {title}", "", f"### {notes['title']}", ""]
    lines.extend(f"- {item}" for item in notes.get("body", []))
    return lines


def render_release_notes(manifest: dict[str, Any]) -> str:
    """Render the user-facing, bilingual GitHub Release description."""
    tag = str(manifest["tag"])
    release_notes = manifest.get("release_notes", {})
    whats_new = release_notes.get("whats_new", {})
    if not all(language in whats_new for language in ("en", "de")):
        raise ValueError("Release notes require English and German content")

    lines = [f"# Binder Pokédex {tag}", ""]
    hero = release_notes.get("hero", {})
    if hero.get("path"):
        alt = hero.get("alt", "BinderPokedex")
        lines.extend([f"![{alt}]({_raw_url(tag, hero['path'])})", ""])

    summary = release_notes.get("summary", {})
    if summary.get("en"):
        lines.extend([summary["en"], ""])

    lines.extend(_localized_section("What's new", whats_new["en"]))
    lines.extend(["", "---", ""])
    if summary.get("de"):
        lines.extend([summary["de"], ""])
    lines.extend(_localized_section("Was ist neu", whats_new["de"]))

    preview = release_notes.get("preview", {})
    if preview.get("path"):
        alt = preview.get("alt", "Actual BinderPokedex PDF output")
        lines.extend(
            [
                "",
                "## Actual PDF output · Echte PDF-Ausgabe",
                "",
                f"![{alt}]({_raw_url(tag, preview['path'])})",
            ]
        )

    lines.extend(["", "## Downloads", ""])
    languages = manifest.get("languages", {})
    for language, (flag, label) in LANGUAGE_LABELS.items():
        asset = languages.get(language, {}).get("zip")
        if not asset:
            raise ValueError(f"Release manifest has no archive for {language}")
        lines.append(f"- {flag} [{label}]({_asset_url(tag, asset)})")

    lines.extend(
        [
            "",
            "---",
            "",
            "This is a fan-made, non-commercial project. Pokémon and all related "
            "trademarks belong to their respective owners.",
            "",
            f"[Documentation](https://github.com/{REPOSITORY}/tree/{tag}/docs) · "
            f"[Full changelog](https://github.com/{REPOSITORY}/blob/{tag}/CHANGELOG.md)",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", default="release-notes.md")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    Path(args.output).write_text(render_release_notes(manifest), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
