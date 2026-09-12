# Poster artwork experiment log

This log records local visual experiments and the decision that followed each
one. Most candidates are intentionally not promoted; an entry says explicitly
when one becomes the accepted baseline. The log complements the requirements
and status documents with the variable changed at each useful checkpoint.
Commands and implementation names below describe their historical checkpoints;
rejected builders were removed from the production tree during the 2026-07-29
KISS cleanup and remain recoverable through Git history.

## Non-negotiable review rules

- The final artwork is synthesized by the model as one coherent scene. No
  character cutout is composited or restored after the final model pass.
- Supplied character artwork is the identity and anatomy authority.
- Landscape elements keep a physically coherent front/behind relationship at
  every character intersection.
- Every complete character remains inside its assigned bottom-row card after
  physical poster slicing.
- Generated text, boxes, landing pads, paths, and visible layout guides are not
  part of the artwork.

## Pokédex Generation I / FLUX.2 Klein rollout

The first remaining Pokédex migration applies the unchanged promoted graph and
prompt builder to seed `260782266`, the Kanto scene brief, and the reviewed
Bulbasaur, Charmander, and Squirtle references.

| Candidate | Pipeline change | Result | Decision |
| --- | --- | --- | --- |
| `joint_scene/00001` | Change only the scope seed, scene brief, identities, and shared physical placement derived for Generation I | Exactly the three expected starters appear once and remain complete inside their assigned physical cards with useful padding. Their defining anatomy, faces, colors, markings, silhouettes, and poses match the references within the accepted one-shot print-detail tolerance. Morning light, contact shadows, continuous meadow terrain, and foreground plants remain spatially coherent | Accepted and promoted on 2026-07-29 as the fifth `joint_scene` scope |

The Metal/MPS render completed in 229.93 seconds. Reproducibility evidence:

| Artifact | SHA-256 |
| --- | --- |
| Raw 848 × 1168 candidate | `4d5ed1e63e1f972fc62054261d4e3d9c016f9e89864b1181cae6b443198b8969` |
| Text-free 2368 × 3268 print raster at 300 dpi | `1a4c376d48d4fdde92d9901985f5baf44207909a0088831f5278e65d18b04df2` |

The complete generation fingerprint is:

```text
3ad057acbcf8f95fd20b1661df5f938c7e06540d9c6275b773524db67b462f8d
```

## Pokédex Generation II / FLUX.2 Klein rollout

The unchanged graph and prompt builder use seed `260753030`, the Johto scene
brief, and the reviewed Chikorita, Cyndaquil, and Totodile references.

| Candidate | Pipeline change | Result | Decision |
| --- | --- | --- | --- |
| `joint_scene/00001` | Change only the scope seed, scene brief, identities, and shared physical placement derived for Generation II | Exactly the three expected starters appear once. Chikorita's leaf and body markings, Cyndaquil's side pose and flame, and Totodile's raised-leg pose, jaws, teeth, limbs, and back spikes remain faithful within the accepted one-shot print-detail tolerance. All three physical crops pass with generous padding; shared warm light, shadows, meadow, and foreground vegetation remain coherent | Accepted and promoted on 2026-07-29 as the sixth `joint_scene` scope |

The Metal/MPS render completed in 203.82 seconds. Reproducibility evidence:

| Artifact | SHA-256 |
| --- | --- |
| Raw 848 × 1168 candidate | `668d5d732771529e4bb3ce2ff8cf13b6bb58bede9d49c1eace86f459e3fb5c92` |
| Text-free 2368 × 3268 print raster at 300 dpi | `f9849c301d29c0176a41b611ecc0c4b0ec7abf9051743a86b3bcd144fb5e3a3d` |

The complete generation fingerprint is:

```text
0ca3ebca51b6683e4956a71b7659123e9db312b961ec4a66b0108dcf88628455
```

## Pokédex Generation III / foreground-depth boundary

The unchanged production graph uses the Hoenn scene brief and reviewed Treecko,
Torchic, and Mudkip references. Configured seed `260750880` first produced a
fourth background creature and failed exact count. Seed `260750881` removed the
extra subject and passed identity and card fit, but exposed the requested hard
case: a plant rooted at the lower-right foreground passed behind Mudkip's rear
body and tail.

The subsequent depth test holds model, seed, references, rectangles, sampler,
scene, count rules, identity rules, and all non-depth prompt text fixed.

| Candidate | Sole depth change | Result | Decision |
| --- | --- | --- | --- |
| `depth/original` | Production prompt; depth paragraph begins after 648 whitespace-delimited words | Exactly three faithful, card-safe subjects, but the lower-right foreground plant passes behind Mudkip | Rejected at coherent-depth gate |
| `depth/early` | Move the existing depth paragraph unchanged so it begins after 388 words; total remains 894 words | The same lower-right foreground relationship remains behind Mudkip | Rejected; prompt priority alone does not solve the crossing |
| `depth/binary` | Keep the earlier position and replace only the depth paragraph with a 904-word total that defines bottom-edge vegetation as foreground and clarifies that anatomical completeness does not require every exterior pixel to remain visible | A lower-right blade still passes behind Mudkip's tail; additionally, the lower-left foreground plant passes behind Treecko's foot, body, and tail | Rejected; the contradiction remains and appears at another subject too |

Metal/MPS evidence:

| Candidate | Runtime | Raw 848 × 1168 SHA-256 | Workflow SHA-256 |
| --- | ---: | --- | --- |
| `depth/original` | 243.75 s | `e8103fe2f8e7a1d426f9aa7f9e036251db41cdeb506af0b85c080b1d39083a5e` | `a13685af821a31f409af117a0da77fddbec13420475d11c51be6cde463d93640` |
| `depth/early` | 189.47 s | `3abfbf3c45c3815b58306b759eb341892634afdc820c8876277c76c3cbb0842c` | `a0f70730f9632270ed546841f45c2f87a44b808c0aed3d5bdb1aa9bedaa33a63` |
| `depth/binary` | 206.11 s | `a6339c43c844897704fa251bd32d196347474881e1bd473e70ba3800436ba268` | `0408f3499909f72902879da377c1e51d51ff723fba547073583a49592c83064c` |

The three materially distinct depth variants exhaust the prompt-only stop rule.
No candidate is promoted, no central prompt wording or ordering changes, and
Generation III remains on its accepted `identity_lock` fallback. A future
retry requires a changed control mechanism rather than more prompt emphasis.

### Discarded single-subject prompt retry

On 2026-07-29 the prompt-only question was reopened once as a deliberately
smaller diagnostic: one Mudkip, one forest clearing, 512 x 512 pixels, two
fixed seeds, and an otherwise identical one-shot FLUX.2 Klein graph on
Metal/MPS. A soft request to cross the rear-right area was avoided entirely.
A concrete request for one connected fern frond to cross a named outer tail
edge produced real foreground occlusion in both seeds, but one seed extended
the overlap too far toward the rear body. Abstract depth wording and explicit
contour/topology terminology produced unnatural dark connecting lines.

The useful local wording did not generalize to the real three-character
poster. With the original Generation III references, geometry, and seed held
fixed, both a short generic overlap rule and a conditional rule declaring
bottom-border vegetation as nearest foreground still allowed the connected
lower-right plant to pass behind Mudkip. The retry is therefore discarded:
its temporary workflows and renders are not retained, no production prompt or
artwork is changed, and `identity_lock` remains the Generation III fallback.
Further prompt-only depth variants stay closed.

### Silhouette-free zone-layout A/B

One bounded architecture A/B on 2026-07-29 tested whether the complete,
unoccluded character pixels in `joint_scene_cast_reference.png` were the
remaining structural depth bias. Candidate A reused the existing Generation
III `depth/original` result at seed `260750881`. Candidate B kept the model,
encoder, VAE, seed, 848 x 1168 empty target, four-step Euler sampler, CFG,
identity-reference bytes and order, normalized rectangles, Hoenn scene,
depth wording, and safe areas unchanged.

B replaced only the first image reference with a silhouette-free 608 x 832
occupancy map. It used the same neutral background as A and three identical,
softly feathered, low-contrast zones at the exact A character bounds. The
three IMAGE-role paragraphs were changed only as required to map Treecko,
Torchic, and Mudkip to the left, center, and right zones and to transfer pose
and orientation authority to their individual identity images.

| Gate | A: complete spatial cast | B: soft occupancy zones |
| --- | --- | --- |
| Count and coarse order | Pass | Three subjects in left/center/right order |
| Identity and anatomy | Pass within accepted one-shot tolerance | Hard fail: the right subject is a bipedal Torchic/Mudkip hybrid with missing Mudkip head fin, wrong limbs, colors, tail, and pose |
| Physical bottom-row cards | Pass | Hard fail: all three subjects are much too high and large; the real bottom-row crops contain only their lowest extremities or no subject |
| Visible control residue | None | No literal zone, box, outline, panel, or landing-pad leak |
| Foreground-depth evidence | Known lower-right contradiction behind Mudkip | Inconclusive: foreground plants avoid every subject silhouette |

Metal/MPS evidence:

| Artifact | Value |
| --- | --- |
| Runtime | `188.31 s` |
| A raw SHA-256 | `e8103fe2f8e7a1d426f9aa7f9e036251db41cdeb506af0b85c080b1d39083a5e` |
| B raw SHA-256 | `172cd2b6191bc7b34c0e2785ba4f45b66f739f712c2125cb6805dba096635603` |
| Zone-reference SHA-256 | `3f44d945163c37d59a35728580f8c270c2ad08e750a612405abb8555d08acef1` |
| B prompt SHA-256 | `ed3e64632deb02e3be7fbb3f42fdfe68828632a5364735f221130af733b2d51f` |
| B workflow SHA-256 | `b1a6e1222421acf58717e05d49bae1dbe557e1862994626dc5f468fb93c8fd17` |
| A/B graph hash after removing prompt, first reference path, and output prefix | `311fb13cfb1df6b91c2088df90e64c4ac5fcb0b9e89288982e446afe52e8ebbe` |

The result reproduces the earlier no-cast placement failure and additionally
breaks identity binding. Making the zones stronger, colored, labeled, or
hard-edged would test new leakage and panel biases rather than repair the
missing reference-to-region control. No second zone variant is justified.
The zone candidate and its temporary assets are discarded, the complete
spatial cast remains the `joint_scene` placement control, and Generation III
remains on its promoted `identity_lock` fallback.

### Cast-strength and regional-conditioning follow-up

On 2026-07-30 a local implementation audit established why the earlier
reference-image variants behaved this way. ComfyUI's `ReferenceLatent` appends
each complete VAE latent to one ordered list. FLUX.2 gives those references
separate sequence indices, but it provides no per-reference target rectangle,
mask, or strength. Prompt roles such as `IMAGE 1` and `IMAGE 2` are therefore
semantic conventions. The complete cast was the only strong placement signal,
and its fully visible subjects also encoded the unwanted visual prior that
every character lies in front of the complete landscape.

One isolated 50-percent-opacity cast A/B kept the original Generation III
prompt, seed `260750881`, graph, model, three identity-reference files, target
geometry, and sampler unchanged. It preserved count, identity, and card fit,
but nearby vegetation again avoided the subjects instead of proving a
foreground crossing. No opacity sweep followed.

The next bounded architecture removed the visible cast and bound each identity
reference through ComfyUI's regional conditioning while retaining one empty
latent, one four-step sampler trajectory, and one decode. A global,
reference-free branch generated the complete Hoenn landscape. Three additional
branches each received exactly one identity reference and were blended only
into the corresponding physical bottom card.

The first 0.25-MP variant used full-canvas branches plus soft masks. It failed
because FLUX still placed each complete subject semantically on the full
canvas; only the body part intersecting its mask survived. The single
diagnostically justified correction used
`ConditioningSetAreaPercentage` instead. Each subject branch then generated
its complete character, local ground, shadow, vegetation, and occlusion inside
the actual physical card region. No mask, box, silhouette, guide pixels, or
post-decode composite entered the graph.

| Candidate | Runtime on Metal/MPS | Raw SHA-256 | Workflow SHA-256 | Result |
| --- | ---: | --- | --- | --- |
| 50% spatial cast, 1 MP | `196.25 s` | `4ebcae043ffb2aead8cbd23e386c40ac5378168d5038337228f63f6cfe099ae2` | `d651828050d2b10abc334bfb7783f6b62ab8d26d4105cc6c23998a9957411878` | Count, identity, and fit pass; depth remains inconclusive; closed |
| Full-context regional masks, 0.25 MP | `169.67 s` | `25451dc72f5b3ed6c55b433f3b43070e950140d4ee13eb4cd3914cf93044ca3a` | `28d0a50398d7797038861280a9e3004f78616420f80a92dd779d196f2680d9b7` | Hard fail: only partial body fragments land inside the masks |
| Physical-card regional areas, 0.25 MP | `120.43 s` | `7aa3a1a4370867b06ef6e7d7ae42e84bf0237c0424aadf0f7592023898d3223c` | `513874c008320c3d144307d608e9480a46b8c22aad150121bc53ca7546d53746` | Coarse pass; earned one 1-MP confirmation |
| Physical-card regional areas, 1 MP | `123.75 s` | `d36592391d59af97a941bbe59c1f54f52a3448d3d97b8452fa2aba869a1e6051` | `6915e98ac26bdc979c42445334a4cc8d4063a5d410b85f871722c3a3e9109863` | Passes count, identity, anatomy, physical crops, padding, grounding, shadows, safe areas, and visible seam review |
| Pipeline-v6 CLI confirmation, 1 MP | `201.38 s` | `800d412c8711f2ae3e4de9afb15a7fcca7e5f08d1c26229142918d20450e25b0` | `6a2671fa3710c625f7240a874a494565518c509b2a2349803919acc1631666cd` | The production prepare → workflow → Metal/MPS sampling → 300-dpi finalization path passes internal preflight; generation fingerprint `78e67a9c93a2be5b5511ee39f5c076b7100602efd289cc49504c04aa4221b8e1` |

The 1-MP candidate contains complete Treecko, Torchic, and Mudkip in the
correct cards with no visible regional boundaries or pasted-layer appearance.
No connected plant changes arbitrarily from behind to in front. Vegetation
mostly avoids direct subject intersections, so this result removes the known
contradiction but does not yet prove reliable foreground occlusion across
different scenes. It is the leading Generation III depth-bias evaluation
candidate. The user approved it on 2026-07-30; it was then promoted
transactionally as the first `regional_identity_joint` pipeline-v6 asset with
the recorded raw, print, prompt, workflow, reference, and source hashes.

## Base1 / FLUX.2 Klein rollout

The first representative rollout of the promoted Generation VII graph keeps
the exact v5 `joint_scene` topology and changes only the scope inputs: seed
`260726503`, the Base Set scene brief, the reviewed Mewtwo/Bulbasaur/Charmander
sources, and their physical card placement. Candidate `00001` was reviewed and
promoted on 2026-07-29; the later prompt-only `00002` failure never changed the
production prompt or active candidate.

| Candidate | Pipeline change | Result | Decision |
| --- | --- | --- | --- |
| `joint_scene/00001` | Apply the reviewed `00018` graph to `Base1`, including the canonical placement profile and additional Mewtwo anatomy/padding constraints | All three subjects remain complete inside their physical cards with useful padding, coherent ground contact, and directionally consistent shadows. Mewtwo retains the defining head, hand, chest, and tail anatomy within the accepted one-shot detail tolerance. The landscape does not intersect a subject, so difficult foreground continuity remains unproven | Accepted and promoted on 2026-07-29 as the second `joint_scene` scope |
| `joint_scene/00002` | Keep the `00001` seed, model, graph, references, geometry, sampler, Mewtwo notes, one-shot paragraph, scene/depth paragraph, safe areas, and exclusions byte-identical; consolidate only repeated spatial, identity, count, and bounds prose | The intended three bottom subjects remain visible, but the model adds a fourth subject behind Bulbasaur: an oversized, upright, cat-eared Mewtwo-like mutation. This violates both exact count and identity before print processing | Rejected; no production prompt change |

The MPS render completed in 201.83 seconds. Reproducibility evidence:

| Artifact | SHA-256 |
| --- | --- |
| Raw 848 × 1168 candidate | `105efc287a5687bd028ec07bfa90ff516df434db3831c46fb47fbca81b041da2` |
| Text-free 2368 × 3268 print raster at 300 dpi | `dc5a1773c8f135d2f9b6adb9468cbda3a710bbbcc2936059cc5b29ca58fa08ea` |
| Effective prompt | `63f7b1a2a24c53f070446cf442161a6affcca6212c8276cf6603aff1e7b302ea` |
| ComfyUI API workflow | `890ff01dce52370b42c29d38e26407b522a9881c4c67e30315093e9349b51561` |

The complete generation fingerprint is:

```text
d26549018a20003c0cb961cb5ab76f256c76872114deff3d34db04a17d7ec70a
```

Promotion binds the raw and text-free print hashes above to an explicit
joint-scene visual review, nine 300-dpi physical card crops, and the stable
`poster-flux2*` PDF assets. A German test PDF with poster enabled rendered
successfully after promotion.

### Prompt complexity audit

The saved `00001` provenance snapshot contains 947 whitespace-delimited words,
6,340 bytes including its final newline, and 1,300 Qwen tokens. Its decorative
snapshot heading is not sent to the model. The actual workflow prompt contains
941 words, 6,299 bytes, and 1,286 tokens; the exact ComfyUI Klein chat template
raises the effective model input to 1,298 tokens. ComfyUI does not truncate this
input, but it is substantially above the nominal 512-token FLUX.2 conditioning
budget. The 512-token boundary falls inside the Mewtwo-specific paragraph; the
one-shot integration, depth, and safe-area rules follow later.

The length is not caused by one unavoidable requirement. The effective prompt
defines the spatial authority twice, the identity authority three times, and
repeats count, bounds, padding, and no-composite constraints in multiple
sections. Those repetitions can compete with the late scene and depth
instructions even though this particular render succeeds.

The reviewed candidate remains the immutable comparison baseline. The bounded
A/B was defined before changing any production prompt:

- Change only repeated spatial-authority, identity-authority, count, and bounds
  prose.
- Keep byte-identical: Mewtwo-specific anatomy and padding, the Base Set scene
  brief, single-pass synthesis, depth behavior, safe areas, and the concrete
  exclusion list.
- Do not target the earlier 510-token form. Candidate `00020` combined
  aggressive compression with a depth-rule change and failed the exact-count
  gate, so it cannot establish a safe minimal prompt.
- Use the same seed, model, references, geometry, and sampler. A compact form
  may replace the current wording only after side-by-side identity, card-fit,
  grounding, depth, and count review.

Candidate `00002` performs the conservative A/B with the exact same non-prompt
inputs as `00001`. It reduces the actual model prompt from 1,286 to 995 Qwen
tokens, or 22.6 percent; the complete chat-templated input falls from 1,298 to
1,007 tokens. Despite retaining every requirement class and leaving the
Mewtwo-specific, one-shot, scene/depth, safe-area, and exclusion paragraphs
unchanged, it repeats the same structural failure class as the earlier
aggressive `00020`: a duplicate fourth subject.

The MPS render completed in 205.29 seconds. Candidate evidence:

| Artifact | SHA-256 |
| --- | --- |
| Raw 848 × 1168 candidate | `c2797654d6eac5268b6c40503127cddcd5c6433a3625164b10df93b0caaf7934` |
| 995-token model prompt | `a3094cddb5ca1e768caca6e92c83b58816b89b2603e2a7dc689f464b6c980ec8` |
| ComfyUI API workflow | `dda583199798d5775fa93e086f33d04f72a3d10272940d42c1e5500be8e34c58` |

No print raster, overlays, or card slices were produced after the hard gate
failed. The exact `00001` prompt remains the Base1 comparison baseline. Prompt
deduplication is closed rather than followed by more near-identical variants:
for this four-reference conditioning topology, the apparently redundant count
and authority wording is behaviorally significant.

## ExGen3 Mega / FLUX.2 Klein rollout

The first `joint_scene` candidate uses seed `260751034`, the unchanged reviewed
prompt builder and graph, the highland-basin scene brief, and exact Official
Artwork form references for Mega Latias, Mega Diancie, and Mega Lucario.

| Candidate | Pipeline change | Result | Decision |
| --- | --- | --- | --- |
| `joint_scene/00001` | Apply the promoted v5 graph to the aggregate Mega section without subject-specific prompt exceptions | Exactly the three named Mega forms appear once. Their defining silhouettes, Mega-form appendages, crystal/ribbon structures, colors, markings, and poses remain within the accepted one-shot detail tolerance. All three physical card crops pass; the shared wall, terrain, lighting, and shadows are coherent | Accepted and promoted on 2026-07-29 as the third `joint_scene` scope |

The stone wall remains behind all three subjects and the nearest grass stays
clear of their defining silhouettes. The result contains no contradictory
depth transition, but it does not prove a connected natural foreground
intersection. As with the first two promotions, open terrain is accepted over a
forced or inconsistent crossing.

The MPS render completed in 197.38 seconds. Reproducibility evidence:

| Artifact | SHA-256 |
| --- | --- |
| Raw 848 × 1168 candidate | `7d3ecebc6e1eaec5a55869da011459265bae350ef3a94a191c7a77bf1ac4259b` |
| Text-free 2368 × 3268 print raster at 300 dpi | `65bfabaf28dc711a907f7b692a7d26f75d85076374e24ee31c0ebc6367167dd4` |
| Prompt snapshot | `62313ccf86f596d9871d23fcb7384d947eb2893318f3080333379adb38ec062f` |
| ComfyUI API workflow | `694105167526465b00b5d8eda10a29c6293b3d5b1b6d736a91bc74a274969d91` |

The complete generation fingerprint is:

```text
099b69bd95a6b6a16e1f57e941b136c69acef484c6db6bd077076314f9005216
```

## ExGen3 Normal / FLUX.2 Klein rollout

The representative proportional-diversity test uses seed `260711318`, the
unchanged v5 graph and prompt builder, the Paldea valley brief, and Koraidon,
Pikachu, and Miraidon. It deliberately combines two large complex bodies with
one small compact subject.

| Candidate | Pipeline change | Result | Decision |
| --- | --- | --- | --- |
| `joint_scene/00001` | Apply the promoted graph to the non-Mega ExGen3 section without subject-specific prompt exceptions | Exactly three subjects appear. Pikachu remains intentionally smaller while Koraidon and Miraidon retain their defining crests, segmented chest/body structures, limbs, tails, colors, and markings within the accepted print-detail tolerance. All physical card crops pass and the cast shares coherent light and shadows | Accepted and promoted on 2026-07-29 as the fourth `joint_scene` scope |

Foreground plants frame the outer card edges without producing a contradictory
intersection. As in the other accepted candidates, the result proves that the
graph can preserve very different proportions and card fill, but not that it
can reliably create connected natural foreground crossings.

The MPS render completed in 181.15 seconds. Reproducibility evidence:

| Artifact | SHA-256 |
| --- | --- |
| Raw 848 × 1168 candidate | `f53c44c20905886a95cd6a0a54a6731b6209bfd5f73bbb7c006382acd9206fae` |
| Text-free 2368 × 3268 print raster at 300 dpi | `5ed638ed90f00ca24120cbc6138bb20206e641f29ccec2ae92c241f1a4cf38b3` |
| Prompt snapshot | `29519877d8a1ac56f4994a156b74d2e8432fe3210945a6b1613e9df17d127aeb` |
| ComfyUI API workflow | `4988865cc16b8fe2530dc00e5863b5e95bdbb359523dc43e26cd776b157e7ec1` |

The complete generation fingerprint is:

```text
133603d3b0ed6ec6b8fea273ff74dfba1893b8112424099bea786d8ee5d69955
```

## Generation VII / FLUX.2 Klein

All candidates below use seed `260726054` and the `standard_3x3` layout. They
remain local review artifacts unless a later entry explicitly records
promotion.

| Candidate | Pipeline change | Result | Decision |
| --- | --- | --- | --- |
| `00003` | Early joint-scene experiment biased by a flat combined draft | Characters read as a layer placed over the landscape | Rejected |
| `00004` | Independent final latent with three identity references and one subject-free landscape reference | Strong identity and integration; Litten and Popplio crossed card boundaries | Rejected |
| `00005` | Smaller source figures inside the identity-reference canvases | Popplio gained an invented orange head detail | Rejected; source-detail reduction reverted |
| `00006` | Larger identity-reference canvases while retaining the landscape reference | Black output under unified-memory pressure | Rejected |
| `00007`–`00012` | Conservative normalized bounds and outward placement tuning | Card placement improved, but connected plants still switched inconsistently between foreground and background around Rowlet and Popplio | Rejected; landscape reference identified as the remaining structural bias |
| `00013` | Pipeline v3: one empty target, one sampler, three identity references, no landscape image | Coherent landscape depth; an over-specific generic prompt list invented a flame on Litten's tail | Rejected; feature-name list removed |
| `00014` | Reference-neutral identity wording | Coherent depth and faithful character designs | Rejected because all three characters extend above their bottom-row cards |
| `00015` | Same v3 graph with 768 px neutral identity canvases instead of 512 px | Placement remained too high and too large; render cost increased | Rejected; 512 px default restored |
| `00016` | Pipeline v4: replace the three global identity references with one neutral, poster-shaped cast layout containing the exact source figures inside their cards | All figures fit their real card crops with padding and the scene has coherent shadows/depth; Litten gains a large pale flank/hindquarter marking absent from the source | Rejected; third one-shot placement attempt fails identity and triggers the stop rule |
| `00017` | Pipeline v5: 0.5-MP spatial cast followed by three unscaled 512 px source-identity references before the same single sampler | All three subjects fit their cards and the scene contains no contradictory intersections, but plants avoid the silhouettes and therefore prove no real foreground crossing. Litten's front-paw digit structure is simplified, Popplio's eye and two muzzle strokes are reduced, and Rowlet lacks a convincing individual contact shadow | Retained as the second-ranked comparison after the identity tolerance was explicitly relaxed; placement is still too small and too far outward |
| `00018` | Reuse the exact canonical `identity_lock` placement profile; model, seed, scene wording, reference topology, identity images, and sampler remain fixed | All three subjects now have nearly the preferred card fill, remain complete inside their physical card crops, and receive clear directionally coherent grounding shadows. No gross identity regression beyond the accepted v5 print-detail tolerance is apparent. Plants again avoid the silhouettes, so true foreground continuity remains unproven | Accepted and promoted on 2026-07-29 as the first `joint_scene` default |
| `00019` | Add an explicit prompt-only stress rule requiring connected front and rear landscape crossings in every occupied bottom card; all non-prompt inputs remain byte-identical to `00018` | Card fit, accepted identity tolerance, and shadows still pass. Rowlet, Litten, and Popplio each have zero actual foreground crossings and zero connected rear elements visibly interrupted by the character. There is no contradictory z-order because the model avoids every requested intersection | Fails as depth evidence; `00018` remains the preferred v5 placement checkpoint |
| `00020` | Compact the effective prompt to 510 Qwen tokens including its chat template, move the depth rule to token 211, and request front/rear crossings in exactly one suitable bottom card; all image, model, geometry, seed, and sampling inputs remain fixed | The intended bottom cast stays recognizable, but the model renders a fourth character: a second, oversized Litten in the middle of the poster. No requested connected front/rear crossing is present | Rejected on hard character-count failure; prompt tuning closed and both experimental prompt changes reverted |

## Current checkpoint

The v3/v4 attempt budget is closed: `00014` and `00015` fail card containment;
`00016` passes containment by violating identity. The later v5
Spatial+Identity architecture is now the accepted default:

1. Create one empty 1-MP FLUX.2 target latent.
2. Condition it first with one neutral 0.5-MP poster-shaped cast reference as
   the sole authority for count, pose, scale, baseline, and card position.
3. Condition it next with one neutral 512 px identity reference per subject.
   Each contains the original 475 × 475 cutout without resampling and is the
   sole authority for anatomy, face, silhouette, colors, and markings.
4. Sample and decode exactly once.
5. Apply only deterministic Lanczos resizing and deterministic text/logo
   overlays after the text-free artwork review.

There is no pre-generated landscape reference, inpaint reference, second
sampler, final character composite, learned post-upscaler, or source-pixel
restoration in this mode. Candidate `00017` proves the v5 graph topology while
still redrawing print-scale facial and paw details. The product review on
2026-07-28 accepted those small simplifications for continued evaluation; a
changed defining feature, body-part count, silhouette, marking, or form still
fails. The later visual review on 2026-07-29 prefers `00018` over the composited
appearance of `identity_lock`. Candidate `00018` was then promoted with its
complete generation fingerprint and explicit raw/print visual approval.
`identity_lock` remains the exact-source fallback.

Candidate `00018` changes only the canonical spatial placement profile. It
delegates to the already accepted `identity_lock` placement helper instead of
maintaining separate shrink, lower-baseline, and outer-shift parameters. The
result passes physical card containment and preferred-fill review without a
new gross identity regression. Its raw SHA-256 is
`fc1375f75ef771d6f1aac05bcd27ef67288597bdf3dd8d2f4baf60a908db5e98`;
the MPS render completed in 180.43 seconds. Because no plant, leaf, flower, or
other connected landscape element actually crosses a subject, `00018` does
not prove foreground continuity. The subsequent `00019` candidate therefore
changes only the generic foreground-depth wording. It inherited neither
promotion nor approval from this placement result.

Candidate `00019` applies that isolated wording change. Its raw SHA-256 is
`2fa1b35df5f240e5396de7c8a3faeb3e41dcd516f86de6c7be8719de04b4832a`;
the MPS render completed in 180.20 seconds. Independent review confirms that
all three physical card crops retain the `00018` fit and accepted identity
tolerance, but not one requested front or rear crossing exists. A tokenizer
audit justified one final bounded retry: the actual
prompt contains 1,350 Qwen tokens and places the explicit stress rule after
token 1,034. ComfyUI does not truncate it, but the official FLUX.2
conditioning budget is 512 tokens.

Candidate `00020` performs that final bounded retry at 510 tokens, with the
depth rule at token 211. Its raw SHA-256 is
`610499556249a965cac52ea3ecea54fd206dd71487185fc967054282df31431c`;
the MPS render completed in 174.18 seconds. It does not produce a controlled
crossing and instead violates the hard count gate by adding a second, oversized
Litten above the intended bottom cast. The compact-prompt refactor and the
preceding stress wording are reverted in dedicated commits, returning the code
exactly to the `00018` prompt behavior. Prompt-only depth tuning is closed:
`00018` is the visually preferred candidate, `identity_lock` remains the
exact-source fallback, and any successor now requires a materially different
control mechanism.

### Anima empty-target preflight

The existing Anima adapter was evaluated without changing either FLUX.2
workflow. The Generation VII preflight uses the same seed `260726054`, reviewed
Rowlet/Litten/Popplio positions, and Alola brief at 432 × 592 px (0.25 MP).
`AnimaYume_tuned_v05`, `AnimaEditV1`, 22 `er_sde`/simple steps, CFG 3.4, and
Cosmos reference conditioning completed on Metal/MPS in 165.57 seconds. The raw
SHA-256 is
`a4ff08c593f385b8d37ce4c0311c36f152a3702efee591d028edcd207fd53922`.

All three subjects are complete and card-safe, but they remain visibly isolated
on a broad flat lawn. There are no convincing contact or cast shadows, local
terrain responses, foreground overlaps, or occlusions. The raw source audit
also records 1,680 changed pixels among 9,461 fully opaque reference pixels.
More importantly, the graph composites an eroded exact identity core back over
the decoded result. It therefore samples from an empty latent but is not a
single unified final synthesis under the joint-scene requirement. A 1-MP retry
cannot remove that structural limitation and is not justified. The adapter was
removed from the production runtime during the 2026-07-29 KISS cleanup;
its evidence remains here and in Git history. `00018` remains decisively
preferred.

## Identity-control successor evaluation

The earlier product decision on 2026-07-28 selected a materially stronger,
object-reference control mechanism without relaxing the then-current hard
gates. That successor search remains closed under its recorded results. The
later explicit review tolerance for v5 `00017` reopens only the FLUX.2
placement and occlusion questions described above; it does not reopen SDXL,
DreamO, Qwen, prompt-only identity tuning, or reference-canvas tuning.

### Frozen comparison fixture

| Input | Frozen value |
| --- | --- |
| Scope | `Pokedex/sections/gen7` |
| Layout | `standard_3x3` with the real physical card raster |
| Seed | `260726054` |
| Subjects | Reviewed Rowlet, Litten, and Popplio Official Artwork cutouts |
| Scene | Existing Alola scene brief from the promoted scope manifest |
| Target | One text-free joint scene; deterministic print resize and overlays remain outside model evaluation |
| Production effect | None until a candidate passes every hard gate and is promoted explicitly |

### Successor matrix

| Candidate family | Material change | Result or next gate |
| --- | --- | --- |
| `sdxl_identity` | SDXL plus one identity adapter per subject, regional masks, and source-derived structural control | Closed after whole-card, exact-silhouette, and tight-box masks all fail identity, grounding, and scene quality |
| `sdxl_identity_pokemon` | Same graph plus one Pokémon domain LoRA | Not rendered: the base graph fails reference binding and anatomy too broadly for a domain/style A/B to isolate |
| `ms_diffusion` | SDXL multi-subject adapter with explicit reference-to-box assignment | Stopped at technical preflight: the available ComfyUI port hides its own Diffusers sampler and requires a substantial MPS/audit refactor |
| `dreamo` | FLUX.1-dev plus three VAE-based DreamO object references before one common sampler | Closed after preflight B binds only two redesigned subjects, omits the third, and misses the fixed card bounds |
| `flux2_refcontrol` | FLUX.2 Klein 4B Base reference-plus-depth control | Stopped at contract preflight: one reference input cannot independently bind three subjects to three boxes |

The intended generic/Pokémon-assisted SDXL A/B was conditional on a viable base
graph. That condition is false, so no Pokémon LoRA is added to a broken
regional binding path. Every later family is evaluated as a new architecture
against the same frozen fixture and hard gates rather than compared as a
single-variable model swap.

### SDXL implementation checkpoint

The first isolated SDXL graph is implemented but not yet visually accepted or
connected to the production runner. It prepares a full-resolution
source-derived structure guide, one exact source identity image per Pokémon,
and initially one invisible regional mask per physical bottom-row card. The
generated ComfyUI graph contains one empty target, three region-bound
IP-Adapter conditions, one shared structural ControlNet condition, one
sampler, and one decode. It contains no background plate, image-to-image
target, inpaint stage, post-decode character composite, or source-pixel
restoration.

The generic graph and its optional Pokémon-LoRA variant differ only at the
single model-LoRA edge. The existing production engine registry, runner,
promotion, manifest, PDF routing, and promoted artwork remain unchanged.
All 163 poster-asset tests pass after this checkpoint. Visual identity,
containment, grounding, and occlusion remain untested until the first local
model render is recorded below.

### SDXL pre-render review checkpoint

A parallel KISS review verified the installed ComfyUI node schemas and found no
production-path changes, but identified that the initial graph reused an
834-word FLUX/Qwen prompt. SDXL's CLIP conditioning should not carry that much
duplicated geometry prose, because the regional masks and structural
ControlNet already own placement. The next workflow snapshot therefore uses a
dedicated 362-word SDXL prompt containing only the scene, named regional cast,
identity invariants, empty-target contract, coherent depth rule, safe areas,
and exclusions. Generic and Pokémon-assisted output prefixes are also explicit
so their artifacts cannot be confused.

The review deliberately leaves the full source-derived Canny guide and hard
per-card masks unchanged until candidate `sdxl_identity/00001` shows whether
they actually cause rigid cutout edges or vertical conditioning seams. These
are visual hypotheses, not reasons to add feathering or another control stage
preemptively. The complete repository test suite passes with 518 tests and one
expected skip.

The first runtime preflight used the 2.5-GB Xinsir Union-ControlNet on the
16-GB M4. ComfyUI remained on Metal and did not report an out-of-memory error
or CPU fallback, but completed only 5 of 30 sampler steps in 11 minutes 15
seconds, with the running estimate exceeding one hour. It was interrupted
before decode and produced no candidate image. This is an operational
rejection, not a visual identity result. The next graph replaces only that
oversized structural model with the official 545-MB FP16 SDXL Canny-mid
ControlNet. The source guide, regional identity adapters, empty target, seed,
resolution, sampler family, and one-pass contract remain unchanged.

### SDXL candidate record

| Candidate | Single changed variable | Runtime and automatic result | Visual result | Decision |
| --- | --- | --- | --- | --- |
| `sdxl_identity/00001` | Replace the rejected Union-ControlNet preflight with SDXL Canny-mid; the effective CLI strength is `0.72` | `253.74 s`; Metal/MPS; one empty target, sampler, and decode; no post-decode composite | Upper scene is a plausible Alola landscape, but the complete bottom row becomes a flat beige strip. All three Pokémon are tiny and visibly redesigned; Litten is severely malformed. No believable ground contact or scene integration remains | Rejected |
| `sdxl_identity/00002` | Keep the effective `00001` graph, including strength `0.72`, fixed and restrict each IP-Adapter mask from its complete card to the exact placed source silhouette | `255.50 s`; Metal/MPS; same one-pass graph and workflow bytes as `00001` | The beige bottom-row seam disappears, but the whole landscape collapses into blurred, segmented color fields. Rowlet is simplified, Litten becomes an unrecognizable red floating body, and Popplio's face and anatomy change. None has credible ground contact | Rejected |
| `sdxl_identity/00003` | Keep `00002` fixed and replace each sparse alpha mask with its tight, continuous visible-subject bounding box | `282.13 s`; Metal/MPS; same one-pass graph and workflow bytes | The scene remains blurred and heavily color-segmented. All subjects are undersized and floating; Rowlet and Popplio lose canonical details, while Litten remains unrecognizable | Rejected; close generic SDXL regional-mask family |

Candidate `00001` strongly indicates the pre-render review risk: a hard
whole-card identity mask does not merely bind a subject to a card. Together
with the neutral identity reference, it appears to condition the card
background itself and creates the exact horizontal seam at the top of the
bottom row. This points to a control-scope failure, not evidence that the scene
prompt needs more detail. The next attempt therefore changes only the masks.
It does not add feathering, another sampler, inpainting, source compositing, or
new prompt clauses.

The mask-only `00002` result confirms that the whole-card conditioning caused
the beige strip: changing only the three mask images removes that exact
boundary. It also shows that exact alpha silhouettes are too sparse for this
regional attention path. They do not retain canonical anatomy and destabilize
the global image despite unchanged structure, prompt, seed, model, and sampler.
This is still a control-scope failure; neither result justifies prompt tuning.
Candidate `00003` tests the simplest midpoint supported by the same node: one
continuous tight region around each visible subject. It adds no padding,
feathering, model, node, or sampler. If canonical identity still fails, the
generic SDXL regional architecture stops rather than adding mask heuristics.

`00003` fails that identity gate by a wide margin and does not recover the
scene. Whole-card, exact-silhouette, and tight-box regions are now three
materially distinct attempts with the same hard-gate failure. Further mask,
weight, prompt, or ControlNet-strength tuning on this generic SDXL regional
graph is closed. The planned public Pokémon-domain-LoRA A/B is not run on a
base graph that already fails subject binding, anatomy, global scene quality,
and ground contact; a domain/style prior cannot isolate which reference owns
which non-human body.

The `00001` snapshot also exposed a configuration drift: the Python workflow
default had already been changed to the Canny-mid recommendation `0.5`, while
the CLI parser still supplied `0.72`. The parser is corrected for future
experiments. Candidate `00002` explicitly keeps `0.72` so its direct comparison
with `00001` changes only the mask pixels; a later `0.5` run would be a
separate candidate.

The exact `00002` preparation command is:

```text
python scripts/poster_assets/create_sdxl_identity_poster_workflow.py \
  --scope Pokedex/sections/gen7 --seed 260726054 --megapixels 1.0 \
  --controlnet-strength 0.72
```

Its three subject-mask SHA-256 values are
`cdc1aeb492aeb5400a61cd4d15b1becb0f95108591127090b11db8620975fc9c`,
`c413d9a56dd33f9b80de3949859542603218013559a4edc6d178d1577c29060f`,
and `13b6fc73075878b81ee9d3125fce31ab6e780b8b8f2bee9aa71af78e9823cf0c`.
Both candidate workflow snapshots remain byte-identical at SHA-256
`5989dcfb41b0bd0dd92419ca0a84d35230bcc7e2484f7c5c7232c740f03d8556`;
only those three input images change.

The `00001` evidence is reproducible from:

- workflow SHA-256
  `5989dcfb41b0bd0dd92419ca0a84d35230bcc7e2484f7c5c7232c740f03d8556`;
- raw `848 × 1168` artwork SHA-256
  `f43d62a9f92fb0e9948399434f5710f46ab7cbfda2956848e1c2c43d23700c10`;
- deterministic `2368 × 3268` 300-dpi print resize SHA-256
  `03aa35e1c2d2a9d4cc62ba17317e4783a936653b714bc5df6c913448065b7439`;
- nine deterministic `750 × 1050` card crops below
  `data/poster_assets/Pokedex/sections/gen7/comfyui_poster/output/`
  `sdxl_identity_generic_00001_cards/`.

The local model fingerprint for this comparison is SDXL Base
`31e35c80…f7e5b`, CLIP Vision `6ca9667d…7b030`, IP-Adapter Plus SDXL
`3f5062b8…e6581`, and Canny-mid `15d4d3dd…b844fe`. The IP-Adapter custom node
is pinned to commit `b188a6cb39b512a9c6da7235b880af42c78ccd0d`. The
print artifact is a deterministic resize of the reviewed model output, not a
second generative or learned upscaling pass.

The rejected `00002` raw artwork SHA-256 is
`4d1172e6ec97e926236f689a7ef8fc97bee58186b69be331b80df29067209d2a`.
Its deterministic 300-dpi print resize is
`f76125b162d984535f082c35a74fcb4835ab228ddf84f7a88f2593e14ed8ba4a`;
the nine review crops are below
`data/poster_assets/Pokedex/sections/gen7/comfyui_poster/output/`
`sdxl_identity_generic_00002_cards/`.

The rejected `00003` evidence uses the unchanged workflow SHA-256
`5989dcfb41b0bd0dd92419ca0a84d35230bcc7e2484f7c5c7232c740f03d8556`
and subject-region SHA-256 values
`b951b8d0fa4e7317001e59940b6a2be383e5163eba4fea847d18f3364d0091fe`,
`6910097bc0962463dc8776cfb1be5fbaf8b0ebf8386a81b6a8501322db4fa08f`,
and `c582e3672cc9fbe718b3240ead67be26a5cbcf6346bdda51c9efc039a3f39b8a`.
Its raw artwork SHA-256 is
`a3b14362bebf378b182d50606e98f02942e975816cd7f9c8dbba68a5d705ed43`;
the deterministic 300-dpi print resize is
`221d071df8027ccb80bd0005f0e09e36e9d890f8635560ecac3dcee3ce2a3144`.
The nine review crops are below
`data/poster_assets/Pokedex/sections/gen7/comfyui_poster/output/`
`sdxl_identity_generic_00003_cards/`.

### Successor technical preflight

The next architecture review starts before downloading another multi-gigabyte
model. [MS-Diffusion](https://github.com/MS-Diffusion/MS-Diffusion) is
conceptually attractive because it assigns multiple image references to
explicit target boxes. The reviewed
[ComfyUI port](https://github.com/smthemex/ComfyUI_MS_Diffusion) at commit
`a5b97bb7cea2ad31d471ed51bb54f210a183ea82` does not expose that mechanism as a
normal Comfy model condition, however. Its loader constructs a complete
Diffusers `StableDiffusionXLPipeline`, unconditionally enables xFormers, and
contains CUDA-only cache calls. Its sampler performs diffusion internally and
returns an `IMAGE`, so the repository cannot statically verify one shared empty
target, one final sampler, and one decode.

Removing those assumptions and converting the hidden pipeline into auditable
Comfy model/conditioning nodes would be a substantial fork. That contradicts
the KISS boundary selected for this experiment, so `ms_diffusion` stops at
technical preflight without installing its adapter or rendering a candidate.
This is an integration rejection of the available port, not evidence against
the published architecture itself.

[DreamO v1.1](https://github.com/bytedance/DreamO) is selected next. The
reviewed
[native ComfyUI integration](https://github.com/ToTheBeginning/ComfyUI-DreamO)
at commit `622f393a13b9e083ab3945d7534b8b3fe38d609e` exposes three optional
reference latents, applies them to a normal FLUX model, and leaves the final
sampling and decode visible in the graph. The upstream project documents
Apple M1-M4/MPS operation and object/animal identity conditioning. The first
candidate therefore has this fixed contract:

1. three separate reviewed Official Artwork references, in left-to-right card
   order;
2. one empty target at the existing Generation VII fixture geometry;
3. one shared scene prompt and one final sampler/decode;
4. no target image encoding, inpainting, character composite, source-pixel
   restoration, or second generative pass;
5. a low-resolution MPS technical preflight before a 1-MP visual candidate;
6. at most one higher-reference-resolution follow-up, and only when the first
   result already passes count, binding, coarse anatomy, and placement.

DreamO is still an experiment, not a new production engine. Its lack of an
explicit three-box input is a known risk: natural-language left/center/right
placement must pass the unchanged physical card-containment gate before any
identity-detail tuning is justified. The accepted `identity_lock` artwork,
manifests, PDF routing, and release inputs remain unchanged.

#### DreamO installation and MPS preflight A

The local installation is pinned rather than following moving upstream heads:
ComfyUI `87d23b81765161624889febfb3b81f19f3c8435b`,
ComfyUI-GGUF `6ea2651e7df66d7585f6ffee804b20e92fb38b8a`,
ComfyUI-DreamO `622f393a13b9e083ab3945d7534b8b3fe38d609e`, and the
DreamO facexlib fork
`5e6c76170f8a9f9c5b4df62d8679f4f769230383`. The graph uses
FLUX.1-dev Q4_K_S
`75bb19459b5240c9f373b5af527584af15b675867fa142efadf7478d6abbf62b`,
then the official v1.1 LoRA chain:

| Model | SHA-256 |
| --- | --- |
| FLUX Turbo | `77f7523a5e9c3da6cfc730c6b07461129fa52997ea06168e9ed5312228aa0bff` |
| DreamO base | `27f01aed81d0c6d4549309ec5ca0d5c96eef6f76cb47bdb370645780f304b90a` |
| DreamO CFG distill | `dc7cb5b503829ab6ab765cf07abf972cef65d5c11bd04de1d17f1f4f0fae2c80` |
| DreamO SFT | `596ce2e45175b07553c7f7051ced1ae940ec2860258e9232385974504f056c54` |
| DreamO DPO | `e66b08922bbfdb0eb15e790160c2709ba5693c1ee59808e48e5cbb9d0d467551` |

The closed SDXL experiment's base checkpoint, CLIP Vision, IP-Adapter, and two
ControlNets were hash-checked against their existing log before deletion.
Their recorded total is 13,371,197,431 bytes (about 12.45 GiB); no production
model is touched.

The first unchanged 0.25-MP graph reached the sampler only after a bounded
compatibility patch forwarded ComfyUI's new `latent_shapes` keyword through
DreamO's outer sampler wrapper. No model logic, conditioning, or sampler
parameter changed. It then completed on Metal/MPS in 11:34 with 12 Euler/simple
steps, CFG 1, guidance 4.5, one empty 432×592 target, one sampler, and one
decode. Workflow SHA-256 before the prompt diagnostic was
`beb2349e78b18ee215ba2d948aa9d849a3aa95f97dbbeb08991a90cd6f236860`.

The raw preflight image SHA-256 is
`46d8020099dff811ce0ade71c8eed3873c5d927bf4f04bdcce3e9f500893dffa`.
It renders a coherent Alola landscape but omits Rowlet, Litten, and Popplio
entirely, so it is not candidate `dreamo/00001` and no upscale, card crops, or
promotion evidence is produced. A cheap diagnostic saved DreamO's own
post-BEN2 reference outputs; all three remain complete and recognizable. The
binding failure is therefore downstream of reference preparation.

The only next variable is prompt conditioning. The preflight prompt contained
765 T5 tokens, beyond the tokenizer's declared 512-token envelope, while the
first pooled 77-token CLIP chunk contained scenery but none of the Pokémon.
The compact replacement puts all three reference/name/card assignments in
that first CLIP chunk and measures 501 T5 tokens for this scope. Its workflow
SHA-256 is
`ab0781ac2b47f8ab2a1e377255ccf8cdb74a3533e1acf1d8eee7c292c4a2bb51`.
The same seed, resolution, references, model chain, sampler, and scene contract
remain fixed for preflight B. Only if subjects appear does DreamO earn a 1-MP
visual candidate.

Preflight B completed on Metal/MPS in 10:11. Its raw output SHA-256 is
`6e027309f1e46bce0b21c40a1fc7d79bf12e00b5bca60dc34c51a5146ad8abb1`.
The compact prompt changes binding, proving that the first result was not
solely an empty-reference failure: Rowlet and Litten now appear. Both are
substantially redesigned, oversized, and outside their target silhouettes;
Popplio is absent. Rowlet gains a costume-like head outline and altered body,
while Litten gains a white chest/muzzle design and altered markings and
proportions. Count, identity/anatomy, and card containment therefore all fail
before detailed grounding review.

DreamO receives no 1-MP candidate. Raising resolution cannot supply the missing
explicit reference-to-box control, and it is not justified while coarse count,
identity, and placement already fail. Adding masks, per-subject passes, or a
post-decode restoration would reintroduce the layered architecture this
experiment is intended to replace. The pinned graph and prompt builder remain
available as reproducible negative evidence, but `identity_lock` remains the
production engine.

#### Selected Qwen spatial-subject preflight

No new model is downloaded for the next bounded experiment. The existing
Qwen-Image-Edit-2511 candidate had a concrete input-topology defect: its first
image already contained all three positioned subjects, then Mewtwo appeared
again on one detail sheet while Bulbasaur and Charmander appeared again on a
second sheet. The model therefore saw the same cast both as composition and as
additional image content. Its giant fourth Mewtwo is consistent with that
ambiguity and does not isolate Qwen's actual three-subject binding ability.

The replacement changes only that topology:

1. exactly three poster-shaped neutral reference images are supplied;
2. each image contains exactly one reviewed source subject, once, at that
   subject's normalized final bottom-card position and scale;
3. no subject appears in any other input image;
4. one empty target, one common sampler, and one decode generate the complete
   landscape and cast together;
5. there is no background plate, structure image, inpaint target, mask,
   post-decode composite, source restoration, or second generative pass.

This is an isolated `qwen_spatial_subjects` preflight, not a production-engine
change. The accepted artwork, manifest, PDF routing, and promotion state remain
untouched. It reuses the already installed Qwen model, encoder, VAE, Lightning
LoRA, fixed Generation VII seed `260726054`, and existing physical placement
geometry.

The stop rule is deliberately cheaper than another tuning branch. First run
one 0.25-MP Metal/MPS binding preflight. Stop immediately on CPU fallback,
memory failure, a missing or duplicate subject, a subject assigned to the
wrong card, or gross anatomy change. Only a preflight that binds all three
distinct subjects to the correct cards earns exactly one 1-MP candidate. A
second 1-MP run is allowed only for a genuine near-pass that already satisfies
count, placement, depth, and coarse anatomy; its sole changed variable may be
the official native non-Lightning sampling preset. Any remaining anatomy
change closes this Qwen topology.

The preparation checkpoint implements that graph without changing the existing
`qwen_edit` runner or its promotion semantics. That separation is intentional:
the current runner treats Qwen as an exact-source edit, while this experiment
is a complete unified redraw and must not inherit or weaken that source-pixel
gate before it proves useful. All three opaque references use the canonical
`848 × 1168` 1-MP poster canvas even for the 0.25-MP target. Qwen normalizes
every reference to roughly 1 MP internally, so preparing a smaller reference
would discard identity detail without reducing that conditioning cost.

The prepared Generation VII evidence is:

| Input | SHA-256 |
| --- | --- |
| Rowlet spatial reference | `bb9f28900c1d91639744c4de3c61570932d9c2201697906414416381ff9cd3f1` |
| Litten spatial reference | `0b6ca1efa05c4d6421a9d361212a74edca899075c4075322c4331ae251d37733` |
| Popplio spatial reference | `11d6a6936532509b40c37530e86e768504f3b8ccc97f3d79e2b43bb6decc9010` |
| Dynamic prompt snapshot | `948e45849b8f9369a0ffc1e55513772fdd0b82b7f6b835ceac3ca09e0ecbdc32` |
| 0.25-MP API workflow | `c0aa0af2322fa1acb11f07966f7c292edbd30ebc924e3c29a4555514cd762ce8` |

The installed model contract is Qwen-Image-Edit-2511 Q3_K_M
`5631fd3a…4e9e9`, Qwen 2.5 VL 7B FP8 `cb5636d8…5c0b4`, Qwen image VAE
`a70580f0…23d1f`, and the four-step Lightning LoRA `22226e8d…a904f`.
Automated tests compare every reference pixel against exactly one expected
source placement, verify the prompt's picture/name/card order and normalized
bounds, and reject any graph containing a source VAE target, inpaint, control,
or composite node. The new focused tests and the existing poster workflow,
generation-option, and provenance suites pass together with 230 tests. The
complete repository suite passes with 536 tests and one expected skip.

The 0.25-MP preflight completed on Metal/MPS with `--lowvram` in 14:38;
four Euler/simple sampling steps took 12:45. The Qwen text encoder, VAE, and
GGUF denoiser all reported MPS loading, while macOS swap reached approximately
15.4 GiB. The resulting `432 × 592` raw image has SHA-256
`d97a81d346dd3ff07f8fa0f2d79dbd0c7987fdb0f30f8688550db932b793b797`.

The result retains the plain neutral reference field, renders one oversized
Litten across almost the complete poster, omits Rowlet and Popplio, and creates
no Alola landscape. Litten remains broadly recognizable, but count, distinct
reference binding, target scale, card containment, final-scene synthesis, and
set-specific scenery all fail at the cheapest gate. Because several coarse
hard gates fail simultaneously, neither a 1-MP run nor a prompt/sampling
follow-up is justified. The isolated topology is closed and retained only as
reproducible evidence. It did not change the then-current `identity_lock`
artwork and does not belong to the later `joint_scene` production runtime.

## Regional-v6 representative rerender audit

After Generation III regional-v6 passed visual review, every existing
spatial-v5 promotion received one 1-MP Metal/MPS candidate with the same model,
prompt builder, physical placement contract, scope seed, four-step sampler, and
empty-target topology. No candidate replaced its existing promotion.

| Scope | Candidate result | Decision |
| --- | --- | --- |
| `Base1` | Mewtwo and Bulbasaur remain close, but Charmander changes pose and detail; a generated edge frame and pseudo-signature are visible | Rejected; one new-seed retry also creates a separate lower panorama and frame |
| `ExGen3/sections/normal` | Scene integration is strong, but Miraidon's defining open tail becomes a compact loop and Koraidon loses hand detail | Rejected on anatomy |
| `ExGen3/sections/mega` | Mega Latias is cropped; Mega Lucario's chest spike and foot anatomy are malformed | Rejected on containment and anatomy |
| `Pokedex/sections/gen1` | Count, identity, card fit, shadows, and local depth pass, but a generated paper/frame strip survives into the cards | Rejected; the single seed retry creates a second lower landscape and frame |
| `Pokedex/sections/gen2` | Count, identity, card fit, and grounding pass, but a generated outer frame is visible | Rejected; the single retry splits the lower row into three framed landscapes and changes Cyndaquil/Totodile details |
| `Pokedex/sections/gen7` | Rowlet, Litten, and Popplio are highly faithful and card-safe, but a second tropical lagoon begins below a full-width horizontal scene boundary | Rejected on global perspective |

The failures exposed a deterministic topology risk. Every local branch owns a
complete bottom-card `ConditioningSetAreaPercentage`. The subsequent
`ConditioningSetDefaultCombine` marks the reference-free landscape as a
default, and ComfyUI subtracts the local multipliers from that default. The
global scene therefore has zero weight throughout the interiors of the lower
cards; the local branches independently predict their own terrain, horizon,
and foreground. Edge feathering hides some boundaries but cannot share scene
geometry.

Two same-seed Generation-I KISS tests changed only that combine behavior:

| Test | Effective regional/global mix | Result | Decision |
| --- | --- | --- | --- |
| Ordinary additive `ConditioningCombine`, strength `1.0` | 50/50 inside each subject card | One continuous landscape, but all subjects become underconditioned; Charmander turns around and defining colors/anatomy collapse | Rejected |
| Same additive graph, local strength `2.0` | 2:1 regional/global | More subject color returns, but pose/anatomy remain wrong and a lower panorama begins to reappear | Rejected; stop strength tuning |

ComfyUI computes the additive result per latent pixel as
`sum(output * strength) / sum(strength)`. Higher local strength would approach
the original independent-card behavior; lower strength already fails identity.
The additive experiment and its tests were reverted, leaving production code
byte-equivalent to regional-v6 before this audit.

Outcome:

- Generation III keeps its explicitly reviewed regional-v6 promotion.
- All six spatial-v5 promotions remain unchanged and approved.
- No rerender receives a new approval.
- Further regional-v6 seed, prompt, or strength sweeps are closed.
- A successor must bind each identity and position while retaining one shared
  full-frame scene prediction inside the subject zones; that is a new control
  mechanism, not prompt tuning.

## Individual spatial-reference successor preflight

The next bounded experiment removes both known sources of conflicting scene
geometry: the combined three-character cast image from spatial v5 and the
per-card conditioning branches from regional v6. Each subject instead receives
one neutral, poster-shaped reference containing only its supplied source
cutout at the canonical final position. All references condition one shared
text prompt and one empty full-frame FLUX.2 target through a single sampler and
decode. There are no area conditions, masks, inpainting, decoded composites, or
post-generation source restoration.

The model, encoder, VAE, four-step sampler, Generation-I seed `260782266`,
prompt contract, and physical placement profile remained fixed. The experiment
uses `flux-2-klein-4b-fp8.safetensors`
(`97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6`),
`qwen_3_4b.safetensors`
(`6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a`),
and `flux2-vae.safetensors`
(`d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5`).
Every render ran on Metal/MPS.

| Attempt | Isolated change | Result | Decision |
| --- | --- | --- | --- |
| Six references, 0.25 MP | Three 0.25-MP poster-position references plus three separate 0.25-MP identity-detail references | The `432 × 592` render completes in `195.95 s` but contains five creatures: the intended three plus an extra green biped and a second Charmander. Raw SHA-256: `ab451373bd2a2d109a9b7391e76c958eb3ef877ad10ebe55eed02d11711df495` | Hard count failure. Commit `131d0ae` retains the reproducible topology; no larger render |
| Three references, 0.25 MP | Remove the duplicate detail channel and give each subject one 0.5-MP identity-and-position reference | Exactly Bulbasaur, Charmander, and Squirtle appear once in the correct bottom cards. The landscape, contact shadows, and foreground/rear vegetation are continuous. Runtime `150.96 s`; workflow SHA-256 `e09b231268f64c1068e7ecf38338a9bd5d2e91e10adb7cd3a7012a8a65aa4f32`; raw SHA-256 `7323d0d490ea787971c6eeb9569230349a46ea6d009865b2c938b182dfedc746` | Coarse gate passes and earns one 1-MP confirmation |
| Three references, 1 MP | Keep the successful topology, seed, prompt, reference resolution, model, and sampler unchanged; enlarge only the empty target to `848 × 1168` | Exactly three recognizable starters remain complete with useful card padding. Defining anatomy, markings, poses, and silhouettes remain within the current one-shot tolerance. Foreground blades overlap Bulbasaur and Squirtle while separate rear vegetation remains behind them; shadows and terrain are jointly synthesized. Runtime `206.38 s`; workflow SHA-256 `a09f52d73f44b7a70654c6f96d37d24cf31805c108f14a9ef97427415382b182`; raw SHA-256 `cf80fd3f0a2f909bb1d58ecc7f43c015431e074ff25adb86fdf4bdee785642ae` | Agent preflight passes; user review and representative-scope validation remain required before production integration |

The three successful 0.5-MP references have SHA-256 values
`b589d1e80fb63ba393a5f7de3bd996c211f1d2bd8d6a4d121f65a8f459236c5d`,
`ebef71bdc22632759f9e5752e30d43d5850522b544a25b5372b9eeec25e4a921`,
and `1ce381cbdcb3c6a2d1e39d088472881d2c491aa9d3b1146f3c275bc1c816d5c5`.
They are deterministic derivatives of the tracked source cutouts and canonical
placement profile, so they remain ignored scratch files.

This is positive evidence for the materially different control mechanism
required by the regional-v6 audit, not yet a new default. Spatial v5 remains
the production default and Generation III remains the sole regional-v6
promotion. If the Generation-I candidate passes user review, the next bounded
validation is the unchanged topology on Generation VII (known depth stress)
and Base1 (Mewtwo anatomy stress). Production integration is justified only if
both preserve count, identity, card containment, and one global scene.

### Generation VII depth validation

User review accepted the Generation-I preflight for continued evaluation. The
unchanged three-reference topology then used Generation VII's promoted seed
`260726054`, scene brief, physical placement profile, cutouts, model, encoder,
VAE, and four-step sampler. Only the scope-specific inputs changed.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP, `432 × 592` | `149.72 s` | `f0f8a196578d0f76e16ff1a6fe6c660af6ca0be1252e6a799e5f32f71277b8ef` | `9b05b903fc8610180d1c7a2b06ab5847fd9ff8924aef0c8d903cae9ca2d5bbbb` | Exactly Rowlet, Litten, and Popplio appear once, complete and inside their assigned cards; one continuous Alola coast earns the 1-MP confirmation |
| 1 MP, `848 × 1168` | `234.67 s` | `288d5dd20c1ce4a74e8b62e52653e7d2288ad9a783738c202b2b0beb85112d4f` | `45a5aa1103f6f7ccb4190d7c699802e0ca9b083442081a5f4438d010ef9a1392` | Count, defining anatomy, pose, card padding, grounding shadows, and the single global coast pass agent review |

Foreground and rear vegetation initially appeared to occupy coherent depth
layers without the separate lower panorama or card frames seen in earlier
graphs. Subsequent user review of the physical Popplio crop found one local
depth defect that the first agent pass missed: a lower-right foreground blade
ends abruptly at Popplio's silhouette. Count, identity, card containment, and
the global scene still pass, but seed `260726054` no longer passes the complete
depth-intersection gate for this experimental topology. It does not replace
the promoted Generation-VII poster.

One bounded seed-only A/B then changed the noise seed to `260726055`. Prompt
and reference conditioning were otherwise unchanged. The 0.25-MP prompt
SHA-256 remained
`76ab58c6bcc33d3fe783965ab1f7922100728dd0a843b4b9476d21bf59d1a43e`;
the 1-MP prompt SHA-256 remained
`935ce0ab57c7ba5b5de8f5f7674f31d69a1ee7256960449c5f5cb76ce8f194f5`.
The three positioned-reference SHA-256 values remained
`1dca9b44a80f977c44aae6da73af13d10e2110646c6a8bd2e3801febc84cddf3`,
`e65ca5a711496bde12c09c549117c636b5d98a6712299cf85736e938cfc5daa5`,
and `f804e98423adc2705c04d0ef433584f5bc88d2b04c64a939e6d03d592502a742`.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP, seed `260726055` | `209.29 s` | `59c43adb3daec4feba6386462ba9aefc8ae6c64ed999f4f58321b59269466918` | `92bc241c540d85577afe2603b1ee63b9a9d67f909f0998cc10fddce5fe1da8d3` | Exactly three complete, correctly assigned subjects inside their cards and one continuous coast; earns the 1-MP confirmation |
| 1 MP, seed `260726055` | `215.73 s` | `8fa83b06da3795286a1e584eb9bdf406ebae7dad478e955e4add2f1f8940ca46` | `e1c060e1dedc6aed317225cfd440818f66544ad01b0a67bfe256bffb12c990a4` | Rowlet, Litten, and Popplio retain defining anatomy, padding, grounding, and shadows; the lower-right vegetation is one coherent rooted cluster and no blade terminates at Popplio's boundary |

Seed `260726055` initially became the preferred Generation-VII candidate for
the individual-spatial topology. Subsequent user review found a smaller but
still visible continuation of the same defect: part of the lower-right plant
breaks or changes depth unexpectedly beside Popplio. It therefore improves on
seed `260726054` but does not pass the final human depth review.

One further bounded seed-only A/B changed only the noise seed to `260726056`.
The 0.25-MP and 1-MP prompt hashes and all three positioned-reference hashes
remain byte-identical to the values recorded above.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP, seed `260726056` | `252.46 s` | `1a636a773954f5205454860277710c20fd2c1d3d76197ec1bc8ccfd65046ef85` | `bf32d03fa337c475b3f435069d5bb4b91b8b46fa96c32dc73bfb27de813e7837` | Exactly three complete, correctly assigned and card-safe subjects; the lower-right plant is coherent and does not intersect Popplio, so the candidate earns the 1-MP confirmation |
| 1 MP, seed `260726056` | `246.64 s` | `8392740075f96ca5155fc8e5ddf45a3399bd72c1ffdd6adb47d214cd4026aff9` | `7ca71c468924130966c1b7796b4274be01afe61b9804ee82a08697a8658d5f66` | Count, defining anatomy, physical-card containment, shadows, and one continuous Alola scene passed the initial agent review; subsequent human review found that a lower-right blade still slips behind Popplio instead of retaining its foreground depth |

Seed `260726056` therefore also fails the final human depth review. A
cross-scope comparison rules out the placement geometry alone: Generation-I
Squirtle occupies `x 72.1–96.1%`, `y 75.6–93.6%`, while Generation-VII
Popplio occupies the nearly identical `x 73.1–94.9%`, `y 79.8–93.6%`. Both
use the same model, encoder, VAE, four-step sampler, individual-spatial graph,
and depth paragraph. Generation I nevertheless produces coherent foreground
crossings at Bulbasaur and Squirtle.

The remaining material differences are the subject pose, scene language, and
noise. The neutral references show every subject with a complete unobscured
silhouette and provide no explicit depth or occlusion channel. Popplio's low,
extended flipper meets the broad tropical foliage requested by the Alola
scene; the model must resolve the conflict between exact visible identity and
foreground continuity from text alone. The meadow scenes more often produce
thin blades crossing only small exterior parts. The successful Generation-I
crossings therefore prove that the graph can synthesize the relationship, but
seeds `260726054` through `260726056` prove that it does not control it
reliably for this Popplio scene.

There is no preferred individual-spatial Generation-VII successor after human
review. Further seed-only searching is paused rather than treated as a control
mechanism. None of these experiments changes the promoted Generation-VII
asset.

### Generation I / VII cross-scene diagnostic

A bounded reciprocal A/B tested whether the Alola scene description alone
causes the Popplio depth failure. Each pair kept its cast, positioned
references, seed, dimensions, model, encoder, VAE, four-step sampler, and
individual-spatial graph unchanged. Only the complete `artwork.scene` mapping
was copied from the other scope; no depth sentence or subject constraint was
added.

| Cast and substituted scene | Target | Runtime | Workflow SHA-256 | Prompt SHA-256 | Raw SHA-256 | Agent result |
| --- | --- | --- | --- | --- | --- | --- |
| Generation VII cast, Generation-I scene | 0.25 MP | `218.52 s` | `3baaecd29ddc0e3a4f497bfd5dcd6af38d3b2495d4e26cd62688b6dd8005dda3` | `072d6f19a75da95ba5f19afb6b4dc4df95f509c87bc583c3ee424e5db366b1c3` | `151999677465e4393ca03f5fd363ef49fce22bb360484095fbcbd6739e0c45c5` | Exactly three complete subjects; fine meadow vegetation avoids the Popplio flipper |
| Generation VII cast, Generation-I scene | 1 MP | `242.08 s` | `77aef37d8d67f9adef4488b9343225e25692a1bb42168c836ed3c17fea476d8f` | `28c97c1dcff116cd9d613fc0a0cd31d28ec6c9547df9cb542ad4a98748d09406` | `aa790d0d88018e4875138afb905a57a36220666d55f86a9f6582870dff668c47` | Count, anatomy, card fit, and one scene pass; the continuous fine foreground remains outside Popplio's flipper without a broken intersection |
| Generation-I cast, Generation-VII scene | 0.25 MP | `189.60 s` | `daff0d30dc0813bbd5faaeb499a4cffefdd2a1d62435eb0375fa78b75b1f06ff` | `73898f02e74e21c51cbacbfddc6b80521986e6e2e385c102c30b9ebc35b0cd89` | `4f92d3757d167c6df5d7fe9df0412a58f8144be4705db8776261e6b894955f18` | Exactly three complete subjects; broad tropical foliage frames the cast without a direct right-card crossing |
| Generation-I cast, Generation-VII scene | 1 MP | `229.67 s` | `0afadc134982a2e7d5f091b4fa8c85831de22ee98ce1ccea02bc12d89731ce1f` | `0dd53e728024aa98093251dc21f3c83ed022cc1f776ac4e9eee92a54fed6ece2` | `77cbc4a4b280e09b2a5835e88a0160aa521506fbce7818bc85fcbb8f8ee3c8f6` | Count, anatomy, card fit, and one Alola scene pass; the lower-right tropical cluster retains one coherent relationship at Squirtle's tail without the Popplio-style front/back jump |

The 0.25-MP outputs are useful only for count and gross composition: the
accepted Generation-I control develops its reviewed small foreground
crossings only at 1 MP. The paired 1-MP results show that meadow language can
remove the problematic Popplio collision, but Alola language does not by
itself break Squirtle. Neither the scene nor the subject is therefore a
sufficient cause. The failure is specific to the interaction between
Popplio's low extended flipper, the sampled Alola plant geometry, and
conditioning that contains no explicit z-order signal.

Scene wording can reduce risky intersections by generating a continuous low
character band or moving broad foliage toward the frame, but that is collision
avoidance rather than depth control. The diagnostic does not justify a new
production prompt, a new default, or a promotion. A guaranteed foreground
crossing would require a materially different explicit depth or occlusion
control.

#### Deferred minimal depth/occlusion guide

The acceptance contract does not require a foreground crossing. A candidate
passes when every connected landscape object either remains entirely clear of
the character or keeps one physically plausible front/behind order for its
whole visible intersection. Abrupt termination at a silhouette and switching
between front and rear along the same object remain hard failures.

A minimal explicit guide is therefore reserved as a future experiment, not an
active workflow branch. It is triggered only when a bounded normal candidate
for a scope can achieve neither clean separation nor coherent overlap. The
guide may encode only coarse `near`, `subject`, and `far` depth ownership around
the three final subject zones. The existing three positioned identity
references remain authoritative for identity and placement; generation still
starts from one empty full-frame target and ends in one sampler and one decode.
The guide must contain no landscape texture, scene plate, character pixels, or
post-decode composite.

The experiment is intentionally bounded: one 0.25-MP binding check followed by
at most one 1-MP confirmation. It is rejected immediately if count, defining
anatomy, physical-card fit, one-scene continuity, grounding, or shadows regress.
Until that trigger occurs, the simpler individual-spatial one-shot remains the
only topology under evaluation.

### Generation VII clarified-depth continuation

The user clarified that visible foreground overlap is optional: clean
separation and one physically consistent overlap both pass. With prompt,
references, model, encoder, VAE, graph, four-step sampler, and all placement
geometry fixed, the continuation changed only the seed. Prompt SHA-256 is
`059c8e0bf05c778c4c6c48eb9bc9bcc0a74849f6b1a60662b580da141f322d78`
at 0.25 MP and
`6c5966d0a5aab04bce23d6c05a85aa9b5aba78bd328b258d2b301b42b86e0860`
at 1 MP. The three positioned references remain byte-identical to the hashes
recorded above.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP, seed `260726057` | `168.91 s` | `f3a730fa6f2f001de8eed81a269edb406cf49e6f1853ee59302b734aa5fa2e2c` | `38102c026d2e37185c574eaa07ca207be519cbe2eedd54776d2c4e0f4a13d0a4` | Exactly three card-safe subjects and clean Popplio/vegetation separation; earns the required 1-MP check |
| 1 MP, seed `260726057` | `202.11 s` | `4d4c2c4f440e860cb27046a73f6fbe123f49b35e8a5d7c9b988cf37b6b1e7176` | `f92a731fd1359049a5011a51387d8bda26b9bf32de91ff9bb7c2f92b3b6457c5` | Adds a fourth Litten-like subject above the bottom row; rejected on the exact-count gate before depth review |
| 0.25 MP, seed `260726058` | `158.58 s` | `09d819f3f5572438b5295ec8c66e3429a78043fe19d6f6d4ddf0321a57d2cdbf` | `9a6989a011ae35959e71860b7d7be430691f2c5b8c224d2922a3c81e43f721aa` | Exactly Rowlet, Litten, and Popplio appear once in the correct physical cards; one open Alola grass plane and clean right-card separation earn the 1-MP check |
| 1 MP, seed `260726058` | `201.44 s` | `78071e50dc7dd3d49dd4795e6819c82ba59b537d54ec387aa7fef8664dd3eac0` | `d9aa528feba024ca1db3f12c038da134e324a13dd07b3a71e4271ea579f54cbb` | Exactly three faithful subjects, complete silhouettes, useful card padding, coherent contact shadows, and one Alola scene; the large right plant remains consistently behind Popplio and the nearer bottom leaf stays clear |

Seed `260726058` is the preferred Generation-VII individual-spatial candidate
after agent review. It satisfies coherent depth through clean separation at the
remaining risky foreground boundary rather than by forcing a crossing. Further
seed searching is closed pending direct human review, and the deferred explicit
guide remains inactive. The promoted production asset is unchanged.

### Base1 anatomy validation

Base1 first used its promoted seed `260726503` with the same graph and
four-step settings. The input contains exactly one positioned reference each
for Mewtwo, Bulbasaur, and Charmander. The `432 × 592` Metal/MPS render
completed in `166.77 s`, but added a second full Mewtwo in the upper sky.
Workflow SHA-256 is
`20772ed8c9bc416013f108760da0a798851f958d506b31f7fffcd2c8b057acc7`;
raw SHA-256 is
`86a41e25461f694f7024ece3f46d59a7bcd0d53add2cf25020132d5d4351c188`.
This is a hard count failure and did not earn a large render.

Inspection confirmed that no reference, stale workflow input, or prompt text
contained a duplicate. One bounded stochastic check therefore changed only
the seed to `260726504`. Prompt SHA-256 remained
`46f4e7226b248613ad65cb1fc821657db34cc379169c97cf75b736722b9f3d1d`;
the three reference SHA-256 values remained
`f799caa0f7aa65903e869dd6d226dfbd0ae0f2bbb58c6ea27b164e2642e7db9e`,
`12016f7d3a74c62c7b61fb05d1ad0c248cf36fa23be6bdbe0f9b5e4bdad0dc48`,
and `19a7a12476f833b59eea8bb64e62043aefe16df263f443ed74485fd50809e6b4`.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP, seed `260726504` | `180.69 s` | `e0bc1ac0dabb412c9963da4b396eb9fd8c660910e91561720ed1bbaa6b2def3b` | `80c05589725984a9dac9269ffd86eef14107230c1d0740eb0262dced7075ee4d` | Exactly three complete subjects and one continuous meadow; Mewtwo's small hand details require the large confirmation |
| 1 MP, seed `260726504` | `237.56 s` | `ef91a0c0168d64ba44ad8edd4f2b7dc0ca76d68d199f3fac50cc975d5a424aaa` | `aa3b711ddc79adb809244e8967efd587e61b0120e7bbd93959ebae7265faaa26` | Mewtwo retains short cranial nubs, three-digit hand structures, the non-human chest/hip anatomy, feet, continuous tail, and generous card padding; Bulbasaur and Charmander remain recognizable and card-safe |

The retry passes the agent anatomy gate, but seed sensitivity is now explicit:
the promoted seed duplicates Mewtwo while the adjacent seed does not. The
current spatial-v5 promotion also renders Mewtwo larger and therefore retains
some fine source linework more clearly. Human comparison of both physical
Mewtwo crops remains mandatory before replacement. No Base1 promotion changes
as part of this experiment.

### Generation IV legacy-scope preflight

The first legacy `identity_lock` scope reused its existing Sinnoh scene brief,
seed `260734875`, cutouts, placement profile, FLUX.2 model, encoder, VAE, and
four-step sampler in the unchanged individual-spatial graph. Prompt SHA-256 is
`56b65aaf1d3fb46197221b047c3b2c603fb4141170bb383efccfb3416d01d179`
at 0.25 MP and
`9448f8819d78d1f0931c2fa36586b40d9cc6cb48a61e72b648755dbb17ebd85f`
at 1 MP. The positioned Turtwig, Chimchar, and Piplup reference SHA-256 values
are `6f7e227e97e97c5f2e101dddab82418717d89c99a180ce62b3228f9c5c284c22`,
`a9a7f2220fb8c6645cd64513729a6ec02c63d52e168838909c65654e104294e3`,
and `876ea00e42025594ae420021e31870a0e0a4ad2d718b87ba8e72be8c1508b7a1`.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP | `150.23 s` | `60bbc5e58e058829e13a6e850cb62aac199cec1f6cd77e85ce7acb4dce1a6736` | `eebec824263e6e6640760e8041d751203e4337d7e572debc1c11f6b063b5f1c5` | Exactly three complete subjects in the correct physical cards, one continuous alpine meadow and lake, and no gross identity or depth defect; earns the 1-MP check |
| 1 MP | `199.28 s` | `741a0c79482f03b1318dec608faff5a3414338a6b1eeb87dfc6451da2bbac907` | `17ffc408f9dba4ec634e18b740620de305c95ecb9c1f8e0abccdbe3dbb56e63e` | Turtwig, Chimchar, and Piplup retain their defining anatomy, faces, markings, appendages, and poses within the accepted print-detail tolerance; all three have useful card padding, contact shadows, and coherent landscape separation |

Seed `260734875` is the preferred Generation-IV individual-spatial candidate
after agent review. No prompt or topology retry is warranted before direct
human review. The promoted Generation-IV `identity_lock` asset remains
unchanged.

### Generation V legacy-scope preflight

Generation V reused its Unova riverside scene, placement profile, source
cutouts, and unchanged individual-spatial graph. Prompt SHA-256 is
`f4d79dd26b857797d6c07de88872400a262ea9e47cfa7176531a012f5911b18a`
at 0.25 MP and
`55a89c3b363dfbced414edb47be627dea17b921566ca8008c0490c12310bee70`
at 1 MP. The positioned Snivy, Tepig, and Oshawott reference SHA-256 values are
`50bbc1f9eed5145b99c28ed721970e132f21c183f731ff221d05ff2ba4911e20`,
`c235bf3acc4c7bed3f4a188c307325194831e04798868c42e9364f8f96b30879`,
and `8645b1173c45d5128c79ce610046092c084a9d4d2fdb3f69ff704085bc7c4512`.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP, seed `260735038` | `158.26 s` | `77d4a5b50ec6c2b3340749ebddfeca8b9946ba329cf52b1c9c8329b2e95ffa0d` | `7109c27b3fca6f5d950ca6d0e3e9a3e1cf07318e44006cab28adc28ae088f609` | Exactly three correctly assigned, card-safe subjects and one continuous riverside park; earns the 1-MP check |
| 1 MP, seed `260735038` | `203.96 s` | `6d1589366b8271f529337197ff6e0d27189459cba8de072720c61484996aacfd` | `ab402831038a99fb4c7fb02afa336be939c0dd80d90aa68aa8e89320c2006160` | Count, card fit, scene, grounding, and depth pass. A first small-preview inspection incorrectly suspected a missing Snivy arm; the enlarged physical crop confirms both arms and hands are present |
| 0.25 MP, seed `260735039` | `149.45 s` | `bc5ad3635c53244439e462fbb2c98033b01186bc96ae0e91ef28ea9561673604` | `7854107682efbb9302ac03a2d3361308287ad8fb1349f80da4156f6da7e4149a` | Exactly three complete subjects, correct physical cards, and one continuous Unova park; earns the 1-MP check |
| 1 MP, seed `260735039` | `213.83 s` | `a4a827536b289d05235c34fe02db2680e7980504b97bf6e77b3b7a275eb75efb` | `056184234c953e038ef23680e6a863fae5a4c5874c38f1afc6bf973da2afa720` | Both Snivy arms and hands, Tepig's ears, legs, snout, and curled tail, and Oshawott's shell, limbs, facial structure, and tail remain readable; all three fit their cards with coherent shadows and clean landscape separation |

Both seeds pass the agent hard gates after enlarged crop review. Seed
`260735039` is preferred because Snivy's two hands and Oshawott's reference pose
read more clearly at card size, while the park and skyline remain balanced.
The retry was caused by an agent preview-reading error rather than a confirmed
model defect; no Snivy-specific prompt note or code path was added. The
promoted Generation-V `identity_lock` asset remains unchanged pending direct
human review.

### Generation VI legacy-scope preflight

Generation VI reused its Kalos flower-country scene, placement profile,
cutouts, and unchanged individual-spatial graph. Prompt SHA-256 is
`c9e7a5888777cba28b0bb0de410d03c69164ee1cc7bc318342efa78c181fb8b2`
at 0.25 MP and
`ffd806d05ea09c98d046b16c842c70206ecde89f5e92dafa70162d4a7076abd9`
at 1 MP. The positioned Chespin, Fennekin, and Froakie reference SHA-256 values
are `ec2aea81a7c1bbe93c115849ee6c30085e483c3c27b027b37d88c91d39e9af49`,
`b5dc948e3d2f0404437d5d4e97c9429ba96f3c6aac055133677d044470873ae7`,
and `4fe8995e00067ccfafe55a38cfaf87308521ffbb6bd9c0d5890dc6cb02b3ceee`.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP, seed `260758583` | `148.95 s` | `e34ca743c7bb3597829cb39cb8394eed2514979670da5f5bd6ae2f8c26e56927` | `9ee4effc185e24d553f6aaefdf20a86452bc150bb8088bba48e4d25f8881caeb` | Exactly three card-safe subjects and one coherent flower meadow; earns the required 1-MP check |
| 1 MP, seed `260758583` | `200.94 s` | `f46c1cb36e83f972eabdbf1d6966cde488f8867a82127c18fa6e56c32b77db43` | `0c8b56472171ad88ec75ec595cbb7858156a24ad0ed62bb965acfaaa2ffdcb27` | Adds a second full Fennekin above the bottom row; rejected on the exact-count gate before anatomy or depth promotion |
| 0.25 MP, seed `260758584` | `150.49 s` | `68200c36d3acdc8b7e60b47f9e1bed082fdc313283e46892becfc9b9d8315260` | `f73ec2dafe8cb61d3f97d48d428108f425570e2c12fa52d5a0df021bc1ea324f` | Exactly Chespin, Fennekin, and Froakie once, complete in their physical cards and surrounded by one continuous Kalos meadow; earns the 1-MP check |
| 1 MP, seed `260758584` | `217.84 s` | `7b6fd9246730a1c4f49b73dc26201743b83c13fa115b379b98b0c2aadcbd4509` | `b16afecbc9a3cd45039ae4eea2a26279832f7121941e0d09a0cf76a31006d4f8` | Exactly three faithful subjects with card padding, grounding, and shadows; dense flowers either stay clear or retain one plausible depth layer around the silhouettes |

Seed `260758584` is the preferred Generation-VI individual-spatial candidate
after agent review. The normal graph resolves even its dense flower foreground
without the deferred explicit occlusion guide. The promoted Generation-VI
`identity_lock` asset remains unchanged pending direct human review.

### Generation VIII legacy-scope preflight

Generation VIII reused its Galar upland scene, seed `260715405`, placement
profile, cutouts, and unchanged individual-spatial graph. Prompt SHA-256 is
`99b3a5f342094554b940887f7661dff9607600bb3859fe9c81be66177b3344fe`
at 0.25 MP and
`1b31c815c9c77ca3280bc3b9601c5dbdb475e0b1826410b4b66e8ade8aa459b2`
at 1 MP. The positioned Grookey, Scorbunny, and Sobble reference SHA-256 values
are `8e1bb37c30772f2e1c30e08e5f7d060551a2501470c11eaf528e1294e41adce3`,
`ce0fab4411182c3878f90072236b150dd555176d9d7bc1a0ee17b362a59cfcff`,
and `47bc881e95d22745ee40166ce57a1dc20613b34d7b1cdd0568498423d622df9b`.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP | `158.91 s` | `04759386356562671cc12ceb378224481f24fc98a8ae44351eb50683f472d871` | `185df697ee8b53d97393ea786a0e9fc7fb1e978b0213c2be17312710475e1e57` | Exactly three complete, correctly assigned subjects inside their physical cards and one coherent moorland, lake, wall, and distant town; earns the 1-MP check |
| 1 MP | `207.43 s` | `bc1625cdeff5d3a9f4198f5bf0918486508fbd45559327274f2df4a88f4b132e` | `cbee5de594939146490f58bb2cdd19118c3551c1f0fab421fc0c6f59a10b857c` | Grookey's stick, leaves, limbs, and tail, Scorbunny's ears, running pose, foot marking, and limbs, and Sobble's face, crest, limbs, and tail remain readable; card padding, dramatic shared light, shadows, and landscape depth pass |

Seed `260715405` is the preferred Generation-VIII individual-spatial candidate
after agent review. The stone wall remains wholly behind the subject plane and
the nearest grasses do not create a broken intersection. No retry or explicit
occlusion guide is warranted before human review. The promoted Generation-VIII
`identity_lock` asset remains unchanged.

### Generation IX legacy-scope preflight

Generation IX reused its Paldea valley scene, seed `260778637`, placement
profile, cutouts, and unchanged individual-spatial graph. Prompt SHA-256 is
`dabe6626a34ae4a9af4f4744b119b9281ae53759bcce054d193d1578ea05dfa8`
at 0.25 MP and
`06354f1ff060fdcd133d75033369be39a9e2a543ff923cc56807d162fc20645b`
at 1 MP. The positioned Sprigatito, Fuecoco, and Quaxly reference SHA-256
values are
`2da64541d18b9dfce71b708f5f97c90f353bbe31b3ebea02887a1bd852aa254b`,
`1cac440a48341c3433e124312f84716a514e23267eb52dfb07bf5a60a5b4f843`,
and `e64935797e02d0c3619ab41908f020dde288715d18523883a19b7b463f2399dd`.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP | `176.54 s` | `313a5e24333c037e39ac74041a6aac4935d04cf467a0bbb19209799a0849b43a` | `0ab6d0fed65364bcb52cc696b10855b4e34d52f33e99c5bbb98d8ed2ede08d79` | Exactly three complete subjects in the correct physical cards and one coherent Mediterranean valley, coast, woodland, and distant academy; earns the 1-MP check |
| 1 MP | `223.01 s` | `d492e9cde34125f53c0f905defa4779a4c925f5631f351fc7b12e85e99c04620` | `3478f01ce419195dd563e60a8798b7c520f36ad9648f6e6b07a7a454b37131e5` | Sprigatito retains face, leaf collar, four legs, and tail; Fuecoco retains both teeth, crest, markings, arms, four feet, and tail; Quaxly retains both wings, cap, face, beak, and feet. Count, card padding, grounding, shadows, and clean depth pass |

Seed `260778637` is the preferred Generation-IX individual-spatial candidate
after agent review. No landscape element creates a broken subject intersection,
and no retry or explicit occlusion guide is warranted before human review. The
promoted Generation-IX `identity_lock` asset remains unchanged.

### SV03.5 legacy-scope preflight

The final legacy scope reused its Kanto coastal-meadow scene, seed `260726101`,
placement profile, Bulbasaur/Charmander/Squirtle cutouts, and unchanged
individual-spatial graph. Prompt SHA-256 is
`d615f31a6529df2264ffb3a6de810ba99e3d86476999cd8e7e05569b694cc379`
at 0.25 MP and
`d43964bdd6a834a76af04c414f9bc24bb23d3471dd91a00ea849817e4296772b`
at 1 MP. The three positioned reference SHA-256 values are
`b589d1e80fb63ba393a5f7de3bd996c211f1d2bd8d6a4d121f65a8f459236c5d`,
`ebef71bdc22632759f9e5752e30d43d5850522b544a25b5372b9eeec25e4a921`,
and `1ce381cbdcb3c6a2d1e39d088472881d2c491aa9d3b1146f3c275bc1c816d5c5`.

| Target | Runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | --- | --- | --- | --- |
| 0.25 MP | `146.67 s` | `e782b3436441bba1cc94ba990f68aeca19ba28cb9583427a7373594d7f47c775` | `818d85566ec47732a7eac7464bec25e534631c1351529802c234ac6b30441096` | Exactly Bulbasaur, Charmander, and Squirtle once in the correct physical cards, one continuous coastal meadow, and a calm upper logo area; earns the 1-MP check |
| 1 MP | `218.89 s` | `3774244de3731885307cf9f43d3e2e5c0102318a93b96c6d400bd8bed42c464c` | `0cd3e8a3b391e652aa53e97e6bc2932b40c41abaf840837b8791a7a0fc9d0043` | All three sources retain defining face, anatomy, markings, appendages, and pose within the accepted print-detail tolerance; card padding, contact shadows, coherent grasses, bay depth, and the text-free logo area pass |

Seed `260726101` is the preferred `SV03.5` individual-spatial candidate after
agent review. The deterministic German finalizer then places the tracked
`Karmesin & Purpur 151` logo and release-information block without changing any
artwork or character pixel. No generated text, extra character, or broken
landscape intersection appears. The promoted `SV03.5` `identity_lock` asset
remains unchanged pending direct human review.

### Review record template

Every rendered candidate appends one row containing the exact workflow and
model hashes, raw and deterministic print-size artifact paths, runtime, and
the following result:

| Gate | Automatic evidence | Mandatory visual evidence |
| --- | --- | --- |
| Joint final scene | Empty target, one final sampler/decode, and no post-decode source composite or restoration | The output does not read as separate pasted layers |
| Identity and anatomy | Exact source hashes and one explicit reference input per subject; record any architecture-specific spatial binding or control | Whole-poster and individual bottom-card comparison against all three supplied cutouts |
| Card containment | Any supplied mask or structural guide remains inside its physical card envelope; all candidates produce the exact nine shared-geometry crops | Every generated silhouette and appendage remains inside its real bottom-card crop with visible padding |
| Coherent depth | The workflow and prompt expose one common scene-depth contract | Contact shadows and every connected landscape/character intersection remain physically consistent |
| Set scene and safe areas | Title and information cells are derived from the shared physical geometry | Whole-poster review before deterministic logo and text overlays |
| Print output | Deterministic Lanczos output has the exact configured 300-dpi dimensions and nine expected crop dimensions | Raw and print-size crops retain the reviewed small identity details |

Geometric crop validation cannot prove that a probabilistically generated
character stayed inside its crop. Similarity, segmentation, CLIP, or DINO
scores may help reject obvious failures but cannot approve anatomy,
containment, grounding, or occlusion.

An architecture stops after three materially distinct attempts at the same
failed hard gate. A domain or training adapter is tested only after the base
graph demonstrates correct per-subject binding, and is retained only when a
controlled A/B improves identity without introducing a new hard-gate
regression.

## Individual-spatial production promotion — 2026-08-03

The user reviewed and approved the seven 1-MP individual-spatial candidates
for Generations IV through IX and `SV03.5`. Before reusing the reviewed raw
pixels, the production v7 builder regenerated every positioned reference and
prompt and rebuilt every workflow. Reference and prompt hashes matched the
isolated experiment exactly; each workflow graph was structurally identical
apart from the non-semantic `SaveImage` filename prefix.

| Scope | Seed | Reviewed raw SHA-256 | Promotion commit |
| --- | ---: | --- | --- |
| `Pokedex/sections/gen4` | `260734875` | `17ffc408f9dba4ec634e18b740620de305c95ecb9c1f8e0abccdbe3dbb56e63e` | `ae76dec` |
| `Pokedex/sections/gen5` | `260735039` | `056184234c953e038ef23680e6a863fae5a4c5874c38f1afc6bf973da2afa720` | `3175e21` |
| `Pokedex/sections/gen6` | `260758584` | `b16afecbc9a3cd45039ae4eea2a26279832f7121941e0d09a0cf76a31006d4f8` | `7ef8ff8` |
| `Pokedex/sections/gen7` | `260726058` | `d9aa528feba024ca1db3f12c038da134e324a13dd07b3a71e4271ea579f54cbb` | `f317c39` |
| `Pokedex/sections/gen8` | `260715405` | `cbee5de594939146490f58bb2cdd19118c3551c1f0fab421fc0c6f59a10b857c` | `5d165dc` |
| `Pokedex/sections/gen9` | `260778637` | `3478f01ce419195dd563e60a8798b7c520f36ad9648f6e6b07a7a454b37131e5` | `2f333b8` |
| `SV03.5` | `260726101` | `0cd3e8a3b391e652aa53e97e6bc2932b40c41abaf840837b8791a7a0fc9d0043` | `bf80977` |

Each approved 848 × 1168 raw result was resized once with deterministic
Lanczos to the 2368 × 3268 print raster and promoted with an explicit visual
approval record. The final state has thirteen enabled `joint_scene` bundles:
seven individual-v7, five accepted spatial-v5, and one Generation-III
regional-v6. No promoted scope uses `identity_lock`; it remains an explicit
fallback.

All thirteen bundles pass promotion validation and report `current` in the
read-only planner. German Pokédex and `SV03.5` PDF smoke builds confirm the
3×3 cuts, deterministic overlays, and insertion path. The minimal explicit
depth/occlusion guide remains documented but inactive; it is reserved for a
future scope that cannot achieve either clean separation or coherent overlap
within the bounded normal candidate rule.

## ExGen3 inline title-logo overlay — 2026-08-03

The ExGen3 section source already supplies localized titles ending in
`[EX_NEW]`, and the existing cover renderer turns that marker into the tracked
silver `ex` artwork. The poster overlay had flattened the same marker to plain
text and placed it inside the generic pale title panel. The deterministic
poster finalizer now supports one trailing inline-logo token: it centers the
localized title and tracked transparent logo as one bounded group directly on
the text-safe artwork cell, with a restrained outline/shadow and no panel.

Both ExGen3 overlays now read their exact `[EX_NEW]` titles directly from the
section source; the manifests contain no copied title or style switch. Their
stable text-free artwork, generation fingerprint, and visual approval remain
unchanged; only previews, top-center card slices, and overlay fingerprints are
refreshed. The German `ExGen3_DE_TEST_NO_IMAGES.pdf` smoke build confirms the
unchanged cover followed by the new cut-safe `Pokémon` plus `ex` poster title.

The following review caught that this exact section title was still repeated
as the first row of the middle information panel. A temporary manifest Boolean
fixed that output but created another data branch. The final form instead
normalizes the resolved top text and first semantic information row, removes a
match automatically, and chooses inline-logo versus text rendering from the
same source value. Pokédex therefore keeps its generation row below the
collection name, while every Ex-generation section uses the compact three-row
panel without a per-scope switch. The overlapping ExGen3 description prefixes
were shortened to date range plus distinguishing variant detail; no generated
artwork or PDF routing changed.

The remaining plain-text fallback still used a pale generic panel, most visibly
for the `Pokédex` collection title. That panel is now removed from the common
fallback renderer: plain titles use the same bounded outlined-text treatment as
the textual part of inline-logo titles. The fingerprint records
`direct_outlined_v1`, so only affected text-title overlays become stale; no
scope-specific display flag or artwork regeneration is required.

## ExGen2 initial section candidates — 2026-08-04

All three sections use the unchanged FLUX.2 individual-spatial v7 one-shot
workflow at 1 MP and the section-specific seeds already stored in their
manifests. The generated candidates remain ignored local review artifacts;
none is promoted or enabled by this record.

| Section | Seed | Raw SHA-256 | Agent review |
| --- | ---: | --- | --- |
| `normal` | `260737078` | `d7f1aa42a121e58b3ec5ae6d5ae34ec23c21a67801701afe42ba7b168fe8ab30` | Exactly Mewtwo, Mew, and Lugia once in the three bottom cards; scene, padding, grounding, shadows, and continuous valley vegetation pass, but human review found that Mewtwo has two instead of three visible fingers and Mew's three pointed fingers become blunt arm stumps; rejected on identity |
| `mega` | `260736802` | `f12dd7053571fcd439265f11620140596a2c2ae906fbceb7e8f7e536abb66fea` | Exactly Mega Mewtwo X, Mega Rayquaza, and Mega Latios once, but Mega Rayquaza's long body is folded and reshaped beyond the accepted identity tolerance; rejected on anatomy |
| `mega` diagnostic | `260736803` | `f0b1f1945222d7171a978726a27e34d9dc1f30368838f390f0034425bcaa7785` | Adds a second Mega Mewtwo X and Mega Rayquaza above the intended bottom cast; rejected on the exact-count gate, with no prompt or production change |
| `mega` diagnostic | `260736804` | `f01f1d8d217267cf0f034e00f16554a968586c35488aab0b02dfae7c753a8cf4` | Returns to the correct count, but repeats the same material Mega Rayquaza body deformation; rejected and the seed-only retry series is closed |
| `primal` | `260759901` | `c7a335d31a48a2804ef78f54304ddfb3d434e5b17712e063b6e62ea2267892d6` | Exactly Primal Kyogre and Primal Groudon once, but Kyogre's outer fin is clipped by the left poster edge; rejected on physical containment |
| `primal` diagnostic | `260759902` | `d021fc85f20c7d04a05f848b1d4e57382f66d3f81aef33a3d79481b3b9a344ba` | Repeats the left-edge Kyogre clipping with a new seed; rejected and classified as a systematic placement-margin failure |
| `primal` safe-margin diagnostic | `260759901` | `ac0317c4fe2282ead8d47d4021d03e633a5c9bb50f30d4fd4ab8c536294cf41c` | Reduces the reference width from 84% to 76% of the physical card; Kyogre clears the edge, but the model adds two large invented Primal creatures above the intended pair; rejected on exact count |
| `primal` safe-margin diagnostic | `260759902` | `d7c1086a4d7c3f77af972ce4fb273ffa08f9ea270278def828b674c0e731ca8d` | Repeats the same four-subject structure with the second seed; rejected and the safe-margin implementation is removed |

The bounded retries confirm that seed variation can regress exact subject
count without resolving systematic anatomy or placement failures. Mega is an
explicit identity blocker for the retained fallback evaluation. The generic
safe-margin mechanism was recorded in commit `c1dd483` and removed again by
`233b8e6` after both controlled Primal confirmations duplicated the cast. No
prompt branch, per-section workflow, automatic seed sweep, promotion, or PDF
enablement remains from these rejected diagnostics.

Human review therefore closes all three initial ExGen2 candidates without a
promotion: `normal` fails small hand anatomy, `mega` fails Mega Rayquaza body
anatomy, and `primal` fails outer-card containment. The next bounded comparison
uses only the already retained `identity_lock` fallback; the one-shot default,
prompt, and production routing remain unchanged.

The bounded `normal` fallback comparison keeps scope, cutouts, scene brief,
seed `260737078`, 1-MP generation target, model, encoder, VAE, and four-step
settings fixed, changing only the mode to the existing two-pass
`identity_lock`. Its raw scene SHA-256 is
`f7c8f6efafade7ee0084eebc6e69c4ec82db26ee1c28bc87cd9318559fbbb78d`;
the deterministic print-size final SHA-256 is
`c78566b4a6d43b4c7706ede15c30dbe8de65f85a0e71e862b2b5e7bfa2c29d71`.
Source-pixel restoration preserves the missing hand details, but Mew has no
convincing contact shadow and all three subjects read as a later foreground
composite rather than members of the generated landscape. The fallback is
rejected on the joint-scene integration gate. No artwork is promoted or PDF
routing enabled.

### ExGen2 stronger identity-control follow-up

Human review selects a materially stronger identity-control model as the next
experiment instead of replacing Mewtwo or Mew with less anatomy-sensitive
featured Pokemon. The existing Qwen-Image-Edit-2511 path is not repeated: its
recorded 0.25-MP Metal/MPS preflight retained the neutral input field, produced
one oversized subject, omitted two subjects, and generated no set landscape.
A Pokemon domain LoRA is also not introduced before the base edit graph proves
correct multi-subject preservation and spatial binding.

The next isolated candidate is FLUX.1 Kontext dev. It receives one complete
poster-shaped input containing the reviewed landscape and the three exact
source cutouts at their physical bottom-card positions. One common Kontext
edit, sampler, and decode may reinterpret terrain, lighting, contact shadows,
and foreground intersections, but must keep every Pokemon's position, scale,
pose, silhouette, markings, appendages, and small anatomy unchanged. There is
no post-decode source composite, identity restoration, inpaint pass, or second
generative stage.

This remains a non-production experiment. The first run is limited to a
0.25-MP Metal/MPS preflight with the ExGen2 normal seed and assets. It stops on
CPU fallback, memory failure, wrong count or card assignment, missing set
scenery, gross anatomy drift, or another visibly composited result. Only a
preflight that passes those coarse gates earns one 1-MP candidate for direct
finger, grounding, occlusion, and card-cut review. The candidate requires the
FLUX.1 dev non-commercial model license; no model download or production
configuration change is implied by this checkpoint.

Before execution, the native Kontext graph changes that resolution gate for a
model-specific reason. Kontext edits the supplied scene latent directly; a
0.25-MP input would discard the finger detail that this experiment must test,
while the official ComfyUI path normally scales edit inputs to approximately
1 MP. The cheapest valid identity preflight is therefore one 848 x 1168 edit,
not a low-resolution proxy. It still has one input, one sampler, one decode,
and no restoration stage.

The 16-GB baseline uses `flux1-kontext-dev-Q4_K_S.gguf` with SHA-256
`cc22ff7a2debb02e63765fa53af8c5ae0b6883b462d0601b9b55f51a15cdd6da`,
the existing Q4 T5 encoder, CLIP-L, and FLUX VAE. Its input is the rejected
identity-lock scene with SHA-256
`f7c8f6efafade7ee0084eebc6e69c4ec82db26ee1c28bc87cd9318559fbbb78d`:
that image is not a candidate, but it provides the exact reviewed landscape,
positions, and source-pixel anatomy for a single joint redraw. The effective
prompt SHA-256 is
`0f4de627d0738b0430cc9d90cad27e22a18cce5524f6fc9d76981f5409a75e50`;
the 12-node API graph SHA-256 is
`eead0e69bf1c5021eddcf57bc6e0f83028dcc79332020d4df2be894573b4675f`.

The Q4 run is a reproducible constrained-hardware baseline, not evidence
against BF16. If a 128-GB Apple-Silicon host is available, the primary quality
comparison uses the original 23.8-GB BF16 Kontext weights with the same input,
prompt, seed, sampler, steps, and output dimensions. A Q4-only small-detail
failure cannot close the architecture before that controlled BF16 comparison.

The Q4 baseline completed all 20 Euler/simple steps on Metal/MPS in 36:25.
ComfyUI reported the VAE and model in BF16, the Q4 model fully loaded, and no
CPU fallback. The 848 x 1168 output SHA-256 is
`211bbd1a5208caf7d937c563bd6c3388f2010d75533b0cf707349c2ff9af57ab`.
It fails before any print-size processing or promotion. Mewtwo and Mew are
materially redesigned, and Lugia becomes a small blue dragon-like character.
The unified redraw does add scene-wide lighting and vegetation, but it also
fails the intended depth fix: the three characters stand behind the nearest
foreground grass while their feet and bodies are drawn over those same blades,
leaving physically inconsistent crossings and interrupted stems. Human review
rates the complete result below the retained FLUX.2 one-shot candidate.

No Q4 prompt, seed, or sampling retry is allowed. One same-job BF16 render on
the 128-GB M4 Max remains justified solely to isolate weight precision. It must
preserve all three coarse identities and correct the foreground depth ordering;
otherwise FLUX.1 Kontext closes for this poster architecture.

The controlled BF16 comparison ran on the remote M4 Max with 128 GB unified
memory. It kept the input, prompt, seed `260737078`, 20 Euler/simple steps,
guidance, dimensions, single edit sampler, and decode fixed. Only the GGUF
loaders and quantized weights were replaced by the native loaders and original
BF16 model. Reproducibility evidence:

| Artifact | SHA-256 |
| --- | --- |
| BF16 diffusion model | `843a26dc765d3105dba081c30bce7b14c65b0988f9e8d14e9fbc8856a6deebd5` |
| CLIP-L | `660c6f5b1abae9dc498ac2d21e1347d2abdb0cf6c0c0c8576cd796491d9a6cdd` |
| T5 XXL FP16 | `6e480b09fae049a72d2a8c5fbccb8d3e92febeb233bbe9dfe7256958a9167635` |
| FLUX VAE | `afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38` |
| Input scene | `f7c8f6efafade7ee0084eebc6e69c4ec82db26ee1c28bc87cd9318559fbbb78d` |
| API workflow | `eab77cfce53ee8c636f05b3531c95a077f18802860c395637edb8a31bbba5d7c` |
| 848 x 1168 output | `b12a1c71b7514485af77348a710f811839e05d5af0113d98b8bcf8fcd0863b98` |

ComfyUI commit `87d23b81765161624889febfb3b81f19f3c8435b` reported
`Device: mps`, loaded all 22.7 GB of diffusion weights as BF16, and completed
the prompt in 318.11 seconds. The VAE loaded on MPS with CPU offload; the text
encoder loaded on CPU as FP16. This is an MPS diffusion render, not evidence
that every auxiliary stage used Metal.

BF16 produces more coherent foreground framing than Q4 in this seed, but it
still fails the non-negotiable identity gate. Lugia is replaced by a small
blue-and-white dragon-like biped with a different silhouette, wings, head,
limbs, markings, and proportions. Mew becomes an upright humanoid cat with a
different pose and body anatomy. The supplied source designs, silhouettes,
poses, and exact placement therefore do not survive the joint redraw.

FLUX.1 Kontext is closed for this poster architecture. There is no BF16 seed,
prompt, sampling, or precision follow-up, and no Kontext artifact is promoted.
The retained FLUX.2 one-shot remains the default and `identity_lock` remains
the fallback; both production paths are unchanged.

### ExGen2 FLUX.2 return gate on the M4 Max

Before broader rendering, the retained FLUX.2 one-shot received one bounded
return gate for `ExGen2/sections/normal`. The original seed `260737078` already
counts as the first attempt: it passed landscape, count, card fit, grounding,
and coarse identity, but failed Mewtwo's and Mew's hand anatomy. Seeds
`260737079` and `260737080` are the second and third attempts. They keep the
prompt, three spatial identity references, model, encoder, VAE, physical-card
geometry, four-step sampler, and 1-MP dimensions fixed.

The first remote queue exposed an infrastructure-only failure before producing
an image: the native worker had not applied the repository's existing Apple
MPS FP8 dequantization patch and stopped at `Undefined type Float8_e4m3fn`.
Commit `14330d8` moves that version-checked patch into the native bootstrap.
After re-bootstrap, ComfyUI reports the VAE, Qwen text encoder, and FLUX.2
diffusion model on MPS; both image attempts complete without CPU rendering.

Prompt SHA-256 is
`5aafaf9add02cb8d5555d7aa6b516438af235b4fcef33c3b2d490d2511845564`.
The model hashes remain the reviewed production hashes recorded by each remote
job. Results:

| Seed | Prompt runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| ---: | ---: | --- | --- | --- |
| `260737079` | `42.41 s` | `5cf9f3cdbb2d33aa8e1b866010b49701544edd00d205ace1a07e51ac332f9c33` | `c5d2a495ede3209e3134d3300e7fcbba879a25318577ca3fb59c0f8060aac3db` | Hard identity failure: Mew is anatomically stretched and Lugia becomes a small low four-limbed subject with redesigned wings, stance, and proportions |
| `260737080` | `42.76 s` | `0480f570d518fae934a55df16158a3ef363578d9a65c4c3c4a5488817a167ed8` | `1fb6b02d0eea6cfc302adfc2ef5e67ab11eecab915b23846b3e7f435015b0175` | Repeats the same failure class: Mew loses its correct arms and hands while Lugia is again reduced and rebuilt as a low four-limbed figure |

The three-attempt seed boundary is reached. Seed variation is closed for this
ExGen2 one-shot gate, neither candidate is promoted, and the conditional Mega
and Primal batch is not started. Rendering additional scopes with the same
unresolved identity gate would create review debt rather than useful poster
candidates.

### FLUX.1 Kontext official-workflow re-audit (2026-08-04)

The earlier Kontext close decision remains part of the history, but a workflow
audit found that its graph omitted the official `FluxKontextImageScale` step
and that its prompt asked the editor to reconstruct too many character details.
That concrete discrepancy justified one bounded re-audit rather than a seed
series. The corrected graph follows the current ComfyUI edit path, scales the
848 x 1168 input to Kontext's nearest 1-MP bucket of 880 x 1184, and uses a
short prompt that asks only for coherent ground contact, vegetation, lighting,
and shadows while freezing the existing characters. See the official
[Kontext workflow](https://docs.comfy.org/tutorials/flux/flux-1-kontext-dev)
and [`FluxKontextImageScale` contract](https://docs.comfy.org/built-in-nodes/FluxKontextImageScale).

Both corrected runs use the native 23.8-GB BF16 Kontext model with SHA-256
`843a26dc765d3105dba081c30bce7b14c65b0988f9e8d14e9fbc8856a6deebd5`
on ComfyUI commit `87d23b81765161624889febfb3b81f19f3c8435b`. ComfyUI reports
the VAE, 9.3-GB text encoder, and 22.7-GB diffusion load on MPS; neither is a
CPU render.

| Variant | Prompt runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | ---: | --- | --- | --- |
| Official scale path, full denoise | `350.75 s` | `f4c32c43223e81f01bca8b3cc8565f84d7f51b9b5d1358dbe08469f6abd3dee5` | `0fe5db7ff3f488c892169c6e398b9fc483cfdcd94bbaa66c15448745bc8d3066` | Coarse identities and the common scene survive much better than in the original audit, but small anatomy is softly repainted, Mew's three pointed fingers are absent, and character-tied shadows remain weaker than the retained FLUX.2 one-shot |
| Official scale path, denoise `0.40` | `370.66 s` | `47ff89acbef14c5c08b001a6cf833e1d37e86a7a1a130eda71463cb74e172844` | `758c7cc9250070e12275a3fed9f55cf89ae0e080280f06541064209a8c694cb6` | Visually preserves more source detail but returns the visibly overlaid contact and shadow tradeoff; rejected |

The corrected audit refines the reason for rejection: the first Kontext graph
was not a fair use of the official scaling path, but a correctly configured
single-image edit still does not beat the FLUX.2 multi-reference one-shot for
three small non-human identities. Kontext remains closed, and neither artifact
is promoted.

### ExGen2 precision, reference-resolution, and capacity matrix (2026-08-04)

The M4 Max worker permits a controlled comparison that the 16-GB host could
not run. Scope, seed `260737078`, scene prompt, target size 848 x 1168, physical
card geometry, placement bounds, empty target, and one-sampler/one-decode
contract remain fixed. The 848 x 1168 references are regenerated directly from
the original cutouts rather than enlarged from the old 608 x 832 reference
PNGs. This grows Mew inside its spatial reference from about 148 x 150 to
207 x 209 pixels, roughly 40% per axis and almost twice the pixel area.

| Variant | Prompt runtime | Workflow SHA-256 | Raw SHA-256 | Strict result |
| --- | ---: | --- | --- | --- |
| Native distilled 4B BF16, 608 x 832 spatial references | `40.68 s` | `4711cc87ec6b29f04b9dcfb280199466ec9f5d1b82cd98f2be736f03d9c96b87` | `a5fdf08f5d00043262c7ddb8fc2d712265e5f406db62edc1bafc564d7bfe8298` | Good complete scene, but Mew's hands remain blunt |
| Native distilled 4B BF16, 848 x 1168 spatial references | `74.06 s` | `0670d722f9a964557548d065b8bae22085a1b63a6d66dd90b42b57d1f221358b` | `66381569d3bc32399829e50f980a331edb5cc18d04ecf77c1255fa7db2dc9c4b` | Small hand-tip hints become visible; still no three distinct Mew fingers |
| Distilled 9B FP8 source weights plus Qwen 8B, 848 x 1168 spatial references | `156.81 s` | `028ccfa91a104c787584f1a9a613bee4920b567c918195a2760456ac7546384d` | `d8c647a604c816b1684f8a882a57f6758173425dd70f7e8653ec697147790253` | Best overall scene and identity result. Mewtwo's digits, Lugia, card fit, grounding, and shadows pass; Mew shows only incomplete finger hints and therefore still fails the hard anatomy gate |
| Native Base 4B BF16, 848 x 1168 spatial references, 20 steps / CFG 5 | `850 s` | `c76530d032de5626f5434cc0702b6addd6cbd49800d1a0c4f0b8f552ebe7f2e5` | `b217b971787d0102c11fb86b854ba1a9fd9bcc7e67d17cad78c056fcc217b608` | Does not displace distilled 9B: Mew returns to smooth hand stumps, Mewtwo's face and planted foot regress, Lugia is flatter, and shadows weaken |
| Distilled 9B FP8 source weights plus Qwen 8B, 1200 x 1664 (2-MP) spatial references | `394.58 s` | `8d9db2f58dfd808dc7d9ebf646da6bfd20e771ea9a03b31dd340074a5d8c2353` | `8f6fd99d9b980a62e1c4f2d82127662a72f284da7f59dfe23d150a622d6d4ee3` | Mewtwo is effectively tied, Mew still lacks three distinct fingers, Lugia is marginally softer, and Mew/Lugia fill their cards less well; higher reference resolution is closed as the sole fix |

The native distilled 4B model SHA-256 is
`ec3d4e733a771f61c052fb4856c48b336c55eaf2c65487c2a1faeb9bbda7a343`;
the native Base 4B model is
`9c5fed22b76baea749d88fc2abe3ad53245e7b21a0d353a762665eea00043b92`.
The tested 9B source checkpoint is FP8 with SHA-256
`865ba09f5b4c3cbd3468a4bd3acb9fcb2f8740c54317482f0bcd4ed1d3655cee`,
paired with Qwen 8B SHA-256
`f0ff9239d56269ca1d05e5f86da6a79fac111af464955681f11c7ab0ec5ef6c1`.
All diffusion runs complete on Metal/MPS. The source FP8 checkpoint remains a
quantized model even though the MPS compatibility path performs BF16 casts.

The Base graph follows the official ComfyUI contract: a separate empty
negative `CLIPTextEncode`, every `ReferenceLatent` attached to both positive
and negative conditioning, `EmptyFlux2LatentImage`, Euler,
`Flux2Scheduler`, 20 steps, and CFG 5. The full FLUX.2 VAE is retained and
`ImageScaleToTotalPixels` is omitted because the controlled references already
have exact poster geometry. BFL's reference implementation also exposes a
50-step/guidance-4 Base default, but the 20-step official Comfy candidate is
not a near-pass and earns no costlier retry. See the official
[FLUX.2 Klein workflow](https://docs.comfy.org/tutorials/flux/flux-2-klein)
and [Base 4B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B).

One final layout/identity separation probe uses the 9B model with an abstract
poster-shaped three-rectangle position guide and three 512 x 512 original
identity crops. It remains one empty target, one sampler, and one decode. The
94.48-second run has workflow SHA-256
`11a651c44b14ace0c9eb828592bdccbe8742ab00746a390bc00be28b40df2a84`
and raw SHA-256
`46480c9924ef95ebd3ad8d634ff9fce07b0a236a1d5e02b1ef19ca4f92db90bf`.
The model renders all three supposedly invisible rectangles into the final
landscape and places the characters above them, so the box-guide hypothesis is
rejected after this single run. A text-only placement retry is not repeated;
earlier evidence already showed material repositioning without visual spatial
conditioning.

The evidence separates two effects. More source pixels plausibly explain the
first tiny hand-tip hints, and greater model capacity improves the whole cast,
but neither 2-MP references nor undistilled Base training produces Mew's three
reliable pointed fingers. The 9B/1-MP result is the strongest unpromoted
candidate, not a production promotion. Native 9B BF16 is the next clean
precision isolation if access to its separately gated BFL checkpoint is
confirmed. No production manifest, default, fallback, PDF route, or promoted
artwork changes in this matrix.

### ExGen2 FLUX.2 Dev capacity gate (2026-08-05)

The next bounded capacity test replaces only the model profile of the original
`ExGen2/sections/normal` one-shot. It retains seed `260737078`, the three
poster-shaped spatial identity references, prompt, 848 x 1168 empty target,
Euler sampler, subject bounds, and one-sampler/one-decode contract. The graph
uses the official FLUX.2 Dev ComfyUI shape: guidance 4, a positive-only
`ReferenceLatent` chain, `BasicGuider`, `Flux2Scheduler`, and 20 steps. This is
the 32B FLUX.2 Dev model rather than another Klein seed or prompt variation.

The run completes on the remote M4 Max with 128 GB unified memory using
ComfyUI commit `87d23b81765161624889febfb3b81f19f3c8435b`. ComfyUI reports
`Device: mps`, loads the 33-GB Mistral encoder on MPS as FP16, loads all
33.8 GB of the Dev diffusion model on MPS with BF16 weights/manual casts, and
finishes the prompt in 28 minutes 50 seconds. There is no CPU rendering
fallback.

| Artifact | SHA-256 |
| --- | --- |
| FLUX.2 Dev FP8-mixed diffusion model | `863a82e4ff950a42a6b0e80bea824828f129eb1a8fbbdbd9e8cb29859127b486` |
| Mistral 3 Small FLUX.2 BF16 encoder | `7d79902f60b1aeb3a6de2cfad02f4367b5e300a1387de3d03ac717cfa3df117c` |
| FLUX.2 VAE | `d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5` |
| Mewtwo reference | `f799caa0f7aa65903e869dd6d226dfbd0ae0f2bbb58c6ea27b164e2642e7db9e` |
| Mew reference | `7faf3993aad617c38917f187bb8e4f590437a3649e5dad8e10b923a3937cad43` |
| Lugia reference | `f29b83f0ad5433561f5776cb8602a25079e44365fca9db520976ebdae19253fe` |
| API workflow | `f5abbecbceb62455e38cfdb93fc45c6c70cf87bc9580a6f17867cf495b06bf07` |
| 848 x 1168 output | `3c74f750ad400b946c5e74f38eed8fddb6ffed765ae9718301264af4972cec5d` |

Dev improves Mewtwo's visible digit separation, preserves Lugia's coarse
identity, respects the three card cells, and generates strong scene-consistent
cast shadows. It still fails the non-negotiable small-anatomy gate: Mew's hands
remain smooth stumps rather than the three pointed fingers visible in the
identity reference. The characters also remain materially crisper and flatter
than the painterly landscape. No foreground object intersects the silhouettes,
so this candidate avoids but does not validate the difficult occlusion case.

One final reference-resolution isolation keeps that exact workflow, prompt,
seed, model stack, target canvas, and sampling schedule, but regenerates all
three poster-shaped references directly from the original cutouts at 848 x
1168 instead of 608 x 832. The higher-resolution input hashes are Mewtwo
`254019a2d7acf67b37a60a1c75bf2e2b4b33758fcee8c958fcfcdbb850fe6069`,
Mew `fcc7d547f451446bf1e5294331229f17f5315a3efe26a10b9360979f66883fe6`,
and Lugia
`f60c1aefe70b6c6cf25a129a2984ef730124a029bf01d967d3422e34acc680ad`.
The workflow hash is unchanged. The MPS prompt runtime rises to 49 minutes 14
seconds and the output SHA-256 is
`839dfc35c33acf7c294a1231c35bb37f41492704bb4782309db846efd5436c9c`.

The extra source pixels do not change the gate result. Mew still has smooth
hand stumps without three distinct pointed fingers, Mewtwo's smaller hand does
not gain more reliable digit separation, and Lugia remains effectively tied.
Card placement and the coherent landscape still pass, but the characters
remain visibly crisper than their surroundings and the cast shadows become
heavier. A roughly 70% runtime increase therefore buys no material identity
improvement. Higher Dev reference resolution is closed as a fix for this
failure class.

The Dev candidate is not promoted. Because the normal-section gate fails, the
conditional Mega and Primal batch is deliberately not started. The retained
FLUX.2 Klein one-shot remains the production default, `identity_lock` remains
the fallback, and no manifest or PDF route changes. Further generic
model/precision/seed escalation is paused: the evidence now points to a
subject-specific identity-control or training experiment, or an explicit
relaxation of the smallest anatomy requirement, rather than another broad
render sweep.

#### Human review resolution (2026-08-05)

The user subsequently reviewed the actual Dev poster and explicitly accepted
it as a strong result. That human decision supersedes the agent's stricter
small-finger rejection: the visible character fidelity, complete card crops,
shared scene, and grounding are accepted within the project's practical print
tolerance. The exact candidate above is promoted for
`ExGen2/sections/normal` at 2368 x 3268 with deterministic 300-dpi Lanczos
output and remains PDF-disabled until its localized overlay is reviewed. This
approval also unlocks one Dev candidate each for the configured Mega and
Primal sections; neither is promoted without its own visual review.

#### Dev follow-up sections (2026-08-05)

The unlocked Mega and Primal candidates use the same Dev model, encoder, VAE,
guidance-4/20-step graph, 848 x 1168 canvas, and M4 Max MPS worker as the
accepted Normal poster. Only each leaf manifest's scene, subject references,
subject count, and stable seed differ.

| Target | Prompt runtime | Workflow SHA-256 | Raw SHA-256 | Result |
| --- | ---: | --- | --- | --- |
| `ExGen2/sections/mega`, seed `260736802` | `29:44` | `d53a39851acabaf7cfac153cbfe528a38dbdcb9bf57fcdebaefde1ff02c496ac` | `4d6d4fe55520f7b620440b7cec2b1525e4dd1e8570655339bee3a46d94636227` | Hard exact-count and placement failure: Mega Mewtwo X and Mega Rayquaza are each duplicated, the central lower card is empty, and the extra subjects occupy the row above. Mega Latios alone fits its intended lower card |
| `ExGen2/sections/primal`, seed `260759901` | `24:03` | `2391a964798016f510ec3bac9d734f1b6ade666b21e4b871753bd6af60e45dc9` | `f7bceb3dc1172edafce5f38607b53729610c1aad13c5c61272099afd72ef3567` | Hard placement failure: both intended Primal forms are generated about one full card row above their target cells; the physical bottom-row crops contain only partial extremities and terrain |

Both jobs report `Device: mps`, use ComfyUI commit
`87d23b81765161624889febfb3b81f19f3c8435b`, and retain the model hashes from
the accepted Normal run. Neither candidate is promoted. The failures are not
small seed-level anatomy variations, so the bounded rollout stops without a
seed sweep or prompt branch. ExGen2 Normal remains the sole Dev promotion;
Mega and Primal require a material placement/count-control change before a new
generation attempt.

## Paired integration LoRA dataset gate (2026-08-05)

The next architecture is isolated from production and begins with data rather
than a new sampler graph. It will train one FLUX.2 Klein 4B edit LoRA to turn a
rough exact-position composite into a coherent scene while preserving count,
card assignment, pose, silhouette, anatomy, face, colors, and markings. The
copy-based image is the edit input; only a separately reviewed integrated image
may be target truth. The full contract, fixed holdouts, baseline parameters,
and stop rule are versioned in `POSTER_ARTWORK_TRAINING.md` and
`config/poster_training/flux2_klein_integration_v1.json`.

The first read-only audit covers all fourteen promoted raw targets and every
locally retained identity-lock scene matching the historical filename contract.

| Audit result | Count | Decision |
| --- | ---: | --- |
| Promoted target scenes | 14 | Seed inventory only; a promoted target is not automatically a gold pair |
| Historical input files | 18 | Hash and pixel-audit each one |
| Blank/constant historical inputs | 4 | Reject |
| Nonblank historical inputs failing the current exact-source contract | 13 | Regenerate; do not reuse silently |
| Exact historical inputs | 1 | ExGen2 Normal only; its known Mew/Mewtwo fine-hand deviations exclude the target from training truth |
| Scopes with no retained identity-lock input | 2 | Base1 and SV03.5 require a fresh input if selected |

The audit therefore produces zero automatic gold samples. This is intentional:
automatic checks may reject, but `candidate_pair_review` cannot approve a pair.

One fresh input for `Pokedex/sections/gen1` then reuses the current
identity-lock workflow, seed `260782266`, and current card-safe cutouts. It runs
on the M4 Max worker with ComfyUI commit
`87d23b81765161624889febfb3b81f19f3c8435b`. The worker reports `Device: mps`;
the 4B diffusion model and VAE use BF16, while the text encoder uses FP16 and
may offload when idle.

| Artifact | SHA-256 |
| --- | --- |
| FLUX.2 Klein 4B BF16 model | `ec3d4e733a771f61c052fb4856c48b336c55eaf2c65487c2a1faeb9bbda7a343` |
| Qwen 3 4B encoder | `6c671498573ac2f7a5501502ccce8d2b08ea6ca2f661c458e708f36b36edfc5a` |
| FLUX.2 VAE | `d64f3a68e1cc4f9f4e29b6e0da38a0204fe9a49f2d4053f0ec1fa1ca02f9c4b5` |
| Exact source reference | `8380ba529255f0581dae6399b90fba69c15c624e4f02d0eca4c645f0588f9c97` |
| API workflow | `58780c547402df5c1935c35e07007aa3c74c1634788e542f555eebaad515ed6e` |
| Fresh 848 x 1168 input | `d8da5015647fee72b880d098dd8f174b70717cce3deccfdae98d61f09758b139` |

The hard input gate passes: all 62,563 fully opaque source pixels are unchanged
and no source pixel differs. The input is deliberately allowed to look copied.

The existing reviewed Generation I one-shot is not promoted to gold pair truth
for this input. Although both images depict the intended mountain meadow and
the target remains a valid production poster, the target redraws the river,
tree line, foreground, character scale, and vertical placement. Training on
that pair would reward unnecessary global reconstruction and subject movement
instead of the requested integration operation. The fresh input remains a
`candidate_pair_review`; the next data step is to create an aligned target that
changes only terrain interaction, light, contact shadows, and coherent depth.
No LoRA job is started before 4-8 such pairs exist.

### Generation I aligned teacher-target probe (2026-08-05)

One isolated probe tests the smallest data-construction change that can produce
an aligned target. FLUX.2 Klein 4B receives the complete fresh 848 x 1168 rough
composite as its only `ReferenceLatent`; there are no separate subject images,
position boxes, masks, regional branches, or production-mode changes. The
prompt asks it to preserve the full composition and revise only integration,
lighting, contact shadows, ground contact, and coherent depth. The graph keeps
the production distilled schedule: one empty target, Euler, four steps, one
sampler, and one decode.

The job runs on the M4 Max worker with `Device: mps` and completes the prompt
in 28.12 seconds. It uses the same BF16 4B model, Qwen encoder, VAE, and ComfyUI
commit recorded above.

| Artifact | SHA-256 |
| --- | --- |
| Complete rough input | `d8da5015647fee72b880d098dd8f174b70717cce3deccfdae98d61f09758b139` |
| API workflow | `5c9204c7c4639b0124cfb598d07863dbf6acd23ee5592354bb4633f5bf5dca31` |
| Raw full-composite edit | `502810178d79df661e596dbcf629fbbfdd767f4880ae87668bf6ab5d192d3d7e` |
| Exact-restored aligned target candidate | `a6b3df27e97f395d68e9b4699e8f82e9738daf0da2cf88ebc3176fc7aae74aec` |

The raw edit preserves the valley, river, tree line, all three card assignments,
and approximate scale much better than pairing the input with the old promoted
one-shot. It also introduces clear common-ground shadows. It is not target
truth by itself: small feet, hands, facial lines, and body contours are softly
repainted. The aligned teacher candidate therefore restores the canonical RGBA
subjects at their original pixels over the integrated scene. Its hard audit
passes with all 62,563 fully opaque source pixels unchanged.

This is promising but not automatic approval. The candidate uses valid clean
occlusion avoidance rather than a foreground crossing, and human review must
still check antialiased edges, possible teacher remnants outside the restored
silhouettes, shadow direction, visual integration, and every physical lower
card. Until that review passes, the sample remains `candidate_pair_review` and
training remains gated. The reusable `compose-target` command implements only
this exact restoration and immutable audit; it does not add a renderer mode.

### Base Set target candidate and Generation VII boundary (2026-08-05)

The same frozen full-composite graph is next applied without prompt or model
changes to one expected positive fixture and one difficult depth fixture. All
jobs run on the same M4 Max MPS worker and use the BF16 4B model stack above.

| Scope / seed | Rough input SHA-256 | Raw edit SHA-256 | Aligned target SHA-256 | Result |
| --- | --- | --- | --- | --- |
| `Base1` / `260726503` | `d52247827f47483c3ff3cd2198f0501f1ac0fffca040d4410c749ee12508722d` | `86be9c3ec6683be3e827782ccf1b10b0d92290ed9980731c6a45216f867a647b` | `c54fa3b36dac1c33f46828252e004a4ba7940176b4996c58a6498864347b4787` | Rejected by human review: Mewtwo is drawn over a grass blade rooted closer to the viewer, so exact anatomy does not rescue the wrong depth order |
| `Pokedex/sections/gen7` / `260726058` | `ea8c0c9fa95fff17c7e57d782b685a6b1d32648eb1df4e77712474d642e39582` | `917574818d0dd2d272e447922f940792e04c60857f7a6c8d578452e07358c08d` | `a08ae9a5a444127bdce53aff27ae139fc3347fb0f2b3707b9d52a847ffbbd864` | Rejected: exact restoration puts the subjects back in front of foreground edge plants, so the original depth contradiction remains |
| `Pokedex/sections/gen7` / `260726059` | `44dc633c974d3d3679b4a33a9b3efd3fa89b8bbd865e9734cc8e970096c3250c` | `860d9cf2f9b8acb5b1a8e56d4016ac7db445d7f1970203d3a7c30a51fd334196` | `a5d738bbb379533be67e2e748266d6ce413fba29b7698b9001af576122f437d8` | Rejected: the clearer meadow helps Rowlet and Litten, but the large bottom-right plant still starts in the foreground and runs behind Popplio |

The Base Set source reference SHA-256 is
`d14967b8ae340432c45159e115407d5e079dced961eba5173df0d57ed5c533e5`;
all 52,343 fully opaque source pixels survive in its target candidate. The
source and edit workflow hashes are respectively
`3cdeaaf5991fe4b9c58db2ca7038f53e6aeedd5f50e1ca8359c7ce0b28502326`
and `def90ff77d3275fb35af68043eca0ca3da9c7445502ea1e3125ab41f51916b3c`.

Generation VII establishes an explicit limit of the simple recipe. Exact
restoration can produce gold examples for clean avoidance or landscape that is
entirely behind a subject. It cannot itself create a valid foreground crossing,
because restoring the canonical subject necessarily draws over that crossing.
The configured lower-band prompt already forbids tall plants and isolated
foreground objects, so another prompt branch or broad seed sweep is not
justified. Both tested seeds are closed. A future foreground-occlusion dataset
needs a separately reviewed foreground layer or another explicit depth-control
mechanism; it is not added to the first plumbing overfit.

Human review also rejects the earlier Generation-I candidate: foreground grass
blades run behind Bulbasaur and Squirtle although their roots place them closer
to the viewer. Generation I, Base Set, and both Generation-VII seeds therefore
share the same failure class. There are zero surviving pair candidates and zero
gold samples. No training starts.

This review exposes a necessary distinction in the gate. Exact opaque-source
pixels prove anatomy and registration only; they say nothing about scene depth.
Training on any of these targets would explicitly reward the wrong occlusion
order, and a four-to-eight-pair overfit would amplify that error. Future target
construction must either keep the expanded subject regions entirely free of
foreground-rooted elements or provide a reviewed foreground layer that is
composited after the exact subject restoration and recorded as intentional
occlusion.

### Intrinsically clear-surface target probe (2026-08-05)

One lower-band inpaint of the original Base Set scene is tested before changing
the data source. Although the complete lower row is masked and the prompt
explicitly forbids tall grass and foreground plants, the inpainted result again
adds blades at the bottom corners and inside subject regions. This route is
closed after one attempt; further mask shapes or prompt branches would not
change the demonstrated semantic tendency.

The next KISS probe changes the training scene rather than patching its depth.
It generates a text-only background whose lower surface is intrinsically free
of upright vegetation, composites the exact positioned Base Set cast to form
the rough input, runs the frozen single-reference teacher graph, and restores
the canonical RGBA cast. These synthetic scenes are training-only augmentation;
they never replace a scope's configured production background.

| Surface / seed | Background SHA-256 | Rough input SHA-256 | Raw teacher SHA-256 | Aligned target SHA-256 | Result |
| --- | --- | --- | --- | --- | --- |
| Smooth compacted earth / `260726510` | `4a59ece8df562cb8f063bb5d87e36176c34074076173a11c05500cd888a20a05` | `d533e73c23025117fabf9e72d4baee8f3d7d5259ef2eb1efd612989a4eb2bdf7` | `69ff066b5bb59e80b788588ae46566e0d87f996e548ab0a2b9816eb9c36f28f2` | `2f8427326fa1cd530e075189040baabb573b4e20189cc53468a5cf1227536223` | Rejected: depth is unambiguous, but the flat lower plane and hard horizontal forest boundary are too sterile to represent desired poster quality |
| Natural rippled sand / `260726511` | `05bd383b546d8d2d6fd3acc4b7c1da18dc6ae58fc030fa6a0d0b9214a2c036bc` | `71a8c555cca651e7e54ff51a45bdf4b8113a9e856d37b46e8dd2ff634a3fe7a4` | `512d74ccd8b101bd84563aafffaeebdfa3460d43b26bfdf06892b2ec465b4ef3` | `1ca81ee79afa155b07e9070dc843e0837d788c6d2fa72acfd48e2be288e41334` | Gold holdout after user review: natural continuous beach, flat surface ripples rather than foreground objects, exact cast and card placement, and coherent upper-left contact shadows |

The sand background and teacher workflow SHA-256 values are respectively
`639c99d626f427ac958637f5ce3ad23f94b5bee14057c1d12de95c5829929fb6`
and `856450892420af8af546230945c5b0b0134d326806f501947252ce732c63d3d1`.
Both jobs report `Device: mps`. The exact-restored target again passes all
52,343 fully opaque Base Set source pixels, but that audit remains only the
identity/registration gate. User review on 2026-08-05 passes scene quality,
shadows, flat-surface semantics, and the three physical crops. Because Base1 is
a fixed holdout scope, this becomes the first gold **holdout**, not a training
pair. Training remains blocked until at least four gold train pairs exist.

### Clear-surface train candidates for Generations II-IV (2026-08-05)

The same KISS recipe next creates three distinct `train_candidate` scenes. The
background is generated without characters, the exact current cast is placed
once to form the rough input, the frozen one-reference teacher adds only scene
integration, and `compose-target` restores every fully opaque source pixel.
Every render uses the same BF16 FLUX.2 Klein 4B stack on the M4 Max MPS worker.

| Scope / surface / seed | Background SHA-256 | Rough input SHA-256 | Raw teacher SHA-256 | Aligned target SHA-256 | Exact opaque pixels |
| --- | --- | --- | --- | --- | ---: |
| Generation II / natural snow / `260726512` | `ffcf5127465543d3898f305ace4769f1aa3983fcbe4cac5f81610ccd79df9af9` | `e313dc6d76df1e8d29cb5a15858261c27d6fbd6c9564d19d79925adac3f78a1b` | `402d0d0baceed8e966bf87722d9787e7bea6e03d0b779be7017750db9e9b10f0` | `23eafd60ba6c86fc9b78a009c0b970394e553f06f5f3742eb5c9f46dcb675106` | 39,446 |
| Generation III / volcanic black sand / `260726513` | `f5597dfc674e0f12d92212d38ae2c0d92edd3965154690b5b92c402176480a21` | `0dbf1f1c92d9c2b9442df3e58f46c61f755fd997abe36c927635ec93ad0c393f` | `183f19c024f47daabad5f5cef24f90af2f7d27eaa8d02c0373a60d9c0649d8e1` | `3b73ef24163a9b13faf8b65320cdf3fd0fba948d1a0cbe2d3d9d240cf39f4de0` | 41,558 |
| Generation IV / pale limestone / `260726515` | `243919f51879003f8599da54825e1ac0db52f4d0ad620da12e7f76e1faa74fa9` | `ae5797f424747bae76b7fd8c49078ac94b31640bd43a3f0ccdd6aac59b75c4c2` | `61c4e1d83e996c4b89231d8b5407d7fba362faf08f6eb8ace8ba2c66f7a15abb` | `0ed7147e99039d5b02c13c8b69f1b45f8528ca77d1be146fbe658c09c77dbc68` | 42,981 |

The first Generation-IV background seed `260726514` is rejected before cast
placement because it depicts a frontal masonry wall rather than walkable
ground. Seed `260726515` corrects that failure with one continuous horizontal
stone plane. Agent-side preflight finds all three replacement scenes card-safe,
text-free, naturally grounded, and free of upright foreground occluders. The
user approves every complete image and all three physical lower-card crops on
2026-08-05. Generation II, III, and IV therefore become the first three gold
`train_candidate` pairs. Together with the Base1 gold holdout, the audit now
contains four gold samples, but the holdout is never training input. One more
gold train pair is required before the bounded plumbing overfit starts.

### Generation V red-clay train candidate (2026-08-05)

Generation V supplies the fourth distinct train scene. A text-only background
uses distant layered badlands and one continuous red-clay pan whose darker
mineral variation remains flat ground texture. The exact Snivy, Tepig, and
Oshawott cast forms the rough input. The unchanged one-reference teacher graph
adds late-afternoon contact light and shadows before `compose-target` restores
the canonical cast.

| Artifact | SHA-256 |
| --- | --- |
| Background workflow | `35082d9db99af4b067a4d329f1482849efc93ddda8752dbc6dd0db886e21e8be` |
| Text-only background | `0db4a796985014f01b44e33962395d2ac0343178dfd127db91942310491f2022` |
| Exact rough input | `6fd9e11611d54d594a3c8625eb5ad25447d67cca033f59d36db0c220c10babb2` |
| Teacher workflow | `a037aa63ba80f9d3b7f56ec283c37dc4f6687d8d9a62048b2263195f2639243e` |
| Raw teacher edit | `6280c70590076bbf358a62c0aace7d2378da9c8ee14750f8ddc3a65f4c0b3b68` |
| Exact-restored aligned target | `2dc2a577a03c53da7e2635ad5170c7dd27ffbb770484f778898ab36010287912` |

Both seed-`260726516` jobs report `Device: mps`. The source audit passes all
52,025 fully opaque pixels with zero changes. Agent preflight passes count,
identity, card containment, flat-ground depth, text-free safe areas, and the
three lower-card crops. The user approves the complete target and crops on
2026-08-05, so Generation V becomes the fourth gold `train_candidate` pair.

Before materialization, a final leakage audit finds that the original exporter
would copy gold holdouts into the same root `target/` directory consumed by AI
Toolkit. The exporter now keeps only train pairs in root `reference/` and
`target/`; evaluation pairs live below `evaluation/<split>/`. The plumbing
overfit cannot start until the corresponding regression test passes.

The regression test subsequently passes. Dataset
`tmp/poster-training/v0/overfit-dataset-v1` contains exactly four paired train
images and captions at its root; Base1 exists only below
`evaluation/holdout/`. Its materialized manifest binds audit SHA-256
`b2d890f683e3149cbd0ec40769bcb1bcf13e9a58d4dd18fdc03a414ec8b755f1`.

### FLUX.2 Klein MPS plumbing-overfit preflight (2026-08-05)

The remote M4 Max worker installs AI Toolkit at exact commit
`9065951da32c0014899e142766846705a18f1347`; its resolved Diffusers dependency
is commit `c943837899b16cbae2f619b8dd4f7bb6f07dd81a`. The toolkit hardware doctor
passes with Apple Silicon MPS, PyTorch 2.13.0, torchvision 0.28.0, and
torchaudio 2.11.0.

The first executable training configuration is
`config/poster_training/flux2_klein_integration_overfit_v1.yaml`. It is
deliberately a single bounded experiment: FLUX.2 Klein Base 4B, linear LoRA
rank/alpha 32/32, BF16, native AdamW, batch 1, gradient accumulation 2,
`match_target_res`, no model or text-encoder quantization, and 100 steps. It
disables sampling during training so the preflight answers only whether the
paired edit path loads, learns, and saves finite weights. Holdout rendering is
a separate gate after that succeeds.

The complete preflight succeeds on the M4 Max through MPS with process exit
code zero. AI Toolkit keeps all four images in one native `848x1168` bucket,
caches exactly four latents and four text embeddings, unloads the text encoder,
and attaches the linear LoRA to 80 image-model modules. One hundred train loops
with gradient accumulation two produce 50 native AdamW updates in 1:13:51.
Observed per-sample losses remain finite throughout; the last reported loss is
`0.1432`. A step-50 checkpoint and final step-100 adapter are both saved.

The final adapter audit is:

| Property | Value |
| --- | --- |
| File size | 92,426,896 bytes |
| SHA-256 | `418816b51ad277f34f9ace555c78add0f4991f5ed14f567ab98602c67f402945` |
| Tensor count | 160 |
| Parameters | 46,202,880 |
| Stored dtype | BF16 only |
| Non-finite tensors | 0 |
| Embedded training info | step 100, epoch 24 |

This passes only the plumbing and numerical gate. It does not promote the LoRA
or prove visual quality. The next gate applies the adapter to the unseen Base1
rough composite with the distilled FLUX.2 Klein 4B inference model, compares a
small fixed strength sweep, and reviews the full poster plus physical crops.

### Base1 holdout strength sweep (2026-08-05)

The step-100 adapter is loaded through ComfyUI's native
`LoraLoaderModelOnly` after the distilled FLUX.2 Klein 4B UNET. Three immutable
worker jobs keep the Base1 sand rough composite, holdout prompt, seed
`260726511`, 848x1168 output, four Euler steps, CFG 1.0, text encoder, VAE, and
every graph edge fixed. Only LoRA strength changes. All jobs complete on MPS
and validate the pinned model and adapter hashes.

| Strength | Output SHA-256 | Full-image MAE to exact-restored holdout | Source-region MAE | Exact source pixels changed |
| ---: | --- | ---: | ---: | ---: |
| 0.0 baseline | `512d74ccd8b101bd84563aafffaeebdfa3460d43b26bfdf06892b2ec465b4ef3` | 0.7061 | 10.1318 | 52,298 / 52,343 |
| 0.7 | `f71f54f796e6a058afc4040dc655c71ebe5c2e6f3b63382f097a65a5e73dae7d` | 2.1450 | 8.9677 | 52,275 / 52,343 |
| 0.9 | `70ab368b0bc118888b1e8ffd0ece6c8f2f6c7d28758c160c1e71efae96f17143` | 2.8172 | 8.9965 | 52,269 / 52,343 |
| 1.0 | `633838078ed7d0f329ef137689c119f559604578ec2850fb0f5506c3b686805a` | 3.5956 | 9.4934 | 52,271 / 52,343 |

The baseline is expected to be closest over the complete image because the
aligned holdout target is constructed from that teacher output before exact
character restoration. The relevant preflight signal is the unseen source
region: strength 0.7 reduces its mean absolute deviation from exact source
pixels by 11.5 percent versus the no-LoRA renderer. Per physical card, 0.7 is
best for Mewtwo and Charmander while 0.9 is narrowly best for Bulbasaur. Visual
preflight finds all three characters complete, card-safe, grounded by coherent
shadows, and anatomically intact, including Mewtwo's three-digit hands.

Strength 0.7 is therefore the sole human-review candidate from this bounded
sweep. It is not promoted: 52,275 fully opaque source pixels still change, so
the LoRA improves average identity fidelity without guaranteeing exact source
pixels. No longer training run starts before human review decides whether this
tradeoff is materially useful.

### Positive foreground-occlusion seed inventory (2026-08-05)

The initial clear-surface overfit intentionally contains only `avoid` examples.
Earlier one-shot renders are retained as complementary evidence rather than
discarded: the Generation-I individual-spatial 1-MP render at seed `260782266`
contains coherent small foreground crossings at Bulbasaur and Squirtle while
separate meadow vegetation remains behind them. Its raw SHA-256 is
`cf80fd3f0a2f909bb1d58ecc7f43c015431e074ff25adb86fdf4bdee785642ae`.
The Generation-VI seed `260758584` is a second visual source in which dense
flower-meadow vegetation stays clear or keeps one plausible depth layer.

These images are useful positive depth references, but they are not copied
directly into the paired-edit dataset. Their one-shot subjects satisfy the
production tolerance rather than the stricter training requirement for exact
canonical pixels, and exact subject restoration would draw over the very
foreground crossings to be learned. A future `front` or `mixed` gold pair must
therefore reuse only a separately reviewed foreground layer (or an equivalent
explicit depth result) over exact canonical subjects. The first such pair is
reviewed as a physical-card crop before any broader training run. No new model,
prompt branch, or production renderer is introduced by this inventory.

### Generation-I explicit foreground-pair preflight (2026-08-05)

The first bounded `front` candidate uses a fresh, subject-free Generation-I
mountain-meadow background rather than trying to erase the cast from a prior
one-shot. One deterministic erase/fill probe is rejected agent-side because it
repeats landscape fragments inside the subject regions; it is not eligible as
training truth and no prompt retry is spent on it.

The replacement text-only background uses seed `260726517`, the unchanged
native FLUX.2 Klein 4B BF16 stack, 848 x 1168 output, four Euler steps, and the
M4 Max MPS worker. The workflow SHA-256 is
`18e68abf442761a1a76aa2a298ea66a594c91e87225d5d180618c8fb8eba8005`;
the raw background SHA-256 is
`21a2a832417736f9de7494b9db1625234a0842d17d1b1ddec3784f2cb37c52d8`.
It contains a calm lower meadow plus real bottom-edge grass clusters and no
living subject, text, panel, path, or landing pad.

The rough reference alpha-composites the canonical Generation-I cast over that
background. The integrated scene adds only soft contact shadows. A tight RGBA
foreground layer then reuses pixels from one continuous blade already rooted
at the lower-left edge and is applied after exact subject restoration through
`compose-occlusion-target`. The immutable audit reports 62,563 fully opaque
source pixels: 130 are intentionally covered by the blade and all remaining
62,433 are byte-exact. The foreground-layer SHA-256 is
`194d1c0b6703e0af31c54ef36116fe5d4bf284c7dafaea2cceb4d651708c4d06`;
the pixel-identical CLI target SHA-256 is
`a10c881601fd0556f4ae1259385327a0a78dfdbd4792cbcf281d10e13eb928b6`.

This remains `candidate_pair_review`. Human review must pass the complete
artwork and all three physical lower-card crops, especially the continuity and
scale of the single blade in front of Bulbasaur. No audit entry changes to
`gold`, no dataset is rematerialized, and no training run starts before that
review.

Human review rejects this candidate. The 130-pixel intersection proves only
that the foreground-layer alpha touches the canonical subject mask; it does
not form a visibly continuous blade over the silhouette. The larger grass
clusters that read as nearest foreground still pass behind Bulbasaur and
Squirtle, so the target repeats the known depth contradiction. Its status is
`rejected_pair`, and it is excluded from every dataset.

This closes manual tight-polygon selection as the construction method. A
future `front` candidate must provide an actual isolated foreground object with
a continuous visible root and a human-readable crossing before the exact-pixel
audit is considered. Numeric overlap remains a reject-only consistency check,
never evidence of correct depth.

### Generation-I hard foreground augmentation (2026-08-05)

The next KISS candidate follows direct user guidance and is training-only. It
keeps the accepted subject-free meadow, contact shadows, and exact canonical
Generation-I cast, then places an intentionally obvious grass fringe as the
last layer. The fringe is rooted at the complete lower image edge and visibly
covers lower subject pixels in all three physical cards. It is not proposed as
production artwork; its sole purpose is to provide an unambiguous positive
depth example instead of asking a numeric mask intersection to imply depth.

The exact-source-aware compositor reports 62,563 fully opaque source pixels:
3,426 are intentionally covered by the hard foreground and all remaining
59,137 are exact. The foreground-layer SHA-256 is
`14e8053b229320f9671e26d0988d4e497fe60aec14c0c2e3ff2f26ae8b3e6ae8`;
the target SHA-256 is
`602aeaf0420cda199a06fa02b8f79e1ccca1c9efbac49347cd6eff86653c3d53`.
Human review accepts the hard Generation-I augmentation as a training example.
It is recorded as `gold`, `front`, and `train_candidate`; this approval does
not promote the image as production poster artwork.

### Positive-depth transfer holdout and overfit v2 (2026-08-05)

A second hard foreground pair is held out completely to distinguish learning
the depth rule from memorizing the Generation-I cast. Its subject-free Kalos
woodland-glade background uses seed `260726518`, native FLUX.2 Klein 4B BF16,
848 x 1168 output, four Euler steps, and the M4 Max MPS worker. The workflow
SHA-256 is
`1b69b9d14a51675fcd0b3845f0d6260b342bc5bcffcc3b5af0a8e682667ea90e`;
the raw background SHA-256 is
`90a805450fd5d6c5be1f38824c9c268e792497d17f584637a3a52cf7d5f8fc2a`.

Chespin, Fennekin, and Froakie come from a freshly built exact canonical
Generation-VI source reference. The rough input places that unchanged cast
over the new scene. The target adds contact shadows and one explicit bottom
foreground fringe after exact source restoration. Of 48,253 fully opaque
source pixels, 2,910 are intentionally covered and all 45,343 uncovered pixels
remain exact. The target SHA-256 is
`258b4f8df852ec8211f6ce2fd0e8a85bc650950ed8a0a1344667f897389269f3`.
This sample is `gold`, `front`, and `holdout`: it never enters training.

The materialized v2 micro-dataset therefore contains five training pairs:
four previously reviewed `avoid` examples plus the Generation-I `front`
example. Evaluation contains the existing Base-Set `avoid` holdout and the new
Generation-VI `front` holdout. The v2 training configuration changes only the
dataset and output names; all model, rank, optimizer, precision, MPS, and
100-loop settings remain identical to v1. This keeps the comparison bounded
to the additional positive-depth supervision.

The M4 Max completes v2 through MPS with exit code zero. One hundred loops and
gradient accumulation two produce 50 AdamW updates in 1:16:05; the final
reported loss is `0.1433`. The final 92,426,896-byte adapter has SHA-256
`04297534ed1041ee2cdcfdc5d2d7619642f51cf7acbb65643ff208aee1e1ab4e`,
160 BF16 tensors, 46,202,880 parameters, and zero non-finite values.

The fixed Generation-VI transfer comparison uses the same rough input, prompt,
seed `260726518`, four Euler steps, CFG 1.0, text encoder, VAE, and model stack.
Only the adapter changes:

| Candidate | Output SHA-256 | Uncovered-source MAE | Covered target advantage |
| --- | --- | ---: | ---: |
| Baseline | `2b8325727d97fd1cb5f5604749ca5e3976500506a0a5ce6217af8636b9ef31f2` | 48.9702 | +10.9532 |
| v1 at 0.7 | `0122f8528860bd029410423e616082d0bff876d1c5b458a37a64c390e4717a6b` | 47.5499 | +9.7908 |
| v2 at 0.7 | `0516d14386c9ea59482f9e839e17d06bd37038722a4894f9b4309b9818a968ac` | 31.7723 | -1.6245 |
| v2 at 1.0 | `c44f4c5d76fa1cb61616e4cf9ed1f68302fe41ce6614bdda649fd4974494aa60` | 14.9176 | -26.2676 |

Positive covered-target advantage means the output pixels in the intended
subject/foreground intersection are closer to the hard foreground target than
to the uncovered source. Visual review is decisive: neither v2 strength draws
the required continuous plants in front. The stronger adapter instead copies
the supplied characters much more faithfully. V2 therefore fails the depth
transfer gate but supplies useful evidence for identity preservation; it is
not promoted and production routing remains unchanged.

The v2 pair asks the model to invent a foreground fringe that is absent from
the rough input. The next isolated hypothesis removes that ambiguity: compose
the identical fringe behind the exact subjects in the input and in front of
them in the target. The only intended learned edit is then layer ordering.
Because that difference occupies fewer than one percent of the full raster,
the trainer's supported focus mask is limited to this pair and keeps a small
global loss floor; no new inference node or production branch is introduced.

### Layer-order focus overfit v3 (2026-08-06)

V3 keeps the same five training scenes, base model, rank, optimizer, BF16 MPS
path, and 100-loop budget. Its Generation-I rough reference now composites the
same foreground fringe before the exact canonical cast; its target composites
that fringe after the cast. The input SHA-256 is
`bc2fe2d224d254ca53eb07caff90acb60a3b58087707f985d00caf0233e2db17`.
All 62,563 fully opaque source pixels remain exact in the input. Input and
target differ at only 3,971 raster pixels, 3,349 of them within fully opaque
source pixels.

The matching trainer focus mask is derived only from that deterministic pair
difference, expanded to several latent cells, and softly feathered. Its
SHA-256 is
`56df1c301f7983f697a2c6f3bdeb1789f4ec6c2e8faa850b1bfb26a09b96996e`;
55,463 pixels carry at least half strength and 95,930 carry any focus weight.
Only this positive pair has a matching mask file. The trainer's
`mask_min_value: 0.1` preserves a small global loss contribution; the four
`avoid` pairs retain ordinary unmasked loss. The Generation-VI holdout receives
the same behind-versus-front construction but remains outside training. Its
corrected input SHA-256 is
`599ba64e11da8afe87145027cae0d3e9fc934393d754af31cbd98cf5b8eca657`.

The M4 Max completes v3 through MPS with exit code zero in 1:13:38. Trainer
timers repeatedly report `get_mask_multiplier`, confirming that the focus mask
participates in loss calculation. The final 92,426,896-byte adapter has
SHA-256
`3b719fc4a82d85e864c860b5fbf568ddb5ab5b4a08cf169fbb24f7b0b114fa58`,
160 BF16 tensors, 46,202,880 parameters, and zero non-finite values.

The corrected Generation-VI holdout compares the same input, prompt, seed,
sampler, and four-step MPS graph. V3 strength is the only swept value:

| Candidate | Output SHA-256 | Uncovered-source MAE | Covered target advantage |
| --- | --- | ---: | ---: |
| Baseline | `bbd081a38bc5e8e39f8b62ca5766ef3f7c6893d5c5d21501f0632ef6a5d682f0` | 46.1445 | +12.9656 |
| v3 at 0.3 | `2f125005ddb80d739c96bea2bdb244fb8f7cde7c03663113e51666cdeef80937` | 31.6755 | +1.7947 |
| v3 at 0.5 | `7e60128709eacd9c2ab479270c714c2adba6676bc1208c297310d6097c896581` | 13.4591 | -28.6236 |
| v3 at 0.7 | `f08d926aca66b03882e9a3939e41b5b8910e4a3ee08d2ba54ece06778833a17c` | 8.8791 | -46.3654 |
| v3 at 1.0 | `856a377d8b0fc432dc4594c48a05db4e5548224efb1351192baab2f80fb7a6c5` | 7.6872 | -59.8846 |

The focus pair teaches a measurable transition but does not remove the core
tradeoff. Strength 0.3 retains some generative foreground behavior while
improving identity over baseline. Strength 0.5 and above increasingly preserves
the supplied source pixels and therefore also preserves the incorrect
behind-subject layer order. No v3 strength is promoted automatically. The 0.3
candidate is the only bounded human-review candidate; deciding whether its
remaining character changes are acceptable requires visual review.

### Balanced layer-order overfit v4 (2026-08-06)

V4 tests one remaining KISS hypothesis before requiring a product tradeoff. It
reuses every v3 pixel and mask, but splits the four `avoid` scenes and the one
`front` scene into separate trainer datasets. The front dataset uses
`num_repeats: 4`, so positive layer-order supervision is balanced against the
four ordinary integration examples instead of appearing once in five samples.
Its caption now explicitly requests reordering the already-present nearest
plants in front of lower feet or legs while preserving exact character design.
The caption SHA-256 is
`3a681de8d906c5841778d2e0fa3a5dee1dabfabfa42ecae0aae4ec2fa02a4581`.

The immutable scratch manifest SHA-256 is
`bc34844e8e672e0e668cfb413ff2137a71bd16449a9fc48f90079ece1324c49a`.
Model, rank, precision, optimizer, learning rate, 100-loop budget, focus mask,
global mask floor, and holdout remain unchanged. This isolates supervision
balance and task wording without adding inference complexity. Success means a
higher adapter strength retains visible front crossings on the unseen
Generation-VI holdout while improving identity over v3 strength 0.3.

The M4 Max completes v4 through MPS with exit code zero in 1:12:54. The
trainer again reports `get_mask_multiplier` throughout the run. The final
92,426,896-byte adapter has SHA-256
`5ff2a81c2ffa8b7442662d5de03d7fadd2f1b28da26a9b9be42a47e6a2cfd7ea`,
160 BF16 tensors, 46,202,880 parameters, and zero non-finite values.

The unchanged Generation-VI holdout produces the following fixed-seed result:

| Candidate | Output SHA-256 | Uncovered-source MAE | Covered target advantage |
| --- | --- | ---: | ---: |
| Baseline | `bbd081a38bc5e8e39f8b62ca5766ef3f7c6893d5c5d21501f0632ef6a5d682f0` | 46.1445 | +12.9656 |
| v3 at 0.3 | `2f125005ddb80d739c96bea2bdb244fb8f7cde7c03663113e51666cdeef80937` | 31.6755 | +1.7947 |
| v4 at 0.3 | `624acdc79c81c08ac545534e20a50c1acbede97177756b51886c0f41aaedf432` | 42.0955 | +10.8172 |
| v4 at 0.5 | `266e19f80b0708efd2f9d5a7789bc7b135a8dac1914604f43b5b20da8ccc1425` | 36.5707 | +9.2090 |
| v4 at 0.7 | `fa15d8d09f69423dfb9781af96c9b9b3635437cfa1b10659819c848ac6a463e3` | 30.7003 | +6.5175 |
| v4 at 1.0 | `9a17a1031eee564a007e104632e4b23fbd3a60da42e070aeb6ffd170d04d538d` | 27.2228 | +7.7565 |

Balancing the positive pair changes the learned behavior: unlike v3, every v4
strength keeps a positive foreground-target advantage. Visual card review also
shows continuous foreground blades rather than abrupt generated fragments.
However, v4 does not meet the combined gate. Its figure colors, shading, and
line treatment remain visibly farther from the supplied source than strong v3,
and increasing strength does not recover v3's identity fidelity. V4 is not
promoted and production routing remains unchanged.

Repeating one Generation-I pair has therefore exhausted its useful evidence.
The next bounded hypothesis replaces repetition with several deterministic
positive layer-order pairs covering different characters and environments,
while retaining ordinary `avoid` pairs and the untouched Generation-VI
holdout. This changes training diversity only; it adds no production node or
inference branch.

### Diverse layer-order overfit v5 (2026-08-06)

V5 replaces v4's four repeats of one positive scene with five distinct
positive scenes spanning Generations I through V. The four existing ordinary
`avoid` pairs remain unchanged, so the materialized micro-dataset contains
four avoid samples and five front samples with no repetition. Generation VI
remains the untouched transfer holdout.

The four new training-only pairs are deterministic composites over the already
reviewed Generation-II through Generation-V scenes. Each reference contains
the same rooted foreground layer behind the exact canonical characters; each
target moves only that layer in front. Every target keeps all opaque canonical
pixels exact outside the intentional intersections. Per-card intersection
audits reject any pair with fewer than 100 covered opaque source pixels. The
accepted new pairs cover between 749 and 2,138 opaque source pixels per lower
card and between 2,998 and 4,143 per full scene.

The v5 manifest SHA-256 is
`d88c41007e9eadc730f8d8c8c68ccc6bcb5488117973254d6fd5a0aed1fa7e2f`;
the shared front caption SHA-256 is
`2ed8aebca4c76cc7b08116c73c685d9881d0e1a2b38bd19db71a30d82da239dc`.
The trainer configuration SHA-256 is
`badb2a0e67afb2b2e70a19a508b7b4f036203dd0bde64fdcbed922aea39f1919`.
Model, MPS/BF16 path, rank, optimizer, learning rate, focus-mask floor, and
100-loop budget remain identical to v4. Success requires both positive
foreground transfer and materially better source identity on the fixed
Generation-VI holdout; the adapter must satisfy both gates at the same useful
strength.

The M4 Max completes v5 through MPS with exit code zero in 1:12:21. The final
92,426,896-byte adapter has SHA-256
`239fa9519b8ebea50ecbf04c25ec0430a6ed2a879ca34eda3e5ec844d1bceccf`,
160 BF16 tensors, 46,202,880 parameters, and zero non-finite values. Trainer
timings report `get_mask_multiplier` in every ten-loop block.

The unchanged Generation-VI holdout produces:

| Candidate | Output SHA-256 | Uncovered-source MAE | Covered target advantage |
| --- | --- | ---: | ---: |
| v3 at 0.7 | `f08d926aca66b03882e9a3939e41b5b8910e4a3ee08d2ba54ece06778833a17c` | 8.8791 | -46.3654 |
| v4 at 0.5 | `266e19f80b0708efd2f9d5a7789bc7b135a8dac1914604f43b5b20da8ccc1425` | 36.5707 | +9.2090 |
| v5 at 0.3 | `42e2c9d472bcc583a3480bb81062b3a11c545e16415292abf896f3f0ed8a9cab` | 46.0644 | +14.2391 |
| v5 at 0.5 | `7ef3e353b8cf7661c984108bc5cd888d51d84a82239a98ae9c460ae8f38c9bf9` | 45.0478 | +15.6403 |
| v5 at 0.7 | `e264a5aa4cd483593c178aaf0c862de6d49a44c83bee2380cc645b3a2fad372b` | 43.8690 | +21.7622 |
| v5 at 1.0 | `ddf6daa9fedf885bd57da6f0053f1844508e777216463cc028e1c12c45a549a0` | 37.9999 | +24.8648 |

V5 generalizes the requested foreground ordering more strongly than v4: every
strength keeps continuous front crossings, and target advantage increases with
adapter strength. It does not recover source identity. The supplied characters
retain recognizable anatomy but acquire substantial color, brightness, and
line-treatment changes at every strength. V5 therefore fails the combined gate
and is not promoted.

V3 and v5 now isolate complementary behavior: v3 strongly preserves identity
while v5 strongly transfers layer ordering. Before creating another dataset or
training run, one bounded inference-only check may stack the existing adapters
at fixed strengths. This is evidence gathering only. A stacked result must
improve both metrics and visual card crops; otherwise the added runtime node is
discarded rather than becoming production complexity.

### Stacked identity/depth adapter check (2026-08-06)

The bounded inference-only check chains the unchanged v3 adapter before the v5
adapter in ComfyUI. The base model, input, prompt, seed, sampler, and four-step
graph remain fixed. Four broad combinations and two interpolated v3 strengths
are rendered on MPS; no adapter is merged or promoted.

| V3 strength | V5 strength | Output SHA-256 | Uncovered-source MAE | Covered target advantage |
| ---: | ---: | --- | ---: | ---: |
| 0.5 | 0.7 | `431ed88798a20783425ff6ba5a240108a982416c7f81c097b8c20edee2d6e159` | 14.1285 | -0.6643 |
| 0.5 | 1.0 | `33c2a2f8b74efff27912cb29808bd08e119f2bb2c1a653181316f6f58cb99919` | 14.3280 | +3.1365 |
| 0.6 | 1.0 | `a6cd3e08132ec39730d932076f7b5aa94cae21f80b364fd2193e94d1eb44b9ac` | 13.7707 | +3.4633 |
| 0.65 | 1.0 | `629170535a76194d4c4bf57b99c9dd41006e9f4da821ca469413bac062a90f80` | 13.1623 | +0.4577 |
| 0.7 | 0.7 | `efecbbec12790178ae0a5386f9365834a194a7207193410df71098fcebf24307` | 11.0740 | -9.0765 |
| 0.7 | 1.0 | `3c6729e2889ae39070160e472ac33a1db346e7b9bb0533ef9b0aacc5b6db4fbe` | 13.0083 | +0.9537 |

Stacking supplies the first candidates that pass both numeric directions in
one render. Strengths v3 0.6/v5 1.0 give the best foreground advantage while
v3 0.7/v5 1.0 gives the best source MAE among positive-depth candidates; v3
0.65/v5 1.0 lies between them. These values qualify the three candidates for
human review only; they do not establish correct layer order.

Human review rejects all three stacked candidates. On Chespin, Fennekin, and
Froakie, supposedly nearer rooted blades partly merge with feet or legs, stop
at a silhouette, or continue behind the character. The result reads as grass
passing through the figures rather than one continuous foreground object
remaining in front. No stacked adapter is promoted and the production graph
remains unchanged.

This review exposes a false-positive evaluation path. `Covered target
advantage` compares colors inside the intended overlap mask, so recolored or
darkened character pixels can improve it without forming a coherent foreground
contour. From this experiment onward it is diagnostic and reject-only: a
positive value can nominate a crop for visual inspection, but cannot approve
occlusion. Approval requires every connected foreground object to preserve one
plausible depth relationship across the complete intersection, without
disappearing into a character, reappearing on its other side, blending into an
appendage, or leaving a foot visibly on top of an object that should be nearer.

Further seed or scalar-strength sweeps are stopped. The next bounded hypothesis
is a minimal explicit occlusion guide evaluated in the same generative pass.
It may describe a small connected foreground crossing, but must not become a
post-generation character or vegetation composite. If that guide does not
produce a clean continuous crossing while retaining identity, the safe
production behavior remains avoiding character/foreground intersections.

### Explicit occlusion-guide check (2026-08-06)

The minimal guide check uses the same Generation-VI holdout, seed, 848 x 1168
canvas, four-step FLUX.2 Klein graph, and M4 Max MPS worker. It changes only
how the required foreground order is supplied.

The first variant uses the reviewed hard-front image itself as the sole edit
reference. The baseline workflow SHA-256 is
`76dc59c697b5a3b7dd2b6ff8a64e53f4f4e47a4a8f9ce5fb5974f73a74307095`;
its output SHA-256 is
`2c63022d314ddcaf847b1463a98cbb6a38eba28f15a81af004f82045ec680750`.
V3 at strength 0.7 uses workflow SHA-256
`21ed9aba7a10bedb8c378817eb844d9989e905958c173c54dc59bc35bf1862ab`
and produces
`0334cb482e61e2a7c2a7d93c2efb6ce4a6db673c99ee2d4b542e22672329ca8c`.
Both preserve the requested front order, but also preserve the hard polygonal
guide shapes. They therefore solve topology by retaining a visibly artificial
input layer rather than integrating natural vegetation and are rejected.

The second variant restores the clean rough scene as IMAGE 1 and supplies a
registered black-and-white occlusion diagram as IMAGE 2. The baseline workflow
SHA-256 is
`026443e13ff1ad3f0d3e1d14c9cf36cb9236d25b37a32bf255be401c02c50eca`;
its output SHA-256 is
`de01bee0669569b3f445e0b2e8b70e2cbc8d6d47ea837024a8f0101b4e581334`.
V3 at 0.7 uses workflow SHA-256
`9d1c97c29365e10f2e534655d8d55cf47174ae1c3db18a5349c9f32dcd7a7e14`
and produces
`6b4f48d3ccdd33cb8254050207a1004bd161dbd2b7525ea7de045ea776b5b4f2`.
Both largely ignore the diagram and generate no reliable foreground crossing.
Adding another ordinary `ReferenceLatent` therefore does not provide structural
occlusion control and is rejected.

The bounded guide series stops here. No guide, adapter stack, or extra
production node is promoted. The simple production policy is instead to prefer
natural separation between landscape elements and character silhouettes. A
remaining intersection must still be coherent, but prompts should arrange
nearer objects around a character before asking the model to solve a crossing.
The wording explicitly forbids halos, artificial gaps, and character-shaped
clearings. This policy is a new versioned generation contract: historical
promotions continue to validate against their exact old prompt, while freshly
prepared workflows use the new avoidance-first wording.

### Masked occlusion-control check (2026-08-06)

The supplied layered-inpainting proposal is tested on the same Generation-VI
fixture without SAM, ControlNet, another model, or a global rewrite. The exact
rough composite is the immutable destination. A registered foreground mask is
the only region that may be sampled, and `ImageCompositeMasked` restores every
pixel outside it from the exact input after VAE decoding.

The initial `VAEEncodeForInpaint` mask includes the rooted lower foreground
strip. At denoise 0.55 the neutral mask fill remains visible; at 1.0 the model
adds plants but leaves large pale gaps. `InpaintModelConditioning` at 1.0 does
not improve those gaps with the standard FLUX.2 Klein checkpoint. Narrowing the
mask to rooted plant silhouettes removes the broad gap but retains visibly
mask-shaped light regions. These paths are rejected.

Normal `VAEEncode` followed by `SetLatentNoiseMask` avoids the neutral fill.
At denoise 0.7 it produces natural vegetation and preserves every pixel outside
the mask exactly. The audit finds zero changed pixels among 883,127 pixels
outside the mask and zero changed fully opaque subject pixels outside it;
13,948 fully opaque subject pixels lie inside the intentional mask. Visual
review still rejects the result because partial denoise blends some original
feet and legs into the generated vegetation instead of establishing an opaque
front layer. Full denoise 1.0 removes that translucency but replaces the
crossings with ground-colored smears rather than connected plants. Its final
output SHA-256 is
`08f22035e02c7c8ff4d9b83fa87ba14bc55d3c70c9899396b133166d5e18117f`.

A final deterministic probe selects dark vegetation from the clean landscape,
restores those original pixels in front, and confirms a separate limitation:
plant segmentation alone does not encode depth or protected anatomy. The
selection places tall vegetation over Chespin's and Froakie's faces. SAM could
improve the silhouette selection but would not by itself decide whether that
plant belongs in front, behind, or outside a protected subject region.

The useful result is therefore narrower than the generic recipe. A noise mask
can guarantee the mutation boundary and preserve exact identity outside it. It
is suitable for a manually or structurally approved contact-shadow mask and
for a verified natural foreground object whose depth is already known. It does
not infer correct z-order from a plant label and is not promoted as automatic
occlusion repair. Production remains avoidance-first; ambiguous intersections
are rejected rather than repaired through a larger automatic mask stack.

All successful render processes in this check report `Device: mps`. The first
submission also exposes a worker-safety issue: another user's ComfyUI Desktop
was listening on the default port, so the job reached the wrong input directory.
The queue client now includes ComfyUI's HTTP validation body in failures, and
the render worker verifies the server's reported input directory before
submitting any workflow.

### Avoidance-first rollout contract (2026-08-06)

The guide, adapter-stack, and masked-inpainting branches are closed after their
bounded failures. Production remains the same KISS one-shot graph: positioned
identity references, one empty target, one FLUX.2 sampler, one decode, and
deterministic print resampling. Only the central prompt policy changes.

Pipeline v9 treats each mandatory character silhouette bound plus two-percent
clearance as an invisible no-crossing volume for camera-near landscape
elements. The landscape must continue as ordinary low ground and subtle texture
beneath the character, while tall grass, leaves, flowers, branches, rocks,
water edges, and comparable scenery are moved outside the volume or clearly
behind it. Halos, isolated clearings, paths, platforms, landing pads, and
character-shaped gaps remain forbidden. The prompt no longer asks the model to
produce a visible foreground crossing.

All 41 configured poster targets now have their required local Official Artwork
cutouts and title logos. The next batch creates fresh v9 review candidates; no
candidate becomes a promotion or enters PDF routing before human review.

### Complete avoidance-first candidate batch (2026-08-06)

All 41 configured targets were rendered from scratch on the remote M4 Max with
128 GB unified memory. Every ComfyUI process reported MPS, used the unquantized
BF16 FLUX.2 Klein 4B model, the `individual_spatial_joint` v9 prompt, four
sampling steps, one decode, and deterministic Lanczos resampling to the exact
2368 x 3268 print raster. No character composite, inpainting pass, vegetation
repair, or learned upscale was added.

The technical audit accepts all 41 selected candidates: every poster has
effective 300-dpi metadata, a unique SHA-256, non-blank pixels, and nine exact
physical card crops. The visual pre-screen retains 30 configured-seed renders
unchanged and replaces eleven bounded failures:

- ExGen3 Mega, ME02, ME03, MEP, Pokédex Generation VIII, SV06, SV06.5, and SVP
  use one `configured seed + 1` retry after the first render produced a clipped
  subject, wrong identity, or an extra subject.
- SV09 uses seed `260747621`; Reshiram is again white and anatomically faithful
  instead of the first candidate's red dragon-like reinterpretation.
- Base3 keeps seed `260755492` but now deliberately features the in-set,
  card-safe Kabutops, Lapras, and Gengar. Two bounded bird-seed retries are
  rejected because the three flying reference poses moved into the title area,
  disappeared from a card, or lost identity.
- SV07 keeps seed `260726008` but now deliberately features the in-set,
  card-safe Bulbasaur, Squirtle, and Scorbunny. Its Celebi/Reshiram/Scorbunny
  candidate and one seed retry are rejected for edge clipping and duplication.

The two curated selections are stored in the ordinary fetch configuration and
scope JSON, with official cutouts and regression coverage. They are not
renderer exceptions. This establishes a useful general boundary: when a valid
set offers several representative subjects, input curation is simpler and more
reliable than adding generation nodes or sweeping seeds for an inherently
card-hostile pose.

The selected 41-poster batch remains review-only. It does not replace the
current promotions or enter PDF routing until the contact sheets and relevant
full-resolution candidates receive explicit human approval.

### Avoidance-first visual promotion gate (2026-08-07)

The complete v9 contact sheets, full-resolution posters, and physical lower
card row were reviewed again after the user identified three suspect scopes.
Thirty-eight candidates pass cast count, Official Artwork identity, defining
anatomy, complete card containment, grounding, scene continuity, and the
avoidance-first landscape boundary. Their exact BF16 raw and 2368 x 3268 print
pixels are promoted and PDF-enabled; the promotion validator accepts all 38
bundles and all 342 physical card slices at effective 299.99 dpi.

Two candidates fail closed and remain disabled:

- `ExGen2/sections/primal` materially redesigns both Primal forms rather than
  preserving Primal Kyogre and Primal Groudon.
- `SV04.5` changes defining character anatomy in the lower row.
These are visual failures, not print or metadata failures. Their technically
valid review files remain local scratch only, and the existing cover route is
the production fallback. The next bounded render work is limited to those two
scopes; no prompt or graph complexity is added to the 39 passing paths.

The first retry for `SV08` (seed `260751064`) was separately reviewed and
passes: Ho-Oh appears exactly once, Kyurem and Fuecoco retain their defining
forms, and all three subjects remain complete inside the lower card row. It is
promoted and enabled with the same v9 contract.

### Targeted v9 replacement rerender (2026-08-07)

The next bounded seed attempt was run on the M4 Max through MPS with the
unchanged BF16 Klein 4B / `individual_spatial_joint` v9 contract:

| Scope | Seed | Result |
| --- | ---: | --- |
| `ExGen2/sections/primal` | `260759902` | Rejected: Kyogre is duplicated and Groudon is still materially redesigned |
| `SV04.5` | `260789456` | Rejected: Mew again loses its three pointed hand fingers |
| `SV08` | `260751064` | Accepted and promoted: one Ho-Oh, faithful Kyurem/Fuecoco, complete lower-row containment |

The two rejected targets remain on the cover fallback. Seed variation is not
silently treated as a universal fix; further work stays scoped to those two
targets and must preserve the same hard identity gate.

### Primal duplicate-cast diagnosis (2026-08-07)

The Primal retry was traced before any deterministic print processing. The
ComfyUI raw output already contains the extra Kyogre; the 300-dpi resize,
poster text overlay, and nine-card slicing only carry that error forward. The
run uses one `EmptyFlux2LatentImage` with `batch_size: 1`, two official cutouts,
two positioned reference images, and one sampler. There is no character
composite or second post-generation render path that could create a duplicate.

The two-subject count is therefore a contributing model risk, not a renderer
bug or an unsupported configuration. `individual_spatial_joint` chains one
full-canvas `ReferenceLatent` pair per subject globally into the same positive
and negative conditioning; it does not assign each reference to a local
conditioning region. With only two subjects and a deliberately open center,
FLUX.2 can resolve the two global references plus the textual pair description
as more than one scene/cast, despite the explicit `render exactly these 2
characters once` instruction. The same graph with seed `260759901` produced a
single pair (but failed edge containment), while seed `260759902` produced the
duplicate. This makes the failure stochastic and amplified by the sparse
two-subject composition, not a deterministic “two Pokémon means duplicate”
rule. No production graph change is promoted from this diagnosis.

### ExGen1 Normal approval revocation (2026-08-07)

Human re-review applies the same hard identity gate to the previously enabled
`ExGen1/sections/normal` poster as to the rejected `SV04.5` candidate. In both
images Mew's canonical three pointed hand fingers are replaced by smooth blunt
ends. ExGen1 Normal is therefore PDF-disabled again and returns to the normal
cover fallback. Its exact tracked promotion remains available only as review
evidence until a replacement is approved; the artwork is not treated as a
passing production result.

The accumulated controlled tests close generic prompt, seed, reference-size,
Klein-9B, and FLUX.2-Dev escalation as a reliable Mew-finger fix. The practical
bounded replacement path is scope-valid subject curation for sets with several
representative Pokemon. Primal cannot use that escape hatch because its two
canonical forms define the section; its next isolated test uses the already
supported joint cast-layout reference so both forms enter the model as one
count-and-position composition, while separate identity references retain
their exact form details.

### Sparse regional Primal cast (2026-08-07)

The joint cast-layout probe removes the duplicate but generates both Primal
forms too large and about one card row too high. Its lower physical-card crops
therefore remain incomplete. This rejects the joint cast reference as the
placement mechanism, not the useful diagnosis that the duplicate came from
globally applied per-subject spatial references.

The next bounded run reuses the existing `regional_identity_joint` graph. A
small generalization removes its unnecessary exactly-three-subject guard and
derives regional cells from the canonical placement contract already used by
the other workflows. Two subjects consequently occupy the outer bottom cards;
three and four subjects retain their existing behavior. There is still one
empty target, one sampler, one decode, and no pixel composite or repair pass.

The M4 Max MPS run keeps scope, seed `260759901`, BF16 FLUX.2 Klein 4B, Qwen
4B encoder, VAE, 848 x 1168 canvas, four Euler steps, scene brief, and exact
official artwork inputs fixed. Only the conditioning strategy changes.

| Artifact | SHA-256 |
| --- | --- |
| Workflow | `078fe8232ebdbd0c34d56034a175b7f2be5e499d4d6bd400d4a85f2ec895b44f` |
| Raw 848 x 1168 artwork | `cfb61fb299b631ab7096b9879ced1cf57b818336a54007d55f9ca3a43744e6b3` |
| 2368 x 3268 text-free artwork | `47105cae0b5131a7c181e2b8f51c214ef31d1dafb374925943baa96cf4c33223` |
| English review poster | `632d81b40da156c33ec94de47f09771caa4a98c7aed9bf2ebedf31bcfaeb75ac` |

The candidate contains exactly one Primal Kyogre in the left card and exactly
one Primal Groudon in the right card. Both silhouettes, appendages, markings,
poses, and shadows remain close to the official references; both are complete
with useful card-edge padding and coherent contact with the generated coastal
stone. No landscape element crosses either silhouette inconsistently. Agent
review therefore advances this render to human review. It remains disabled
and unpromoted until that approval.

### Mew holdout closure and curated replacements (2026-08-07)

One final `SV04.5` isolation applies `regional_identity_joint` to the original
Charmander, Pikachu, and Mew cast at seed `260789455`. It removes reference
competition and keeps Mew's overall pose, silhouette, face, tail, and body
close, but the left hand is again a smooth stump and the right hand still does
not retain three distinct pointed fingers. The raw SHA-256 is
`baf2379c011d26e69cffed9c4a5c0b5c2e38ccdce07438271d8dd03f756e4472`.
This closes regional binding as a fine-anatomy fix for Mew; the failed render
is not promoted.

Both affected scopes now use ordinary, reproducible input curation rather than
a prompt or renderer exception:

- `SV04.5`: Charmander (`sv04.5-007`), Pikachu (`sv04.5-018`), and Lapras
  (`sv04.5-016`).
- `ExGen1/sections/normal`: Venusaur (`ex6-112`), Blastoise (`ex6-104`), and
  Lugia (`ex10-105`).

The card IDs live in `section_featured_card_ids`; regenerated scope JSON,
official artwork cutouts, and regression tests make the choice survive future
fetches. Obsolete Mew and Mewtwo bundle cutouts are removed. This is a change
of featured poster cast only, not a change to either scope's card content.

The first curated renders deliberately reuse the production
`individual_spatial_joint` mode. `ExGen1/sections/normal` passes agent review:
all three official reference poses and defining anatomy remain recognizable,
the cast appears exactly once, and every silhouette fits its lower card. Its
raw SHA-256 is
`ba95338bdb97ade1bd82d46eb01bdb776bf2f470bcaee24cdc73e6c596e9a778`;
the English review poster SHA-256 is
`2ce1a666643245a44c6c4e28552df00fd79c1670691f1283cdba411b2fe43894`.
Blastoise's rear three-quarter pose is not generated pose drift: it matches the
official artwork input.

The same global-reference mode fails `SV04.5` by producing two Pikachu and two
overlapping Lapras. The curated cast is therefore tested once with the already
retained regional graph rather than with more prompt text. Seed `260789455`
has the correct count and identities but places Pikachu's extended left hand
on the physical-card edge. One bounded regional retry at seed `260789456`
moves all three complete silhouettes inside their cards while keeping their
official poses and anatomy close, coherent ground contact, shadows, and one
continuous moonlit scene. Reproducibility evidence:

| Artifact | SHA-256 |
| --- | --- |
| Regional workflow | `b1a64f5aeba86a879de51937e1dccecc30cad2dfba660955c366173c755601a8` |
| Raw 848 x 1168 artwork | `719ed39874fff61a3bfe85d04bd49b367809527ed1de465818e7c7b87419ce75` |
| 2368 x 3268 text-free artwork | `938663ef85b0b0e18c1a39e2098ad13a3473f44c4e80ec571b05d1ab5aad8a22` |
| English review poster | `d719f8ef6d84772c4d050e5f34987cdf356092b7d780e06d92821518c9fd35ec` |

The `SV04.5`, `ExGen1/sections/normal`, and Primal candidates advance to human
review together. All three scopes remain PDF-disabled and no review pixels are
promoted before approval. On approval, ExGen1 retains the normal
`individual_spatial_joint` default; SV04.5 and Primal record
`regional_identity_joint` and their reviewed seeds in their manifests.

### Regional scene discontinuity audit (2026-08-07)

Human review correctly rejected the claim that the regional candidates form a
fully continuous landscape. Their lower subject zones can be anticipated as
future physical cards because terrain, horizon, atmosphere, or lighting changes
inside each zone.

The cause is structural. Each regional branch attaches a complete 512 x 512 RGB
identity reference to its own masked conditioning. The reference contains the
subject on a flat neutral field, and `ReferenceLatent` passes the complete VAE
latent rather than an alpha-isolated subject. FLUX therefore predicts some
local scene content independently for each identity branch. Hard physical-card
areas made this explicit; non-card-aligned feathered masks soften the seam but
cannot make independent regional predictions share one geography.

The bounded audit changed one factor at a time:

| Probe | Result | Decision |
| --- | --- | --- |
| Keep the global landscape additive throughout every region | Restores terrain globally, but the subjects disappear at equal strength | Retain only as diagnosis |
| Global strength `0.20` to `0.35` | The local fields remain while Charmander and the other identities weaken | Reverted in commit `7a998de`; no more strength sweep |
| Remove all scenery, lighting, and rendering descriptions from local prompts | Eliminates repeated prompt-driven moons and rainbows, but latent-driven local terrain remains | Retained as regional pipeline v19 because it is a strict improvement |
| Give every local branch the same generated full-frame landscape reference | Each mask redraws that full scene as a miniature local vista, including repeated horizons and moons | Rejected |
| Give only the global branch that landscape reference | The common scene survives better, but local identity branches still create visible side vistas | Rejected; a two-pass scene plate does not solve regional conditioning |

The existing mask-free `spatial_identity_joint` topology is therefore the
correct KISS solution whenever its cast is stable. A same-seed rerun of the
curated `SV04.5` Charmander/Pikachu/Lapras cast produces one continuous
moonlit meadow, exactly three complete subjects in the lower cards, and no
regional landscape fields. Raw SHA-256:
`6dbecdfeafd8f9bb1888fbfc61f0e2eeeb3c782f52db199af99480669826ac88`.
It advances to human review but is not promoted or PDF-enabled yet.

Primal reaches a real constraint boundary rather than the same easy switch:

- the global two-reference workflow can keep one pair, but enlarges both broad
  forms beyond their individual cards;
- shrinking those two independent references duplicates both forms;
- a shared cast plus detail references duplicates Groudon when the cast is
  reduced;
- a single high-resolution cast duplicates both forms and materially changes
  Kyogre;
- regional conditioning preserves exactly one recognizable Primal Kyogre and
  one recognizable Primal Groudon inside their cards, but larger regions create
  the landscape discontinuity under review.

One final moderate-mask probe uses soft regions 1.15 times the target width and
1.35 times its height. It keeps the single pair and greatly reduces the visible
side panoramas, but the subjects become deliberately small. Raw SHA-256:
`23510f58d2d0d6afdad8af1460a309b7d37be34aad7548dc951637c601450448`.
It is review-only. No Primal option is promoted until human review chooses
between smaller card-safe subjects with better continuity and the larger
regional composition with more visible local scene variation. The mutually
incompatible requirements are not hidden behind another prompt or seed sweep.

### Curated holdout promotion and bounded close (2026-08-08)

Human review accepts the continuous mask-free `SV04.5` candidate and confirms
that the curated ExGen1 Normal replacement should be activated. Promotion uses
the already reviewed pixels; no rerender, compositing, repair pass, or learned
upscale is introduced.

| Target | Active contract | Seed | Raw SHA-256 | 300-dpi text-free SHA-256 | Decision |
| --- | --- | ---: | --- | --- | --- |
| `ExGen1/sections/normal` | individual-spatial v9 | `260737078` | `ba95338bdb97ade1bd82d46eb01bdb776bf2f470bcaee24cdc73e6c596e9a778` | `80457937f2507257f9ff45a82e6826e567c86186f0de379b109374d249a860ea` | Venusaur, Blastoise, and Lugia promoted and PDF-enabled |
| `SV04.5` | spatial-identity v7 | `260789456` | `6dbecdfeafd8f9bb1888fbfc61f0e2eeeb3c782f52db199af99480669826ac88` | `05a519ec108167e8eec28f50410252c8be294d90100aedf99a7d215cb15d8c6b` | Charmander, Pikachu, and Lapras promoted and PDF-enabled |

Both promotions produce the stable text-free master, localized preview, nine
physical-card slices, and complete provenance. The validator accepts all 40
enabled bundles at 2368 x 3268 px and effective 299.99 dpi. Fresh German
no-card-image PDFs confirm cover, poster, and first-card-page ordering plus the
localized overlays for both targets.

`ExGen2/sections/primal` is deliberately not promoted. The visually reviewed
regional option contains an impossible second horizon/water layer, while the
other bounded options fail identity, count, containment, or continuous-scene
gates. The normal Primal section cover is therefore the sole production
fallback. This closes the current rollout at 40 of 41 configured targets
without weakening a hard visual requirement or adding another production
workflow.

### Poster-first PDF migration and clean German rebuild (2026-08-08)

Human review confirms that a promoted poster is the section's start page rather
than an additional page after the canonical cover. The PDF generator now makes
that choice at one boundary: an enabled, consumable poster replaces the cover;
otherwise the existing cover is rendered. This keeps `--skip-poster` and the
disabled `ExGen2/sections/primal` route as automatic cover fallbacks without a
second PDF mode or scope-specific branch.

The German output directory was cleared and rebuilt from an empty state with
the normal production command for all 30 scopes. The run completed with 30
successes and no failures. Every resulting PDF is readable and every first page
is a rasterized poster page. Final visual QA covers representative Base Set,
Pokédex, EX-generation, and Scarlet/Violet pages. The aggregate ExGen2 PDF was
also checked at every section boundary: Normal and Mega begin with their
approved posters, while Primal begins with the canonical cover on page 18.

The focused PDF tests, all 40 promoted-bundle validations, and the full project
suite pass after the migration. No `TEST`, `NO_IMAGES`, or `NO_POSTER` artifact
remains in `output/de`.

### Primal landscape-first hybrid promotion (2026-08-10)

Manual ComfyUI editing isolated the Primal placement failure to prompt
hierarchy rather than reference count. A compact 230-word prompt made the vast
landscape, empty upper canvas, small lower-corner subjects, and absolute outer
extents primary. At fixed seed `647668836648946`, it placed exactly one Primal
Kyogre and one Primal Groudon correctly but produced an overly generic valley.
The previous long prompt at that same seed enlarged and redesigned both forms.

The accepted hybrid retains the compact composition hierarchy and adds only
the minimum Hoenn coastal-basin scene direction, identity restrictions, one
continuous low ground plane, and output exclusions. It is 419 words; the exact
model prompt SHA-256 is
`3f19fef6842d031f1f0578ffd160f967facef9405418ea9086c41702a9847e17`.
It uses the existing `individual_spatial_joint` graph, two already positioned
identity references, one empty latent, one sampler, one decode, FLUX.2 Klein
4B BF16, four steps, and deterministic Lanczos conversion to the 300-dpi print
raster. No composite, restoration, repair pass, or generated text is added.

| Target | Prompt profile | Seed | Raw SHA-256 | 300-dpi text-free SHA-256 | Decision |
| --- | --- | ---: | --- | --- | --- |
| `ExGen2/sections/primal` | `landscape_first_v1` | `647668836648946` | `35ca6dcd97f77301980e003e6eaecc1cb7bb0fc46a397b12a41f8426213713df` | `74c828b35bbf41bd745c80b088179ac41aba9e560a2cfff824504f0c2c85b836` | Approved, promoted, and PDF-enabled |

Human review accepts the exact full artwork and both outer lower card crops.
The small grass-blade anomaly at the lower-right edge is explicitly accepted
for these pixels. This exception does not weaken the normal occlusion gate for
future candidates. A hash regression test protects the reviewed prompt, and
the profile fails closed unless the scope has exactly two ordered outer
subjects in `standard_3x3`. It is opt-in only; the other 40 promotions and
their prompt paths remain unchanged.

This closes the configured rollout at 41 of 41 reviewed and enabled targets.
The cover implementation remains available for missing/disabled assets and
explicit `--skip-poster` builds, but no current configured target needs that
fallback in the normal build.

### v10 missing-set completion and review attribution (2026-09-12)

The operator requires a panorama for every set. ME05 and SV08 cover-only
outputs were an incomplete intermediate state, not an accepted v10 fallback.
The active workspace's existing renderer configuration was reused. Every
immutable job returned its `run.json`, `comfyui.log`, and complete output set;
private connection/runtime values remain only in the ignored workspace marker.

All probes below use joint scene synthesis. Default individual-spatial inputs
proved unstable for Miraidon/Black Kyurem and sometimes transferred anatomy
between simpler subjects. The comparison changed one factor at a time before
returning to the existing 4B BF16 model. The shared spatial cast plus three
large identity references is the retained mask-free v7 graph, not a new model
or post-generation character composite. Four steps are the distilled model's
configured sampling contract.

| Scope / probe | Seed | Raw SHA-256 | Review result |
| --- | ---: | --- | --- |
| ME05, original cast / 4B individual | 260765584 | `58c870cd18ed276c6ea78dd823e7577b5401c4f6d018ef1d9d70c8319840cfdc` | Rejected: malformed Miraidon |
| ME05, original cast / 4B individual | 260912505 | `9a4ec1c7ed619d2da58817b964e91782db5d14eb42cf07b6a0207235c29f5dbe` | Rejected: malformed Miraidon |
| ME05, Morpeko cast / 4B individual | 260765584 | `58365daf3552f51a8a013ecb345fee577eacdca549a159d2197a9b49e8e48f83` | Rejected: Robball flipper transferred to Marshadow |
| ME05, Morpeko cast / 4B individual | 260912506 | `4ccce41a9bbae6b3761741f1ea605f308d9c79986b740a3d6281a5a6fedbfe2c` | Rejected: extra fourth creature |
| ME05, 4B individual / 2 MP | 260912506 | `59cf94ef34e2120e844138f021df28c61330e678a2dfbf4d52597d40634b1080` | Rejected: flipper transfer remains |
| ME05, 9B individual / 1 MP | 260912506 | `720245bc44dd40855c95efdcf75141ed321be7da091f9c8f888c7c1d95861aa9` | Rejected: Robball eye/flipper drift |
| ME05, 9B spatial / 1 MP | 260912506 | `83ca4d6bd2d22f866f6c7e5b697d89007449a76db3b8c26ba615ecee5161cd23` | Passed visual comparison; superseded by 4B before commit |
| ME05, 4B spatial / 1 MP | 260912506 | `57747266f564e24e8bce5627122e0fc69038ac969be8a79ed8d80ad198be3d76` | Rejected: extra fourth creature |
| ME05, 4B spatial / 1 MP | 260912507 | `ef5f102c94cb37375db4c5d0643d10fdd8ad89917f7fe7f8c2bbb14aa49f6298` | Accepted after full raw/master and nine-crop agent review |
| SV08, Kyurem cast / 4B individual | 260912008 | `560a50403fb7086b0e6dcf8e801a4e44ca3939cfc133c7b7c2179f3958e08475` | Rejected: Kyurem form/containment |
| SV08, Kyurem cast / 4B individual | 260912108 | `80e81b66a5d1deeb54144c386de838a42137745597ce52b180da656a7ba34d4f` | Rejected: Kyurem form/containment |
| SV08, 9B individual / 1 MP | 260912108 | `943515215bfbe2fb33c1c4a8ac0a7d795317f4e0725a264718b8f5568fe079e1` | Rejected: missing Kyurem and misplaced Ho-Oh |
| SV08, 9B spatial / 1 MP | 260912108 | `e90d05671d27a9f7f7e313fdf0640e04d02221130a22cc1c8a190789d02a90e6` | Rejected: Kyurem form/clipping and foreground conflict |
| SV08, Pikachu cast / 4B spatial | 260912108 | `60f250311d23e9faf27303af28a20778f73b20ffe4973f987f61e94544f81f83` | Rejected: grass crosses Ho-Oh tail and Pikachu belly |
| SV08, Pikachu cast / clear foreground / 4B spatial | 260912109 | `038d4f2e3df89aa08644e57d9bb1bbd1649b386eed25fb74636bda62241dc73c` | Accepted after full raw/master and nine-crop agent review |

ME05 retains Robball (728), Morpeko (877), and Marshadow (802). SV08 now uses
Ho-Oh (250), Krokel (909), and Pikachu (25); the poster-only third-slot choice
references actual set card `sv08-057`. Black Kyurem card `sv08-048` remains
unchanged in the data. The final SV08 constraint requests a clear low foreground
so all figures retain exposed silhouettes. No failed candidate enters a PDF.

The earlier v10 SV07 replacement at seed `260912007`, raw SHA-256
`649b8976c1a032d646b21bc22aaf2a38916789ba128073ca40fe7f15af314720`,
retains exactly two Hopplo ears after full-image and nine-crop agent review.
The exact final print masters are:

| Target | 2368 x 3268 text-free SHA-256 |
| --- | --- |
| ME05 | `3120f1f07526c80d74f5cd83aa6bbb09dbc256e423f4d1c3c7ee3ecbf8f95732` |
| SV07 | `876c1c23d1bd31ee832c419845e2f0469b069e0e596e7171b438246c56a4c8ef` |
| SV08 | `d931776dc062cc9f9db4b632fab658ce678ad6fe2afcc73d33e363f1e51fe7f8` |

All active assets remain FLUX.2 Klein 4B BF16, 1-MP raw generation and exact
300-dpi Lanczos print output. The 9B comparison is ignored experiment evidence,
not a production model dependency or a claim about third-party image rights.

Independent code review exposed a pre-existing provenance bug: the promotion
helper labeled every explicit review as human review. New approvals now require
an explicit `human` or `agent` reviewer kind, preserving all pixel/hash gates
and historical human records. The three v10 replacements truthfully record
agent review under the operator's autonomous implementation request, not a
human aesthetic approval. No source-cache image or private worker marker is
committed. A real `PosterPageCollection` regression checks all 31 release scopes
and their 42 sections so missing/disabled panoramas cannot silently satisfy the
normal release gate with an ordinary cover.

The full suite also exposed duplicated subject-selection logic in the read-only
work planner: it appended fallback candidates but ignored explicit slots, so it
incorrectly expected Kyurem after the importer had correctly selected Pikachu.
A failing regression reproduces the disagreement; the planner now delegates to
the same `select_pokemon` function as import and generation, including invalid
slot validation. No cache falsification or alternate selection path is added.
