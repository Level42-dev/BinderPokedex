# 🎯 Usage Guide

Quick reference for generating BinderPokedex PDFs using the scope-based system.

## 📦 Available Scopes

**30 Total Scopes:**
- **Pokedex**: Complete National Pokédex (1025 Pokémon)
- **Base1-Base3**: Base Set, Jungle, and Fossil (3 sets)
- **ExGen1-3**: TCG EX variant collections generated from their current source snapshots
- **ME01-MEP**: Pokémon TCG Mega Evolution era (6 sets)
- **SV01-SVP**: Pokémon TCG Scarlet & Violet main series (17 sets)

List all available scopes:
```bash
ls config/scopes/*.yaml
```

## Basic Usage

### Single Scope, Single Language

```bash
# Generate German Pokedex
python scripts/pdf/generate_pdf.py --scope Pokedex --language de

# Generate English TCG set
python scripts/pdf/generate_pdf.py --scope ME01 --language en
```

### Single Scope, All Languages

Omit `--language` to generate all 9 supported languages:

```bash
# Generate Pokedex in all languages
python scripts/pdf/generate_pdf.py --scope Pokedex

# Generate TCG set in all languages
python scripts/pdf/generate_pdf.py --scope SV01
```

### All Scopes, All Languages

Use `--scope all` to generate everything:

```bash
# Generate all 30 scopes in every available language
python scripts/pdf/generate_pdf.py --scope all
```

The current release inventory produces 167 PDFs across nine language archives;
the exact count, duration, and size depend on each scope's available languages
and the fetched source data. `release-manifest.json` is authoritative for a
completed release-candidate build.

### Optional poster pages

The normal PDF command automatically includes accepted local poster artwork.
Individual scopes opt in with `pdf.enabled: true` in
`config/posters/<scope>/poster.yaml`. Aggregate scopes use
`config/posters/<scope>/posters.yaml` to bind isolated leaf manifests to
section IDs; each enabled page replaces its matching section cover. Scopes and
bindings without that opt-in continue through the ordinary cover path. Poster
generation itself is a separate reviewed workflow; the PDF command only
consumes promoted local artwork and does not start ComfyUI.
Downloadable set logos are not checked in. After fetching scope data, populate
the ignored PDF-overlay cache for TCG posters; Pokédex-only PDFs do not need
this step:

```bash
python scripts/poster_assets/fetch_poster_sources.py \
  --scope SV01 \
  --kind logos
```

The default poster presentation uses cuttable physical cards. A 3×3 poster
occupies one A4 page. A local 2×2 poster uses the upper-left four slots of that
same page, leaving the right column and bottom row empty. A local 4×3 poster is
not scaled down and instead uses two A4 pages with nine cards followed by three
cards vertically in the next page's first column.
To keep the same localized 3×3 poster as one continuous 200.5 × 276.7 mm image
centered on A4, without cutting guides:

```bash
python scripts/pdf/generate_pdf.py \
  --scope Base1 \
  --language de \
  --poster-page-mode full-page
```

This writes a separate file such as
`output/de/Base1_DE_POSTER_FULL_PAGE.pdf`. Scopes without an enabled promoted
poster continue through the existing cover and card-page path.

The normal page order is poster, then card pages. The poster carries the
section's semantic title/subtitle, count, description or release date, and
project identity. If no enabled promoted poster exists, the page order remains
cover, then card pages.

Use `scripts/poster_assets/create_custom_poster_layout.py` to prepare an
ignored local poster-assets root for `standard_2x2`, `wide_4x3`, or another
registered layout. `standard_2x2` places the title at upper left, the
information panel at upper right, and two Pokémon below them.
The complete isolated-workspace example is in
[Poster Artwork Workflow](POSTER_WORKFLOW.md).

Skip the poster for one build without changing the scope manifest:

```bash
python scripts/pdf/generate_pdf.py \
  --scope Base1 \
  --language de \
  --skip-poster
```

The skipped build uses a separate filename such as
`output/de/Base1_DE_NO_POSTER.pdf`, so it cannot overwrite
`output/de/Base1_DE.pdf`. `--skip-poster` bypasses all poster-index, manifest,
and artwork loading—including every section poster of an aggregate scope—and
can be combined with `--test` and `--skip-images`.
It is not combined with `--poster-page-mode full-page`, because no poster is
loaded in a skipped build.

Poster artwork is an explicit optional post-fetch workflow. See
[Poster Artwork Workflow](POSTER_WORKFLOW.md) for initialization, the
set-specific scene catalog, local ComfyUI generation, review, promotion, and
PDF activation.

## Standalone artwork PDFs

From the repository root, run the export in your BinderPokedex Python
environment. Both commands use checked-in artwork.

```sh
python -m scripts.pdf.generate_artwork_pdf --scope glurak-sammlung --language de --poster-page-mode cards
python -m scripts.poster_assets.extended_artwork --recipe config/extended-artwork/bisasam-scr-143.yaml export
```

- **Collection poster.** The Glurak (Charizard) command writes
  `output/artwork/glurak-sammlung-de-a4-cards.pdf`. The poster fills all nine
  slots. For other subjects, see the
  [available collection scopes](POSTER_WORKFLOW.md#standalone-collection-artwork).
- **Extended Artwork Page.** The Bisasam (Bulbasaur) command writes
  `output/extended-artwork/bisasam-scr-143-de-a4-cards.pdf`. The eight
  illustrated inserts surround the original Stellarkrone (Stellar Crown)
  143/142 card. See the [printing guide](PRINTING_GUIDE.md#extended-artwork-pages).

## Supported Languages

```bash
de      # Deutsch
en      # English
fr      # Français
es      # Español
it      # Italiano
ja      # 日本語
ko      # 한국어
zh-hans # 简体中文
zh-hant # 繁體中文
```

**Note:** Not all TCG sets are available in all languages. The generator will skip unavailable languages automatically.

## 🔄 Data Fetching

Before generating PDFs, you need to fetch the data:

```bash
# Fetch single scope
python scripts/fetcher/fetch.py --scope Pokedex
python scripts/fetcher/fetch.py --scope ME01

# Fetch all scopes (takes ~5 minutes)
for scope in Pokedex ExGen1 ExGen2 ExGen3 ME01 ME02 ME02.5 MEP SV01 SV02 SV03 SV03.5 SV04 SV04.5 SV05 SV06 SV06.5 SV07 SV08 SV08.5 SV09 SV10 SV10.5B SV10.5W SVP; do
    python scripts/fetcher/fetch.py --scope $scope
done
```

## 💾 Output Files

PDFs are organized by language in subdirectories:
```
output/
  de/
    Pokedex_DE.pdf
    ME01_DE.pdf
    ...
  en/
    Pokedex_EN.pdf
    ME01_EN.pdf
    ...
  fr/
  ...
```

### File Sizes (Approximate)

| Scope | Type | Cards/Pokémon | Size per Language |
|-------|------|----------------|-------------------|
| Pokedex | Pokédex | 1025 | ~60 MB |
| ExGen1 | TCG | 94 | ~2 MB |
| ExGen2 | TCG | 324 | ~5 MB |
| ExGen3 | TCG | Dynamic, exact forms | ~6 MB |
| ME01 | TCG | 165 | ~2 MB |
| SV01 | TCG | 198 | ~2.5 MB |

**Total for all scopes & languages:** ~377 MB

## 📝 Examples

### Example 1: Complete Pokédex in German

```bash
python scripts/fetcher/fetch.py --scope Pokedex
python scripts/pdf/generate_pdf.py --scope Pokedex --language de
# Output: output/de/Pokedex_DE.pdf (~60 MB)
```

### Example 2: All TCG Mew Sets in English

```bash
# Fetch all Mew sets
for scope in ME01 ME02 ME02.5 MEP; do
    python scripts/fetcher/fetch.py --scope $scope
done

# Generate English PDFs
for scope in ME01 ME02 ME02.5 MEP; do
    python scripts/pdf/generate_pdf.py --scope $scope --language en
done

# Check results
ls output/en/ME*.pdf
```

### Example 3: Complete Collection (All Scopes, All Languages)

```bash
# This generates all 225 PDFs (~377 MB total)
python scripts/pdf/generate_pdf.py --scope all

# Check results
for lang in de en fr es it ja ko zh-hans zh-hant; do
    echo "$lang: $(ls output/$lang/*.pdf 2>/dev/null | wc -l) PDFs"
done
```

```bash
# Start all languages
python scripts/generate_pdf.py --language all

# Monitor completion
watch 'ls -1 output/*.pdf | wc -l'
```

### Scenario 4: Rerun failed language

If a language fails during `--language all`:

```bash
# Rerun just that language
python scripts/generate_pdf.py --language ja
```

## Performance Tips

1. **Close other apps** - Frees up memory for parallel processing
2. **Stable internet** - Faster image downloads
3. **SSD storage** - Faster PDF writing (output/ directory)
4. **Morning run** - Schedule for off-peak hours if generating all languages
5. **Monitor space** - Ensure 2 GB free disk space

## Troubleshooting

### "Only X out of Y images processed"
- Usually temporary network issue
- Rerun the command (images are cached after first download)
- Check internet connection

### "Font not found" error
- Missing CJK fonts for Asian languages
- **macOS:** Install STHeiti font
- **Linux:** `sudo apt install fonts-noto-cjk`
- **Windows:** Download and install from Google Fonts

### Slow generation
- Check internet speed
- Close other applications
- Check CPU/memory usage
- Try running single language first

### Disk space error
- Delete old PDFs: `rm output/*.pdf`
- Free up disk space
- Reduce generations at once

## Advanced Options

### View help text
```bash
python scripts/generate_pdf.py --help
```

### Monitor all languages
```bash
# Watch PDF count grow
watch 'ls output/*.pdf | wc -l'

# Watch file sizes
watch 'du -sh output/'

# Count by language
for lang in DE EN FR ES IT JA KO PT RU; do
  count=$(ls output/*_$lang.pdf 2>/dev/null | wc -l)
  echo "  $lang: $count"
done
```

## Environment Variables

No special environment variables needed.

Python virtual environment should be activated:
```bash
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate      # Windows
```

## Supported Python Versions

- Python 3.8+
- Python 3.9+
- Python 3.10+
- Python 3.11+ (recommended)
- Python 3.12+

Check version:
```bash
python --version
```

---

**[← Back to README](../README.md)** | **[Scripts Documentation](../scripts/README.md)**
