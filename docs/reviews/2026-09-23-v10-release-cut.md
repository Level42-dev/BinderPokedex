# v10.0 release cut — 2026-09-23

> Historical checkpoint. The operator subsequently requested adoption of all
> 29 accepted artworks. The current candidate is documented in
> [the 2026-09-24 adoption record](2026-09-24-v10-approved-panorama-adoption.md).

## Decision boundary

Ship the corrected data and PDF renderer without waiting for further poster
generation. Do not treat an accepted artwork candidate as an installed poster:
only a bundle that passes the current production validator may be enabled in a
release PDF. An unavailable or unfinished artwork uses the existing set or
section cover; its nine physical poster cards are omitted, not replaced by an
unreviewed image. The card lists, promo numbering, and normal insert pages
remain in scope.

This supersedes the earlier v10 expectation that all 42 targets open with a
panorama. It does not revoke the exact-image decisions or delete poster assets.

## Verified starting point

- The committed 63-file data snapshot at the 2026-09-12 boundary passes
  `verify_data_snapshot.py`.
- Before the release cut, 42 poster targets are configured as PDF-enabled.
  Exactly five pass `validate_promoted_poster.py` individually:
  `ExGen2/sections/mega`, `ExGen3/sections/normal`, `ME05`,
  `Pokedex/sections/gen1`, and `Pokedex/sections/gen7`.
- The other 37 fail current production validation, predominantly because the
  visual identity approval is incomplete or stale. The installed P05 and
  Stellarkrone bundles additionally have generation metadata drift.
- The pre-cut test suite has 905 passed, three failed, and one skipped. The
  three failures are poster-currentness/validation tests that encounter the
  stale enabled bundles; they are not evidence that those posters may ship.
- 29 exact candidate masters in the collected review are accepted as artwork
  only and preserved in `assets/reviewed-candidates/v10-batch-20260923`.
  They are not production bundles or approved release PDFs.

## Future artwork work

1. Technically adopt each of the 29 accepted exact masters through the normal
   provenance/promotion path, bind the exact source and review hashes, validate
   the resulting bundle, inspect the full localized panorama and all nine
   physical cards, and then re-enable its PDF route. Do not broaden the
   image-specific human acceptance to a later render.
2. Revisit the accepted but unpromoted Base1-B and ExGen3 Mega-C candidates;
   resolve their documented localization/integration gaps before enabling.
3. Correct P01/SV07 Hopplo's reserved ground shadow; finish P02/Base2's
   remaining character and scene review; finish P06/Pokédex gen3's source
   identity review. These are not covered by the 29-candidate approval.
4. Regenerate or otherwise solve P16/ExGen2 primal and P37/ME03, which were
   explicitly non-approvable in the collected comparison. Keep the one-shot
   workflow primary and the stronger-model or multi-stage path a bounded
   fallback only when needed.
5. After every adoption wave, re-run the production validator, all PDF tests,
   the full release-candidate build, and visual checks of localized logos,
   card crops and print geometry. Publish artwork updates only from a new
   reviewed release, never by silently replacing a released ZIP.
6. Resolve the planner-only `scene_catalog_drift` warning on the accepted
   ExGen3 Normal/P40 bundle. Its production validator passes, so this warning
   does not block the current release, but planner state should be reconciled
   before treating it as a clean regeneration baseline.

## Publication gate

Before tagging v10.0: make the enabled-poster set match only currently valid
bundles; update release news so it does not claim full panorama coverage;
run the full test suite and the shared nine-language release-candidate build;
inspect representative German pages and release archives; then merge the
reviewed commit, tag it, and verify the published GitHub Release plus README
announcement. Keep local untracked ZIPs and notes untouched.
