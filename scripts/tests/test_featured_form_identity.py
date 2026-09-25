import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts.fetcher.steps.enrich_featured_cards import (
    EnrichFeaturedElementsStep,
)
from scripts.fetcher.steps.base import PipelineContext
from scripts.fetcher.steps import pokemon_utils
from scripts.poster_assets.poster_subject import (
    PosterSubject,
    poster_display_name_from_card,
    resolve_poster_subject,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _card(
    pokemon_id: int,
    artwork_id: int,
    name: str,
    card_id: str,
    prefix: str | None = "Mega",
) -> dict:
    return {
        "pokemon_id": pokemon_id,
        "name": {"en": name},
        "prefix": prefix,
        "image_url": PosterSubject(pokemon_id, artwork_id).image_url,
        "tcg_card": {"id": card_id},
    }


def test_featured_enrichment_preserves_cover_and_exact_form_subject(
    monkeypatch,
    tmp_path: Path,
):
    step = EnrichFeaturedElementsStep("featured")

    def fake_cover(pokemon_id, card, _cache_dir, _set_info):
        return {
            "pokemon_id": pokemon_id,
            "pokemon_name": card["name"]["en"],
            "card_id": card["tcg_card"]["id"],
            "image_url": (
                f"https://assets.tcgdex.net/en/test/{card['tcg_card']['id']}"
                "/high.png"
            ),
        }

    monkeypatch.setattr(step, "_fetch_card_image_from_any_card", fake_cover)
    elements = step._identify_and_fetch_featured_elements(
        [
            _card(380, 10062, "Latias", "me01-100"),
            _card(6, 10034, "Charizard X", "me02-013"),
            _card(6, 10035, "Charizard Y", "me02-022"),
        ],
        3,
        tmp_path,
    )

    assert [item["pokemon_name"] for item in elements] == [
        "Mega Latias",
        "Mega Charizard X",
        "Mega Charizard Y",
    ]
    assert all(
        item["image_url"].startswith("https://assets.tcgdex.net/")
        for item in elements
    )
    assert [
        resolve_poster_subject(item).official_artwork_id
        for item in elements
    ] == [10062, 10034, 10035]


def test_internal_mega_marker_becomes_prompt_friendly_exact_form_name():
    assert poster_display_name_from_card(
        {
            "prefix": "[M]",
            "variant_form": "x",
        },
        "[M] Mewtwo",
    ) == "Mega Mewtwo X"
    assert poster_display_name_from_card(
        {
            "prefix": "[M]",
        },
        "Rayquaza",
    ) == "Mega Rayquaza"


def test_configured_featured_cards_are_authoritative_and_keep_exact_order(
    monkeypatch,
    tmp_path: Path,
):
    step = EnrichFeaturedElementsStep("featured")
    cards = [
        _card(1008, 1008, "Miraidon", "set-073", prefix=None),
        _card(25, 25, "Pikachu", "set-057", prefix=None),
        _card(1007, 1007, "Koraidon", "set-121", prefix=None),
    ]
    context = PipelineContext({})
    context.set_data(
        {
            "sections": {
                "normal": {
                    "cards": cards,
                    "featured_elements": [{"card_id": "stale-card"}],
                }
            }
        }
    )

    def fake_cover(pokemon_id, card, _cache_dir, _set_info):
        return {
            "pokemon_id": pokemon_id,
            "pokemon_name": card["name"]["en"],
            "card_id": card["tcg_card"]["id"],
            "image_url": "https://assets.tcgdex.net/en/test/high.png",
        }

    monkeypatch.setattr(step, "_fetch_card_image_from_any_card", fake_cover)
    result = step.execute(
        context,
        {
            "max_cards": 3,
            "cache_dir": str(tmp_path),
            "section_featured_card_ids": {
                "normal": ["set-121", "set-057", "set-073"],
            },
        },
    )
    featured = result.get_data()["sections"]["normal"]["featured_elements"]

    assert [item["card_id"] for item in featured] == [
        "set-121",
        "set-057",
        "set-073",
    ]
    assert [item["pokemon_name"] for item in featured] == [
        "Koraidon",
        "Pikachu",
        "Miraidon",
    ]
    assert [
        resolve_poster_subject(item).official_artwork_id
        for item in featured
    ] == [1007, 25, 1008]


@pytest.mark.parametrize(
    ("configured_card_ids", "message"),
    [
        (["set-121", "set-121"], "duplicate card IDs"),
        (["missing-card"], "missing configured featured card IDs"),
    ],
)
def test_configured_featured_cards_reject_invalid_card_ids(
    monkeypatch,
    tmp_path: Path,
    configured_card_ids: list[str],
    message: str,
):
    step = EnrichFeaturedElementsStep("featured")
    context = PipelineContext({})
    context.set_data(
        {
            "sections": {
                "normal": {
                    "cards": [
                        _card(
                            1007,
                            1007,
                            "Koraidon",
                            "set-121",
                            prefix=None,
                        )
                    ],
                }
            }
        }
    )
    monkeypatch.setattr(
        step,
        "_fetch_card_image_from_any_card",
        lambda *_args: pytest.fail("invalid config must fail before fetching"),
    )

    with pytest.raises(ValueError, match=message):
        step.execute(
            context,
            {
                "max_cards": 3,
                "cache_dir": str(tmp_path),
                "section_featured_card_ids": {
                    "normal": configured_card_ids,
                },
            },
        )


def test_exgen3_scope_pins_curated_featured_card_ids():
    config = yaml.safe_load(
        (REPO_ROOT / "config" / "scopes" / "ExGen3.yaml").read_text(
            encoding="utf-8"
        )
    )
    featured_step = next(
        step
        for step in config["pipeline"]
        if step["step"] == "enrich_featured_elements"
    )

    assert featured_step["params"]["section_featured_card_ids"] == {
        "normal": ["sv01-125", "me02.5-057", "sv01-081"],
        "mega": ["me01-100", "me02.5-267", "me02.5-113"],
    }


def test_exgen2_scope_pins_its_curated_mega_cast():
    config = yaml.safe_load(
        (REPO_ROOT / "config" / "scopes" / "ExGen2.yaml").read_text(
            encoding="utf-8"
        )
    )
    featured_step = next(
        step
        for step in config["pipeline"]
        if step["step"] == "enrich_featured_elements"
    )

    assert featured_step["params"]["section_featured_card_ids"] == {
        "mega": ["xy8-63", "xy7-98", "xy6-59"],
    }


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        (
            "SV04.5",
            {"all": ["sv04.5-007", "sv04.5-018", "sv04.5-016"]},
        ),
        (
            "ExGen1",
            {"normal": ["ex6-112", "ex6-104", "ex10-105"]},
        ),
        (
            "MEP",
            {"all": ["mep-015", "mep-037", "mep-038"]},
        ),
    ],
)
def test_curated_poster_casts_pin_card_safe_scope_cards(scope, expected):
    config = yaml.safe_load(
        (REPO_ROOT / "config" / "scopes" / f"{scope}.yaml").read_text(
            encoding="utf-8"
        )
    )
    featured_step = next(
        step
        for step in config["pipeline"]
        if step["step"] == "enrich_featured_elements"
    )

    assert featured_step["params"]["section_featured_card_ids"] == expected


def test_featured_enrichment_rejects_artwork_species_mismatch(
    tmp_path: Path,
):
    step = EnrichFeaturedElementsStep("featured")
    with pytest.raises(ValueError, match="belongs to Pokemon #6"):
        step._identify_and_fetch_featured_elements(
            [
                {
                    "pokemon_id": 1,
                    "name": {"en": "Wrong Bulbasaur"},
                    "prefix": "Mega",
                    "image_url": PosterSubject(6, 10034).image_url,
                    "tcg_card": {"id": "a"},
                }
            ],
            1,
            tmp_path,
        )


def test_mega_artwork_resolution_never_falls_back_to_base(monkeypatch):
    monkeypatch.setattr(
        pokemon_utils.requests,
        "get",
        lambda *_args, **_kwargs: SimpleNamespace(status_code=404),
    )

    with pytest.raises(RuntimeError, match="did not resolve"):
        pokemon_utils.get_mega_artwork_url(
            pokemon_name="Latias",
            base_id=380,
        )


@pytest.mark.parametrize(
    ('pokemon_name', 'form_suffix', 'expected_slug', 'artwork_id'),
    [
        ('Charizard X', 'X', 'charizard-mega-x', 10034),
        ('Charizard Y', 'Y', 'charizard-mega-y', 10035),
    ],
)
def test_mega_artwork_does_not_duplicate_explicit_xy_suffix(
    monkeypatch,
    pokemon_name,
    form_suffix,
    expected_slug,
    artwork_id,
):
    requested_urls = []

    def fake_get(url, **_kwargs):
        requested_urls.append(url)
        return SimpleNamespace(
            status_code=200,
            json=lambda: {'id': artwork_id},
        )

    monkeypatch.setattr(pokemon_utils.requests, 'get', fake_get)

    result = pokemon_utils.get_mega_artwork_url(
        pokemon_name=pokemon_name,
        base_id=6,
        form_suffix=form_suffix,
    )

    assert requested_urls == [
        f'https://pokeapi.co/api/v2/pokemon/{expected_slug}'
    ]
    assert result == PosterSubject(6, artwork_id).image_url


def _checked_in_subjects(scope: str, section_id: str):
    payload = json.loads(
        (REPO_ROOT / "data" / "output" / f"{scope}.json").read_text(
            encoding="utf-8"
        )
    )
    payload["sections"] = {
        section_id: payload["sections"][section_id],
    }
    from scripts.poster_assets.fetch_cutouts import scope_featured_elements

    return [
        (
            subject.species_id,
            subject.official_artwork_id,
        )
        for subject in (
            resolve_poster_subject(item)
            for item in scope_featured_elements(payload)
        )
    ]


def test_checked_in_variant_scopes_resolve_their_exact_form_artwork():
    assert _checked_in_subjects("ExGen3", "mega") == [
        (380, 10062),
        (719, 10075),
        (448, 10059),
    ]
    assert _checked_in_subjects("ExGen2", "mega") == [
        (150, 10043),
        (384, 10079),
        (381, 10063),
    ]
    assert _checked_in_subjects("ExGen2", "primal") == [
        (382, 10077),
        (383, 10078),
    ]
    assert _checked_in_subjects("ME03", "all") == [
        (495, 495),
        (722, 722),
        (718, 10301),
    ]
    assert _checked_in_subjects("MEP", "all") == [
        (888, 888),
        (1, 1),
        (4, 4),
    ]


def test_checked_in_exgen2_featured_names_are_prompt_friendly():
    payload = json.loads(
        (REPO_ROOT / "data" / "output" / "ExGen2.json").read_text(
            encoding="utf-8"
        )
    )

    assert [
        item["pokemon_name"]
        for item in payload["sections"]["mega"]["featured_elements"]
    ] == ["Mega Mewtwo X", "Mega Rayquaza", "Mega Latios"]
