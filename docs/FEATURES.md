# ✨ Features & Technical Details

## Project Status

### Phase 1: Generation PDFs ✅ COMPLETE
- 9 generations (Gen 1-9) with 1,025 Pokémon
- All 9 languages fully supported
- 81 PDFs generated (9 × 9 languages)

### Phase 2: Pokémon Variants ✅ COMPLETE
- **Mega Evolution** ✅ Complete
  - 87 Pokémon species with 92 Mega forms
  - PokeAPI form variety IDs correctly mapped (official artwork where available)
  - 9 language PDFs generated
  - Iconic Pokémon on covers (Charizard X, Mewtwo X, Gengar)

### Full TCG Support ✅ COMPLETE (v7.0+)
- 30 TCG scopes across the original Base era, 3 EX generations, Mega
  Evolution, and the full Scarlet & Violet era
- 31 total scopes (1 Pokédex + 30 TCG scopes)

### SVG Template System ✅ COMPLETE (v8.0)
- Full SVG-based card, page, and cover templates
- Live-editable in Inkscape, Illustrator, or any SVG editor

### CJK Fix & TCG Type Translations ✅ COMPLETE (v8.1)
- All 9 languages generate correct PDFs on Linux/CI
- TCG-exclusive energy types (Colorless, Darkness, Lightning, Metal) fully translated

## Language Support

### 9 Languages Supported

| Language | Code | Font | Type |
|----------|------|------|------|
| Deutsch | `de` | Helvetica | Latin |
| English | `en` | Helvetica | Latin |
| Español | `es` | Helvetica | Latin |
| Français | `fr` | Helvetica | Latin |
| Italiano | `it` | Helvetica | Latin |
| 日本語 | `ja` | Songti / WenQuanYi¹ | CJK |
| 한국어 | `ko` | Songti / WenQuanYi¹ | CJK |
| 简体中文 | `zh_hans` | Songti / WenQuanYi¹ | CJK |
| 繁體中文 | `zh_hant` | Songti / WenQuanYi¹ | CJK |

*¹ macOS: Songti.ttc (JA/ZH) and AppleGothic.ttf (KO) / STHeiti Medium.ttc (ZH-Hant).
Linux/CI: WenQuanYi Zen Hei (wqy-zenhei.ttc) registered as fallback for all CJK languages.*

### CJK Rendering

- **Proper text rendering** for Japanese (Hiragana, Katakana, Kanji)
- **Korean Hangul** support with TrueType fonts
- **Chinese** (Simplified & Traditional) with full Unicode support
- **Gender symbols** (♂/♀) working correctly in all languages
- **English subtitles** on non-English cards for readability
- **Bilingual covers** with localized variant names and English labels

## PDF Features

### Layout
- **3×3 card grid** (9 cards per page)
- **Cover page** for each generation/variant with featured elements
- **A4 format** (210 × 297 mm)
- **Print-ready** with precise measurements
- **Type-based header colors** with transparency
- **Featured Elements** on cover (up to 3 iconic Pokémon with trading cards or artwork)

### Content
- **Official Pokémon artwork** from PokéAPI
- **TCG set logos** embedded in PDF subtitles with [image] tag support
- **Species names** in target language
- **Variant names** (e.g., "Mega Venusaur" → "Mega Bisaflor" in German)
- **Multilingual set names** from TCGdex API (5 languages: DE, EN, FR, ES, IT)
- **Release dates** in set descriptions with localized labels
- **Type information** with type colors
- **National Pokédex number**
- **Height & weight** in metric units
- **Multilingual footers** with translation keys
- **Cutting guides** for easy card extraction

### Generation Covers
- Region name (Kanto, Johto, etc.)
- Pokédex range (#001-#151)
- Pokémon count in collection
- Generation-specific color scheme
- 3 iconic Pokémon images

### Variant Covers
- Variant type (Mega Evolution, etc.)
- Variant name (e.g., "Mega Evolution")
- Species and forms count
- Variant-specific color scheme
- Up to 3 iconic variant Pokémon images

### Optimization
- **File sizes:** 200-400 KB per generation, ~2MB per variant collection
- **Image compression:** JPEG quality 85 (balanced for crisp printing)
- **Image resolution:** Up to 100px on cards, 250px for featured images
- **In-memory caching:** Efficient batch processing with disk cache
- **URL image caching:** MD5-based temp directory caching for logos and external images

## Architecture

### Modular Design

```
scripts/lib/
├── __init__.py              # Package initialization
├── constants.py             # Language configs & URLs
├── fonts.py                 # Font management & registration
├── card_template.py         # Reusable card rendering
├── text_renderer.py         # Unicode-aware text rendering
├── pdf_generator.py         # Generation PDF orchestration
├── variant_pdf_generator.py # Variant PDF orchestration
├── pokeapi_client.py        # PokéAPI data fetching
├── data_storage.py          # File I/O & caching
├── rendering/
│   ├── logo_renderer.py     # Logo & image rendering with [image] tag support
│   └── image_cache.py       # URL image caching with MD5 hashing
└── form_fetchers/
    ├── __init__.py
    └── mega_evolution_fetcher.py  # Mega form fetching
```

### Key Principles

- ✅ **Template-based rendering** - Reusable templates for generation & variant PDFs
- ✅ **Translation callbacks** - Format translations passed as functions to templates
- ✅ **No monkey-patching** - Clean code without hacks
- ✅ **Proper error handling** - Graceful fallbacks
- ✅ **Type hints** - Better IDE support
- ✅ **Modular design** - Testable, reusable components
- ✅ **Separation of concerns** - Each module has clear responsibility
- ✅ **Custom field preservation** - Fetch scripts maintain custom data (e.g., iconic_pokemon_ids)

## Testing

### Test Coverage
- 15 unit tests
- 100% pass rate
- Tests for:
  - Font registration and availability
  - PDF rendering with CJK text
  - Text rendering with symbols
  - Image processing
  - Data enrichment

### Running Tests

```bash
python -m pytest scripts/tests/ -v
```

## Performance

### Generation Times

- **Gen 1 (151 Pokémon):** ~37 seconds
- **Gen 2 (100 Pokémon):** ~1m 7s
- **Gen 3-9 (774 Pokémon):** ~7m 47s
- **All 9 generations:** ~10 minutes
- **All 81 PDFs (9 gen × 9 lang):** ~1.5 hours
- **Mega Evolution (66 forms × 9 lang):** ~3 minutes

### Data Caching

- Pokémon data cached locally in JSON
- Cached data included in repository
- No API calls required after first fetch
- Reproducible builds from cache
- Custom fields (iconic_pokemon_ids, etc.) preserved across fetches

## Image Processing

### Smart Handling

1. **Download** from PokéAPI official artwork
2. **Remove background** (transparent → white)
3. **Compress** aggressively (quality 40)
4. **Optimize** resolution (100px max)
5. **Cache** in memory for batch processing

### Fallback Strategy

- Primary source: Official Pokémon artwork
- Fallback: Alternative image sources
- Last resort: Type-based placeholder colors

## System Requirements

### Minimum

- **Python 3.10+**
- **macOS** (for system fonts - required for CJK)
- **2 GB RAM**
- **Internet connection** (first run only, for API & images)

### Recommended

- **Python 3.11+**
- **4 GB RAM**
- **SSD** (faster processing)

## Dependencies

- **ReportLab 4.0.7** - PDF generation
- **Pillow 12.1.0** - Image processing
- **requests 2.31.0** - HTTP requests
- **urllib3** - Connection pooling

See [requirements.txt](../requirements.txt) for full list.
