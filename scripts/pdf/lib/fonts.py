"""
Font Management Module

Handles TrueType font registration for CJK languages.
All fonts are registered once at module load time.

Includes Unicode character support and graceful fallback handling.
"""

import logging
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
import unicodedata

logger = logging.getLogger(__name__)


class FontManager:
    """
    Manages font registration and retrieval for multi-language support.
    
    Uses TrueType fonts from system directories when available.
    Latin languages use built-in ReportLab fonts.
    
    Features:
    - Graceful font fallback for unsupported characters
    - Character-level font selection for mixed-script text
    - CJK language support with Songti.ttc
    """
    
    # Mapping of language codes to font configuration
    LANGUAGE_FONTS = {
        'de': {'font': 'Helvetica', 'font_bold': 'Helvetica-Bold'},
        'en': {'font': 'Helvetica', 'font_bold': 'Helvetica-Bold'},
        'es': {'font': 'Helvetica', 'font_bold': 'Helvetica-Bold'},
        'fr': {'font': 'Helvetica', 'font_bold': 'Helvetica-Bold'},
        'it': {'font': 'Helvetica', 'font_bold': 'Helvetica-Bold'},
        'ja': {'font': 'HeiseiKakuGo-W5', 'font_bold': 'HeiseiKakuGo-W5'},  # Japanese
        'ko': {'font': 'AppleGothic', 'font_bold': 'AppleGothic'},        # Korean (AppleGothic for Hangul)
        'zh_hans': {'font': 'SongtiBold', 'font_bold': 'SongtiBold'},     # Simplified Chinese
        'zh_hant': {'font': 'STHeitiMedium', 'font_bold': 'STHeitiMedium'},     # Traditional Chinese
    }
    
    # CJK Languages that need TrueType fonts
    CJK_LANGUAGES = ['ja', 'ko', 'zh_hans', 'zh_hant']

    JAPANESE_CID_FONT = 'HeiseiKakuGo-W5'

    # ReportLab ships these Unicode CID font definitions on every supported
    # platform.  They keep PDF generation functional in minimal Linux/CI
    # environments where macOS or distribution-specific TrueType fonts are
    # unavailable.
    CJK_CID_FALLBACKS = {
        'ja': JAPANESE_CID_FONT,
        'ko': 'HYGothic-Medium',
        'zh_hans': 'STSong-Light',
        'zh_hant': 'MSung-Light',
    }
    
    # Path to Songti TrueType Collection (Japanese, Simplified Chinese)
    SONGTI_PATH = Path('/System/Library/Fonts/Supplemental/Songti.ttc')
    
    # Path to STHeiti font (Traditional Chinese)
    STHEITI_PATH = Path('/System/Library/Fonts/STHeiti Medium.ttc')
    
    # Path to AppleGothic font (Korean)
    APPLEGOTHIC_PATH = Path('/System/Library/Fonts/Supplemental/AppleGothic.ttf')
    
    # Fallback CJK fonts for Linux systems
    NOTO_CJK_PATHS = [
        # WenQuanYi fonts (TTF format that works with ReportLab) - prefer these
        Path('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttf'),
        Path('/usr/share/fonts/truetype/wqy/wqy-microhei.ttf'),
        Path('/usr/share/fonts/wenquanyi/wqy-zenhei.ttf'),
        Path('/usr/share/fonts/wenquanyi/wqy-microhei.ttf'),
        # Noto Sans CJK (PostScript outlines - won't work with ReportLab)
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'),
        Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),
        Path('/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc'),
        Path('/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'),
    ]
    
    # Track if fonts have been registered
    _fonts_registered = False
    _font_cache = {}
    
    @classmethod
    def register_fonts(cls):
        """
        Register all fonts at startup.
        
        This should be called once before any PDF generation.
        If called multiple times, subsequent calls are no-ops.
        
        Supports graceful fallback if fonts are missing.
        """
        if cls._fonts_registered:
            logger.debug("Fonts already registered, skipping")
            return
        
        logger.info("Registering fonts for multi-language support...")

        # Songti's macOS TTC face omits valid Japanese glyphs such as 現 and
        # 時. Register a language-specific built-in CID fallback for every CJK
        # language before probing optional system fonts.
        for language, font_name in cls.CJK_CID_FALLBACKS.items():
            try:
                pdfmetrics.registerFont(UnicodeCIDFont(font_name))
                cls._font_cache[font_name] = True
                logger.info(
                    f"✓ Registered built-in {language} CID font '{font_name}'"
                )
            except Exception as e:
                cls._font_cache[font_name] = False
                logger.warning(
                    f"✗ Could not register {language} CID font "
                    f"'{font_name}': {e}"
                )
        
        # Register Songti font for Simplified Chinese
        if cls.SONGTI_PATH.exists():
            try:
                font = TTFont('SongtiBold', str(cls.SONGTI_PATH))
                pdfmetrics.registerFont(font)
                logger.info(f"✓ Registered Songti font (JA, ZH_HANS)")
                logger.debug(f"  Path: {cls.SONGTI_PATH}")
                cls._font_cache['SongtiBold'] = True
            except Exception as e:
                logger.warning(f"✗ Could not register Songti: {e}")
                logger.warning(f"  Some CJK characters may not render properly")
                cls._font_cache['SongtiBold'] = False
        
        # Register STHeiti font for Traditional Chinese
        if cls.STHEITI_PATH.exists():
            try:
                font = TTFont('STHeitiMedium', str(cls.STHEITI_PATH))
                pdfmetrics.registerFont(font)
                logger.info(f"✓ Registered STHeiti font (ZH_HANT)")
                logger.debug(f"  Path: {cls.STHEITI_PATH}")
                cls._font_cache['STHeitiMedium'] = True
            except Exception as e:
                logger.warning(f"✗ Could not register STHeiti: {e}")
                logger.warning(f"  Traditional Chinese characters may not render properly")
                cls._font_cache['STHeitiMedium'] = False
        
        # Register AppleGothic font for Korean
        if cls.APPLEGOTHIC_PATH.exists():
            try:
                font = TTFont('AppleGothic', str(cls.APPLEGOTHIC_PATH))
                pdfmetrics.registerFont(font)
                logger.info(f"✓ Registered AppleGothic font (KO)")
                logger.debug(f"  Path: {cls.APPLEGOTHIC_PATH}")
                cls._font_cache['AppleGothic'] = True
            except Exception as e:
                logger.warning(f"✗ Could not register AppleGothic: {e}")
                logger.warning(f"  Korean characters may not render properly")
                cls._font_cache['AppleGothic'] = False
        else:
            logger.warning(f"⚠️  Songti font not found at {cls.SONGTI_PATH}")
            logger.warning(f"  CJK characters may not render - install fonts or use Noto Sans CJK")
            cls._font_cache['SongtiBold'] = False
            
            # Try Noto Sans CJK as fallback on Linux systems
            noto_registered = False
            
            # First try specific known paths
            for noto_path in cls.NOTO_CJK_PATHS:
                if noto_path.exists():
                    try:
                        # Register as 'SongtiBold' for compatibility with existing code
                        font = TTFont('SongtiBold', str(noto_path))
                        pdfmetrics.registerFont(font)
                        logger.info(f"✓ Registered Noto Sans CJK font as SongtiBold (JA, KO, ZH)")
                        logger.debug(f"  Path: {noto_path}")
                        cls._font_cache['SongtiBold'] = True
                        noto_registered = True
                        break
                    except Exception as e:
                        logger.debug(f"Could not register {noto_path}: {e}")
                        continue
                else:
                    logger.debug(f"Noto path does not exist: {noto_path}")
            
            # If specific paths didn't work, try to find any .ttc file in noto directories
            if not noto_registered:
                noto_dirs = [
                    Path('/usr/share/fonts/opentype/noto/'),
                    Path('/usr/share/fonts/truetype/noto/'),
                    Path('/usr/share/fonts/noto-cjk/'),
                    Path('/usr/share/fonts/truetype/wqy/'),
                    Path('/usr/share/fonts/wenquanyi/'),
                ]
                
                for noto_dir in noto_dirs:
                    logger.warning(f"Checking directory: {noto_dir}")
                    if noto_dir.exists():
                        logger.warning(f"Directory exists: {noto_dir}")
                        # Look for both .ttc and .ttf files (prefer .ttf for ReportLab compatibility)
                        ttf_files = list(noto_dir.glob('**/*.ttf'))
                        ttc_files = list(noto_dir.glob('**/*.ttc'))
                        font_files = ttf_files + ttc_files  # TTF first
                        logger.warning(f"Found TTF files: {ttf_files}")
                        logger.warning(f"Found TTC files: {ttc_files}")
                        if font_files:
                            for font_path in font_files:
                                try:
                                    logger.warning(f"Trying to register: {font_path}")
                                    font = TTFont('SongtiBold', str(font_path))
                                    pdfmetrics.registerFont(font)
                                    logger.info(f"✓ Registered CJK font as SongtiBold (JA, KO, ZH)")
                                    logger.debug(f"  Path: {font_path} (found in {noto_dir})")
                                    cls._font_cache['SongtiBold'] = True
                                    noto_registered = True
                                    break
                                except Exception as e:
                                    logger.warning(f"Could not register {font_path}: {e}")
                                    continue
                            if noto_registered:
                                break
                        else:
                            logger.warning(f"No font files found in {noto_dir}")
                    else:
                        logger.warning(f"Directory does not exist: {noto_dir}")
            
            if not noto_registered:
                logger.warning(f"⚠️  Noto Sans CJK fonts not found. CJK characters may not render properly.")
                logger.warning(f"  Checked specific paths: {cls.NOTO_CJK_PATHS}")
                logger.warning(f"  Checked directories: /usr/share/fonts/opentype/noto/, /usr/share/fonts/truetype/noto/, /usr/share/fonts/noto-cjk/, /usr/share/fonts/truetype/wqy/, /usr/share/fonts/wenquanyi/")
                cls._font_cache['SongtiBold'] = False
        
        # Built-in Helvetica fonts are always available
        logger.debug("✓ Built-in Latin fonts available (Helvetica)")
        cls._font_cache['Helvetica'] = True
        cls._font_cache['Helvetica-Bold'] = True

        cls._fonts_registered = True
        logger.info(f"Font registration complete")
    
    @classmethod
    def get_font_name(cls, language: str, bold: bool = False) -> str:
        """
        Get the appropriate font name for a language.
        
        Args:
            language: Language code (e.g., 'de', 'ja', 'zh_hans')
            bold: If True, returns bold variant (if available)
        
        Returns:
            Font name suitable for ReportLab
        
        Raises:
            ValueError: If language is not supported
        """
        if language not in cls.LANGUAGE_FONTS:
            raise ValueError(f"Unsupported language: {language}. "
                           f"Supported: {', '.join(cls.LANGUAGE_FONTS.keys())}")
        
        font_info = cls.LANGUAGE_FONTS[language]
        font_key = 'font_bold' if bold else 'font'
        requested = font_info[font_key]
        if cls._font_cache.get(requested):
            return requested

        fallback = cls.CJK_CID_FALLBACKS.get(language)
        if fallback and cls._font_cache.get(fallback):
            logger.warning(
                f"⚠️  '{requested}' is not registered for language "
                f"'{language}', falling back to '{fallback}'"
            )
            return fallback

        return 'Helvetica-Bold' if bold else 'Helvetica'

    @classmethod
    def get_symbol_font_name(cls) -> str:
        """Return a registered font for Unicode gender symbols."""
        for font_name in (
            cls.CJK_CID_FALLBACKS['zh_hans'],
            'SongtiBold',
            cls.JAPANESE_CID_FONT,
        ):
            if cls._font_cache.get(font_name):
                return font_name
        return 'Helvetica-Bold'
    
    @classmethod
    def get_supported_languages(cls) -> list:
        """Get list of all supported languages."""
        return list(cls.LANGUAGE_FONTS.keys())
    
    @classmethod
    def is_cjk_language(cls, language: str) -> bool:
        """Check if language is CJK."""
        return language in cls.CJK_LANGUAGES


# Register fonts when module is imported
FontManager.register_fonts()
