"""
Shared utility functions for PDF generators.

Consolidates common functionality used across pdf_generator.py and variant_pdf_generator.py.
"""

import json
import logging
import re
from pathlib import Path
from typing import List
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics

logger = logging.getLogger(__name__)


class TextRenderer:
    """Unified text rendering utilities for handling special characters."""

    @staticmethod
    def fit_name_lines(
        text: str,
        font_name: str,
        normal_size: float,
        minimum_size: float,
        max_width: float,
    ) -> tuple[List[str], float]:
        """Fit a card title into one or two bounded lines.

        The largest usable font size wins.  At each size a single line is
        preferred; otherwise all whitespace and hyphen boundaries are scored
        deterministically by their widest line and visual imbalance.
        """
        if not isinstance(text, str) or not text.strip():
            raise ValueError("card title must be a non-empty string")
        if minimum_size <= 0 or normal_size < minimum_size:
            raise ValueError("invalid card title font-size bounds")
        if max_width <= 0:
            raise ValueError("card title width must be positive")

        normalized = re.sub(r"\s+", " ", text.strip())
        split_positions = {
            match.end()
            for match in re.finditer(r"\s+", normalized)
        }
        split_positions.update(
            index + 1
            for index, character in enumerate(normalized)
            if character == "-" and index + 1 < len(normalized)
        )

        step = 0.25
        step_count = int(round((normal_size - minimum_size) / step))
        sizes = [normal_size - index * step for index in range(step_count + 1)]
        if not sizes or sizes[-1] > minimum_size:
            sizes.append(minimum_size)

        for size in sizes:
            if pdfmetrics.stringWidth(normalized, font_name, size) <= max_width:
                return [normalized], size

            candidates = []
            for position in sorted(split_positions):
                first = normalized[:position].rstrip()
                second = normalized[position:].lstrip()
                if not first or not second:
                    continue
                widths = (
                    pdfmetrics.stringWidth(first, font_name, size),
                    pdfmetrics.stringWidth(second, font_name, size),
                )
                if max(widths) > max_width:
                    continue
                imbalance = abs(widths[0] - widths[1])
                score = max(widths) + imbalance * 0.25
                candidates.append((score, max(widths), imbalance, first, second))

            if candidates:
                _, _, _, first, second = min(candidates)
                return [first, second], size

        raise ValueError(
            f"card title does not fit within {max_width:.2f} points at "
            f"{minimum_size:.2f} points: {normalized!r}"
        )
    
    @staticmethod
    def draw_name_with_symbol_fallback(canvas_obj, name: str, x: float, width: float, 
                                       y: float, primary_font: str, font_size: float = 8,
                                       text_color: str = "#2D2D2D") -> None:
        """
        Draw text with gender symbol fallback.
        
        If name contains ♂/♀ symbols, renders text parts with primary font and 
        symbols with SongtiBold for better Unicode support.
        
        This is the canonical implementation replacing:
        - card_template._draw_name_with_symbol_fallback
        - pdf_generator._draw_name_with_symbol_fallback
        
        Args:
            canvas_obj: ReportLab canvas object
            name: Text with potential ♂/♀ symbols
            x: X position for centering
            width: Width for centering calculation
            y: Y position
            primary_font: Primary font name (e.g., 'Helvetica-Bold')
            font_size: Font size in points (default 8)
            text_color: Hex color for text (default black)
        """
        # Split name into parts and symbols
        parts: List[tuple] = []
        current_part: str = ""
        
        for char in name:
            if char in '♂♀':
                if current_part:
                    parts.append(('text', current_part))
                    current_part = ""
                parts.append(('symbol', char))
            else:
                current_part += char
        
        if current_part:
            parts.append(('text', current_part))
        
        # Measure total width to center
        total_width = 0
        for part_type, part_text in parts:
            if part_type == 'text':
                total_width += canvas_obj.stringWidth(part_text, primary_font, font_size)
            else:  # symbol
                total_width += canvas_obj.stringWidth(part_text, 'SongtiBold', font_size)
        
        # Draw centered
        start_x = x + width / 2 - total_width / 2
        current_x = start_x
        
        for part_type, part_text in parts:
            if part_type == 'text':
                canvas_obj.setFont(primary_font, font_size)
                canvas_obj.setFillColor(HexColor(text_color))
                canvas_obj.drawString(current_x, y, part_text)
                current_x += canvas_obj.stringWidth(part_text, primary_font, font_size)
            else:  # symbol
                canvas_obj.setFont('SongtiBold', font_size)
                canvas_obj.setFillColor(HexColor(text_color))
                canvas_obj.drawString(current_x, y, part_text)
                current_x += canvas_obj.stringWidth(part_text, 'SongtiBold', font_size)


class TranslationHelper:
    """Helper class for managing translations across PDF generators."""
    
    @staticmethod
    def load_translations(language: str) -> dict:
        """
        Load translations from i18n/translations.json
        
        Args:
            language: Language code (de, en, fr, etc.)
        
        Returns:
            Dictionary with translations for current language
        """
        try:
            trans_file = Path(__file__).parent.parent.parent.parent / 'i18n' / 'translations.json'
            with open(trans_file, 'r', encoding='utf-8') as f:
                all_trans = json.load(f)
            
            # Return UI translations for the current language, or empty dict if not found
            ui_trans = all_trans.get('ui', {})
            return ui_trans.get(language, {})
        except Exception as e:
            logger.warning(f"Could not load translations: {e}")
            return {}
    
    @staticmethod
    def format_translation(translations: dict, key: str, **kwargs) -> str:
        """
        Get a translated string and format it with provided variables.
        
        Args:
            translations: Dictionary with translations for current language
            key: Translation key (e.g., 'variant_species')
            **kwargs: Variables to format into the string
        
        Returns:
            Formatted translation or key if not found
        """
        text = translations.get(key, key)
        
        # Simple template replacement
        for var_name, var_value in kwargs.items():
            text = text.replace(f'{{{{{var_name}}}}}', str(var_value))
        
        return text


class RendererInitializer:
    """
    Utility for initializing rendering components in PDF generators.
    
    Consolidates common renderer initialization patterns from PokedexGenerator 
    and VariantPDFGenerator to reduce code duplication.
    """
    
    @staticmethod
    def initialize_renderers(language: str, image_cache=None, variant_data: dict = None, type_translations: dict = None, card_template: str = None, cover_template: str = None):
        """
        Initialize standard rendering components for PDF generation.
        
        Centralizes the initialization of CardRenderer, PageRenderer, and 
        CoverRenderer used by both Pokédex and Variant generators.
        
        Args:
            language: Language code (de, en, fr, etc.)
            image_cache: Optional image cache for loading Pokémon images
            variant_data: Optional variant data dict for variant-specific initialization
            type_translations: Optional type translations dict from API
            card_template: Optional SVG template for card rendering
            cover_template: Optional SVG template for cover rendering
        
        Returns:
            Tuple of (card_renderer, page_renderer, cover_renderer)
        """
        from .rendering.card_renderer import CardRenderer
        from .rendering.page_renderer import PageRenderer
        from .rendering.cover_renderer import CoverRenderer
        
        # Initialize CardRenderer with optional variant parameters
        if variant_data:
            card_renderer = CardRenderer(
                language=language,
                image_cache=image_cache,
                variant=variant_data.get('variant_type'),
                variant_data=variant_data,
                type_translations=type_translations,
                card_template=card_template
            )
        else:
            card_renderer = CardRenderer(
                language=language,
                image_cache=image_cache,
                type_translations=type_translations,
                card_template=card_template
            )
        
        # Initialize common renderers
        page_renderer = PageRenderer()
        cover_renderer = CoverRenderer(language=language, image_cache=image_cache, cover_template=cover_template)
        
        if card_template:
            logger.info(f"Renderers initialized for language: {language} with template: {card_template}")
        else:
            logger.info(f"Renderers initialized for language: {language}")
        
        return card_renderer, page_renderer, cover_renderer
