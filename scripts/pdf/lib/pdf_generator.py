"""
PDF Generator Module - Enhanced

Orchestrates the complete PDF generation process.
Uses FontManager for font handling and TextRenderer for text rendering.

Features:
- Multi-language support with CJK rendering
- Cover pages with generation info
- Pokémon card layout (3x3 per page)
- Image embedding with fallback
- Clean architecture - no monkey-patching
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
import urllib.request
import urllib.error
from io import BytesIO
from PIL import Image

try:
    from .project_notice import append_project_notice, set_document_provenance
    from .fonts import FontManager
    from .utils import TranslationHelper, TextRenderer
    from .constants import (
        LANGUAGES, PAGE_WIDTH, PAGE_HEIGHT, PAGE_MARGIN,
        CARD_WIDTH, CARD_HEIGHT, CARDS_PER_ROW, CARDS_PER_COLUMN, GAP_X, GAP_Y,
        OUTPUT_DIR, PDF_PREFIX, PDF_EXTENSION, COLORS, TYPE_COLORS, GENERATION_COLORS,
        GENERATION_INFO
    )
    from .rendering import CardRenderer, CoverRenderer, PageRenderer
except ImportError:
    from project_notice import append_project_notice, set_document_provenance
    # Fallback for direct imports (testing)
    from fonts import FontManager
    from utils import TranslationHelper, TextRenderer
    from constants import (
        LANGUAGES, PAGE_WIDTH, PAGE_HEIGHT, PAGE_MARGIN,
        CARD_WIDTH, CARD_HEIGHT, CARDS_PER_ROW, CARDS_PER_COLUMN, GAP_X, GAP_Y,
        OUTPUT_DIR, PDF_PREFIX, PDF_EXTENSION, COLORS, TYPE_COLORS, GENERATION_COLORS,
        GENERATION_INFO
    )
    from rendering import CardRenderer, CoverRenderer, PageRenderer

logger = logging.getLogger(__name__)


class ImageCache:
    """Image cache with fallback to network downloads and optimized pre-resizing."""
    
    # Image sizes for different use cases
    CARD_SIZE = (180, 180)          # Optimized: Pokémon cards for 150-300 DPI print (164-328px needed)
    FEATURED_SIZE = (500, 500)      # Large: Featured Pokémon on covers (46×65mm, 234px needed)
    MAX_CACHE_SIZE = 500            # ⚡ Keep only 500 most recent images in RAM
    
    def __init__(self):
        self.cache = {}
        self.cache_order = []  # Track insertion order for LRU eviction
        self.disk_cache_dir = Path(__file__).parent.parent.parent.parent / 'data' / 'pokemon_images_cache'
    
    def _get_cached_file(self, pokemon_id: int, variant: str = 'default', size: str = 'card') -> Optional[Path]:
        """
        Get path to cached image file if it exists.
        
        Args:
            pokemon_id: Pokémon ID
            variant: Variant name (default: 'default')
            size: Image size ('card' for 100×100, 'featured' for 250×250)
        
        Returns:
            Path to cached file or None
        """
        if size == 'featured':
            cache_file = self.disk_cache_dir / f'pokemon_{pokemon_id}' / f'{variant}_featured.png'
        else:  # 'card' size
            cache_file = self.disk_cache_dir / f'pokemon_{pokemon_id}' / f'{variant}_thumb.png'
        
        if cache_file.exists():
            return cache_file
        
        # Fallback: check for old JPG format
        if size == 'featured':
            old_cache_file = self.disk_cache_dir / f'pokemon_{pokemon_id}' / f'{variant}_featured.jpg'
        else:
            old_cache_file = self.disk_cache_dir / f'pokemon_{pokemon_id}' / f'{variant}_thumb.jpg'
        
        if old_cache_file.exists():
            return old_cache_file
        
        return None
    
    def _create_thumbnail(self, pil_image: Image.Image, target_size: tuple = None) -> Image.Image:
        """
        Create an optimized thumbnail from a PIL image.
        
        Args:
            pil_image: PIL Image object
            target_size: Target dimensions (width, height). Default: CARD_SIZE (100×100)
        
        Returns:
            Resized PIL Image
        """
        if target_size is None:
            target_size = self.CARD_SIZE
        
        # Use LANCZOS for high-quality downsampling
        return pil_image.resize(target_size, Image.Resampling.LANCZOS)
    
    def _save_thumbnail(self, pil_image: Image.Image, pokemon_id: int, variant: str = 'default') -> Path:
        """
        Save a thumbnail to disk cache for future use.
        
        Args:
            pil_image: PIL Image object (should already be thumbnail size)
            pokemon_id: Pokémon ID
            variant: Variant name (default: 'default')
        
        Returns:
            Path to saved thumbnail
        """
        try:
            pokemon_dir = self.disk_cache_dir / f'pokemon_{pokemon_id}'
            pokemon_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as PNG to preserve transparency (if present)
            thumbnail_file = pokemon_dir / f'{variant}_thumb.png'
            
            # Convert to RGBA if image has transparency
            if pil_image.mode in ('RGBA', 'LA') or (pil_image.mode == 'P' and 'transparency' in pil_image.info):
                if pil_image.mode != 'RGBA':
                    pil_image = pil_image.convert('RGBA')
                pil_image.save(thumbnail_file, format='PNG', optimize=True)
            else:
                # No transparency - can use RGB for smaller file size
                if pil_image.mode not in ('RGB', 'L'):
                    pil_image = pil_image.convert('RGB')
                pil_image.save(thumbnail_file, format='PNG', optimize=True)
            
            return thumbnail_file
        except Exception as e:
            logger.debug(f"Could not save thumbnail for #{pokemon_id}: {e}")
            return None
    
    def get_image(self, pokemon_id: int, url: Optional[str] = None, timeout: int = 5, size: str = 'card'):
        """
        Get ImageReader object from disk cache, RAM cache, or download.
        
        Performance optimization: Images are pre-resized to optimize for their use case:
        - 'card' (100×100px): For small Pokémon cards in binder
        - 'featured' (250×250px): For large featured Pokémon on cover pages
        
        ⚡ RAM Cache Optimization: Uses LRU (Least Recently Used) eviction to keep
        at most MAX_CACHE_SIZE images in memory. This prevents memory bloat during
        multi-generation PDF generation.
        
        Args:
            pokemon_id: Pokémon ID for disk cache lookup
            url: Fallback URL if not cached
            timeout: Download timeout in seconds
            size: Image size ('card' for 100×100px, 'featured' for 250×250px). Default: 'card'
        
        Returns:
            ImageReader object if successful, None otherwise
        """
        # Check RAM cache first - use URL hash to differentiate forms (e.g., Mega Charizard X vs normal)
        # Extract unique identifier from URL (e.g., "10034" from PokeAPI or card ID from TCGdex)
        url_identifier = "default"
        if url:
            # Extract the last numeric part from the URL as identifier
            # PokeAPI: .../10034.png -> 10034 (Mega Charizard X)
            # TCGdex: .../me02/013 -> me02-013
            url_parts = url.rstrip('/').split('/')
            if url_parts:
                last_part = url_parts[-1].replace('.png', '').replace('.jpg', '')
                if last_part.isdigit() or '-' in last_part:
                    url_identifier = last_part
        
        cache_key = f'pokemon_{pokemon_id}_{url_identifier}_{size}'
        if cache_key in self.cache:
            # Move to end (mark as recently used)
            self.cache_order.remove(cache_key)
            self.cache_order.append(cache_key)
            return self.cache[cache_key]
        
        # Try disk cache - use url_identifier as variant to differentiate forms
        cached_file = self._get_cached_file(pokemon_id, variant=url_identifier, size=size)
        if cached_file:
            try:
                logger.debug(f"✓ Loading from cache: {cached_file.name}")
                # Load directly from cached file path - ReportLab handles file ownership
                image_reader = ImageReader(str(cached_file))
                
                # Add to RAM cache with LRU eviction
                self._add_to_cache(cache_key, image_reader)
                
                return image_reader
            except Exception as e:
                logger.debug(f"✗ Failed to load cached image: {e}")
        
        # Fallback to network download if URL provided
        if url:
            # ⚠️ WARNING: Image not found in cache, falling back to network download
            logger.warning(f"⚠️  Image #{pokemon_id} (size={size}) not in cache - downloading from URL as fallback")
            logger.warning(f"   Run fetch pipeline to cache all images: python scripts/fetcher/fetch.py --scope <scope>")
            try:
                logger.debug(f"⬇ Downloading image: {url.split('/')[-1]}")
                req = urllib.request.Request(
                    url,
                    headers={'User-Agent': 'Binder Pokédex/2.0'}
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    image_data = BytesIO(response.read())
                    image_data.seek(0)
                    
                    # Load with PIL
                    pil_image = Image.open(image_data)
                    
                    # Preserve transparency - DO NOT convert RGBA to RGB
                    # Keep alpha channel for transparent backgrounds
                    if pil_image.mode == 'P':
                        # Convert palette images to RGBA to preserve transparency
                        pil_image = pil_image.convert('RGBA')
                    # Note: We keep RGBA mode to preserve transparency!
                    
                    # ⚡ OPTIMIZATION: Pre-resize based on use case
                    # Card size (180×180px): Small, fast (for binder cards)
                    # Featured size (500×500px): Large, for cover displays
                    target_size = self.FEATURED_SIZE if size == 'featured' else self.CARD_SIZE
                    pil_image = self._create_thumbnail(pil_image, target_size)
                    
                    # ⚡ CRITICAL FIX: Always save to disk first, then load from disk
                    # This ensures ImageReader gets a stable file path instead of a BytesIO
                    # that might get garbage-collected, causing image data corruption
                    pokemon_dir = Path(self.disk_cache_dir) / f'pokemon_{pokemon_id}'
                    pokemon_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Determine cache filename based on size and variant (to differentiate forms)
                    # Use PNG format to preserve transparency
                    if size == 'featured':
                        cache_path = pokemon_dir / f'{url_identifier}_featured.png'
                    else:
                        cache_path = pokemon_dir / f'{url_identifier}_thumb.png'
                    
                    # Save to disk as PNG to preserve transparency
                    if pil_image.mode in ('RGBA', 'LA'):
                        pil_image.save(str(cache_path), format='PNG', optimize=True)
                    else:
                        # Convert to RGB for non-transparent images (smaller file size)
                        if pil_image.mode not in ('RGB', 'L'):
                            pil_image = pil_image.convert('RGB')
                        pil_image.save(str(cache_path), format='PNG', optimize=True)
                    
                    # Load from disk file (not BytesIO) - ensures stable image data
                    image_reader = ImageReader(str(cache_path))
                    
                    # Add to RAM cache with LRU eviction
                    self._add_to_cache(cache_key, image_reader)
                    
                    logger.debug(f"✓ Downloaded & cached ({len(self.cache)}/{self.MAX_CACHE_SIZE} images, size={size})")
                    return image_reader
            except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
                logger.debug(f"✗ Failed to download image: {e}")
        
        return None
    
    def _add_to_cache(self, cache_key: str, image_reader):
        """
        Add image to RAM cache with LRU eviction.
        
        If cache exceeds MAX_CACHE_SIZE, removes the least recently used item.
        
        Args:
            cache_key: Cache key (e.g., 'pokemon_1')
            image_reader: ImageReader object to cache
        """
        # Remove if already cached (for re-insertion)
        if cache_key in self.cache_order:
            self.cache_order.remove(cache_key)
        
        # Add to end (most recently used)
        self.cache[cache_key] = image_reader
        self.cache_order.append(cache_key)
        
        # Evict oldest if needed
        while len(self.cache) > self.MAX_CACHE_SIZE:
            oldest_key = self.cache_order.pop(0)
            del self.cache[oldest_key]
            logger.debug(f"  ⚡ Cache full ({self.MAX_CACHE_SIZE}). Evicted oldest: {oldest_key}")


class PDFGenerator:
    """
    Generates Pokémon binder PDFs in multiple languages.
    
    Handles:
    - Language selection and validation
    - PDF creation and page management
    - Card layout and rendering
    - File output
    """
    
    def __init__(self, language: str, generation: int, translations: dict = None):
        """
        Initialize PDF generator.
        
        Args:
            language: Language code (e.g., 'de', 'ja', 'zh_hans')
            generation: Pokémon generation (1-9)
            translations: Optional translations dictionary. If None, will be loaded from file.
        
        Raises:
            ValueError: If language or generation is invalid
        """
        if language not in LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        if generation not in range(1, 10):
            raise ValueError(f"Invalid generation: {generation}")
        
        self.language = language
        self.generation = generation
        self.pokemon_list = []
        self.current_page_cards = []
        self.page_count = 0
        self.image_cache = ImageCache()  # Initialize image cache
        
        # Initialize new rendering modules
        self.card_renderer = CardRenderer(language, self.image_cache)
        self.cover_renderer = CoverRenderer(language, generation, self.image_cache)
        self.page_renderer = PageRenderer()
        
        # Load translations via TranslationLoader
        try:
            from .rendering.translation_loader import TranslationLoader
        except ImportError:
            from rendering.translation_loader import TranslationLoader
        self.translation_loader = TranslationLoader()
        self.translations = self.translation_loader.load_ui(self.language)
        
        logger.info(f"Initialized PDFGenerator for {LANGUAGES[language]['name']} (Gen {generation})")
    
    def set_pokemon_list(self, pokemon_list: list):
        """
        Set the list of Pokémon to render.
        
        Args:
            pokemon_list: List of pokemon data dictionaries
        """
        self.pokemon_list = pokemon_list
        logger.info(f"Set {len(pokemon_list)} Pokémon for rendering")
    
    
    def _draw_cover_page(self, canvas_obj):
        """
        Draw a cover page for the generation with featured Pokémon.
        
        Features:
        - Colored top stripe with generation info
        - Large region name and generation number
        - Three featured Pokémon displayed at the bottom
        - Clean, modern design
        - Multi-language support for all text
        
        Args:
            canvas_obj: ReportLab canvas object
        """
        # White background
        canvas_obj.setFillColor(HexColor("#FFFFFF"))
        canvas_obj.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=True, stroke=False)
        
        # Get generation color
        gen_color = GENERATION_COLORS.get(self.generation, '#999999')
        
        # ===== TOP COLORED STRIPE (Header section) =====
        stripe_height = 100 * mm
        canvas_obj.setFillColor(HexColor(gen_color))
        canvas_obj.rect(0, PAGE_HEIGHT - stripe_height, PAGE_WIDTH, stripe_height, fill=True, stroke=False)
        
        # Subtle gradient effect with semi-transparent overlay
        canvas_obj.setFillColor(HexColor("#000000"), alpha=0.05)
        canvas_obj.rect(0, PAGE_HEIGHT - stripe_height, PAGE_WIDTH, stripe_height, fill=True, stroke=False)
        
        # Binder Pokédex title
        canvas_obj.setFont("Helvetica-Bold", 42)
        canvas_obj.setFillColor(HexColor("#FFFFFF"))
        title_y = PAGE_HEIGHT - 30 * mm
        canvas_obj.drawCentredString(PAGE_WIDTH / 2, title_y, "Binder Pokédex")
        
        # Decorative underline for title
        canvas_obj.setStrokeColor(HexColor("#FFFFFF"))
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(40 * mm, title_y - 8, PAGE_WIDTH - 40 * mm, title_y - 8)
        
        # Generation and Region info in header
        get_info = GENERATION_INFO[self.generation]
        region_name = get_info.get('region', f'Generation {self.generation}')
        
        # Use translations for Generation text
        gen_text = self.translations.get('generation_num', 'Generation {{gen}}').replace('{{gen}}', str(self.generation))
        
        # Use appropriate font for generation text
        try:
            gen_font_name = FontManager.get_font_name(self.language, bold=False)
            canvas_obj.setFont(gen_font_name, 14)
        except:
            canvas_obj.setFont("Helvetica", 14)
        canvas_obj.setFillColor(HexColor("#FFFFFF"))
        canvas_obj.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 55 * mm, gen_text)
        
        canvas_obj.setFont("Helvetica-Bold", 18)
        canvas_obj.setFillColor(HexColor("#FFFFFF"))
        canvas_obj.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 65 * mm, region_name)
        
        # ===== MIDDLE CONTENT SECTION =====
        # ID range with translation
        start_id, end_id = get_info['range']
        id_range_text = self.translations.get('pokedex_range', 'Pokédex {{start}} – {{end}}').replace('{{start}}', f"#{start_id:03d}").replace('{{end}}', f"#{end_id:03d}")
        
        # Use appropriate font for ID range text
        try:
            id_font_name = FontManager.get_font_name(self.language, bold=False)
            canvas_obj.setFont(id_font_name, 16)
        except:
            canvas_obj.setFont("Helvetica", 16)
        canvas_obj.setFillColor(HexColor("#333333"))
        canvas_obj.drawCentredString(PAGE_WIDTH / 2, 120 * mm, id_range_text)
        
        # Pokémon count and info with translation
        pokemon_text = self.translations.get('pokemon_count_text', '{{count}} Pokémon in this collection').replace('{{count}}', str(len(self.pokemon_list)))
        
        # Use appropriate font for pokemon count text
        try:
            count_font_name = FontManager.get_font_name(self.language, bold=False)
            canvas_obj.setFont(count_font_name, 14)
        except:
            canvas_obj.setFont("Helvetica", 14)
        canvas_obj.setFillColor(HexColor("#666666"))
        canvas_obj.drawCentredString(PAGE_WIDTH / 2, 110 * mm, pokemon_text)
        
        # Decorative elements
        canvas_obj.setStrokeColor(HexColor(gen_color))
        canvas_obj.setLineWidth(1)
        canvas_obj.line(40 * mm, 105 * mm, PAGE_WIDTH - 40 * mm, 105 * mm)
        
        # Bottom info - single line with print instructions (multilingual)
        try:
            font_name = FontManager.get_font_name(self.language, bold=False)
            canvas_obj.setFont(font_name, 6)
        except:
            canvas_obj.setFont("Helvetica", 6)
        
        canvas_obj.setFillColor(HexColor("#CCCCCC"))
        
        # Build footer text with translations
        self.page_renderer.add_footer(canvas_obj)
    
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
    
    
    def generate(self, pokemon_list: list = None) -> Path:
        """
        Generate the complete PDF with cover page and cards.
        
        Uses unified rendering modules (CardRenderer, CoverRenderer, PageRenderer)
        for consistent quality across all PDF types.
        
        Args:
            pokemon_list: List of Pokémon to render (optional, uses self.pokemon_list if not provided)
        
        Returns:
            Path to generated PDF file
        
        Raises:
            ValueError: If no Pokémon list is available
            IOError: If PDF cannot be written
        """
        if pokemon_list:
            self.set_pokemon_list(pokemon_list)
        
        if not self.pokemon_list:
            raise ValueError("No Pokémon list provided")
        
        # Create output directory structure: output/{language}/
        output_path = Path(OUTPUT_DIR)
        lang_output_path = output_path / self.language
        lang_output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate PDF filename
        lang_code = self.language
        gen_code = self.generation
        pdf_filename = f"{PDF_PREFIX}{gen_code}_{lang_code}{PDF_EXTENSION}"
        pdf_file_path = lang_output_path / pdf_filename
        
        logger.info(f"Starting PDF generation: {pdf_file_path}")
        
        try:
            # Create canvas
            c = canvas.Canvas(str(pdf_file_path), pagesize=A4)
            set_document_provenance(c, pdf_filename)
            
            # Draw cover page using legacy Pokedex cover renderer
            self._draw_cover_page(c)
            c.showPage()
            logger.info(f"  Cover page created")
            
            # Render cards (9 per page) using unified CardRenderer and PageRenderer
            card_count = 0
            page_number = 1
            total_cards = len(self.pokemon_list)
            
            for idx, pokemon in enumerate(self.pokemon_list, 1):
                # Progress indicator every 10 cards
                if idx % 10 == 0 or idx == 1:
                    progress_pct = (idx / total_cards) * 100
                    bar_width = 30
                    filled = int(bar_width * progress_pct / 100)
                    bar = '█' * filled + '░' * (bar_width - filled)
                    print(f"\r  [{bar}] {idx}/{total_cards} ({progress_pct:.0f}%)", end='', flush=True)
                
                # Check if we need a new page
                if self.page_renderer.should_start_new_page(card_count):
                    # Add footer before showing page
                    self.page_renderer.add_footer(c)
                    c.showPage()
                    page_number += 1
                    logger.debug(f"  Page {page_number} created ({card_count}/{total_cards} cards)")
                
                # Create new page if needed
                if self.page_renderer.get_card_index_on_page(card_count) == 0:
                    self.page_renderer.create_page(c)
                
                # Calculate position on page
                card_position = self.page_renderer.get_card_index_on_page(card_count)
                
                # Draw the card using unified CardRenderer
                self.page_renderer.add_card_to_page(c, self.card_renderer, pokemon, card_position)
                card_count += 1
            
            # Add footer to last page before showing it
            self.page_renderer.add_footer(c)
            
            # Final page
            c.showPage()
            
            # Save and close the PDF
            append_project_notice(c, self.language)
            c.save()
            
            print()  # Newline after progress bar
            
            file_size_mb = pdf_file_path.stat().st_size / 1024 / 1024
            total_pages = self.page_renderer.get_total_pages(card_count, include_cover=True) + 1
            self.page_count = total_pages  # Store for testing/reporting
            
            logger.info(f"✓ PDF generated successfully: {pdf_file_path}")
            logger.info(f"  - Pages: {total_pages} (with cover)")
            logger.info(f"  - Cards: {card_count}")
            logger.info(f"  - Size: {file_size_mb:.2f} MB")
            
            return pdf_file_path
        
        except IOError as e:
            logger.error(f"Failed to write PDF: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during PDF generation: {e}")
            import traceback
            traceback.print_exc()
            raise


def generate_pdf_for_generation(generation: int, language: str = 'de', 
                               pokemon_data: list = None) -> Path:
    """
    Convenience function to generate a PDF for a specific generation.
    
    Args:
        generation: Pokémon generation (1-9)
        language: Language code (default: 'de')
        pokemon_data: List of pokemon data (if None, uses sample data)
    
    Returns:
        Path to generated PDF
    """
    generator = PDFGenerator(language, generation)
    
    if pokemon_data is None:
        # Generate sample data for testing
        pokemon_data = [
            {'name': f'Pokemon {i}', 'types': ['Normal']}
            for i in range(1, GENERATION_INFO[generation]['count'] + 1)
        ]
    
    return generator.generate(pokemon_data)
