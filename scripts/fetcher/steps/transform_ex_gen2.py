"""
Transform Black & White EX Cards to Variant Format (Single Card per Pokemon)

Transforms TCGdex Black & White EX card data from source format to the variant format
expected by the PDF generator. Selects ONE card per Pokemon (priority: Next Destinies first,
then alphabetically by set name).

Input: data/source/tcg_bw_ex.json
Output: data/output/ExGen2.json (normal, Mega, and Primal sections)
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
import sys
import json
import requests
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from steps.base import BaseStep, PipelineContext
from steps.pokemon_utils import get_mega_artwork_url

logger = logging.getLogger(__name__)


class TransformBlackWhiteEXStep(BaseStep):
    """
    Transform Black & White EX cards to variant format - ONE card per Pokemon.
    
    Selection priority when multiple cards exist:
    1. BW - Next Destinies (first BW EX set, bw2)
    2. Alphabetically by set name
    
    Mega and Primal variants are emitted in dedicated sections.
    """

    # TCGdex does not include the X/Y form in these English card names.
    # Their attacks are stable, form-specific source data, so they let us
    # preserve the identity of the selected card without guessing a sibling.
    _MEGA_FORM_BY_ATTACK = {
        6: {
            'Crimson Dive': 'Y',
            'Wild Blaze': 'X',
        },
        150: {
            'Vanishing Strike': 'X',
            'Psychic Infinity': 'Y',
        },
    }
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def execute(self, context: PipelineContext, params: Dict[str, Any]) -> PipelineContext:
        """
        Execute the transformation.
        
        1. Load source data from context
        2. Group by Pokemon (dexId)
        3. Select one card per Pokemon (priority rules)
        4. Transform to variant format
        """
        logger.info(f"Starting BW EX cards transformation (single card per Pokemon)")
        
        # Load cards from context
        cards = context.data.get('tcg_bw_xy_ex_cards')
        if not cards:
            raise ValueError("No BW/XY EX cards found in context. Make sure fetch_tcgdex_ex_gen2 ran before this step.")
        
        logger.info(f"Loaded {len(cards)} cards from source")
        
        # Group cards by type (normal, mega, primal)
        # For mega cards, use tuple (dexId, form_suffix) to handle X/Y variants
        normal_cards: Dict[int, List[Dict[str, Any]]] = {}
        mega_cards: Dict[tuple, List[Dict[str, Any]]] = {}
        primal_cards: Dict[int, List[Dict[str, Any]]] = {}
        
        for card in cards:
            dex_ids = card.get('dexId', [])
            if not dex_ids:
                logger.warning(f"Card {card.get('name')} has no dexId")
                continue
            
            dex_id = dex_ids[0]
            name = card.get('name', '')
            
            # Categorize by type
            if 'Primal' in name:
                if dex_id not in primal_cards:
                    primal_cards[dex_id] = []
                primal_cards[dex_id].append(card)
            elif 'M ' in name or 'Mega' in name or name.startswith('M-'):
                # Resolve form identity before grouping so X/Y siblings never
                # collapse into a single dexId bucket.
                form_suffix = self._resolve_mega_form_suffix(card) or ""
                
                mega_key = (dex_id, form_suffix)
                if mega_key not in mega_cards:
                    mega_cards[mega_key] = []
                mega_cards[mega_key].append(card)
            else:
                if dex_id not in normal_cards:
                    normal_cards[dex_id] = []
                normal_cards[dex_id].append(card)
        
        logger.info(f"Grouped: {len(normal_cards)} normal, {len(mega_cards)} mega, {len(primal_cards)} primal Pokemon")
        
        # Select one card per Pokemon for each category
        selected_normal = self._select_best_cards(normal_cards)
        selected_mega = self._select_best_cards(mega_cards)
        selected_primal = self._select_best_cards(primal_cards)
        
        logger.info(f"Selected: {len(selected_normal)} normal, {len(selected_mega)} mega, {len(selected_primal)} primal")
        
        # Transform to variant format
        variant_data = self._transform_to_variant_format(selected_normal, selected_mega, selected_primal, context)
        
        # Store in context for subsequent enrichment steps and for save_output step
        context.set_data(variant_data)
        
        logger.info(f"✅ Transformed Black & White EX cards to variant format")
        
        return context
    
    def _select_best_cards(self, pokemon_cards: Dict) -> List[Dict[str, Any]]:
        """
        Select one card per Pokemon (or form) based on priority rules.
        
        Accepts either:
        - Dict[int, List] for normal/primal cards (grouped by dexId)
        - Dict[tuple, List] for mega cards (grouped by dexId + form_suffix)
        """
        selected_cards = []
        
        for key in sorted(pokemon_cards.keys()):
            # Extract dex_id from key (either int or tuple)
            dex_id = key if isinstance(key, int) else key[0]
            cards_for_pokemon = pokemon_cards[key]
            
            if len(cards_for_pokemon) == 1:
                selected_cards.append(cards_for_pokemon[0])
            else:
                # Apply priority rules
                # 1. Next Destinies (bw4)
                nd_cards = [c for c in cards_for_pokemon if c['set']['id'] == 'bw4']
                if nd_cards:
                    selected_cards.append(nd_cards[0])
                    continue
                
                # 2. Alphabetically by set name
                cards_sorted = sorted(cards_for_pokemon, key=lambda c: c['set']['name'])
                selected_cards.append(cards_sorted[0])
        
        return selected_cards

    @staticmethod
    def _explicit_mega_form_suffix(name: str) -> str | None:
        """Return an explicitly named X/Y Mega form, if present."""
        tokens = (
            name.upper()
            .replace('(', ' ')
            .replace(')', ' ')
            .replace('-', ' ')
            .split()
        )
        while tokens and tokens[-1] == 'EX':
            tokens.pop()
        if tokens and tokens[-1] in {'X', 'Y'}:
            return tokens[-1]
        return None

    def _resolve_mega_form_suffix(self, card: Dict[str, Any]) -> str | None:
        """
        Resolve an X/Y Mega form from explicit or form-specific card data.

        Charizard and Mewtwo have sibling Mega forms whose TCGdex names are
        identical. In that case the selected card's attack identifies the
        depicted form. Unknown or conflicting evidence must fail loudly rather
        than silently substituting an arbitrary sibling.
        """
        name = card.get('name', '')
        explicit_suffix = self._explicit_mega_form_suffix(name)
        dex_ids = card.get('dexId', [])
        dex_id = dex_ids[0] if dex_ids else None
        attack_signatures = self._MEGA_FORM_BY_ATTACK.get(dex_id)

        if not attack_signatures:
            return explicit_suffix

        attack_names = {
            attack.get('name', '').strip()
            for attack in card.get('attacks', [])
            if isinstance(attack, dict)
        }
        evidenced_suffixes = {
            suffix
            for attack_name, suffix in attack_signatures.items()
            if attack_name in attack_names
        }

        card_id = card.get('id', '<unknown>')
        if len(evidenced_suffixes) > 1:
            raise ValueError(
                f"Conflicting X/Y Mega evidence for card {card_id!r}"
            )

        evidenced_suffix = next(iter(evidenced_suffixes), None)
        if (
            explicit_suffix
            and evidenced_suffix
            and explicit_suffix != evidenced_suffix
        ):
            raise ValueError(
                f"Named Mega form {explicit_suffix} conflicts with card "
                f"{card_id!r} attack evidence {evidenced_suffix}"
            )

        resolved_suffix = explicit_suffix or evidenced_suffix
        if not resolved_suffix:
            raise ValueError(
                f"Could not determine the exact X/Y Mega form for card "
                f"{card_id!r} ({name!r})"
            )
        return resolved_suffix
    
    def _transform_to_variant_format(self, normal_cards: List[Dict[str, Any]], 
                                     mega_cards: List[Dict[str, Any]],
                                     primal_cards: List[Dict[str, Any]],
                                     context: PipelineContext) -> Dict[str, Any]:
        """
        Transform cards to the variant format expected by PDF generator.
        
        Format matches existing variant structure with multiple sections.
        """
        # Get variant metadata from context
        metadata = context.storage.get('metadata', {})
        variant_meta = metadata.get('variants', {}).get('ExGen2', {})
        
        # Transform each section
        normal_pokemon = self._transform_card_list(normal_cards, 'normal')
        mega_pokemon = self._transform_card_list(mega_cards, 'mega')
        primal_pokemon = self._transform_card_list(primal_cards, 'primal')
        
        variant_data = {
            'type': 'variant',
            'name': 'Pokémon EX - Generation 2',
            'sections': {
                'normal': {
                    'section_id': 'normal',
                    'color_hex': variant_meta.get('color', '#3D5A80'),
                    'title': variant_meta.get('title', {}),
                    'subtitle': variant_meta.get('subtitle', {}),
                    'suffix': '',
                    'cards': normal_pokemon
                },
                'mega': {
                    'section_id': 'mega',
                    'color_hex': '#7B2CBF',
                    'title': {
                        'de': 'Mega-Pokémon [EX]',
                        'en': 'Mega Pokémon [EX]',
                        'fr': 'Méga-Pokémon [EX]',
                        'es': 'Mega-Pokémon [EX]',
                        'it': 'Mega-Pokémon [EX]',
                        'ja': 'メガポケモン [EX]',
                        'ko': '메가 포켓몬 [EX]',
                        'zh_hans': '超级宝可梦 [EX]',
                        'zh_hant': '超級寶可夢 [EX]'
                    },
                    'subtitle': {
                        'de': 'Mega-Entwicklung',
                        'en': 'Mega Evolution',
                        'fr': 'Méga-Évolution',
                        'es': 'Megaevolución',
                        'it': 'Megaevoluzione',
                        'ja': 'メガシンカ',
                        'ko': '메가진화',
                        'zh_hans': '超级进化',
                        'zh_hant': '超級進化'
                    },
                    'suffix': '',
                    'cards': mega_pokemon
                },
                'primal': {
                    'section_id': 'primal',
                    'color_hex': '#C1121F',
                    'title': {
                        'de': 'Proto-Pokémon [EX]',
                        'en': 'Primal Pokémon [EX]',
                        'fr': 'Pokémon Primo [EX]',
                        'es': 'Pokémon Primigenio [EX]',
                        'it': 'Pokémon Archeo [EX]',
                        'ja': 'ゲンシポケモン [EX]',
                        'ko': '원시포켓몬 [EX]',
                        'zh_hans': '原始宝可梦 [EX]',
                        'zh_hant': '原始寶可夢 [EX]'
                    },
                    'subtitle': {
                        'de': 'Urform-Reversion',
                        'en': 'Primal Reversion',
                        'fr': 'Primo-Résurgence',
                        'es': 'Regresión Primigenia',
                        'it': 'Archeorisveglio',
                        'ja': 'ゲンシカイキ',
                        'ko': '원시회귀',
                        'zh_hans': '原始回归',
                        'zh_hant': '原始回歸'
                    },
                    'suffix': '',
                    'cards': primal_pokemon
                }
            }
        }
        
        logger.info(f"Created variant with {len(normal_pokemon)} normal, {len(mega_pokemon)} mega, {len(primal_pokemon)} primal")
        
        return variant_data
    
    def _get_pokeapi_artwork_url(self, dex_id: int, pokemon_name: str, section: str, form_suffix: str = None) -> str:
        """
        Generate PokeAPI official artwork URL for a Pokemon.
        
        Args:
            dex_id: National Pokedex ID
            pokemon_name: Pokemon name (e.g., "Charizard")
            section: 'normal', 'mega', or 'primal'
            form_suffix: Form suffix like "X" or "Y" for Mega variants
        
        Returns:
            URL to official artwork PNG
        """
        # For normal Pokemon, use direct artwork URL
        if section == 'normal':
            return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{dex_id}.png"
        
        # For Mega Evolutions and Primal forms, use shared utility or special handling
        if section == 'primal':
            # Primal forms need special handling (kept as is for now)
            form_name = f"{pokemon_name.lower().replace(' ', '-')}-primal"
            
            # Query PokeAPI for primal form
            for attempt in range(3):
                try:
                    response = requests.get(
                        f"https://pokeapi.co/api/v2/pokemon/{form_name}", 
                        timeout=30
                    )
                    if response.status_code == 200:
                        form_data = response.json()
                        form_id = form_data.get('id')
                        if form_id:
                            logger.debug(f"✓ Found primal form artwork for {form_name} (ID: {form_id})")
                            return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{form_id}.png"
                    
                    logger.warning(
                        f"Could not fetch primal form data for {form_name}"
                    )
                    break
                    
                except requests.Timeout:
                    if attempt < 2:
                        logger.warning(f"Timeout fetching {form_name}, retrying ({attempt + 1}/3)...")
                        time.sleep(2)
                    else:
                        logger.warning(
                            f"Timeout fetching {form_name} after 3 attempts"
                        )
                except Exception as e:
                    logger.warning(f"Error fetching primal artwork for {pokemon_name}: {e}")
                    break

            raise RuntimeError(
                f"Could not resolve exact PokeAPI artwork for primal form "
                f"{form_name!r}"
            )
            
        elif section == 'mega':
            # Handle special cases: Charizard and Mewtwo MUST have X or Y suffix
            base_name = pokemon_name.lower().replace(' ', '-')
            if base_name in ['charizard', 'mewtwo'] and not form_suffix:
                raise ValueError(
                    f"{pokemon_name} Mega requires an explicit X or Y suffix"
                )
            
            # Use shared utility for Mega evolutions
            return get_mega_artwork_url(
                pokemon_name=pokemon_name,
                base_id=dex_id,
                form_suffix=form_suffix
            )
        else:
            # Normal Pokemon
            return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{dex_id}.png"
    
    def _transform_card_list(self, cards: List[Dict[str, Any]], section: str) -> List[Dict[str, Any]]:
        """Transform a list of cards to Pokemon entries."""
        pokemon_list = []
        
        for card in cards:
            dex_ids = card.get('dexId', [])
            if not dex_ids:
                continue
            
            dex_id = dex_ids[0]
            name = card.get('name', '')
            form_variant = None
            
            # Extract Pokemon name and determine prefix/suffix
            if section == 'primal':
                # Primal cards: "Primal Kyogre EX" -> prefix="Primal", name="Kyogre", suffix="[EX]"
                pokemon_name = name.replace('Primal ', '').replace(' EX', '').replace('-EX', '').strip()
                prefix = 'Primal'
                suffix = '[EX]'
            elif section == 'mega':
                # Mega cards: "M Charizard EX" -> prefix="[M]", name="Charizard", suffix="[EX]"
                pokemon_name = name.replace('M ', '').replace('Mega ', '').replace(' EX', '').replace('-EX', '').strip()
                
                # Check for X/Y form variants: "M Charizard EX (X)" or "M Charizard EX (Y)"
                form_variant = self._resolve_mega_form_suffix(card)
                if form_variant == 'X':
                    pokemon_name = pokemon_name.replace('(X)', '').replace(' X', '').strip()
                elif form_variant == 'Y':
                    pokemon_name = pokemon_name.replace('(Y)', '').replace(' Y', '').strip()
                
                prefix = '[M]'
                suffix = '[EX]'
            else:
                # Normal EX cards: no prefix, suffix="[EX]"
                if '-EX' in name:
                    pokemon_name = name.replace('-EX', '').strip()
                elif ' EX' in name:
                    pokemon_name = name.replace(' EX', '').strip()
                else:
                    pokemon_name = name.strip()
                prefix = None
                suffix = '[EX]'
                form_variant = None
            
            # Get image URL from PokeAPI official artwork
            image_url = self._get_pokeapi_artwork_url(dex_id, pokemon_name, section, form_variant if section == 'mega' else None)
            
            form_suffix = f"_EX2_{section.upper()[:3]}"
            if section == 'mega' and form_variant:
                form_suffix += f"_{form_variant}"
            
            pokemon_entry = {
                'pokemon_id': dex_id,
                'types': card.get('types', []),
                'image_url': image_url,
                'name': {
                    'en': pokemon_name,
                    'de': pokemon_name,
                    'fr': pokemon_name,
                    'es': pokemon_name,
                    'it': pokemon_name,
                    'ja': pokemon_name,
                    'ko': pokemon_name,
                    'zh_hans': pokemon_name,
                    'zh_hant': pokemon_name
                },
                'prefix': prefix,
                'suffix': suffix,
                'form_code': f"#{dex_id:03d}{form_suffix}",
                'tcg_card': {
                    'id': card.get('id'),
                    'localId': card.get('localId'),
                    'set': card.get('set'),
                    'hp': card.get('hp'),
                    'rarity': card.get('rarity')
                }
            }

            if section == 'primal':
                pokemon_entry['localized_prefix'] = {'de': 'Proto-'}

            if section == 'mega' and form_variant:
                pokemon_entry['variant_form'] = form_variant.lower()
            
            pokemon_list.append(pokemon_entry)
        
        return pokemon_list
    
