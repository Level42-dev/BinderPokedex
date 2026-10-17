# Source-Locked Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a source-faithful ExGen3 Mega panorama with convincing ground shadows before applying the method to other rejected panoramas.

**Architecture:** Extend the existing FLUX identity-lock renderer with an explicitly selected `grounded_source_pixels` reference contract. Generate one clean landscape, composite the exact source cast, and edit only reviewed ground regions using ordinary VAE encoding plus a latent noise mask. Restore all pixels outside the RGB edit mask; do not run the former upper-context blend for this contract.

**Tech Stack:** Existing Python/Pillow/PyYAML tests, pinned ComfyUI core nodes, FLUX.2 Klein 4B BF16, existing immutable remote jobs, existing learned 300-dpi upscale.

**Spec:** Approved chat design of 12 September 2026 and `docs/reviews/2026-09-12-panorama-audit.md`, section "Grenze des bestehenden Renderers". The operator explicitly approved implementation and requested the approach's advantages and disadvantages.

## Global Constraints

- Continue in the existing `codex/v10-refresh` checkout, preserving the prior audit changes and ignored source/job caches. No new workspace or render target is needed for this continuation.
- Only the active ignored `renderer.local.yaml` controls the render target. Never print or commit private connection values or copy the marker into jobs/provenance.
- Keep existing production images/PDFs/archives unchanged until a candidate passes complete source/raw/master/nine-crop visual review. Pixel checks are not aesthetic approval.
- Initially select the new contract only for the ExGen3 Mega prototype. Existing historical reference modes remain reproducible, not automatic fallbacks.
- Every source pixel with nonzero alpha is protected from the ground edit. Every output pixel outside the approved mask must equal the pre-edit composite exactly.
- Masks are explicit ground-region polygons with reviewed contact/projection anchors and exact source identities, not automatic generic ellipses.
- The new contract includes the mask configuration/prompt and derived input hashes in provenance and requires a new pipeline version. It must not inherit approval from another graph.
- Use normal `VAEEncode`, `SetLatentNoiseMask`, reference conditioning, and `ImageCompositeMasked`; do not use neutral-filling `VAEEncodeForInpaint` in the new pass.
- Use the existing pinned models and runtime; return and verify every job's run metadata, log, and output. No promotion, publication, merge, or release without passing gates.
- TDD is required for production changes. Use `tmp/v10-artwork-audit-env/bin/python -m pytest` and keep unrelated revoked-artwork baseline failures explicit.

---

### Task 1: Explicit ground masks and exact-pixel audit

**Files:**
- Create: `scripts/poster_assets/grounding.py`
- Create: `scripts/tests/test_poster_grounding.py`

**Interfaces:**
- Consumes: the existing placement dictionaries from `composition.cutout_placements`, containing `item`, RGBA `image`, `x`, `y`, and `cell`.
- Produces: `grounding_config(manifest: dict) -> dict`; `build_grounding_masks(width: int, height: int, placements: list[dict], manifest: dict, output_dir: Path) -> dict`; `audit_grounding_pixels(reference_path: Path, baseline_path: Path, artwork_path: Path, mask_path: Path) -> dict`.
- Configuration lives at `artwork.identity_lock.grounding`: `schema_version: 1`, required nonempty `prompt`, `feather_ratio` in `[0, 0.02]`, and nonempty `regions`. Each region has `subject_key`, `contact` (`grounded` or `hover`), at least three normalized `[x,y]` polygon vertices, and nonempty normalized `anchors`. Reject unknown fields, nonfinite/bool coordinates, coordinates outside `[0,1]`, degenerate polygons, duplicate/missing/unmatched subjects, anchors outside their polygon, and masks that leave no editable ground. Region keys bind to the source's `poster_subject.subject_key` through existing subject resolution, including base sources.
- Outputs: `grounding_mask.png` (RGBA inverse-alpha RGB-composite mask), `grounding_sampling_mask.png` (RGBA inverse-alpha binary sampling mask), and `grounding_mask.json` containing normalized configuration, dimensions, mask hashes, source identities, anchor pixels and counts. All nonzero-alpha source pixels must be excluded from both masks. Reject union coverage above 12% of the canvas. For positive feather, the outermost polygon pixel has zero edit weight and weights rise inward to 255; feather must not enlarge the allowed region. A zero feather ratio explicitly requests the binary mask.
- The audit raises on dimension mismatches, mask/source overlap, changed protected pixels, or an unchanged editable region. Return `method: exact_grounding_protected_pixels`, `passed`, dimensions, SHA-256 of all four inputs, `editable_pixels`, `changed_editable_pixels`, `source_visible_pixels`, `changed_source_pixels`, `outside_mask_pixels`, and `changed_outside_mask_pixels`.

- [x] **Step 1: Write failing tests using tiny real RGBA fixtures.** Catch a removed source exclusion, outward feather, wrong mask polarity, misplaced anchor acceptance, degenerate/invalid inputs, and ignored protected-pixel changes. Derive expected pixels by hand:

```python
reference = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
reference.putpixel((50, 80), (255, 0, 0, 1))
# Polygon x40..60/y70..90; the one alpha=1 source pixel is still locked.
# After preparation, ComfyUI edit weight at (50,80) and (20,20) is zero;
# an interior transparent point has nonzero weight.
```

- [x] **Step 2: Run `tmp/v10-artwork-audit-env/bin/python -m pytest scripts/tests/test_poster_grounding.py -q`; record the expected RED failure.**
- [x] **Step 3: Implement only the declared module.** Use Pillow polygon rasterization, binary source-alpha union, inward-only feathering, and byte comparisons. The revised output mask formula is:

```python
allowed = ImageChops.multiply(polygon_union, ImageChops.invert(source_support))
feathered = polygon_union.copy()
if radius > 0:
    feathered = Image.new("L", polygon_union.size, 0)
    inner = polygon_union.copy()
    steps = max(1, math.ceil(radius))
    for step in range(1, steps + 1):
        inner = inner.filter(ImageFilter.MinFilter(3))
        level = round(255 * step / steps)
        feathered = ImageChops.lighter(feathered, inner.point(lambda p: level if p else 0))
editable = ImageChops.multiply(feathered, ImageChops.invert(source_support))
comfy_alpha = ImageChops.invert(editable)
```

The boundary test must catch the previously proposed clipped Gaussian, whose
last interior pixel retained approximately 50% edit weight and could expose a
polygon seam. Verify literal zero/monotonic intermediate/full weights on a
rectangular fixture, plus unchanged nonzero-alpha source exclusion.

After rounding, validate each anchor against its own rasterized binary region,
before union/feather/source exclusion. A normalized boundary point can fall
outside the discrete polygon. Regression fixture: 1280x720, polygon
`[[0.12,0.507],[0.779,0.46],[0.483,0.667]]`, anchor
`[0.4495,0.4835]` maps to `(575,348)`, where that polygon has no permission;
reject it rather than recording an invalid raster anchor.

After positive feathering and source exclusion, each configured region must
still contain at least one full edit-weight (255) pixel. Reject a region that
is too thin or whose full-weight core is entirely covered by source support;
a different wide region must not hide this failure. Regression: a 100x100
canvas, feather ratio 0.02 and rectangle raster x40..43/y70..90 currently
leave nonzero pixels but only a maximum of 128. Include this narrow region
alongside a second, wide valid region and still require rejection. Zero
feather remains an explicitly binary mask.

- [x] **Step 4: Run the focused tests, compile the module and run `git diff --check`.**
- [x] **Step 5: Self-review and commit only the two task files; submit the task report with RED/GREEN evidence.**

### Task 2: Versioned renderer and provenance integration

**Files:**
- Modify: `scripts/poster_assets/generation_contract.py`, `poster_config.py`, `prepare_comfyui_poster.py`, `create_comfyui_poster_workflow.py`, `run_comfyui_poster.py`, `provenance.py`, `promote_comfyui_poster.py`, `validate_promoted_poster.py`
- Modify the actual CLI reference-mode choice lists that consume the same contract, found with `rg 'two_pass_source_pixels' scripts`.
- Extend tests in `scripts/tests/test_poster_grounding.py` and relevant existing contract/fingerprint tests.

**Interfaces:**
- Consumes the three Task 1 functions and existing identity-lock source placement, model loading, scene prompt, output sizing and upscale.
- Produces explicit `flux/identity_lock/grounded_source_pixels` pipeline v4, with required generation fingerprint and hash-bound protected-pixel validation before upscale/promotion.

- [x] **Step 1: Add failing integration tests.** Verify the new graph routes the exact pre-edit composite into normal VAE encoding and final outside-mask restoration, excludes the old upper-context blend, saves exactly one final and one distinguishable baseline image, and records only consumed mask references. Mutating an anchor/prompt must change the fingerprint; rebuilding from recorded sources must agree. Historical identity-lock v1–3 and existing joint-scene contracts stay unchanged.
- [x] **Step 2: Observe RED with the focused tests.**
- [x] **Step 3: Add the new supported reference mode and pipeline v4; preserve existing canonical defaults until the visual prototype passes.** The new graph uses this flow, reusing existing base nodes and extracting a focused helper if useful:

```text
clean scene -> crop -> exact cast composite -> SaveImage(baseline)
                         | -> VAEEncode -> ReferenceLatent(grounding prompt)
                         | -> VAEEncode -> SetLatentNoiseMask -> sampler -> decode
                         +-------------------------------------> ImageCompositeMasked -> SaveImage(final)
```

The sampler sees the cast but final compositing uses only the source-excluding ground mask. Sampling remains four steps, with a separately encoded grounding prompt. No extra upper pass is generated for this mode. Extend prompt snapshots/fingerprints with the separate grounding prompt and normalized config. Validate mask metadata and input hashes; reject missing or stale evidence. A returned baseline must belong to this exact job. The normal runner recognizes the two labeled outputs, performs both source and protected-pixel audits before upscale, and records the baseline identity with validation.
- [x] **Step 4: Add fail-closed provenance checks for the new mode.** Missing validation, changed protected/source counts, wrong mask/reference/raw/baseline hashes, empty edits, and another graph's approval must not allow promotion. Reuse shared checks at runner/promotion/consumption boundaries rather than introducing parallel validators.

  The new grounded mode requires BOTH pixel audits AND the existing complete source/raw/print-artwork visual-review binding. Generalize the shared review eligibility check for the new mode rather than copying its hash/identity/criteria logic; retain historical review records and public names for compatibility. A technical pixel pass alone must not promote grounded artwork. The validator's current identity-lock prompt check must account for both the scene and grounding prompt snapshot. The baseline is a labeled generated output with its own `file_record`, not an unchecked hash string supplied by a caller.
- [x] **Step 5: Run focused renderer/contract/fingerprint tests, compile and diff checks, then task review; commit only task files.**

### Task 3: ExGen3 pilot and visual acceptance

**Files:**
- Modify only for the approved pilot: `config/posters/ExGen3/sections/mega/poster.yaml`
- Extend ignored `tmp/v10_identity_lock_trial.py` and `tmp/test_v10_identity_lock_trial.py` to pass the explicit mode, verify both returned outputs, and run protected-pixel checks before upscale.
- Correct the real-worker PNG metadata comparison in `scripts/poster_assets/provenance.py`, with regression coverage in `scripts/tests/test_poster_grounding_integration.py` as specified below.
- Record evidence: `docs/reviews/2026-09-12-exgen3-grounding-pilot.md`, `docs/POSTER_ARTWORK_EXPERIMENT_LOG.md`, and the audit status/checklist.

**Interfaces:**
- Consumes the new mode and audit functions. Reuse exact Mega Latias/Diancie/Lucario source files, immutable-job handling and frozen-input checks.
- Produces an unapproved candidate with hashes, raw image, baseline, mask, model-upscaled master, localized preview and nine crops; only a fully passing candidate may be promoted.

- [x] **Step 1: View the original sources, placement and current landscape; specify per-figure ground polygons and support/projection anchors.** Use the current upper-left daylight direction. Review rendered masks at native resolution before sending a job.
- [x] **Step 2: Test helper changes with real local fixtures and fake external transport only; verify no replay of attempted jobs, frozen-input checks, all outputs retrieved and audits before upscale.** Remote model hashes must equal the selected pinned artifacts, not merely be readable hashes of whatever is currently installed. Keep private diagnostics suppressed and never queue during the preparation-only mode. An explicit reference-mode argument must propagate through configuration, preparation, workflow and resume argument matching.

  Real-worker preflight found that pinned ComfyUI adds a top-level
  `is_changed: [<lowercase SHA-256>]` runtime cache annotation to each LoadImage
  node in saved PNG prompt metadata. The input graph itself is unchanged.
  `grounded_output_record` must compare the exact semantic workflow while
  tolerating ONLY that known annotation on an expected LoadImage node, with
  exactly one valid digest. Do not normalize inputs, unknown fields, node
  classes, role prefixes or arbitrary metadata. Do not mutate returned PNGs or
  the sealed graph. Current source/input hashes still undergo their independent
  checks. Add RED/GREEN fixtures with genuine SaveImage-style annotated prompt
  metadata; an altered input, unknown node field, invalid cache annotation, or
  annotation on a non-LoadImage node must still be rejected. This is a shared
  canonical comparison fix, not an ignored-helper bypass.
- [x] **Step 3: Reuse the active renderer marker, probe worker/models safely, prepare the immutable pilot, inspect its graph/input hashes, then execute and retrieve it.**
- [ ] **Step 4: Check source and protected pixels, then inspect raw/master/all nine physical crops against originals.** Reject new creatures, altered anatomy, floating feet, wrong-direction shadows, rectangular seams, ghost contours, halos and foreground conflicts. If needed, vary one grounded-pass factor at a time; keep unsuccessful evidence and do not promote it.
- [ ] **Step 5: Obtain independent code and visual review.** A passing ExGen3 prototype permits representative further subjects to be tested; it does not approve the other 40 failures. If the pilot remains visibly deficient, report the concrete limit without rolling it out.
- [ ] **Step 6: Update the audit checklist and documentation with verified results and outstanding scope.** Rebuild PDFs/archives only after approved replacements exist; do not publish or merge in this task.
