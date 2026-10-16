"""
Enrich Featured Elements

Identifies the most important/famous Pokemon in each section and fetches
representative visual content for display on section cover pages.

Content Sources (auto-detected):
- TCG Card Scopes: Trading card images from TCGdex API
- Pokedex Scopes: Official Pokemon artwork from PokeAPI

This enrichment:
1. Analyzes Pokemon in each section
2. Identifies 2-3 most notable/famous Pokemon (using predefined rankings)
3. Fetches suitable images based on scope type:
   - ExGen: TCG cards with tcg_card sub-object
   - TCG-Sets (ME*, SV*): Card images via localId
   - Pokedex: Official artwork from PokeAPI
4. Stores unified element data structure for PDF generator

The step can be skipped if featured elements already exist, unless forced.
"""

import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from steps.base import BaseStep, PipelineContext
from scripts.poster_assets.poster_subject import (
    poster_display_name_from_card,
    poster_subject_from_card,
    resolve_poster_subject,
)

logger = logging.getLogger(__name__)

# Series mapping for TCGdex image URLs
SERIES_MAPPING = {
    'sv': 'sv', 'me': 'me', 'swsh': 'swsh', 'xy': 'xy', 'bw': 'bw',
    'dp': 'dp', 'pop': 'pop', 'ex': 'ex', 'base': 'base', 'gym': 'gym',
    'neo': 'neo', 'dc': 'dc', 'np': 'np', 'cel': 'swsh'
}

# Pokemon popularity/importance rankings
# Based on: Starter Pokemon, Legendaries, Pseudo-legendaries, Popular Pokemon, etc.
FEATURED_POKEMON_PRIORITY = {
    # Gen 1 Starters & Evolutions
    1: 100, 2: 95, 3: 90,  # Bulbasaur line
    4: 100, 5: 95, 6: 90,  # Charmander line
    7: 100, 8: 95, 9: 90,  # Squirtle line
    
    # Gen 1 Legendaries & Mythicals
    25: 100,  # Pikachu (mascot)
    131: 95,  # Lapras
    133: 95,  # Eevee
    143: 95,  # Snorlax
    144: 98,  # Articuno
    145: 98,  # Zapdos
    146: 98,  # Moltres
    150: 100, # Mewtwo
    151: 100, # Mew
    
    # Gen 2 Starters & Evolutions
    152: 100, 153: 95, 154: 90,  # Chikorita line
    155: 100, 156: 95, 157: 90,  # Cyndaquil line
    158: 100, 159: 95, 160: 90,  # Totodile line
    
    # Gen 2 Legendaries & Mythicals
    172: 95,  # Pichu
    175: 95,  # Togepi
    196: 90,  # Espeon
    197: 90,  # Umbreon
    243: 98,  # Raikou
    244: 98,  # Entei
    245: 98,  # Suicune
    249: 100, # Lugia
    250: 100, # Ho-Oh
    251: 100, # Celebi
    
    # Gen 3 Starters & Evolutions
    252: 100, 253: 95, 254: 90,  # Treecko line
    255: 100, 256: 95, 257: 90,  # Torchic line
    258: 100, 259: 95, 260: 90,  # Mudkip line
    
    # Gen 3 Legendaries & Mythicals
    380: 98,  # Latias
    381: 98,  # Latios
    382: 100, # Kyogre
    383: 100, # Groudon
    384: 100, # Rayquaza
    385: 100, # Jirachi
    386: 100, # Deoxys
    
    # Gen 4 Starters & Evolutions
    387: 100, 388: 95, 389: 90,  # Turtwig line
    390: 100, 391: 95, 392: 90,  # Chimchar line
    393: 100, 394: 95, 395: 90,  # Piplup line
    
    # Gen 4 Legendaries & Mythicals
    445: 95,  # Garchomp (Pseudo-legendary)
    447: 95,  # Riolu
    448: 95,  # Lucario
    480: 98,  # Uxie
    481: 98,  # Mesprit
    482: 98,  # Azelf
    483: 100, # Dialga
    484: 100, # Palkia
    485: 95,  # Heatran
    486: 98,  # Regigigas
    487: 100, # Giratina
    488: 98,  # Cresselia
    490: 100, # Manaphy
    491: 100, # Darkrai
    492: 98,  # Shaymin
    493: 100, # Arceus
    
    # Gen 5 Starters & Evolutions
    495: 100, 496: 95, 497: 90,  # Snivy line
    498: 100, 499: 95, 500: 90,  # Tepig line
    501: 100, 502: 95, 503: 90,  # Oshawott line
    
    # Gen 5 Legendaries & Mythicals
    635: 95,  # Hydreigon (Pseudo-legendary)
    638: 98,  # Cobalion
    639: 98,  # Terrakion
    640: 98,  # Virizion
    641: 98,  # Tornadus
    642: 98,  # Thundurus
    643: 100, # Reshiram
    644: 100, # Zekrom
    645: 98,  # Landorus
    646: 100, # Kyurem
    647: 98,  # Keldeo
    648: 98,  # Meloetta
    649: 100, # Genesect
    
    # Gen 6 Starters & Evolutions
    650: 100, 651: 95, 652: 90,  # Chespin line
    653: 100, 654: 95, 655: 90,  # Fennekin line
    656: 100, 657: 95, 658: 90,  # Froakie line
    
    # Gen 6 Legendaries & Mythicals
    700: 95,  # Sylveon
    716: 100, # Xerneas
    717: 100, # Yveltal
    718: 100, # Zygarde
    719: 98,  # Diancie
    720: 100, # Hoopa
    721: 98,  # Volcanion
    
    # Gen 7 Starters & Evolutions
    722: 100, 723: 95, 724: 90,  # Rowlet line
    725: 100, 726: 95, 727: 90,  # Litten line
    728: 100, 729: 95, 730: 90,  # Popplio line
    
    # Gen 7 Legendaries & Mythicals
    785: 98,  # Tapu Koko
    786: 98,  # Tapu Lele
    787: 98,  # Tapu Bulu
    788: 98,  # Tapu Fini
    789: 98,  # Cosmog
    790: 98,  # Cosmoem
    791: 100, # Solgaleo
    792: 100, # Lunala
    793: 98,  # Nihilego
    800: 100, # Necrozma
    801: 98,  # Magearna
    802: 100, # Marshadow
    807: 98,  # Zeraora
    809: 100, # Melmetal
    
    # Gen 8 Starters & Evolutions
    810: 100, 811: 95, 812: 90,  # Grookey line
    813: 100, 814: 95, 815: 90,  # Scorbunny line
    816: 100, 817: 95, 818: 90,  # Sobble line
    
    # Gen 8 Legendaries & Mythicals
    888: 100, # Zacian
    889: 100, # Zamazenta
    890: 100, # Eternatus
    891: 98,  # Kubfu
    892: 98,  # Urshifu
    893: 98,  # Zarude
    894: 98,  # Regieleki
    895: 98,  # Regidrago
    896: 100, # Glastrier
    897: 100, # Spectrier
    898: 100, # Calyrex
    
    # Gen 9 Starters & Evolutions
    906: 100, 907: 95, 908: 90,  # Sprigatito line
    909: 100, 910: 95, 911: 90,  # Fuecoco line
    912: 100, 913: 95, 914: 90,  # Quaxly line
    
    # Gen 9 Legendaries & Mythicals
    1007: 100, # Koraidon
    1008: 100, # Miraidon
}


class EnrichFeaturedElementsStep(BaseStep):
    """
    Enriches sections with featured elements (cards or artwork) for cover display.
    """
    
    def __init__(self, name: str):
        super().__init__(name)
    
    def execute(self, context: PipelineContext, params: Dict[str, Any]) -> PipelineContext:
        """
        Identify featured Pokemon and fetch card images.
        
        Args:
            context: Pipeline context with data
            params: Step parameters
                - max_cards: Maximum number of featured elements per section (default: 3)
                - force: Force regeneration even if elements exist (default: False)
                - cache_dir: Directory to cache images (default: data/section_artwork)
                - target_file: Load data from file if not in context
                - section_featured_card_ids: Optional mapping of section IDs to
                  ordered TCG card IDs. Configured sections are regenerated
                  deterministically even when featured elements already exist.
        
        Returns:
            Updated context with featured elements added to sections
        """
        max_cards = params.get('max_cards', 3)
        force = params.get('force', False)
        cache_dir = Path(params.get('cache_dir', 'data/section_artwork'))
        target_file = params.get('target_file') or context.target_file
        
        print(f"    🎴 Enriching featured elements (max: {max_cards}, force: {force})")
        
        data = context.get_data()
        
        # If no data in context, try to load from file
        if not data or 'sections' not in data:
            if target_file and Path(target_file).exists():
                print(f"       📂 Loading data from: {target_file}")
                with open(target_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                context.set_data(data)
            else:
                print("       ⚠️  No sections found in data and no target_file available")
                return context
        
        if not data or 'sections' not in data:
            print("       ⚠️  No sections found in data")
            return context
        
        # Ensure cache directory exists
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        sections = data['sections']
        section_featured_card_ids = self._validate_section_featured_card_ids(
            params.get('section_featured_card_ids'),
            sections,
            max_cards,
        )
        total_sections = len(sections)
        processed = 0
        skipped = 0
        added = 0
        
        for section_id, section_data in sections.items():
            configured_card_ids = section_featured_card_ids.get(section_id)

            # Check if featured elements already exist (unless forced)
            if (
                configured_card_ids is None
                and not force
                and 'featured_elements' in section_data
                and section_data['featured_elements']
            ):
                print(f"       ⏭️  Section '{section_id}': Featured elements already exist (use force=True to regenerate)")
                skipped += 1
                continue
            
            # Get Pokemon list from section
            cards = section_data.get('cards', [])
            if not cards:
                print(f"       ⚠️  Section '{section_id}': No cards found")
                processed += 1
                continue
            
            # Get set info from context or data
            # For TCG-Set scopes, set info might be in context.data['tcg_set_source'] (before transform)
            # or in data itself (after transform)
            set_info = None
            if 'tcg_set_source' in data:
                set_info = data['tcg_set_source'].get('set_info', {})
            elif 'set_id' in data and 'serie' in data:
                # After transform - construct set_info from top-level data
                set_info = {
                    'id': data.get('set_id').lower() if data.get('set_id') else None,
                    'name': data.get('name'),
                    'serie': data.get('serie'),
                }
            
            # Identify featured Pokemon and their visual elements from the section.
            # An explicit card list is authoritative and preserves its order.
            if configured_card_ids is not None:
                featured_elements = self._fetch_configured_featured_elements(
                    cards,
                    configured_card_ids,
                    cache_dir,
                    set_info,
                    section_id,
                )
            else:
                featured_elements = self._identify_and_fetch_featured_elements(
                    cards,
                    max_cards,
                    cache_dir,
                    set_info,
                )
            
            if not featured_elements:
                print(f"       ⚠️  Section '{section_id}': No featured elements identified")
                processed += 1
                continue
            
            # Add to section data
            if featured_elements:
                section_data['featured_elements'] = featured_elements
                added += len(featured_elements)
                pokemon_names = [c['pokemon_name'] for c in featured_elements]
                print(f"       ✅ Section '{section_id}': Added {len(featured_elements)} featured elements ({', '.join(pokemon_names)})")
            else:
                print(f"       ⚠️  Section '{section_id}': No card images found")
            
            processed += 1
        
        return context

    @staticmethod
    def _validate_section_featured_card_ids(
        configured_sections: Any,
        sections: Dict[str, Any],
        max_cards: int,
    ) -> Dict[str, List[str]]:
        """Validate an optional section-to-card-ID selection."""
        if configured_sections is None:
            return {}
        if not isinstance(configured_sections, dict):
            raise ValueError(
                "section_featured_card_ids must be a mapping of section IDs "
                "to ordered card ID lists"
            )

        unknown_sections = sorted(set(configured_sections) - set(sections))
        if unknown_sections:
            raise ValueError(
                "section_featured_card_ids references unknown sections: "
                + ", ".join(unknown_sections)
            )

        validated = {}
        for section_id, card_ids in configured_sections.items():
            if not isinstance(card_ids, list) or not card_ids:
                raise ValueError(
                    f"section_featured_card_ids.{section_id} must be a "
                    "non-empty ordered list"
                )
            if any(
                not isinstance(card_id, str) or not card_id
                for card_id in card_ids
            ):
                raise ValueError(
                    f"section_featured_card_ids.{section_id} contains an "
                    "invalid card ID"
                )
            duplicates = sorted(
                card_id
                for card_id, count in Counter(card_ids).items()
                if count > 1
            )
            if duplicates:
                raise ValueError(
                    f"section_featured_card_ids.{section_id} contains "
                    f"duplicate card IDs: {', '.join(duplicates)}"
                )
            if len(card_ids) > max_cards:
                raise ValueError(
                    f"section_featured_card_ids.{section_id} configures "
                    f"{len(card_ids)} cards, exceeding max_cards={max_cards}"
                )
            validated[section_id] = list(card_ids)

        return validated

    @staticmethod
    def _card_identifier(
        card: Dict[str, Any],
        set_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Return the stable full TCG card ID for supported card formats."""
        tcg_card = card.get('tcg_card')
        if isinstance(tcg_card, dict) and isinstance(tcg_card.get('id'), str):
            return tcg_card['id']

        if isinstance(card.get('id'), str):
            return card['id']

        local_id = card.get('localId')
        set_id = set_info.get('id') if set_info else None
        if local_id is not None and set_id:
            return f"{set_id}-{local_id}"

        return None

    def _fetch_configured_featured_elements(
        self,
        cards: List[Dict[str, Any]],
        configured_card_ids: List[str],
        cache_dir: Path,
        set_info: Optional[Dict[str, Any]],
        section_id: str,
    ) -> List[Dict[str, Any]]:
        """Fetch a section's explicitly configured cards in exact order."""
        matches = {card_id: [] for card_id in configured_card_ids}
        for card in cards:
            card_id = self._card_identifier(card, set_info)
            if card_id in matches:
                matches[card_id].append(card)

        missing = [
            card_id
            for card_id, matched_cards in matches.items()
            if not matched_cards
        ]
        if missing:
            raise ValueError(
                f"Section '{section_id}' is missing configured featured card "
                f"IDs: {', '.join(missing)}"
            )

        ambiguous = [
            card_id
            for card_id, matched_cards in matches.items()
            if len(matched_cards) > 1
        ]
        if ambiguous:
            raise ValueError(
                f"Section '{section_id}' contains configured featured card "
                f"IDs more than once: {', '.join(ambiguous)}"
            )

        featured_elements = []
        for card_id in configured_card_ids:
            card = matches[card_id][0]
            pokemon_id = card.get('pokemon_id')
            if not pokemon_id:
                raise ValueError(
                    f"Configured featured card '{card_id}' in section "
                    f"'{section_id}' has no pokemon_id"
                )

            poster_subject = poster_subject_from_card(card)
            # Resolve once here so invalid species/form mappings fail before a
            # cover image is accepted into the generated aggregate.
            resolve_poster_subject({
                'pokemon_id': pokemon_id,
                'poster_subject': poster_subject,
            })
            element_data = self._build_featured_element(
                pokemon_id,
                card,
                poster_subject,
                cache_dir,
                set_info,
            )
            if element_data is None:
                raise RuntimeError(
                    f"Could not resolve featured card '{card_id}' in section "
                    f"'{section_id}'"
                )
            featured_elements.append(element_data)

        return featured_elements
    
    def _identify_and_fetch_featured_elements(self, cards: List[Dict], max_cards: int, cache_dir: Path, set_info: Optional[Dict] = None) -> List[Dict]:
        """
        Identify featured Pokemon and fetch their visual elements.
        
        Args:
            cards: List of card dictionaries from the section
            max_cards: Maximum number to return
            cache_dir: Directory to cache images
            set_info: Optional set info for TCG-Set scopes
        
        Returns:
            List of featured element data dicts
        """
        # Extract unique visual subjects with their cards, sorted by species
        # priority.  Base and special forms of the same species may coexist.
        pokemon_cards = {}
        conflicting_subjects: set[tuple[str, int]] = set()
        for card in cards:
            pokemon_id = card.get('pokemon_id')
            if not pokemon_id:
                continue

            poster_subject = poster_subject_from_card(card)
            subject = resolve_poster_subject({
                'pokemon_id': pokemon_id,
                'poster_subject': poster_subject,
            })
            subject_key = subject.artwork_key()

            # Only keep the first (best) card for each exact artwork subject.
            # Flag inconsistent upstream mappings if such a subject would be
            # selected instead of silently binding it to the wrong species.
            existing = pokemon_cards.get(subject_key)
            if existing is not None:
                if existing['pokemon_id'] != pokemon_id:
                    conflicting_subjects.add(subject_key)
                continue

            if subject_key not in pokemon_cards:
                priority = FEATURED_POKEMON_PRIORITY.get(pokemon_id, 0)
                pokemon_cards[subject_key] = {
                    'priority': priority,
                    'pokemon_id': pokemon_id,
                    'card': card,
                    'poster_subject': poster_subject,
                }
        
        # Sort by priority (highest first)
        sorted_pokemon = sorted(
            pokemon_cards.items(),
            key=lambda x: x[1]['priority'],
            reverse=True
        )
        
        # Take top N and fetch their images
        featured_elements = []
        for subject_key, data in sorted_pokemon[:max_cards]:
            if subject_key in conflicting_subjects:
                raise ValueError(
                    f"Poster subject {subject_key!r} is assigned to more than "
                    "one Pokemon species in the source data"
                )
            pokemon_id = data['pokemon_id']
            card = data['card']
            element_data = self._build_featured_element(
                pokemon_id,
                card,
                data['poster_subject'],
                cache_dir,
                set_info,
            )
            if element_data:
                featured_elements.append(element_data)
        
        return featured_elements

    def _build_featured_element(
        self,
        pokemon_id: int,
        card: Dict[str, Any],
        poster_subject: Dict[str, Any],
        cache_dir: Path,
        set_info: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Build the common featured-element shape for auto and curated cards."""
        element_data = self._fetch_card_image_from_any_card(
            pokemon_id,
            card,
            cache_dir,
            set_info,
        )
        if element_data is None:
            return None

        element_data['poster_subject'] = poster_subject
        element_data['pokemon_name'] = poster_display_name_from_card(
            card,
            element_data.get('pokemon_name'),
        )
        return element_data
    
    def _download_and_cache_image(self, image_url: str, cache_file: Path) -> bool:
        """
        Download and cache a card image.
        
        Args:
            image_url: URL to download from
            cache_file: Path to save the image
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if cache_file.exists():
                return True
            
            img_response = requests.get(image_url, timeout=10)
            img_response.raise_for_status()
            cache_file.write_bytes(img_response.content)
            logger.info(f"Cached card image: {cache_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to download image from {image_url}: {e}")
            return False
    
    def _get_series_from_set_id(self, set_id: str) -> str:
        """
        Determine series identifier from set_id.
        
        Args:
            set_id: TCG set identifier (e.g., 'sv05', 'me01', 'ex1')
        
        Returns:
            Series identifier for TCGdex URLs
        """
        # Check for known prefixes
        for prefix, series in SERIES_MAPPING.items():
            if set_id.startswith(prefix):
                return series
        
        # Fallback
        return 'base'
    
    def _fetch_card_image_from_any_card(self, pokemon_id: int, card: Dict, cache_dir: Path, set_info: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch card image for a Pokemon. Auto-detects card format.
        
        Supported formats:
        - ExGen: Cards with tcg_card sub-object (classic ex series)
        - TCG-Set: Cards with localId (modern ME*/SV* sets)
        - Pokedex: Cards with image_url (PokeAPI official artwork)
        
        Args:
            pokemon_id: National Pokedex ID
            card: Card data from the scope
            cache_dir: Directory to cache images
            set_info: Optional set info for TCG-Set scopes
        
        Returns:
            Card data dict with unified structure or None if not found
        """
        # Check if card has tcg_card sub-object (ExGen format)
        if 'tcg_card' in card and card['tcg_card']:
            return self._fetch_card_image_from_exgen_card(pokemon_id, card, cache_dir)
        
        # Otherwise assume TCG-Set format (card IS the TCG card)
        elif 'localId' in card and set_info:
            return self._fetch_card_image_from_tcg_set_card(pokemon_id, card, cache_dir, set_info)
        
        # Pokedex format (has image_url from PokeAPI)
        elif 'image_url' in card:
            return self._fetch_card_image_from_pokedex_card(pokemon_id, card, cache_dir)
        
        else:
            # Debug: Show why we're rejecting this card
            has_tcg_card = 'tcg_card' in card
            has_local_id = 'localId' in card
            has_set_info = set_info is not None
            logger.warning(f"Unknown card format for Pokemon ID {pokemon_id} (tcg_card={has_tcg_card}, localId={has_local_id}, set_info={has_set_info})")
            return None
    
    def _fetch_card_image_from_exgen_card(self, pokemon_id: int, card: Dict, cache_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Fetch card image for a Pokemon using its card data from the scope.
        
        Args:
            pokemon_id: National Pokedex ID
            card: Card data from the scope (with tcg_card)
            cache_dir: Directory to cache images
        
        Returns:
            Card data dict or None if not found
        """
        try:
            # Get TCG card data from the scope card
            tcg_data = card.get('tcg_card', {})
            if not tcg_data:
                logger.warning(f"No TCG card data for Pokemon ID {pokemon_id}")
                return None
            
            card_id = tcg_data.get('id')
            if not card_id:
                logger.warning(f"No card ID for Pokemon ID {pokemon_id}")
                return None
            
            # Build image URL from card ID
            # Format: sv03.5-003 -> https://assets.tcgdex.net/en/sv/sv03.5/003/high.png
            parts = card_id.split('-')
            if len(parts) != 2:
                logger.warning(f"Unexpected card ID format: {card_id}")
                return None
            
            set_id = parts[0]
            local_id = parts[1]
            
            # Determine series from set_id
            series = self._get_series_from_set_id(set_id)
            
            image_url = f"https://assets.tcgdex.net/en/{series}/{set_id}/{local_id}/high.png"
            
            # Get Pokemon name
            pokemon_name = card.get('name', {}).get('en', 'Unknown')
            
            # Cache the image
            cache_file = cache_dir / f"pokemon_{pokemon_id}_{card_id.replace('/', '_')}.png"
            if not self._download_and_cache_image(image_url, cache_file):
                logger.warning(f"Failed to cache card image for Pokemon {pokemon_id}")
                return None
            
            # Return card data
            return {
                'pokemon_id': pokemon_id,
                'pokemon_name': pokemon_name,
                'card_id': card_id,
                'set_name': tcg_data.get('set', {}).get('name', 'Unknown'),
                'image_url': image_url,
                'local_image_path': str(cache_file),
                'rarity': tcg_data.get('rarity'),
                'hp': tcg_data.get('hp'),
            }
            
        except Exception as e:
            logger.error(f"Unexpected error fetching card image for Pokemon {pokemon_id}: {e}")
            return None
    
    def _fetch_card_image_from_tcg_set_card(self, pokemon_id: int, card: Dict, cache_dir: Path, set_info: Dict) -> Optional[Dict[str, Any]]:
        """
        Fetch card image for a Pokemon from a TCG-Set card (ME*, SV* scopes).
        
        Args:
            pokemon_id: National Pokedex ID
            card: Card data (IS the TCG card, has localId)
            cache_dir: Directory to cache images
            set_info: Set information from context
        
        Returns:
            Card data dict or None if not found
        """
        try:
            # Get card identifiers
            local_id = card.get('localId')
            if not local_id:
                logger.warning(f"No localId for Pokemon ID {pokemon_id}")
                return None
            
            # Get set info
            set_id = set_info.get('id')
            set_name = set_info.get('name', 'Unknown')
            series_id = set_info.get('serie', 'base')
            
            if not set_id:
                logger.warning(f"No set_id in set_info for Pokemon ID {pokemon_id}")
                return None
            
            # A release scope may use a collector-facing code such as 30C
            # while TCGdex uses a different set ID such as 30th.  Preserve
            # the card's real upstream identity for images and provenance.
            card_id = self._card_identifier(card, set_info)
            if not card_id:
                logger.warning(f"No stable card ID for Pokemon ID {pokemon_id}")
                return None
            suffix = f"-{local_id}"
            source_set_id = (
                card_id[:-len(suffix)]
                if card_id.endswith(suffix)
                else set_id
            )
            
            # Build image URL
            # Format: https://assets.tcgdex.net/en/{series}/{set_id}/{localId}/high.png
            image_url = f"https://assets.tcgdex.net/en/{series_id}/{source_set_id}/{local_id}/high.png"
            
            # Get Pokemon name
            pokemon_name = card.get('name', {})
            if isinstance(pokemon_name, dict):
                pokemon_name = pokemon_name.get('en', 'Unknown')
            else:
                pokemon_name = str(pokemon_name) if pokemon_name else 'Unknown'
            
            # Cache the image
            cache_file = cache_dir / f"pokemon_{pokemon_id}_{card_id.replace('/', '_')}.png"
            if not self._download_and_cache_image(image_url, cache_file):
                logger.warning(f"Failed to cache TCG-Set card image for Pokemon {pokemon_id}, trying PokeAPI fallback")
                # Cover fallback uses the exact poster subject.  A special form
                # must never be replaced with base-species artwork.
                fallback_subject = poster_subject_from_card(card)
                fallback_url = fallback_subject['image_url']
                artwork_id = fallback_subject['official_artwork_id']
                fallback_cache = cache_dir / (
                    f"pokemon_{pokemon_id}_artwork_{artwork_id}_"
                    f"{card_id.replace('/', '_')}_fallback.png"
                )
                if self._download_and_cache_image(fallback_url, fallback_cache):
                    cache_file = fallback_cache
                    image_url = fallback_url
                    logger.info(f"Using PokeAPI fallback artwork for Pokemon {pokemon_id}")
                else:
                    logger.warning(f"Both TCG and PokeAPI fallback failed for Pokemon {pokemon_id}")
                    return None
            
            # Return card data
            return {
                'pokemon_id': pokemon_id,
                'pokemon_name': pokemon_name,
                'card_id': card_id,
                'set_name': set_name,
                'image_url': image_url,
                'local_image_path': str(cache_file),
                'rarity': card.get('rarity'),
                'hp': card.get('hp'),
            }
            
        except Exception as e:
            logger.error(f"Unexpected error fetching TCG-Set card image for Pokemon {pokemon_id}: {e}")
            return None    
    def _fetch_card_image_from_pokedex_card(self, pokemon_id: int, card: Dict, cache_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Fetch card image for a Pokemon from Pokedex (uses PokeAPI artwork).
        
        Args:
            pokemon_id: National Pokedex ID
            card: Card data from Pokedex
            cache_dir: Directory to cache images
        
        Returns:
            Card data dict or None if not found
        """
        try:
            # Get image URL from PokeAPI
            image_url = card.get('image_url')
            if not image_url:
                logger.warning(f"No image_url for Pokemon ID {pokemon_id}")
                return None
            
            # Get Pokemon name
            pokemon_name = card.get('name', {})
            if isinstance(pokemon_name, dict):
                pokemon_name = pokemon_name.get('en', 'Unknown')
            else:
                pokemon_name = str(pokemon_name) if pokemon_name else 'Unknown'
            
            # Use pokemon_id as cache file identifier (no card_id for Pokedex)
            cache_file = cache_dir / f"pokemon_{pokemon_id}_pokedex.png"
            if not self._download_and_cache_image(image_url, cache_file):
                logger.warning(f"Failed to cache Pokedex image for Pokemon {pokemon_id}")
                return None
            
            # Return card data
            return {
                'pokemon_id': pokemon_id,
                'pokemon_name': pokemon_name,
                'card_id': f"pokedex-{pokemon_id}",
                'set_name': 'National Pokédex',
                'image_url': image_url,
                'local_image_path': str(cache_file),
                'rarity': None,
                'hp': None,
            }
            
        except Exception as e:
            logger.error(f"Unexpected error fetching Pokedex image for Pokemon {pokemon_id}: {e}")
            return None
