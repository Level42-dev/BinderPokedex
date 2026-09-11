"""
Enrich TCG Cards from Pokedex

Enriches TCG card data by:
1. Resolving canonical card identity from the English name with dexId fallback
2. Adding multilingual names (DE, FR, ES, IT, JA, KO, ZH) from Pokedex
3. Adding missing types from Pokedex if not in TCG data
4. Classifying cards as pokemon/trainer/energy

An exactly resolved name corrects inconsistent upstream IDs; otherwise a valid
TCGdex dexId remains authoritative.
"""

import logging
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from steps.base import BaseStep, PipelineContext
from steps.dex_id_utils import resolve_card_dex_id

logger = logging.getLogger(__name__)


class EnrichTCGCardsFromPokedexStep(BaseStep):
    """
    Enrich TCG cards with Pokemon data from Pokedex.
    
    Maps card names to Pokemon IDs and adds missing metadata.
    """
    
    def __init__(self, name: str):
        super().__init__(name)
        
        # Common card name patterns that indicate non-Pokemon cards
        self.trainer_indicators = [
            'befehl', 'amulett', 'bonbon', 'gong',
            'tausch', 'candy', 'switch', 'orders',
            'energy', 'energie', 'amulet', 'poffin', 'stretcher',
            'compass', 'mischief', 'determination', 'bargain',
            'wald', 'forest', 'garten', 'garden', 'ruinen', 'ruins',
            'strand', 'beach', 'schutz', 'repel',
            'zeitmesser', 'timepiece', 'premium', 'schabernack',
            'hyperball', 'luftballon', 'balloon', 'signal',
            'eisendefensive', 'iron defender', 'defender'
        ]
    
    def execute(self, context: PipelineContext, params: Dict[str, Any]) -> PipelineContext:
        """
        Execute the enrichment step.
        
        Required params:
            - pokedex_file: Path to Pokedex JSON
        
        Reads from context.data['tcg_set_source']
        Writes enriched data back to context.data['tcg_set_source']
        """
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Load pokedex file
        pokedex_path = params.get('pokedex_file', 'data/output/Pokedex.json')
        if not Path(pokedex_path).is_absolute():
            pokedex_file = project_root / pokedex_path
        else:
            pokedex_file = Path(pokedex_path)
        
        logger.info(f"🔍 Enriching TCG cards from Pokedex")
        
        # Load TCG data from context
        tcg_data = context.data.get('tcg_set_source')
        if not tcg_data:
            raise ValueError("No TCG set data found in context. Make sure fetch_tcgdex_set ran before this step.")
        
        # Load pokedex from file (needed for multilingual data)
        with open(pokedex_file, 'r', encoding='utf-8') as f:
            pokedex = json.load(f)
        
        cards = tcg_data.get('cards', [])
        logger.info(f"📋 Processing {len(cards)} cards")
        
        # Build canonical ID and English-name indexes from the Pokédex.
        pokemon_by_id = self._build_pokemon_id_index(pokedex)
        pokemon_by_name = self._build_pokemon_name_index(pokemon_by_id)
        logger.info(f"📚 Indexed {len(pokemon_by_id)} Pokemon by National Dex ID")
        
        # Enrich cards
        enriched_cards = []
        pokemon_count = 0
        trainer_count = 0
        
        for card in cards:
            enriched_card = self._enrich_card(
                card,
                pokemon_by_id,
                pokemon_by_name,
            )
            enriched_cards.append(enriched_card)
            
            if enriched_card.get('pokemon_id'):
                pokemon_count += 1
            elif enriched_card.get('card_type') == 'trainer':
                trainer_count += 1
        
        logger.info(f"✅ Enriched {len(enriched_cards)} cards")
        logger.info(f"   - Pokemon: {pokemon_count}")
        logger.info(f"   - Trainer/Energy: {trainer_count}")
        
        # Update data in context
        tcg_data['cards'] = enriched_cards
        context.data['tcg_set_source'] = tcg_data
        
        return context
    
    def _build_pokemon_id_index(self, pokedex: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """
        Build index of Pokemon by National Dex ID.

        Maps dexId -> Pokemon data with multilingual names and types.
        """
        index = {}
        
        if 'sections' in pokedex:
            for section_name, section_data in pokedex['sections'].items():
                # Get cards list
                pokemon_list = section_data.get('cards', [])
                for pokemon in pokemon_list:
                    # Get Pokemon ID
                    dex_id = pokemon.get('pokemon_id')
                    if not dex_id:
                        continue
                    
                    # Get types - supports both types[] array and type1/type2 fields
                    types = pokemon.get('types', [])
                    if not types and 'type1' in pokemon:
                        types = [pokemon['type1']]
                        if pokemon.get('type2'):
                            types.append(pokemon['type2'])
                    
                    # Get multilingual names
                    names = {}
                    name_value = pokemon.get('name')
                    if isinstance(name_value, dict):
                        # Multi-language dict - extract all languages
                        names = name_value.copy()
                    else:
                        # Fallback if simple string
                        names['en'] = name_value or ''
                    
                    # Store in index by dexId
                    index[dex_id] = {
                        'pokemon_id': dex_id,
                        'names': names,
                        'types': types,
                        'pokemon': pokemon
                    }
        
        return index

    def _build_pokemon_name_index(
        self,
        pokemon_by_id: Dict[int, Dict[str, Any]],
    ) -> Dict[str, int]:
        """Build a case-insensitive English-name identity lookup."""
        index = {}
        for pokemon_id, pokemon_data in pokemon_by_id.items():
            names = pokemon_data.get('names', {})
            english_name = (
                names.get('en')
                if isinstance(names, dict)
                else None
            )
            if (
                type(pokemon_id) is int
                and pokemon_id > 0
                and isinstance(english_name, str)
                and english_name.strip()
            ):
                index[english_name.strip().casefold()] = pokemon_id
        return index
    
    def _normalize_name(self, name: str) -> str:
        """Normalize Pokemon name for matching."""
        if not name:
            return ""
        
        # Remove form indicators and special characters
        name = re.sub(r'[-\s]+', '', name.lower())
        
        # Remove common suffixes
        for suffix in ['-ex', 'ex', '-gx', 'gx', '-v', '-vmax', '-vstar']:
            name = name.replace(suffix, '')
        
        return name
    
    def _extract_variant_markers(self, name: str) -> Dict[str, str]:
        """
        Extract variant markers from card name.
        Returns dict with 'prefix' and 'suffix' keys.
        Example: "Mega Venusaur ex" -> {'prefix': 'Mega', 'suffix': 'ex'}
        """
        markers = {'prefix': '', 'suffix': ''}
        
        # Check for prefix (Mega, Shining, Radiant, etc.)
        if name.lower().startswith('mega '):
            markers['prefix'] = 'Mega'
            name = name[5:].strip()  # Remove prefix for suffix check
        elif name.lower().startswith('shining '):
            markers['prefix'] = 'Shining'
            name = name[8:].strip()
        elif name.lower().startswith('radiant '):
            markers['prefix'] = 'Radiant'
            name = name[8:].strip()
        
        # Check for suffix (ex, GX, V, VMAX, VSTAR, etc.)
        name_lower = name.lower()
        if name_lower.endswith(' ex') or name_lower.endswith('-ex'):
            markers['suffix'] = 'ex'
        elif name_lower.endswith(' gx') or name_lower.endswith('-gx'):
            markers['suffix'] = 'GX'
        elif name_lower.endswith(' vstar'):
            markers['suffix'] = 'VSTAR'
        elif name_lower.endswith(' vmax'):
            markers['suffix'] = 'VMAX'
        elif name_lower.endswith(' v') or name_lower.endswith('-v'):
            markers['suffix'] = 'V'
        
        return markers if (markers['prefix'] or markers['suffix']) else None
    
    def _build_variant_name(self, base_name: str, markers: Dict[str, str], lang: str) -> str:
        """
        Build localized variant name from base Pokemon name + markers.
        Example: base_name="Bisaflor", markers={'prefix': 'Mega', 'suffix': 'ex'}, lang='de'
                 -> "Mega-Bisaflor-ex"
        """
        result = base_name
        
        # Add prefix
        if markers.get('prefix'):
            prefix = markers['prefix']
            # German uses hyphen for Mega
            separator = '-' if lang == 'de' else ' '
            result = f"{prefix}{separator}{result}"
        
        # Add suffix
        if markers.get('suffix'):
            suffix = markers['suffix']
            # Use hyphen for German, space for most others
            separator = '-' if lang in ['de', 'fr', 'es', 'it'] else ' '
            result = f"{result}{separator}{suffix}"
        
        return result
    
    def _enrich_card(
        self,
        card: Dict[str, Any],
        pokemon_by_id: Dict[int, Dict[str, Any]],
        pokemon_by_name: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Enrich a card with canonical Pokédex identity and localized names.

        The card name validates the upstream dexId when it resolves exactly;
        otherwise a valid upstream ID remains the fallback.
        """
        enriched = card.copy()
        
        # Check if it's a trainer/energy card using TCGdex category
        category = card.get('category', '').lower()
        if category in ['trainer', 'energy', 'entraîneur', 'energie']:
            enriched['card_type'] = 'trainer'
            
            # Set trainer_type: use Energy for energy cards, otherwise use trainerType
            if category in ['energy', 'energie']:
                enriched['trainer_type'] = 'Energy'
            else:
                trainer_type = card.get('trainerType', '')
                
                # Fallback: If trainerType is empty, try to infer from card name
                if not trainer_type:
                    card_name = card.get('name', '').lower()
                    # Common stadium keywords
                    if any(keyword in card_name for keyword in ['stadium', 'resort', 'gym', 'tower', 'temple', 'cave', 'lab']):
                        trainer_type = 'Stadium'
                        logger.info(f"✓ Inferred Stadium type for: {card.get('name')}")
                    else:
                        # Older sets predate the modern Trainer subcategories and
                        # TCGdex therefore leaves trainerType empty. Render these
                        # cards with the generic Item artwork instead of no image.
                        trainer_type = 'Item'
                
                enriched['trainer_type'] = trainer_type
            
            # Trainer names should already be enriched by enrich_tcg_names_multilingual step
            # Keep existing name_XX fields if present, otherwise fallback to English
            if not any(key.startswith('name_') for key in card.keys()):
                logger.warning(f"⚠️  Trainer card {card.get('name')} has no multilingual names, using English fallback")
                original_name = card.get('name', '')
                for lang in ['de', 'en', 'fr', 'es', 'it', 'ja', 'ko', 'zh_hans', 'zh_hant']:
                    enriched[f'name_{lang}'] = original_name
            
            return enriched
        
        # Resolve the name first so a plausible but inconsistent API ID cannot
        # bind a card to the wrong species.
        dex_ids = card.get('dexId', [])
        if pokemon_by_name is None:
            pokemon_by_name = self._build_pokemon_name_index(pokemon_by_id)
        resolved_dex_id = resolve_card_dex_id(
            card.get('name', ''),
            dex_ids,
            pokemon_by_name,
        )

        if resolved_dex_id is not None:
            dex_id = resolved_dex_id
            if dex_id in pokemon_by_id:
                supplied_dex_id = (
                    dex_ids[0]
                    if isinstance(dex_ids, list) and dex_ids
                    else None
                )
                if supplied_dex_id != dex_id:
                    enriched['dexId'] = [dex_id]
                    logger.warning(
                        "Corrected inconsistent TCGdex dexId for %r: #%s -> #%s",
                        card.get('name', ''),
                        (
                            supplied_dex_id
                            if supplied_dex_id is not None
                            else "none"
                        ),
                        dex_id,
                    )
                pokemon_data = pokemon_by_id[dex_id]
                
                enriched['pokemon_id'] = pokemon_data['pokemon_id']
                enriched['card_type'] = 'pokemon'
                
                # TCG card titles are authoritative because they may contain
                # ownership or other card-specific wording (for example,
                # "Ns Zoroark-ex").  Pokédex names only fill genuinely
                # missing localized fields; the transform step separately
                # extracts visual variant markers such as ex and Mega.
                if 'names' in pokemon_data:
                    observed_languages = card.get('available_languages')
                    for lang, base_name in pokemon_data['names'].items():
                        if (
                            isinstance(observed_languages, list)
                            and lang not in observed_languages
                        ):
                            continue
                        enriched.setdefault(f'name_{lang}', base_name)
                
                # Add types from Pokedex if missing
                if not enriched.get('types') and pokemon_data.get('types'):
                    enriched['types'] = pokemon_data['types']
                
                return enriched
        
        # Fallback: No dexId or not found
        # Check if it's still a Pokemon card based on category and types
        if category == 'pokemon' and card.get('types'):
            # Pokemon card without dexId (e.g., special promos like "Pikachu with Grey Felt Hat")
            # Keep as pokemon but without pokemon_id
            enriched['card_type'] = 'pokemon'
            enriched['pokemon_id'] = None
            enriched['types'] = card['types']  # Keep original types
            logger.warning(f"⚠️  No dexId mapping for: {card.get('name')} (dexIds: {dex_ids})")
        elif self._is_trainer_by_keywords(card.get('name', ''), ''):
            enriched['card_type'] = 'trainer'
        else:
            logger.warning(f"⚠️  No dexId mapping for: {card.get('name')} (dexIds: {dex_ids})")
            enriched['card_type'] = 'unknown'
        
        return enriched
    
    def _find_pokemon(self, name_de: str, name_en: str, pokemon_index: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find Pokemon in index by name."""
        # Clean names for Mega/ex variants
        names_to_try = [
            name_de,
            name_en,
            re.sub(r'^Mega[-\s]', '', name_de),  # "Mega-Bisaflor-ex" -> "Bisaflor-ex"
            re.sub(r'^Mega\s+', '', name_en),
            re.sub(r'-ex$', '', name_de),  # Remove -ex suffix
            re.sub(r'\s+ex$', '', name_en)
        ]
        
        for name in names_to_try:
            if not name:
                continue
            
            normalized = self._normalize_name(name)
            if normalized in pokemon_index:
                return pokemon_index[normalized]
        
        return None
    
    def _is_trainer_by_keywords(self, name_de: str, name_en: str) -> bool:
        """Check if card is trainer/energy based on keywords."""
        name_lower = f"{name_de} {name_en}".lower()
        
        for indicator in self.trainer_indicators:
            # Use word boundaries to match whole words only
            pattern = r'\b' + re.escape(indicator) + r'\b'
            if re.search(pattern, name_lower):
                return True
        
        return False
