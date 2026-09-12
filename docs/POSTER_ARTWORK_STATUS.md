# Poster Artwork Feature Status

This document records the current accepted production state. Operator commands
live in [Poster Workflow](POSTER_WORKFLOW.md), durable product requirements in
[Poster Requirements](POSTER_ARTWORK_REQUIREMENTS.md), architecture details in
[Poster Architecture](POSTER_ARTWORK_CONCEPT.md), and rejected or superseded
evidence in [Poster Experiment Log](POSTER_ARTWORK_EXPERIMENT_LOG.md).

Last audited: 2026-09-12

## Current decision

The production generator supports one model family and two generation modes.
`joint_scene` has three explicit reference topologies:

| Role | Contract | Current use |
| --- | --- | --- |
| Default | FLUX.2 `joint_scene` / avoidance-first `individual_spatial_joint` pipeline v9 | One poster-shaped identity-and-position reference per subject, invisible no-crossing character volumes, empty target, one sampler, one decode, deterministic 300-dpi Lanczos output; 38 active promotions |
| Scope-specific accepted profile | FLUX.2 `joint_scene` / `individual_spatial_joint` with `landscape_first_v1` | The two-subject Primal target uses the same references and graph, but a reviewed compact landscape-first prompt that makes the canvas hierarchy and outer silhouette extents primary; one active promotion |
| Scope-specific accepted profile | FLUX.2 `joint_scene` / `spatial_identity_joint` pipeline v7 | One shared spatial cast plus unscaled identity references; used by reviewed `SV04.5`, `ME05`, and `SV08` promotions |
| Scope-specific legacy | FLUX.2 `joint_scene` / `regional_identity_joint` pipeline v6 | One regional identity branch per physical card; retained for historical reproduction and bounded diagnostics, with no active promotion |
| Explicit fallback | FLUX.2 `identity_lock` | Two-pass scene, immutable source figures, exact opaque-pixel audit, and 300-dpi model upscale; currently no active scope uses it |

New manifests default to `individual_spatial_joint`. A manifest and provenance
describe exactly one active contract. Switching to a legacy topology or the
fallback requires a deliberate manifest change, a new candidate, explicit visual review,
and a new promotion; there is no automatic dual-active registry. New review
records explicitly identify the reviewer as `human` or `agent`; agent inspection
does not claim operator aesthetic approval.

## Generation environment

The reviewed v9 candidates were rendered on an isolated remote Apple Silicon
worker through portable, hash-pinned render jobs and returned for local visual
review and promotion. The worker hostname, address, credentials, and concrete
paths are intentionally not tracked. Future generation is not tied to that
machine: the operator explicitly chooses local Apple MPS or the generic remote
worker path documented in
[Remote Poster Render Worker](POSTER_RENDER_WORKER.md). That path now builds a
disposable native runtime from checksum-pinned archives and hash-locked Python
dependencies. The runtime owns Python, ComfyUI, and tools; an independently
managed external cache owns model weights. Packaging preserves the cache as a
symbolic link, and validated destruction removes only the runtime.

The reviewed rollout now uses the unquantized BF16 FLUX.2 Klein 4B checkpoint
for all current promotions. The v10 ME05/SV08 comparison also tested 9B and
2-MP rendering; neither became a production dependency. Native Klein 4B/9B,
Base 4B, corrected Kontext
BF16, the earlier Dev 32B candidate, 2-MP spatial references, and an abstract
box guide remain experiment evidence rather than competing active contracts.

Anima, FLUX.1 Canny, FLUX.1 Kontext, Qwen Edit/spatial, SDXL regional identity,
DreamO, direct FLUX edit, and direct inpaint remain rejected for this feature.
Their evidence is retained in the experiment log and Git history, not the
production runner.

An isolated FLUX.2 Klein 4B paired edit-LoRA experiment is now in its dataset
phase. Its versioned contract and audit tool do not add a production mode. The
first inventory found fourteen promoted raw targets and eighteen historical
`identity_lock` inputs: four inputs are blank, thirteen nonblank inputs no
longer match the current exact-source placement/pixel contract, and the one
historically exact input belongs to the deliberately excluded ExGen2 Normal
target. A fresh Generation I MPS/BF16 identity-lock render passes all 62,563
opaque source pixels. A bounded full-composite FLUX.2 teacher pass keeps the
scene geometry and card placement substantially aligned and adds common contact
shadows, but its raw character repaint still changes small anatomy. Restoring
the canonical positioned RGBA subjects produces zero changed opaque source
pixels, but human card-crop review rejects Generation I and the original Base
Set scene as well as
two bounded Generation-VII seeds: grass or leaves rooted in the foreground run
behind one or more restored subjects. Exact pixels prove anatomy and placement,
not depth. There are therefore zero surviving pair candidates from the original
scope scenes and no training checkpoint. One training-only Base Set
augmentation on a natural sand beach is the first human-approved gold holdout:
its
surface has no upright occluder, all 52,343 opaque source pixels remain exact,
and the teacher adds shared directional shadows. Three further clear-surface
gold train pairs use Generation II on snow, Generation III on black sand, and
Generation IV on pale stone; the user approved all three complete targets and
their physical card crops on 2026-08-05. A fourth gold train pair places the
Generation-V cast on a natural red-clay badlands floor; its complete target and
card crops were approved the same day. A sterile
smooth-earth control and the first wall-like Generation-IV stone background are
rejected. The simple recipe is
restricted to genuinely clean avoidance or entirely behind-subject landscape;
foreground crossings need an explicit reviewed foreground layer. See
[Poster Artwork Integration LoRA](POSTER_ARTWORK_TRAINING.md).

## Promoted scope state

All 42 bundles are promoted and enabled. Thirty-eight use the reviewed
avoidance-first individual-spatial v9 contract, `ExGen2/sections/primal` uses
the accepted landscape-first individual-spatial profile, and `SV04.5`, `ME05`,
and `SV08` deliberately use their reviewed mask-free spatial-identity v7
contracts. Every
bundle is 2368 x 3268 px, is sliced into nine physical cards, carries effective
299.99-dpi PNG metadata, and binds its approval to the exact raw and print
pixels plus the exact Official Artwork identities.

`ExGen1/sections/normal` is active with the reviewed Venusaur, Blastoise, and
Lugia replacement cast. `SV04.5` is active with Charmander, Pikachu, and
Lapras in one continuous moonlit scene. `ExGen2/sections/primal` is active with
the accepted small outer-bottom Kyogre/Groudon composition and continuous
coastal-basin landscape. The tiny lower-right grass-blade anomaly is an
explicitly accepted residual for these exact reviewed pixels, not a relaxed
general depth requirement.

Stable `poster-flux2*` filenames keep PDF routing unchanged. Logos, localized
information panels, card slicing, and PDF placement remain deterministic and
are not model-generated.

The v10 agent-reviewed replacements are `SV07` (two-ear Hopplo), `ME05`
(Robball, Morpeko, Marshadow), and `SV08` (Ho-Oh, Krokel, Pikachu). SV08 uses
the existing poster-only slot selection for Pikachu `sv08-057`; Black Kyurem
`sv08-048` remains unchanged in the card data. Full raw/master and all nine
physical crops were inspected before promotion. Their provenance records
agent inspection, not a new human approval.

## Configured target and language coverage

Every current target has a checked-in manifest and a configured creative brief.
Unreviewed targets remain disabled, so configuration coverage never implies
visual approval.

| Scope family | Configured | Promoted and enabled | Disabled / awaiting activation |
| --- | ---: | ---: | ---: |
| Individual TCG sets | 27 | 27 | 0 |
| Pokédex generations | 9 | 9 | 0 |
| ExGen1 sections | 1 | 1 | 0 |
| ExGen2 sections | 3 | 3 | 0 |
| ExGen3 sections | 2 | 2 | 0 |
| **Total** | **42** | **42** | **0** |

Every configured target now has one reviewed promotion. Rejected candidates
remain experiment evidence and never enter PDF routing.

The deterministic overlay contract is complete for all 267 language outputs
currently implied by those targets. Aggregate sections contain title,
subtitle/region, Pokémon count, and description/range in all nine PDF languages.
Individual TCG sets define localized set copy and logo routes for every
language advertised by their fetched source data. Missing TCG languages are
not invented and are not PDF targets.

Scope JSON is the only semantic copy source for both covers and posters.
Poster manifests no longer copy titles or select title/deduplication styles.
The overlay infers complete logo, inline token logo, or text rendering and
draws plain text directly without a title panel. It removes an identical title
row automatically. Cover count labels use the scope
type, so TCG-set totals are cards while Pokédex and variant totals are Pokémon.
Both panorama counts and card pages use the same per-card language filter.
Unnumbered cards count as one insert, and cards available only in other
languages do not inflate a localized information panel.

The poster contains all semantic cover information: collection/set title,
section title where applicable, subtitle/region, collection count, description
or release date, representative Pokémon, and the `Binder Pokedex` project mark.
It therefore replaces the ordinary cover whenever an enabled promotion exists.
The cover's build-time footer (cutting hint and build date) is operational
metadata and remains available only on fallback and `--skip-poster` builds.

## Accepted default graph

For each subject, `individual_spatial_joint`:

1. derives the final silhouette bounds, scale, baseline, and padding from the
   same physical layout used for slicing;
2. writes one neutral poster-shaped reference containing only that subject at
   its final position;
3. describes those named reference roles and exact normalized bounds in the
   central prompt;
4. starts from one empty FLUX.2 latent;
5. synthesizes landscape and all subjects together through one sampler and one
   decode;
6. performs no character composite, restoration, movement, inpaint repair, or
   learned upscale after decode;
7. resamples the reviewed text-free result deterministically to the exact
   300-dpi print raster;
8. adds localized logo and information only in deterministic post-processing.

Explicit visual review remains mandatory because generated identity cannot be proven by
pixel equality. Review covers exact cast count and form, anatomy, face,
markings, silhouette, pose, card fit, padding, grounding, shadows, coherent
depth, safe text cells, and every physical card crop.

New candidates use avoidance-first pipeline v9. Every known character bound
plus its two-percent clearance is an invisible no-crossing volume for
camera-near scenery. The same low ground plane and subtle ground texture
continue beneath the characters, while tall grass, leaves, flowers, branches,
rocks, and water edges are composed outside those volumes or clearly behind
them. The volumes must not become visible clearings, halos, platforms, paths,
or character-shaped gaps. An accidental intersection still fails if an object
terminates at a silhouette or switches depth along its visible length.

## Deferred depth guide

The minimal explicit depth/occlusion guide remains deliberately inactive. It
may be tested only when a bounded normal candidate achieves neither clean
separation nor coherent overlap. Any such test must retain the three positioned
identity references, one empty target, one sampler, and one decode, and may add
only coarse `near`, `subject`, and `far` ownership. It must not contain scene
texture, character pixels, or a post-decode composite.

## PDF, aggregate, and CI boundaries

- Fetching and PDF generation never start ComfyUI.
- Local generation is an optional post-fetch, pre-PDF phase.
- Only promoted, tracked artwork can enter a normal PDF.
- `--skip-poster` remains an explicit build bypass.
- A disabled or absent poster route leaves the existing section cover and card
  pages intact for diagnostics; the all-section regression test rejects such
  a route for any normal release target.
- Enabled A4 posters default to nine physical cards; `--poster-page-mode
  full-page` emits the same localized poster once at 200.5 × 276.7 mm, centered
  on A4 without cutting guides.
- Aggregate scopes route independent section manifests and promotions through
  `posters.yaml`, then replace each matching section cover with its poster.
- All 42 current individual and aggregate targets are configured, promoted,
  enabled, and provenance-validated.
- Full release verification (manual runs, release/hotfix branches, or pull
  requests labeled `full-release-check`) validates every enabled promotion and
  builds a complete release candidate as a temporary artifact only. Ordinary
  pull-request checks exercise the scoped notice/PDF/packaging tests; they do
  not imply a complete release build.
- Only a successful `v*` tag job may publish a GitHub Release.

## Remaining work

1. Keep representative multilingual PDF QA current across the 42 enabled promotions.
2. Keep `wide_4x3` and `wide_4x4` modeled but disabled for PDF production until
   matching physical page formats, memory tests, and visual QA exist.

## Cleanup boundary

Downloaded cutouts and set logos, generated references, workflows, candidates,
run metadata, PDF smoke tests, localized previews, card slices, and rendered QA
pages are ignored local scratch. Only promoted masters and their provenance are
versioned as poster raster assets. Rejected implementations remain only in Git
history and the experiment log. Production tests call the canonical workflow
builders directly; retired experiment entry points are not retained.

## Verification

The branch gate is:

```bash
python -m pytest scripts/tests -q
python -m scripts.poster_assets.validate_promoted_poster --all-enabled
python -m scripts.poster_assets.poster_work_plan --all-configured
```

Core branch verification rerun on 2026-09-12:

- the complete project suite passes with `733 passed, 1 skipped`;
- all 42 enabled poster bundles validate at 2368 x 3268 px and effective 300 dpi;
- all 31 release scopes / 42 section routes require a real panorama;
- all 267 target/language information-panel counts match their card-page selection;
- all 27 TCG overlay fingerprints are current; all 42 master files and their
  generation/review records are unchanged by the localized-count correction;
- the work planner uses the same slot-aware subject selection as generation;
- ME05/SV08 raw masters, print masters, all nine crops, and freshly rendered
  German PDF opening pages pass agent visual review;
- ME05, SV07, and SV08 record agent review, while existing human records remain
  valid and are not rewritten;
- the 63-file data snapshot remains unchanged and verifies at 2026-09-12;
- Python compilation, whitespace checks, and independent code review pass.

The final local v10.0 candidate was rebuilt from source commit
`48f82439bf7aa1272fe7d877ebb25919287c4d93`: 168 PDFs / 4,781 pages in nine
languages, including 31 German PDFs / 807 pages. Every PDF's version and source
notice were checked. All nine language archives pass the canonical integrity
verifier and an independent byte-for-byte PDF, license, and source-commit check.

Final Poppler review covers the reported SV04/SV05 overflow pages, German
SV09 ownership labels, both German SV10.5 logos, SV07 Hopplo, SVP numbers and
the unnumbered card, MEP numbers 064/079, and the ME05/SV08 panorama openings.
The corrected raster information panels show SVP/de 217, MEP/de 88, and
SV10/ja 132. Thirty previously reviewed comparison pages are pixel-identical;
only the two German promo opener counts changed, with the Japanese opener
added to this check. This is targeted visual QA plus complete programmatic
artifact verification, not a claim that all 4,781 pages received manual review.

PR #17 contains the implementation and candidate metadata. External PR approval
remains a separate gate; no merge, tag, or GitHub Release was performed.

Historical branch verification on 2026-08-12:

- the project suite passes with `568 passed, 1 skipped`;
- all 41 enabled poster bundles validate;
- all 41 promotions also validate from an empty poster-source cache, using
  their audited provenance rather than repository copies of downloaded
  cutouts;
- the planner reports all 41 configured targets as current and PDF-enabled;
- a fresh German ExGen2 build with remote card images disabled succeeds with
  127 entries and 19 pages;
- rendered page 18 confirms that the localized nine-card Primal poster now
  replaces the section cover and keeps both Primal forms inside their outer
  bottom cards;
- Python compilation and `git diff --check` pass.

The following production and visual checks remain current from 2026-08-03:

- every v7 production graph matches its reviewed candidate graph except for
  the output filename prefix;
- a full German Pokédex PDF plus Japanese Pokédex and German ExGen3 smoke PDFs
  build successfully with posters enabled;
- fresh German Base1, Pokédex, and ExGen3 smoke PDFs confirm the shared title,
  count-unit, description, and poster-insertion data flow;
- fresh German ExGen1 and `SV04.5` PDFs confirm the two replacement promotions,
  localized overlays, poster-first order, and first card page;
- rendered poster pages preserve the 3x3 card grid, overlays, card containment,
  and full-bleed scene continuity;
- rendered Base1 smoke PDFs verify both the default cuttable page and the
  continuous full-page presentation; an explicit `--skip-poster` smoke verifies
  the unchanged cover fallback independently of a scope's normal poster route.
