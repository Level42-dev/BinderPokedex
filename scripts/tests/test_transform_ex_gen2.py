"""Focused regressions for exact EX Generation 2 Mega form identity."""

import json
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent / 'fetcher'))

from steps import transform_ex_gen2 as transform_ex_gen2_module
from steps.base import PipelineContext
from steps.transform_ex_gen2 import TransformBlackWhiteEXStep


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_primal_german_names_follow_official_proto_card_naming(monkeypatch):
    step = TransformBlackWhiteEXStep('test_exgen2_proto')
    monkeypatch.setattr(step, '_get_pokeapi_artwork_url', lambda *args: 'https://example.test/10077.png')
    cards = step._transform_card_list([
        {"id": "xy7-96", "name": "Primal Kyogre EX", "dexId": [382],
         "types": ["Water"], "set": {"id": "xy7"}},
    ], "primal")
    assert cards[0]["localized_prefix"] == {"de": "Proto-"}


def _mega_card(
    card_id: str,
    dex_id: int,
    pokemon_name: str,
    attack_name: str,
    set_id: str,
    set_name: str,
) -> dict:
    return {
        'id': card_id,
        'localId': card_id.rsplit('-', 1)[-1],
        'name': f'M {pokemon_name} EX',
        'dexId': [dex_id],
        'types': ['Psychic' if dex_id == 150 else 'Fire'],
        'attacks': [{'name': attack_name}],
        'set': {'id': set_id, 'name': set_name},
    }


@pytest.mark.parametrize(
    ('dex_id', 'attack_name', 'expected_suffix'),
    [
        (6, 'Crimson Dive', 'Y'),
        (6, 'Wild Blaze', 'X'),
        (150, 'Vanishing Strike', 'X'),
        (150, 'Psychic Infinity', 'Y'),
    ],
)
def test_unnamed_xy_mega_form_is_resolved_from_card_attack(
    dex_id,
    attack_name,
    expected_suffix,
):
    step = TransformBlackWhiteEXStep('test_exgen2_form')
    card = _mega_card(
        'xy-test-1',
        dex_id,
        'Charizard' if dex_id == 6 else 'Mewtwo',
        attack_name,
        'xy-test',
        'Test Set',
    )

    assert step._resolve_mega_form_suffix(card) == expected_suffix


def test_real_exgen2_xy_mega_siblings_remain_distinct(monkeypatch):
    artwork_ids = {
        (6, 'X'): 10034,
        (6, 'Y'): 10035,
        (150, 'X'): 10043,
        (150, 'Y'): 10044,
    }

    def fake_mega_artwork_url(**kwargs):
        artwork_id = artwork_ids.get(
            (kwargs['base_id'], kwargs['form_suffix'])
        )
        if artwork_id is None:
            artwork_id = 99999
        return (
            "https://raw.githubusercontent.com/PokeAPI/sprites/master/"
            f"sprites/pokemon/other/official-artwork/{artwork_id}.png"
        )

    monkeypatch.setattr(
        transform_ex_gen2_module,
        'get_mega_artwork_url',
        fake_mega_artwork_url,
    )
    context = PipelineContext({})
    source_cards = json.loads(
        (REPO_ROOT / 'data/source/tcg_bw_ex.json').read_text(
            encoding='utf-8'
        )
    )['cards']
    context.data['tcg_bw_xy_ex_cards'] = [
        card
        for card in source_cards
        if (
            'M ' in card.get('name', '')
            or 'Mega' in card.get('name', '')
            or card.get('name', '').startswith('M-')
        )
    ]

    result = TransformBlackWhiteEXStep('test_exgen2').execute(
        context,
        {},
    )
    cards = result.data['sections']['mega']['cards']
    siblings = {
        (card['pokemon_id'], card.get('variant_form')): card
        for card in cards
        if card['pokemon_id'] in {6, 150}
    }

    assert len(cards) == 29
    assert set(siblings) == {
        (6, 'x'),
        (6, 'y'),
        (150, 'x'),
        (150, 'y'),
    }
    assert {
        key: (
            card['tcg_card']['id'],
            card['form_code'],
            int(card['image_url'].rsplit('/', 1)[-1].removesuffix('.png')),
        )
        for key, card in siblings.items()
    } == {
        (6, 'x'): ('xy2-69', '#006_EX2_MEG_X', 10034),
        (6, 'y'): ('xy12-13', '#006_EX2_MEG_Y', 10035),
        (150, 'x'): ('xy8-63', '#150_EX2_MEG_X', 10043),
        (150, 'y'): ('xy8-64', '#150_EX2_MEG_Y', 10044),
    }


def test_unnamed_xy_mega_without_form_evidence_is_rejected():
    step = TransformBlackWhiteEXStep('test_exgen2_form')
    card = _mega_card(
        'xy-test-1',
        6,
        'Charizard',
        'Unknown Attack',
        'xy-test',
        'Test Set',
    )

    with pytest.raises(ValueError, match='Could not determine the exact X/Y'):
        step._resolve_mega_form_suffix(card)


def test_named_xy_mega_conflicting_with_attack_is_rejected():
    step = TransformBlackWhiteEXStep('test_exgen2_form')
    card = _mega_card(
        'xy-test-1',
        6,
        'Charizard',
        'Crimson Dive',
        'xy-test',
        'Test Set',
    )
    card['name'] = 'M Charizard X EX'

    with pytest.raises(ValueError, match='conflicts with'):
        step._resolve_mega_form_suffix(card)
