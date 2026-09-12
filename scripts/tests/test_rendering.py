"""
Comprehensive test suite for rendering modules.

Tests CardRenderer, CoverRenderer, PageRenderer, and TranslationLoader.
"""

import json

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics

# Import rendering modules
from scripts.pdf.lib.rendering import (
    CardRenderer,
    CardStyle,
    CoverRenderer,
    CoverStyle,
    PageRenderer,
    PageStyle,
    TranslationLoader
)
from scripts.pdf.lib.constants import (
    TYPE_COLORS,
    GENERATION_COLORS,
    VARIANT_COLORS,
    CARD_WIDTH,
    CARD_HEIGHT,
    PAGE_WIDTH,
    PAGE_HEIGHT,
    CARDS_PER_ROW,
    CARDS_PER_COLUMN
)
from scripts.pdf.lib.fonts import FontManager
from scripts.pdf.lib.text_renderer import TextRenderer


REPO_ROOT = Path(__file__).resolve().parents[2]


class TestCardStyle:
    """Test CardStyle constants."""
    
    def test_type_colors_loaded(self):
        """Verify TYPE_COLORS is loaded from constants."""
        assert TYPE_COLORS is not None
        assert len(TYPE_COLORS) == 18
        assert TYPE_COLORS.get('Normal') == '#A8A878'
    
    def test_card_dimensions(self):
        """Verify card dimensions are correct."""
        assert CardStyle.CARD_WIDTH == CARD_WIDTH
        assert CardStyle.CARD_HEIGHT == CARD_HEIGHT


class TestCardRenderer:
    """Test CardRenderer functionality."""
    
    def test_renderer_initialization(self):
        """Test CardRenderer initializes correctly."""
        renderer = CardRenderer(language='en')
        assert renderer.language == 'en'
        assert renderer.style is not None
    
    def test_language_support(self):
        """Test CardRenderer supports multiple languages."""
        for lang in ['de', 'en', 'fr', 'ja']:
            renderer = CardRenderer(language=lang)
            assert renderer.language == lang

    def test_gender_symbols_use_explicit_registered_fallback_font(self):
        canvas_obj = MagicMock()
        canvas_obj.stringWidth.return_value = 5

        TextRenderer.draw_name_with_symbol_fallback(
            canvas_obj,
            "Nidoran♀",
            0,
            CARD_WIDTH,
            10,
            "Helvetica-Bold",
            symbol_font="STSong-Light",
        )

        assert canvas_obj.setFont.call_args_list[-1].args[0] == "STSong-Light"

    @pytest.mark.parametrize(
        "name",
        (
            "Technische Maschine: Heiterer Himmel",
            "Technische Maschine: Rückentwicklung",
            "Energiekapsel aus der Vergangenheit",
            "Schubenergie",
        ),
    )
    def test_long_card_name_fits_safe_width(self, name):
        safe_width = CARD_WIDTH - 6 * mm

        lines, size = TextRenderer.fit_name_lines(
            name,
            "Helvetica-Bold",
            11,
            8,
            safe_width,
        )

        assert 1 <= len(lines) <= 2
        assert size >= 8
        assert all(
            pdfmetrics.stringWidth(line, "Helvetica-Bold", size)
            <= safe_width
            for line in lines
        )

    def test_unnumbered_card_does_not_fall_back_to_section_index(self):
        renderer = CardRenderer(language="de")
        canvas_obj = MagicMock()

        renderer.render_card(
            canvas_obj,
            {
                "printed_number": None,
                "section_index": 217,
                "name": {"de": "Terapagos & Freunde"},
                "types": ["Colorless"],
                "type": "pokemon",
            },
            0,
            0,
            variant_mode=True,
        )

        centred_strings = [
            call.args[-1]
            for call in canvas_obj.drawCentredString.call_args_list
        ]
        assert "#217" not in centred_strings

    def test_tcg_card_draws_its_original_printed_number(self):
        renderer = CardRenderer(language="de")
        canvas_obj = MagicMock()

        renderer.render_card(
            canvas_obj,
            {
                "printed_number": "224",
                "section_index": 216,
                "name": {"de": "Pikachu"},
                "types": ["Electric"],
                "type": "pokemon",
            },
            0,
            0,
            variant_mode=True,
        )

        centred_strings = [
            call.args[-1]
            for call in canvas_obj.drawCentredString.call_args_list
        ]
        assert "#224" in centred_strings
        assert "#216" not in centred_strings

    def test_legacy_tcg_card_uses_local_id_not_section_index(self):
        assert CardRenderer._format_card_number({
            "localId": "079",
            "section_index": 55,
        }) == "#079"

    def test_every_checked_in_german_tcg_title_fits_the_safe_band(self):
        safe_width = CARD_WIDTH - 6 * mm
        font_name = FontManager.get_font_name("de", bold=True)
        failures = []

        for data_path in sorted((REPO_ROOT / "data" / "output").glob("*.json")):
            scope_data = json.loads(data_path.read_text(encoding="utf-8"))
            if scope_data.get("type") != "tcg_set":
                continue
            if "de" not in scope_data.get("available_languages", []):
                continue

            renderer = CardRenderer(language="de")
            for section in scope_data.get("sections", {}).values():
                for card in section.get("cards", []):
                    name = renderer._construct_variant_name(
                        card,
                        section.get("prefix"),
                        section.get("suffix"),
                    )
                    try:
                        TextRenderer.fit_name_lines(
                            name,
                            font_name,
                            11,
                            8,
                            safe_width,
                        )
                    except ValueError:
                        failures.append(
                            f"{data_path.stem}/{card.get('localId')}: {name}"
                        )

        assert failures == []


class TestCoverStyle:
    """Test CoverStyle constants."""
    
    def test_generation_colors_loaded(self):
        """Verify GENERATION_COLORS is loaded from constants."""
        assert GENERATION_COLORS is not None
        assert len(GENERATION_COLORS) == 9
    
    def test_cover_style_dimensions(self):
        """Verify CoverStyle has correct dimensions."""
        assert CoverStyle.STRIPE_HEIGHT == 100 * mm
        assert CoverStyle.TITLE_FONT_SIZE == 42


class TestCoverRenderer:
    """Test CoverRenderer functionality."""
    
    def test_renderer_initialization(self):
        """Test CoverRenderer initializes correctly."""
        renderer = CoverRenderer(language='en')
        assert renderer.language == 'en'
        assert renderer.style is not None
        assert isinstance(renderer.style, CoverStyle)

    def test_collection_count_uses_scope_unit(self):
        renderer = CoverRenderer(language='de')

        assert renderer._collection_count_text(102, {'type': 'tcg_set'}) == (
            '102 Karten in dieser Sammlung'
        )
        assert renderer._collection_count_text(151, {'type': 'pokedex'}) == (
            '151 Pokémon in dieser Sammlung'
        )

    @pytest.mark.parametrize(
        'language',
        ('de', 'en', 'fr', 'es', 'it', 'ja', 'ko', 'zh_hans', 'zh_hant'),
    )
    def test_card_collection_count_exists_in_every_pdf_language(self, language):
        text = CoverRenderer(language=language)._collection_count_text(
            7,
            {'type': 'tcg_set'},
        )

        assert '7' in text
        assert '{{count}}' not in text
        assert text != 'card_count_text'


class TestPageStyle:
    """Test PageStyle constants."""
    
    def test_page_dimensions(self):
        """Verify page dimensions are correct."""
        assert PageStyle.PAGE_WIDTH == PAGE_WIDTH
        assert PageStyle.PAGE_HEIGHT == PAGE_HEIGHT
    
    def test_card_grid_dimensions(self):
        """Verify card grid constants are correct."""
        assert PageStyle.CARDS_PER_ROW == CARDS_PER_ROW
        assert PageStyle.CARDS_PER_COLUMN == CARDS_PER_COLUMN


class TestPageRenderer:
    """Test PageRenderer functionality."""
    
    def test_renderer_initialization(self):
        """Test PageRenderer initializes correctly."""
        renderer = PageRenderer()
        assert renderer is not None
        assert hasattr(renderer, 'style')


class TestTranslationLoader:
    """Test TranslationLoader functionality."""
    
    def test_loader_initialization(self):
        """Test TranslationLoader initializes correctly."""
        loader = TranslationLoader()
        assert loader is not None
    
    def test_language_support(self):
        """Test TranslationLoader supports multiple languages."""
        loader = TranslationLoader()
        for lang in ['de', 'en', 'fr', 'ja']:
            ui_trans = loader.load_ui(lang)
            assert isinstance(ui_trans, dict)


class TestIntegration:
    """Integration tests for rendering pipeline."""
    
    def test_renderers_importable(self):
        """Test all renderers can be imported."""
        from scripts.pdf.lib.rendering import (
            CardRenderer,
            CoverRenderer,
            PageRenderer,
            TranslationLoader
        )
        assert CardRenderer is not None
        assert CoverRenderer is not None
        assert PageRenderer is not None
        assert TranslationLoader is not None
    
    def test_renderer_instances_creatable(self):
        """Test all renderers can be instantiated."""
        card = CardRenderer(language='en')
        cover = CoverRenderer(language='en')
        page = PageRenderer()
        
        assert card is not None
        assert cover is not None
        assert page is not None
    
    def test_multiple_languages(self):
        """Test renderers support multiple languages."""
        for lang in ['de', 'en', 'fr', 'ja']:
            card = CardRenderer(language=lang)
            cover = CoverRenderer(language=lang)
            
            assert card.language == lang
            assert cover.language == lang


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
