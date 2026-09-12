import json
from pathlib import Path

from scripts.data.audit_data_refresh import compare_scope, validate_scope
from scripts.data.build_snapshot_manifest import build_manifest
from scripts.release.verify_data_snapshot import verify_manifest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_snapshot_detects_changed_file_hash(tmp_path):
    data_file = tmp_path / "data" / "output" / "SV01.json"
    _write_json(data_file, {"set_id": "SV01"})
    manifest = build_manifest(
        tmp_path,
        "2026-09-12T00:00:00Z",
        "2026-09-12",
    )

    data_file.write_text("{}\n", encoding="utf-8")

    assert verify_manifest(tmp_path, manifest) == [
        "hash mismatch: data/output/SV01.json"
    ]


def test_snapshot_manifest_is_sorted_and_covers_source_and_output(tmp_path):
    _write_json(tmp_path / "data" / "source" / "z.json", {"z": 1})
    _write_json(tmp_path / "data" / "output" / "A.json", {"a": 1})

    manifest = build_manifest(
        tmp_path,
        "2026-09-12T00:00:00Z",
        "2026-09-12",
    )

    assert manifest["schema_version"] == 1
    assert manifest["boundary"] == "2026-09-12"
    assert manifest["fetched_at"] == "2026-09-12T00:00:00Z"
    assert [item["path"] for item in manifest["files"]] == [
        "data/output/A.json",
        "data/source/z.json",
    ]
    assert verify_manifest(tmp_path, manifest) == []


def test_compare_scope_reports_localized_field_change_by_card_identity():
    before = {
        "sections": {
            "all": {
                "cards": [{
                    "id": "sv09-189",
                    "localId": "189",
                    "name": {"de": "Zoroark", "en": "Zoroark"},
                }]
            }
        }
    }
    after = {
        "sections": {
            "all": {
                "cards": [{
                    "id": "sv09-189",
                    "localId": "189",
                    "name": {"de": "Ns Zoroark", "en": "N's Zoroark"},
                }]
            }
        }
    }

    result = compare_scope(before, after)

    assert result["before_count"] == 1
    assert result["after_count"] == 1
    assert result["added"] == []
    assert result["removed"] == []
    assert result["changed"] == [{
        "id": "sv09-189",
        "fields": {
            "name.de": {"before": "Zoroark", "after": "Ns Zoroark"},
            "name.en": {"before": "Zoroark", "after": "N's Zoroark"},
        },
    }]


def test_scope_validation_rejects_duplicate_printed_number_per_language():
    scope = {
        "type": "tcg_set",
        "set_id": "SVP",
        "available_languages": ["de", "en"],
        "sections": {
            "all": {
                "cards": [
                    {
                        "id": "svp-001",
                        "printed_number": "001",
                        "available_languages": ["de", "en"],
                        "name": {"de": "A", "en": "A"},
                    },
                    {
                        "id": "svp-other-001",
                        "printed_number": "001",
                        "available_languages": ["de"],
                        "name": {"de": "B"},
                    },
                ]
            }
        },
    }

    assert validate_scope(scope) == [
        "duplicate printed number de/001: svp-001, svp-other-001"
    ]


def test_scope_validation_rejects_name_outside_observed_languages():
    scope = {
        "type": "tcg_set",
        "set_id": "SVP",
        "available_languages": ["de", "en"],
        "sections": {
            "all": {
                "cards": [{
                    "id": "svp-190",
                    "printed_number": "190",
                    "available_languages": ["en"],
                    "name": {"de": "Pikachu", "en": "Pikachu"},
                }]
            }
        },
    }

    assert validate_scope(scope) == [
        "name language not observed svp-190: de"
    ]


def test_scope_validation_does_not_apply_tcg_number_rules_to_pokedex():
    scope = {
        "type": "pokedex",
        "sections": {
            "one": {"cards": [{"id": 25, "name": {"de": "Pikachu"}}]},
            "two": {"cards": [{"id": 25, "name": {"de": "Pikachu"}}]},
        },
    }

    assert validate_scope(scope) == []
