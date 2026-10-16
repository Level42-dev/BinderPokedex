"""The 30-year anniversary release keeps both printed collections intact."""

import json
from pathlib import Path

from scripts.release.build_manifest import count_cards, discover_scopes


ROOT = Path(__file__).resolve().parents[2]


def _cards(scope: str) -> list[dict]:
    payload = json.loads((ROOT / "data" / "output" / f"{scope}.json").read_text())
    return [card for section in payload["sections"].values() for card in section["cards"]]


def test_anniversary_main_and_classic_collections_ship_as_distinct_scopes():
    scopes = discover_scopes(ROOT)

    assert "30C" in scopes
    assert "30CClassic" in scopes
    assert count_cards(ROOT, scopes)["30C"] == 161
    assert count_cards(ROOT, scopes)["30CClassic"] == 30


def test_anniversary_cards_keep_their_original_printed_numbers():
    main = _cards("30C")
    classic = _cards("30CClassic")

    assert {card["id"] for card in main} == {
        *(f"30th-{number:03d}" for number in range(1, 159)),
        "30th-B",
        "30th-G",
        "30th-R",
    }
    assert {card["printed_number"] for card in main} == {
        *(f"{number:03d}" for number in range(1, 159)),
        "B",
        "G",
        "R",
    }
    assert {card["id"] for card in classic} == {
        f"30th-c-{number:03d}" for number in range(1, 31)
    }
    assert {card["printed_number"] for card in classic} == {
        f"{number:03d}" for number in range(1, 31)
    }
    assert all("de" in card["available_languages"] for card in main + classic)


def test_anniversary_scopes_only_advertise_observed_language_editions():
    expected = {"de", "en", "fr", "es", "it"}
    for scope in ("30C", "30CClassic"):
        payload = json.loads((ROOT / "data" / "output" / f"{scope}.json").read_text())
        assert set(payload["available_languages"]) == expected
        assert all(set(card["available_languages"]) <= expected for card in _cards(scope))
