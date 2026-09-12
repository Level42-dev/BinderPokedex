#!/usr/bin/env python3
"""Compare refreshed data with a Git baseline and report unsafe drift."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _cards(scope: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not scope:
        return []
    result = []
    top_level = scope.get("cards")
    if isinstance(top_level, list):
        result.extend(card for card in top_level if isinstance(card, dict))
    for section in scope.get("sections", {}).values():
        if isinstance(section, dict):
            result.extend(
                card
                for card in section.get("cards", [])
                if isinstance(card, dict)
            )
    return result


def _match_key(card: dict[str, Any], index: int) -> str:
    # localId is the stable bridge to v9 snapshots that predate retained API IDs.
    for field in ("localId", "id", "pokemon_id", "num"):
        value = card.get(field)
        if value is not None and value != "":
            return f"{field}:{value}"
    return f"position:{index}"


def _display_id(card: dict[str, Any], fallback: str) -> str:
    for field in ("id", "localId", "pokemon_id", "num"):
        value = card.get(field)
        if value is not None and value != "":
            return str(value)
    return fallback


def _field_changes(before: Any, after: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(before, dict) and isinstance(after, dict):
        changes = {}
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before:
                changes[path] = {"before": None, "after": after[key]}
            elif key not in after:
                changes[path] = {"before": before[key], "after": None}
            else:
                changes.update(_field_changes(before[key], after[key], path))
        return changes
    if before != after:
        return {prefix: {"before": before, "after": after}}
    return {}


def _metadata(scope: dict[str, Any] | None) -> dict[str, Any]:
    if not scope:
        return {}
    metadata = {}
    for key, value in scope.items():
        if key == "cards":
            continue
        if key == "sections" and isinstance(value, dict):
            metadata[key] = {
                section_id: {
                    field: field_value
                    for field, field_value in section.items()
                    if field != "cards"
                }
                for section_id, section in value.items()
                if isinstance(section, dict)
            }
        else:
            metadata[key] = value
    return metadata


def compare_scope(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return stable card and metadata changes for one scope file."""
    before_cards = _cards(before)
    after_cards = _cards(after)
    before_map = {
        _match_key(card, index): card
        for index, card in enumerate(before_cards)
    }
    after_map = {
        _match_key(card, index): card
        for index, card in enumerate(after_cards)
    }

    added = [
        _display_id(after_map[key], key)
        for key in sorted(set(after_map) - set(before_map))
    ]
    removed = [
        _display_id(before_map[key], key)
        for key in sorted(set(before_map) - set(after_map))
    ]
    changed = []
    for key in sorted(set(before_map) & set(after_map)):
        fields = _field_changes(before_map[key], after_map[key])
        if fields:
            changed.append({
                "id": _display_id(after_map[key], key),
                "fields": fields,
            })

    return {
        "before_count": len(before_cards),
        "after_count": len(after_cards),
        "added": added,
        "removed": removed,
        "changed": changed,
        "metadata_changes": _field_changes(_metadata(before), _metadata(after)),
    }


def _card_languages(card: dict[str, Any], scope: dict[str, Any]) -> list[str]:
    languages = card.get("available_languages")
    if isinstance(languages, list):
        return [str(language) for language in languages]
    scope_languages = scope.get("available_languages")
    return (
        [str(language) for language in scope_languages]
        if isinstance(scope_languages, list)
        else []
    )


def validate_scope(scope: dict[str, Any]) -> list[str]:
    """Return blockers for duplicate identity/number and foreign names."""
    if scope.get("type") != "tcg_set":
        return []
    blockers = []
    cards = _cards(scope)
    identities: dict[str, list[str]] = {}
    numbers: dict[tuple[str, str], list[str]] = {}
    for index, card in enumerate(cards):
        identity = _display_id(card, f"position:{index}")
        stable_id = card.get("id")
        if stable_id:
            identities.setdefault(str(stable_id), []).append(identity)

        languages = _card_languages(card, scope)
        names = card.get("name")
        if isinstance(names, dict) and languages:
            for language in sorted(set(names) - set(languages)):
                blockers.append(
                    f"name language not observed {identity}: {language}"
                )

        printed_number = card.get("printed_number", card.get("localId"))
        if printed_number is None or printed_number == "":
            continue
        for language in languages or ["und"]:
            numbers.setdefault(
                (language, str(printed_number)), []
            ).append(identity)

    for stable_id, occurrences in sorted(identities.items()):
        if len(occurrences) > 1:
            blockers.append(
                f"duplicate card identity {stable_id}: "
                + ", ".join(occurrences)
            )
    for (language, number), identities_for_number in sorted(numbers.items()):
        if len(identities_for_number) > 1:
            blockers.append(
                f"duplicate printed number {language}/{number}: "
                + ", ".join(identities_for_number)
            )
    return sorted(blockers)


def _git_paths(root: Path, baseline_ref: str) -> set[str]:
    result = subprocess.run(
        [
            "git", "ls-tree", "-r", "--name-only", baseline_ref,
            "--", "data/source", "data/output",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        line
        for line in result.stdout.splitlines()
        if line.endswith(".json")
    }


def _git_json(root: Path, baseline_ref: str, relative: str) -> dict[str, Any] | None:
    result = subprocess.run(
        ["git", "show", f"{baseline_ref}:{relative}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def _working_paths(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for relative_dir in (Path("data/source"), Path("data/output"))
        for path in (root / relative_dir).rglob("*.json")
        if path.is_file()
    }


def audit_refresh(root: Path, baseline_ref: str) -> dict[str, Any]:
    """Audit every current or baseline data JSON file."""
    root = root.resolve()
    paths = sorted(_git_paths(root, baseline_ref) | _working_paths(root))
    comparisons = {}
    blockers = []
    for relative in paths:
        before = _git_json(root, baseline_ref, relative)
        working_path = root / relative
        after = (
            json.loads(working_path.read_text(encoding="utf-8"))
            if working_path.is_file()
            else None
        )
        comparison = compare_scope(before, after)
        if any(
            (
                comparison["added"],
                comparison["removed"],
                comparison["changed"],
                comparison["metadata_changes"],
            )
        ):
            comparisons[relative] = comparison
        if relative.startswith("data/output/") and after is not None:
            blockers.extend(
                f"{relative}: {blocker}"
                for blocker in validate_scope(after)
            )

    return {
        "schema_version": 1,
        "baseline_ref": baseline_ref,
        "generated_at": datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z"),
        "files_checked": len(paths),
        "files_changed": len(comparisons),
        "blockers": sorted(blockers),
        "comparisons": comparisons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default="HEAD")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    report = audit_refresh(root, args.baseline_ref)
    output = (root / args.output).resolve()
    if not output.is_relative_to(root):
        raise ValueError(f"audit output escapes repository: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"Audited {report['files_checked']} files; "
        f"{report['files_changed']} changed; "
        f"{len(report['blockers'])} blocker(s)."
    )
    return 1 if report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
