"""Shared language selection for card pages and their panorama overlays."""

import copy


def filter_variant_data_for_language(variant_data, language):
    """Return render data containing only cards observed in ``language``.

    Older non-TCG data has no per-card availability marker and remains
    unchanged.  The source object is never mutated when filtering is needed.
    """
    sections = variant_data.get("sections")
    if not isinstance(sections, dict):
        return variant_data

    has_language_scoped_cards = any(
        isinstance(card.get("available_languages"), list)
        for section in sections.values()
        if isinstance(section, dict)
        for card in section.get("cards", [])
        if isinstance(card, dict)
    )
    if not has_language_scoped_cards:
        return variant_data

    filtered = copy.deepcopy(variant_data)
    for section in filtered["sections"].values():
        if not isinstance(section, dict):
            continue
        cards = section.get("cards")
        if not isinstance(cards, list):
            continue
        section["cards"] = [
            card
            for card in cards
            if not isinstance(card, dict)
            or not isinstance(card.get("available_languages"), list)
            or language in card["available_languages"]
        ]

    return filtered
