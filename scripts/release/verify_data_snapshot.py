#!/usr/bin/env python3
"""Verify that release data exactly matches its reviewed snapshot manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.data.build_snapshot_manifest import sha256_file, snapshot_files
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.data.build_snapshot_manifest import sha256_file, snapshot_files


def verify_manifest(root: Path, manifest: dict[str, Any]) -> list[str]:
    """Return deterministic validation errors for one data manifest."""
    root = root.resolve()
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        return ["unsupported snapshot schema"]
    entries = manifest.get("files")
    if not isinstance(entries, list):
        return ["snapshot files must be a list"]

    expected: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("invalid snapshot file entry")
            continue
        relative = entry.get("path")
        digest = entry.get("sha256")
        if (
            not isinstance(relative, str)
            or not isinstance(digest, str)
            or len(digest) != 64
        ):
            errors.append("invalid snapshot file entry")
            continue
        candidate = (root / relative).resolve()
        if (
            relative in expected
            or not candidate.is_relative_to(root)
            or not relative.endswith(".json")
            or not relative.startswith(("data/source/", "data/output/"))
        ):
            errors.append(f"invalid snapshot path: {relative}")
            continue
        expected[relative] = digest

    actual = {
        path.relative_to(root).as_posix(): path
        for path in snapshot_files(root)
    }
    for relative in sorted(set(expected) - set(actual)):
        errors.append(f"missing file: {relative}")
    for relative in sorted(set(actual) - set(expected)):
        errors.append(f"unexpected file: {relative}")
    for relative in sorted(set(expected) & set(actual)):
        if sha256_file(actual[relative]) != expected[relative]:
            errors.append(f"hash mismatch: {relative}")

    if manifest.get("file_count") != len(entries):
        errors.append("snapshot file_count mismatch")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="data/snapshot.json")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    manifest_path = (root / args.manifest).resolve()
    if not manifest_path.is_relative_to(root) or not manifest_path.is_file():
        print(f"ERROR: snapshot manifest not found: {manifest_path}")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = verify_manifest(root, manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(
        f"Verified {manifest['file_count']} data files at boundary "
        f"{manifest['boundary']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
