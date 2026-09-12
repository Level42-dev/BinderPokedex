# Changelog

All notable changes to BinderPokedex are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### 🔧 Renderer Infrastructure

- Added a disposable native Apple-Silicon renderer runtime built from
  checksum-pinned `uv`, portable Python, ComfyUI source, and hash-locked Python
  dependencies without Homebrew Python, Git, or global package installation.
- Separated reusable model weights into an operator-selected external cache;
  runtime bundles retain only a symbolic link, while every render job continues
  to bind the exact model paths and SHA-256 values it requires.
- Added validated runtime packaging, model-cache rebinding, and destruction so
  transferred or directly bootstrapped runtimes can be removed without touching
  the external models.

## [10.0.0] - 2026-09-12

### ✨ Current Collections and Data

- Refreshed all 31 configured scopes from their current sources, reviewed every
  changed output, and locked the accepted 63-file dataset with a reproducible
  snapshot manifest and drift audit.
- Added the complete ME05 Dunkelnacht collection and updated the Mega Evolution
  era to seven scopes. Energy-only subsets remain intentionally outside the
  printable set collection.
- Recorded exact per-card language availability so a PDF no longer presents an
  untranslated card as if it had been released in the selected language.
- Preserved localized TCG identities such as `Ns Zoroark-ex` while keeping the
  National Pokédex on canonical owner-free species names.

### 🐛 German PDF and Promo Corrections

- Corrected the German Basic Energy names in SV01, SV02, SV03, and SV06.5.
- Reconciled SVP with 216 numbered German cards through `#224`, the eight real
  number gaps, and the unnumbered `Terapagos & Freunde` promo for 217 German
  inserts in total.
- Rebuilt MEP from its original promo identities, including `Serpiroyal #064`
  and `Glutexo #079`, instead of renumbering the selected cards sequentially.
- Added measured one- or two-line label fitting so long Trainer names stay
  inside their card and cutting boundaries.
- Added exact German title logos for Schwarze Blitze and Weiße Flammen and
  corrected the Stellarkrone panorama with anatomically correct Hopplo artwork.
- Added the reviewed Dunkelnacht panorama and replaced the Stürmische Funken
  panorama after bounded reference, resolution, model, and seed comparisons.
  All 42 set and aggregate-section targets now have enabled panoramas.

### 🔧 Release Quality

- Added fail-closed refresh behavior, change classification, release snapshot
  verification, and regression coverage for localized names, language filters,
  printed promo numbers, German logos, and safe label geometry.
- Release builds consume the committed data snapshot instead of silently
  fetching mutable card data during publication.
- Regression tests exercise real PDF poster routing for every release section;
  a disabled panorama or cover-only route fails the normal release test gate.
- New visual-review records explicitly distinguish agent inspection from human
  approval while retaining the same source, raw, print, and crop checks.
- The poster planner uses the importer's canonical subject selection, including
  explicit card slots, instead of incorrectly flagging a valid curated cast as stale.

## [9.0.0] - 2026-08-11

### ✨ Major Feature: Poster Artwork for Every Binder

- Added 41 reviewed and PDF-enabled poster openings covering every current TCG
  set, all nine Pokédex generations, and every EX subsection.
- Designed the continuous scenes around the physical 3×3 card grid, subject
  safe areas, localized title/logo space, and deterministic print geometry.
- Replaced a section's normal start page with its promoted poster while keeping
  the canonical cover as the missing/disabled and `--skip-poster` fallback.
- Added a continuous `full-page` poster mode alongside the default cuttable
  nine-card page.
- Completed localized poster copy for all 266 current target/language
  combinations.
- Kept ComfyUI/Metal authoring separate from release consumption: CI and
  end users require only the reviewed, versioned repository assets.
- Generated the reviewed v9 poster candidates on an isolated remote Apple
  Silicon render worker through portable, hash-pinned jobs. The worker's
  hostname, network address, credentials, and machine-specific paths are
  intentionally not part of the repository or release artifacts.

### 🔧 Release and Quality

- Pull requests and tags share one release-candidate build that fetches every
  scope, validates all promoted posters, generates all PDFs, and verifies all
  nine language archives.
- GitHub Release descriptions are now rendered and verified from the versioned
  release-note configuration instead of a hard-coded historical announcement.
- Separated collector-facing README and GitHub Release news from the technical
  changelog. Release automation now replaces one dedicated README news block
  instead of growing a second version history on the project start page.
- Added bilingual v9.0 feature news, an approved key visual with exact
  BinderPokedex content and matching card scans, and an actual PDF poster
  screenshot.
- Last complete project verification: 554 passed, 1 skipped; the focused
  release communication suite passes 8/8 checks; 41/41 promotions remain at
  2368 × 3268 px and effective 300 dpi.

## [8.4.0] - 2026-07-15

### ✨ New Features

**Pokemon Jungle (base2) and Fossil (base3)**
- Added Jungle (base2, 1999) scope with 64 cards: 63 Pokémon, 1 Trainer
- Added Fossil (base3, 1999) scope with 62 cards: 57 Pokémon, 5 Trainers
- Available in de, en, fr, es, it — ja/ko/zh were not released for these sets and are correctly skipped

### 🐛 Bug Fixes

**Classic Trainer card artwork**
- Older Trainer cards without a TCGdex subtype now use the generic Item artwork instead of rendering without an image

---

## [8.3.0] - 2026-07-12

### ✨ New Features

**Pokemon Base Set (base1)**
- Added Base Set (base1, 1999) scope with 102 cards: 69 Pokémon, 26 Trainers, 7 Energy
- Available in de, en, fr, es, it — ja/ko/zh were not released for this set and are correctly skipped

---

## [8.1.1] - 2026-07-01

### 🐛 Bug Fixes

**CI: Chinese ZIPs missing from release**
- Output directories use underscores (`zh_hans`, `zh_hant`) but the zip loop used hyphens (`zh-hans`, `zh-hant`), causing the `if [ -d ]` check to silently skip both Chinese languages
- Added a `WARNING` echo for any missing directory to make future omissions visible

---

## [8.1.0] - 2026-07-01

### 🐛 Bug Fixes

**CJK font fallback on Linux/CI**
- Korean (`ko`) and Traditional Chinese (`zh_hant`) PDFs were empty on Linux/CI because `AppleGothic` and `STHeitiMedium` are macOS-exclusive fonts
- `FontManager` now remaps any unregistered CJK font to the best available fallback (WenQuanYi/Noto) after all registration attempts, preventing a `KeyError` crash before `c.save()` is reached
- Updated font tests to assert that the returned font name is actually registered, rather than checking for a specific macOS font name

**TCG-exclusive type translations**
- `Colorless`, `Darkness`, `Lightning`, and `Metal` are TCG-specific energy type names that were absent from all translation files — the renderer fell back to English for every language
- Added full translations in all 9 languages to both `i18n/translations.json` and `enrichments/type_translations.json`
- Mapping: `Darkness` → Dark, `Lightning` → Electric, `Metal` → Steel equivalents per language

---

## [8.0.0] - 2026-07-01

### ✨ New Features

**SVG WYSIWYG Template System**
- Full SVG-based card, page, and cover templates — editable live in any SVG editor
- Templates support inline logo embedding and automatic image placement
- New CLI parameters: `--card-template`, `--page-template`, `--cover-template`, `--list-templates`
- Backwards-compatible: existing renders are unchanged when no template flag is passed
- Base templates provided for cards, pages, and covers

**MEP Bulbapedia Supplement**
- MEP set expanded from 10 → 55 cards via Bulbapedia data supplement
- Covers all missing cards not available in TCGdex

### 🐛 Bug Fixes

- Preserved PNG transparency in image cache and all rendered PDFs
- Fixed TCG multilingual card name handling (incorrect names in non-English languages)
- Fixed template loading paths and SVG import resolution
- Added section artwork fallbacks for MEP-015, MEP-037, MEP-038

### 🔧 Technical Improvements

- `data/pokemon_images_cache/` excluded from git tracking via `.gitignore`
- CI workflow: removed no-op "Clean old PDFs" step (output never tracked in git)
- CI workflow: upgraded to `setup-python@v5`, Python 3.12, `action-gh-release@v2`, added pip cache
- Release body now uses dynamic tag name instead of hardcoded version string
- Test suite: replaced `return True/False` pattern with proper `assert` statements (no more `PytestReturnNotNoneWarning`)

### 📄 Documentation

- Added comprehensive SVG template system specification (`docs/SVG_WYSIWYG_TEMPLATES.md`)

---

## [7.2.0] - 2026-02-05

### ✨ New Features

**Featured Elements on Section Covers**
- Added visual highlights to every section cover page
- 3 most iconic Pokémon automatically selected per section based on priority rankings
- Smart content detection:
  - TCG Sets: Trading card images from TCGdex API
  - National Pokédex: Official artwork from PokeAPI
- Priority system ranks Pokémon by importance (starters: 100, legendaries: 95-100, others: 0-90)

### 🔧 Technical Improvements

**Featured Elements Architecture**
- Implemented format-agnostic pipeline step: `enrich_featured_elements`
- 3 card format handlers with automatic detection:
  - ExGen: TCG cards with `tcg_card` sub-object
  - TCG-Set: Modern cards with `localId` (ME*, SV* scopes)
  - Pokédex: PokeAPI official artwork
- Automatic fallback to PokeAPI artwork when TCG images unavailable (e.g., MEP set)
- Unified data structure for all content types
- Efficient caching system (~800KB-1MB per element)

**Code Quality**
- Refactored image download logic into reusable method
- Centralized series mapping for TCGdex URLs
- Improved error handling with graceful fallbacks
- Backward compatibility maintained (`featured_cards` → `featured_elements`)

### 📦 Scope Coverage

**All 25 Scopes Supported:**
- ✅ Pokédex (9 generations with starter Pokémon)
- ✅ ExGen1-3 (Classic ex cards)
- ✅ ME01, ME02, ME02.5 (Mega Evolution sets)
- ✅ MEP (with PokeAPI fallback)
- ✅ SV01-SV10, SVP (Scarlet & Violet sets)
- ✅ All special sets (SV03.5, SV04.5, SV06.5, SV08.5, SV10.5B, SV10.5W)

### 🎨 Visual Improvements

- Section covers now display 3 featured cards/artwork elements
- Consistent layout across all scope types
- Proper aspect ratio handling (TCG portrait vs. Pokédex square)
- High-quality images (400×550px for TCG, 475×475px for Pokédex)

### 📄 Documentation

- Added `docs/FEATURED_CARDS.md` (will be updated to FEATURED_ELEMENTS.md)
- Updated architecture documentation
- Enhanced code documentation with handler details

---

## [7.1.0] - 2026-02-03

### 🐛 Bug Fixes

**TCG Images Fixed**
- **Critical Fix:** Fixed missing Pokémon images in all TCG sets
- Resolved pipeline architecture flaw in `fix_missing_dex_ids` step
- All Pokémon cards now display correct artwork in generated PDFs
- Regenerated all 225 PDFs with complete images

### 🔧 Technical Details
- Made `fix_missing_dex_ids` step consistent with pipeline architecture
- Now uses `context.data['tcg_set_source']` instead of file I/O
- `source_path` parameter is now optional (only for debugging/caching)
- Updated ME02.5.yaml config to remove redundant `source_path` parameter
- 26 files updated with fixed pipeline and regenerated data

### Impact
**All TCG Sets** now show Pokémon artwork correctly in PDFs (previously only trainer/energy cards had images)

---

## [7.0.0] - 2026-02-02

### 🎯 Major Changes

**Complete TCG Support & Scope System**
- **25 Scopes Total:** National Pokédex + 24 TCG sets
  - 3 EX Generation sets (ExGen1, ExGen2, ExGen3)
  - 21 Modern TCG sets (ME01, ME02, ME02.5, MEP, SV01-SV10, SVP)
- All Scarlet & Violet TCG sets (SV01-SV10 + special sets)
- Paldea Era support (ME01, ME02, ME02.5, MEP)
- Auto-discovery system with batch generation
- Logo validation with automatic fallback
- Multilingual TCG metadata (up to 9 languages)

**System Improvements**
- Scope-based configuration for flexible data fetching
- Extended Pokemon image cache (1025+ Pokemon)
- Type translation enrichment system
- Batch PDF generation with `--scope all`
- Improved pipeline error handling and validation

**PDF Generation**
- 225 total PDFs across all scopes and languages
- Per-language ZIP archives for easy distribution
- Optimized file sizes and generation speed

### 📊 Statistics
- **Pokémon Coverage:** 1,025 Pokémon (all 9 generations)
- **TCG Sets:** 24 complete sets with multilingual support
- **Languages:** 9 (DE, EN, FR, ES, IT, JA, KO, ZH-Hans, ZH-Hant)
- **Total PDFs:** 225 (9 for Pokedex + EX sets, 5 for most TCG sets)

### 🔧 Technical Details
- Enhanced scope system with YAML configuration
- TCGdex API integration for all modern sets
- Automatic dexId fixing for trainer-owned and special Pokémon
- Section-based data format for TCG sets
- Logo embedding with fallback handling

---

## [6.0.0] - 2026-01-30

### 🎯 Major Changes
- **Complete Data Fetcher Redesign** - New modular pipeline architecture
  - Step-based processing with clear separation of concerns
  - Context-driven data flow between pipeline steps
  - Scope-based configuration (Pokedex, ExGen1, ExGen2, ExGen3, ME01)
  - Comprehensive documentation: DATA_FETCHER.md

- **TCG Set Support** - Complete TCGdex integration
  - Multilingual card names from TCGdex API (5 languages: DE, EN, FR, ES, IT)
  - Set logos embedded in PDFs with [image] tag support
  - Release dates in set descriptions with localized labels
  - New pipeline steps: fetch_tcgdex_set, enrich_tcg_names_multilingual, transform_to_sections_format
  - Example scope: ME01 (Miraidon ex Starter Deck)

- **URL Image Caching** - MD5-based external image caching
  - Temporary directory caching for logos and external images
  - MD5 hash of URL as cache key
  - ImageReader with mask='auto' for PNG transparency
  - New logo_renderer module for [image] tag parsing
  - Prevents duplicate downloads across PDF generation

- **Image Cache Redesign** - URL-based identifiers prevent collisions
  - New format: `pokemon_{id}_{url_identifier}_{size}.jpg`
  - Prevents collisions for form variants (Mega X/Y, Primal forms)
  - Unified caching between fetcher and PDF generator
  - Complete specification: IMAGE_CACHE.md

- **Multilingual Form Suffix Preservation** - X/Y/Primal suffixes across all 9 languages
  - Extract suffix from English name (e.g., " X", " Y", "-Primal")
  - Apply to all language translations automatically
  - Example: "Mega Glurak X" (German) instead of just "Mega Glurak"

- **Project Restructuring** - Clear separation of concerns
  - `scripts/fetcher/` - Data fetching and pipeline processing
  - `scripts/pdf/` - PDF generation and rendering
  - Removed obsolete configuration options

### 🐛 Fixes
- Fixed image cache collisions for form variants (Mega X/Y)
- Corrected ExGen3 featured Pokémon list (Mega section: 150→448)
- Removed obsolete `use_pokeapi_artwork` configuration
- Fixed Python syntax errors in docstrings (Unicode arrows, malformed strings)

### 🔧 Technical Details
- New pipeline engine with step-based processing
- Enhanced name enrichment preserving form suffixes
- GitHub Actions workflow fixes for automated releases
- Updated all scopes to use new pipeline architecture
- Logo rendering with inline image support
- MD5-based URL caching in temp directory

### 📚 Documentation
- Added `docs/DATA_FETCHER.md` - Pipeline architecture and usage
- Added `docs/IMAGE_CACHE.md` - Cache specification and design
- Updated `docs/ARCHITECTURE.md` - Overall project architecture
- Updated `docs/VARIANTS_ARCHITECTURE.md` - Variant system details
- Updated `docs/FEATURES.md` - TCG set features and URL caching
- Updated `README.md` - TCGdex integration and usage examples
- Comprehensive README updates with v6.0 information

### Impact
**Mega Charizard X** now displays correct image and name ("Mega Glurak X" in German, not just "Mega Glurak")
**TCG Sets** now have proper multilingual metadata with logos and release dates

### Migration from 5.0
1. Delete old cache: `rm -rf data/pokemon_images_cache/`
2. Re-fetch all data using new scopes:
   ```bash
   python scripts/fetcher/fetch.py --scope Pokedex
   python scripts/fetcher/fetch.py --scope ExGen1
   python scripts/fetcher/fetch.py --scope ExGen2
   python scripts/fetcher/fetch.py --scope ExGen3
   python scripts/fetcher/fetch.py --scope ME01
   ```
3. Generate PDFs with new paths:
   ```bash
   python scripts/pdf/generate_pdf.py --language de --scope Pokedex
   python scripts/pdf/generate_pdf.py --language de --scope ME01
   ```

---

## [5.0.0] - 2026-01-23

### 🐛 Bug Fixes

**CJK Font Rendering**
- Fixed font warnings and missing CJK characters in GitHub Actions
- Added Noto Sans CJK font installation for Linux environments
- Implemented automatic font fallback support
- Japanese, Korean, and Chinese characters now render properly in all PDFs

### 🔧 Technical Details

**Cross-Platform Font Support**
- macOS: Songti SC/TC (system fonts)
- Linux: Noto Sans CJK (auto-installed)
- Automatic font fallback detection
- Proper CJK character rendering in PDF generation

### 📊 Stats
- **Total PDFs:** 117 (81 generations + 36 variants)
- **Total Pokémon:** 1,025+ including variants
- **Languages:** 9 (DE, EN, FR, ES, IT, JA, KO, ZH, ZH-T)
- **Size per PDF:** 5-8 MB with embedded images

---

## [4.3.0] - 2026-01-30

### Fixed
- **Image Cache Collision Bug** - Mega Evolution forms (X/Y) and other variants now display correct images
  - Root cause: Cache used only `pokemon_{id}_{size}` format, causing collisions
  - Example: Charizard (ID 6) cache was shared between normal and Mega X/Y forms
  - Solution: Redesigned cache to use `pokemon_{id}_{url_identifier}_{size}` format
  - Impact: All 17 Mega variants in ExGen3 now show correct artwork
  
- **Form Suffix Preservation** - X/Y/Primal suffixes now appear correctly in all 9 languages
  - Root cause: Name enrichment step stripped form suffixes during translation
  - Example: "Mega Charizard X" became "Mega Glurak" (German) instead of "Mega Glurak X"
  - Solution: Extract suffix from English name, apply to all language translations
  - Impact: All form variants properly labeled in DE, EN, FR, ES, IT, JA, KO, ZH_HANS, ZH_HANT

- **ExGen3 Featured Pokémon** - Corrected Mega section featured list
  - Issue: Mewtwo (ID 150) was configured but doesn't exist in ExGen3 Mega section
  - Changed: 150 (Mewtwo) → 448 (Lucario)
  - Current: Charizard X (6), Gengar (94), Lucario (448)

### Changed
- **Code Cleanup** - Removed obsolete `use_pokeapi_artwork` configuration option
  - Reason: TCGdex images include card frames, unsuitable for binder layout
  - PokeAPI official artwork is now always used for all variants
  - Files updated: 3 YAML configs, 3 transform steps
  
- **Unified Caching Strategy** - Synchronized cache implementation across components
  - `cache_pokemon_images.py` (fetcher) and `pdf_generator.py` (PDF) use identical logic
  - Both extract URL identifiers the same way (PokeAPI IDs, TCGdex card IDs)
  - Ensures fetcher-cached images are properly found by PDF generator

### Technical Details

#### Image Cache Redesign
**Old Format:**
```
data/pokemon_images_cache/pokemon_6/default_thumb.jpg  # Collision!
```

**New Format:**
```
data/pokemon_images_cache/
  pokemon_6/
    6_thumb.jpg         # Normal Charizard
    10034_thumb.jpg     # Mega Charizard X
    10035_thumb.jpg     # Mega Charizard Y
```

**URL Identifier Extraction:**
- PokeAPI: `.../10034.png` → `"10034"` (Mega form ID)
- TCGdex: `.../sv1/013/high.webp` → `"sv1-013"` (card ID)

#### Name Enrichment Enhancement
```python
# Extract suffix from English name
english_name = "Charizard X"
base_name = "Charizard"
suffix = " X"  # Extracted

# Apply to all languages
german_translation = "Glurak"
final_german = german_translation + suffix  # "Glurak X"
```

**Affected Languages:** All 9 (de, en, fr, es, it, ja, ko, zh_hans, zh_hant)

### Documentation
- Added `docs/IMAGE_CACHE.md` - Complete cache architecture specification
- Updated `docs/ARCHITECTURE.md` - Added image cache section
- Updated `docs/DATA_FETCHER.md` - Removed obsolete artwork options
- Updated `docs/VARIANTS_ARCHITECTURE.md` - Updated variant counts and features
- Updated `README.md` and `README.de.md` - Added v4.3 release notes

### Migration from 4.2
1. Delete old cache: `rm -rf data/pokemon_images_cache/`
2. Re-fetch all data: 
   ```bash
   python scripts/fetcher/fetch.py --scope Pokedex
   python scripts/fetcher/fetch.py --scope ExGen1
   python scripts/fetcher/fetch.py --scope ExGen2
   python scripts/fetcher/fetch.py --scope ExGen3
   ```
3. Regenerate PDFs as needed

**Data Size:** ~45 MB for 1,439 Pokémon entries (2,878 cache files)

---

## [4.2.0] - 2026-01-15

### Added
- **Comprehensive CJK Font Support** - WenQuanYi font integration
- **Enhanced Font Detection** - Fallback mechanisms for Noto and system fonts
- **Korean Rendering Improvements** - Using SongtiBold for better coverage

### Fixed
- Font path resolution for Ubuntu/Linux systems (OpenType fonts)
- ReportLab font warnings suppressed (expected behavior)
- PDF generation across all 9 languages in CI/CD environments

### Changed
- Consolidated font configuration with single source of truth
- Verified Japanese, Chinese, Korean PDF generation

**Result:** All 1,025+ Pokémon render correctly in all 9 languages

---

## [4.1.1] - 2026-01-10

### Added
- Fine dashed gray cutting guides for all PDFs
- Improved preview screenshot

### Fixed
- Minor rendering issues

---

## [4.1.0] - 2026-01-05

### Added
- Unified logging system with clean output
- Verbose mode for debugging
- Section-based featured Pokémon support

### Changed
- Improved typography and rendering quality
- Better error messages and progress indicators

---

## [4.0.0] - 2025-12-20

### Added
- **Variant Collections System** - Support for EX generations and Mega Evolution
- **Pipeline Architecture** - Modular fetch/transform/enrich/save system
- **Multi-Section Support** - Variants with different sections (normal/mega/primal)
- **Featured Pokémon** - Configurable featured Pokémon per section

### Changed
- Complete rewrite of data fetching system
- Unified data structure for Pokédex and variants
- New JSON schema for flexibility

### Documentation
- Added comprehensive architecture documentation
- Added variant system specification
- Added pipeline step documentation

---

## [3.x] - Legacy Versions

Earlier versions focused on basic Pokédex generation without variant support.
See git history for details.

---

## Version Numbering

**Format:** MAJOR.MINOR.PATCH

- **MAJOR:** Breaking changes, incompatible data formats
- **MINOR:** New features, backwards compatible
- **PATCH:** Bug fixes, documentation updates

**Current:** 4.3.0
- Major version 4: Current architecture with pipeline system
- Minor version 3: Image cache and name enrichment fixes
- Patch version 0: Initial release of this version
