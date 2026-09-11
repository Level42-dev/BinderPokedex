"""
Enrich TCG Cards with Multilingual Names and Set Metadata from TCGdex API

Fetches set data in all supported languages (9 API calls total) and enriches:
- Card names with translations (name_{lang} fields)
- Set names in all languages (set_names dict)

Much more efficient than fetching individual cards.

Pipeline: fetch_tcgdex_set → THIS → enrich_tcg_cards_from_pokedex → transform
"""

import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import time
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from steps.base import BaseStep, PipelineContext
from lib.tcgdex_client import TCGdexClient
from lib.tcg_card_overrides import (
    apply_tcg_card_overrides,
    load_tcg_card_overrides,
)

logger = logging.getLogger(__name__)


class EnrichTCGNamesMultilingualStep(BaseStep):
    """
    Enrich TCG card names and set metadata with multilingual data from TCGdex.
    
    Fetches the complete set in each language (9 API calls) and:
    - Matches cards by localId for name translations
    - Extracts set names from each language version
    
    Much more efficient than individual card fetching.
    """
    
    # Supported languages (matching i18n/languages.json)
    LANGUAGES = [
        'de',
        'en',
        'fr',
        'es',
        'it',
        'ja',
        'ko',
        'zh_hans',
        'zh_hant',
    ]
    
    def execute(self, context: PipelineContext, params: Dict[str, Any]) -> PipelineContext:
        """
        Execute the multilingual name enrichment.
        
        Required params:
            - set_id: TCG set ID (e.g., "me01")
        
        Reads from context.data['tcg_set_source']
        Writes enriched data back to context.data['tcg_set_source']
        """
        set_id = params.get('set_id')
        if not set_id:
            raise ValueError("set_id parameter is required")
        
        logger.info(f"🌍 Enriching card names with multilingual data from TCGdex")
        logger.info(f"📦 Set: {set_id}")
        
        # Load source data from context
        data = context.data.get('tcg_set_source')
        if not data:
            raise ValueError("No TCG set data found in context. Make sure fetch_tcgdex_set ran before this step.")
        
        cards = data.get('cards', [])
        logger.info(f"📋 Processing {len(cards)} cards")
        
        # Fetch set data in all languages
        logger.info(f"🌐 Fetching set in {len(self.LANGUAGES)} languages...")
        multilingual_names, set_names, logo_urls, available_languages = self._fetch_multilingual_names(set_id)
        
        # Enrich cards with multilingual names
        enriched_cards = self._enrich_cards(cards, multilingual_names)
        
        # Log language availability
        unavailable = sorted(set(self.LANGUAGES) - set(available_languages))
        if unavailable:
            logger.warning(f"⚠️  Languages not available for this set: {', '.join(unavailable)}")
        logger.info(f"✅ Available languages: {', '.join(sorted(available_languages))}")
        
        logger.info(f"✅ Enriched all cards with {len(self.LANGUAGES)} languages")
        
        # Update data in context
        data['cards'] = enriched_cards
        data['set_names'] = set_names
        data['logo_urls'] = logo_urls
        data['available_languages'] = available_languages
        overrides_path = (
            Path(__file__).resolve().parents[3]
            / 'enrichments'
            / 'tcg_card_overrides.json'
        )
        data = apply_tcg_card_overrides(
            data,
            load_tcg_card_overrides(overrides_path),
        )
        context.data['tcg_set_source'] = data
        
        return context
    
    def _fetch_multilingual_names(self, set_id: str) -> tuple[Dict[str, Dict[str, str]], Dict[str, str], Dict[str, str], List[str]]:
        """
        Fetch set data in all languages and build name index.
        
        Returns:
            Tuple of (names_by_card, set_names, logo_urls, available_languages)
            - names_by_card: Dict mapping localId -> {lang: name}
            - set_names: Dict mapping language -> set name
            - logo_urls: Dict mapping language -> logo URL
            - available_languages: List of successfully fetched language codes
        """
        names_by_card = {}
        set_names = {}
        logo_urls = {}
        available_languages = []
        
        start_time = time.time()
        
        for i, lang in enumerate(self.LANGUAGES, 1):
            # Map language codes (Python uses underscore, TCGdex uses hyphen)
            api_lang = 'zh-Hans' if lang == 'zh_hans' else 'zh-Hant' if lang == 'zh_hant' else lang
            
            logger.info(f"  [{i}/{len(self.LANGUAGES)}] Fetching {api_lang}...")
            
            try:
                # Create client for this language
                client = TCGdexClient(language=api_lang)
                
                set_data = client.get_set(set_id)
                if not set_data:
                    logger.warning(f"⚠️  No data for {api_lang}, skipping")
                    continue
                
                cards = set_data.get('cards', [])
                set_name = set_data.get('name', '')
                logo_url = set_data.get('logo', '')
                logger.info(f"     ✓ Got {len(cards)} cards in {api_lang}")
                
                # Track this language as available
                available_languages.append(lang)
                
                # Store set name and logo URL
                storage_lang = 'zh_hans' if api_lang == 'zh-Hans' else 'zh_hant' if api_lang == 'zh-Hant' else lang
                if set_name:
                    set_names[storage_lang] = set_name
                if logo_url:
                    # Ensure logo URL has .png extension
                    if not logo_url.endswith('.png'):
                        logo_url += '.png'
                    logo_urls[storage_lang] = logo_url
                
                # Index cards by localId
                for card in cards:
                    local_id = card.get('localId', '')
                    name = card.get('name', '')
                    
                    if local_id and name:
                        if local_id not in names_by_card:
                            names_by_card[local_id] = {}
                        
                        # Normalize language code for storage
                        storage_lang = 'zh_hans' if api_lang == 'zh-Hans' else 'zh_hant' if api_lang == 'zh-Hant' else lang
                        names_by_card[local_id][storage_lang] = name
                
            except Exception as e:
                logger.warning(f"⚠️  Error fetching {api_lang}: {e}")
                continue
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Fetched all languages in {elapsed:.1f}s ({len(self.LANGUAGES)} API calls)")
        
        # If no logo URLs were found, check for local fallback logo
        if not logo_urls:
            local_logo = self._check_local_logo(set_id)
            if local_logo:
                logger.info(f"📎 Using local fallback logo: {local_logo}")
                # Add local logo for all available languages
                for lang in available_languages:
                    logo_urls[lang] = local_logo
        # If we have logo URLs but not for all available languages, try to generate them
        elif len(logo_urls) < len(available_languages):
            logo_urls = self._generate_missing_logo_urls(logo_urls, available_languages)
        
        return names_by_card, set_names, logo_urls, available_languages
    
    def _generate_missing_logo_urls(self, logo_urls: Dict[str, str], 
                                     available_languages: List[str]) -> Dict[str, str]:
        """
        Generate logo URLs for missing languages by replacing language code in existing URL.
        Validates each URL with a HEAD request and falls back to English if unavailable.
        
        For example, if we have 'it': 'https://assets.tcgdex.net/it/me/me02.5/logo.png',
        we can generate 'de': 'https://assets.tcgdex.net/de/me/me02.5/logo.png'.
        
        Args:
            logo_urls: Dict of existing language -> logo URL mappings
            available_languages: List of all available language codes
        
        Returns:
            Updated logo_urls dict with validated URLs for missing languages
        """
        if not logo_urls:
            return logo_urls
        
        # Take the first available logo URL as template
        template_lang = list(logo_urls.keys())[0]
        template_url = logo_urls[template_lang]
        
        logger.info(f"🔧 Generating missing logo URLs from template ({template_lang}): {template_url}")
        
        # Try to find English URL as fallback (either existing or generated)
        fallback_url = None
        if 'en' in logo_urls:
            fallback_url = logo_urls['en']
        else:
            # Generate English URL as potential fallback
            fallback_url = template_url.replace(f'/{template_lang}/', '/en/')
            # Validate English URL
            if self._validate_url(fallback_url):
                logger.info(f"   ℹ️  Using English as fallback: {fallback_url}")
            else:
                fallback_url = None  # English doesn't exist either
        
        generated_count = 0
        fallback_count = 0
        
        for lang in available_languages:
            if lang not in logo_urls:
                # Replace language code in URL (e.g., /it/ -> /de/)
                generated_url = template_url.replace(f'/{template_lang}/', f'/{lang}/')
                
                # Validate URL with HEAD request
                if self._validate_url(generated_url):
                    logo_urls[lang] = generated_url
                    logger.info(f"   ✓ Validated {lang}: {generated_url}")
                    generated_count += 1
                elif fallback_url and lang != 'en':
                    # Use English as fallback
                    logo_urls[lang] = fallback_url
                    logger.info(f"   → Fallback {lang}: {fallback_url} (404 for lang-specific URL)")
                    fallback_count += 1
                else:
                    logger.warning(f"   ✗ Skipped {lang}: URL not available (404)")
        
        if generated_count > 0:
            logger.info(f"✅ Generated {generated_count} logo URLs")
        if fallback_count > 0:
            logger.info(f"📎 Used English fallback for {fallback_count} languages")
        
        return logo_urls
    
    def _check_local_logo(self, set_id: str) -> str:
        """
        Check if a local fallback logo exists for this set.
        
        Checks for logos in this order:
        1. images/logos/{set_id}/default.png
        2. images/logos/promo/default.png (for promo sets like svp, swsh, etc.)
        
        Args:
            set_id: Set ID (e.g., 'svp', 'me02.5')
        
        Returns:
            Relative path to logo file if found, empty string otherwise
        """
        from pathlib import Path
        
        # Get project root (4 levels up from this file)
        project_root = Path(__file__).parent.parent.parent.parent
        
        # Try set-specific logo first
        set_logo = project_root / "images" / "logos" / set_id / "default.png"
        if set_logo.exists():
            # Return relative path
            return f"images/logos/{set_id}/default.png"
        
        # Try promo logo for promo-style sets (svp, swsh, dp, etc.)
        promo_logo = project_root / "images" / "logos" / "promo" / "default.png"
        if promo_logo.exists():
            return "images/logos/promo/default.png"
        
        return ""
    
    def _validate_url(self, url: str) -> bool:
        """
        Check if a URL exists by making a HEAD request.
        
        Args:
            url: URL to validate
        
        Returns:
            True if URL returns 200, False otherwise
        """
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"URL validation failed for {url}: {e}")
            return False
    
    def _enrich_cards(self, cards: List[Dict[str, Any]], 
                     multilingual_names: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Enrich cards with multilingual names.
        
        Args:
            cards: List of card dicts with English names
            multilingual_names: Dict mapping localId -> {lang: name}
        
        Returns:
            Enriched cards with name_XX fields
        """
        enriched = []
        cards_with_names = 0
        cards_missing_names = 0
        
        for card in cards:
            enriched_card = card.copy()
            local_id = card.get('localId', '')
            enriched_card['printed_number'] = card.get(
                'printed_number',
                local_id,
            )
            
            if local_id in multilingual_names:
                # Add all available language names
                for lang, name in multilingual_names[local_id].items():
                    enriched_card[f'name_{lang}'] = name
                enriched_card['available_languages'] = [
                    lang
                    for lang in self.LANGUAGES
                    if lang in multilingual_names[local_id]
                ]
                cards_with_names += 1
            else:
                # The master source is English. Do not present it as a native
                # translation in languages where this card was not observed.
                english_name = card.get('name', '')
                enriched_card['name_en'] = english_name
                enriched_card['available_languages'] = ['en']
                cards_missing_names += 1
                logger.warning(f"⚠️  No multilingual names for card {local_id}")
            
            enriched.append(enriched_card)
        
        logger.info(f"📊 Enrichment summary:")
        logger.info(f"   - Cards with multilingual names: {cards_with_names}")
        logger.info(f"   - Cards using fallback: {cards_missing_names}")
        
        return enriched
