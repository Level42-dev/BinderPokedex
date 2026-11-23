# 🎯 Bedienungsanleitung

Schnellreferenz für die Generierung von BinderPokedex-PDFs mit dem Scope-basierten System.

## 📦 Verfügbare Scopes

**30 Scopes insgesamt:**
- **Pokedex**: Kompletter National Pokédex (1025 Pokémon)
- **Base1-Base3**: Base Set, Dschungel und Fossil (3 Sets)
- **ExGen1-3**: TCG EX Varianten-Kollektionen aus den aktuellen Quelldaten
- **ME01-MEP**: Pokémon TCG Mega-Evolution-Ära (6 Sets)
- **SV01-SVP**: Pokémon TCG Karmesin & Purpur Hauptserie (17 Sets)

Alle verfügbaren Scopes auflisten:
```bash
ls config/scopes/*.yaml
```

## Grundlegende Verwendung

### Ein Scope, eine Sprache

```bash
# Deutschen Pokedex generieren
python scripts/pdf/generate_pdf.py --scope Pokedex --language de

# Englisches TCG-Set generieren
python scripts/pdf/generate_pdf.py --scope ME01 --language en
```

### Ein Scope, alle Sprachen

`--language` weglassen, um alle 9 unterstützten Sprachen zu generieren:

```bash
# Pokedex in allen Sprachen generieren
python scripts/pdf/generate_pdf.py --scope Pokedex

# TCG-Set in allen Sprachen generieren
python scripts/pdf/generate_pdf.py --scope SV01
```

### Alle Scopes, alle Sprachen

`--scope all` verwenden, um alles zu generieren:

```bash
# Alle 30 Scopes in jeder verfügbaren Sprache generieren
python scripts/pdf/generate_pdf.py --scope all
```

Der aktuelle Release-Bestand erzeugt 167 PDFs in neun Spracharchiven. Die
exakte Anzahl, Dauer und Größe hängen von den je Scope verfügbaren Sprachen und
den abgerufenen Quelldaten ab. Für einen abgeschlossenen Release-Kandidaten ist
`release-manifest.json` maßgeblich.

### Optionale Posterseiten

Der normale PDF-Befehl fügt freigegebene lokale Poster-Artworks automatisch ein.
Einzelne Scopes aktivieren sie mit `pdf.enabled: true` in
`config/posters/<scope>/poster.yaml`. Sammel-Scopes ordnen in
`config/posters/<scope>/posters.yaml` isolierte Leaf-Manifeste stabil ihren
Sections zu; jede aktivierte Seite folgt direkt auf das passende Section-Cover.
Scopes und Bindings ohne Freigabe werden unverändert erzeugt. Die
Artwork-Generierung bleibt ein separater Review-Workflow; der PDF-Befehl
verwendet nur das promotete lokale Artwork und startet ComfyUI nicht selbst.
Herunterladbare Set-Logos werden nicht eingecheckt. Nach dem Daten-Fetch lädt
der folgende Schritt die für TCG-Poster benötigten PDF-Overlays in den
ignorierten Workspace; für reine Pokédex-PDFs ist er nicht erforderlich:

```bash
python scripts/poster_assets/fetch_poster_sources.py \
  --scope SV01 \
  --kind logos
```

Standardmäßig wird das Poster als zuschneidbare Karten in physischer Größe
ausgegeben. Ein 3×3-Poster belegt eine A4-Seite. Ein lokales 2×2-Poster nutzt
die vier Felder links oben; die rechte Spalte und die untere Reihe bleiben leer.
Lokale 4×3-Poster werden ohne Verkleinerung auf zwei A4-Seiten verteilt: Die
linken drei Artwork-Spalten bilden Seite 1, die vierte Artwork-Spalte steht
senkrecht in der ersten Spalte von Seite 2. Dasselbe lokalisierte 3×3-Poster
kann alternativ als ein zusammenhängendes, 200,5 × 276,7 mm großes Bild mittig
auf A4 und ohne Schnittlinien ausgegeben werden:

```bash
python scripts/pdf/generate_pdf.py \
  --scope Base1 \
  --language de \
  --poster-page-mode full-page
```

Dabei entsteht eine separate Datei wie
`output/de/Base1_DE_POSTER_FULL_PAGE.pdf`. Scopes ohne aktiviertes promotetes
Poster verwenden weiterhin den bestehenden Cover- und Kartenseiten-Pfad.

Ein aktiviertes Poster ersetzt das passende Section-Cover und steht direkt vor
den Kartenseiten. Ohne aktiviertes Poster oder mit `--skip-poster` bleibt das
gewöhnliche Cover erhalten.

#### Lokaler 4×3-Pilot für den deutschen Pokédex

Der Custom-Layout-Befehl kopiert nur Konfiguration und deterministische
Quell-Cutouts nach `tmp/`. Eingecheckte 3×3-Artworks und Release-Manifeste werden
nicht verändert:

```bash
python scripts/poster_assets/create_custom_poster_layout.py \
  --scope Pokedex \
  --section gen1 \
  --layout wide_4x3 \
  --fallback-pokemon 25

export BINDER_POKEDEX_POSTER_ASSETS="$PWD/tmp/custom-poster-layouts/pokedex-gen1-wide_4x3"

python scripts/poster_assets/fetch_cutouts.py \
  --scope Pokedex/sections/gen1
```

Danach ComfyUI-Runner, Review/Promotion und PDF-Generator mit derselben gesetzten
Umgebungsvariable ausführen. Der vollständige Ablauf mit allen Befehlen steht im
[Poster Artwork Workflow](POSTER_WORKFLOW.md). Ohne `--section gen1` wird ein
lokaler Workspace für alle neun Generationen vorbereitet.

Für einen 2×2-Piloten stattdessen `--layout standard_2x2` verwenden. Das
Custom-Layout übernimmt deterministisch die ersten zwei kuratierten Pokémon und
ordnet Titel links oben, Infobox rechts oben und beide Pokémon darunter an. Ein
zusätzlicher `--fallback-pokemon` ist dafür nicht nötig.

Für einen einzelnen Build kann das Poster ohne Manifeständerung übersprungen
werden:

```bash
python scripts/pdf/generate_pdf.py \
  --scope Base1 \
  --language de \
  --skip-poster
```

Der Build erhält einen eigenen Dateinamen wie
`output/de/Base1_DE_NO_POSTER.pdf` und überschreibt daher nicht
`output/de/Base1_DE.pdf`. `--skip-poster` verhindert bereits das Laden aller
Poster-Indizes, Manifeste und Artworks – bei Sammel-Scopes also sämtlicher
Section-Poster – und lässt sich mit `--test` sowie `--skip-images` kombinieren.
Die Option wird nicht mit `--poster-page-mode full-page` kombiniert, weil in
einem übersprungenen Build kein Poster geladen wird.

Die Artwork-Erzeugung ist ein expliziter optionaler Schritt nach dem
Daten-Fetch. Die Anleitung
[Poster Artwork Workflow](POSTER_WORKFLOW.md) beschreibt Initialisierung,
set-spezifische Szenen, lokale ComfyUI-Erzeugung, Review, Promotion und
PDF-Aktivierung.

## Eigenständige Artwork-PDFs

Führe die Befehle im Projektordner mit der BinderPokedex-Python-Umgebung aus.
Beide Exporte verwenden Bilder aus dem Repository.

```sh
python -m scripts.pdf.generate_artwork_pdf --scope glurak-sammlung --language de --poster-page-mode cards
python -m scripts.poster_assets.extended_artwork --recipe config/extended-artwork/bisasam-scr-143.yaml export
```

- **Sammlungsposter.** Der Glurak-Export schreibt
  `output/artwork/glurak-sammlung-de-a4-cards.pdf`. Das Motiv füllt alle neun
  Fächer. Weitere Motive findest du in der
  [Liste der verfügbaren Sammlungen](POSTER_WORKFLOW.md#standalone-collection-artwork).
- **Extended Artwork Page.** Der Bisasam-Export schreibt
  `output/extended-artwork/bisasam-scr-143-de-a4-cards.pdf`. Die acht
  Einleger ergänzen die Originalkarte Stellarkrone 143/142. Die
  [Druckanleitung](PRINTING_GUIDE.de.md#extended-artwork-pages) zeigt, wie du
  sie ausschneidest und einsortierst.

## Unterstützte Sprachen

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

**Hinweis:** Nicht alle TCG-Sets sind in allen Sprachen verfügbar. Der Generator überspringt nicht verfügbare Sprachen automatisch.

### Im Hintergrund ausführen und überwachen

```bash
# Generierung starten
nohup python scripts/generate_pdf.py --language all > pdf_all.log 2>&1 &

# Fortschritt verfolgen
tail -f pdf_all.log

# Status überprüfen
ls -lh output/*.pdf | wc -l    # Anzahl generierter PDFs
du -sh output/                  # Gesamtgröße
```

### Parallele Ausführung (Manuell)

Mehrere Sprachen gleichzeitig generieren:

```bash
# Terminal 1: Deutsch
python scripts/generate_pdf.py --language de &

# Terminal 2: Französisch
python scripts/generate_pdf.py --language fr &

# Terminal 3: Japanisch
python scripts/generate_pdf.py --language ja &

# Auf Abschluss aller warten
wait
```

## Ausgabedateien

PDFs werden in `output/` mit folgendem Muster gespeichert:
```
BinderPokedex_Gen{1-9}_{SPRACHE}.pdf
```

### Dateigröße (Ungefähre Werte)

| Generation | Pokémon | Gen 1 Größe | Dateigröße-Muster |
|------------|---------|-----------|-------------------|
| 1 | 151 | 25 MB | Größte |
| 2 | 100 | 15 MB | Klein |
| 3 | 135 | 21 MB | Groß |
| 4 | 107 | 16 MB | Klein-Mittel |
| 5 | 156 | 23 MB | Groß |
| 6 | 72 | 10 MB | Klein |
| 7 | 88 | 11 MB | Klein |
| 8 | 96 | 10 MB | Klein |
| 9 | 120 | 15 MB | Klein-Mittel |

**Gesamtgröße für alle Sprachen:** ~1,1 TB (wenn alle 81 Dateien generiert werden)

## 📝 Beispiele

### Beispiel 1: Kompletter Pokédex auf Deutsch

```bash
python scripts/fetcher/fetch.py --scope Pokedex
python scripts/pdf/generate_pdf.py --scope Pokedex --language de
# Ausgabe: output/de/Pokedex_DE.pdf (~60 MB)
```

### Beispiel 2: Alle TCG Mew-Sets auf Englisch

```bash
# Alle Mew-Sets fetchen
for scope in ME01 ME02 ME02.5 MEP; do
    python scripts/fetcher/fetch.py --scope $scope
done

# Englische PDFs generieren
for scope in ME01 ME02 ME02.5 MEP; do
    python scripts/pdf/generate_pdf.py --scope $scope --language en
done

# Ergebnisse prüfen
ls output/en/ME*.pdf
```

### Beispiel 3: Komplette Sammlung (Alle Scopes, alle Sprachen)

```bash
# Dies generiert alle 225 PDFs (~377 MB gesamt)
python scripts/pdf/generate_pdf.py --scope all

# Ergebnisse prüfen
for lang in de en fr es it ja ko zh-hans zh-hant; do
    echo "$lang: $(ls output/$lang/*.pdf 2>/dev/null | wc -l) PDFs"
done
```
# Alle Sprachen starten
python scripts/generate_pdf.py --language all

# Fertigstellung überwachen
watch 'ls -1 output/*.pdf | wc -l'
```

### Szenario 4: Fehlerhafte Sprache erneut generieren

Wenn eine Sprache während `--language all` fehlschlägt:

```bash
# Nur diese Sprache erneut generieren
python scripts/generate_pdf.py --language ja
```

## Performance-Tipps

1. **Andere Apps schließen** - Spart Speicher für parallele Verarbeitung
2. **Stabile Internetverbindung** - Schnellere Bilddownloads
3. **SSD-Speicher** - Schnelleres PDF-Schreiben (output/ Verzeichnis)
4. **Morgens generieren** - Zeitplan für Off-Peak-Zeiten bei Generierung aller Sprachen
5. **Speicherplatz überprüfen** - Mindestens 2 GB freier Speicher erforderlich

## Fehlerbehebung

### "Only X out of Y images processed"
- Normalerweise ein vorübergehendes Netzwerkproblem
- Befehl erneut ausführen (Bilder werden nach dem ersten Download zwischengespeichert)
- Internetverbindung überprüfen

### "Font not found" Fehler
- CJK-Fonts für asiatische Sprachen fehlen
- **macOS:** STHeiti-Schrift installieren
- **Linux:** `sudo apt install fonts-noto-cjk`
- **Windows:** Von Google Fonts herunterladen und installieren

### Langsame Generierung
- Internetgeschwindigkeit überprüfen
- Andere Anwendungen schließen
- CPU-/Speicherauslastung überprüfen
- Zuerst eine einzelne Sprache versuchen

### Fehler bei Speicherplatz
- Alte PDFs löschen: `rm output/*.pdf`
- Speicherplatz freigeben
- Weniger Generationen auf einmal

## Fortgeschrittene Optionen

### Hilfetext anzeigen
```bash
python scripts/generate_pdf.py --help
```

### Alle Sprachen überwachen
```bash
# PDF-Anzahl wachsen sehen
watch 'ls output/*.pdf | wc -l'

# Dateigrößen überwachen
watch 'du -sh output/'

# Anzahl nach Sprache zählen
for lang in DE EN FR ES IT JA KO PT RU; do
  count=$(ls output/*_$lang.pdf 2>/dev/null | wc -l)
  echo "  $lang: $count"
done
```

## Umgebungsvariablen

Keine speziellen Umgebungsvariablen erforderlich.

Python Virtual Environment sollte aktiviert sein:
```bash
source .venv/bin/activate  # macOS/Linux
# oder
.venv\Scripts\activate      # Windows
```

## Unterstützte Python-Versionen

- Python 3.8+
- Python 3.9+
- Python 3.10+
- Python 3.11+ (empfohlen)
- Python 3.12+

Version überprüfen:
```bash
python --version
```

---

**[← Zurück zu README](../README.md)** | **[Script-Dokumentation](../scripts/README.md)**
