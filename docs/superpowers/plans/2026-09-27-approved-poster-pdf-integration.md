# Approved Poster PDF Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Die exakt akzeptierten Base1-B- und ExGen3-Mega-C-Master mit wahrheitsgetreuem historischem Vertrag übernehmen und zwei geprüfte deutsche PDF-Ausgaben erzeugen.

**Architecture:** Ein auf zwei Kandidaten begrenzter Import prüft Originaljob, Prompt, Quellen und Master, bevor er normale Run-Metadaten mit einem zusätzlichen historischen Vertragsfeld erzeugt. Die bestehende Promotion, Overlay-Erstellung und PDF-Route bleiben die einzigen produktiven Verbraucher; sie erhalten gezielte Vertragsvalidierung und eine getrennte PDF-Prüfausgabe.

**Tech Stack:** Python 3, Pytest, Pillow, YAML/JSON, bestehender Poster-Renderer und ReportLab/Poppler-PDF-Prüfung.

**Spec:** `docs/superpowers/specs/2026-09-27-approved-poster-pdf-integration-design.md`

## Global Constraints

- Nur `Base1` Kandidat B (`d06f69eb6e010b2670987a2209d3aec50848ac694aaefec64dc70d342ce0d9b4`) und `ExGen3/sections/mega` Kandidat C (`eb61f272fd22bd400b2c2555cb2a490fad47c85b3947087a88b96b2e9dce3ebd`) importieren; keine Neugenerierung und keine veränderten Masterpixel.
- Ursprüngliche `experimental_prompt_override: true` und `canonical_promotion_eligible: false` als historische Fakten erhalten; keinen aktuellen v11-Render behaupten.
- Vor Produktivrouting je genau einen aktiven Manifestvertrag; alle anderen Master und der ExGen3-Normalabschnitt bleiben unverändert.
- `Base1`-DE braucht ein belegtes deutsches Logo; ohne dieses keine Base1-PDF-Aktivierung. Original-/Release-PDFs erst nach Prüfung einer separat erzeugten neuen Ausgabe ablösen.
- Keine privaten Worker-Werte oder ignorierten Quell-/Jobdateien committen; nur allowlist-staged Projektdateien. Im bestehenden Checkout arbeiten.

## Review Focus

1. Fehlender oder manipulierter ignorierter Originaljob muss den Import vor jeder Dateiänderung stoppen (`test_missing_original_job_is_read_only`, Task 1).
2. Richtiger PNG-Dateiname mit anderen Pixeln muss trotz sonst passender Daten abgelehnt werden (`test_changed_master_pixels_are_rejected`, Task 1).
3. Ein beliebiger neuer Kandidat darf den historischen Vertragsmodus nicht als Promotion-Abkürzung verwenden (`test_historical_contract_is_allowlisted`, Task 2).
4. Fehlende oder englisch beschriftete DE-Logodatei darf kein deutsches Base1-Poster aktivieren (`test_base1_de_logo_is_language_bound`, Task 3).
5. Ein fehlgeschlagener Prüfbau darf die bestehende Standard-PDF nicht überschreiben und keine ExGen3-Sektion auslassen (`test_output_dir_is_isolated_on_failure`, Task 4; `test_exgen3_keeps_both_sections`, Task 5).

---

### Task 1: Belegprüfung und unveränderliche Importdaten

**Files:**
- Create: `scripts/poster_assets/historical_review_import.py` — allowlist-gebundene Belegprüfung und normalisierte, private Angaben bereinigte Metadaten.
- Create: `scripts/tests/test_historical_review_import.py` — kleine temporäre Originaljob-/Archiv-Fixtures und negative Fälle.
- Create: `config/posters/historical_review_candidates.json` — genau zwei IDs, Scopes, akzeptierte Master- und Review-Hashes; keine Rechnerpfade.

**Interfaces:**
- Produces: `verify_historical_trial(scope: str, archive_dir: Path, trial_dir: Path) -> dict[str, Any]`. Ergebnis enthält `candidate_id`, tatsächliches `generation`, Datei-/Pixelhashes für Master, Rohbild und drei Quellen sowie Job-/Workflow-/Prompt-Hashes; es enthält keine Host-/Benutzerdaten.
- Consumes: vorhandene `poster_bundle`, `file_record`, `image_pixel_record`; keine Netzwerk- oder GPU-Arbeit.

- [ ] **Step 1: Write the failing tests** `test_missing_original_job_is_read_only`, `test_changed_master_pixels_are_rejected`, `test_scope_seed_and_model_mismatch_rejected`, `test_verified_evidence_omits_private_run_fields`; jeweils Originalzustand und unveränderte Ausgabeverzeichnisse prüfen.
- [ ] **Step 2: Run the red tests** `python -m pytest scripts/tests/test_historical_review_import.py -q`; erwarteter Befund: fehlende Importfunktion, keine unbeabsichtigten Schreibeffekte.
- [ ] **Step 3: Implement** `verify_historical_trial(...)` mit sicherer Pfadauflösung, `experiment.json`/Review-Archiv-Abgleich und direkten Hashprüfungen von Original-`job.json`, Workflow, Prompt, `run.json`, Rohbild, Quellen und akzeptiertem Master. Private Felder aus dem Remote-`run.json` niemals in das Ergebnis übernehmen.
- [ ] **Step 4: Run the green tests** derselbe Pytest-Aufruf; erwarteter Befund: alle Tests dieser Datei bestehen.
- [ ] **Step 5: Commit** nur die drei genannten Dateien als eigenen Belegprüfungs-Commit.

### Task 2: Versionierter historischer Vertrag durch die normale Promotion

**Files:**
- Modify: `scripts/poster_assets/provenance.py` — historische Fingerprint-Variante und dauerhafte Revalidierung.
- Modify: `scripts/poster_assets/promote_comfyui_poster.py` — nur bei verifizierter historischer Run-Metadatei den aufgezeichneten Vertrag verwenden.
- Modify: `scripts/poster_assets/generation_contract.py` — ausschließlich benötigte historische Vertragskennung zulassen, ohne den One-shot-Default zu ändern.
- Modify: `scripts/poster_assets/historical_review_import.py` — aus Task 1 geprüfte Daten als standardkompatible `.run.json` schreiben.
- Test: `scripts/tests/test_historical_review_import.py`, `scripts/tests/test_poster_fingerprints.py`, `scripts/tests/test_poster_assets.py`, `scripts/tests/test_poster_work_plan.py`.

**Interfaces:**
- Consumes: `verify_historical_trial(...)` aus Task 1.
- Produces: `write_historical_run_metadata(scope: str, archive_dir: Path, trial_dir: Path, output_path: Path) -> Path` mit `historical_import.schema_version == 1`, exakten Originalhashes und einem eigenen, nur lesbaren `spatial_identity_joint`-Vertragsstand. `require_historical_import(bundle: PosterBundle, run: dict[str, Any]) -> None` muss bei Promotion und Produktionsvalidierung greifen.

- [ ] **Step 1: Write the failing tests** `test_historical_contract_is_allowlisted`, `test_original_prompt_hash_is_revalidated`, `test_historical_run_promotes_without_claiming_current_graph`, `test_modern_promotion_remains_unchanged`, `test_planner_reports_reviewed_historical_scope_current`.
- [ ] **Step 2: Run the red tests** `python -m pytest scripts/tests/test_historical_review_import.py scripts/tests/test_poster_fingerprints.py scripts/tests/test_poster_work_plan.py -q`; erwarteter Befund: neue historische Fälle scheitern, bisherige moderne Fälle bleiben grün.
- [ ] **Step 3: Implement** ein separates historisches `spatial_identity_joint`-Vertragskennzeichen (nicht v11), das die originale 2,0-MP-Workflow-Topologie und den exakten archivierten Prompt bindet. Der Import baut normale `inputs.generation_fingerprint`-/Rohbild-/Quellrecords plus `historical_import`; generische neue Runs bleiben an die bisherigen Fingerprint-Gatter gebunden. Promotion und Revalidierung prüfen die Archivkennung und jede Abweichung fail-closed.
- [ ] **Step 4: Run the green/regression tests** `python -m pytest scripts/tests/test_historical_review_import.py scripts/tests/test_poster_fingerprints.py scripts/tests/test_poster_assets.py scripts/tests/test_poster_work_plan.py scripts/tests/test_poster_provenance_migration.py -q`; erwarteter Befund: alle bestehen.
- [ ] **Step 5: Commit** nur Vertrags-/Promotionscode und die genannten Tests.

### Task 3: Deutsches Base1-Logo mit belegbarer Quelle

**Files:**
- Modify: `config/posters/Base1/poster.yaml` — sprachgebundene `title_logo.files`/`sources`; andere bisherige Sprachen unverändert zuordnen.
- Test: `scripts/tests/test_poster_assets.py` — Logo-Sprachwahl und Quellauflösung.
- Create: `docs/reviews/2026-09-27-base1-de-logo-source.md` — URL, Herkunft, Cache-Hash, Bildbefund und Rechtehinweis.

**Interfaces:**
- Consumes: `fetch_title_logos.resolve_logo_downloads(...)` und `finalize_comfyui_poster.title_logo_file(...)`; erzeugt nur ignorierte `tmp/poster-workspaces/Base1/sources/`-Dateien.

- [ ] **Step 1: Write the failing test** `test_base1_de_logo_is_language_bound`: `de` verweist auf deutsches Logo, `en` und die bisher konfigurierten weiteren Sprachen verändern ihre bisherige Zuordnung nicht; fehlende DE-Quelle schlägt fehl.
- [ ] **Step 2: Run the red test** `python -m pytest scripts/tests/test_poster_assets.py -k base1_de_logo -q`; erwarteter Befund: falsche/fehlende DE-Zuordnung.
- [ ] **Step 3: Verify an authentic German asset** zuerst an der Pokémon-Originalquelle der deutschen Sammelkartenspiel-Marke, ersatzweise anhand einer belegten offiziellen deutschen PDF. Nur eine visuell echte, ausreichend große Datei mit dokumentierter Herkunft in `title_logo.sources.de` eintragen. Ist sie nicht belegbar oder technisch nicht abrufbar, Base1 deaktiviert lassen und diese Task als konkreten Scope-Blocker melden; keine improvisierte Grafik.
- [ ] **Step 4: Run** `python scripts/poster_assets/fetch_poster_sources.py --scope Base1 --kind logos` sowie den gezielten Pytest-Aufruf; erwarteter Befund: DE-Cache zeigt „SAMMELKARTENSPIEL“, alle Sprachen werden eindeutig aufgelöst.
- [ ] **Step 5: Commit** nur Manifest, Test und Quellenbericht; niemals gecachte Logos.

### Task 4: Getrenntes PDF-Prüfausgabeverzeichnis

**Files:**
- Modify: `scripts/pdf/generate_pdf.py` — optionales `--output-dir` als Ziel für einen Scope-Lauf, Standard bleibt `output/`.
- Test: `scripts/tests/test_pdf_generation_options.py` — Kandidatenausgabe und Fehlererhalt.

**Interfaces:**
- Produces: CLI `--output-dir PATH`; ohne Option bleibt die bisherige Aufrufsignatur und Dateibenennung unverändert.

- [ ] **Step 1: Write the failing tests** `test_output_dir_is_isolated_on_failure` und `test_default_output_dir_is_unchanged`: temporärer Zielordner, erzwungener PDF-Fehler, Hash des vorhandenen Standard-PDF unverändert.
- [ ] **Step 2: Run the red tests** `python -m pytest scripts/tests/test_pdf_generation_options.py -q`; erwarteter Befund: nur die neuen Optionsfälle scheitern.
- [ ] **Step 3: Implement** `--output-dir` in `main()` und Übergabe des aufgelösten sicheren Zielordners an `generate_scope_pdf(...)`; bestehende atomare Ausgabe-/Fehlerlogik weiterverwenden.
- [ ] **Step 4: Run the green tests** `python -m pytest scripts/tests/test_pdf_generation_options.py scripts/tests/test_poster_pdf.py -q`; erwarteter Befund: alle bestehen.
- [ ] **Step 5: Commit** CLI und Tests getrennt vom Artwork-Import.

### Task 5: Exakte Übernahme, Routing und deutsche PDF-Prüfung

**Files:**
- Modify: `config/posters/Base1/poster.yaml`, `config/posters/ExGen3/sections/mega/poster.yaml`, `config/posters/ExGen3/posters.yaml` — tatsächliche Generierungsverträge und erst nach Validierung PDF-Routing.
- Create: `assets/posters/Base1/poster-flux2-artwork.png`, `assets/posters/Base1/poster-flux2-provenance.json`, `assets/posters/ExGen3/sections/mega/poster-flux2-artwork.png`, `assets/posters/ExGen3/sections/mega/poster-flux2-provenance.json` — normale Promotionsergebnisse.
- Test: `scripts/tests/test_poster_pdf.py`, `scripts/tests/test_poster_assets.py`.
- Create: `docs/reviews/2026-09-27-historical-poster-pdf-integration.md` — Hashes, Karten-/Quellvergleich, PDF-Seiten und offen gebliebene Scope-Blocker.

**Interfaces:**
- Consumes: Task-2-Runmetadaten, Task-3-Logo, Task-4-`--output-dir`.
- Produces: geprüfte DE-Kandidaten unter `tmp/` und erst danach die aktualisierten regulären PDFs für erfolgreich geprüfte Scopes.

- [ ] **Step 1: Write the failing routing test** `test_exgen3_keeps_both_sections`: normale und Mega-Sektion erscheinen in Quellreihenfolge mit ihren jeweiligen Poster-Slots; deaktivierter/ungültiger Mega-Scope bleibt abgelehnt.
- [ ] **Step 2: Run the red test** `python -m pytest scripts/tests/test_poster_pdf.py -k exgen3_keeps_both_sections -q`; erwarteter Befund: Mega noch deaktiviert.
- [ ] **Step 3: Import and promote each scope separately** mit `write_historical_run_metadata(...)`, Agentenreview aller neun Karten und drei Quellen, originaler menschlicher Gesamtbild-Freigabe als getrenntem Revieweintrag und normalem `promote_comfyui_poster.py`/`validate_promoted_poster.py`. Gesicherte Vorgänger und alle anderen Master-Hashes vergleichen; bei einem Fehler nur den betroffenen Scope stoppen.
- [ ] **Step 4: Enable routing only after scope validation**: `Base1` nur mit deutschem Logo, ExGen3-Mega im Aggregat neben unverändertem Normalposter. Test und `poster_work_plan.py --scope Base1` sowie `--scope ExGen3` müssen aktuelle, eindeutige Zustände melden.
- [ ] **Step 5: Build candidate PDFs** `python scripts/pdf/generate_pdf.py --scope Base1 --language de --output-dir tmp/pdf-review/base1` und entsprechend `ExGen3`; zusätzlich je `--poster-page-mode full-page`. Beide Zielvarianten seitenweise rastern, alle Karten, Logos, Schnittlinien, Seitenfolge und angrenzenden Abschnitte visuell prüfen; PDF-Hashes und Umfang dokumentieren.
- [ ] **Step 6: Run final verification** fokussierte Poster-/PDF-Tests und `python scripts/poster_assets/validate_promoted_poster.py --scope Base1`/`--scope ExGen3/sections/mega`; nach grüner Prüfung reguläre PDFs mit denselben Eingaben bauen und Seitenraster, eingebettete Posterpixel, Reihenfolge und Umfang gegen die Kandidaten prüfen. PDF-Bytehashes separat berichten, weil Metadaten oder Zeitstempel variieren können. Bei Blocker keine Standard-PDF überschreiben.
- [ ] **Step 7: Commit and push** nur geprüfte Manifest-, Master-, Provenienz-, Test- und Reviewdateien; generierte PDFs nach bestehender Release-Regel behandeln, keine privaten Caches/ZIPs. Remote-Branch-SHA gegen lokalen HEAD prüfen.
