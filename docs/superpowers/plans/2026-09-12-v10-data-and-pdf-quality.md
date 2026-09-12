# Binder Pokédex v10.0 Data and PDF Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible Binder Pokédex v10.0 release candidate with a fully reviewed data refresh, correct localized TCG identity and numbering, safe card-label layout, German poster logos, corrected Stellarkrone artwork, and the new ME05 set.

**Architecture:** API access happens only in an explicit refresh workflow. The refresh records per-card language and printed-number semantics, applies versioned curated corrections, emits a reviewable diff and snapshot manifest, and commits the resulting data. Release builds validate and consume that snapshot without contacting data APIs; poster source downloads remain a separate reproducible asset phase.

**Tech Stack:** Python 3.12, pytest, requests, PyYAML, ReportLab, Pillow, Poppler, GitHub Actions, repository ComfyUI poster tooling.

**Spec:** `docs/superpowers/specs/2026-09-12-v10-data-and-pdf-quality-design.md`

## Global Constraints

- Snapshot boundary: 2026-09-12.
- Preserve exact localized TCG card names; Pokédex names remain canonical and owner-free.
- Never label an English fallback as a German card name or German set logo.
- `Terapagos & Freunde` keeps stable source identity `svp-500` but has `printed_number: null`.
- German SVP contains 216 current TCGdex records plus the curated unnumbered card.
- German MEP preserves the 88 current TCGdex records and their original local IDs.
- Add released main set ME05; do not add MEE, SVE, or the post-boundary anniversary expansion.
- Release builds must not fetch mutable card data.
- Poster masters stay text-free; source logos and cutouts remain ignored reproducible cache files.
- Do not promote an AI poster until the full image and all nine physical crops pass visual review.
- Do not publish or tag v10.0 as part of this plan.

---

### Task 1: Versioned TCG overrides and card provenance

**Files:**
- Create: `enrichments/tcg_card_overrides.json`
- Create: `scripts/fetcher/lib/tcg_card_overrides.py`
- Modify: `scripts/fetcher/steps/enrich_tcg_names_multilingual.py`
- Modify: `scripts/fetcher/steps/transform_tcg_set.py`
- Test: `scripts/tests/test_tcg_card_overrides.py`
- Test: `scripts/tests/test_tcg_enrichment.py`

**Interfaces:**
- Produces: `load_tcg_card_overrides(path: Path) -> dict`
- Produces: `apply_tcg_card_overrides(data: dict, overrides: dict) -> dict`
- Produces on every transformed card: `available_languages: list[str]` and `printed_number: str | None`
- Consumes: multilingual names indexed by upstream `localId`

- [ ] **Step 1: Write failing override and provenance tests**

```python
def test_terapagos_override_keeps_identity_but_removes_printed_number():
    data = {"id": "svp", "cards": [{"id": "svp-500", "localId": "500", "name_en": "Terapagos & Friends", "available_languages": ["en"]}]}
    result = apply_tcg_card_overrides(data, OVERRIDES)
    card = result["cards"][0]
    assert card["id"] == "svp-500"
    assert card["localId"] == "500"
    assert card["printed_number"] is None
    assert card["name_de"] == "Terapagos & Freunde"
    assert card["available_languages"] == ["de", "en"]

def test_multilingual_enrichment_records_only_observed_languages():
    card = {"id": "svp-190", "localId": "190", "name": "Pikachu"}
    result = step._enrich_cards([card], {"190": {"en": "Pikachu"}})[0]
    assert result["available_languages"] == ["en"]
    assert "name_de" not in result
```

- [ ] **Step 2: Run the new tests and verify RED**

Run: `pytest -q scripts/tests/test_tcg_card_overrides.py scripts/tests/test_tcg_enrichment.py`

Expected: failures because the override module, per-card language list, and nullable printed number do not exist.

- [ ] **Step 3: Add the reviewed correction data**

Use this top-level shape and include every correction from the spec:

```json
{
  "version": 1,
  "sets": {
    "sv01": {"cards": {"257": {"names": {"de": "Basis-Elektro-Energie"}}}},
    "svp": {
      "cards": {
        "500": {
          "names": {"de": "Terapagos & Freunde", "en": "Terapagos & Friends"},
          "available_languages": ["de", "en"],
          "printed_number": null
        }
      }
    }
  }
}
```

Also include SV01 258, SV02 278/279, SV03 230, and SV06.5 098/099 exactly as specified.

- [ ] **Step 4: Implement strict loading and application**

`apply_tcg_card_overrides` must copy its input, reject an unknown set/card, merge only declared localized names and language membership, set `printed_number`, and record `tcg_card_overrides_version` in the set metadata. The multilingual step sets each card's languages from the actual API name map and defaults `printed_number` to its `localId` before applying overrides.

- [ ] **Step 5: Preserve the new fields through transformation**

Ensure `TransformTCGSetStep` copies `id`, `localId`, `printed_number`, and `available_languages` into the section card without coercing null to a sequence number.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `pytest -q scripts/tests/test_tcg_card_overrides.py scripts/tests/test_tcg_enrichment.py scripts/tests/test_tcg_transform.py`

- [ ] **Step 7: Commit**

```bash
git add enrichments/tcg_card_overrides.json scripts/fetcher/lib/tcg_card_overrides.py scripts/fetcher/steps/enrich_tcg_names_multilingual.py scripts/fetcher/steps/transform_tcg_set.py scripts/tests/test_tcg_card_overrides.py scripts/tests/test_tcg_enrichment.py scripts/tests/test_tcg_transform.py
git commit -m "fix(data): preserve TCG language and printed identity"
```

### Task 2: Keep official TCG names without polluting the Pokédex

**Files:**
- Modify: `scripts/fetcher/steps/enrich_tcg_cards_from_pokedex.py`
- Modify: `scripts/pdf/generate_pdf.py`
- Test: `scripts/tests/test_tcg_enrichment.py`
- Test: `scripts/tests/test_pdf_generation_options.py`

**Interfaces:**
- Consumes: `available_languages` and existing localized fields such as `name_de` and `name_en` from Task 1
- Produces: TCG section cards whose observed localized names survive Pokédex identity enrichment
- Produces: `filter_cards_for_language(cards: list[dict], language: str) -> list[dict]`

- [ ] **Step 1: Add failing name-authority tests**

```python
def test_pokedex_enrichment_preserves_observed_trainer_owned_name():
    card = {"name": "N's Zoroark ex", "name_de": "Ns Zoroark-ex", "available_languages": ["de", "en"], "category": "Pokemon", "dexId": [571]}
    result = step._enrich_card(card, pokemon_by_id, pokemon_by_name)
    assert result["name_de"] == "Ns Zoroark-ex"

def test_language_filter_omits_unavailable_card():
    cards = [{"id": "svp-190", "available_languages": ["en"]}]
    assert filter_cards_for_language(cards, "de") == []
```

Add a companion Pokédex assertion proving canonical Zoroark remains `Zoroark`, with no `Ns` and no `-ex`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `pytest -q scripts/tests/test_tcg_enrichment.py scripts/tests/test_pdf_generation_options.py`

Expected: the TCG name is overwritten by the canonical species name and cards are not filtered per language.

- [ ] **Step 3: Change Pokédex enrichment to fill, never replace, observed TCG names**

For each language in `available_languages`, use `setdefault` for canonical fallback metadata. Continue to correct `pokemon_id`, `dexId`, types, and card classification. Do not create localized names for unavailable languages.

- [ ] **Step 4: Filter each TCG section by exact card language before PDF generation**

Deep-copy the output data for each language, retain only cards where the language appears in `available_languages`, and leave Pokédex/variant scopes that lack the field unchanged.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `pytest -q scripts/tests/test_tcg_enrichment.py scripts/tests/test_pdf_generation_options.py`

- [ ] **Step 6: Commit**

```bash
git add scripts/fetcher/steps/enrich_tcg_cards_from_pokedex.py scripts/pdf/generate_pdf.py scripts/tests/test_tcg_enrichment.py scripts/tests/test_pdf_generation_options.py
git commit -m "fix(data): retain localized trainer-owned card names"
```

### Task 3: Original card numbers and bounded label layout

**Files:**
- Modify: `scripts/pdf/lib/rendering/text_renderer.py`
- Modify: `scripts/pdf/lib/rendering/card_renderer.py`
- Modify: `scripts/pdf/lib/styles.py`
- Test: `scripts/tests/test_pdf_rendering.py`
- Test: `scripts/tests/test_rendering.py`

**Interfaces:**
- Produces: `TextRenderer.fit_name_lines(text: str, font_name: str, normal_size: float, minimum_size: float, max_width: float) -> tuple[list[str], float]`
- Consumes: `printed_number: str | None`

- [ ] **Step 1: Write failing label-fitting and number tests**

```python
@pytest.mark.parametrize("name", [
    "Technische Maschine: Heiterer Himmel",
    "Technische Maschine: Rückentwicklung",
    "Energiekapsel aus der Vergangenheit",
    "Schubenergie",
])
def test_long_card_name_fits_safe_width(name):
    lines, size = TextRenderer.fit_name_lines(name, FONT, 11, 8, SAFE_WIDTH)
    assert 1 <= len(lines) <= 2
    assert size >= 8
    assert all(pdfmetrics.stringWidth(line, FONT, size) <= SAFE_WIDTH for line in lines)

def test_unnumbered_card_does_not_fall_back_to_section_index(canvas):
    renderer.render_card(canvas, {"printed_number": None, "section_index": 217, "name_de": "Terapagos & Freunde"}, 0, 0, variant_mode=True)
    assert "217" not in captured_strings
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `pytest -q scripts/tests/test_pdf_rendering.py scripts/tests/test_rendering.py`

- [ ] **Step 3: Implement the deterministic fit policy**

Measure with ReportLab `pdfmetrics.stringWidth`. Try normal size, shrink in 0.25-point steps to 8 points, then score every legal word/hyphen split by maximum line width plus line imbalance. Reject text that still exceeds the safe width. Draw one or two centered baselines within the existing name band.

- [ ] **Step 4: Render only `printed_number` for TCG cards**

Use an explicit field-presence check so `None` remains blank. Legacy Pokédex cards may continue to use their existing National Dex number path; TCG cards must never use `section_index` as a printed promo number.

- [ ] **Step 5: Run focused tests and the complete data-driven label-width scan**

Run: `pytest -q scripts/tests/test_pdf_rendering.py scripts/tests/test_rendering.py`

Run: `python scripts/pdf/generate_pdf.py --scope SV04 --language de --skip-poster --skip-images`

Run: `python scripts/pdf/generate_pdf.py --scope SV05 --language de --skip-poster --skip-images`

- [ ] **Step 6: Commit**

```bash
git add scripts/pdf/lib/rendering/text_renderer.py scripts/pdf/lib/rendering/card_renderer.py scripts/pdf/lib/styles.py scripts/tests/test_pdf_rendering.py scripts/tests/test_rendering.py
git commit -m "fix(pdf): fit long labels and preserve printed numbers"
```

### Task 4: Exact-language official logo enrichment

**Files:**
- Create: `enrichments/tcg_set_logo_sources.json`
- Modify: `scripts/fetcher/steps/enrich_tcg_names_multilingual.py`
- Modify: `scripts/poster_assets/finalize_comfyui_poster.py`
- Modify: `scripts/poster_assets/fetch_title_logos.py`
- Modify: `config/posters/SV10.5B/poster.yaml`
- Modify: `config/posters/SV10.5W/poster.yaml`
- Test: `scripts/tests/test_tcg_enrichment.py`
- Test: `scripts/tests/test_fetch_title_logos.py`
- Test: `scripts/tests/test_poster_pdf.py`

**Interfaces:**
- Produces: `load_curated_logo_sources() -> dict[str, dict[str, str]]`
- Consumes: exact language key; no cross-language fallback

- [ ] **Step 1: Add failing exact-language logo tests**

```python
def test_missing_german_logo_never_uses_english_url():
    result = step._generate_missing_logo_urls({"en": ENGLISH_URL}, ["de", "en"])
    assert result == {"en": ENGLISH_URL}

def test_curated_german_logo_overrides_missing_tcgdex_logo():
    assert logos["sv10.5b"]["de"].endswith("sv10pt5_logo_169_de.png")
```

Add finalizer coverage proving a German render without an exact German logo uses localized text instead of `files.en`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `pytest -q scripts/tests/test_tcg_enrichment.py scripts/tests/test_fetch_title_logos.py scripts/tests/test_poster_pdf.py`

- [ ] **Step 3: Add the two official Pokémon asset URLs from the spec**

Store only `sv10.5b.de` and `sv10.5w.de` in the curated mapping. Merge curated sources after TCGdex exact-language URLs. Remove English fallback generation for other languages.

- [ ] **Step 4: Make poster logo resolution exact-language only**

`title_logo_file` returns a file only for the requested language. `resolve_logo_downloads` accepts curated local/HTTP sources and keeps existing path-containment and PNG normalization checks.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `pytest -q scripts/tests/test_tcg_enrichment.py scripts/tests/test_fetch_title_logos.py scripts/tests/test_poster_pdf.py`

- [ ] **Step 6: Commit**

```bash
git add enrichments/tcg_set_logo_sources.json scripts/fetcher/steps/enrich_tcg_names_multilingual.py scripts/poster_assets/finalize_comfyui_poster.py scripts/poster_assets/fetch_title_logos.py config/posters/SV10.5B/poster.yaml config/posters/SV10.5W/poster.yaml scripts/tests/test_tcg_enrichment.py scripts/tests/test_fetch_title_logos.py scripts/tests/test_poster_pdf.py
git commit -m "fix(posters): use exact German set logos"
```

### Task 5: Refresh audit, snapshot manifest, and immutable release input

**Files:**
- Create: `scripts/data/audit_data_refresh.py`
- Create: `scripts/data/build_snapshot_manifest.py`
- Create: `scripts/release/verify_data_snapshot.py`
- Create: `scripts/tests/test_data_snapshot.py`
- Create: `data/snapshot.json`
- Modify: `.github/workflows/build-release.yml`
- Modify: `docs/DATA_FETCHER.md`
- Modify: `docs/RELEASE_WORKFLOW.md`
- Modify: `scripts/tests/test_release_workflows.py`

**Interfaces:**
- Produces: `compare_scope(before: dict | None, after: dict) -> dict`
- Produces: `build_manifest(root: Path, fetched_at: str, boundary: str) -> dict`
- Produces: `verify_manifest(root: Path, manifest: dict) -> list[str]`

- [ ] **Step 1: Add failing snapshot and workflow tests**

```python
def test_snapshot_detects_changed_file_hash(tmp_path):
    manifest = build_manifest(tmp_path, "2026-09-12T00:00:00Z", "2026-09-12")
    (tmp_path / "data/output/SV01.json").write_text("{}", encoding="utf-8")
    assert verify_manifest(tmp_path, manifest) == ["hash mismatch: data/output/SV01.json"]

def test_release_build_does_not_fetch_mutable_data():
    source = (WORKFLOWS / "build-release.yml").read_text(encoding="utf-8")
    assert "fetch.py --scope all" not in source
    assert "verify_data_snapshot.py" in source
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `pytest -q scripts/tests/test_data_snapshot.py scripts/tests/test_release_workflows.py`

- [ ] **Step 3: Implement deterministic audit and snapshot tools**

The audit reads baseline JSON through Git object lookups such as `git show HEAD:data/output/SV01.json`, compares cards by stable `id`, and writes sorted JSON containing counts and field-level changes. It exits non-zero on duplicate printed numbers, foreign-name fallbacks, or an identity/number conflict. The manifest hashes every committed JSON file under `data/source` and `data/output`, records the boundary and UTC fetch time, and is verified before a release build.

- [ ] **Step 4: Replace live release fetching with snapshot verification**

Remove the `Fetch all scope data` step from `.github/workflows/build-release.yml`. Insert `python scripts/release/verify_data_snapshot.py --manifest data/snapshot.json` before poster source fetching.

- [ ] **Step 5: Document the single canonical refresh path**

Document these ordered commands:

```bash
python scripts/fetcher/fetch.py --scope all
python scripts/data/audit_data_refresh.py --baseline-ref HEAD --output tmp/v10-data-refresh-audit.json
python scripts/data/build_snapshot_manifest.py --boundary 2026-09-12 --output data/snapshot.json
python scripts/release/verify_data_snapshot.py --manifest data/snapshot.json
```

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `pytest -q scripts/tests/test_data_snapshot.py scripts/tests/test_release_workflows.py`

- [ ] **Step 7: Commit**

```bash
git add scripts/data/audit_data_refresh.py scripts/data/build_snapshot_manifest.py scripts/release/verify_data_snapshot.py scripts/tests/test_data_snapshot.py .github/workflows/build-release.yml docs/DATA_FETCHER.md docs/RELEASE_WORKFLOW.md
git commit -m "fix(release): build from a verified data snapshot"
```

### Task 6: Add ME05 and perform the complete controlled refresh

**Files:**
- Create: `config/scopes/ME05.yaml`
- Create: `data/source/me05.json`
- Create: `data/output/ME05.json`
- Modify: all changed files under `data/source/` and `data/output/`
- Modify: `data/snapshot.json`
- Create: `config/posters/ME05/poster.yaml`
- Test: `scripts/tests/test_generation_options.py`
- Test: `scripts/tests/test_poster_targets.py`
- Review artifact: `tmp/v10-data-refresh-audit.json`

**Interfaces:**
- Consumes: current public PokeAPI and TCGdex data through the existing fetch engine
- Produces: reviewed 2026-09-12 source/output snapshot including ME05

- [ ] **Step 1: Add failing ME05 scope-discovery tests**

```python
def test_me05_is_a_release_scope():
    assert "ME05" in get_all_scopes()
    assert Path("config/scopes/ME05.yaml").is_file()
```

Add poster-target coverage requiring an enabled ME05 manifest after its artwork is promoted.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `pytest -q scripts/tests/test_generation_options.py scripts/tests/test_poster_targets.py`

- [ ] **Step 3: Add ME05 by following the complete ME04 pipeline pattern**

Use TCGdex set ID `me05`, scope ID `ME05`, output `data/output/ME05.json`, and the normal multilingual, dex-ID correction, Pokédex enrichment, special-card, section, featured-element, and cache steps.

- [ ] **Step 4: Run the complete refresh once**

Run: `python scripts/fetcher/fetch.py --scope all`

Do not edit around a failed scope. Diagnose and fix the responsible source or pipeline boundary, then rerun that scope and finally rerun the complete command.

- [ ] **Step 5: Generate and inspect the structured audit**

Run: `python scripts/data/audit_data_refresh.py --baseline-ref HEAD --output tmp/v10-data-refresh-audit.json`

Review every removal, addition, localized rename, language change, dex-ID correction, and logo change. Add only evidence-backed overrides; rerun until the audit has no unexplained blocking item.

- [ ] **Step 6: Build and verify the snapshot manifest**

Run: `python scripts/data/build_snapshot_manifest.py --boundary 2026-09-12 --output data/snapshot.json`

Run: `python scripts/release/verify_data_snapshot.py --manifest data/snapshot.json`

- [ ] **Step 7: Verify the German promo boundaries**

Run a focused validator that asserts German SVP has 217 insert records, eight intentional gaps between 001 and 224, no printed 500, and exactly one unnumbered `Terapagos & Freunde`; assert German MEP has 88 records and displays 064/079 for Serpiroyal/Glutexo.

- [ ] **Step 8: Run focused tests and verify GREEN**

Run: `pytest -q scripts/tests/test_generation_options.py scripts/tests/test_poster_targets.py scripts/tests/test_tcg_enrichment.py scripts/tests/test_tcg_transform.py scripts/tests/test_data_snapshot.py`

- [ ] **Step 9: Commit**

```bash
git add config/scopes/ME05.yaml config/posters/ME05/poster.yaml data/source data/output data/snapshot.json scripts/tests/test_generation_options.py scripts/tests/test_poster_targets.py
git commit -m "feat(data): refresh all scopes and add ME05"
```

### Task 7: Correct and add reviewed poster artwork

**Files:**
- Modify: `assets/posters/SV07/poster-flux2-artwork.png`
- Modify: `assets/posters/SV07/poster-flux2-provenance.json`
- Modify: `assets/posters/SV10.5B/poster-flux2-provenance.json`
- Modify: `assets/posters/SV10.5W/poster-flux2-provenance.json`
- Create: `assets/posters/ME05/poster-flux2-artwork.png`
- Create: `assets/posters/ME05/poster-flux2-provenance.json`
- Modify: `docs/POSTER_ARTWORK_EXPERIMENT_LOG.md`
- Test: `scripts/tests/test_poster_assets.py`
- Test: `scripts/tests/test_poster_fingerprints.py`

**Interfaces:**
- Consumes: the complete private `renderer.local.yaml` without logging its values
- Produces: immutable `run.json`, `comfyui.log`, generated candidates, reviewed promoted masters, and provenance

- [ ] **Step 1: Probe the configured render worker and plan each scope**

Run: `python scripts/poster_assets/poster_work_plan.py --scope SV07`

Run: `python scripts/poster_assets/poster_work_plan.py --scope ME05`

Run the documented remote probe from `docs/POSTER_RENDER_WORKER.md` using only marker values. If unreachable, stop GPU work while continuing all non-GPU tasks.

- [ ] **Step 2: Refresh exact German title-logo sources without regenerating artwork**

Run: `python scripts/poster_assets/fetch_poster_sources.py --scope SV10.5B --kind logos --force`

Run: `python scripts/poster_assets/fetch_poster_sources.py --scope SV10.5W --kind logos --force`

Regenerate localized poster overlays/provenance through the documented finalizer path and verify the German logo pixel hash differs from English.

- [ ] **Step 3: Generate one new-seed SV07 candidate through the configured remote worker**

Select a new deterministic seed that is not present in the SV07 provenance or experiment log. Run the repository's remote prepare, transfer, queue, retrieve, and validate commands. Retrieve `run.json`, `comfyui.log`, and every generated image.

- [ ] **Step 4: Inspect SV07 full image and all physical crops**

Render the candidate's nine physical slices. Reject it if Hopplo has anything other than two long ears or if any other subject has duplicate limbs, malformed anatomy, wrong count, bad crop containment, text, logo, or watermark. If rejected for the same Hopplo defect, make one controlled identity-lock candidate rather than stacking prompt tweaks.

- [ ] **Step 5: Initialize, generate, and inspect ME05**

Run: `python scripts/poster_assets/init_poster_scope.py --scope ME05`

Fetch cutouts and logos, validate exact subject identities, generate through the configured remote worker, retrieve all immutable artifacts, and inspect the full master plus all nine physical crops. Promote only a candidate that passes every gate.

- [ ] **Step 6: Promote reviewed candidates and refresh provenance**

Use `promote_comfyui_poster.py` for SV07 and ME05. Record rejected and accepted candidates in `docs/POSTER_ARTWORK_EXPERIMENT_LOG.md` without private host, username, alias, or path data.

- [ ] **Step 7: Verify all promoted posters**

Run: `python scripts/poster_assets/validate_promoted_poster.py --all-enabled`

Run: `pytest -q scripts/tests/test_poster_assets.py scripts/tests/test_poster_fingerprints.py scripts/tests/test_source_pixel_audit.py scripts/tests/test_runner_source_pixel_gate.py`

- [ ] **Step 8: Commit**

```bash
git add assets/posters/SV07 assets/posters/SV10.5B/poster-flux2-provenance.json assets/posters/SV10.5W/poster-flux2-provenance.json assets/posters/ME05 config/posters/ME05 docs/POSTER_ARTWORK_EXPERIMENT_LOG.md
git commit -m "fix(posters): replace Stellarkrone and add Dunkelnacht"
```

### Task 8: Generate and visually verify the corrected German PDFs

**Files:**
- Create or update ignored deliverables under: `output/de/`
- Create ignored QA renders under: `tmp/pdfs/v10-review/`
- Test: `scripts/tests/test_pdf_generation_options.py`
- Test: `scripts/tests/test_poster_pdf.py`

**Interfaces:**
- Consumes: committed v10.0 data snapshot and promoted poster assets
- Produces: changed/new German v10.0 PDFs plus PNG evidence for manual QA

- [ ] **Step 1: Confirm the exact PDF output count before authoring**

Generate all 31 German scope PDFs. This intentionally covers the 30 existing scopes plus ME05, because the renderer and language-membership changes are global and the complete refresh may change scopes beyond the thirteen initially reported.

- [ ] **Step 2: Mark the PDF edit operation exactly once**

Immediately before the first generation command, run:

```bash
node container_tools/mark_artifact_operation_started.mjs --operation-kind edit --expected-output-count 31 --output-format pdf
```

- [ ] **Step 3: Generate every changed German PDF**

Run: `python scripts/pdf/generate_pdf.py --scope all --language de`

A generation failure in any of the 31 scopes blocks the candidate.

- [ ] **Step 4: Verify text and numbering programmatically**

Use `pdftotext` or `pdfplumber` to assert all seven Energy corrections, exact SV09 owner names including `Ns Zoroark-ex`, MEP 064 and 079, and exactly one `Terapagos & Freunde` with no adjacent printed promo number.

- [ ] **Step 5: Render visual QA pages**

Render at least SV04 pages 19 and 21, SV05 page 17, the SV07 poster pages/crops, both SV10.5 German poster pages, the SVP tail, the MEP pages containing 064 and 079, and the complete ME05 poster to PNG with Poppler.

- [ ] **Step 6: Inspect affected and representative pages**

Confirm no clipped or overlapping labels, no English logo in German output, two Hopplo ears, correct promo gaps and blank unnumbered label, sharp artwork, correct crop order, and consistent cut geometry. Rebuild after any correction and inspect the latest PNGs again.

- [ ] **Step 7: Run PDF-focused tests**

Run: `pytest -q scripts/tests/test_pdf_generation_options.py scripts/tests/test_pdf_rendering.py scripts/tests/test_rendering.py scripts/tests/test_poster_pdf.py`

### Task 9: v10.0 release metadata and full candidate verification

**Files:**
- Create: `config/release_notes/v10.0.yaml`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `README.de.md`
- Modify: `.github/workflows/verify-release.yml`
- Modify: `scripts/tests/test_render_release_notes.py`
- Modify: `scripts/tests/test_announce_release.py`
- Modify: `release-manifest.json` only through the release tooling

**Interfaces:**
- Consumes: verified snapshot, posters, and generated PDFs
- Produces: local v10.0 release notes, manifest, language archives, and verification result

- [ ] **Step 1: Add failing v10.0 release-contract tests**

Assert that the manual/PR verification workflow selects `v10.0`, release notes describe the reviewed refresh and ME05, and rendered scope/PDF counts come from the manifest rather than a handwritten number.

- [ ] **Step 2: Run release tests and verify RED**

Run: `pytest -q scripts/tests/test_render_release_notes.py scripts/tests/test_announce_release.py scripts/tests/test_release_workflows.py`

- [ ] **Step 3: Add v10.0 notes and documentation**

Describe the immutable data snapshot, corrected German card labels/names/logos/promos, rejected/replaced Stellarkrone panorama, ME05 addition, and clear 2026-09-12 boundary. Do not claim release publication.

- [ ] **Step 4: Run release tests and verify GREEN**

Run: `pytest -q scripts/tests/test_render_release_notes.py scripts/tests/test_announce_release.py scripts/tests/test_release_workflows.py`

- [ ] **Step 5: Run the complete verification suite**

Run: `pytest -q`

Run: `python scripts/release/verify_data_snapshot.py --manifest data/snapshot.json`

Run: `python scripts/poster_assets/validate_promoted_poster.py --all-enabled`

Run the same full release-candidate build commands documented in `.github/workflows/build-release.yml`, using the committed snapshot and v10.0 release-notes contract. Verify all generated archives, the manifest, and release notes.

- [ ] **Step 6: Review the final diff against this plan**

Check every spec acceptance item against fresh command output and the latest rendered images. Confirm that no ignored renderer marker, hostname, username, private path, token, downloaded source cache, or raw user photograph is staged.

- [ ] **Step 7: Commit the verified release candidate metadata**

```bash
git add config/release_notes/v10.0.yaml CHANGELOG.md README.md README.de.md .github/workflows/verify-release.yml scripts/tests/test_render_release_notes.py scripts/tests/test_announce_release.py release-manifest.json
git commit -m "docs: prepare Binder Pokédex v10.0 candidate"
```

- [ ] **Step 8: Report the local candidate without publishing**

Report exact test totals, snapshot boundary and reviewed count changes, poster candidate provenance hashes, generated PDF paths, and any remaining blocker. Do not push, tag, create a GitHub release, or claim visual approval for an image that was not inspected.

## Execution status (2026-09-12)

The checklists above retain the original plan. This table and the final
verification record below describe actual execution and supersede interim states.

| Area | Status | Verified result |
| --- | --- | --- |
| Tasks 1-6: identity, localization, layout, logos, snapshot, refresh | Complete | All 31 scopes refreshed; the 63-file snapshot is locked to the 2026-09-12 boundary and verifies without drift. ME05 is included with 120 cards. |
| Task 7: poster artwork | Complete | SV07, ME05, and SV08 passed raw/master and all nine physical-crop agent review. All 42 targets are promoted, enabled, and validated. Bounded resolution/model/reference comparisons and every accepted/rejected raw hash are recorded in the experiment log; all production assets remain 4B BF16. Provenance now distinguishes agent review from human approval. |
| Task 8: German PDFs | Complete | All 31 PDFs / 807 pages were rebuilt from the final source revision. Text and Poppler checks pass for Energy names, owner-qualified SV09 names, safe SV04/SV05 wrapping, German SV10.5 logos, corrected SV07 Hopplo, SVP numbering plus the unnumbered card, and MEP numbers 064/079. The actual PDF panorama counts visibly show SVP 217 and MEP 88. |
| Task 9: local release candidate | Complete locally; external PR approval pending | 733 tests passed and 1 skipped; independent code review has no remaining findings. All 42 bundles are current without planner actions and all 267 language counts agree with their card selection. All 168 PDFs / 4,781 pages were rebuilt from one source commit, and all nine archives pass integrity, exact PDF content, notices, and source checks. Manifest and release notes were regenerated from these final artifacts. No release was published. |

ME05 and SV08 now also have reviewed panoramas. The ordinary cover remains a
diagnostic/explicit skip option, not an
accepted substitute for these release targets. A regression test now exercises
the real PDF poster routing for every current section and rejects a missing or
disabled panorama. The final localized PDFs and release archives have now been
rebuilt and checked. The branch has been pushed and PR #17 opened with subsequent
operator authorization; no merge, tag, or GitHub release was created.

The additional French page-22 QA exposed a localization gap in Task 2: names
such as `Zoroark-ex de N` retained their embedded marker but the renderer added
a second ex logo at the end. The canonical name composer now renders that
existing marker in its original position. Six literal regression cases cover
French, Spanish, Italian, German, English, and a species-name substring guard;
the three affected-language cases were observed failing before the fix. The
full snapshot scan finds 201 affected labels in twelve PDF targets (ME02.5,
SV09, SV10, and SVP, each in FR/ES/IT). No source card data or poster pixels
change. Independent review accepts the correction; all PDFs are being rebuilt
from one new source revision so their notices and archive provenance agree.

The subsequent raster review caught one more Task 8 mismatch: German SVP and
MEP card pages correctly contained 217 and 88 inserts, but their panorama
information panels counted all languages (226 and 89). Japanese SV10 similarly
showed 244 instead of 132. The existing card-page language selector is now a
shared pure helper used by the panorama finalizer as well. Three regressions
were observed failing before the fix; 33 focused tests now pass, including all
267 configured target/language counts. Only deterministic overlays and their
provenance need refreshing; no artwork regeneration or new visual approval is
implied. Full validation and a source-consistent candidate rebuild follow.

That canonical refresh also exposed a legacy serialization case in ME02,
SV01, SV02, and SV04: promotion had re-encoded the reviewed PNG. The loader
compared the stable output against the pre-promotion byte hash even though its
registered output hash and reviewed pixel hash both matched. It now accepts
only that exact registered, pixel-identical promoted encoding; new generation
runs, changed pixels, missing output records, and wrong output hashes remain
rejected. The valid re-encoding test failed before the correction, and all six
focused loader cases now pass. Generation history and visual reviews are kept
unchanged.

Final pre-build gate: `733 passed, 1 skipped`; all 42 bundles are current with
no planner actions, the 63-file snapshot verifies, and independent review has
no findings for either follow-up. All 42 master SHA-256 values are unchanged;
across all provenance records only 27 overlay fingerprints and their refresh
timestamps changed. The source-consistent 168-PDF rebuild subsequently passed.

### Final artifact verification

- PDF and archive source: `48f82439bf7aa1272fe7d877ebb25919287c4d93`, version `v10.0`.
- 168 PDFs / 4,781 A4 pages across nine languages; German: 31 PDFs / 807 pages.
- Every final PDF has the correct version, exact source commit, and project
  notice. All nine ZIPs pass CRC/integrity checks and contain byte-identical
  copies of the final PDFs, exact license files, and matching `SOURCE.json`.
- Final Poppler checks confirm all reported label, number, logo, and panorama
  corrections. Thirty previous comparison pages are pixel-identical; SVP/de
  and MEP/de openers have only the intended count correction, and SV10/ja now
  visibly shows 132. ME05/SV08 opening pages retain their checked appearance
  in every configured language. Visual QA is targeted, not a manual review of
  every one of the 4,781 pages.
- All 63 locked data files still verify. Nine additional release-note/workflow
  tests pass against the final metadata.
- Local audit evidence: `tmp/v10-language-build/verification.json`,
  `tmp/v10-language-build/archive-verification.json`, and
  `tmp/pdfs/v10-panorama-final/`. Public candidate metadata is generated in
  `release-manifest.json`; ZIPs and rendered PDFs remain local artifacts.
- Required external PR review remains pending. Scoped GitHub checks pass for
  the source revision; the full Linux artifact job was intentionally skipped
  without `full-release-check` or manual dispatch. No merge or release is implied.
