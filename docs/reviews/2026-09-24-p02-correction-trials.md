# P02 Dschungel — source-bound correction trials (H awaiting human review)

The operator requested correction of Relaxo and Evoli instead of accepting
their errors in the older candidate E. Candidate E's Pikachu-only acceptance
does not transfer to a different whole-scene master.

Two immutable 2-MP FLUX.2 one-shot trials used the three exact cached official
artworks, a source-detail manifest and the configured private worker. Both
returned `run.json`, `comfyui.log` and all output images. Their frozen packages,
source hashes, prompt/graph fingerprints and nine physical card crops verified.

| Trial | Text-free master SHA-256 | Visual result |
| --- | --- | --- |
| A, seed 260924002 | `67f4e6dcfa88260aa35cb75c843b47c9975ddd3985154d3f318addb69a892e4d` | One Pikachu, one Relaxo, one Evoli. Relaxo's continuous mouth and two teeth and Evoli's standing body are much closer to the sources. Pikachu's lower grass blade is in front; the blade at the extended arm remains behind. Not approved. |
| B, seed 260924003 | `747ddbdf3fe3baee20f9c15769f32bec9a6ba8f36609f106fc82f6f0be488418` | Stronger foreground wording produced a duplicate Relaxo. Rejected immediately; no promotion. |

After those one-shot failures, a **bounded fallback** used A as the base. One
agent-traced arm-blade contour was supplied as a guide, followed by a masked
FLUX.2 harmonization pass. The resulting candidate F text-free master is
`80cd236abb32ce62af7a6ea2cb9b6c24af544b9932d8297f05ff8f1a1cccd9a1`.
The pixel audit found 3,406 changed pixels in a 3,418-pixel editable region
and **zero** changed pixels outside it. All eight other physical card crops,
including Relaxo and Evoli, are pixel-identical to one-shot A. The existing
lower belly grass crossing was untouched. Full scene and all nine physical
cards were inspected by the agent.

The F arm blade now crosses Pikachu in front, but its pointed tip near the
left cheek/neck is somewhat hard-edged. This concern was shown explicitly to
the operator together with the complete panorama and all three exact
source-versus-physical-card pairs. The operator briefly accepted F, then
**withdrew that acceptance** after noticing the tip and a second depth error:
the long dark-green leaf rising from the lower-right foreground remains
behind Evoli's tail. F is rejected as a whole and must not be promoted.

A revised, shorter Pikachu contour and a separate narrow Evoli-tail-leaf
contour were tested as bounded masked fallbacks against the same frozen
one-shot A. The first Evoli leaf trial failed visually: the model restored
the tail over the leaf. A second, wider contour succeeded in keeping the leaf
in front of the right half of the tail. The Evoli guide uses the **text-free
master crop** so the deterministic lower-right card title is not baked into
the artwork; that title remains intact in the German preview.

The two successful local edits were combined into review-only candidate G,
text-free master SHA-256
`373acf45e9ee0df523494213637134eb6cb4917330feb1a21f12c83c83c64b81`.
Exactly 9,042 pixels changed inside the union of the two small repair masks;
**zero changed outside**. The other seven physical cards are pixel-identical
to one-shot A, and the Pikachu/Evoli cards exactly match their separate local
repair previews. The full scene and all nine card positions were inspected;
new source-versus-card sheets were generated for Pikachu, Relaxo and Evoli.
The operator subsequently rejected G because both foreground blades still
looked wrong. It has not been promoted.
The exact text-free G master is preserved in the
[review-pending archive](../../assets/review-pending/p02-g/artwork-300dpi.png)
with explicit non-release provenance for traceability.

On 25 September a further limited fallback constructed two **continuous
foreground layers** from the existing vegetation: a blade crossing both
edges of Pikachu's extended arm and a broad leaf crossing Evoli's tail. The
layers were supplied as guides to two separate masked FLUX.2 harmonization
jobs, not pasted straight into the final master. Both jobs returned `run.json`,
`comfyui.log` and all output images. The model changed no pixel outside its
small respective mask. The Evoli guide came from A's text-free master, so the
German card title was not incorporated into the artwork.

The two bounded results form review-only candidate **H**, text-free master
SHA-256 `26d6a468e59b7dd1ea21931d85ae016ed220324d23eee1fd8aacb642001a07f6`.
The union-mask pixel audit found 10,548 changed pixels within 11,121 editable
pixels and **zero outside**. Seven other physical card crops are pixel-identical
to A. The full German panorama, all nine physical card positions and three
source-versus-card pairs (Pikachu, Relaxo, Evoli) were inspected. The result
places the blade before Pikachu's arm and the leaf before Evoli's tail; the
tip near Pikachu's cheek remains a point for the operator to inspect. H is
**awaiting human acceptance**, is not promoted, and is preserved as an exact
[review-pending master](../../assets/review-pending/p02-h/artwork-300dpi.png).

No masked-fallback candidate is yet technically promotion-eligible: the
current standard promoter has a one-shot provenance contract, not a
composited, masked-fallback contract. Do not label such pixels as a one-shot
run or silently replace candidate E/production.

Independent of the artwork decision, the current German Dschungel preview
uses a deterministic text title. It is not evidence that an original German
set logo has been sourced; that localization issue requires separate review.
