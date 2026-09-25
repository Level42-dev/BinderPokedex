# Poster Artwork Requirements and Roadmap

This is the stable product and engineering contract for scope posters. Current
accepted assets are listed in
[Poster Status](POSTER_ARTWORK_STATUS.md), operator commands in
[Poster Workflow](POSTER_WORKFLOW.md), and rejected candidate evidence in
[Poster Experiment Log](POSTER_ARTWORK_EXPERIMENT_LOG.md). The isolated paired
edit-training experiment is specified in
[Poster Artwork Integration LoRA](POSTER_ARTWORK_TRAINING.md).

Last reviewed: 2026-09-22

**Historical visual baseline (12 September):** The source-by-source re-audit
supersedes the older artwork acceptance statements below: 41 of 42 installed
panoramas were rejected, only ME05 passed. Their historical files remain, but
the 41 approval flags have been revoked. See the
[complete audit](reviews/2026-09-12-panorama-audit.md). The operator has approved
an ExGen3-first source-locked grounding prototype; implementation and technical
tests do not reinstate any visual approval. On 14 September the operator
reaffirmed genuine one-shot generation as the preferred correction path and
reserved the multi-stage approach for a separately justified last resort. The
ExGen3-only restart and revised occlusion acceptance are recorded in
[the bounded comparison](reviews/2026-09-14-exgen3-oneshot-restart.md).
Later exact-image acceptances and scoped technical adoptions supersede this
baseline only for their own artifacts; see [current status](POSTER_ARTWORK_STATUS.md).

## Decisions

| Decision | Current direction |
| --- | --- |
| Default binder format | `standard_3x3` on A4 portrait at physical card size |
| Wide layouts | Keep `wide_4x3` and `wide_4x4` at physical card size; paginate their cutouts across A4 and reserve A3 for a continuous one-sheet print |
| Generation timing | Explicit optional post-fetch step, before PDF generation |
| Generation host | Reuse the active workspace's complete private renderer marker; ask local/remote only for a fresh, incomplete or unreachable configuration. Remote endpoints and credentials stay outside tracked files |
| PDF behavior | Consume only promoted local artwork; never launch ComfyUI implicitly |
| Cover fallback | Use the promoted poster as the section start page; keep the existing section cover only when no promoted poster is enabled or the build explicitly skips posters |
| Poster presentation | Render enabled posters as cuttable physical cards by default; optionally render the same localized poster as one continuous physical-grid-sized image centered on its PDF page |
| Generator | FLUX.2 `joint_scene` remains the mode for new candidates with avoidance-first `individual_spatial_joint` v9 as the default; earlier reviewed contracts remain reproducible |
| Fallback | FLUX.2 `identity_lock` remains available only as an explicitly justified last resort after documented one-shot investigation; individual failed candidates do not trigger it automatically |
| Prompt ownership | Set-specific creative briefs in one catalog plus one centrally generated identity, placement, depth, and safe-area contract |
| Character identity | Supplied Official Artwork is the authority for form, stature, anatomy, silhouette, pose, color, and markings |
| Form identity | Card/cover imagery and poster subjects are separate; Mega, Primal, X/Y, regional, and other forms keep their exact allowlisted Official Artwork identity |
| Promotion | Explicit, hash-bound visual review plus deterministic validation is mandatory; record whether the reviewer is human or agent, without claiming agent review is operator approval |
| Missing poster | A scope without an enabled promotion uses its normal cover path; enabled-but-missing promoted artwork is an error; `--skip-poster` explicitly forces the cover-based path |
| CI boundary | Pull requests build and validate a complete release candidate without publishing; only `v*` tags may publish |
| Rejected experiments | Anima, FLUX.1 Canny, Qwen, SDXL, DreamO, direct edit, and direct inpaint remain evidence in the log and Git history, not live production options |
| Training experiment | A paired FLUX.2 Klein 4B integration LoRA may be evaluated outside production; copied exact-position artwork is input, only fully reviewed integrated scenes are targets, and routing cannot change before unseen holdout approval |

## One-shot acceptance gate

A `joint_scene` candidate is promoted only when one result satisfies all hard
gates at the same time:

| Gate | Priority | Acceptance |
| --- | --- | --- |
| One model-owned final scene | Hard | The final pass starts from an empty target and generates landscape and characters together; no character pixels are composited, restored, moved, or replaced after decode |
| Character identity | Hard | Cast count, exact form, pose, stature, silhouette, defining anatomy, face, colors, and markings match the supplied references without invented or missing traits |
| Physical card containment | Hard | Every complete character and appendage remains inside its assigned bottom-row card in the actual print raster, with visually appropriate padding |
| Coherent scene depth | Hard | Shadows and ground contact agree. A connected landscape element either stays clear of a character or keeps one physically plausible front/behind relationship for its entire visible intersection; ending at a silhouette or switching depth around it fails |
| Deterministic print output | Hard | Text-free output reaches the exact configured 300-dpi dimensions through deterministic resampling; typography, logo, slicing, and PDF use remain deterministic |
| Set-specific scene quality | Preferred | The result is attractive, recognizable for the scope, and preserves the requested text-safe regions |
| Foreground intersections | Desired when scene-appropriate | Existing near-camera landscape elements may cover small exterior parts with consistent depth. This is not a character-identity change. Preserve defining features for review; do not invent unrelated vegetation, hide malformed anatomy, truncate plants at silhouettes, or force every scene to contain an overlap. The checked-in avoidance-first prompt is historical behavior pending a reviewed replacement |

Minor print-scale simplification of a non-defining line may be accepted only
after direct comparison at final card size. A changed body-part count, facial
structure, defining contour, marking, form, or gross proportion always fails.

`identity_lock` uses a different hard gate: every fully opaque source pixel
must be byte-identical after generation. Its weaker local terrain interaction
is a known limitation of the historical two-pass contract, not sufficient
acceptance for the new version-10 correction. The explicitly selected
`grounded_source_pixels` prototype must additionally preserve every
nonzero-alpha source pixel and all pixels outside reviewed ground masks,
produce convincing contacts/shadows, and pass the same full source/raw/print
visual review. No broad upper-context blend is used in that new contract.

## Experiment and decision rule

1. Record the accepted baseline and every material experiment through focused
   commits and the experiment log.
2. Change one placement, identity, or scene-control mechanism at a time.
3. Give one architecture at most three materially distinct attempts to fix the
   same repeatedly failing hard gate.
4. After the third failure, stop and choose explicitly: retain the baseline,
   relax one named gate, change the mechanism, or accept more implementation
   complexity.
5. Do not silently turn a failed one-shot back into compositing, or a fallback
   into an alleged one-shot.

## Architecture evidence

The following acceptance descriptions are historical experiment records.
Current asset approval is determined by the September re-audit and the linked
status document, not by these older rollout summaries.

| Architecture | Final scene jointly generated | Identity | Card containment | Scene integration | Role |
| --- | --- | --- | --- | --- | --- |
| FLUX.2 Individual Spatial v9 `joint_scene` | Yes | One positioned identity reference per subject remains the identity authority; existing v7 promotions define the accepted print-detail tolerance | Existing promotions pass their physical crops with useful padding; new v9 candidates retain the same geometry | The one-shot now keeps camera-near scenery outside the known character volumes while preserving one continuous ground plane | Default for new candidates; existing v7 promotions remain reproducible |
| FLUX.2 Spatial+Identity v5 `joint_scene` | Yes | Gen I `00001`, Gen II `00001`, Base1 `00001`, ExGen3 Mega `00001`, and ExGen3 Normal `00001` pass the accepted print-detail tolerance | All five promotions pass their physical crops with preferred fill | Coherent grounding and shadows; retained as an accepted reproducible topology | Reproducible legacy; five scopes promoted |
| FLUX.2 Regional Identity v6 `joint_scene` | Yes | The promoted Generation III candidate keeps all three supplied identities within normal one-shot tolerance | All three complete subjects pass their physical bottom-card crops | The reviewed promotion passes, but the six-scope audit exposes independent lower-card scene predictions and fails to generalize | Generation III reproduction only; broader rollout stopped |
| Two-pass `identity_lock` | No | Exact source pixels | Reliable | Protected lower band can read as a layer | Explicit fallback; no active promoted scope |
| Landscape reference plus joint final pass | Final pass only | Usually strong | Inconsistent | Retained plants can switch depth at silhouettes | Rejected |
| Direct FLUX edit/inpaint | No | Inconsistent | Inconsistent | Retains cutout/composite artifacts | Rejected |
| Anima with restored identity core | No | Recognizable only because pixels are restored after decode | Card-safe in preflight | Flat lawn and weak contact | Rejected |
| FLUX.1 Canny / Qwen | Varies | Redesigns, duplicates, or drops subjects | Fails | Does not satisfy the scene contract | Rejected |
| SDXL regional identity / DreamO | Yes in their isolated graphs | Fails reference binding or anatomy | Fails | Insufficient for the required cast | Rejected |

## Requirement register

| ID | Requirement | Status | Acceptance |
| --- | --- | --- | --- |
| `PA-001` | A4 production defaults to a 3×3 physical card grid | Done | Initializer and active A4 manifests use `standard_3x3` |
| `PA-002` | 4×3 and 4×4 remain first-class artwork layouts | Done | Geometry, placement, prompting, promotion, validation, slicing, and A4 PDF pagination are layout-driven |
| `PA-003` | Wide layouts preserve physical card dimensions | Done | Cuttable PDFs keep every card at 63.5 × 88.9 mm and paginate without scaling; continuous 4×3 and 4×4 sheets still require A3 |
| `PA-004` | Every individual TCG set has explicit scene direction | Done | `config/posters/scenes.yaml` has exact one-to-one catalog coverage enforced by tests |
| `PA-005` | Full prompts cannot drift per set | Done | Creative scene is scope-specific; technical requirements are generated centrally |
| `PA-006` | Poster preparation is an optional post-fetch phase | Done | One-scope and batch initialization exist and preserve reviewed manifests |
| `PA-007` | Generation follows the scope contract | Done | Runner reads FLUX.2 model, mode, reference topology, seed, steps, generation size, output method, and dpi from `poster.yaml`; explicit overrides are recorded |
| `PA-008` | Figures remain authentic | Reopened by source audit | Technical review binding exists, but 41 installed panoramas failed direct source comparison. The approved grounding prototype adds nonzero-alpha protection; full visual acceptance remains mandatory |
| `PA-009` | Artwork matches typography and card cuts | Done | Prompt safe cells and subject placement derive from the same physical layout used by finalization and slicing |
| `PA-010` | Only promoted artwork enters a normal PDF | Done | `pdf.enabled` plus a local tracked promoted file gates inclusion |
| `PA-011` | Poster use is optional per build | Done | `--skip-poster` bypasses poster discovery and writes a separate build |
| `PA-012` | Every promotion is reproducible and auditable | Done | Provenance records model, prompt, source, references, workflow, review/audit, and output hashes |
| `PA-013` | Aggregate sections can own separate posters | Done | `posters.yaml` routes isolated leaf manifests and replaces each matching cover with its enabled poster |
| `PA-014` | 4×3/4×4 cutouts print on the standard A4 renderer | Done | A 4×3 renderer keeps source columns 1–3 together on page one and places source column 4 vertically in page two's first column; cutting guides remain around empty cells |
| `PA-015` | Aggregate variants receive section-specific scenes and curated subject/reference sets | Configuration done; artwork review reopened | All 15 aggregate sections have exact catalog coverage and installed promotions; their revoked visual approvals must be replaced |
| `PA-015A` | Variant subjects retain their exact form | Done | Selection, cutouts, planner, fingerprints, promotion, and validation bind exact Official Artwork identity |
| `PA-016` | Post-fetch orchestration detects stale inputs | Done | Read-only planner separates expensive generation drift from cheap overlay/routing changes |
| `PA-017` | Generation provides natural grounding without losing identity or card safety | Reopened; scoped corrections in progress | The 12 September baseline passed only ME05. Later exact-image decisions and technical adoptions are listed in Poster Status; no blanket approval follows from renderer tests or a Git checkpoint |
| `PA-018` | Runtime remains KISS after experiments | Done | Production exposes only FLUX.2 `joint_scene` and `identity_lock`; all three reference topologies use the canonical joint workflow builder and common empty-target sampler path, with no separate experiment entry point |
| `PA-019` | Pull requests prove a release can be built without publishing | Done | PRs validate promotions, build every PDF/archive/manifest, and upload only a temporary artifact |
| `PA-020` | Raster card geometry closes exactly on every real canvas | Done | Cumulative physical endpoints drive preparation, finalization, slicing, promotion, and validation |
| `PA-021` | Default and fallback cannot become ambiguous | Done | One manifest owns one active generation contract; fallback selection and promotion are explicit |
| `PA-022` | Poster copy works in every language emitted for its scope | Done | Tests cover all 266 current target/language combinations; aggregate copy is complete in all nine PDF languages and TCG sets follow their advertised language inventory |
| `PA-023` | A poster carries the semantic information of its preceding cover | Done | Scope JSON is the only semantic copy source. Set posters show localized set name, card count, release date, title/logo, and project identity; aggregate posters show section title, subtitle/region, Pokémon count, description/range, collection title, and project identity. The renderer automatically removes an identical upper/info title, infers supported inline logo tokens, and keeps the cover-only cutting hint/build timestamp as operational metadata |
| `PA-024` | An enabled poster replaces its preceding cover without removing the fallback path | Done | The renderer emits exactly one section start page: promoted poster when enabled, otherwise the canonical cover; `--skip-poster` explicitly selects covers |
| `PA-025` | Every current set and subsection is represented in the poster work plan | Configuration done | 42 checked-in manifests cover 27 individual sets and 15 aggregate sections; configuration coverage does not imply visual approval |
| `PA-026` | A scope with fewer canonical subjects is not padded with duplicates or unrelated forms | Done | Section manifests accept one to the layout column count; two-subject `ExGen2/primal` uses the two outer bottom cards while the normal 3×3 default remains three subjects |
| `PA-027` | The existing cover path remains available when no poster can be consumed | Done | Missing or disabled poster routes leave the section cover and normal card pages intact; `--skip-poster` bypasses poster discovery before asset loading |
| `PA-028` | One promoted poster can be emitted either as physical cards or as a continuous page | Done for A4 3×3 | `cards` remains the default with nine 63.5 × 88.9 mm images and cutting guides; `--poster-page-mode full-page` draws one 200.5 × 276.7 mm image centered on A4 without cutting guides and writes a distinct filename |
| `PA-029` | A learned integration path cannot weaken current identity, layout, depth, or fallback guarantees | In progress | Versioned pair contract, audit tooling, and an immutable aligned teacher-target builder exist; exact canonical source pixels are restored after the teacher pass, every target still needs human integration review, production stays unchanged, and promotion requires an unseen five-fixture comparison against both retained paths |
| `PA-RW-001` | Artwork generation explicitly supports local or remote execution without storing worker endpoints | Done | Root guidance reuses a complete active workspace marker and asks only when needed; immutable hash-pinned jobs, private SSH configuration, loopback-only ComfyUI, returned logs/metadata and explicit visual review remain required |
| `PA-RW-002` | Remote runtime dependencies and reusable model weights have independent lifecycles | Done | A checksum-pinned standalone bootstrap builds portable Python, locked packages, and ComfyUI entirely below an ephemeral runtime root; `ComfyUI/models` links to an external operator-selected cache, bundles never dereference it, and validated destruction preserves it |
| `PA-030` | Custom layouts can be generated without changing release assets | Done | The custom-layout workspace command clones manifests and deterministic source inputs below ignored `tmp/`; aggregate workspaces accept explicit per-section fallback Pokémon for complete wide layouts, an optional hybrid mode copies unselected existing promotions, and `BINDER_POKEDEX_POSTER_ASSETS` routes generation, promotion, validation, slicing, and PDF discovery without writing tracked release assets |

## Historical production boundary (before the September re-audit)

- All 41 promoted 3×3 bundles are enabled.
- All 41 current poster targets are configured, promoted, and enabled.
- Thirty-nine enabled bundles use the reviewed avoidance-first `joint_scene` /
  `individual_spatial_joint` v9 contract. Primal uses the same graph with its
  explicitly reviewed `landscape_first_v1` prompt profile. `SV04.5` uses its
  explicitly reviewed mask-free `spatial_identity_joint` v7 contract. All use
  unquantized BF16 FLUX.2 Klein 4B generation and deterministic Lanczos print
  resampling.
- `identity_lock` remains an explicit fallback but has no active promoted scope.
- Current manifests use `joint_scene`; 40 select `individual_spatial_joint`
  (39 with v9 and Primal with `landscape_first_v1`) and `SV04.5` selects
  `spatial_identity_joint` v7. Earlier v5/v6 and Dev promotions remain
  reproducible through Git history but are not active.
- The reviewed v9 candidates were generated through the isolated remote-worker
  job path. Worker endpoints and credentials are operational state and are not
  part of tracked provenance.
- Fetching, planning, PDF building, and CI do not start ComfyUI.
- A generation operator or agent chooses local or remote execution explicitly.
- Generated candidates remain ignored scratch locally or in a returned remote
  job; only promotion creates tracked input for deterministic PDF and release
  jobs.
- The rollout is complete for 41 user-reviewed promotions.
- Each section has exactly one start page. Enabled promotions replace their
  section covers; missing/disabled assets and explicit `--skip-poster` builds
  retain the canonical cover fallback.
- Enabled A4 posters use the cuttable `cards` presentation by default. The
  explicit `full-page` presentation keeps the complete localized poster at its
  200.5 × 276.7 mm physical grid size, centered on A4 without cutting guides.
- Wide PDF formats remain an explicit roadmap item.

## Change rule

When a requirement changes:

1. update its row and acceptance statement here;
2. update the operator guide when behavior or commands change;
3. add or adapt a deterministic regression test;
4. update the related GitHub tracking issue;
5. record candidate-specific evidence in the status or experiment log.
