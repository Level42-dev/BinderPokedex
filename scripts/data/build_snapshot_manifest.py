#!/usr/bin/env python3
"""Build a deterministic manifest for the checked-in data snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


DATA_DIRECTORIES = (Path("data/source"), Path("data/output"))


def snapshot_files(root: Path) -> list[Path]:
    """Return every JSON data input in canonical repository order."""
    root = root.resolve()
    files = {
        path.resolve()
        for relative_dir in DATA_DIRECTORIES
        for path in (root / relative_dir).rglob("*.json")
        if path.is_file()
    }
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_timestamp(value: str) -> None:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("fetched_at must include a timezone")


def build_manifest(root: Path, fetched_at: str, boundary: str) -> dict[str, Any]:
    """Build a stable SHA-256 manifest for source and output JSON files."""
    root = root.resolve()
    date.fromisoformat(boundary)
    _validate_timestamp(fetched_at)
    files = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
        for path in snapshot_files(root)
    ]
    if not files:
        raise ValueError("data snapshot contains no JSON files")
    return {
        "schema_version": 1,
        "boundary": boundary,
        "fetched_at": fetched_at,
        "file_count": len(files),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boundary", required=True)
    parser.add_argument("--output", default="data/snapshot.json")
    parser.add_argument("--fetched-at")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    fetched_at = args.fetched_at or datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")
    manifest = build_manifest(root, fetched_at, args.boundary)
    output = (root / args.output).resolve()
    if not output.is_relative_to(root):
        raise ValueError(f"snapshot output escapes repository: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {manifest['file_count']} data hashes to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
