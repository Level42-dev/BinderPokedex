"""
Footer Renderer - Shared footer rendering logic

Consolidates footer rendering for both Generation and Variant covers.
Provides a single, canonical implementation used by CoverRenderer and VariantCoverRenderer.

Features:
- Unified footer layout logic
- Multi-language translation support
- Centered text positioning
- Configurable font size and position
"""

import logging

from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor

try:
    from ..project_notice import FOOTER_TEXT
except ImportError:
    from project_notice import FOOTER_TEXT

logger = logging.getLogger(__name__)


class FooterRenderer:
    """Unified renderer for cover page footers."""
    
    # Default dimensions
    DEFAULT_FONT_SIZE = 6
    DEFAULT_Y_POSITION = 2.5 * mm
    DEFAULT_COLOR = '#CCCCCC'
    
    @staticmethod
    def draw_footer(canvas_obj, page_width: float, language: str, 
                   translation_getter, font_size: float = DEFAULT_FONT_SIZE,
                   y_position: float = DEFAULT_Y_POSITION,
                   color: str = DEFAULT_COLOR,
                   font_name: str = "Helvetica") -> None:
        """
        Draw a footer on a cover page.
        
        Canonical implementation used by both CoverRenderer and VariantCoverRenderer.
        
        Args:
            canvas_obj: ReportLab canvas object
            page_width: Total page width for centering
            language: Language code for translations
            translation_getter: Callable that returns translated string for key
                               (e.g., lambda key: translations.get(key, key))
            font_size: Font size for footer text (default: 6)
            y_position: Y position for footer (default: 2.5mm from bottom)
            color: Text color hex code (default: #CCCCCC)
            font_name: Font name to use (default: Helvetica)
        """
        # Set font and color
        canvas_obj.setFont(font_name, font_size)
        canvas_obj.setFillColor(HexColor(color))
        
        footer_text = FOOTER_TEXT
        
        # Calculate centered position
        text_width = (canvas_obj.stringWidth(footer_text, canvas_obj._fontname, font_size) 
                     if hasattr(canvas_obj, '_fontname') 
                     else len(footer_text) * 2)
        x_pos = (page_width - text_width) / 2
        
        canvas_obj.drawString(x_pos, y_position, footer_text)
