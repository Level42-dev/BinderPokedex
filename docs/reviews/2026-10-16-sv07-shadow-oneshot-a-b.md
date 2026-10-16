# SV07 shadow-direction one-shot trials A and B

Status: **both rejected by agent review for artwork release; no user approval claimed**.
The accepted 2026-09-15 SV07-B
master (`3d44b64f29b99898f150a4a5bee5cf62d6e928f1658dd9396a4464e76dda2799`)
and the disabled production PDF route remain unchanged.

The operator reaffirmed that multi-stage composition is only a worst-case
fallback. Two isolated true `joint_scene/spatial_source_detail_joint`
one-shots therefore tested whether a precise lighting/contact-shadow prompt
could resolve Hopplo's reserved shadow issue. A kept the accepted B seed
`260915007`; B changed only the seed to `260915008`. Both retained the same
three source Pokémon, four image references, pinned Klein model, encoder,
VAE, 2-MP generation, four steps, one sampler and one decode. The added prompt
asked for a compact, soft shadow toward the lower-right from upper-left light,
contact only at Hopplo's supporting foot, and no left-pointing bar or detached
patch. Both jobs ran on the configured private Apple-MPS worker and returned
their complete `run.json`, `comfyui.log`, input and output images. Model and
input hashes, `Device: mps`, 300-dpi master geometry and all nine physical
card hashes were checked.

| Trial | Text-free master SHA-256 | Visual outcome |
| --- | --- | --- |
| A, same seed | `3023482cd91a579d7562ca65d93a4cf5e88b55b4ed4ddc8d07a045aee80838c6` | Pokémon anatomy and layout remained close, but a distinct dark horizontal shadow still extends left from Hopplo's standing foot. |
| B, new seed | `9336ee60551bf395afc406811541d52b19ce437c3a69c5aae2f159e561b90ab6` | The left-pointing foot-shadow strokes remain; a new thin tail-like contour appears behind the raised foot, unlike the source artwork. |

Both full German previews, all nine card crops, and side-by-side comparisons
for Bisasam, Schiggy and Hopplo are preserved under ignored
`tmp/oneshot-trials/sv07-shadow-oneshot-20261016-{a,b}/review/`. Their
`evidence.json` records the exact job, preview, card and comparison hashes.
The trial prompts and workflows are in the corresponding ignored job folders.
No trial is approved or eligible for promotion; no active artwork, manifest,
PDF or release archive was changed.

Next design decision: do not repeat minor seed variations or use the already
rejected rectangular texture repair. If SV07 is pursued further, test a
materially different **one-shot** control (for example the repository's
stronger FLUX.2 Dev profile, whose model file is present in the configured
worker cache but still needs a pinned-hash/job preparation), with the same
source and print review gates. Multi-stage composition remains the last resort.
