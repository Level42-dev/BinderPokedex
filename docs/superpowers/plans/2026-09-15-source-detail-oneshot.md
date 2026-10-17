# Source-detail One-Shot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development for the renderer implementation and its task review. Preserve the user's P01 image-review checkpoint.

**Goal:** Integrate the accepted spatial-layout plus individual-detail one-shot recipe, review P01, then execute the agreed P15/P40 transfer pilots without changing existing masters.

**Architecture:** Add a versioned, opt-in joint-scene reference contract to the existing ComfyUI renderer. Reuse the shared spatial reference and individual identity references and existing deterministic print pipeline. Historical contracts retain their exact behavior.

**Tech Stack:** Python, Pillow, pytest, FLUX.2 Klein 4B, existing immutable remote ComfyUI jobs.

**Spec:** `docs/reviews/2026-09-14-panorama-next-steps.md`, approved by the user on 2026-09-15. P01 Hopplo, P15 Mega-Latios and P40 Miraidon are explicitly mandatory regeneration targets.

## Global Constraints

- One shared spatial-layout reference plus one separate exact individual detail reference per subject; one empty target, one sampler, one decode. No post-decode subject paste, learned upscale, mask or restore stage.
- Actual generation target: 2 MP; standard_3x3 is 1200 x 1664. Deterministic Lanczos to 300 dpi; standard_3x3 master is 2368 x 3268 and nine physical cards are 750 x 1050.
- Exact subject count, correct special form, source-specific visual details and layout-derived positions take precedence. Plausible scene-appropriate foreground overlaps are allowed and desired, not forbidden by an avoidance paragraph.
- Historical generation contracts, provenance and user image approvals must not be rewritten or relabeled. Existing masters, PDFs and release archives remain unchanged. No commits, pushes or promotion in this task.
- Reuse the active ignored renderer marker. Never print private connection data or transfer it into jobs/provenance.
- Produce P01 first, inspect raw image, full master and all nine cards, then show all three card/source pairs before rendering P15 or P40.

## File responsibilities

- `scripts/poster_assets/generation_contract.py`: opt-in mode and fail-closed generation requirements.
- `scripts/poster_assets/source_detail.py` (new): strict exact-source trait binding and concise source-detail prompt construction; keep this separate from the already large configuration module.
- Existing prepare/workflow/runner/provenance modules: route the new mode through shared layout/detail preparation and single-pass graph, snapshot/fingerprint exact prompt and source traits, validate outputs and promotion gates.
- `scripts/tests/test_poster_source_detail.py` (new): behavioral tests of new graph, prompt, source binding and legacy compatibility. Existing poster test modules supply regression coverage.
- `docs/POSTER_WORKFLOW.md`: small additive documentation preserving existing edits.
- Pilot configuration is activated only after the controller supplies inspected source descriptions. No bulk migration or default initializer switch before pilot review.

### Task 1: Versioned source-detail renderer contract

**Interfaces:** Add reference mode `spatial_source_detail_joint` for `flux/joint_scene`, pipeline contract version `10`. Keep all existing modes and their historical fingerprint results unchanged. `artwork.source_details` maps each exact canonical subject key (for example `pokeapi:official-artwork:813`) to `{sha256: <source PNG digest>, traits: <non-empty English description>}`. Validate exact cast key coverage and each actual cutout file digest before reference preparation/workflow building. Bind traits to special-form artwork IDs, not just species IDs. No trait guessing or network/API dependency.

**Files:** Create `source_detail.py` and `test_poster_source_detail.py`; modify the existing generation contract, prepare, workflow, runner and provenance integration where required. Do not modify pilot manifests yet. Extend the existing workflow documentation with a manifest example.

- [x] Step 1: Run focused baseline tests using `tmp/v10-artwork-audit-env/bin/python -m pytest scripts/tests/test_poster_assets.py scripts/tests/test_poster_fingerprints.py scripts/tests/test_render_job.py -q`; record pre-existing failures separately.
- [x] Step 2: Add failing real-output tests for the new mode: three subjects yield four LoadImage nodes; two special-form subjects yield three; exactly one EmptyFlux2LatentImage, SamplerCustomAdvanced, VAEDecode and SaveImage; no Composite/Mask/Upscale nodes; expected 2-MP raster and four steps. Assert exact source traits appear only with the correct reference role and count/layout comes first. Missing/extra/duplicate keys, empty traits, bad hash and actual-source mismatch fail closed. Reject incompatible output method and wrong fixed resolution/steps. Record expected RED output.
- [x] Step 3: Implement the new source-detail module and route the mode through the existing shared spatial-plus-detail reference builder. Build a concise count/layout-priority prompt followed by exact per-source features, configured scene description and physically consistent foreground-depth rules. Derive positions and upper subject-free area from existing layout placements; never hardcode three subjects or a specific set. Preserve the old prompt builders unchanged for legacy modes.
- [x] Step 4: Integrate snapshots, generation metadata/fingerprints, input records, output selection and provenance validation. Both changed traits and changed sources must invalidate the new generation fingerprint and any old visual approval; existing historical fingerprints must stay reproducible. New runs must use the canonical graph and prompt, not an experimental override or a copied prototype graph.
- [x] Step 5: Run new tests GREEN, then relevant poster regression tests. Include tests with real preparation and graph generation, source mutation, trait mutation and legacy prompt/contract fixtures. Do not assert implementation source text or duplicate algorithms as the oracle. Document commands, outputs, changed files and concerns in the task report. Do not render or commit. Controller supplies independent task review.

### Task 2: P01 pilot and user review checkpoint

**Interfaces:** Consume Task 1's canonical mode and exact `artwork.source_details` mapping. Retain configured SV07 scene and use newly inspected Bulbasaur, Squirtle and Scorbunny source images. Freeze source/manifest/config/code/workflow hashes in an immutable local job before submission.

- [x] Inspect exact local sources, describe observed features (not guessed anatomy), activate only SV07 with the new mode, 2 MP and a recorded seed.
- [x] Reuse active workspace marker and verified worker/model pins; generate through canonical builder, seal and execute one immutable job. Retrieve all run metadata, logs and image outputs.
- [x] Verify returned seals, output dimensions, raw image, deterministic 300-dpi raster, all nine pixel-exact physical crops and unchanged production master hashes.
- [x] Review actual source/card pairs and full artwork. No automatic acceptance based on successful rendering or numerical tests. If a hard visual failure occurs, document it; at most three materially different attempts per recurring gate.
- [x] Prepare full P01 artwork and all three source/card pairs for the agreed user checkpoint. Keep P15 and P40 queued. No promotion or release claim.
- [x] Obtain the user's P01 identity/composition feedback before further generation. The user accepted the shown figures/composition; the previously reserved ground-shadow correction remains open before technical promotion.

### Task 3: Scoped transport adapter for P15 and P40

**Files:** Create ignored `tmp/v10_source_detail_transfer.py` and `tmp/test_v10_source_detail_transfer.py`. Do not edit production renderer modules, historical helper files, manifests, images, sealed trials or other tests in this task.

**Interfaces:** Reuse the canonical builder/prepare/fingerprint/sidecar/finalization APIs and immutable transport/sealing functions already used in `tmp/v10_sv07_source_detail_pilot_b.py`. Add a narrow CLI accepting exactly `--scope ExGen2/sections/mega` or `--scope ExGen3/sections/normal`, a safe `--variant` basename, and action `prepare|execute|retrieve|verify`. Root controls manifest activation, source traits and real render submission. The adapter must freeze the selected bundle's scope data (`ExGen2.json` or `ExGen3.json`), not SV07 data. Every other one-shot/sealing invariant remains the same.

- [x] Step 1: Write failing behavior tests before implementation. They must catch the hardcoded SV07-data error, reject unsupported scopes and unsafe variant path traversal, reject a state with mismatched scope/variant, and reject overwrite of an existing trial. Test real path/input-record results with filesystem fixtures; do not assert helper source text. No real worker access in tests.
- [x] Step 2: Implement the narrow adapter with `prepare`, `execute`, `retrieve` and `verify` actions. Keep a single canonical render graph and current source-detail prompt; no prompt override, alternate topology, new generation mode, manifest edits or model downloads. Retain four references, 2 MP, four steps, 300-dpi Lanczos, complete nine-card evidence, complete job retrieval and no automatic replay. Freeze the selected scope data, exact manifest/sources, renderer code and adapter/helper dependencies; resolve paths from the selected bundle. Sanitize private exception output as in the pilot. Earlier helpers are immutable historical evidence, so do not refactor them.
- [x] Step 3: Run `tmp/v10-artwork-audit-env/bin/python -m pytest tmp/test_v10_source_detail_transfer.py scripts/tests/test_poster_source_detail.py scripts/tests/test_render_job.py -q` and CLI help. Record RED/GREEN, files, test output and any limitations. No real preparation/render, commits or subagents. Controller performs independent scoped review before using the adapter.

### Task 4: P15 and P40 source-detail transfer pilots

**Files:** Activate only `config/posters/ExGen2/sections/mega/poster.yaml` and `config/posters/ExGen3/sections/normal/poster.yaml`; create ignored immutable trials `tmp/oneshot-trials/p15-source-detail-20260915-a` and `tmp/oneshot-trials/p40-source-detail-20260915-a`, plus hash-bound review records and a compact all-six-source-pairs review document.

**Interfaces:** Use the source notes in `docs/reviews/2026-09-15-p15-p40-source-notes.md`, visually checked again against each exact original PNG. Use current source-detail pipeline 11, 2 MP, original per-scope scene/model pins/seed, and complete `artwork.source_details` entries. No P01-style size exception transfers to these new files.

- [x] Reverify and record the user's exact P01-B identity/composition approval, without mutating sealed creation-time evidence or treating the reserved shadow issue as fixed.
- [x] Inspect all six exact source images; derive per-source English traits and bind their hashes in the two manifests. Keep existing landscapes and special-form selection. Run fail-closed source-map validation before preparing either job.
- [x] Resolve the active owner-only marker and probe the configured worker/model availability without printing private values. If unreachable, do not select a different worker from history; report the missing choice. No runtime/model bootstrap or cleanup of a pre-existing shared runtime in this bounded continuation.
- [x] Prepare each isolated job through the reviewed adapter. View each shared position reference and all individual references; verify actual model pins, seed, prompt, reference hashes and source IDs before one serial submission per scope.
- [x] Complete controlled second attempts after A findings: P15-B corrects only the source wording for the single Mewtwo tail and Latios's small root-wing mark; P40-B adds only a final scene-layout reminder covering complete appendages. Keep seeds/references/model pins/graph unchanged and preserve A manifests and sealed evidence. Reinspect full outputs and all physical cards; no automatic third attempt or multistage fallback.
- [x] Retrieve all jobs/logs/outputs, verify seals, dimensions, physical crop pixels/DPI and unchanged installed masters. Inspect each raw image, full master, German preview, all nine cards and all sources; obtain an independent visual comparison for the most identity-sensitive details. Any hard failure is documented; at most three materially distinct attempts per recurring gate, with no automatic fallback.
- [x] Present both outcomes honestly and all six actual card/source pairs. No automatic promotion, PDF/ZIP rebuild, whole-batch generation, commit or push. Each new image requires its own user decision.

**Checkpoint:** The six-pair document is delivered for review (panel opening queued).
The user's exact P15-B/P40-B decisions are still pending; this checked
presentation task does not mean image approval or release completion.

### Follow-up: P15 Rayquaza clearance only

User decision after Task 4: P40-B and all shown P15 identities/composition are
accepted, except P15 Rayquaza needs more space around it. Record acceptance
against the exact B images; no whole-release or changed-pixel approval.

- [x] Reverify both B evidence sets, record scoped user decisions and retain an exact B manifest snapshot before changing P15.
- [x] Reuse the complete owner-only active workspace marker after a fresh read-only worker/model check.
- [x] Add only a Rayquaza full-silhouette clearance reminder to P15's scene constraints. No production renderer/code, seed, model, source PNG or reference changes.
- [x] Prepare one immutable P15-C, compare the consumed prompt/graph/references against B and inspect its four references before submission.
- [x] Run once, retrieve all evidence and verify the full master plus all nine physical cards, especially Rayquaza's surroundings and unchanged identities of Mewtwo X/Latios.
- [x] Present C with actual card/source comparisons; reject it if clearance still fails. No fourth attempt, automatic fallback, P40 re-render or promotion.

C result: requested left clearance still fails. Interior teal body pixels
start at x10 in both B and C, not the requested 60 px; outlines/glow extend
farther. Root inspected raw/master/preview/all nine cards and all three sources.
Canonical C verify passed before restoring the exact B active manifest.
The complete C job, image and exact C manifest snapshot remain archived.
All original approvals and production masters are unchanged.

### Follow-up D: approved spatial-reference size adjustment

The user's "versuch's bitte weiter" approves the proposed 15–20% smaller
Rayquaza position reference. Start with factor 0.8, retain all exact original
detail references and the canonical one-shot, original seed/scene/model pins.
This explicitly authorized different approach supersedes C's no-fourth-trial
checkpoint; it does not authorize a prompt-only loop or automatic fallback.

- [x] Add opt-in exact-subject shrink factors test-first; preserve visible center/baseline, unchanged neighbors and original detail references.
- [x] Bind the override in both fresh and source-less reconstructed fingerprints, including exact special forms; retain default/historical byte compatibility.
- [x] Complete scoped independent review and prepare one immutable P15-D after checking all four references.
- [x] Render once, retrieve all outputs/logs, inspect full poster/all nine physical cards/all three originals and quantify Rayquaza clearance.
- [x] Prepare D's review with actual card/source pairs for its own user decision. Keep P40, installed masters, PDFs and archives untouched; no promotion or Git publication.

D result: user-review candidate, not release-ready. Left/right interior-color
margin proxy improves 10/14 to 73/39 px, with no definite new identity blocker
in root and independent review. The 60 px right-side aim and configured smaller
silhouette bounds are not fully achieved; disclose these, do not convert them
to a pass. Complete D, all three source pairs and a small feedback checklist are
in `docs/reviews/2026-09-15-p15-scale-review.md`. Subsequent user response
"Passt prima!" accepts the shown D Rayquaza clearance; that correction point
is resolved and hash-bound in the D report. No E, fallback, P40 re-render or
promotion was performed. Production adoption and release checks remain separate.

Next decision requested: introduce a narrowly scoped per-subject spatial
reference scale for Rayquaza, about 15–20% smaller, while retaining all exact
detail sources and the same one-shot approach. No implementation or fourth
generation starts before that approach decision. C itself is not submitted
for approval because it fails the user's requested correction.

## Execution result — 2026-09-15

**Later continuation, 2026-09-22:** Exact P15-D and P40-B were adopted after a
fresh complete agent review, retaining all historical feedback and numerical
layout findings below. Both production validators pass; two panorama-only
German proof PDFs (cut cards / continuous art, plus project notices) are
verified, not complete set or release builds. P15 is current in the planner;
P40's additional constraint triggers a separately diagnosed planner list
comparison warning, whose small proposed correction awaits design approval.
SV07's shadow, older experimental imports and remaining panoramas are still
open. See `docs/reviews/2026-09-22-approved-artwork-production.md` for exact
scope, proof hashes and the refreshed next three-target review queue. The
following paragraphs retain the historical 15 September checkpoint.

Task 1 is implemented and independently reviewed. Pipeline 10 was delivered first; feedback from failed pilot A led to a separately versioned count/layout-only revision 11, retaining exact v10 reconstruction. Root covering verification: 356 passes and the same three pre-existing revoked/stale-approval failures; 27 new focused tests pass.

Task 2 produced A (rejected) and B (held for disclosed feedback, not release-ready). Both retained full immutable jobs and all output evidence. Root and independent reviewer inspected B raw, master, German preview, all nine physical cards and exact sources. B contains exactly three source-close figures fully inside their cards, but Scorbunny/Squirtle exceed the configured smaller silhouette bounds and Scorbunny has a narrow leftward shadow inconsistency. No local repaint or third attempt was made. See `docs/reviews/2026-09-15-sv07-source-detail-review.md` and its hash-bound B JSON report. All 42 installed masters are unchanged. P15 and P40 are mandatory next targets after the user checkpoint; their source notes are prepared, no renders performed.

Subsequent continuation: the user accepted P01-B's disclosed identity and
composition, including figure scale; the reserved shadow correction remains
open. Task 3's bounded transfer adapter is implemented, independently reviewed
and corrected to fail closed on missing or modified review evidence. The
covering adapter/source-detail/render-job suite has 60 passing tests.

Task 4 produced immutable A/B pairs for P15 and P40. P15-B corrects the one-tail
constraint and the initially wrong Latios marking description. P40-B only adds
a complete-silhouette layout reminder. Exact A manifest snapshots, original
source bytes, four reference hashes, seeds and model pins are preserved.
All jobs, logs and output images were retrieved. Both B canonical verifiers
pass. Every raw/master/preview, all nine cards and all exact source images were
viewed by root and an independent reviewer.

Neither B passes the configured small-cast layout. P15-B resolves the duplicate
tail and extra wing-mark failures but Rayquaza has narrow left clearance.
P40-B places both visible lightning tips inside the physical card with narrow
top clearance; the cast remains larger/higher and the building central.
The original P40-A assertion that both lightning tips were definitely clipped
was qualified after targeted reinspection. Both B images are for disclosed,
image-specific identity/composition feedback only. The full six-pair review is
`docs/reviews/2026-09-15-p15-p40-source-detail-review.md`.
No third generation, fallback, production promotion, release rebuild, commit
or push. All 42 installed masters remain unchanged. The next gate is the user's
decision on these exact B files; P01's size acceptance does not transfer.
