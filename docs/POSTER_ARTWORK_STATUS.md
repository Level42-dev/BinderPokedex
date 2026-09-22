# Poster Artwork Feature Status

This document records the installed artwork and its current review state. Operator commands
live in [Poster Workflow](POSTER_WORKFLOW.md), durable product requirements in
[Poster Requirements](POSTER_ARTWORK_REQUIREMENTS.md), architecture details in
[Poster Architecture](POSTER_ARTWORK_CONCEPT.md), and rejected or superseded
evidence in [Poster Experiment Log](POSTER_ARTWORK_EXPERIMENT_LOG.md).

Installed-artwork audit reopened: 2026-09-12. Full target retriage: 2026-09-14.
Latest scoped production update: 2026-09-22 (accepted P15-D, P40-B, P10-C and P04-B).
Latest human shortlist feedback: 2026-09-22 (P03/P27, corrected P10-C and P04-B accepted).
Latest continuation: 2026-09-22 (P04-B adopted with checked print proofs; development checkpoint and separate review-master archive prepared).

## Current decision

**Artwork release gate reopened on 2026-09-12.** The full source-by-source
re-audit found concrete anatomy or scene-boundary defects in the installed
panoramas, including ExGen3 Mega Lucario and the previously reviewed SV07.
The earlier blanket promotion flags are not sufficient evidence of source
fidelity. The detailed, hash-bound reports are in
[`docs/reviews`](reviews/); they supersede the older visual-pass claims below.
Bounded correction candidates were generated and individually reviewed. The
historical identity-lock path preserves anatomy but cannot create subject-aware
ground shadows. The subsequent source-locked shadow renderer was implemented;
both ExGen3 pilots passed pixel protection but failed scene review. On 14
September the operator reaffirmed one-shot as the preferred approach, with
multi-stage generation reserved as a justified last resort. Scene-appropriate
foreground occlusion is explicitly desired and does not itself count as an
appearance change. A bounded, source-specific ExGen3 one-shot comparison is
recorded in [the restart review](reviews/2026-09-14-exgen3-oneshot-restart.md).
The operator visually accepted candidate C on 14 September, explicitly
accepting its small missing black eye/pupil detail and other minor deviations.
This acceptance is bound to the exact candidate master in
[its review record](reviews/2026-09-14-exgen3-oneshot-c.json); it is not a
general anatomy exception. The first-example user-review gate is satisfied.
Source-detail prompt integration is now implemented as an opt-in versioned
contract, as described in the 15 September pilot below. Technical promotion of
the earlier ExGen3 Mega C and Base1 B experiments remains pending. P15-D and
P40-B were adopted separately on 22 September as detailed below. Existing release PDFs and ZIPs are
retained as unapproved candidates, not sale-ready artwork.
No replacement is accepted merely because its render or pixel audit succeeds.

The operator then requested a Base1 transfer test focused on lower-left Mewtwo.
Of two controlled one-shot trials, A was rejected for an extra Bulbasaur in
the middle landscape; B changes only the leading count/placement instruction
and is a close-source comparison candidate with all nine cards inspected.
Its remaining fine-detail differences and the unchanged English title-logo
subtitle in the German preview are recorded in
[the Base1 review](reviews/2026-09-14-base1-oneshot.md). The operator subsequently
visually accepted B on 14 September, independently of ExGen3 C. Both exact
candidate masters now have scoped human acceptance; neither is technically
promoted. The installed Base1 artwork and release files remain unchanged.

### P04-B accepted and adopted (2026-09-22)

P04 (`Pokedex/sections/gen1`) has two new canonical v11 source-detail one-shots.
The targeted pale Charmander tail underside is restored. A is rejected for a
fourth visible Bulbasaur claw. B changes only Bulbasaur's inspected trait text,
with byte-identical references and unchanged seed/models/scene description.
B has three outer claw forms, with a rounded middle tip and extra inner line
explicitly disclosed for user judgment. No exact-source or numeric-layout
pass is invented. Every raw/master/preview and all nine cards per variant were
inspected; B's canonical verifier and 119 focused tests passed before user
acceptance. All 42 installed masters were unchanged during those P04 trials;
the later scoped adoption is recorded below. No release build was performed.

The operator subsequently accepted the exact B scene and all three shown
source/card comparisons with “sieht alles super aus!”. The disclosed middle
claw inner contour and other minor differences are accepted for these exact
pixels only. All 33 hash bindings in the original agent report were rechecked;
that historical report remains unchanged. This does not imply a numeric-layout
pass, a user inspection of every physical crop or approval of any full release.
The exact B master is now installed through the normal promotion command with
an agent technical review, separate from the human decision. Master, German
preview and all nine physical cards match the accepted candidate pixel-for-pixel;
the other 41 installed masters are unchanged. Both German panorama-only proof
PDFs passed embedded-pixel, A4/placement and all-four-page visual checks. These
are not full Pokédex or release builds.

[Exact P04-B user acceptance](reviews/2026-09-22-p04-b-user-acceptance.json) and
[production evidence](reviews/2026-09-22-p04-b-production.json).

[P04-B full scene, all source pairs and enlarged claw detail](reviews/2026-09-22-p04-source-detail-review.md).

### Git preservation checkpoint (2026-09-22)

The accumulated source-detail code, tests, decisions and installed masters are
preserved in checkpoint `82b23a9` on `codex/v10-refresh`, pushed to the existing
GitHub repository. The full test directory remains 828 passed, 3 failed,
1 skipped before and after P04 adoption; the three pre-existing global tests
still encounter revoked historical approvals. See the
[explicit test boundaries](reviews/2026-09-22-git-checkpoint-verification.md).

The exact previously accepted/partly accepted Base1-B, ExGen3 Mega-C, P02-E and
SV07-B text-free masters are additionally preserved in
[the review-only archive](../assets/reviewed-candidates/README.md). No production
routing or acceptance scope changes follow from that backup. Downloaded source
images, private renderer state and complete temporary render jobs remain excluded.

### P10-C accepted and adopted (2026-09-22)

The operator accepted the exact C comparison and full scene with “passt alles
prima! mach damit weiter”. This includes the disclosed remaining forepaw
rounding and larger Litten composition, not a retrospective numeric-layout
pass. The original agent findings below remain historical evidence.

C is now installed through the normal promotion command. The prior P10 bundle
and QA files are retained in the ignored backup. Current production validation
passes, and master, German preview and all nine cards match the accepted
candidate pixel-for-pixel. The other 41 installed masters are unchanged.
The provenance records an agent technical review; the separate user acceptance
does not claim the user personally inspected every physical crop.

[Exact user acceptance](reviews/2026-09-22-p10-c-user-acceptance.json) and
[adoption / continuation record](reviews/2026-09-22-p10-adoption-and-next-round.md).
Separate German panorama-only print proofs passed all-four-page visual review,
exact embedded-pixel checks and physical placement checks. No complete
Pokédex PDF or release archive is rebuilt or approved by this adoption.

### P10 source-detail correction trials (historical checkpoint, 2026-09-22)

P10 (`Pokedex/sections/gen7`) now has inspected exact-source traits and the
existing opt-in v11 2-MP source-detail one-shot configuration. Three immutable
trials used the same original seed, pinned models, scene and four reference
images; only Litten's trait paragraph changed between A/B/C. No production
renderer module or historical transport helper was edited. A P10-only local
invocation reuses and freezes the reviewed transport.

The missing oblique right-foreleg segment is visible in all three new results.
A/B overexpose the far forepaw. C reduces that protrusion but retains a small
rounded contour that is more visible than in the exact original. C was shown
with this residual difference, not declared fully source-identical.
Litten is also larger/higher than the small placement target, while all three
figures remain inside their actual physical cards. No numerical small-cast
layout pass is claimed. The later user decision accepts these exact new pixels.

Root inspected every raw/master/German preview, all nine physical cards per
trial, the three exact originals and four input references. All jobs, logs and
outputs were retrieved and verified. The current C canonical verifier and 119
focused tests pass. All 42 installed masters stayed unchanged during this P10
work; no promotion, PDF/archive rebuild, commit or publication occurred. No
fourth automatic prompt retry or multistage fallback was started. Existing
P03/P27 and older P10 partial acceptances were not transferred to new variants.

See [C and all three source/card comparisons](reviews/2026-09-22-p10-source-detail-review.md)
and [the exact C findings](reviews/2026-09-22-p10-source-detail-c.json).

### Scoped shortlist feedback (2026-09-22)

The operator identified a missing right foreleg segment in P10 Flamiau and
called it the only issue in the latest comparisons. Exact-source/card
reinspection confirms the narrow oblique segment visible behind the planted
foreleg in the original is absent from the shown card, without vegetation
occluding that location. The earlier P10 agent assessment of minor differences
only was incomplete and is superseded for this subject; its historical report
is retained unchanged.

The initial feedback is recorded as exact-image acceptance of the latest P03/P10/P27
round except Flamiau: P03 and P27, plus P10 Bauz and Robball, are accepted in
the shown comparisons. P10 was then blocked on Flamiau's correction; the later
C acceptance and adoption above supersede that blocker. All 21
master/card/source file hashes still match the presented artifacts. No image
was regenerated or promoted in this feedback checkpoint. This does not extend
to P02's separate remaining decisions, other sets, new variants, full print
inspection or release approval. A corrected Flamiau candidate must again be
shown beside the original source, with any new master and all physical cards
checked before promotion.

See [the current comparison page](reviews/2026-09-14-panorama-shortlist.md) and
[the exact feedback and artifact bindings](reviews/2026-09-22-shortlist-user-feedback.json).

### Scoped production adoption (2026-09-22)

The accepted P15-D (`ExGen2/sections/mega`) and P40-B
(`ExGen3/sections/normal`) are now installed through the regular promotion
command after fresh source, raw/master, German-preview and all-nine-card
inspection. Both production bundles pass current generation/source/overlay
validation and preserve the exact reviewed pixels. Prior bundles are backed
up in the ignored workspace. This is an agent technical review, not a claim
that the user inspected every crop.

P15 is also current in the work planner. P40 still receives the planner-only
`scene_catalog_drift` warning because the unchanged catalog constraint list
has an appended, fingerprinted placement reminder. This exact-list comparison
issue is diagnosed and a bounded correction proposed, but not implemented
without its separate design confirmation. The warning is not hidden by the
successful production-validator or print-proof results.

The historical small-cast numeric-layout findings remain unchanged. P15-D's
accepted Rayquaza spacing and P40-B's accepted larger composition are
image-specific decisions. Latios still has a narrow, contained left margin;
no generous cutting-tolerance claim is made.

Separate German panorama-only print proofs use the production PDF page
renderer. They are not complete ExGen2/ExGen3 sets or a new release. Those
aggregate PDFs still depend on unapproved sibling panoramas. SV07's reserved
Hopplo shadow, the earlier experimental candidate integration, and other
open artwork reviews remain separate work.

See [the production verification record](reviews/2026-09-22-approved-artwork-production.md).

### Canonical source-detail pilot (2026-09-15, historical checkpoint)

The accepted spatial-layout plus individual-detail recipe is now available as
`flux/joint_scene/spatial_source_detail_joint`, current pipeline version 11.
Version 10 and the older contracts remain reconstructable. Exact inspected
source hashes and per-figure traits are bound into prompts, input records and
fingerprints. Generation uses a real 2-MP target, one sampler and one decode;
print preparation remains deterministic 300-dpi Lanczos. There is no source
paste or automatic multistage fallback. The bulk initializer is unchanged;
only SV07 and the two explicitly requested transfer scopes
`ExGen2/sections/mega` (P15) and `ExGen3/sections/normal` (P40) are activated.

P01/SV07 A was rejected for an extra Bulbasaur, misplaced Squirtle and clipped,
oversized Scorbunny. Same-seed B changes only the first two count/layout prompt
paragraphs. It restores the three intended figures and physical-card
containment, with source-close faces and appendages. It does **not** satisfy the
configured size bounds: Scorbunny and Squirtle are larger/higher than requested.
Scorbunny's narrow leftward ground shadow is also inconsistent with the
upper-left key light. B was presented with those limitations. The operator
then accepted the shown figures, scene and composition, including the larger
Scorbunny/Squirtle, with "alles perfekt. der neue Flow scheint sehr gut zu greifen!".
This is exact-image identity/composition acceptance, not a changed historical
technical verdict or blanket permission for larger figures elsewhere. The
previously reserved shadow correction and technical promotion remain open;
B is **not yet a release-ready replacement**. Both the controller and an
independent visual reviewer viewed the raw, full master, German preview, all
nine cards and all three exact originals. See the
[three source/card pairs and open decisions](reviews/2026-09-15-sv07-source-detail-review.md)
and [hash-bound B findings](reviews/2026-09-15-sv07-source-detail-b.json).

The new focused suite has 27 passing tests. The covering suite has 356 passes
and three pre-existing failures from revoked/stale historical visual approvals;
these have not been relabeled to make tests green. Scoped implementation reviews
passed. Neither those checks nor this pilot establish reliability for all sets.
After the P01 checkpoint, both mandatory transfer targets were regenerated as
two controlled A/B trials each. P15 A was rejected for a duplicated Mewtwo tail,
an added Latios wing marking and layout drift. B corrects two source-trait
paragraphs, including an initially erroneous description of Latios's marking.
P40 B adds only a final full-silhouette layout reminder after A's top-edge
concern. Seeds, model pins and all four references remain identical within
each A/B pair; the A manifests and sealed jobs remain historical evidence.

Both B candidates are source-close and physically contained in their actual
cards, but **neither passes the configured small-cast layout**. Rayquaza is
close to its left cut edge; Miraidon's lightning has visible but narrow top
clearance. P40 also retains a central rather than outer-horizon building.
Independent review does not approve P40 for promotion on layout grounds.
Both outcomes are presented only for explicit identity/composition feedback,
with all six actual card/source pairs in
[the P15/P40 review](reviews/2026-09-15-p15-p40-source-detail-review.md).
The user subsequently accepted P40-B's shown identities and composition, and
P15-B's identities and remaining scene, explicitly asking only for more room
around Rayquaza. Both decisions are bound to the exact B master/card/source
hashes after fresh verification. P40-B remains unchanged. A single P15-C
one-shot was tested for the requested clearance and rejected: the image-left
gap remains insufficient (distinctive teal body pixels start at x10 in both B
and C, versus a 60 px target; this is not full silhouette segmentation).
No acceptance transfers to changed C pixels or converts the historical layout
checks to passes. C, its complete immutable job and exact manifest snapshot
are retained; the active P15 manifest was restored byte-for-byte to B.
See [the clearance comparison](reviews/2026-09-15-p15-clearance-review.md).
The user approved the proposed Rayquaza-only spatial-reference size adjustment.
P15-D uses factor 0.8 only for that shared-position subject; exact individual
references, original seed/model pins/scene and single one-shot synthesis remain.
The opt-in renderer adjustment passed independent scoped review and 119 covering
tests; actual B reference PNGs/graphs/fingerprints remain byte-identical when
unconfigured. D completed once; root and independent review inspected raw,
master, German preview, all nine cards, all three sources and four references.
Rayquaza has visibly more actual cut-edge clearance: the same interior-color
proxy changes left 10 to 73 px and right 14 to 39 px; this is not whole-outline
segmentation and the 60 px right-side aim is still unmet. No definite new
anatomical blocker was found. The user subsequently replied "Passt prima!" to
the shown D Rayquaza comparison and spacing question. Exact D clearance is now
accepted and that correction point is resolved; this does not assert a separate
human inspection of every other D card. D was not promoted at this checkpoint;
its later adoption is recorded above. Its configured smaller silhouette bounds
remain exceeded; technical findings are not rewritten.
See [D and all three original/card pairs](reviews/2026-09-15-p15-scale-review.md).
The early claim that both P40-A lightning tips were cut was too strong:
targeted reinspection supports left-tip edge contact/suspected clipping,
not proven loss of the right tip. B has visibly improved clearance.

The bounded transfer adapter received independent review and a fail-closed
evidence fix. The new focused covering suite reports 119 passes; D's canonical
verifier passes. Both B verifiers passed before the intentional renderer change;
their frozen-code preflight is historical now and is not rewritten. Root and independent reviewers inspected
raw/master/preview, all nine cards and all exact sources for every trial.
At the 15 September checkpoint all 42 installed masters and earlier exact-image
approvals remained unchanged. No bulk generation, promotion, PDF/ZIP rebuild,
commit or push was performed at that checkpoint.
P01's reserved narrow-shadow correction remains open. The new P15-C is the
third controlled P15 trial, explicitly requested after B. The later explicit
approval authorizes D's new spatial-size approach, not an automatic prompt-only
loop, P40 regeneration or multistage fallback.

## Installed pipeline before the reopened audit

The following pipeline and promotion inventory records the pre-audit state;
"promoted" and "enabled" do not mean that the new visual review passed.

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

## Installed scope state and superseded approvals

All 42 bundles remain installed and enabled, but 41 fail the current visual
gate and cannot be consumed by a passing normal release build. The following
inventory describes their historical generation contracts. Thirty-eight use the
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

The initial v10 agent-reviewed replacements were `SV07` (two-ear Hopplo), `ME05`
(Robball, Morpeko, Marshadow), and `SV08` (Ho-Oh, Krokel, Pikachu). SV08 uses
the existing poster-only slot selection for Pikachu `sv08-057`; Black Kyurem
`sv08-048` remains unchanged in the card data. Full raw/master and all nine
physical crops were inspected before promotion. Their provenance records
agent inspection, not a new human approval. The subsequent complete source
comparison revoked SV07 and SV08; only ME05 retains its pass.

## Configured target and language coverage

Every current target has a checked-in manifest and a configured creative brief.
Configuration and installed-file coverage never imply visual approval. The 41
rejected installed targets retain enabled routing and now fail closed at the
review gate; they have not silently fallen back to ordinary covers.

| Scope family | Configured | Promoted and enabled | Disabled / awaiting activation |
| --- | ---: | ---: | ---: |
| Individual TCG sets | 27 | 27 | 0 |
| Pokédex generations | 9 | 9 | 0 |
| ExGen1 sections | 1 | 1 | 0 |
| ExGen2 sections | 3 | 3 | 0 |
| ExGen3 sections | 2 | 2 | 0 |
| **Total** | **42** | **42** | **0** |

Every configured target has an installed promotion record. Exactly one passes
the current source review; 41 records have been revoked. New rejected
candidates remain experiment evidence and are not promoted or substituted into
PDFs. Existing release files remain retained, unapproved candidates.

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

1. Implement and validate the approved source-pixel-protected contact-shadow
   prototype; the existing upper-only identity-lock mask cannot correct grounding.
2. Replace every rejected or unresolved panorama with a source-faithful,
   naturally integrated candidate; inspect raw/master and all physical crops.
3. Promote only passing candidates, rebuild affected PDFs and archives from
   one source revision, and repeat artifact and multilingual visual checks.
4. Keep `wide_4x3` and `wide_4x4` modeled but disabled for PDF production until
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

Historical pre-re-audit branch verification on 2026-09-12 (technical evidence
remains historical evidence; visual approvals below have been reopened):

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
