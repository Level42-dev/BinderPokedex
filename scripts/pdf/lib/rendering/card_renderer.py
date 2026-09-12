"""
Card Renderer - Unified card rendering for all PDF types

Consolidates card rendering logic from pdf_generator.py and card_template.py
into a single, unified implementation. This eliminates code duplication and ensures
consistent card rendering across Generation PDFs and Variant PDFs.

Features:
- Unified card rendering with type-based header colors
- Pokémon name and number rendering
- Image area handling
- Language-aware font selection
- Type translation support
- Gender symbol fallback rendering
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Optional

from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

try:
    from ..fonts import FontManager
    from ..constants import CARD_WIDTH, CARD_HEIGHT, TYPE_COLORS
    from ..utils import TextRenderer
    from .translation_loader import TranslationLoader
    from .logo_renderer import LogoRenderer
    from .template_loader import TemplateLoader, CardTemplateRenderer
except ImportError:
    # Fallback for direct imports
    from fonts import FontManager
    from constants import CARD_WIDTH, CARD_HEIGHT, TYPE_COLORS
    from utils import TextRenderer
    from rendering.translation_loader import TranslationLoader
    from rendering.logo_renderer import LogoRenderer
    from rendering.template_loader import TemplateLoader, CardTemplateRenderer

logger: logging.Logger = logging.getLogger(__name__)


class CardStyle:
    """Unified card styling constants."""
    
    # Pokémon type color mapping - NOW IMPORTED FROM constants.py (canonical source)
    TYPE_COLORS: Dict[str, str] = TYPE_COLORS
    
    # Card dimensions
    CARD_WIDTH: float = CARD_WIDTH
    CARD_HEIGHT: float = CARD_HEIGHT
    HEADER_HEIGHT: float = 12 * mm
    IMAGE_PADDING: float = 2 * mm
    
    # Colors
    CARD_BORDER_COLOR = '#CCCCCC'
    CARD_BACKGROUND = '#FFFFFF'
    TEXT_DARK = '#2D2D2D'
    TEXT_GRAY = '#5D5D5D'
    TEXT_LIGHT_GRAY = '#999999'
    
    # Fonts - Increased sizes for better readability on printed A4
    FONT_SIZE_NAME = 11          # Increased from 8
    FONT_SIZE_NAME_MIN = 8
    NAME_HORIZONTAL_PADDING = 3 * mm
    NAME_LINE_LEADING = 0.95
    FONT_SIZE_TYPE = 6           # Increased from 5
    FONT_SIZE_ID = 16
    FONT_SIZE_SUBTITLE = 7       # Increased from 4


class CardRenderer:
    """Unified renderer for Pokémon cards."""
    
    def __init__(self, language: str = 'en', image_cache=None, variant: str = None, variant_data: dict = None, type_translations: dict = None, card_template: str = None) -> None:
        """
        Initialize card renderer.
        
        Args:
            language: Language code for text rendering (e.g., 'en', 'de', 'fr')
            image_cache: Optional image cache for loading Pokémon images
            variant: Optional variant ID (ex_gen1, ex_gen2, etc.) for variant-specific rendering
            variant_data: Optional variant data dict for accessing variant-level config (suffix, etc.)
            type_translations: Optional dict with type translations from data (e.g., from Pokedex.json)
            card_template: Optional name of SVG template to use (e.g., 'classic'). If None, uses legacy rendering.
        """
        self.language: str = language
        self.image_cache = image_cache
        self.variant: str = variant
        self.variant_data = variant_data or {}
        self.style = CardStyle()
        
        # Load type translations - prefer passed translations, fallback to i18n files
        if type_translations:
            self.type_translations: Dict[str, str] = type_translations
        else:
            self.type_translations: Dict[str, str] = TranslationLoader.load_types(language)
        
        # Template-based rendering (optional)
        self.template_renderer: Optional[CardTemplateRenderer] = None
        if card_template:
            try:
                self.template_renderer = CardTemplateRenderer(card_template)
                logger.info(f"Using SVG template: {card_template}")
            except Exception as e:
                logger.warning(f"Failed to load template '{card_template}': {e}. Falling back to legacy rendering.")
                self.template_renderer = None
    
    @staticmethod
    def _darken_color(hex_color: str, factor: float = 0.6) -> str:
        """Darken a hex color by multiplying RGB values by factor."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _draw_card_name_with_ex_logo(self, canvas_obj, name: str, x: float, card_width: float,
                                     name_y: float, font_name: str, font_size: float = None,
                                     logo_type: str = 'ex') -> None:
        """
        Draw card name with EX or special variant logos.
        
        Handles Gen1 'ex' suffix, Gen2 'M EX' and 'EX' variants, Gen3 '[EX_NEW]' and '[EX_TERA]' tokens.
        
        Delegates to LogoRenderer for unified logo handling.
        
        Args:
            canvas_obj: ReportLab canvas
            name: Full name with suffix/prefix
            x: Card x position
            card_width: Card width
            name_y: Y position for name
            font_name: Font to use
            logo_type: Type of logo ('ex', 'm_ex', 'ex_new', 'ex_tera')
        """
        if font_size is None:
            font_size = self.style.FONT_SIZE_NAME
        canvas_obj.setFont(font_name, font_size)
        canvas_obj.setFillColor(HexColor(self.style.TEXT_DARK))
        
        # Use unified LogoRenderer with card context
        LogoRenderer.draw_text_with_logos(
            canvas_obj,
            name,
            x + card_width / 2,
            name_y,
            font_name,
            font_size,
            context='card',
            text_color=self.style.TEXT_DARK,
            language=self.language,
        )

    def _draw_fitted_name_line(
        self,
        canvas_obj,
        name: str,
        x: float,
        card_width: float,
        name_y: float,
        font_name: str,
        font_size: float,
    ) -> None:
        """Draw one already-fitted title line with special glyph support."""
        if any(
            token in name
            for token in ('[EX_TERA]', '[EX_NEW]', '[M]', '[EX]')
        ):
            self._draw_card_name_with_ex_logo(
                canvas_obj,
                name,
                x,
                card_width,
                name_y,
                font_name,
                font_size=font_size,
            )
        elif ('♂' in name or '♀' in name) and font_name == 'Helvetica-Bold':
            TextRenderer.draw_name_with_symbol_fallback(
                canvas_obj,
                name,
                x,
                card_width,
                name_y,
                font_name,
                font_size,
                self.style.TEXT_DARK,
                symbol_font=FontManager.get_symbol_font_name(),
            )
        else:
            canvas_obj.setFont(font_name, font_size)
            canvas_obj.setFillColor(HexColor(self.style.TEXT_DARK))
            canvas_obj.drawCentredString(x + card_width / 2, name_y, name)

    @staticmethod
    def _format_card_number(pokemon_data: dict) -> Optional[str]:
        """Format the printed identity without inventing a TCG set number."""
        if 'printed_number' in pokemon_data:
            value = pokemon_data['printed_number']
        elif 'localId' in pokemon_data:
            # Legacy TCG snapshots predate ``printed_number`` but still carry
            # their original set-local identity.  Never substitute the
            # renderer's compact section position for such cards.
            value = pokemon_data['localId']
        else:
            value = (
                pokemon_data.get('num')
                or pokemon_data.get('id')
                or pokemon_data.get('section_index')
            )

        if value is None or value == '':
            return None
        if isinstance(value, int):
            return f"#{value:03d}"
        value = str(value)
        return value if value.startswith('#') else f"#{value}"
    
    def render_card(self, canvas_obj, pokemon_data: dict, x: float, y: float,
                   card_width: float = None, card_height: float = None,
                   variant_mode: bool = False, section_prefix: str = None, 
                   section_suffix: str = None) -> None:
        """
        Draw a Pokémon card.
        
        Unified rendering method that handles both Generation PDFs and Variant PDFs.
        
        Args:
            canvas_obj: ReportLab canvas object
            pokemon_data: Dictionary with pokemon info (name, type, image, id, etc.)
            x: X position (top-left)
            y: Y position (top-left)
            card_width: Card width (default: CARD_WIDTH from constants)
            card_height: Card height (default: CARD_HEIGHT from constants)
            variant_mode: If True, uses variant data format (variant_name, trainer, etc.)
            section_prefix: Prefix from section-level data (e.g., "Mega", "Rocket's")
            section_suffix: Suffix from section-level data (e.g., "[EX]", "ex")
        """
        # If template renderer is available, use it instead of legacy rendering
        if self.template_renderer:
            return self.template_renderer.render(
                canvas_obj, 
                pokemon_data, 
                x, 
                y, 
                self.language,
                self.image_cache
            )
        
        # === LEGACY RENDERING (original code) ===
        
        if card_width is None:
            card_width = self.style.CARD_WIDTH
        if card_height is None:
            card_height = self.style.CARD_HEIGHT
        
        header_height: float = self.style.HEADER_HEIGHT
        
        # ===== HEADER SETUP =====
        # Get primary type and its color
        types = pokemon_data.get('types', [])
        if not types and pokemon_data.get('type1'):
            types = [pokemon_data.get('type1')]
        
        # For special cards (Trainer, Energy) without types, use 'Colorless' as default
        if not types:
            card_type = pokemon_data.get('type', '')
            if card_type in ['trainer', 'energy']:
                types = ['Colorless']
            else:
                raise ValueError(
                    f"Pokémon '{pokemon_data.get('name', 'Unknown')}' "
                    f"(ID: {pokemon_data.get('id', 'N/A')}) has no types defined"
                )
        
        pokemon_type = types[0]
        header_color = self.style.TYPE_COLORS.get(pokemon_type, self.style.TYPE_COLORS['Normal'])
        
        # ===== DRAW CARD STRUCTURE =====
        
        # Header background with type color (10% opaque)
        canvas_obj.setFillColor(HexColor(header_color), alpha=0.1)
        canvas_obj.rect(x, y + card_height - header_height, card_width, header_height, 
                       fill=True, stroke=False)
        
        # Card border
        canvas_obj.setLineWidth(0.5)
        canvas_obj.setStrokeColor(HexColor(self.style.CARD_BORDER_COLOR))
        canvas_obj.rect(x, y, card_width, card_height, fill=False, stroke=True)
        
        # ===== TYPE DISPLAY =====
        type_english = types[0]
        
        # Get type translation - handle both dict (from API) and string (fallback) formats
        type_translation_data = self.type_translations.get(type_english, type_english)
        
        if isinstance(type_translation_data, dict):
            # New format: translations are a dict with language codes
            type_translated = type_translation_data.get(self.language, type_english)
        else:
            # Old format: translation is already a string
            type_translated = type_translation_data
        
        # Debug: Check if translation exists
        if not type_translated:
            logger.warning(f"No type translation for '{type_english}' in language '{self.language}'")
            type_translated = type_english
        
        try:
            type_font: str = FontManager.get_font_name(self.language, bold=False)
            canvas_obj.setFont(type_font, self.style.FONT_SIZE_TYPE)
        except Exception:
            canvas_obj.setFont("Helvetica", self.style.FONT_SIZE_TYPE)
        
        canvas_obj.setFillColor(HexColor(self.style.TEXT_GRAY))
        type_x: float = x + card_width - 3  # Right edge with margin
        # Keep the small type label below the two-line title band.  The image
        # area intentionally leaves a 4 mm gap below the header.
        type_y: float = y + card_height - header_height - 2 * mm
        canvas_obj.drawRightString(type_x, type_y, type_translated)
        
        # ===== NAME RENDERING =====
        if variant_mode:
            # For variant PDFs - construct full variant name
            name: str = self._construct_variant_name(pokemon_data, section_prefix, section_suffix)
        else:
            # For generation PDFs
            # Support both string and multilingual dict format
            name_data = pokemon_data.get('name', 'Unknown')
            if isinstance(name_data, dict):
                # Multilingual format (TCG cards) - fallback to English
                name = name_data.get(self.language, name_data.get('en', 'Unknown'))
            else:
                # String format (Pokedex cards)
                name = name_data
        
        try:
            font_name: str = FontManager.get_font_name(self.language, bold=True)
        except Exception:
            font_name = "Helvetica-Bold"

        safe_name_width = card_width - 2 * self.style.NAME_HORIZONTAL_PADDING
        name_lines, name_font_size = TextRenderer.fit_name_lines(
            name,
            font_name,
            self.style.FONT_SIZE_NAME,
            self.style.FONT_SIZE_NAME_MIN,
            safe_name_width,
        )
        name_y: float = y + card_height - header_height / 2 - 1 * mm
        line_leading = name_font_size * self.style.NAME_LINE_LEADING
        first_line_y = name_y + (line_leading / 2 if len(name_lines) == 2 else 0)
        for line_index, line in enumerate(name_lines):
            self._draw_fitted_name_line(
                canvas_obj,
                line,
                x,
                card_width,
                first_line_y - line_index * line_leading,
                font_name,
                name_font_size,
            )
        
        # ===== IMAGE AREA =====
        image_height: float = card_height - header_height - 4 * mm
        canvas_obj.setFillColor(HexColor(self.style.CARD_BACKGROUND))
        canvas_obj.rect(x, y, card_width, image_height, fill=True, stroke=False)
        
        # Draw the physical card's number.  An explicit null value is a real
        # unnumbered card and must never fall back to its list position.
        poke_num_str = self._format_card_number(pokemon_data)
        if poke_num_str is not None:
            darkened_color: str = self._darken_color(header_color, factor=0.6)
            canvas_obj.setFont("Helvetica-Bold", self.style.FONT_SIZE_ID)
            canvas_obj.setFillColor(HexColor(darkened_color))
            canvas_obj.drawCentredString(
                x + card_width / 2,
                y + 4 * mm,
                poke_num_str,
            )
        
        # ===== IMAGE RENDERING =====
        image_source = pokemon_data.get('image_path') or pokemon_data.get('image_url')
        if image_source and self.image_cache:
            self._draw_image(canvas_obj, pokemon_data, x, y, card_width, image_height)
    
    def _construct_variant_name(self, pokemon_data: dict, section_prefix: str = None, 
                                section_suffix: str = None) -> str:
        """
        Construct translated variant name from pokemon_data.
        
        Fully data-driven approach using section-level prefix/suffix.
        
        Args:
            pokemon_data: Pokemon variant data dict
            section_prefix: Prefix from section data (e.g., "Mega", "Rocket's", "[M]")
            section_suffix: Suffix from section data (e.g., "[EX]", "ex", "[EX_NEW]")
        
        Returns:
            Fully formatted variant name with prefix/suffix
        """
        # Get base name in target language (unified name object structure - required)
        # Fallback to English if language not available
        name_obj = pokemon_data.get('name', {})
        
        # Handle both dict (multilingual) and string (monolingual) name formats
        if isinstance(name_obj, dict):
            base_name = name_obj.get(self.language, name_obj.get('en', 'Unknown'))
        else:
            base_name = str(name_obj) if name_obj else 'Unknown'
        
        # Get pokemon-specific prefix/suffix (can override section defaults)
        pokemon_prefix = pokemon_data.get('prefix', None)
        pokemon_suffix = pokemon_data.get('suffix', None)
        
        # Use pokemon-specific values if present, otherwise use section values
        prefix = pokemon_prefix if pokemon_prefix is not None else (section_prefix or '')
        suffix = pokemon_suffix if pokemon_suffix is not None else (section_suffix or '')
        
        # Build name with prefix and suffix
        name = base_name
        
        # Add prefix (if present)
        if prefix:
            name = f"{prefix} {name}"
        
        # Handle variant_form (delta, x, y)
        variant_form = pokemon_data.get('variant_form', None)
        if variant_form:
            if variant_form == 'delta':
                # Delta Species: add δ symbol to suffix
                if suffix:
                    suffix = f"{suffix} δ"
            elif variant_form in ['x', 'y']:
                # Mega X/Y forms: add X or Y after name, before suffix
                name = f"{name} {variant_form.upper()}"
        
        # Some localized TCG names put the owner after ex ("Zoroark-ex de N").
        # Keep the marker in that position instead of appending a second one.
        # Match a complete marker, never the letters inside a species name.
        if suffix == '[EX_NEW]':
            name, embedded_ex = re.subn(
                r'(?<=\S)[-\s]ex(?=\s|$)',
                ' [EX_NEW]',
                name,
                count=1,
                flags=re.IGNORECASE,
            )
            if embedded_ex:
                suffix = ''

        # Add suffix (if present)
        if suffix:
            name = f"{name} {suffix}"
        
        return name
    
    def _draw_image(self, canvas_obj, pokemon_data: dict, x: float, y: float,
                   card_width: float, image_height: float) -> None:
        """Draw Pokémon image on card."""
        image_source = pokemon_data.get('image_path') or pokemon_data.get('image_url')
        
        if not image_source:
            return
        
        try:
            image_to_render = None
            
            if image_source.startswith(('http://', 'https://')):
                # URL - load from cache or download
                pokemon_id = pokemon_data.get('pokemon_id') or pokemon_data.get('id')
                logger.debug(f"Getting image for #{pokemon_id}...")
                image_data = self.image_cache.get_image(pokemon_id, url=image_source)
                if image_data:
                    logger.debug(f"✓ Got image")
                    image_to_render = image_data
                else:
                    logger.debug(f"✗ Failed to get image data")
            else:
                # Local path
                if Path(image_source).exists():
                    logger.debug(f"Using local path: {image_source}")
                    image_to_render = image_source
            
            if image_to_render:
                logger.debug(f"Drawing image...")
                padding: float = self.style.IMAGE_PADDING
                max_width: float = (card_width - 2 * padding) / 2
                max_height: float = (image_height - 2 * padding) / 2
                
                img_x: float = x + (card_width - max_width) / 2
                img_y: float = y + (image_height - max_height) / 2 + padding
                
                # Use ImageReader for PNG transparency support
                from reportlab.lib.utils import ImageReader
                if isinstance(image_to_render, str):
                    image_to_render = ImageReader(image_to_render)
                
                canvas_obj.drawImage(
                    image_to_render, img_x, img_y,
                    width=max_width, height=max_height,
                    preserveAspectRatio=True,
                    mask='auto'  # Preserve PNG transparency
                )
                logger.debug(f"✓ Image drawn")
        
        except Exception as e:
            logger.debug(f"Could not render image from {image_source}: {e}")
