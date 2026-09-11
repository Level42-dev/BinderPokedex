"""
Tests for TCG Card Enrichment Module

Tests the enrichment of TCG cards with Pokedex data, including:
- dexId-based Pokemon mapping
- Variant marker extraction (Mega, ex, GX, V, etc.)
- Localized variant name building
- Trainer card handling
"""

import sys
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'fetcher'))

from steps.enrich_tcg_cards_from_pokedex import EnrichTCGCardsFromPokedexStep
from steps.enrich_tcg_names_multilingual import EnrichTCGNamesMultilingualStep


class TestVariantMarkerExtraction:
    """Test variant marker extraction from card names."""
    
    def setup_method(self):
        """Setup test instance."""
        self.step = EnrichTCGCardsFromPokedexStep("test_marker_extraction")
    
    def test_mega_ex_extraction(self):
        """Test extraction of Mega + ex markers."""
        markers = self.step._extract_variant_markers("Mega Venusaur ex")
        assert markers == {'prefix': 'Mega', 'suffix': 'ex'}
    
    def test_mega_only(self):
        """Test extraction of Mega prefix only."""
        markers = self.step._extract_variant_markers("Mega Charizard")
        assert markers == {'prefix': 'Mega', 'suffix': ''}
    
    def test_ex_only(self):
        """Test extraction of ex suffix only."""
        markers = self.step._extract_variant_markers("Pikachu ex")
        assert markers == {'prefix': '', 'suffix': 'ex'}
    
    def test_gx_suffix(self):
        """Test extraction of GX suffix."""
        markers = self.step._extract_variant_markers("Charizard GX")
        assert markers == {'prefix': '', 'suffix': 'GX'}
    
    def test_vmax_suffix(self):
        """Test extraction of VMAX suffix."""
        markers = self.step._extract_variant_markers("Pikachu VMAX")
        assert markers == {'prefix': '', 'suffix': 'VMAX'}
    
    def test_vstar_suffix(self):
        """Test extraction of VSTAR suffix."""
        markers = self.step._extract_variant_markers("Arceus VSTAR")
        assert markers == {'prefix': '', 'suffix': 'VSTAR'}
    
    def test_v_suffix(self):
        """Test extraction of V suffix."""
        markers = self.step._extract_variant_markers("Lucario V")
        assert markers == {'prefix': '', 'suffix': 'V'}
    
    def test_radiant_prefix(self):
        """Test extraction of Radiant prefix."""
        markers = self.step._extract_variant_markers("Radiant Charizard")
        assert markers == {'prefix': 'Radiant', 'suffix': ''}
    
    def test_shining_prefix(self):
        """Test extraction of Shining prefix."""
        markers = self.step._extract_variant_markers("Shining Mew")
        assert markers == {'prefix': 'Shining', 'suffix': ''}
    
    def test_no_variants(self):
        """Test card with no variants."""
        markers = self.step._extract_variant_markers("Pikachu")
        assert markers is None
    
    def test_hyphenated_ex(self):
        """Test hyphenated ex suffix."""
        markers = self.step._extract_variant_markers("Venusaur-ex")
        assert markers == {'prefix': '', 'suffix': 'ex'}
    
    def test_case_insensitive(self):
        """Test case-insensitive detection."""
        markers = self.step._extract_variant_markers("MEGA CHARIZARD EX")
        assert markers == {'prefix': 'Mega', 'suffix': 'ex'}


class TestVariantNameBuilding:
    """Test building localized variant names."""
    
    def setup_method(self):
        """Setup test instance."""
        self.step = EnrichTCGCardsFromPokedexStep("test_name_building")
    
    def test_german_mega_ex(self):
        """Test German Mega-ex name format."""
        result = self.step._build_variant_name(
            "Bisaflor", 
            {'prefix': 'Mega', 'suffix': 'ex'}, 
            'de'
        )
        assert result == "Mega-Bisaflor-ex"
    
    def test_english_mega_ex(self):
        """Test English Mega ex name format (spaces)."""
        result = self.step._build_variant_name(
            "Venusaur", 
            {'prefix': 'Mega', 'suffix': 'ex'}, 
            'en'
        )
        assert result == "Mega Venusaur ex"
    
    def test_french_ex(self):
        """Test French ex format (hyphen)."""
        result = self.step._build_variant_name(
            "Florizarre", 
            {'prefix': '', 'suffix': 'ex'}, 
            'fr'
        )
        assert result == "Florizarre-ex"
    
    def test_japanese_ex(self):
        """Test Japanese ex format (space)."""
        result = self.step._build_variant_name(
            "フシギバナ", 
            {'prefix': '', 'suffix': 'ex'}, 
            'ja'
        )
        assert result == "フシギバナ ex"
    
    def test_vmax_all_languages(self):
        """Test VMAX suffix works across languages."""
        for lang in ['de', 'en', 'fr', 'es', 'it', 'ja', 'ko']:
            result = self.step._build_variant_name(
                "Pikachu", 
                {'prefix': '', 'suffix': 'VMAX'}, 
                lang
            )
            separator = '-' if lang in ['de', 'fr', 'es', 'it'] else ' '
            assert result == f"Pikachu{separator}VMAX"
    
    def test_prefix_only(self):
        """Test prefix without suffix."""
        result = self.step._build_variant_name(
            "Bisaflor", 
            {'prefix': 'Mega', 'suffix': ''}, 
            'de'
        )
        assert result == "Mega-Bisaflor"
    
    def test_suffix_only(self):
        """Test suffix without prefix."""
        result = self.step._build_variant_name(
            "Pikachu", 
            {'prefix': '', 'suffix': 'GX'}, 
            'en'
        )
        assert result == "Pikachu GX"
    
    def test_no_variants(self):
        """Test base name without variants."""
        result = self.step._build_variant_name(
            "Pikachu", 
            {'prefix': '', 'suffix': ''}, 
            'en'
        )
        assert result == "Pikachu"


class TestCardEnrichment:
    """Test full card enrichment logic."""
    
    def setup_method(self):
        """Setup test instance with mock Pokedex data."""
        self.step = EnrichTCGCardsFromPokedexStep("test_card_enrichment")
        
        # Mock pokemon_by_id index
        self.pokemon_by_id = {
            1: {
                'pokemon_id': 1,
                'names': {
                    'de': 'Bisasam',
                    'en': 'Bulbasaur',
                    'fr': 'Bulbizarre',
                    'es': 'Bulbasaur',
                    'it': 'Bulbasaur',
                    'ja': 'フシギダネ',
                    'ko': '이상해씨',
                    'zh_hans': '妙蛙种子',
                    'zh_hant': '妙蛙種子'
                },
                'types': ['Grass']
            },
            3: {
                'pokemon_id': 3,
                'names': {
                    'de': 'Bisaflor',
                    'en': 'Venusaur',
                    'fr': 'Florizarre'
                },
                'types': ['Grass']
            },
            351: {
                'pokemon_id': 351,
                'names': {
                    'de': 'Formeo',
                    'en': 'Castform',
                    'fr': 'Morphéo'
                },
                'types': ['Normal']
            },
            359: {
                'pokemon_id': 359,
                'names': {
                    'de': 'Absol',
                    'en': 'Absol',
                    'fr': 'Absol'
                },
                'types': ['Darkness']
            },
            571: {
                'pokemon_id': 571,
                'names': {
                    'de': 'Zoroark',
                    'en': 'Zoroark',
                    'fr': 'Zoroark'
                },
                'types': ['Darkness']
            }
        }
    
    def test_enrich_base_pokemon_card(self):
        """Test enrichment of base Pokemon card."""
        card = {
            'id': 'sv01-001',
            'localId': '001',
            'name': 'Bulbasaur',
            'category': 'Pokemon',
            'dexId': [1],
            'types': ['Grass']
        }
        
        enriched = self.step._enrich_card(card, self.pokemon_by_id)
        
        assert enriched['pokemon_id'] == 1
        assert enriched['card_type'] == 'pokemon'
        assert enriched['name_de'] == 'Bisasam'
        assert enriched['name_en'] == 'Bulbasaur'
        assert enriched['name_ja'] == 'フシギダネ'
        assert enriched['types'] == ['Grass']
    
    def test_enrich_variant_pokemon_card(self):
        """Test enrichment of variant Pokemon card (base name only)."""
        card = {
            'id': 'me01-003',
            'localId': '003',
            'name': 'Mega Venusaur ex',
            'category': 'Pokemon',
            'dexId': [3],
            'types': ['Grass']
        }
        
        enriched = self.step._enrich_card(card, self.pokemon_by_id)
        
        assert enriched['pokemon_id'] == 3
        assert enriched['card_type'] == 'pokemon'
        # Should use base names only (variants handled by transform step)
        assert enriched['name_de'] == 'Bisaflor'
        assert enriched['name_en'] == 'Venusaur'
        assert enriched['name_fr'] == 'Florizarre'
        assert enriched['dexId'] == [3]

    def test_enrich_card_corrects_inconsistent_tcgdex_dexid_from_name(self):
        """The ME01 Absol card must not inherit Castform's identity."""
        card = {
            'id': 'me01-086',
            'localId': '086',
            'name': 'Mega Absol ex',
            'category': 'Pokemon',
            'dexId': [351],
            'types': ['Darkness']
        }

        enriched = self.step._enrich_card(card, self.pokemon_by_id)

        assert card['dexId'] == [351]
        assert enriched['dexId'] == [359]
        assert enriched['pokemon_id'] == 359
        assert enriched['name_en'] == 'Absol'
        assert enriched['name_de'] == 'Absol'

    def test_enrich_card_keeps_valid_dexid_when_name_is_not_canonical(self):
        card = {
            'id': 'promo-001',
            'name': 'Bulbasaur with Grey Felt Hat',
            'category': 'Pokemon',
            'dexId': [1],
            'types': ['Grass'],
        }

        enriched = self.step._enrich_card(card, self.pokemon_by_id)

        assert enriched['dexId'] == [1]
        assert enriched['pokemon_id'] == 1
        assert enriched['name_en'] == 'Bulbasaur'

    def test_enrich_card_preserves_observed_trainer_owned_names(self):
        """TCG card titles remain authoritative over canonical Pokédex names."""
        card = {
            'id': 'sv09-189',
            'localId': '189',
            'name': "N's Zoroark ex",
            'name_de': 'Ns Zoroark-ex',
            'name_en': "N's Zoroark ex",
            'available_languages': ['de', 'en'],
            'category': 'Pokemon',
            'dexId': [571],
            'types': ['Darkness'],
        }

        enriched = self.step._enrich_card(card, self.pokemon_by_id)

        assert enriched['pokemon_id'] == 571
        assert enriched['name_de'] == 'Ns Zoroark-ex'
        assert enriched['name_en'] == "N's Zoroark ex"
        assert 'name_fr' not in enriched
        assert self.pokemon_by_id[571]['names']['de'] == 'Zoroark'
    
    def test_enrich_trainer_card(self):
        """Test enrichment of trainer card."""
        card = {
            'id': 'me01-113',
            'localId': '113',
            'name': "Acerola's Mischief",
            'category': 'Trainer',
            'dexId': [],
            'types': []
        }
        
        enriched = self.step._enrich_card(card, self.pokemon_by_id)
        
        assert enriched['card_type'] == 'trainer'
        assert enriched['trainer_type'] == 'Item'
        # Trainer cards get the same name in all languages
        assert enriched['name_de'] == "Acerola's Mischief"
        assert enriched['name_en'] == "Acerola's Mischief"
        assert enriched['name_ja'] == "Acerola's Mischief"
    
    def test_enrich_card_missing_dexid(self):
        """Test card with no dexId (should be unknown)."""
        card = {
            'id': 'test-001',
            'localId': '001',
            'name': 'Unknown Card',
            'category': 'Pokemon',
            'dexId': [],
            'types': []
        }
        
        enriched = self.step._enrich_card(card, self.pokemon_by_id)
        
        assert enriched.get('card_type') == 'unknown'
        assert enriched.get('pokemon_id') is None


class TestMultilingualCardAvailability:
    """A localized PDF may contain only cards observed in that language."""

    def setup_method(self):
        self.step = EnrichTCGNamesMultilingualStep("test_languages")

    def test_enrichment_records_only_observed_languages(self):
        card = {
            'id': 'svp-190',
            'localId': '190',
            'name': 'Pikachu',
        }

        [result] = self.step._enrich_cards(
            [card],
            {'190': {'en': 'Pikachu'}},
        )

        assert result['available_languages'] == ['en']
        assert result['printed_number'] == '190'
        assert result['name_en'] == 'Pikachu'
        assert 'name_de' not in result

    def test_enrichment_marks_every_observed_translation(self):
        card = {
            'id': 'sv09-189',
            'localId': '189',
            'name': "N's Zorua",
        }

        [result] = self.step._enrich_cards(
            [card],
            {
                '189': {
                    'de': 'Ns Zorua',
                    'en': "N's Zorua",
                    'fr': 'Zorua de N',
                    'zh_hans': 'Ｎ的索罗亚',
                }
            },
        )

        assert result['available_languages'] == ['de', 'en', 'fr', 'zh_hans']
        assert result['printed_number'] == '189'


class TestPokemonIndexBuilding:
    """Test building Pokemon ID index from Pokedex."""
    
    def setup_method(self):
        """Setup test instance."""
        self.step = EnrichTCGCardsFromPokedexStep("test_index_building")
    
    def test_build_pokemon_id_index(self):
        """Test building index from Pokedex data."""
        pokedex_data = {
            'sections': {
                'all': {
                    'cards': [
                        {
                            'pokemon_id': 1,
                            'name': {'de': 'Bisasam', 'en': 'Bulbasaur'},
                            'types': ['Grass']
                        },
                        {
                            'pokemon_id': 25,
                            'name': {'de': 'Pikachu', 'en': 'Pikachu'},
                            'types': ['Electric']
                        }
                    ]
                }
            }
        }
        
        index = self.step._build_pokemon_id_index(pokedex_data)
        
        assert len(index) == 2
        assert 1 in index
        assert 25 in index
        assert index[1]['names']['de'] == 'Bisasam'
        assert index[25]['names']['en'] == 'Pikachu'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
