"""
Fetch TCG Set Cards from TCGdex API

Fetches all cards from a specific TCG set (e.g., me01, me02) from TCGdex API
and stores them in source format for PDF generation.

This differs from the variant-based fetchers (ExGen1, ExGen2, etc.) which combine
cards from multiple sets. This fetcher retrieves a single, complete set.

Example sets:
- me01: Mega Evolution (Mega-Entwicklung)
- me02: Phantasmal Flames (Fatale Flammen)
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from steps.base import BaseStep, PipelineContext
from lib.tcgdex_client import TCGdexClient

logger = logging.getLogger(__name__)


class FetchTCGdexSetStep(BaseStep):
    """
    Fetches all cards from a specific TCG set from TCGdex API.
    
    Output format (source):
    {
        "set_info": {
            "id": "me01",
            "name": "Mega Evolution",
            "release_date": "2025-09-26",
            "serie": "me",
            "serie_name": "Mega Evolution",
            "card_count": {
                "total": 188,
                "official": 132
            },
            "logo": "https://assets.tcgdex.net/en/me/me01/logo",
            "symbol": "https://assets.tcgdex.net/univ/me/me01/symbol"
        },
        "cards": [
            {
                "id": "me01-001",
                "localId": "001",
                "name": "Bulbasaur",
                "image": "https://assets.tcgdex.net/en/me/me01/001",
                "category": "Pokémon",
                "types": ["Grass"],
                "dexId": [1]
            },
            ...
        ],
        "metadata": {
            "total_cards": 188,
            "set_id": "me01",
            "date_fetched": "2026-01-30T12:00:00Z",
            "source": "TCGdex API v2",
            "language": "en"
        }
    }
    
    Note: Always fetches in English. Other languages will be enriched from Pokedex.
    """
    
    def execute(self, context: PipelineContext, params: Dict[str, Any]) -> PipelineContext:
        """
        Execute the fetch step.
        
        Required params:
            - set_id: TCG set ID (e.g., "me01")
        
        Optional params:
            - language: Language code (default: "de")
            - output_file: Output path (default: "data/source/{set_id}.json")
        
        Steps:
        1. Initialize TCGdex client
        2. Fetch set data (including card list)
        3. Fetch English names for cross-reference
        4. Store in source format
        """
        set_id = params.get('set_id')
        if not set_id:
            raise ValueError("set_id parameter is required")
        
        # Always fetch in English (master language)
        # Other languages will be enriched from Pokedex
        language = 'en'
        
        # Make path absolute relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        output_path = params.get('output_file', f'data/source/{set_id}.json')
        if not Path(output_path).is_absolute():
            output_path = project_root / output_path
        else:
            output_path = Path(output_path)
        
        logger.info(f"🎴 Fetching TCG set: {set_id} (English - master language)")
        
        # Fetch set data (card list with minimal info)
        client = TCGdexClient(language=language)
        set_data = self._fetch_set(client, set_id)
        
        if not set_data:
            raise RuntimeError(f"Failed to fetch set {set_id}")
        
        # Fetch complete data for each card (includes category, types, dexId)
        logger.info(f"🔍 Fetching complete data for {len(set_data.get('cards', []))} cards...")
        cards_complete = self._fetch_complete_cards(client, set_data.get('cards', []))
        
        # Create output data structure
        output_data = self._create_output_data(set_data, cards_complete, set_id, language)
        
        # Add metadata
        output_data['metadata'] = {
            'total_cards': len(output_data['cards']),
            'set_id': set_id,
            'date_fetched': datetime.utcnow().isoformat() + 'Z',
            'source': 'TCGdex API v2',
            'language': language
        }
        
        # Save to source
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved {len(output_data['cards'])} cards to {output_path}")
        
        # Store in context
        context.data['tcg_set_source'] = output_data
        
        return context
    
    def _fetch_set(self, client: TCGdexClient, set_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch set data from TCGdex API.
        
        Args:
            client: TCGdex client instance
            set_id: Set ID
            
        Returns:
            Set data with card list or None
        """
        logger.info(f"🔍 Fetching set {set_id}...")
        set_data = client.get_set(set_id)
        
        if not set_data:
            logger.error(f"❌ Failed to fetch set {set_id}")
            return None
        
        logger.info(f"✅ Found {len(set_data.get('cards', []))} cards in set")
        return set_data
    
    def _fetch_complete_cards(self, client: TCGdexClient, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fetch complete card data for each card in the list.
        
        The set endpoint only returns minimal card info (id, localId, name, image).
        This method fetches full card details including category, HP, types, etc.
        
        Args:
            client: TCGdex client instance
            cards: List of card brief objects from set endpoint
            
        Returns:
            List of complete card objects with category field
        """
        import time
        
        complete_cards = []
        missing_card_ids = []
        total = len(cards)
        start_time = time.time()
        
        # Track categories for summary
        category_counts = {}
        
        for i, card in enumerate(cards, 1):
            card_id = card['id']
            
            # Show progress (update same line)
            elapsed = time.time() - start_time
            avg_time = elapsed / i if i > 0 else 0
            remaining = (total - i) * avg_time
            
            # Use \r to overwrite the same line, flush to ensure immediate output
            sys.stdout.write(f"\r  📥 Progress: {i}/{total} cards ({i*100//total}%) - ETA: {remaining:.0f}s")
            sys.stdout.flush()
            
            complete_card = client.get_card(card_id)
            if complete_card:
                complete_cards.append(complete_card)
                # Track category
                category = complete_card.get('category', 'Unknown')
                category_counts[category] = category_counts.get(category, 0) + 1
            else:
                # Clear progress line for warning
                sys.stdout.write("\r" + " " * 80 + "\r")
                logger.error(
                    f"❌ Failed to fetch complete data for {card_id}"
                )
                missing_card_ids.append(card_id)
        
        # Clear progress line and show summary
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        elapsed = time.time() - start_time
        logger.info(f"✅ Fetched {len(complete_cards)} cards in {elapsed:.1f}s")
        logger.info(f"📊 Categories found:")
        for category, count in sorted(category_counts.items()):
            logger.info(f"   - {category}: {count} cards")

        if missing_card_ids:
            raise RuntimeError(
                "Failed to fetch complete card data for: "
                + ", ".join(missing_card_ids)
            )
        
        return complete_cards
    
    def _create_output_data(self,
                           set_data: Dict[str, Any],
                           cards_complete: List[Dict[str, Any]],
                           set_id: str,
                           language: str) -> Dict[str, Any]:
        """
        Create output data structure from fetched cards.
        
        Args:
            set_data: Set metadata
            cards_complete: Complete card data in English
            set_id: Set ID
            language: Language code (always 'en')
            
        Returns:
            Output data structure for enrichment step
        """
        # Build set info
        set_info = {
            'id': set_data['id'],
            'name': set_data['name'],
            'release_date': set_data.get('releaseDate', ''),
            'card_count': set_data.get('cardCount', {}),
            'logo': set_data.get('logo', ''),
            'symbol': set_data.get('symbol', '')
        }
        
        # Fix logo URL: TCGdex returns without .png extension, add it
        if set_info['logo'] and not set_info['logo'].endswith('.png'):
            set_info['logo'] += '.png'
        
        # Add serie info if available
        if 'serie' in set_data:
            serie = set_data['serie']
            if isinstance(serie, dict):
                set_info['serie'] = serie.get('id', '')
                set_info['serie_name'] = serie.get('name', '')
        
        # Process cards - extract key fields including dexId and trainerType
        cards = []
        for card in cards_complete:
            card_entry = {
                'id': card['id'],
                'localId': card.get('localId', ''),
                'name': card.get('name', ''),  # English name
                'image': card.get('image', ''),
                'category': card.get('category', ''),
                'types': card.get('types', []),
                'dexId': card.get('dexId', []),  # National Dex IDs - key for mapping!
                'trainerType': card.get('trainerType', '')  # Supporter, Item, Stadium, Tool
            }
            cards.append(card_entry)
        
        # Sort by localId
        cards.sort(key=lambda c: int(c['localId']) if c['localId'].isdigit() else 999999)
        
        return {
            'set_info': set_info,
            'cards': cards
        }
