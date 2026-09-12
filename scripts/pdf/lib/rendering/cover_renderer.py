"""
Cover Renderer - Consolidates all cover page rendering

Provides a single, data-driven renderer for both Pokédex and Variant covers.
All differences are driven by data structures, not code branching.

Features:
- Generation-based (Pokédex) and variant-based covers
- Unified styling system
- Data-driven title modes and colors
- Multi-language support
- Featured Pokémon display
- Clean, modern design
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

try:
    from ..project_notice import FOOTER_TEXT
    from ..fonts import FontManager
    from ..constants import PAGE_WIDTH, PAGE_HEIGHT, GENERATION_COLORS
    from ..utils import TranslationHelper
    from .translation_loader import TranslationLoader
    from .title_renderer import TitleRenderer
    from .footer_renderer import FooterRenderer
except ImportError:
    from project_notice import FOOTER_TEXT
    # Fallback for direct imports
    from fonts import FontManager
    from constants import PAGE_WIDTH, PAGE_HEIGHT, GENERATION_COLORS
    from utils import TranslationHelper
    from rendering.translation_loader import TranslationLoader
    from rendering.title_renderer import TitleRenderer
    from rendering.footer_renderer import FooterRenderer

logger = logging.getLogger(__name__)


class CoverStyle:
    """Cover styling constants for both Pokédex and Variant covers."""
    
    # Generation color scheme
    GENERATION_COLORS = GENERATION_COLORS
    
    # Dimensions
    STRIPE_HEIGHT = 100 * mm
    TITLE_FONT_SIZE = 42
    GENERATION_FONT_SIZE = 14
    REGION_FONT_SIZE = 18
    POKEMON_COUNT_FONT_SIZE = 14
    POKEDEX_RANGE_FONT_SIZE = 16
    FOOTER_FONT_SIZE = 6
    
    # Colors
    BACKGROUND_COLOR = '#FFFFFF'
    STRIPE_OVERLAY_ALPHA = 0.05
    TITLE_COLOR = '#FFFFFF'
    TEXT_DARK = '#333333'
    TEXT_MEDIUM = '#666666'
    TEXT_GRAY = '#666666'
    TEXT_LIGHT_GRAY = '#CCCCCC'
    FOOTER_COLOR = '#CCCCCC'
    DECORATIVE_LINE_WIDTH = 1.0
    
    # Positions
    TITLE_Y_OFFSET = 30 * mm
    GENERATION_Y_OFFSET = 55 * mm
    REGION_Y_OFFSET = 65 * mm
    POKEDEX_RANGE_Y = 160 * mm     # Pokédex ID range (optional, above count)
    COLLECTION_COUNT_Y = 150 * mm  # Collection count (always above decorative line)
    DECORATIVE_LINE_Y = 145 * mm   # Decorative line position
    ICONIC_POKEMON_Y = 10 * mm
    FOOTER_Y = 2.5 * mm
    
    # Featured Pokémon sizing
    ICONIC_CARD_WIDTH = 65 * mm
    ICONIC_CARD_HEIGHT = 90 * mm
    ICONIC_IMAGE_SCALE = 0.72
    
    # Margins
    MARGIN_HORIZONTAL = 15 * mm
    MARGIN_VERTICAL = 30 * mm


class CoverRenderer:
    """Renderer for both Pokédex and Variant cover pages."""
    
    def __init__(self, language: str = 'en', image_cache=None, cover_template: str = None):
        """
        Initialize cover renderer.
        
        Args:
            language: Language code (e.g., 'en', 'de', 'fr')
            image_cache: Optional image cache for loading Pokémon images
            cover_template: Optional SVG template name for covers
        """
        self.language = language
        self.image_cache = image_cache
        self.cover_template = cover_template
        self.style = CoverStyle()
        self.translation_loader = TranslationLoader()
        self.translations = TranslationHelper.load_translations(language)
    
    def render_cover(self, canvas_obj, pokemon_list: List[Dict], cover_data: Dict, 
                    color: Optional[str] = None) -> None:
        """
        Draw a cover page for any scope (unified for all types).
        
        Args:
            canvas_obj: ReportLab canvas object
            pokemon_list: List of Pokémon to display
            cover_data: Section data dict with title, subtitle, color_hex, description, featured_elements
            color: Optional color override for header stripe. If None, uses color_hex from cover_data.
        """
        # If template is specified, use template rendering
        if self.cover_template:
            self._render_with_template(canvas_obj, pokemon_list, cover_data, color)
        else:
            # Use legacy hardcoded rendering
            self._render_legacy(canvas_obj, pokemon_list, cover_data, color)

    def render_variant_cover(self, canvas_obj, variant_data: Dict, pokemon_list: List[Dict],
                            color: Optional[str] = None, section_title: Optional[str] = None) -> None:
        """Backward-compatible wrapper for older variant cover call sites."""
        cover_data = dict(variant_data)

        display_title = section_title if section_title else (
            cover_data.get('variant_name')
            or cover_data.get('variant_display_name')
            or cover_data.get('title')
            or ''
        )
        subtitle = cover_data.get('variant_display_name') or cover_data.get('region') or ''

        cover_data['title'] = display_title
        cover_data['variant_name'] = display_title
        if subtitle:
            cover_data['subtitle'] = subtitle
            cover_data.setdefault('title_mode', 'with_subtitle')
        else:
            cover_data.setdefault('title_mode', 'no_subtitle')

        self.render_cover(canvas_obj, pokemon_list, cover_data, color)
    
    def _render_legacy(self, canvas_obj, pokemon_list: List[Dict], cover_data: Dict, color: Optional[str] = None) -> None:
        """Legacy hardcoded cover rendering."""
        # Get color from cover_data or use provided override
        if color is None:
            color = cover_data.get('color_hex', '#999999')
        
        # White background
        canvas_obj.setFillColor(HexColor(self.style.BACKGROUND_COLOR))
        canvas_obj.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
        
        # ===== TOP COLORED STRIPE =====
        self._draw_header_stripe(canvas_obj, color)
        
        # ===== MIDDLE CONTENT SECTION =====
        self._draw_title_section(canvas_obj, cover_data)
        self._draw_collection_count(canvas_obj, len(pokemon_list), cover_data, color)
        
        # ===== FEATURED CARDS =====
        self._draw_featured_elements(canvas_obj, cover_data)
        
        # ===== FOOTER =====
        self._draw_footer(canvas_obj)
    
    def _render_with_template(self, canvas_obj, pokemon_list: List[Dict], cover_data: Dict, color: Optional[str] = None) -> None:
        """Render cover using SVG template with XML manipulation (WYSIWYG approach)."""
        from .template_loader import TemplateLoader
        from .logo_renderer import LogoRenderer
        
        # Get color from cover_data or use provided override
        if color is None:
            color = cover_data.get('color_hex', '#999999')
        
        # Load SVG template
        svg_content = TemplateLoader.load_cover_template(self.cover_template)
        if not svg_content:
            logger.warning(f"Cover template '{self.cover_template}' not found, falling back to legacy rendering")
            self._render_legacy(canvas_obj, pokemon_list, cover_data, color)
            return
        
        # Prepare dynamic content
        section_title = cover_data.get('title', {})  # Changed from 'section_title' to 'title'
        if isinstance(section_title, dict):
            section_title_text = section_title.get(self.language, section_title.get('en', ''))
        else:
            section_title_text = str(section_title) if section_title else ''
        
        section_subtitle = cover_data.get('subtitle', {})  # Changed from 'section_subtitle' to 'subtitle'
        if isinstance(section_subtitle, dict):
            section_subtitle_text = section_subtitle.get(self.language, section_subtitle.get('en', ''))
        else:
            section_subtitle_text = str(section_subtitle) if section_subtitle else ''
        
        collection_count_text = self._collection_count_text(len(pokemon_list), cover_data)
        
        description = cover_data.get('description', {})
        if isinstance(description, dict):
            description_text = description.get(self.language, description.get('en', ''))
        else:
            description_text = str(description) if description else ''
        
        footer_text = FOOTER_TEXT
        
        # Manipulate SVG content via XML
        replacements = {
            'section_title': section_title_text,
            'section_subtitle': section_subtitle_text,
            'pokemon_count': collection_count_text,
            'description': description_text,
            'footer': footer_text,
        }
        
        # Substitute color variable first (for decorative_line stroke color)
        svg_content = TemplateLoader.substitute_variables(svg_content, {'stripe_color': color})
        
        # Now manipulate XML to replace text content
        svg_content = TemplateLoader.manipulate_svg_xml(svg_content, replacements)
        
        # Render complete SVG with all content
        TemplateLoader.render_svg_to_canvas(svg_content, canvas_obj, 0, 0)
        
        # ===== DYNAMIC CONTENT that can't be in SVG =====
        
        # Featured elements (images need to be dynamically loaded)
        # Note: featured_area in SVG is just placeholder rects, we overlay the actual images
        featured_elements = cover_data.get('featured_elements') or cover_data.get('featured_cards', [])
        if featured_elements and self.image_cache:
            # SVG: y=199mm (top), height=63mm → bottom at y=262mm
            # ReportLab needs bottom-left: 297mm - 262mm = 35mm from bottom
            featured_y = 35 * mm  # Bottom-left corner of featured area
            self._draw_featured_elements_at(canvas_obj, cover_data, featured_y)
    
    def _draw_header_stripe(self, canvas_obj, color: str) -> None:
        """Draw the colored top stripe with title."""
        stripe_height = self.style.STRIPE_HEIGHT
        
        # Fill with color
        canvas_obj.setFillColor(HexColor(color))
        canvas_obj.rect(0, PAGE_HEIGHT - stripe_height, PAGE_WIDTH, stripe_height, 
                       fill=True, stroke=False)
        
        # Semi-transparent overlay
        canvas_obj.setFillColor(HexColor("#000000"), alpha=self.style.STRIPE_OVERLAY_ALPHA)
        canvas_obj.rect(0, PAGE_HEIGHT - stripe_height, PAGE_WIDTH, stripe_height, 
                       fill=True, stroke=False)
        
        # Title
        canvas_obj.setFont("Helvetica-Bold", self.style.TITLE_FONT_SIZE)
        canvas_obj.setFillColor(HexColor(self.style.TITLE_COLOR))
        title_y = PAGE_HEIGHT - self.style.TITLE_Y_OFFSET
        canvas_obj.drawCentredString(PAGE_WIDTH / 2, title_y, "Binder Pokédex")
        
        # Decorative underline
        canvas_obj.setStrokeColor(HexColor(self.style.TITLE_COLOR))
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(40 * mm, title_y - 8, PAGE_WIDTH - 40 * mm, title_y - 8)
    
    def _draw_title_section(self, canvas_obj, cover_data: Dict) -> None:
        """Draw title and subtitle using TitleRenderer."""
        try:
            font_name = FontManager.get_font_name(self.language, bold=True)
        except Exception:
            font_name = "Helvetica-Bold"
        
        TitleRenderer.draw_title(
            canvas_obj,
            cover_data,
            self.language,
            PAGE_WIDTH,
            PAGE_HEIGHT,
            translation_getter=self._get_translation,
            font_name=font_name,
            subtitle_font_size=18,
            title_y_offset=55 * mm,
            subtitle_y_offset=65 * mm,
            section_title=None
        )
    
    def _draw_collection_count(self, canvas_obj, count: int, cover_data: Dict, color: str) -> None:
        """Draw the typed collection count, description, and decorative line."""
        collection_count_text = self._collection_count_text(count, cover_data)
        
        try:
            count_font_name = FontManager.get_font_name(self.language, bold=False)
            canvas_obj.setFont(count_font_name, self.style.POKEMON_COUNT_FONT_SIZE)
        except Exception:
            canvas_obj.setFont("Helvetica", self.style.POKEMON_COUNT_FONT_SIZE)
        
        canvas_obj.setFillColor(HexColor(self.style.TEXT_MEDIUM))
        canvas_obj.drawCentredString(
            PAGE_WIDTH / 2,
            self.style.COLLECTION_COUNT_Y,
            collection_count_text,
        )
        
        # Decorative line
        canvas_obj.setStrokeColor(HexColor(color))
        canvas_obj.setLineWidth(self.style.DECORATIVE_LINE_WIDTH)
        canvas_obj.line(40 * mm, self.style.DECORATIVE_LINE_Y, PAGE_WIDTH - 40 * mm, self.style.DECORATIVE_LINE_Y)
        
        # Description text (below the line)
        description = cover_data.get('description', {})
        if isinstance(description, dict):
            description_text = description.get(self.language, description.get('en', ''))
        else:
            description_text = str(description) if description else ''
        
        if description_text:
            try:
                desc_font_name = FontManager.get_font_name(self.language, bold=False)
            except Exception:
                desc_font_name = "Helvetica"
            
            # Use LogoRenderer to handle [EX], [EX_NEW] tokens in description
            from .logo_renderer import LogoRenderer
            LogoRenderer.draw_text_with_logos(
                canvas_obj,
                description_text,
                PAGE_WIDTH / 2,
                self.style.DECORATIVE_LINE_Y - 8 * mm,
                desc_font_name,
                11,
                context='title',
                text_color=self.style.TEXT_GRAY,
                language=self.language
            )
    
    def _draw_featured_elements(self, canvas_obj, cover_data: Dict) -> None:
        """Draw featured element images in the lower section of the cover."""
        # Support both old and new field names for backward compatibility
        featured_elements = cover_data.get('featured_elements') or cover_data.get('featured_cards', [])
        
        if not featured_elements:
            return
        
        # Position for featured elements (lower section, above footer)
        card_y_base = 35 * mm
        card_width = 45 * mm
        card_height = 63 * mm
        
        num_elements = len(featured_elements)
        
        # Calculate spacing to center elements horizontally
        if num_elements == 1:
            spacing = 0
            start_x = (PAGE_WIDTH - card_width) / 2
        elif num_elements == 2:
            spacing = 10 * mm
            total_width = 2 * card_width + spacing
            start_x = (PAGE_WIDTH - total_width) / 2
        else:  # 3 elements
            spacing = 8 * mm
            total_width = 3 * card_width + 2 * spacing
            start_x = (PAGE_WIDTH - total_width) / 2
        
        # Draw each featured element
        for i, element in enumerate(featured_elements[:3]):  # Max 3 elements
            element_x = start_x + i * (card_width + spacing)
            
            # Get local image path
            image_path = element.get('local_image_path')
            if not image_path or not Path(image_path).exists():
                logger.warning(f"Featured element image not found: {image_path}")
                continue
            
            try:
                # Draw element image
                canvas_obj.drawImage(
                    str(image_path),
                    element_x,
                    card_y_base,
                    width=card_width,
                    height=card_height,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception as e:
                logger.error(f"Failed to draw featured element image {image_path}: {e}")
    
    def _draw_footer(self, canvas_obj) -> None:
        """Draw footer using canonical renderer."""
        try:
            font_name = FontManager.get_font_name(self.language, bold=False)
        except Exception:
            font_name = "Helvetica"
        
        FooterRenderer.draw_footer(
            canvas_obj,
            page_width=PAGE_WIDTH,
            language=self.language,
            translation_getter=self._get_translation,
            font_size=6,
            y_position=2.5 * mm,
            color=self.style.TEXT_LIGHT_GRAY,
            font_name=font_name
        )
    
    def _draw_featured_elements_at(self, canvas_obj, cover_data: Dict, featured_y: float) -> None:
        """Draw featured element images using fixed SVG position."""
        # Support both old and new field names for backward compatibility
        featured_elements = cover_data.get('featured_elements') or cover_data.get('featured_cards', [])
        
        if not featured_elements:
            return
        
        # Use fixed Y position
        card_y_base = featured_y
        card_width = 45 * mm
        card_height = 63 * mm
        
        # Fixed X positions from SVG template (match the placeholder rects)
        # SVG: x=27.5, x=82.5, x=137.5 (centered with 10mm spacing)
        x_positions = [27.5 * mm, 82.5 * mm, 137.5 * mm]
        
        # Draw each featured element
        for i, element in enumerate(featured_elements[:3]):  # Max 3 elements
            if i >= len(x_positions):
                break
                
            element_x = x_positions[i]
            
            # Get local image path
            image_path = element.get('local_image_path')
            if not image_path or not Path(image_path).exists():
                logger.warning(f"Featured element image not found: {image_path}")
                continue
            
            try:
                # Load and draw image
                img = ImageReader(image_path)
                canvas_obj.drawImage(
                    img,
                    element_x,
                    card_y_base,
                    width=card_width,
                    height=card_height,
                    preserveAspectRatio=True,
                    mask='auto'
                )
            except Exception as e:
                logger.error(f"Error drawing featured element: {e}")
    
    def _get_translation(self, key: str, fallback: str = None, **kwargs) -> str:
        """Get translated text from UI translations."""
        text = self.translation_loader.load_ui(self.language).get(key, fallback or key)
        
        # Replace placeholders
        for k, v in kwargs.items():
            text = text.replace(f"{{{{{k}}}}}", str(v))
        
        return text

    def _collection_count_text(self, count: int, cover_data: Dict) -> str:
        """Describe the actual collection unit shown on the cover."""
        is_card_collection = cover_data.get('type') == 'tcg_set'
        translation_key = 'card_count_text' if is_card_collection else 'pokemon_count_text'
        fallback = (
            f"{count} cards in this collection"
            if is_card_collection
            else f"{count} Pokémon in this collection"
        )
        return self._get_translation(translation_key, fallback=fallback, count=count)
