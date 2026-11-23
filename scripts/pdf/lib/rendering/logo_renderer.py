"""
Unified Logo Renderer - Centralized logo rendering for variants

Consolidates all logo rendering logic (EX, M, EX_NEW, EX_TERA, MEGA) and 
image URL rendering ([image]URL[/image] tags) into a single, reusable component 
used by both cover pages and card rendering.

This ensures consistent logo placement, sizing, and rendering across all contexts.

Features:
- Logo tokens: [EX], [M], [EX_NEW], [EX_TERA], [MEGA]
- Image URLs: [image]https://example.com/image.png[/image]
- PNG transparency support via ImageReader with mask='auto'
- Automatic image caching in temp directory
"""

import logging
import re
from pathlib import Path
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
import urllib.request
import tempfile
import hashlib
import shutil

logger = logging.getLogger(__name__)


class LogoRenderer:
    """Unified renderer for variant logos (EX, M, EX_NEW, EX_TERA, MEGA)."""
    
    # Logo file locations (uses logos/ directory structure)
    LOGO_FILES = {
        'ex': "logos/ex",  # Non-localized (default.png)
        'm': "logos/m_pokemon",  # Non-localized (default.png)
        'ex_new': "logos/ex_new",  # Non-localized (default.png)
        'ex_tera': "logos/ex_tera",  # Non-localized (default.png)
        'mega': "logos/mega_evolution",  # Localized (de.png, en.png, ja.png, etc.)
    }
    
    # Standard logo dimensions for different contexts
    LOGO_DIMENSIONS = {
        'title': {  # For cover/section titles
            'ex': (7.3 * mm, 8.8 * mm),
            'm': (6.65 * mm, 5.3 * mm),
            'ex_new': (7.3 * mm, 8.8 * mm),
            'ex_tera': (7.3 * mm, 8.8 * mm),
            'mega': (80 * mm, 40 * mm),  # Mega Evolution logo dimensions (10x larger)
        },
        'card': {  # For card names
            'ex': (6 * mm, 7.2 * mm),
            'm': (5 * mm, 4 * mm),
            'ex_new': (6 * mm, 7.2 * mm),
            'ex_tera': (6 * mm, 7.2 * mm),
            'mega': (65 * mm, 32.5 * mm),  # Mega Evolution logo dimensions for cards (10x larger)
        }
    }
    
    @staticmethod
    def get_logo_path(logo_key: str, language: str = 'en') -> Path:
        """
        Get full path to logo file with localization support.
        
        Fallback chain:
        1. Try localized logo: logos/{logo_key}/{language}.png
        2. Try default logo: logos/{logo_key}/default.png
        
        Args:
            logo_key: Logo identifier ('ex', 'm', 'ex_new', 'ex_tera', 'mega')
            language: Language code (de, en, fr, es, it, ja, ko, zh_hans, zh_hant)
        
        Returns:
            Path to logo file (may not exist)
        """
        # From scripts/pdf/lib/rendering/logo_renderer.py -> project root (4 levels up)
        # Then into images/ directory
        base_path = Path(__file__).parent.parent.parent.parent.parent / "images"
        logo_config = LogoRenderer.LOGO_FILES.get(logo_key, "")
        
        if not logo_config:
            return base_path / "unknown.png"
        
        logo_dir = base_path / logo_config
        
        # Try localized version first
        localized_logo = logo_dir / f"{language}.png"
        if localized_logo.exists():
            return localized_logo
        
        # Fallback to default.png
        default_logo = logo_dir / "default.png"
        if default_logo.exists():
            return default_logo
        
        return None
    
    @staticmethod
    def download_image(url: str) -> Path:
        """
        Download image from URL and cache it locally in temp directory.
        Supports both HTTP(S) URLs and local file paths.
        
        Uses MD5 hash of URL as cache key for efficient retrieval.
        Returns cached file if already downloaded.
        
        Args:
            url: Image URL or local file path to cache
        
        Returns:
            Path to cached image file (may not exist if download/copy failed)
        """
        # Create cache directory in temp folder
        cache_dir = Path(tempfile.gettempdir()) / "binderokedex_image_cache"
        cache_dir.mkdir(exist_ok=True)
        
        # Generate filename from URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()
        is_remote = url.startswith(('http://', 'https://'))
        image_path = url.partition('?')[0].partition('#')[0] if is_remote else url
        file_extension = Path(image_path).suffix or '.png'
        cache_file = cache_dir / f"{url_hash}{file_extension}"
        
        # Return cached file if it exists
        if cache_file.exists():
            return cache_file
        
        # Check if it's a local file path (relative or absolute)
        if not is_remote:
            # Try to find the file relative to project root
            # Get project root (5 levels up from this file: scripts/pdf/lib/rendering/logo_renderer.py)
            project_root = Path(__file__).parent.parent.parent.parent.parent
            local_path = project_root / url
            
            if local_path.exists():
                try:
                    logger.debug(f"Copying local image from {local_path} to cache")
                    shutil.copy2(local_path, cache_file)
                    logger.debug(f"Cached image to {cache_file}")
                    return cache_file
                except Exception as e:
                    logger.warning(f"Failed to copy local image from {local_path}: {e}")
                    return cache_file
            else:
                logger.warning(f"Local image not found: {local_path} (from url: {url})")
                return cache_file
        
        # Download image from URL
        try:
            logger.debug(f"Downloading image from {url}")
            with urllib.request.urlopen(url, timeout=10) as response:
                with open(cache_file, 'wb') as f:
                    f.write(response.read())
            logger.debug(f"Cached image to {cache_file}")
            return cache_file
        except Exception as e:
            logger.warning(f"Failed to download image from {url}: {e}")
            # Return path even if download failed (caller will handle missing file)
            return cache_file
    
    @staticmethod
    def parse_text_with_logos(text: str) -> list:
        """
        Parse text into segments of plain text, logo tokens, and image URLs.
        
        Args:
            text: Text that may contain tokens like [M], [EX], [EX_NEW], [EX_TERA], [image]URL[/image]
        
        Returns:
            List of tuples: [('text', 'plain text'), ('logo', 'ex'), ('image', 'https://...'), ...]
        """
        segments = []
        remaining = text
        
        # Pattern for [image]URL[/image]
        image_pattern = re.compile(r'\[image\](.*?)\[/image\]', re.IGNORECASE)
        
        while remaining:
            # Check for [image] tags first
            image_match = image_pattern.search(remaining)
            if image_match and image_match.start() == 0:
                # Found [image] at start
                image_url = image_match.group(1).strip()
                segments.append(('image', image_url))
                remaining = remaining[image_match.end():].lstrip()
                continue
            
            # Check for logo tokens (longest first)
            if remaining.startswith('[EX_TERA]'):
                segments.append(('logo', 'ex_tera'))
                remaining = remaining[9:].lstrip()
            elif remaining.startswith('[EX_NEW]'):
                segments.append(('logo', 'ex_new'))
                remaining = remaining[8:].lstrip()
            elif remaining.startswith('[MEGA]'):
                segments.append(('logo', 'mega'))
                remaining = remaining[6:].lstrip()
            elif remaining.startswith('[M]'):
                segments.append(('logo', 'm'))
                remaining = remaining[3:].lstrip()
            elif remaining.startswith('[EX]'):
                segments.append(('logo', 'ex'))
                remaining = remaining[4:].lstrip()
            else:
                # Find next token (logo or image)
                token_positions = []
                for token, idx in [('[EX_TERA]', 9), ('[EX_NEW]', 8), ('[MEGA]', 6), ('[M]', 3), ('[EX]', 4)]:
                    pos = remaining.find(token)
                    if pos >= 0:
                        token_positions.append((pos, idx))
                
                # Also check for next [image] tag
                next_image = image_pattern.search(remaining)
                if next_image:
                    token_positions.append((next_image.start(), 0))
                
                if token_positions:
                    next_idx = min(token_positions)[0]
                    text_segment = remaining[:next_idx].rstrip()
                else:
                    text_segment = remaining.rstrip()
                    next_idx = len(remaining)
                
                if text_segment:
                    segments.append(('text', text_segment))
                
                remaining = remaining[next_idx:]
        
        return segments
    
    @staticmethod
    def draw_text_with_logos(canvas_obj, text: str, x_center: float, y: float,
                            font_name: str, font_size: int, context: str = 'title',
                            text_color: str = '#2D2D2D', language: str = 'en') -> None:
        """
        Draw text with embedded logos and images, centered at x_center.
        
        Args:
            canvas_obj: ReportLab canvas
            text: Text with optional logo tokens and [image]URL[/image] tags
            x_center: X coordinate for centering
            y: Y coordinate (baseline for text)
            font_name: Font name
            font_size: Font size
            context: 'title' or 'card' (determines logo sizing)
            text_color: Hex color for text
            language: Language code for localized logos (de, en, fr, etc.)
        """
        canvas_obj.setFont(font_name, font_size)
        canvas_obj.setFillColor(HexColor(text_color))
        
        # Check if text contains any logo tokens or image tags
        has_tokens = ('[EX_TERA]' in text or '[EX_NEW]' in text or '[MEGA]' in text or 
                     '[M]' in text or '[EX]' in text or '[image]' in text.lower())
        
        if not has_tokens:
            # No logos or images - render plain text
            canvas_obj.drawCentredString(x_center, y, text)
            return
        
        # Parse text into segments
        segments = LogoRenderer.parse_text_with_logos(text)
        
        # Get logo dimensions for this context
        dims = LogoRenderer.LOGO_DIMENSIONS.get(context, LogoRenderer.LOGO_DIMENSIONS['title'])
        gap = 1.5 * mm
        
        # Standard image dimensions for subtitle context (TCGdex set logos)
        image_width = 60 * mm
        image_height = 30 * mm
        
        # Calculate total width
        total_width = 0
        for seg_type, seg_value in segments:
            if seg_type == 'text':
                total_width += canvas_obj.stringWidth(seg_value + ' ', font_name, font_size)
            elif seg_type == 'logo':
                logo_width, _ = dims.get(seg_value, (6 * mm, 7.2 * mm))
                total_width += logo_width + gap
            elif seg_type == 'image':
                total_width += image_width + gap
        
        # Draw segments starting from calculated position
        current_x = x_center - total_width / 2
        
        for seg_type, seg_value in segments:
            if seg_type == 'text':
                canvas_obj.drawString(current_x, y, seg_value + ' ')
                current_x += canvas_obj.stringWidth(seg_value + ' ', font_name, font_size)
            elif seg_type == 'logo':
                logo_file = LogoRenderer.get_logo_path(seg_value, language)
                logo_width, logo_height = dims.get(seg_value, (6 * mm, 7.2 * mm))
                logo_y = y - (logo_height / 2) + 1.2 * mm
                
                try:
                    if logo_file.exists():
                        canvas_obj.drawImage(
                            str(logo_file),
                            current_x,
                            logo_y,
                            width=logo_width,
                            height=logo_height,
                            preserveAspectRatio=True,
                            mask='auto'
                        )
                    current_x += logo_width + gap
                except Exception as e:
                    logger.debug(f"Could not draw {seg_value} logo: {e}")
                    current_x += logo_width + gap
            elif seg_type == 'image':
                # Download and cache image from URL
                image_file = LogoRenderer.download_image(seg_value)
                # Align image top edge with text top edge for subtitle context
                if context == 'subtitle':
                    # y is text baseline, text top is at y + font_size * 0.8 (ascender)
                    # Image top should align with text top: y + font_size * 0.8
                    # Image bottom is at: (y + font_size * 0.8) - image_height
                    image_y = y + (font_size * 0.8) - image_height
                else:
                    # Center image vertically for other contexts
                    image_y = y - (image_height / 2) + 1.2 * mm
                
                try:
                    if image_file.exists():
                        # Use ImageReader to support PNG transparency
                        img_reader = ImageReader(str(image_file))
                        canvas_obj.drawImage(
                            img_reader,
                            current_x,
                            image_y,
                            width=image_width,
                            height=image_height,
                            preserveAspectRatio=True,
                            mask='auto'
                        )
                        logger.debug(f"Rendered image from {seg_value}")
                    else:
                        logger.warning(f"Image file not found: {image_file}")
                    current_x += image_width + gap
                except Exception as e:
                    logger.warning(f"Could not draw image from {seg_value}: {e}")
                    current_x += image_width + gap
    
    @staticmethod
    def draw_text_with_suffix_logo(canvas_obj, text: str, suffix: str, x: float, width: float, y: float,
                                  font_name: str, font_size: int, context: str = 'card',
                                  text_color: str = '#2D2D2D') -> None:
        """
        Draw text with a logo suffix, left-aligned within width.
        
        Args:
            canvas_obj: ReportLab canvas
            text: Plain text (e.g., "Charizard")
            suffix: Suffix token (e.g., " [EX_NEW]" or " EX")
            x: X position (left)
            width: Available width
            y: Y position (baseline)
            font_name: Font name
            font_size: Font size
            context: 'title' or 'card' (determines logo sizing)
            text_color: Hex color for text
        """
        canvas_obj.setFont(font_name, font_size)
        canvas_obj.setFillColor(HexColor(text_color))
        
        # Parse suffix to identify logo type
        logo_type = None
        if '[EX_TERA]' in suffix:
            logo_type = 'ex_tera'
            suffix_text = ' [EX_TERA]'
        elif '[EX_NEW]' in suffix:
            logo_type = 'ex_new'
            suffix_text = ' [EX_NEW]'
        elif ' EX' in suffix or suffix == 'EX':
            logo_type = 'ex'
            suffix_text = ' EX'
        elif ' ex' in suffix or suffix == 'ex':
            logo_type = 'ex'
            suffix_text = ' ex'
        else:
            # No recognized suffix - render as plain text
            canvas_obj.drawString(x, y, text + suffix)
            return
        
        if not logo_type:
            canvas_obj.drawString(x, y, text + suffix)
            return
        
        # Get logo dimensions
        dims = LogoRenderer.LOGO_DIMENSIONS.get(context, LogoRenderer.LOGO_DIMENSIONS['card'])
        logo_width, logo_height = dims.get(logo_type, (6 * mm, 7.2 * mm))
        gap = 1 * mm
        
        # Draw text
        canvas_obj.drawString(x, y, text)
        
        # Draw logo
        logo_file = LogoRenderer.get_logo_path(logo_type)
        logo_x = x + canvas_obj.stringWidth(text, font_name, font_size) + gap
        logo_y = y - (logo_height / 2)
        
        try:
            if logo_file.exists():
                canvas_obj.drawImage(
                    str(logo_file),
                    logo_x,
                    logo_y,
                    width=logo_width,
                    height=logo_height,
                    preserveAspectRatio=True,
                    mask='auto'
                )
        except Exception as e:
            logger.debug(f"Could not draw {logo_type} logo: {e}")
