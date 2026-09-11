"""
Transform TCG Set Cards to Target Format

Pure transformation step - converts enriched TCG data to target format.
All enrichment (pokemon_id, types, classification, multilingual names) should 
happen before this step.

This step:
- Transforms cards from source to target structure
- Passes through metadata: set_names, release_date, available_languages
- Preserves set info: logo, symbol, card_count

Input: data/source/{set_id}.json (enriched)
Output: data/{set_id}.json (target format)
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
import sys
import json
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from steps.base import BaseStep, PipelineContext
from steps.pokemon_utils import get_mega_artwork_url

logger = logging.getLogger(__name__)


class TransformTCGSetStep(BaseStep):
    """Transform enriched TCG set cards to target format for PDF generation."""
    
    def execute(self, context: PipelineContext, params: Dict[str, Any]) -> PipelineContext:
        """
        Execute the transform step.
        
        Combines raw source data with enrichments from context to create PDF-ready output.
        
        Required params:
            - set_id: Set ID (e.g., "ME01")
        
        Reads from context.data['tcg_set_source']
        Writes to context.data['tcg_set_target']
        """
        set_id = params.get('set_id')
        if not set_id:
            raise ValueError("set_id parameter is required")
        
        logger.info(f"🔄 Transforming TCG set: {set_id}")
        
        # Load data from context
        source_data = context.data.get('tcg_set_source')
        if not source_data:
            raise ValueError("No TCG set data found in context. Make sure fetch_tcgdex_set ran before this step.")
        
        raw_cards = source_data['cards']
        set_info = source_data['set_info']
        logger.info(f"📋 Loaded {len(raw_cards)} raw cards from {set_info['name']}")
        
        # Cards already have all enrichments applied by enrich steps
        # (multilingual names, pokedex data, special card images)
        # Just transform to target format
        
        transformed_cards = self._transform_cards(raw_cards)
        
        pokemon_cards = sum(1 for c in transformed_cards if c.get('pokemon_id'))
        trainer_cards = len(transformed_cards) - pokemon_cards
        
        logger.info(f"✅ Transformed {len(transformed_cards)} cards")
        logger.info(f"   - Pokemon cards: {pokemon_cards}")
        logger.info(f"   - Trainer/Energy cards: {trainer_cards}")
        
        # Create target format (PDF-ready, minimal data)
        target_data = {
            'type': 'tcg_set',
            'set_id': set_id,
            'name': set_info['name'],
            'name_en': set_info.get('name_en', set_info['name']),
            'release_date': set_info.get('release_date', ''),
            'serie': set_info.get('serie', ''),
            'serie_name': set_info.get('serie_name', ''),
            'logo': set_info.get('logo', ''),
            'symbol': set_info.get('symbol', ''),
            'card_count': set_info.get('card_count', {}),
            'available_languages': source_data.get('available_languages', ['en']),
            'set_names': source_data.get('set_names', {}),
            'logo_urls': source_data.get('logo_urls', {}),
            'cards': transformed_cards
        }
        
        # Store in context for subsequent steps (transform_to_sections_format, save_output)
        context.data['tcg_set_target'] = target_data
        
        logger.info(f"✅ Transformed {set_id} to target format")
        
        return context
    
    def _transform_cards(self, raw_cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform raw API cards to PDF-ready format.
        Cards already have all enrichments applied.
        
        Args:
            raw_cards: Already enriched cards from context
        
        Returns:
            List of PDF-ready card objects
        """
        transformed = []
        
        for card in raw_cards:
            card_type = card.get('card_type', 'unknown')
            
            if card_type == 'trainer':
                # Trainer/Energy card - already has all enrichments
                # Build multilingual name dict from name_XX fields
                name_dict = self._build_multilingual_name(card)
                
                transformed.append({
                    'id': card.get('id'),
                    'localId': card['localId'],
                    'printed_number': card.get(
                        'printed_number',
                        card['localId'],
                    ),
                    'available_languages': card.get(
                        'available_languages',
                        ['en'],
                    ),
                    'name': name_dict,
                    'type': 'trainer',
                    'trainer_type': card.get('trainer_type', 'Trainer'),
                    'types': card.get('types', ['Trainer']),
                    'pokemon_id': None,
                    'image_url': card.get('special_card_image') or None
                })
            elif card_type == 'pokemon':
                # Pokemon card - already enriched
                pokemon_id = card.get('pokemon_id')
                types = card.get('types', [])
                
                # Get multilingual name
                name_dict = card.get('name', {})
                if not isinstance(name_dict, dict):
                    # Build from name_XX fields (set by enrich_tcg_names_multilingual step)
                    name_dict = self._build_multilingual_name(card)
                    if not name_dict:
                        name_dict = {'en': str(card.get('name', 'Unknown'))}
                
                # Get sprite URL - only if pokemon_id exists
                if pokemon_id:
                    suffix, prefix = self._determine_variant_suffix_and_prefix(card)
                    
                    # Remove suffix from name if it's already in the name
                    if suffix:
                        name_dict = self._strip_suffix_from_name(name_dict, suffix)
                    
                    # Remove prefix from name if it's already in the name
                    if prefix:
                        name_dict = self._strip_prefix_from_name(name_dict, prefix)
                    
                    if prefix == 'Mega':
                        original_name = card.get('name', '')
                        if isinstance(original_name, dict):
                            original_name = original_name.get('en', '')
                        sprite_url = get_mega_artwork_url(
                            pokemon_name=name_dict.get('en', ''),
                            base_id=pokemon_id,
                            original_card_name=original_name
                        )
                    else:
                        sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pokemon_id}.png"
                else:
                    sprite_url = ''
                    suffix = ''
                    prefix = ''
                
                card_data = {
                    'id': card.get('id'),
                    'localId': card['localId'],
                    'printed_number': card.get(
                        'printed_number',
                        card['localId'],
                    ),
                    'available_languages': card.get(
                        'available_languages',
                        ['en'],
                    ),
                    'name': name_dict,
                    'type': 'pokemon',
                    'pokemon_id': pokemon_id,
                    'types': types,
                    'image_url': sprite_url
                }
                
                # Add variant markers if present
                if pokemon_id:
                    if suffix:
                        card_data['suffix'] = suffix
                    if prefix:
                        card_data['prefix'] = prefix
                
                transformed.append(card_data)
            else:
                # Unknown or unmapped card
                logger.warning(f"⚠️  Unknown card: {card.get('name')} (type: {card_type})")
                transformed.append({
                    'id': card.get('id'),
                    'localId': card['localId'],
                    'printed_number': card.get(
                        'printed_number',
                        card['localId'],
                    ),
                    'available_languages': card.get(
                        'available_languages',
                        ['en'],
                    ),
                    'name': {'en': str(card.get('name', 'Unknown'))},
                    'type': 'unknown',
                    'image_url': ''
                })
        
        return transformed
    
    def _determine_variant_suffix_and_prefix(self, card: Dict[str, Any]) -> tuple:
        """
        Determine the variant suffix and prefix from card name.
        Returns (suffix, prefix) tuple.
        
        Suffix formats:
        - "[EX_NEW]" for modern lowercase ex (2023+, e.g., "Venusaur ex")
        - "ex" for Classic ex (2003-2007, uppercase EX in name)
        - "GX" for GX cards
        - "V", "VMAX", "VSTAR" for V-series
        
        Prefix formats:
        - "Mega" for Mega evolutions
        - "Radiant", "Shining" for special variants
        
        Args:
            card: Card dict (can be raw or enriched, needs 'name' field)
        """
        # Get name from card (works with both raw and enriched cards)
        original_name = card.get('name', '')
        if isinstance(original_name, dict):
            original_name = original_name.get('en', '')
        if not original_name:
            return (None, None)
        
        suffix = None
        prefix = None
        
        # Check for prefix
        if original_name.startswith('Mega '):
            prefix = 'Mega'
        elif original_name.startswith('Radiant '):
            prefix = 'Radiant'
        elif original_name.startswith('Shining '):
            prefix = 'Shining'
        
        # Check for suffix - distinguish between Classic ex and modern [ex]
        name_lower = original_name.lower()
        if name_lower.endswith(' ex') or name_lower.endswith('-ex'):
            # Modern lowercase ex (Scarlet & Violet era) uses [EX_NEW] suffix
            suffix = '[EX_NEW]'
        elif name_lower.endswith(' vstar'):
            suffix = 'VSTAR'
        elif name_lower.endswith(' vmax'):
            suffix = 'VMAX'
        elif name_lower.endswith(' v') or name_lower.endswith('-v'):
            suffix = 'V'
        elif name_lower.endswith(' gx') or name_lower.endswith('-gx'):
            suffix = 'GX'
        
        return (suffix, prefix)
    
    def _strip_suffix_from_name(self, name_dict: Dict[str, str], suffix: str) -> Dict[str, str]:
        """
        Remove suffix markers from Pokemon names if they're already in the name.
        
        Prevents double-suffix like "Miraidon-ex [EX_NEW]" -> should be "Miraidon [EX_NEW]"
        
        Args:
            name_dict: Multilingual name dictionary
            suffix: Detected suffix (e.g., '[EX_NEW]', 'GX', 'V')
        
        Returns:
            Cleaned name dictionary with suffix markers removed
        """
        if not suffix or not name_dict:
            return name_dict
        
        cleaned = {}
        
        # Define suffix patterns to remove from names
        patterns_to_remove = []
        
        if suffix == '[EX_NEW]':
            # Modern lowercase ex - remove " ex" or "-ex" from end
            patterns_to_remove = [' ex', '-ex', ' Ex', '-Ex']
        elif suffix == 'ex':
            # Classic uppercase EX - remove " ex" or "-ex" from end  
            patterns_to_remove = [' ex', '-ex', ' Ex', '-Ex']
        elif suffix == 'GX':
            patterns_to_remove = [' GX', '-GX', ' gx', '-gx']
        elif suffix in ['V', 'VMAX', 'VSTAR']:
            patterns_to_remove = [f' {suffix}', f'-{suffix}', f' {suffix.lower()}', f'-{suffix.lower()}']
        
        # Clean each language
        for lang, name in name_dict.items():
            cleaned_name = name
            for pattern in patterns_to_remove:
                if cleaned_name.endswith(pattern):
                    cleaned_name = cleaned_name[:-len(pattern)]
                    break  # Only remove first match
            cleaned[lang] = cleaned_name
        
        return cleaned
    
    def _strip_prefix_from_name(self, name_dict: Dict[str, str], prefix: str) -> Dict[str, str]:
        """
        Remove prefix markers from Pokemon names if they're already in the name.
        
        Prevents double-prefix like "Mega Mega Gengar" -> should be "Gengar" with prefix="Mega"
        
        Args:
            name_dict: Multilingual name dictionary
            prefix: Detected prefix (e.g., 'Mega', 'Radiant', 'Shining')
        
        Returns:
            Cleaned name dictionary with prefix markers removed
        """
        if not prefix or not name_dict:
            return name_dict
        
        cleaned = {}
        
        # Define language-specific prefix patterns
        prefix_patterns = {
            'Mega': {
                'de': ['Mega-', 'Mega '],
                'en': ['Mega '],
                'fr': ['Méga-', 'Méga '],
                'es': ['Mega-', 'Mega '],
                'it': ['Mega '],
                'ja': ['メガ'],
                'ko': ['메가'],
                'zh_hans': ['超级'],
                'zh_hant': ['超級']
            },
            'Radiant': {
                'de': ['Strahlend ', 'Strahlende ', 'Strahlender ', 'Strahlendes '],
                'en': ['Radiant '],
                'fr': ['Radieux ', 'Radieuse '],
                'es': ['Radiante '],
                'it': ['Radiante '],
                'ja': ['かがやく'],
                'ko': ['빛나는 '],
                'zh_hans': ['光辉'],
                'zh_hant': ['光輝']
            },
            'Shining': {
                'de': ['Shiny '],
                'en': ['Shining '],
                'fr': ['Shining '],
                'es': ['Shining '],
                'it': ['Shining '],
                'ja': ['ひかる'],
                'ko': ['빛나는 '],
                'zh_hans': ['闪光'],
                'zh_hant': ['閃光']
            }
        }
        
        patterns = prefix_patterns.get(prefix, {})
        
        # Clean each language
        for lang, name in name_dict.items():
            cleaned_name = name
            lang_patterns = patterns.get(lang, [])
            
            for pattern in lang_patterns:
                if cleaned_name.startswith(pattern):
                    cleaned_name = cleaned_name[len(pattern):]
                    break  # Only remove first match
            
            cleaned[lang] = cleaned_name
        
        return cleaned
    
    def _build_multilingual_name(self, card: Dict[str, Any]) -> Dict[str, str]:
        """
        Build multilingual name dict from name_XX fields.
        
        Args:
            card: Card dict with name_de, name_fr, etc. fields from enrich_tcg_names_multilingual
        
        Returns:
            Dict with language keys (de, en, fr, etc.) -> translated names
        """
        name_dict = {}
        
        # Supported languages
        languages = ['de', 'en', 'fr', 'es', 'it', 'ja', 'ko', 'zh_hans', 'zh_hant']
        
        for lang in languages:
            # Check for name_{lang} field from enrich_tcg_names_multilingual
            lang_name = card.get(f'name_{lang}')
            if lang_name:
                name_dict[lang] = lang_name
        
        # Fallback: if no multilingual names found, use the 'name' field for all languages
        if not name_dict:
            fallback_name = card.get('name', 'Unknown')
            for lang in languages:
                name_dict[lang] = fallback_name
        
        return name_dict
