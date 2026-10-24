#!/usr/bin/env python3
"""Update README downloads and user-facing news from a release manifest."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


LANGUAGE_LINKS_EN = [
    ("de", "🇩🇪", "Deutsch"),
    ("en", "🇬🇧", "English"),
    ("fr", "🇫🇷", "Français"),
    ("es", "🇪🇸", "Español"),
    ("it", "🇮🇹", "Italiano"),
    ("ja", "🇯🇵", "日本語"),
    ("ko", "🇰🇷", "한국어"),
    ("zh_hans", "🇨🇳", "简体中文"),
    ("zh_hant", "🇹🇼", "繁體中文"),
]

LANGUAGE_LINKS_DE = [
    ("de", "🇩🇪", "DE"),
    ("en", "🇬🇧", "EN"),
    ("fr", "🇫🇷", "FR"),
    ("es", "🇪🇸", "ES"),
    ("it", "🇮🇹", "IT"),
    ("ja", "🇯🇵", "JA"),
    ("ko", "🇰🇷", "KO"),
    ("zh_hans", "🇨🇳", "ZH"),
    ("zh_hant", "🇹🇼", "ZH-T"),
]

NEWS_START = "<!-- release-news:start -->"
NEWS_END = "<!-- release-news:end -->"


def read_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def replace_one(text: str, pattern: str, replacement: str, path: Path) -> str:
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Expected exactly one match for {pattern!r} in {path}")
    return new_text


def release_url(manifest: dict[str, Any], explicit_url: str | None) -> str:
    if explicit_url:
        return explicit_url
    tag = manifest["tag"]
    return f"https://github.com/Level42-dev/BinderPokedex/releases/tag/{tag}"


def download_url(tag: str, asset: str, release_page_url: str) -> str:
    release_suffix = f"/releases/tag/{tag}"
    if not release_page_url.endswith(release_suffix):
        raise ValueError(f"Unexpected release URL: {release_page_url}")
    repository_url = release_page_url[: -len(release_suffix)]
    return f"{repository_url}/releases/download/{tag}/{asset}"


def language_links(
    tag: str,
    links: list[tuple[str, str, str]],
    separator: str,
    release_page_url: str,
) -> str:
    parts = []
    for language, flag, label in links:
        asset = f"binder-pokedex-{language}.zip"
        parts.append(f"{flag} [{label}]({download_url(tag, asset, release_page_url)})")
    return separator.join(parts)


def release_news(
    markdown_language: str,
    manifest: dict[str, Any],
    explicit_url: str | None,
) -> str:
    """Render the compact, collector-facing news block for the README."""
    notes = (
        manifest.get("release_notes", {})
        .get("whats_new", {})
        .get(markdown_language, {})
    )
    title = notes.get("title", manifest["tag"])
    body = notes.get("body", [])
    intro = summary(markdown_language, manifest)
    if markdown_language == "en":
        heading = f"### New in {manifest['tag']}: {title}"
        cta = (
            f"**[Explore {manifest['tag']} and download the PDFs]"
            f"({release_url(manifest, explicit_url)})**"
        )
        details = "Technical details: [full changelog](CHANGELOG.md)."
    else:
        heading = f"### Neu in {manifest['tag']}: {title}"
        cta = (
            f"**[{manifest['tag']} ansehen und PDFs herunterladen]"
            f"({release_url(manifest, explicit_url)})**"
        )
        details = "Technische Details: [vollständiges Changelog](CHANGELOG.md)."

    lines = [heading, "", intro]
    if body:
        lines.extend(["", *(f"- {item}" for item in body)])
    lines.extend(["", cta, "", details])
    return "\n".join(lines)


def replace_release_news(
    text: str,
    path: Path,
    markdown_language: str,
    manifest: dict[str, Any],
    explicit_url: str | None,
) -> str:
    """Replace the single README news slot without growing a second changelog."""
    replacement = (
        f"{NEWS_START}\n"
        f"{release_news(markdown_language, manifest, explicit_url)}\n"
        f"{NEWS_END}"
    )
    return replace_one(
        text,
        rf"{re.escape(NEWS_START)}[\s\S]*?{re.escape(NEWS_END)}",
        replacement,
        path,
    )


def summary(markdown_language: str, manifest: dict[str, Any]) -> str:
    fallback = manifest["tag"]
    return manifest.get("release_notes", {}).get("summary", {}).get(markdown_language, fallback)


def inline_summary(markdown_language: str, manifest: dict[str, Any]) -> str:
    return summary(markdown_language, manifest).rstrip().rstrip(".!?")


def update_readme_en(path: Path, manifest: dict[str, Any], explicit_url: str | None) -> None:
    tag = manifest["tag"]
    pdf_count = manifest["pdfs"]["total"]
    scope_count = manifest["scope_count"]
    mega_scopes = ", ".join(manifest["scope_groups"]["mega"])
    sv_count = len(manifest["scope_groups"]["scarlet_violet"])
    language_separator = " |\n"
    text = path.read_text(encoding="utf-8")

    text = replace_one(text, r"!\[v[^\]]+\]\(https://img\.shields\.io/badge/version-v[^)]+-green\.svg\)", f"![{tag}](https://img.shields.io/badge/version-{tag}-green.svg)", path)
    text = replace_one(text, r"  - \*\*\d+ (?:Modern|Scarlet & Violet) Sets:\*\* Full Scarlet & Violet era \(SV01-SV10 \+ specials\)", f"  - **{sv_count} Scarlet & Violet Sets:** Full Scarlet & Violet era (SV01-SV10 + specials)", path)
    text = replace_one(text, r"  - \*\*(?:Paldea|Mega Evolution) Era:\*\* .+", f"  - **Mega Evolution Era:** {mega_scopes}", path)
    text = replace_one(text, r"- \*\*Scope-Based System\*\* with \d+ total scopes", f"- **Scope-Based System** with {scope_count} total scopes", path)
    text = replace_one(
        text,
        r"\*\*Latest \(v[^)]+\):\*\* \[All \d+ PDFs\]\([^)]+\) ✨ \*New: [^*]+\*",
        f"**Latest ({tag}):** [All {pdf_count} PDFs]({release_url(manifest, explicit_url)}) ✨ *New: {inline_summary('en', manifest)}!*",
        path,
    )
    text = replace_one(
        text,
        r"\*\*By Language \(v[^)]+\):\*\*\n(?:.+\n){8}.+",
        f"**By Language ({tag}):**\n{language_links(tag, LANGUAGE_LINKS_EN, language_separator, release_url(manifest, explicit_url))}",
        path,
    )
    text = replace_release_news(text, path, "en", manifest, explicit_url)
    text = replace_one(
        text,
        r"# List available scopes \(\d+ total: 1 Pokedex \+ 3 ExGen \+ \d+ TCG sets\)",
        f"# List available scopes ({scope_count} total: 1 Pokedex + 3 ExGen + {scope_count - 4} TCG sets)",
        path,
    )

    path.write_text(text, encoding="utf-8")


def update_readme_de(path: Path, manifest: dict[str, Any], explicit_url: str | None) -> None:
    tag = manifest["tag"]
    pdf_count = manifest["pdfs"]["total"]
    scope_count = manifest["scope_count"]
    mega_scopes = ", ".join(manifest["scope_groups"]["mega"])
    sv_count = len(manifest["scope_groups"]["scarlet_violet"])
    text = path.read_text(encoding="utf-8")

    text = replace_one(text, r"!\[v[^\]]+\]\(https://img\.shields\.io/badge/Version-v[^)]+-green\.svg\)", f"![{tag}](https://img.shields.io/badge/Version-{tag}-green.svg)", path)
    text = replace_one(text, r"  - \*\*\d+ (?:Moderne Sets|Karmesin-&-Purpur-Sets):\*\* Komplette Karmesin & Purpur-Ära \(SV01-SV10 \+ Spezial-Sets\)", f"  - **{sv_count} Karmesin-&-Purpur-Sets:** Komplette Karmesin & Purpur-Ära (SV01-SV10 + Spezial-Sets)", path)
    text = replace_one(text, r"  - \*\*(?:Paldea-Ära|Mega-Evolution-Ära):\*\* .+", f"  - **Mega-Evolution-Ära:** {mega_scopes}", path)
    text = replace_one(text, r"- \*\*Scope-basiertes System\*\* mit \d+ Scopes insgesamt", f"- **Scope-basiertes System** mit {scope_count} Scopes insgesamt", path)
    text = replace_one(
        text,
        r"\*\*Aktuelle Version \(v[^)]+\):\*\* \[Alle \d+ PDFs\]\([^)]+\) ✨ \*Neu: [^*]+\*",
        f"**Aktuelle Version ({tag}):** [Alle {pdf_count} PDFs]({release_url(manifest, explicit_url)}) ✨ *Neu: {inline_summary('de', manifest)}!*",
        path,
    )
    text = replace_one(
        text,
        r"\*\*Nach Sprache \(v[^)]+\):\*\* .+",
        f"**Nach Sprache ({tag}):** {language_links(tag, LANGUAGE_LINKS_DE, ' | ', release_url(manifest, explicit_url))}",
        path,
    )
    text = replace_release_news(text, path, "de", manifest, explicit_url)
    text = replace_one(
        text,
        r"# Verfügbare Scopes anzeigen \(\d+ gesamt: 1 Pokedex \+ 3 ExGen \+ \d+ TCG Sets\)",
        f"# Verfügbare Scopes anzeigen ({scope_count} gesamt: 1 Pokedex + 3 ExGen + {scope_count - 4} TCG Sets)",
        path,
    )

    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--release-url", default=None)
    parser.add_argument("--project-dir", default=".")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    manifest = read_manifest(Path(args.manifest))
    update_readme_en(project_dir / "README.md", manifest, args.release_url)
    update_readme_de(project_dir / "README.de.md", manifest, args.release_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
