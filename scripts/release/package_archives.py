#!/usr/bin/env python3
"""Package current PDF releases with offline licenses and build provenance."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

try:
    from .build_manifest import LANGUAGES
except ImportError:
    from build_manifest import LANGUAGES

PROJECT_URL = "https://github.com/Level42-dev/BinderPokedex"
NOTICE_FILES = (
    "NOTICE.md", "LICENSE", "LICENSE-CODE", "LICENSE-CONTENT.md",
    "LICENSES/CC-BY-NC-4.0.txt",
)


def package_archives(project_dir: Path, tag: str, source_ref: str) -> list[Path]:
    """Build every language ZIP only after validating all required inputs."""
    project_dir = project_dir.resolve()
    if not tag.strip() or not re.fullmatch(r"[0-9a-fA-F]{40}", source_ref):
        raise ValueError("A release tag and full source commit SHA are required")
    for name in NOTICE_FILES:
        path = project_dir / name
        if not path.is_file() or not path.read_bytes().strip():
            raise ValueError(f"Missing or empty notice: {name}")
    pdfs_by_language = {}
    for language in LANGUAGES:
        pdfs = sorted((project_dir / "output" / language).glob("*.pdf"))
        if not pdfs or any(path.stat().st_size == 0 for path in pdfs):
            raise ValueError(f"Missing or empty PDFs for language: {language}")
        pdfs_by_language[language] = pdfs

    source = json.dumps({
        "repository": PROJECT_URL, "tag": tag, "commit": source_ref,
        "source_url": f"{PROJECT_URL}/tree/{source_ref}",
        "notice": "Licenses are scoped; see NOTICE.md and LICENSE-CONTENT.md.",
    }, indent=2) + "\n"
    archives = []
    for language, info in LANGUAGES.items():
        destination = project_dir / info["zip"]
        temporary = destination.with_name(f".{destination.name}.tmp")
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in pdfs_by_language[language]:
                    archive.write(path, f"{language}/{path.name}")
                for name in NOTICE_FILES:
                    archive.write(project_dir / name, f"{language}/{name}")
                archive.writestr(f"{language}/SOURCE.json", source)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        archives.append(destination)
    return archives


def verify_archive_notices(archive: zipfile.ZipFile, language: str, tag: str) -> None:
    """Reject candidates whose download packages lost notices or identity."""
    for name in (*NOTICE_FILES, "SOURCE.json"):
        member = f"{language}/{name}"
        if member not in archive.namelist() or not archive.read(member).strip():
            raise ValueError(f"Missing release notice: {member}")
    source = json.loads(archive.read(f"{language}/SOURCE.json"))
    if (
        source.get("repository") != PROJECT_URL
        or source.get("tag") != tag
        or not re.fullmatch(r"[0-9a-fA-F]{40}", str(source.get("commit", "")))
    ):
        raise ValueError(f"Invalid release source identity: {language}/SOURCE.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-ref", required=True)
    args = parser.parse_args()
    for path in package_archives(args.project_dir, args.tag, args.source_ref):
        print(path.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
