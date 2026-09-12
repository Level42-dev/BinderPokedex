#!/usr/bin/env python3
"""
Generate Pokémon Binder PDFs - Scope-Based Architecture

Generates PDFs for any scope defined in data/*.json files.
Each scope is a self-contained collection (Pokédex, TCG cards, variants, etc.).

Features:
- Unified architecture: One generator for all scopes
- Multi-language support (DE, EN, FR, ES, IT, JA, KO, ZH-HANS, ZH-HANT)
- CJK text rendering with proper fonts
- Cover pages with featured Pokémon
- 3x3 card layout per page
- Clean, modular architecture

Usage:
    # List all available scopes
    python generate_pdf.py --list
    
    # Generate specific scope in one language
    python generate_pdf.py --scope ExGen1_Single --language de
    
    # Generate specific scope in all languages
    python generate_pdf.py --scope Pokedex
    
    # Test mode (only 9 Pokémon for fast iteration)
    python generate_pdf.py --scope ExGen1_All --language en --test
"""

import json
import sys
import argparse
import logging
from pathlib import Path

# Check for required dependencies and provide helpful hint
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
except ImportError as e:
    # Will use CLIFormatter after it's imported, but need to show error before
    lines = [
        "\n" + "=" * 80,
        "❌ Missing Python Dependencies",
        "=" * 80,
        f"\nError: {e}",
        "\n💡 HINT: You need to activate the Python virtual environment first:",
        "\n   source venv/bin/activate",
        "\nOr run with the venv Python directly:",
        "\n   ./venv/bin/python scripts/generate_pdf.py",
        "\n" + "=" * 80 + "\n"
    ]
    print("\n".join(lines))
    sys.exit(1)

# Use the repository package path so another top-level ``lib`` imported by the
# fetcher cannot change which PDF modules resolve during a full test run.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.pdf.lib.fonts import FontManager
from scripts.pdf.lib.variant_pdf_generator import VariantPDFGenerator
from scripts.pdf.lib.cli_formatter import CLIFormatter
from scripts.pdf.lib.cli_validator import (
    GenerationValidator,
    LanguageValidator,
    VariantValidator,
    DirectoryValidator,
)
from scripts.pdf.lib.constants import LANGUAGES
from scripts.pdf.lib.generation_options import (
    POSTER_PAGE_MODES,
    pdf_output_filename,
    prepare_variant_data,
)
from scripts.poster_assets.scope_language import filter_variant_data_for_language

# Configure logging - suppress INFO during generation for clean output
logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)

# Suppress ReportLab font rendering warnings for known unsupported characters
# These are expected when rendering CJK text with limited font support
logging.getLogger('reportlab.pdfbase.ttfonts').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


def get_all_scopes(data_dir: Path) -> list:
    """Get all available scope names from data directory."""
    if not data_dir.exists():
        return []
    
    # Find all JSON files in data directory (excluding subdirectories and source/)
    json_files = sorted([f for f in data_dir.glob("*.json") if f.is_file()])
    
    # Extract scope names (filename without .json)
    scopes = [f.stem for f in json_files]
    
    return scopes


def list_available_templates(project_dir: Path):
    """
    List all available SVG templates.
    
    Args:
        project_dir: Project root directory
    
    Returns:
        Exit code (0 for success)
    """
    templates_dir = project_dir / "config" / "templates"
    
    if not templates_dir.exists():
        logger.error(f"❌ Templates directory not found: {templates_dir}")
        return 1
    
    print("\n📋 Available Templates:\n")
    
    # Card templates
    cards_dir = templates_dir / "cards"
    if cards_dir.exists():
        card_templates = sorted([f.stem for f in cards_dir.glob("*.svg")])
        if card_templates:
            print("  Card Templates (63×88mm):")
            for template in card_templates:
                print(f"    • {template}")
        else:
            print("  Card Templates: (none)")
    else:
        print("  Card Templates: (directory not found)")
    
    # Page templates
    pages_dir = templates_dir / "pages"
    if pages_dir.exists():
        page_templates = sorted([f.stem for f in pages_dir.glob("*.svg")])
        if page_templates:
            print("\n  Page Templates (A4):")
            for template in page_templates:
                print(f"    • {template}")
        else:
            print("\n  Page Templates: (none)")
    else:
        print("\n  Page Templates: (directory not found)")
    
    # Cover templates
    covers_dir = templates_dir / "covers"
    if covers_dir.exists():
        cover_templates = sorted([f.stem for f in covers_dir.glob("*.svg")])
        if cover_templates:
            print("\n  Cover Templates (A4):")
            for template in cover_templates:
                print(f"    • {template}")
        else:
            print("\n  Cover Templates: (none)")
    else:
        print("\n  Cover Templates: (directory not found)")
    
    print("\nUsage:")
    print("  python generate_pdf.py --scope Pokedex --card-template classic")
    print("  python generate_pdf.py --scope ExGen1 --card-template classic --page-template grid_3x3\n")
    
    return 0


def main():
    """Parse arguments and generate PDFs."""
    parser = argparse.ArgumentParser(
        description="Generate multi-language Pokémon binder PDFs with CJK support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate all PDFs (consolidated pokedex + variants) for all languages
  python generate_pdf.py
  
  # Generate German consolidated Pokédex
  python generate_pdf.py --type pokedex --language de
  
  # Generate Japanese consolidated Pokédex for Gen 1-3 only
  python generate_pdf.py --type pokedex --language ja --generations 1-3
  
  # Generate Mega Evolution variants in English
  python generate_pdf.py --type variant --variant mega --language en
  
  # Generate all variant categories for German
  python generate_pdf.py --type variant --variant all --language de
  
  # List available variants
  python generate_pdf.py --type variant --list
        """
    )
    
    parser.add_argument(
        "--scope",
        "-s",
        type=str,
        default=None,
        help="Scope to generate PDF for. Examples: 'Pokedex', 'ExGen1_Single', 'ExGen1_All'. Corresponds to JSON files in data/ folder. OMIT to list all available scopes."
    )
    
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        default=None,
        help="Language code (de, en, fr, es, it, ja, ko, zh-hans, zh-hant). OMIT to generate all languages (default). NEVER use 'all' as value."
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        default=False,
        help="List all available scopes (JSON files in data/ directory)"
    )
    
    parser.add_argument(
        "--skip-images",
        action="store_true",
        default=False,
        help="Skip remote card images while retaining local logos and poster artwork"
    )

    parser.add_argument(
        "--skip-poster",
        action="store_true",
        default=False,
        help="Skip optional poster pages enabled by a scope's poster.yaml"
    )

    parser.add_argument(
        "--poster-page-mode",
        choices=POSTER_PAGE_MODES,
        default="cards",
        help=(
            "Render enabled posters as cuttable cards (default) or as one "
            "continuous full page"
        ),
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        default=False,
        help="Test mode: render only the first 9 cards across all sections"
    )
    
    parser.add_argument(
        "--verbose",
        "-vv",
        action="store_true",
        default=False,
        help="Verbose mode: show detailed logs during generation"
    )
    
    parser.add_argument(
        "--card-template",
        type=str,
        default=None,
        help="SVG template name for card rendering (e.g., 'classic'). Omit to use legacy rendering. Use --list-templates to see available templates."
    )
    
    parser.add_argument(
        "--page-template",
        type=str,
        default=None,
        help="SVG template name for page layout (e.g., 'grid_3x3'). Omit to use legacy layout. Use --list-templates to see available templates."
    )
    
    parser.add_argument(
        "--cover-template",
        type=str,
        default=None,
        help="SVG template name for cover page (e.g., 'simple'). Omit to use legacy cover. Use --list-templates to see available templates."
    )
    
    parser.add_argument(
        "--list-templates",
        action="store_true",
        default=False,
        help="List all available SVG templates (cards, pages, covers)"
    )
    
    args = parser.parse_args()
    if args.skip_poster and args.poster_page_mode != "cards":
        parser.error(
            "--poster-page-mode cannot be combined with --skip-poster"
        )
    
    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        logging.getLogger().handlers[0].setFormatter(
            logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        )
    
    # Get workspace directories
    script_dir = Path(__file__).parent  # scripts/pdf/
    project_dir = script_dir.parent.parent  # project root
    data_dir = project_dir / "data" / "output"  # Read from output directory
    
    if not data_dir.exists():
        logger.error(f"❌ Data directory not found: {data_dir}")
        return 1
    
    # Handle --list-templates: show all available templates
    if args.list_templates:
        return list_available_templates(project_dir)
    
    # Handle --list: show all available scopes
    if args.list or args.scope is None:
        return list_available_scopes(data_dir)
    
    # Handle --scope all: generate PDFs for all scopes
    if args.scope.lower() == 'all':
        scopes = get_all_scopes(data_dir)
        
        if not scopes:
            logger.error(f"❌ No scopes found in {data_dir}")
            return 1
        
        # Ensure Pokedex is first if it exists
        if 'Pokedex' in scopes:
            scopes.remove('Pokedex')
            scopes.insert(0, 'Pokedex')
        
        CLIFormatter.section_header(f"PDF Generation - All Scopes ({len(scopes)})")
        print(f"\n📋 Processing {len(scopes)} scopes:\n")
        for scope in scopes:
            print(f"   • {scope}")
        print()
        
        # Determine languages
        if args.language:
            languages = [args.language]
            if args.language not in LANGUAGES:
                logger.error(f"❌ Invalid language: {args.language}")
                logger.info(f"   Valid languages: {', '.join(LANGUAGES.keys())}")
                return 1
        else:
            languages = list(LANGUAGES.keys())  # All 9 languages
        
        print(f"🌍 Languages: {', '.join([LANGUAGES[l]['name'] for l in languages])}\n")
        print("=" * 80)
        
        # Process each scope
        failed_scopes = []
        total_pdfs_generated = 0
        
        for i, scope in enumerate(scopes, 1):
            scope_file = data_dir / f"{scope}.json"
            
            if not scope_file.exists():
                logger.warning(f"⚠️  Skipping {scope}: File not found")
                failed_scopes.append(scope)
                continue
            
            print(f"\n[{i}/{len(scopes)}] Generating PDFs for: {scope}")
            print("-" * 80)
            
            try:
                result = generate_scope_pdf(
                    scope_name=scope,
                    scope_file=scope_file,
                    languages=languages,
                    output_dir=project_dir / 'output',
                    script_dir=script_dir,
                    skip_images=args.skip_images,
                    skip_poster=args.skip_poster,
                    poster_page_mode=args.poster_page_mode,
                    test_mode=args.test,
                    card_template=args.card_template,
                    page_template=args.page_template,
                    cover_template=args.cover_template
                )
                
                if result != 0:
                    failed_scopes.append(scope)
                    logger.warning(f"⚠️  Scope {scope} failed, continuing with next...")
                else:
                    total_pdfs_generated += len(languages)  # Approx count
            
            except Exception as e:
                logger.error(f"❌ Error processing {scope}: {e}")
                failed_scopes.append(scope)
                logger.warning(f"⚠️  Continuing with next scope...")
            
            if i < len(scopes):
                print("=" * 80)
        
        # Summary
        print("\n" + "=" * 80)
        CLIFormatter.section_header("Summary - All Scopes")
        print(f"\n   Total scopes:    {len(scopes)}")
        print(f"   ✅ Successful:   {len(scopes) - len(failed_scopes)}")
        print(f"   ❌ Failed:       {len(failed_scopes)}")
        
        if failed_scopes:
            print(f"\n⚠️  Failed scopes: {', '.join(failed_scopes)}")
        
        CLIFormatter.section_footer()
        
        return 1 if failed_scopes else 0
    
    # Single scope mode
    # Validate scope exists
    scope_file = data_dir / f"{args.scope}.json"
    if not scope_file.exists():
        logger.error(f"❌ Scope not found: {args.scope}")
        logger.info(f"   Expected file: {scope_file}")
        logger.info(f"\n💡 Use --list to see all available scopes")
        return 1
    
    # Determine languages
    if args.language:
        languages = [args.language]
        if args.language not in LANGUAGES:
            logger.error(f"❌ Invalid language: {args.language}")
            logger.info(f"   Valid languages: {', '.join(LANGUAGES.keys())}")
            return 1
    else:
        languages = list(LANGUAGES.keys())
    
    # Generate PDFs for the scope
    return generate_scope_pdf(
        scope_name=args.scope,
        scope_file=scope_file,
        languages=languages,
        output_dir=project_dir / 'output',
        script_dir=script_dir,
        skip_images=args.skip_images,
        skip_poster=args.skip_poster,
        poster_page_mode=args.poster_page_mode,
        test_mode=args.test,
        card_template=args.card_template,
        page_template=args.page_template,
        cover_template=args.cover_template
    )


def list_available_scopes(data_dir: Path) -> int:
    """List all available scopes (JSON files in data directory)."""
    CLIFormatter.section_header("Available Scopes")
    
    # Find all JSON files in data directory (excluding subdirectories)
    json_files = sorted(data_dir.glob("*.json"))
    
    if not json_files:
        logger.error(f"❌ No scope files found in {data_dir}")
        return 1
    
    print(f"\n📂 Found {len(json_files)} scope(s) in {data_dir}:\n")
    
    for json_file in json_files:
        scope_name = json_file.stem
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract metadata
            scope_type = data.get('type', 'unknown')
            sections = data.get('sections', {})
            
            # Count total cards across all sections
            total_pokemon = 0
            for section_data in sections.values():
                cards_list = section_data.get('cards', [])
                total_pokemon += len(cards_list)
            
            # Get title from first section (usually 'normal')
            title = "Unknown"
            if sections:
                first_section = next(iter(sections.values()))
                title_dict = first_section.get('title', {})
                title = title_dict.get('en', title_dict.get('de', 'Unknown'))
            
            # Format output
            type_icon = "📚" if scope_type == "pokedex" else "✨" if scope_type == "variant" else "❓"
            size_str = f"{json_file.stat().st_size / 1024:.0f} KB"
            
            print(f"  {type_icon} {scope_name:20s} | {total_pokemon:3d} entries | {size_str:>8s} | {title}")
            
        except Exception as e:
            print(f"  ❌ {scope_name:20s} | Error reading file: {e}")
    
    print(f"\n💡 Usage: python generate_pdf.py --scope <name> --language de")
    CLIFormatter.section_footer()
    return 0


def generate_scope_pdf(scope_name: str, scope_file: Path, languages: list, 
                       output_dir: Path, script_dir: Path,
                       skip_images: bool = False, test_mode: bool = False,
                       card_template: str = None, page_template: str = None, 
                       cover_template: str = None,
                       skip_poster: bool = False,
                       poster_page_mode: str = "cards") -> int:
    """
    Generate PDF for a specific scope.
    
    Args:
        scope_name: Name of the scope (e.g., "Pokedex", "ExGen1_Single")
        scope_file: Path to the scope JSON file
        languages: List of language codes to generate
        output_dir: Base output directory
        script_dir: Script directory for relative paths
        skip_images: Skip image processing
        skip_poster: Skip an otherwise enabled poster page
        poster_page_mode: Render an enabled poster as cards or one full page
        test_mode: Use only first 9 Pokemon for testing
        card_template: Optional SVG template for cards
        page_template: Optional SVG template for pages
        cover_template: Optional SVG template for covers
    
    Returns:
        0 on success, 1 on failure
    """
    CLIFormatter.section_header(f"PDF Generation - {scope_name}")
    CLIFormatter.key_value("Scope:", scope_name)
    CLIFormatter.key_value("Languages:", ", ".join(languages))
    CLIFormatter.key_value("Output dir:", str(output_dir))
    
    try:
        # Load scope data
        with open(scope_file, 'r', encoding='utf-8') as f:
            scope_data = json.load(f)
        
        # Check for language availability metadata (TCG sets)
        available_languages = scope_data.get('available_languages', None)
        
        total_generated = 0
        total_failed = 0
        total_skipped = 0
        
        for language in languages:
            # Check if language is available for this scope
            if available_languages and language not in available_languages:
                logger.warning(f"⚠️  Skipping {LANGUAGES.get(language, {}).get('name', language.upper())}: Not available for {scope_name} (set not released in this language)")
                total_skipped += 1
                continue
            try:
                logger.info(f"\n📊 Generating {scope_name} → {LANGUAGES.get(language, {}).get('name', language.upper())}")
                
                # Generate PDF using unified VariantPDFGenerator (works for all types)
                generated = _generate_variant_pdf(
                    variant_data=scope_data,
                    language=language,
                    output_dir=output_dir / language,
                    script_dir=script_dir,
                    skip_images=skip_images,
                    skip_poster=skip_poster,
                    poster_page_mode=poster_page_mode,
                    test_mode=test_mode,
                    scope_name=scope_name,
                    card_template=card_template,
                    page_template=page_template,
                    cover_template=cover_template
                )
                if not generated:
                    raise RuntimeError(
                        f"PDF renderer reported failure for {scope_name}/{language}"
                    )
                
                total_generated += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to generate {scope_name} for {language}: {e}")
                if logger.isEnabledFor(logging.INFO):
                    import traceback
                    traceback.print_exc()
                total_failed += 1
        
        # Summary
        CLIFormatter.section_footer()
        if total_skipped > 0:
            print(f"✅ Generated: {total_generated} | ⚠️  Skipped: {total_skipped} | ❌ Failed: {total_failed}")
        else:
            print(f"✅ Generated: {total_generated} | ❌ Failed: {total_failed}")
        
        return 0 if total_failed == 0 else 1
        
    except Exception as e:
        logger.error(f"❌ Failed to load scope: {e}")
        return 1




def handle_variant_mode(args, script_dir, project_dir, data_dir, variants_dir):
    """Handle variant-based PDF generation."""
    # Validate variant directory
    if not variants_dir.exists():
        logger.error(f"❌ Variants directory not found: {variants_dir}")
        logger.info(f"   Please run Phase 1 setup first to create variant infrastructure")
        return 1
    
    meta_file = variants_dir / "meta.json"
    if not meta_file.exists():
        logger.error(f"❌ Variants metadata not found: {meta_file}")
        return 1
    
    # Load variant metadata
    with open(meta_file, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    
    # Determine which variants to generate
    if args.variant is None:
        # Default: generate all variants
        variants_to_generate = [cat['id'] for cat in meta['variant_categories']]
    elif args.variant.lower() == 'all':
        variants_to_generate = [cat['id'] for cat in meta['variant_categories']]
    else:
        # Parse comma-separated list
        variant_ids = [v.strip() for v in args.variant.lower().split(',')]
        valid_ids = {cat['id'] for cat in meta['variant_categories']}
        
        variants_to_generate = []
        for vid in variant_ids:
            if vid not in valid_ids:
                logger.error(f"❌ Unknown variant: {vid}")
                logger.info(f"   Valid variants: {', '.join(sorted(valid_ids))}")
                return 1
            variants_to_generate.append(vid)
    
    # Validate language
    if args.language:
        if args.language not in LANGUAGES:
            logger.error(f"❌ Unsupported language: {args.language}")
            logger.info(f"   Supported: {', '.join(LANGUAGES.keys())}")
            return 1
        languages = [args.language]
    else:
        languages = list(LANGUAGES.keys())
    

    # Generate variant PDFs
    CLIFormatter.section_header("PDF Generation - Pokémon Variants (v3.0)")
    CLIFormatter.key_value("Variants:", ", ".join(variants_to_generate))
    CLIFormatter.key_value("Languages:", ", ".join(languages))
    CLIFormatter.key_value("Output dir:", str(project_dir / 'output'))
    CLIFormatter.key_value("Data dir:", str(variants_dir))
    
    total_generated = 0
    total_failed = 0
    
    for variant_id in variants_to_generate:
        variant_meta = next((cat for cat in meta['variant_categories'] if cat['id'] == variant_id), None)
        if not variant_meta:
            logger.error(f"❌ Variant metadata not found: {variant_id}")
            total_failed += 1
            continue
        
        variant_file = variants_dir / variant_meta['json_file']
        
        if not variant_file.exists():
            logger.warning(f"⏭️  Variant not yet implemented: {variant_id} (file: {variant_file.name})")
            continue
        
        for language in languages:
            try:
                logger.info(f"\n📊 Generating {variant_id} → {LANGUAGES.get(language, {}).get('name', language.upper())}")
                
                # Load variant data
                with open(variant_file, 'r', encoding='utf-8') as f:
                    variant_data = json.load(f)
                
                # Generate PDF
                generated = _generate_variant_pdf(
                    variant_data=variant_data,
                    language=language,
                    output_dir=project_dir / 'output' / language,
                    script_dir=script_dir
                )
                if not generated:
                    raise RuntimeError(
                        f"PDF renderer reported failure for {variant_id}/{language}"
                    )
                
                total_generated += 1
                logger.info(f"   ✅ Generated: {variant_id}_{language}.pdf")
            except Exception as e:
                logger.error(f"❌ Error generating variant PDF: {e}")
                total_failed += 1
    
    # Summary
    CLIFormatter.progress_summary(total_generated, total_failed)
    
    return 0 if total_failed == 0 else 1


def _generate_variant_pdf(
    variant_data,
    language,
    output_dir,
    script_dir,
    skip_images=False,
    test_mode=False,
    scope_name=None,
    card_template=None,
    page_template=None,
    cover_template=None,
    skip_poster=False,
    poster_page_mode="cards",
):
    """Generate a PDF for a scope (variant or pokedex)."""
    from scripts.pdf.lib.pdf_generator import ImageCache
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use scope_name if provided, otherwise fall back to variant name
    if scope_name:
        filename_base = scope_name
    else:
        variant_name = variant_data.get('name', 'Variant')
        # Clean up filename (remove special characters)
        filename_base = variant_name.replace(' ', '_').replace('-', '_')
    
    # Generate output filename
    output_file = output_dir / pdf_output_filename(
        filename_base,
        language,
        skip_images=skip_images,
        skip_poster=skip_poster,
        poster_page_mode=poster_page_mode,
        test_mode=test_mode,
    )
    
    language_variant_data = filter_variant_data_for_language(
        variant_data,
        language,
    )
    prepared_variant_data = prepare_variant_data(
        language_variant_data,
        skip_images=skip_images,
        test_mode=test_mode,
    )

    # Initialize image cache for loading Pokémon images
    image_cache = ImageCache()
    
    # Extract type_translations if present in data
    type_translations = prepared_variant_data.get('type_translations')
    
    # Create and generate PDF
    pdf_gen = VariantPDFGenerator(
        variant_data=prepared_variant_data,
        language=language,
        output_file=output_file,
        image_cache=image_cache,
        type_translations=type_translations,
        card_template=card_template,
        page_template=page_template,
        cover_template=cover_template,
        include_poster=not skip_poster,
        poster_page_mode=poster_page_mode,
        scope_name=scope_name,
        poster_source_data=variant_data,
    )
    
    return pdf_gen.generate()


if __name__ == "__main__":
    sys.exit(main())
