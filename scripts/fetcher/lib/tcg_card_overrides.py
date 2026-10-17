"""Versioned, reviewed corrections for TCG card metadata.

The upstream card identifier remains untouched. Overrides may only add or
replace localized names, declare reviewed language availability, and describe
the number printed on the physical card (including no printed number).
"""

import copy
import json
from pathlib import Path


LANGUAGE_ORDER = (
    "de",
    "en",
    "fr",
    "es",
    "it",
    "ja",
    "ko",
    "zh_hans",
    "zh_hant",
)


def load_tcg_card_overrides(path: Path) -> dict:
    """Load the override document from *path*."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    version = document.get("version")
    sets = document.get("sets")
    if type(version) is not int or version < 1:
        raise ValueError("TCG card overrides require a positive integer version")
    if not isinstance(sets, dict):
        raise ValueError("TCG card overrides require a sets object")
    return document


def apply_tcg_card_overrides(data: dict, overrides: dict) -> dict:
    """Apply the overrides for one set without mutating source data."""
    result = copy.deepcopy(data)
    set_info = result.get("set_info", {})
    set_id = str(set_info.get("id") or result.get("id") or "").casefold()
    if not set_id:
        raise ValueError("TCG card data has no set identity")

    version = overrides.get("version")
    if type(version) is not int or version < 1:
        raise ValueError("TCG card overrides require a positive integer version")

    cards = result.get("cards")
    if not isinstance(cards, list):
        raise ValueError(f"{set_id} cards must be a list")
    cards_by_local_id = {
        str(card.get("localId")): card
        for card in cards
        if card.get("localId") is not None
    }

    set_overrides = overrides.get("sets", {}).get(set_id, {})
    for local_id, card_override in set_overrides.get("cards", {}).items():
        card = cards_by_local_id.get(str(local_id))
        if card is None:
            raise ValueError(f"{set_id} card {local_id} is missing from source data")

        names = card_override.get("names", {})
        if not isinstance(names, dict):
            raise ValueError(f"{set_id} card {local_id} names must be an object")
        for language, name in names.items():
            if language not in LANGUAGE_ORDER or not isinstance(name, str) or not name:
                raise ValueError(
                    f"{set_id} card {local_id} has invalid {language} name"
                )
            card[f"name_{language}"] = name

        if "available_languages" in card_override:
            declared = card_override["available_languages"]
            if (
                not isinstance(declared, list)
                or any(language not in LANGUAGE_ORDER for language in declared)
            ):
                raise ValueError(
                    f"{set_id} card {local_id} has invalid available_languages"
                )
            observed = set(card.get("available_languages", []))
            observed.update(declared)
            card["available_languages"] = [
                language for language in LANGUAGE_ORDER if language in observed
            ]
        elif names:
            observed = set(card.get("available_languages", []))
            observed.update(names)
            card["available_languages"] = [
                language for language in LANGUAGE_ORDER if language in observed
            ]

        if "printed_number" in card_override:
            printed_number = card_override["printed_number"]
            if printed_number is not None and not isinstance(printed_number, str):
                raise ValueError(
                    f"{set_id} card {local_id} printed_number must be text or null"
                )
            card["printed_number"] = printed_number

    result.setdefault("metadata", {})["tcg_card_overrides_version"] = version
    return result
