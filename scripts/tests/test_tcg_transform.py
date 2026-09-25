"""
Tests for TCG Set Transform Module

Tests the transformation of TCG cards to target format, including:
- Variant suffix/prefix determination
- Name dict building
- Pokemon vs Trainer card handling
"""

import json
import subprocess
import sys
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'fetcher'))

from steps.transform_tcg_set import TransformTCGSetStep
from steps import transform_tcg_set as transform_tcg_set_module
from steps.base import PipelineContext
from steps.enrich_names_from_pokedex import EnrichNamesFromPokedexStep
from steps.transform_ex_gen3 import TransformScarletVioletEXStep
from scripts.poster_assets.poster_subject import (
    PosterSubject,
    official_artwork_id_for_card_name,
    poster_subject_from_card,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_transform_step_imports_without_prior_repository_path_bootstrap(tmp_path):
    """The fetcher step must not depend on earlier imports adding repo root."""
    fetcher_dir = REPO_ROOT / "scripts" / "fetcher"
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(fetcher_dir)!r})\n"
        f"sys.path = [path for path in sys.path if path != {str(REPO_ROOT)!r}]\n"
        "import steps.transform_tcg_set\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


class TestVariantSuffixPrefixDetection:
    """Test variant suffix and prefix detection from card names."""
    
    def setup_method(self):
        """Setup test instance."""
        self.step = TransformTCGSetStep("test_suffix_prefix")
    
    def test_modern_ex_detection(self):
        """Test detection of modern lowercase ex (Scarlet & Violet era)."""
        card = {'name': 'Mega Venusaur ex'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix == '[EX_NEW]'
        assert prefix == 'Mega'
    
    def test_ex_only(self):
        """Test detection of ex suffix without prefix."""
        card = {'name': 'Charizard ex'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix == '[EX_NEW]'
        assert prefix is None
    
    def test_gx_detection(self):
        """Test detection of GX suffix."""
        card = {'name': 'Pikachu GX'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix == 'GX'
        assert prefix is None
    
    def test_vmax_detection(self):
        """Test detection of VMAX suffix."""
        card = {'name': 'Charizard VMAX'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix == 'VMAX'
        assert prefix is None
    
    def test_vstar_detection(self):
        """Test detection of VSTAR suffix."""
        card = {'name': 'Arceus VSTAR'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix == 'VSTAR'
        assert prefix is None
    
    def test_v_detection(self):
        """Test detection of V suffix."""
        card = {'name': 'Lucario V'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix == 'V'
        assert prefix is None
    
    def test_mega_only(self):
        """Test detection of Mega prefix only."""
        card = {'name': 'Mega Charizard'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix is None
        assert prefix == 'Mega'
    
    def test_radiant_prefix(self):
        """Test detection of Radiant prefix."""
        card = {'name': 'Radiant Charizard'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix is None
        assert prefix == 'Radiant'
    
    def test_shining_prefix(self):
        """Test detection of Shining prefix."""
        card = {'name': 'Shining Mew'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix is None
        assert prefix == 'Shining'
    
    def test_base_card(self):
        """Test base card without variants."""
        card = {'name': 'Pikachu'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix is None
        assert prefix is None
    
    def test_hyphenated_ex(self):
        """Test hyphenated ex suffix."""
        card = {'name': 'Venusaur-ex'}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix == '[EX_NEW]'
        assert prefix is None
    
    def test_case_insensitive(self):
        """Test case-insensitive detection."""
        card = {'name': 'Mega CHARIZARD ex'}  # Mixed case
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix == '[EX_NEW]'
        assert prefix == 'Mega'
    
    def test_no_name_field(self):
        """Test card with missing name field."""
        card = {}
        suffix, prefix = self.step._determine_variant_suffix_and_prefix(card)
        
        assert suffix is None
        assert prefix is None


class TestCardTransformation:
    """Test full card transformation logic."""
    
    def setup_method(self):
        """Setup test instance."""
        self.step = TransformTCGSetStep("test_transformation")
    
    def test_transform_base_pokemon_card(self):
        """Test transformation of base Pokemon card."""
        cards = [{
            'localId': '001',
            'name': 'Bulbasaur',
            'card_type': 'pokemon',
            'pokemon_id': 1,
            'types': ['Grass'],
            'image': 'https://example.com/image.png',
            'name_de': 'Bisasam',
            'name_en': 'Bulbasaur',
            'name_fr': 'Bulbizarre'
        }]
        
        result = self.step._transform_cards(cards)
        
        assert len(result) == 1
        card = result[0]
        
        assert card['localId'] == '001'
        assert card['type'] == 'pokemon'
        assert card['pokemon_id'] == 1
        assert card['types'] == ['Grass']
        assert isinstance(card['name'], dict)
        assert card['name']['de'] == 'Bisasam'
        assert card['name']['en'] == 'Bulbasaur'
        assert card['name']['fr'] == 'Bulbizarre'
        assert 'suffix' not in card  # No suffix for base card
        assert 'prefix' not in card

    @pytest.mark.parametrize(
        ('pokemon_id', 'name', 'artwork_id'),
        [
            (901, 'Bloodmoon Ursaluna', 10272),
            (646, 'Black Kyurem ex', 10022),
            (1017, 'Hearthflame Mask Ogerpon ex', 10274),
        ],
    )
    def test_transform_uses_exact_named_form_artwork(
        self,
        pokemon_id,
        name,
        artwork_id,
    ):
        cards = [{
            'localId': '001',
            'name': name,
            'card_type': 'pokemon',
            'pokemon_id': pokemon_id,
            'types': ['Colorless'],
            'name_en': name,
        }]

        [card] = self.step._transform_cards(cards)

        assert card['image_url'] == PosterSubject(
            pokemon_id,
            artwork_id,
        ).image_url
        assert poster_subject_from_card(card)['official_artwork_id'] == artwork_id
    
    def test_transform_variant_pokemon_card(self, monkeypatch):
        """Test transformation of variant Pokemon card."""
        monkeypatch.setattr(
            transform_tcg_set_module,
            "get_mega_artwork_url",
            lambda **_kwargs: (
                "https://raw.githubusercontent.com/PokeAPI/sprites/master/"
                "sprites/pokemon/other/official-artwork/10033.png"
            ),
        )
        cards = [{
            'localId': '003',
            'name': 'Mega Venusaur ex',  # Original TCGdex name
            'card_type': 'pokemon',
            'pokemon_id': 3,
            'types': ['Grass'],
            'image': 'https://example.com/image.png',
            'name_de': 'Bisaflor',  # Base name from Pokedex
            'name_en': 'Venusaur',
            'name_fr': 'Florizarre'
        }]
        
        result = self.step._transform_cards(cards)
        
        assert len(result) == 1
        card = result[0]
        
        assert card['type'] == 'pokemon'
        assert card['pokemon_id'] == 3
        # Base names only
        assert card['name']['de'] == 'Bisaflor'
        assert card['name']['en'] == 'Venusaur'
        # Variants as separate fields
        assert card['suffix'] == '[EX_NEW]'
        assert card['prefix'] == 'Mega'

    def test_transform_retains_trainer_owner_while_extracting_ex_suffix(self):
        cards = [{
            'id': 'sv09-189',
            'localId': '189',
            'name': "N's Zoroark ex",
            'card_type': 'pokemon',
            'pokemon_id': 571,
            'types': ['Darkness'],
            'name_de': 'Ns Zoroark-ex',
            'name_en': "N's Zoroark ex",
            'available_languages': ['de', 'en'],
        }]

        [card] = self.step._transform_cards(cards)

        assert card['name']['de'] == 'Ns Zoroark'
        assert card['name']['en'] == "N's Zoroark"
        assert card['suffix'] == '[EX_NEW]'

    def test_transform_corrected_mega_absol_never_requests_castform_mega(
        self,
        monkeypatch,
    ):
        """Regression for TCGdex's incorrect ME01 #086 Castform dexId."""
        artwork_calls = []

        def fake_mega_artwork_url(**kwargs):
            artwork_calls.append(kwargs)
            return (
                "https://raw.githubusercontent.com/PokeAPI/sprites/master/"
                "sprites/pokemon/other/official-artwork/10057.png"
            )

        monkeypatch.setattr(
            transform_tcg_set_module,
            "get_mega_artwork_url",
            fake_mega_artwork_url,
        )
        cards = [{
            'localId': '086',
            'name': 'Mega Absol ex',
            'card_type': 'pokemon',
            'pokemon_id': 359,
            'types': ['Darkness'],
            'name_de': 'Absol',
            'name_en': 'Absol',
            'name_fr': 'Absol',
        }]

        [card] = self.step._transform_cards(cards)

        assert card['pokemon_id'] == 359
        assert card['name']['en'] == 'Absol'
        assert card['prefix'] == 'Mega'
        assert card['suffix'] == '[EX_NEW]'
        assert artwork_calls == [{
            'pokemon_name': 'Absol',
            'base_id': 359,
            'original_card_name': 'Mega Absol ex',
        }]
    
    def test_transform_trainer_card(self):
        """Test transformation of trainer card."""
        cards = [{
            'localId': '113',
            'name': "Acerola's Mischief",
            'card_type': 'trainer',
            'types': [],
            'image': 'https://example.com/image.png',
            'name_de': "Acerola's Mischief",
            'name_en': "Acerola's Mischief"
        }]
        
        result = self.step._transform_cards(cards)
        
        assert len(result) == 1
        card = result[0]
        
        assert card['type'] == 'trainer'
        assert card['types'] == []
        assert card['image_url'] is None
        assert isinstance(card['name'], dict)
        assert card['name']['de'] == "Acerola's Mischief"

    def test_transform_preserves_identity_languages_and_blank_number(self):
        cards = [{
            'id': 'svp-500',
            'localId': '500',
            'printed_number': None,
            'available_languages': ['de', 'en'],
            'name': 'Terapagos & Friends',
            'card_type': 'pokemon',
            'pokemon_id': 1024,
            'types': ['Colorless'],
            'name_de': 'Terapagos & Freunde',
            'name_en': 'Terapagos & Friends',
        }]

        [card] = self.step._transform_cards(cards)

        assert card['id'] == 'svp-500'
        assert card['localId'] == '500'
        assert card['printed_number'] is None
        assert card['available_languages'] == ['de', 'en']
    
    def test_transform_multiple_cards(self):
        """Test transformation of multiple cards."""
        cards = [
            {
                'localId': '001',
                'name': 'Bulbasaur',
                'card_type': 'pokemon',
                'pokemon_id': 1,
                'types': ['Grass'],
                'image': 'https://example.com/1.png',
                'name_de': 'Bisasam',
                'name_en': 'Bulbasaur'
            },
            {
                'localId': '002',
                'name': 'Pikachu ex',
                'card_type': 'pokemon',
                'pokemon_id': 25,
                'types': ['Electric'],
                'image': 'https://example.com/2.png',
                'name_de': 'Pikachu',
                'name_en': 'Pikachu'
            },
            {
                'localId': '003',
                'name': 'Professor Oak',
                'card_type': 'trainer',
                'types': [],
                'image': 'https://example.com/3.png',
                'name_de': 'Professor Oak',
                'name_en': 'Professor Oak'
            }
        ]
        
        result = self.step._transform_cards(cards)
        
        assert len(result) == 3
        assert result[0]['type'] == 'pokemon'
        assert result[1]['type'] == 'pokemon'
        assert result[1]['suffix'] == '[EX_NEW]'
        assert result[2]['type'] == 'trainer'
    
    def test_transform_all_variant_types(self, monkeypatch):
        """Test transformation of all variant types."""
        monkeypatch.setattr(
            transform_tcg_set_module,
            "get_mega_artwork_url",
            lambda **_kwargs: (
                "https://raw.githubusercontent.com/PokeAPI/sprites/master/"
                "sprites/pokemon/other/official-artwork/10034.png"
            ),
        )
        variant_cards = [
            {'name': 'Pikachu ex', 'expected_suffix': '[EX_NEW]'},
            {'name': 'Charizard GX', 'expected_suffix': 'GX'},
            {'name': 'Lucario V', 'expected_suffix': 'V'},
            {'name': 'Charizard VMAX', 'expected_suffix': 'VMAX'},
            {'name': 'Arceus VSTAR', 'expected_suffix': 'VSTAR'},
            {'name': 'Mega Charizard', 'expected_prefix': 'Mega'},
            {'name': 'Radiant Greninja', 'expected_prefix': 'Radiant'},
            {'name': 'Shining Mew', 'expected_prefix': 'Shining'}
        ]
        
        for variant in variant_cards:
            cards = [{
                'localId': '001',
                'name': variant['name'],
                'card_type': 'pokemon',
                'pokemon_id': 1,
                'types': ['Fire'],
                'image': 'https://example.com/image.png',
                'name_en': 'Test'
            }]
            
            result = self.step._transform_cards(cards)
            card = result[0]
            
            if 'expected_suffix' in variant:
                assert card.get('suffix') == variant['expected_suffix'], \
                    f"Expected suffix {variant['expected_suffix']} for {variant['name']}"
            
            if 'expected_prefix' in variant:
                assert card.get('prefix') == variant['expected_prefix'], \
                    f"Expected prefix {variant['expected_prefix']} for {variant['name']}"


def test_exgen3_corrects_inconsistent_tcgdex_dex_id_from_card_name(
    monkeypatch,
):
    step = TransformScarletVioletEXStep("test_exgen3_identity")
    monkeypatch.setattr(
        step,
        "_load_pokedex_lookup",
        lambda: {"absol": 359},
    )
    source = {
        "id": "me01-086",
        "name": "Mega Absol ex",
        "dexId": [351],
    }

    normalized = step._normalize_card_dex_ids([source])

    assert source["dexId"] == [351]
    assert normalized[0]["dexId"] == [359]


@pytest.mark.parametrize(
    ("species_id", "card_name", "artwork_id"),
    [
        (103, "Alolan Exeggutor ex", 10114),
        (646, "Black Kyurem ex", 10022),
        (901, "Bloodmoon Ursaluna ex", 10272),
        (6, "Charizard X", 10034),
        (6, "Charizard Y", 10035),
        (150, "Mewtwo X", 10043),
        (150, "Mewtwo Y", 10044),
        (1017, "Teal Mask Ogerpon ex", 1017),
        (1017, "Wellspring Mask Ogerpon ex", 10273),
        (1017, "Hearthflame Mask Ogerpon ex", 10274),
        (1017, "Cornerstone Mask Ogerpon ex", 10275),
    ],
)
def test_exgen3_resolves_named_forms_from_pinned_registry(
    species_id,
    card_name,
    artwork_id,
):
    assert official_artwork_id_for_card_name(
        species_id,
        card_name,
    ) == artwork_id


def test_exgen3_named_form_cannot_fall_back_to_base_artwork():
    with pytest.raises(ValueError, match="requires official artwork #10114"):
        poster_subject_from_card(
            {
                "pokemon_id": 103,
                "name": {"en": "Alolan Exeggutor"},
                "image_url": PosterSubject(103, 103).image_url,
            }
        )


def test_exgen3_named_base_id_form_rejects_another_registered_form():
    with pytest.raises(ValueError, match="requires official artwork #1017"):
        poster_subject_from_card(
            {
                "pokemon_id": 1017,
                "name": {"en": "Teal Mask Ogerpon"},
                "image_url": PosterSubject(1017, 10273).image_url,
            }
        )


def test_named_mega_xy_form_rejects_the_sibling_artwork():
    with pytest.raises(ValueError, match="requires official artwork #10034"):
        poster_subject_from_card(
            {
                "pokemon_id": 6,
                "name": {"en": "Charizard X"},
                "prefix": "Mega",
                "image_url": PosterSubject(6, 10035).image_url,
            }
        )


def test_exgen3_named_forms_keep_distinct_localized_labels(tmp_path):
    languages = {
        "de": "Ogerpon",
        "en": "Ogerpon",
        "fr": "Ogerpon",
        "es": "Ogerpon",
        "it": "Ogerpon",
        "ja": "オーガポン",
        "ko": "오거폰",
        "zh_hans": "厄诡椪",
        "zh_hant": "厄鬼椪",
    }
    pokedex_file = tmp_path / "Pokedex.json"
    pokedex_file.write_text(
        json.dumps(
            {
                "sections": {
                    "gen9": {
                        "cards": [
                            {"pokemon_id": 1017, "name": languages}
                        ]
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    context = PipelineContext({})
    context.set_data(
        {
            "sections": {
                "normal": {
                    "cards": [
                        {
                            "pokemon_id": 1017,
                            "name": {"en": form_name},
                        }
                        for form_name in (
                            "Teal Mask Ogerpon",
                            "Wellspring Mask Ogerpon",
                            "Hearthflame Mask Ogerpon",
                            "Cornerstone Mask Ogerpon",
                        )
                    ]
                }
            }
        }
    )

    result = EnrichNamesFromPokedexStep("form_names").execute(
        context,
        {
            "pokedex_file": str(pokedex_file),
            "form_names_file": str(
                REPO_ROOT / "enrichments" / "card_form_names.json"
            ),
        },
    )
    names = [
        card["name"]
        for card in result.get_data()["sections"]["normal"]["cards"]
    ]

    for language in languages:
        assert len({name[language] for name in names}) == 4
    assert names[0]["de"] == "Türkisgrüne-Maske-Ogerpon"
    assert names[3]["ja"] == "オーガポン（いしずえのめん）"


def test_exgen3_prefers_actual_sv01_base_set_identifier():
    step = TransformScarletVioletEXStep("test_exgen3_sv01_priority")
    sv03 = {
        "id": "sv03-001",
        "set": {"id": "sv03", "name": "A Earlier Alphabetically"},
    }
    sv01 = {
        "id": "sv01-001",
        "set": {"id": "sv01", "name": "Z Scarlet & Violet"},
    }

    selected = step._select_best_cards({(25, 25): [sv03, sv01]})

    assert selected == [sv01]


def test_exgen3_card_selection_is_stable_within_the_same_set():
    step = TransformScarletVioletEXStep("test_exgen3_stable_card_order")
    later = {
        "id": "me01-163",
        "localId": "163",
        "set": {"id": "me01", "name": "Mega Evolution"},
    }
    desired = {
        "id": "me01-100",
        "localId": "100",
        "set": {"id": "me01", "name": "Mega Evolution"},
    }

    selected = step._select_best_cards(
        {(380, ""): [later, desired]}
    )

    assert selected == [desired]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
