# P02 Masked-Fallback Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Release the exact accepted P02-H panorama with honest two-repair provenance and a German `Juni 2000` info panel, while retaining the one-shot default and the user's final overlay review gate.

**Architecture:** A new focused masked-composition audit verifies the two card-local repairs against original one-shot A, embeds compact mask geometry and an outside-pixel digest in schema-3 promoted provenance, and lets the release validator recheck the durable master without temporary GPU files. The renderer gains a strictly validated language-specific, month-precision display override; ordinary one-shot promotions and other sets retain their current contracts.

**Tech Stack:** Python 3, Pillow, pytest, ReportLab/Poppler for final PDF QA, YAML/JSON, Git.

**Spec:** `docs/superpowers/specs/2026-09-25-p02-masked-fallback-promotion-design.md`

## Global Constraints

- Keep FLUX.2 `joint_scene` one-shot the default. Masked composition is an explicit, reviewed fallback only; never relabel H as a pure one-shot.
- P02-H master SHA-256 is `26d6a468e59b7dd1ea21931d85ae016ed220324d23eee1fd8aacb642001a07f6`; one-shot A is `67f4e6dcfa88260aa35cb75c843b47c9975ddd3985154d3f318addb69a892e4d`.
- The exact H audit is 10,548 changed pixels inside 11,121 editable pixels, zero outside, with seven other physical cards pixel-identical to A. Derive these figures afresh before using them as evidence.
- Do not invent a German day. Show `Juni 2000` only in P02's German poster overlay; retain the global imported date and other languages unchanged.
- Before any GPU work, obey `AGENTS.md` and the active workspace's private `renderer.local.yaml`. This plan needs no new GPU run.
- Commit only the reviewed text-free master and provenance as poster raster assets; source cutouts, logos, render jobs, masks and previews stay under ignored workspaces. Never expose private worker configuration.
- Keep P02 `pdf.enabled: false` until the corrected info card is shown to and accepted by the user and every routed language passes its prebuild check. An uncommitted local enable is permitted for the candidate PDF build; commit the enabled route only after print/PDF QA passes.
- Do not stage unrelated root-level ZIPs or release files; commit and push focused changes to `codex/v10-refresh` after each independent task.

## Review Focus

1. An old or missing ignored source artifact must fail *before* replacing the stable master; Task 3 tests this transaction boundary.
2. A padded 768 × 1056 repair mask must not shift by one pixel when mapped into its 750 × 1050 physical card; Task 2 tests center-crop geometry and the exact H audit.
3. A one-channel, one-level pixel change outside the mask must be detected after PNG re-encoding; Task 2 tests pixel-based, not byte-based, comparison.
4. A malformed `2000-06-16` value declared as month precision, or an override for the wrong language, must not leak into the German/English panels; Task 1 tests both.
5. Enabling P02's global PDF route while any routed language lacks a valid logo/overlay or the German info card lacks approval must fail; Task 5 tests and checks this gate.

---

### Task 1: Localized month-precision poster date

**Files:**
- Modify: `scripts/poster_assets/finalize_comfyui_poster.py:212-253,318-350,555-600`
- Modify: `scripts/poster_assets/provenance.py:1420-1530`
- Modify: `config/posters/Base2/poster.yaml`
- Test: `scripts/tests/test_poster_targets.py`
- Test: `scripts/tests/test_poster_fingerprints.py`

**Interfaces:**
- Consumes: existing `scope_data["release_date"]` and optional `text_content.release_date_overrides` mapping.
- Produces: `info_panel_values(scope_data, language, content_mode, *, header_text=None, text_content=None)`, where `text_content` is an optional `dict`; callers not passing it retain the old result.

- [ ] **Step 1: Write failing renderer tests.** Add a P02 test asserting `info_panel_values(data, "de", "set_summary", text_content={"release_date_overrides": {"de": {"value": "2000-06", "precision": "month"}}})[-1] == "Juni 2000"`, the same call for `en` still yields `June 16, 1999`, and malformed/mismatched precision raises `ValueError`. A separate overlay-fingerprint fixture must change its digest when the override changes, while its generation fingerprint stays fixed.

```python
def test_p02_month_override_is_local_and_strict():
    data = {"name": "Jungle", "release_date": "1999-06-16", "sections": {"all": {"title": {"de": "Dschungel", "en": "Jungle"}, "cards": []}}}
    config = {"release_date_overrides": {"de": {"value": "2000-06", "precision": "month"}}}
    assert info_panel_values(data, "de", "set_summary", text_content=config)[-1] == "Juni 2000"
    assert info_panel_values(data, "en", "set_summary", text_content=config)[-1] == "June 16, 1999"
    with pytest.raises(ValueError, match="month precision"):
        info_panel_values(data, "de", "set_summary", text_content={"release_date_overrides": {"de": {"value": "2000-06-16", "precision": "month"}}})
```

- [ ] **Step 2: Prove red.** Run `venv/bin/python -m pytest -q scripts/tests/test_poster_targets.py::test_p02_month_override_is_local_and_strict` and the new fingerprint test; expect the new `text_content` keyword to fail before implementation.
- [ ] **Step 3: Implement only the optional override.** Validate `YYYY-MM` for `month`, `YYYY-MM-DD` for `day`, real calendar dates, and exact language keys. Thread `text_content` through `draw_final_text_cells` → `draw_info_panel` → `info_panel_values`, and through `build_overlay_fingerprint`. Add to Base2 only:

```python
def release_text(scope_data: dict, language: str, text_content: dict | None) -> str:
    overrides = (text_content or {}).get("release_date_overrides", {})
    override = overrides.get(language)
    if override is None:
        return localized_date(str(scope_data["release_date"]), language)
    value, precision = override["value"], override["precision"]
    if precision == "day" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return localized_date(value, language)
    if precision == "month" and re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = map(int, value.split("-"))
        if not 1 <= month <= 12:
            raise ValueError("Invalid release month")
        if language in ("ja", "zh_hans", "zh_hant"):
            return f"{year}年{month}月"
        if language == "ko":
            return f"{year}년 {month}월"
        return f"{MONTHS[language][month - 1]} {year}"
    raise ValueError(f"Invalid {precision} precision release date: {value}")
```

```yaml
text_content:
  mode: set_summary
  release_date_overrides:
    de:
      value: "2000-06"
      precision: month
```

- [ ] **Step 4: Prove green and regression.** Run the new tests, `venv/bin/python -m pytest -q scripts/tests/test_poster_targets.py scripts/tests/test_poster_fingerprints.py`, and inspect the DE/EN computed rows. Confirm `data/output/Base2.json` is not modified.
- [ ] **Step 5: Commit and push.** Stage only the renderer, fingerprint, Base2 config, and tests; commit `Add month-precision German poster release date`.

### Task 2: Mask geometry and compositing proof

**Files:**
- Create: `scripts/poster_assets/masked_fallback.py`
- Create: `scripts/tests/test_masked_fallback.py`

**Interfaces:**
- Produces: `card_mask_to_canvas(mask: Image.Image, cell: Cell, canvas_size: tuple[int, int]) -> Image.Image`; `audit_masked_merge(base: Path, final: Path, repairs: list[tuple[Path, Image.Image]]) -> dict`; `encode_mask(mask: Image.Image) -> dict`; `decode_mask(record: dict) -> Image.Image`; `outside_pixel_digest(image: Image.Image, union_mask: Image.Image) -> str`.
- The repair tuple is `(full-size repaired artwork path, full-size binary mask)`. The audit verifies each repaired artwork is unchanged outside its own mask and reconstructs the final image from A plus the disjoint repairs.

- [ ] **Step 1: Write failing small-image tests.** Cover center-crop mapping from 768 × 1056 to 750 × 1050, rejection of any white mask pixel in removed padding, RLE roundtrip, overlapping masks, an altered outside pixel with only one red-channel unit, a missing repair image, and final-pixel mismatch.

```python
def test_one_channel_outside_change_is_rejected(tmp_path):
    base = Image.new("RGB", (4, 4), (10, 20, 30))
    repair = base.copy(); repair.putpixel((1, 1), (40, 20, 30))
    final = repair.copy(); final.putpixel((3, 3), (11, 20, 30))
    mask = Image.new("L", (4, 4), 0); mask.putpixel((1, 1), 255)
    base_path = tmp_path / "base.png"; base.save(base_path)
    repair_path = tmp_path / "repair.png"; repair.save(repair_path)
    final_path = tmp_path / "final.png"; final.save(final_path)
    with pytest.raises(ValueError, match="outside"):
        audit_masked_merge(base_path, final_path, [(repair_path, mask)])
```

- [ ] **Step 2: Prove red.** Run `venv/bin/python -m pytest -q scripts/tests/test_masked_fallback.py`; expect import/function failures.
- [ ] **Step 3: Implement strict Pillow audit.** Use each `layout.cell(row, column)` as the position; the mask's centered padding is `(mask.width-cell.width)//2` and `(mask.height-cell.height)//2`, rejecting odd differences or nonzero cropped-away pixels. Require binary `0/255` mask pixels, disjoint full-canvas masks, identical 2368 × 3268 image geometry for P02, exact reassembly of the final *pixels*, and zero changes outside each repair mask. Store sorted nonoverlapping `(start, length)` RLE spans and image dimensions; compute outside digest by zeroing masked pixels in RGB then SHA-256 hashing dimensions plus pixel bytes.

```python
def encode_mask(mask: Image.Image) -> dict:
    if mask.mode != "L" or any(value not in (0, 255) for value in mask.getdata()):
        raise ValueError("Repair mask must be binary L")
    runs: list[list[int]] = []
    start = None
    for index, value in enumerate(mask.getdata()):
        if value == 255 and start is None:
            start = index
        elif value == 0 and start is not None:
            runs.append([start, index - start]); start = None
    if start is not None:
        runs.append([start, mask.width * mask.height - start])
    return {"width": mask.width, "height": mask.height, "runs": runs}
```

```python
def outside_pixel_digest(image: Image.Image, union_mask: Image.Image) -> str:
    rgb = image.convert("RGB")
    outside = rgb.copy()
    outside.paste((0, 0, 0), (0, 0), union_mask)
    digest = hashlib.sha256()
    digest.update(f"{rgb.width}x{rgb.height}:RGB\n".encode("ascii"))
    digest.update(outside.tobytes())
    return digest.hexdigest()
```

- [ ] **Step 4: Prove green and audit H read-only.** Run `venv/bin/python -m pytest -q scripts/tests/test_masked_fallback.py`. Use the existing A, Pikachu/Evoli repaired masters and masks under `tmp/`; require H's current SHA-256 and pixel counts `10548/11121/0`. If center-crop geometry does not reproduce those counts, stop and trace the actual padding/origin rather than adjusting expected numbers.
- [ ] **Step 5: Commit and push.** Stage only the new helper and tests; commit `Audit masked fallback composition at print pixels`.

### Task 3: Explicit schema-3 promotion and validation

**Files:**
- Modify: `scripts/poster_assets/promote_comfyui_poster.py`
- Modify: `scripts/poster_assets/provenance.py`
- Modify: `scripts/poster_assets/validate_promoted_poster.py`
- Modify: `scripts/poster_assets/poster_work_plan.py`
- Modify: `scripts/poster_assets/training_dataset.py` to exclude schema-3 masked finals from pure one-shot target discovery
- Test: `scripts/tests/test_poster_fingerprints.py`
- Test: `scripts/tests/test_poster_work_plan.py`
- Test: `scripts/tests/test_masked_fallback.py`

**Interfaces:**
- Consumes: Task 2's audit/encode/decode/digest functions and a new ignored `--composition-input PATH` JSON containing relative A-run/A-master paths, the two repair run/log/job/result/mask paths, physical `(row,column)` targets, and the tracked H review-provenance path.
- Produces: `load_and_audit_composition(input_path: Path, artwork: Path, bundle: PosterBundle) -> tuple[dict, Path, Path]` in `masked_fallback.py`, returning a durable composition record plus local A-run/A-master paths; `verify_localized_overlay_approval(payload: dict) -> bool` comparing an accepted preview hash **and** overlay-fingerprint hash to the schema-3 records; `promote(..., composition_input_path: Path | None = None)` in the promoter. Ordinary calls retain schema 2. Explicit composition calls emit schema 3 with `run` recording actual A, `composition.kind == "masked_fallback"` recording H, the two repairs, and the newly rendered preview hash, and `outputs.artwork` recording the stable H master.

- [ ] **Step 1: Write failing integration tests.** Add `_masked_promotion_fixture(tmp_path, monkeypatch)` beside the existing `_promotion_fixture` in `test_poster_fingerprints.py`: it returns a `SimpleNamespace` with `base_run`, `base_artwork`, `final`, `input`, `base_sha256` and prepared mock source/logo paths. Give it one base image, two disjoint repair images and masks, H review binding, and a fake logo approval. Assert schema 3 records exact A and H separately, technical validation passes without temporary files after promotion, normal schema-2 promotion is unchanged, refresh of a schema-3 overlay retains the same H pixels, and wrong job hash/missing log/overlap/outside pixel/missing human approval/fingerprint drift fail before stable file replacement.

```python
def test_masked_promotion_never_calls_one_shot_approval(tmp_path, monkeypatch):
    fixture = _masked_promotion_fixture(tmp_path, monkeypatch)
    artwork, _, _, provenance_path = promotion.promote(
        "Example", fixture.final, language="de",
        run_metadata_path=fixture.base_run,
        composition_input_path=fixture.input,
    )
    stored = json.loads(provenance_path.read_text())
    assert stored["schema_version"] == 3
    assert stored["run"]["source_artwork"]["sha256"] == fixture.base_sha256
    assert stored["composition"]["kind"] == "masked_fallback"
    assert stored["outputs"]["artwork"]["pixel_sha256"] == image_pixel_record(artwork)["pixel_sha256"]
```

- [ ] **Step 2: Prove red.** Run the new exact tests in `test_poster_fingerprints.py`, `test_poster_work_plan.py`, and `test_masked_fallback.py`; expect rejection of `composition_input_path`/schema 3.
- [ ] **Step 3: Implement fail-closed branch before staging.** Keep the existing one-shot branch untouched. In the new branch, load A with `load_run_metadata(base_run, base_master)`, validate its generation fingerprint against the current manifest/sources, hash each review evidence and returned job component, run Task 2's audit, bind exact H and logo human approvals, and stage H with a byte-preserving copy (its archived PNG already has 300-dpi metadata). Render the new German preview and store its SHA-256 in `composition.preview_sha256`, then stage schema-3 provenance and stable master transactionally. Do **not** call `approve_joint_scene_visual_review` on H as if H were raw one-shot output.

```python
if composition_input_path is None:
    run_metadata = load_run_metadata(run_metadata_path, artwork)
    composition = None
else:
    composition, base_run_path, base_artwork_path = load_and_audit_composition(
        composition_input_path, artwork, bundle
    )
    run_metadata = load_run_metadata(base_run_path, base_artwork_path)
    if approve_joint_scene:
        raise ValueError("Masked fallback uses its exact human review record")
```

- [ ] **Step 4: Implement durable validation and overlay refresh.** Schema-3 technical validation requires H's pixel hash/human artwork acceptance and the decoded mask's outside digest, checks the recorded A generation fingerprint and source hashes, and never requires ignored A files. It reports `localized_overlay_approved: false` until the later user approval; release validation rejects that state only if the PDF route is enabled. Refresh reads the existing schema-3 container, reuses the same text-free H master and composition record, and changes only the cheap overlay fingerprint/derivatives. Make `poster_work_plan` identify this as a validated masked fallback; have `training_dataset` skip schema-3 fallback entries rather than label H as a raw one-shot target.

```python
if schema_version == 3:
    composition = payload["composition"]
    if composition.get("kind") != "masked_fallback":
        raise ValueError("Unsupported schema-3 poster composition")
    mask = decode_mask(composition["union_mask"])
    with Image.open(artwork_path) as loaded:
        outside_hash = outside_pixel_digest(loaded, mask)
    if outside_hash != composition["outside_base_pixel_sha256"]:
        raise ValueError("Promoted artwork changed outside repair masks")
    overlay_approved = verify_localized_overlay_approval(payload)
    if bundle.pdf_enabled and not overlay_approved:
        raise ValueError("Enabled masked poster lacks localized overlay approval")
```
- [ ] **Step 5: Prove green and regression.** Run the three focused test modules, then `venv/bin/python -m pytest -q scripts/tests`; run `python -m scripts.poster_assets.validate_promoted_poster --all-enabled` and `python -m scripts.poster_assets.poster_work_plan --all-configured`. No current poster may change route or fail due to schema-3 support.
- [ ] **Step 6: Commit and push.** Stage only the contract, validator, planner/training changes actually needed, and tests; commit `Validate explicit masked poster fallback provenance`.

### Task 4: Adopt exact P02-H master, keep PDF disabled, request overlay review

**Files:**
- Modify: `config/posters/Base2/poster.yaml`
- Create after successful audit: `assets/posters/Base2/poster-flux2-artwork.png`
- Create after successful audit: `assets/posters/Base2/poster-flux2-provenance.json`
- Modify: `assets/review-pending/p02-h/review-provenance.json` to mark technical master promotion while retaining pending localized overlay and PDF flags; do not rewrite earlier approval hashes
- Modify: `docs/reviews/2026-09-25-p02-h-logo-review.md` and `docs/POSTER_ARTWORK_STATUS.md` for factual status
- Test: `scripts/tests/test_poster_targets.py`, `scripts/tests/test_poster_fingerprints.py`

**Interfaces:**
- Consumes: `tmp/oneshot-trials/p02-batch-20260922-a/review/artwork-300dpi.run.json`, archived A/H masters, both repair workspaces and the tracked H approval. Writes ignored assembly input/preview/crops under `tmp/foreground-repair-trials/p02-combined-20260925-h/`.
- Produces: stable H master and schema-3 provenance only if exact historical inputs validate; a new review preview and nine physical crops, with `pdf.enabled: false`.

- [ ] **Step 1: Add a failing P02 contract test.** It must compare Base2's configured `generation` to A's actual `2.0` MP, `spatial_source_detail_joint`, seed `260924002`, compare A's recorded fingerprint to a rebuild from current manifest and cached sources, and assert H/master/review hashes. If ignored A is absent in CI, the test uses the committed schema-3 provenance after adoption rather than opening `tmp/`.

```python
def test_p02_accepted_h_promotion_is_exact():
    bundle = poster_bundle("Base2")
    generation = bundle.manifest["artwork"]["generation"]
    assert (generation["generation_megapixels"], generation["reference_mode"], generation["seed"]) == (
        2.0, "spatial_source_detail_joint", 260924002
    )
    assert sha256_file(bundle.asset_dir / "poster-flux2-artwork.png") == (
        "26d6a468e59b7dd1ea21931d85ae016ed220324d23eee1fd8aacb642001a07f6"
    )
    assert bundle.pdf_enabled is False
```
- [ ] **Step 2: Align only A's real inputs.** Move the exact three source-detail `sha256`/`traits` records, the added grass-depth scene constraint and actual generation values from A's immutable run into Base2's manifest. Rebuild its generation fingerprint; it must equal A's recorded `ce5b0c3761663ce466d9b5aacbc34c0036e8bcf87e9bc915a98257e9f67f38df`. A mismatch is a stop condition, not an invitation to edit the recorded hash.
- [ ] **Step 3: Build the ignored composition input and run promotion.** Use the Pikachu mask SHA-256 `a6b15c59e7132ccf3f36c70c83d532690898ad31ac0f2776c0a9024a16af524b`, Evoli mask `9f33dd254b10d96edc2da1b20e5bb687e0b1e684498cfa82f5283b01c1dcf9ba`, both returned jobs, their review evidence and H's exact master. The CLI is:

```bash
venv/bin/python -m scripts.poster_assets.promote_comfyui_poster \
  --scope Base2 \
  --artwork assets/review-pending/p02-h/artwork-300dpi.png \
  --run-metadata tmp/oneshot-trials/p02-batch-20260922-a/review/artwork-300dpi.run.json \
  --composition-input tmp/foreground-repair-trials/p02-combined-20260925-h/promotion-input.json \
  --language de
```

- [ ] **Step 4: Verify adoption before claiming it.** Run `venv/bin/python -m scripts.poster_assets.validate_promoted_poster --scope Base2`; expect technical validation to pass with `localized_overlay_approved: false`. Rehash H, inspect the full German preview and all nine new physical crops; compare the three Pokémon cards to source art and seven unchanged cards to A. Confirm the new r2c2 date reads `Juni 2000`, logo remains the exact approved historical mark, and `pdf.enabled` remains false.
- [ ] **Step 5: Show the new info card to the user.** Present the full panorama plus r2c2 close-up for its separate overlay acceptance. Do not enable the PDF or claim localized approval until the user accepts this exact preview hash.
- [ ] **Step 6: Commit and push only the technically validated master, provenance, manifest and status documentation.** The release gate remains disabled; commit `Promote reviewed P02 H with honest fallback evidence`.

### Task 5: After user approval, enable and print-check the P02 PDF

**Files:**
- Modify: `assets/review-pending/p02-h/review-provenance.json` with the new exact overlay approval hash/date
- Modify: `config/posters/Base2/poster.yaml` (`pdf.enabled: true` only after all checks)
- Modify: `docs/POSTER_ARTWORK_STATUS.md` and P02 review note
- Test: `scripts/tests/test_poster_pdf.py`, `scripts/tests/test_poster_targets.py`, and full suite
- Output: canonical v10 P02 PDF(s) from `scripts/pdf/generate_pdf.py`, not the unchanged v9 originals

**Interfaces:**
- Consumes: explicit user approval of the Task-4 German info card and verified schema-3 P02 promotion.
- Produces: enabled P02 panorama route only after all supported/routed language overlays and final print checks pass.

- [ ] **Step 1: Write a failing release-gate test.** The test must reject `pdf.enabled: true` for schema-3 P02 when the localized overlay approval is absent or its preview hash does not match; a separate routing test confirms a disabled P02 keeps the old section-cover fallback.
- [ ] **Step 2: Implement the gate and record the exact user approval.** Store it in schema-3 `composition.localized_overlay_approval` and the tracked P02-H review record, bound to the new German preview hash and current overlay-fingerprint hash, not the earlier logo-preview hash. The Task-3 validator's `verify_localized_overlay_approval` then blocks PDF routing if either binding drifts. Re-run the gate tests red/green.
- [ ] **Step 3: Check every routed language.** Fetch configured title logos via `fetch_poster_sources.py --scope Base2 --kind logos`; generate and inspect each affected title/info card. Any configured-but-missing logo, clipped text, incorrect card count or date blocks `pdf.enabled: true`. A language deliberately configured with text instead of a logo retains that explicit path.
- [ ] **Step 4: Enable locally and build a candidate.** First check existing PDF output paths/hashes to preserve previous artifacts. Set `pdf.enabled: true` in the uncommitted candidate checkout only after Steps 1–3 pass. Follow the `pdf:pdf` skill's operation marker immediately before the first authoring command, then run the canonical `venv/bin/python scripts/pdf/generate_pdf.py --scope Base2 --language de` build and the other routed-language builds. Render the resulting PDF pages with Poppler; inspect the complete nine-card panorama, page boundaries and the new r2c2 info card at print size. A command exit code alone is insufficient.
- [ ] **Step 5: Final verification.** Run `venv/bin/python -m pytest -q scripts/tests`, `venv/bin/python -m scripts.poster_assets.validate_promoted_poster --all-enabled`, `venv/bin/python -m scripts.poster_assets.poster_work_plan --all-configured`, PDF metadata/text extraction and the release candidate checks relevant to changed P02 assets. If any fail, leave P02 disabled or revert only the newly attempted route through a recoverable edit; do not alter the v9 original.
- [ ] **Step 6: Commit and push focused release files.** Report the precise PDF output(s), hashes, page/crop QA results and any unresolved licensing/publication boundary. Do not publish a release or merge a PR without a separate explicit request.
