import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "fetcher"))

from lib.tcg_card_overrides import (  # noqa: E402
    apply_tcg_card_overrides,
    load_tcg_card_overrides,
)


OVERRIDES_PATH = ROOT / "enrichments" / "tcg_card_overrides.json"


def test_reviewed_energy_names_are_loaded_verbatim():
    overrides = load_tcg_card_overrides(OVERRIDES_PATH)

    assert overrides["sets"]["sv01"]["cards"]["257"]["names"]["de"] == (
        "Basis-Elektro-Energie"
    )
    assert overrides["sets"]["sv01"]["cards"]["258"]["names"]["de"] == (
        "Basis-Kampf-Energie"
    )
    assert overrides["sets"]["sv02"]["cards"]["278"]["names"]["de"] == (
        "Basis-Pflanzen-Energie"
    )
    assert overrides["sets"]["sv02"]["cards"]["279"]["names"]["de"] == (
        "Basis-Wasser-Energie"
    )
    assert overrides["sets"]["sv03"]["cards"]["230"]["names"]["de"] == (
        "Basis-Feuer-Energie"
    )
    assert overrides["sets"]["sv06.5"]["cards"]["098"]["names"]["de"] == (
        "Basis-Finsternis-Energie"
    )
    assert overrides["sets"]["sv06.5"]["cards"]["099"]["names"]["de"] == (
        "Basis-Metall-Energie"
    )


def test_terapagos_override_keeps_identity_but_removes_printed_number():
    data = {
        "set_info": {"id": "svp"},
        "cards": [
            {
                "id": "svp-500",
                "localId": "500",
                "name": "Terapagos & Friends",
                "name_en": "Terapagos & Friends",
                "available_languages": ["en"],
                "printed_number": "500",
            }
        ],
    }

    result = apply_tcg_card_overrides(
        data,
        load_tcg_card_overrides(OVERRIDES_PATH),
    )

    [card] = result["cards"]
    assert card["id"] == "svp-500"
    assert card["localId"] == "500"
    assert card["printed_number"] is None
    assert card["name_de"] == "Terapagos & Freunde"
    assert card["name_en"] == "Terapagos & Friends"
    assert card["available_languages"] == ["de", "en"]
    assert result["metadata"]["tcg_card_overrides_version"] == 1


def test_override_rejects_card_missing_from_the_source_set():
    data = {
        "set_info": {"id": "svp"},
        "cards": [],
    }
    overrides = {
        "version": 1,
        "sets": {"svp": {"cards": {"500": {"printed_number": None}}}},
    }

    with pytest.raises(ValueError, match="svp card 500"):
        apply_tcg_card_overrides(data, overrides)


def test_override_application_does_not_mutate_source_data():
    data = {
        "set_info": {"id": "sv01"},
        "cards": [
            {
                "id": "sv01-257",
                "localId": "257",
                "name_de": "Basis-Lightning-Energie",
                "available_languages": ["de", "en"],
                "printed_number": "257",
            }
        ],
    }
    original = json.loads(json.dumps(data))

    overrides = {
        "version": 1,
        "sets": {
            "sv01": {
                "cards": {
                    "257": {
                        "names": {"de": "Basis-Elektro-Energie"},
                    }
                }
            }
        },
    }

    apply_tcg_card_overrides(data, overrides)

    assert data == original
