# v10.0 approved-panorama adoption — 2026-09-24

## Scope and authority

The operator asked for the 29 already accepted poster artworks to be included
in the v10 release candidate. This is a technical adoption of the **exact**
images in [the acceptance record](2026-09-23-panorama-batch-user-acceptance.json),
not a new visual approval or an authorization to use replacement renders.
No GPU generation was performed.

## Evidence and installation

- All 29 archived text-free masters match their acceptance SHA-256 values.
  Their original German previews, raw renders, run metadata, worker logs and
  all 261 physical card crops match the frozen
  [evidence index](2026-09-22-panorama-batch-evidence.json).
- Each master was promoted through the normal provenance path with its exact
  run sidecar, generation fingerprint, source records and recorded human
  visual approval. Production artwork pixels match the corresponding accepted
  master; PNG compression is not treated as a new image.
- All 34 enabled bundles (the previous five and these 29) pass the production
  poster validator at 2368 × 3268 pixels, nine cards and effective 300 dpi.
- Comparing every newly finalized German card with its reviewed counterpart:
  all nine cards of 28 candidates are pixel-identical. For P05/Johto, only
  the title card, information card and bottom-right branding card differ in
  dynamically set overlay pixels; the six other cards are pixel-identical.
  The underlying accepted artwork is pixel-identical in all nine cells.
- The local test suite reports 910 passed and one skipped; the committed
  63-file data snapshot verifies at its 2026-09-12 boundary. Two temporary
  German QA PDFs (SV03.5 and Pokédex, rendered without ordinary card scans)
  built successfully at A4. SV03.5 page 1 and Pokédex page 19 were rendered
  and visually checked for the nine-card layout, localized copy and cut lines.

## Release routing

The 29 accepted routes are enabled in addition to the five already valid
routes: **34 of 42** targets now route to a panorama. The eight remaining
disabled targets use their set or section cover: Base1, Base2, ExGen2 Primal,
ExGen3 Mega, ME03, Pokédex Generation 3, SV07 Stellarkrone and SV08
Stürmische Funken. Their earlier reviews and future work remain open; none is
implicitly approved by this batch.

## Remaining publication gates

The nine-language release build with ordinary card scans, final release-PDF
spot checks, independent PR review, merge, tag and GitHub Release must be
verified before v10.0 is described as published. The pre-existing untracked
local release ZIPs and notes are not part of this candidate and must not be
staged.
