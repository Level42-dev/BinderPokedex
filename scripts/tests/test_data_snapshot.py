import json
from pathlib import Path

import pytest
import yaml

from scripts.data.audit_data_refresh import compare_scope, validate_scope
from scripts.data.build_snapshot_manifest import build_manifest
from scripts.release.verify_data_snapshot import verify_manifest


REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_scope_validation_rejects_incomplete_unknown_card():
    scope = {
        "type": "tcg_set",
        "set_id": "SV07",
        "available_languages": ["de", "en"],
        "sections": {
            "all": {
                "cards": [{
                    "id": "sv07-139",
                    "printed_number": "139",
                    "available_languages": ["de", "en"],
                    "name": {"de": "Amura", "en": "Lacey"},
                    "type": "unknown",
                }]
            }
        },
    }

    assert validate_scope(scope) == [
        "unknown card classification sv07-139"
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


def _load_output_scope(scope: str) -> dict:
    return json.loads(
        (REPO_ROOT / "data" / "output" / f"{scope}.json").read_text(
            encoding="utf-8"
        )
    )


def _cards_for_language(scope: dict, language: str) -> list[dict]:
    return [
        card
        for section in scope["sections"].values()
        for card in section["cards"]
        if language in card.get("available_languages", [])
    ]


def test_german_svp_snapshot_has_number_gaps_and_unnumbered_terapagos():
    cards = _cards_for_language(_load_output_scope("SVP"), "de")
    numbered = [card for card in cards if card.get("printed_number") is not None]
    unnumbered = [card for card in cards if card.get("printed_number") is None]
    missing_numbers = {"085", "102", "190", "191", "192", "213", "214", "215"}

    assert len(cards) == 217
    assert {card["printed_number"] for card in numbered} == (
        {f"{number:03d}" for number in range(1, 225)} - missing_numbers
    )
    assert unnumbered == [
        next(card for card in cards if card["id"] == "svp-500")
    ]
    assert unnumbered[0]["localId"] == "500"
    assert unnumbered[0]["name"]["de"] == "Terapagos & Freunde"


def test_german_mep_snapshot_preserves_original_promo_numbers():
    cards = _cards_for_language(_load_output_scope("MEP"), "de")
    cards_by_number = {card["printed_number"]: card for card in cards}

    assert len(cards) == 88
    assert set(cards_by_number) == {f"{number:03d}" for number in range(1, 89)}
    assert cards_by_number["064"]["name"]["de"] == "Serpiroyal"
    assert cards_by_number["079"]["name"]["de"] == "Glutexo"


def test_trainer_owned_name_stays_in_tcg_set_but_not_pokedex():
    sv09_cards = _cards_for_language(_load_output_scope("SV09"), "de")
    zoroark_card = next(card for card in sv09_cards if card["id"] == "sv09-189")
    pokedex_cards = [
        card
        for section in _load_output_scope("Pokedex")["sections"].values()
        for card in section["cards"]
    ]
    zoroark_pokedex = next(card for card in pokedex_cards if card["pokemon_id"] == 571)

    assert zoroark_card["name"]["de"] == "Ns Zoroark"
    assert zoroark_card["suffix"] == "[EX_NEW]"
    assert zoroark_pokedex["name"]["de"] == "Zoroark"


@pytest.mark.parametrize("scope_name", ("ME02.5", "ME03", "ME04", "ME05"))
def test_mega_scopes_do_not_retain_obsolete_missing_dex_id_workaround(scope_name):
    source = json.loads(
        (REPO_ROOT / "data" / "source" / f"{scope_name.lower()}.json").read_text(
            encoding="utf-8"
        )
    )
    missing_dex_ids = [
        card["id"]
        for card in source["cards"]
        if card.get("category") == "Pokemon" and not card.get("dexId")
    ]
    config = yaml.safe_load(
        (REPO_ROOT / "config" / "scopes" / f"{scope_name}.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert missing_dex_ids == []
    assert "fix_missing_dex_ids" not in {
        item["step"] for item in config["pipeline"]
    }
