"""
Page Renderer - Page layout and structure management

Handles page creation, card positioning, and page structure
for consistent layout across all PDF types.

Features:
- Page background and styling
- Card grid layout (3x3)
- Cutting guides
- Footer rendering
- Page navigation
"""

import logging
from typing import Tuple

from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor

try:
    from ..project_notice import FOOTER_TEXT
    from ..constants import (
        PAGE_WIDTH, PAGE_HEIGHT, PAGE_MARGIN, CARD_WIDTH, CARD_HEIGHT,
        CARDS_PER_ROW, CARDS_PER_COLUMN, GAP_X, GAP_Y
    )
except ImportError:
    from project_notice import FOOTER_TEXT
    # Fallback for direct imports
    from constants import (
        PAGE_WIDTH, PAGE_HEIGHT, PAGE_MARGIN, CARD_WIDTH, CARD_HEIGHT,
        CARDS_PER_ROW, CARDS_PER_COLUMN, GAP_X, GAP_Y
    )

logger = logging.getLogger(__name__)


class PageStyle:
    """Unified page styling constants."""
    
    # Dimensions
    PAGE_WIDTH = PAGE_WIDTH
    PAGE_HEIGHT = PAGE_HEIGHT
    PAGE_MARGIN = PAGE_MARGIN
    
    # Card grid
    CARD_WIDTH = CARD_WIDTH
    CARD_HEIGHT = CARD_HEIGHT
    CARDS_PER_ROW = CARDS_PER_ROW
    CARDS_PER_COLUMN = CARDS_PER_COLUMN
    GAP_X = GAP_X
    GAP_Y = GAP_Y
    CARDS_PER_PAGE = CARDS_PER_ROW * CARDS_PER_COLUMN
    
    # Colors
    BACKGROUND_COLOR = '#FFFFFF'
    BORDER_COLOR = '#CCCCCC'
    GUIDE_COLOR = "#9C9C9C"
    FOOTER_COLOR = '#AAAAAA'
    
    # Cutting guides
    GUIDE_LINE_WIDTH = 0.5
    GUIDE_DASH_PATTERN = (2, 2)
    
    # Footer
    FOOTER_FONT_SIZE = 6


class PageRenderer:
    """Unified page layout renderer."""
    
    def __init__(self):
        """Initialize page renderer."""
        self.style = PageStyle()
    
    def create_page(self, canvas_obj) -> None:
        """
        Create a new blank page with background. Cutting guides are now drawn last for visibility.
        
        Args:
            canvas_obj: ReportLab canvas object
        """
        # White background
        canvas_obj.setFillColor(HexColor(self.style.BACKGROUND_COLOR))
        canvas_obj.rect(0, 0, self.style.PAGE_WIDTH, self.style.PAGE_HEIGHT, 
                       fill=True, stroke=False)
        # Cutting guides will be drawn after cards and footer
    
    def add_card_to_page(self, canvas_obj, card_renderer, pokemon_data: dict, 
                        card_index: int, **render_kwargs) -> None:
        """
        Add a card to a page at the appropriate position.
        
        Args:
            canvas_obj: ReportLab canvas object
            card_renderer: CardRenderer instance
            pokemon_data: Pokémon data dictionary
            card_index: Card index on current page (0-8)
            **render_kwargs: Additional arguments for card_renderer.render_card()
        """
        x, y = self.calculate_card_position(card_index)
        card_renderer.render_card(canvas_obj, pokemon_data, x, y, **render_kwargs)
    
    def calculate_card_position(self, card_index: int) -> Tuple[float, float]:
        """
        Calculate x, y position for a card on a page.
        
        Args:
            card_index: Index of card on current page (0-8 for 3x3 layout)
        
        Returns:
            (x, y) coordinates in points
        
        Raises:
            ValueError: If card_index is out of range (0-8)
        """
        if not (0 <= card_index < self.style.CARDS_PER_PAGE):
            raise ValueError(f"Card index must be 0-{self.style.CARDS_PER_PAGE - 1}, got {card_index}")
        
        row = card_index // self.style.CARDS_PER_ROW
        col = card_index % self.style.CARDS_PER_ROW
        
        x = self.style.PAGE_MARGIN + col * (self.style.CARD_WIDTH + self.style.GAP_X)
        y = (self.style.PAGE_HEIGHT - self.style.PAGE_MARGIN - 
             (row + 1) * self.style.CARD_HEIGHT - row * self.style.GAP_Y)
        
        return (x, y)
    
    def draw_cutting_guides(self, canvas_obj) -> None:
        """
        Draw cutting guides as a dashed grid.
        
        Lines are drawn in the middle of gaps between cards,
        with an outer frame around the entire card area.
        
        Args:
            canvas_obj: ReportLab canvas object
        """
        # Cutting guides: dashed lines between cards and outer frame
        canvas_obj.setLineWidth(self.style.GUIDE_LINE_WIDTH)
        canvas_obj.setStrokeColor(HexColor(self.style.GUIDE_COLOR))
        canvas_obj.setDash(*self.style.GUIDE_DASH_PATTERN)


        # Calculate the center of the gap for the outer frame
        gap_x = self.style.GAP_X
        gap_y = self.style.GAP_Y
        left = self.style.PAGE_MARGIN - gap_x / 2
        top = self.style.PAGE_HEIGHT - self.style.PAGE_MARGIN + gap_y / 2
        right = self.style.PAGE_MARGIN + self.style.CARDS_PER_ROW * self.style.CARD_WIDTH + (self.style.CARDS_PER_ROW - 1) * gap_x + gap_x / 2
        bottom = top - self.style.CARDS_PER_COLUMN * self.style.CARD_HEIGHT - (self.style.CARDS_PER_COLUMN - 1) * gap_y - gap_y

        # Draw vertical dashed lines between cards (in the middle of the gap)
        for col in range(self.style.CARDS_PER_ROW + 1):
            x = self.style.PAGE_MARGIN + col * self.style.CARD_WIDTH + (col - 0.5) * gap_x
            canvas_obj.line(x, top, x, bottom)

        # Draw horizontal dashed lines between cards (in the middle of the gap)
        for row in range(self.style.CARDS_PER_COLUMN + 1):
            y = self.style.PAGE_HEIGHT - self.style.PAGE_MARGIN - row * self.style.CARD_HEIGHT - (row - 0.5) * gap_y
            canvas_obj.line(left, y, right, y)

        canvas_obj.setDash()  # Reset to solid line
    
    def add_footer(self, canvas_obj, footer_text: str = None) -> None:
        """
        Add footer text to a page.
        
        Default footer identifies the project and the final notice page.
        
        Args:
            canvas_obj: ReportLab canvas object
            footer_text: Optional custom footer text
        """
        if footer_text is None:
            footer_text = FOOTER_TEXT
        
        canvas_obj.setFont("Helvetica", self.style.FOOTER_FONT_SIZE)
        canvas_obj.setFillColor(HexColor(self.style.FOOTER_COLOR))
        canvas_obj.drawCentredString(self.style.PAGE_WIDTH / 2, 8, footer_text)
    
    def should_start_new_page(self, card_count: int) -> bool:
        """
        Determine if a new page should be started.
        
        Args:
            card_count: Total cards rendered so far
        
        Returns:
            True if new page should be started
        """
        return card_count > 0 and card_count % self.style.CARDS_PER_PAGE == 0
    
    def get_card_index_on_page(self, card_count: int) -> int:
        """
        Get the card index on the current page (0-8).
        
        Args:
            card_count: Total cards rendered so far
        
        Returns:
            Card index on current page (0-8)
        """
        return card_count % self.style.CARDS_PER_PAGE
    
    def get_page_number(self, card_count: int, include_cover: bool = True) -> int:
        """
        Calculate page number based on card count.
        
        Args:
            card_count: Total cards rendered so far
            include_cover: If True, adds 1 for cover page
        
        Returns:
            Current page number (1-indexed)
        """
        page_num = (card_count + self.style.CARDS_PER_PAGE - 1) // self.style.CARDS_PER_PAGE
        if include_cover:
            page_num += 1
        return page_num
    
    def get_total_pages(self, total_cards: int, include_cover: bool = True) -> int:
        """
        Calculate total pages needed.
        
        Args:
            total_cards: Total number of cards to render
            include_cover: If True, adds 1 for cover page
        
        Returns:
            Total page count
        """
        card_pages = (total_cards + self.style.CARDS_PER_PAGE - 1) // self.style.CARDS_PER_PAGE
        if include_cover:
            card_pages += 1
        return card_pages
