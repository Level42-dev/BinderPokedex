# Panorama Batch Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare as many still-open v10 panorama artworks as can be genuinely rendered and checked in one joint, source-paired user review, without adopting unapproved pixels.

**Architecture:** Reuse the established v11 spatial-plus-individual-source one-shot. Keep each trial's source-bound manifest, immutable render job, worker evidence, text-free master, localized preview, and nine physical card crops separate from production. Build one indexed review showing the complete panorama and each source/card pair, marking existing partial approvals precisely.

**Tech Stack:** Python 3, PyYAML, Pillow, FLUX.2/ComfyUI through the workspace's configured private render worker, Git.

**Spec:** [Existing artwork status](../../POSTER_ARTWORK_STATUS.md), [source-detail workflow](../../POSTER_WORKFLOW.md), [40-scope retriage](../../reviews/2026-09-14-panorama-next-steps.md), and the user's current request for one collected approval round.

## Global Constraints

- Keep `joint_scene`/`spatial_source_detail_joint`, one empty target, one sampler, one decode, and 2 MP for new source-detail attempts.
- Do not alter accepted candidate pixels, production masters, released PDFs, or production manifests merely to prepare a review trial.
- Bind each source description to its exact source image hash; check the full poster, all nine physical cards, and all source/card identity comparisons.
- The ignored `renderer.local.yaml` selects the render target; never record its private values in the repository or reports.
- A successful render is not human artwork approval; every new image remains pending until the user accepts the exact file.
- Keep Git synchronized with scoped, verified checkpoints; never stage worker configuration, source caches, render logs, or release archives.

## Review Focus

- A source image changes after preparation: the frozen job or review verification must reject it.
- A candidate includes an extra Pokémon, missing Pokémon, wrong special form, or shifted bottom-row placement: do not offer it as a passable candidate.
- An identity detail is lost while foreground vegetation is plausible: classify identity separately from depth; do not hide the identity problem behind a grass repair.
- An accepted partial image is combined with new work: preserve the exact accepted pixels and label the remaining figures unresolved until separately accepted.
- A job succeeds but omits `run.json`, `comfyui.log`, an output image, or a card crop: exclude it from the approval gallery.

---

### Task 1: Batch-safe trial preparation

**Files:**
- Create: `scripts/poster_assets/review_batch_source_detail.py`
- Create: `scripts/tests/test_review_batch_source_detail.py`
- Create: `docs/reviews/2026-09-22-panorama-source-traits.yaml`

**Interfaces:**
- Consumes: existing poster manifests, cached cutout manifests, the hash-bound 40-scope retriage, and existing v11 renderer functions.
- Produces: a trial-local `poster.yaml` for a named scope and seed, with exact source hashes and source-specific English traits; the production manifest remains byte-identical.

- [ ] **Step 1: Test safety and completeness before implementation.** Assert that a listed scope produces exactly the canonical cast keys and matching hashes; an unlisted scope, changed source, missing traits, or output path outside ignored trial space is rejected; production manifest bytes remain unchanged.
- [ ] **Step 2: Run the focused test and confirm the new behavior fails.** Run `venv/bin/python -m unittest scripts.tests.test_review_batch_source_detail -v` and retain the initial failure output.
- [ ] **Step 3: Implement only the trial-local manifest builder and exhaustive source-trait table.** Keep renderer configuration and source files out of the output.
- [ ] **Step 4: Run focused tests, validate every source binding, and commit the code/traits checkpoint.** Run the focused unit test and `venv/bin/python -m unittest scripts.tests.test_poster_source_detail -v`; commit only the listed source files.

### Task 2: Immutable one-shot render batch

**Files:**
- Create: ignored `tmp/oneshot-trials/<variant>/` directories only; do not touch `assets/posters/`.
- Create: `docs/reviews/2026-09-22-panorama-batch-evidence.json`

**Interfaces:**
- Consumes: Task 1 trial manifests, the configured worker marker, and the established immutable render transport.
- Produces: independently sealed trial jobs, complete returned worker evidence, text-free 300-dpi masters, German previews, and nine exact physical card crops per completed scope.

- [ ] **Step 1: Confirm the existing marker is complete and the selected worker reachable.** Stop before GPU work if the marker or worker check fails.
- [ ] **Step 2: Prepare and verify immutable jobs in small groups.** Reject changed sources, malformed graphs, unexpected load-image counts, or changed production masters.
- [ ] **Step 3: Execute/retrieve each group without automatic replay.** Preserve `run.json`, `comfyui.log`, every generated output, and the sealed job; a failed job is recorded as failed, not silently retried.
- [ ] **Step 4: Verify output dimensions, print sizing, every one of nine crop pixel matches, and frozen source hashes.** Record exact hashes and any failures in the evidence file.

### Task 3: Joint artwork review and checkpoint

**Files:**
- Create: `docs/reviews/2026-09-22-panorama-batch-gallery.md`
- Update: `docs/reviews/2026-09-22-panorama-batch-evidence.json`

**Interfaces:**
- Consumes: verified Task 2 candidate files and the exact previously accepted/partial candidate records.
- Produces: one clearly labeled gallery with each full panorama and source/card pair, plus a decision list distinguishing passable, retry, existing partial acceptance, and pending human approval.

- [ ] **Step 1: View every full candidate and all physical cards, then compare each Pokémon crop with the exact source.** Record anatomy, form, scale, depth, title overlay, and edge issues separately.
- [ ] **Step 2: Omit or mark failed candidates transparently.** Do not ask for approval of an unreviewed or visibly broken image.
- [ ] **Step 3: Publish one grouped approval gallery and keep the Git checkpoint current.** Commit only review documents and eligible review assets, push the branch, verify remote SHA, and provide the user one compact decision checklist.

## Self-review

The plan covers preparation, immutable rendering, full print-card/source visual review, precise partial approvals, presentation, and Git synchronization. No released PDF or production master is changed as part of asking for artwork approval. Its five review-focus conditions are each checked in Task 1, Task 2, or Task 3.
