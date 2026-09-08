#!/usr/bin/env python3
"""Verify that a release candidate contains every expected PDF archive."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

try:
    from .build_manifest import LANGUAGES
    from .package_archives import verify_archive_notices
except ImportError:
    from build_manifest import LANGUAGES
    from package_archives import verify_archive_notices


def _load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported release manifest schema: {path}")
    if not str(payload.get("tag", "")).strip():
        raise ValueError(f"Release manifest has no version label: {path}")
    return payload


def _verify_scope_data(payload: dict[str, Any]) -> None:
    scopes = payload.get("scopes")
    if not isinstance(scopes, list) or not scopes:
        raise ValueError("Release manifest contains no scopes")
    if payload.get("scope_count") != len(scopes):
        raise ValueError("Release manifest scope count does not match its scope list")

    card_counts = payload.get("card_counts")
    if not isinstance(card_counts, dict) or set(card_counts) != set(scopes):
        raise ValueError("Release manifest does not contain card counts for every scope")


def _asset_records(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = payload.get("assets")
    if not isinstance(records, list):
        raise ValueError("Release manifest assets must be a list")
    by_language = {
        str(record.get("language")): record
        for record in records
        if isinstance(record, dict)
    }
    if set(by_language) != set(LANGUAGES):
        raise ValueError("Release manifest does not contain every language archive")
    return by_language


def _verify_release_notes(payload: dict[str, Any], release_notes_path: Path) -> None:
    text = release_notes_path.read_text(encoding="utf-8")
    tag = str(payload["tag"])
    if not text.strip() or f"# Binder Pokédex {tag}" not in text:
        raise ValueError("Release notes are empty or do not match the release tag")
    notes = payload.get("release_notes", {}).get("whats_new", {})
    for language in ("en", "de"):
        title = notes.get(language, {}).get("title")
        if not title or title not in text:
            raise ValueError(f"Release notes do not contain the {language} title")
    for info in LANGUAGES.values():
        if str(info["zip"]) not in text:
            raise ValueError("Release notes do not link every language archive")


def verify(
    manifest_path: Path, release_notes_path: Path | None = None
) -> dict[str, int]:
    """Validate manifest counts, local PDFs, and all language ZIP archives."""
    manifest_path = manifest_path.resolve()
    project_dir = manifest_path.parent
    payload = _load_manifest(manifest_path)
    _verify_scope_data(payload)

    pdfs = payload.get("pdfs")
    if not isinstance(pdfs, dict) or int(pdfs.get("total", 0)) <= 0:
        raise ValueError("Release manifest contains no PDFs")
    by_language = pdfs.get("by_language")
    if not isinstance(by_language, dict) or set(by_language) != set(LANGUAGES):
        raise ValueError("Release manifest PDF counts do not cover every language")
    if sum(int(count) for count in by_language.values()) != int(pdfs["total"]):
        raise ValueError("Release manifest total PDF count is inconsistent")

    records = _asset_records(payload)
    verified_counts: dict[str, int] = {}
    for language, info in LANGUAGES.items():
        expected_count = int(by_language[language])
        if expected_count <= 0:
            raise ValueError(f"Release candidate has no {language} PDFs")

        output_pdfs = sorted((project_dir / "output" / language).glob("*.pdf"))
        if len(output_pdfs) != expected_count:
            raise ValueError(
                f"Output PDF count for {language} is {len(output_pdfs)}, "
                f"expected {expected_count}"
            )

        record = records[language]
        expected_name = str(info["zip"])
        if record.get("name") != expected_name:
            raise ValueError(f"Unexpected {language} archive name in manifest")
        archive_path = project_dir / expected_name
        if (
            record.get("exists") is not True
            or int(record.get("size_bytes", 0)) <= 0
            or not archive_path.is_file()
            or archive_path.stat().st_size != int(record["size_bytes"])
        ):
            raise ValueError(f"Missing or invalid release archive: {archive_path}")

        with zipfile.ZipFile(archive_path) as archive:
            if archive.testzip() is not None:
                raise ValueError(f"Corrupt release archive: {archive_path}")
            verify_archive_notices(archive, language, str(payload["tag"]))
            pdf_members = [
                name
                for name in archive.namelist()
                if name.startswith(f"{language}/") and name.endswith(".pdf")
            ]
        if len(pdf_members) != expected_count:
            raise ValueError(
                f"Archive {archive_path} contains {len(pdf_members)} PDFs, "
                f"expected {expected_count}"
            )
        verified_counts[language] = expected_count

    if release_notes_path is not None:
        _verify_release_notes(payload, release_notes_path.resolve())
    return verified_counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="release-manifest.json")
    parser.add_argument("--release-notes", default=None)
    args = parser.parse_args()

    notes_path = Path(args.release_notes) if args.release_notes else None
    counts = verify(Path(args.manifest), notes_path)
    print(
        f"Verified {sum(counts.values())} PDFs across "
        f"{len(counts)} release archives."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
