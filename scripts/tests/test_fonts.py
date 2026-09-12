"""
Tests for Font Management Module

Tests font registration, retrieval, and CID font support.
"""

import sys
import logging
from pathlib import Path

import pytest
from reportlab.pdfbase import pdfmetrics

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

from fonts import FontManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_fonts_registered():
    """Test that fonts are registered at module load."""
    logger.info("Testing font registration...")
    
    # All supported languages should work
    languages = FontManager.get_supported_languages()
    assert len(languages) > 0, "No supported languages found"
    assert 'ja' in languages, "Japanese not in supported languages"
    assert 'zh_hans' in languages, "Simplified Chinese not in supported languages"
    assert 'de' in languages, "German not in supported languages"
    
    logger.info(f"✓ All {len(languages)} languages supported: {languages}")


def test_get_font_names():
    """Test retrieving font names for each language."""
    logger.info("Testing font name retrieval...")
    
    # Latin fonts always use Helvetica (built-in, no path dependency)
    latin_cases = [
        ('de', False, 'Helvetica'),
        ('de', True, 'Helvetica-Bold'),
        ('en', False, 'Helvetica'),
    ]
    for language, bold, expected_font in latin_cases:
        font = FontManager.get_font_name(language, bold)
        assert font == expected_font, f"For {language} (bold={bold}): expected {expected_font}, got {font}"
        logger.info(f"✓ {language}: {font}")

    # CJK fonts may be remapped to a fallback on non-macOS systems.
    # Assert that the returned font name is actually registered (i.e. usable).
    cjk_languages = ['ja', 'ko', 'zh_hans', 'zh_hant']
    for language in cjk_languages:
        font = FontManager.get_font_name(language, False)
        registered = FontManager._font_cache.get(font, False)
        assert registered, (
            f"Font '{font}' returned for language '{language}' is not registered. "
            f"Font cache: {FontManager._font_cache}"
        )
        logger.info(f"✓ {language}: {font} (registered)")


def test_japanese_uses_complete_cid_font():
    assert FontManager.get_font_name('ja') == 'HeiseiKakuGo-W5'
    assert FontManager._font_cache['HeiseiKakuGo-W5'] is True


@pytest.mark.parametrize(
    ('language', 'fallback_font'),
    (
        ('ja', 'HeiseiKakuGo-W5'),
        ('ko', 'HYGothic-Medium'),
        ('zh_hans', 'STSong-Light'),
        ('zh_hant', 'MSung-Light'),
    ),
)
def test_platform_neutral_cjk_fallbacks_are_registered(language, fallback_font):
    assert FontManager.CJK_CID_FALLBACKS[language] == fallback_font
    assert FontManager._font_cache[fallback_font] is True
    assert pdfmetrics.getFont(fallback_font) is not None


@pytest.mark.parametrize('language', ('ko', 'zh_hans', 'zh_hant'))
def test_missing_system_font_uses_language_specific_cid_fallback(
    monkeypatch,
    language,
):
    configured_font = FontManager.LANGUAGE_FONTS[language]['font']
    monkeypatch.setitem(FontManager._font_cache, configured_font, False)

    assert (
        FontManager.get_font_name(language)
        == FontManager.CJK_CID_FALLBACKS[language]
    )


def test_symbol_font_is_registered():
    symbol_font = FontManager.get_symbol_font_name()

    assert FontManager._font_cache[symbol_font] is True
    assert pdfmetrics.getFont(symbol_font) is not None


def test_minimal_linux_environment_uses_only_built_in_cid_fonts(
    monkeypatch,
    tmp_path,
):
    missing_font = tmp_path / 'missing-font.ttf'
    monkeypatch.setattr(FontManager, '_fonts_registered', False)
    monkeypatch.setattr(FontManager, '_font_cache', {})
    monkeypatch.setattr(FontManager, 'SONGTI_PATH', missing_font)
    monkeypatch.setattr(FontManager, 'STHEITI_PATH', missing_font)
    monkeypatch.setattr(FontManager, 'APPLEGOTHIC_PATH', missing_font)
    monkeypatch.setattr(FontManager, 'NOTO_CJK_PATHS', [])

    FontManager.register_fonts()

    assert {
        language: FontManager.get_font_name(language)
        for language in FontManager.CJK_LANGUAGES
    } == FontManager.CJK_CID_FALLBACKS
    assert FontManager.get_symbol_font_name() == 'STSong-Light'



def test_cid_fonts():
    """Test CJK language detection."""
    logger.info("Testing CJK language detection...")
    
    # CJK languages
    cjk_languages = ['ja', 'ko', 'zh_hans', 'zh_hant']
    for lang in cjk_languages:
        is_cjk = FontManager.is_cjk_language(lang)
        assert is_cjk, f"{lang} should be CJK"
        logger.info(f"✓ {lang} is CJK")
    
    # Latin languages
    latin_languages = ['de', 'en', 'es', 'fr', 'it']
    for lang in latin_languages:
        is_cjk = FontManager.is_cjk_language(lang)
        assert not is_cjk, f"{lang} should not be CJK"
        logger.info(f"✓ {lang} is not CJK")


def test_invalid_language():
    """Test error handling for unsupported languages."""
    logger.info("Testing error handling...")
    
    try:
        FontManager.get_font_name('invalid_lang')
        assert False, "Should have raised ValueError for invalid language"
    except ValueError as e:
        assert "Unsupported language" in str(e)
        logger.info(f"✓ Correctly raised error: {e}")


def run_all_tests():
    """Run all font tests."""
    logger.info("\n" + "="*60)
    logger.info("FONT MANAGER TESTS")
    logger.info("="*60 + "\n")
    
    try:
        test_fonts_registered()
        test_get_font_names()
        test_cid_fonts()
        test_invalid_language()
        
        logger.info("\n" + "="*60)
        logger.info("✓ ALL TESTS PASSED!")
        logger.info("="*60 + "\n")
        return True
    except AssertionError as e:
        logger.error(f"\n✗ TEST FAILED: {e}")
        return False
    except Exception as e:
        logger.error(f"\n✗ UNEXPECTED ERROR: {e}")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
