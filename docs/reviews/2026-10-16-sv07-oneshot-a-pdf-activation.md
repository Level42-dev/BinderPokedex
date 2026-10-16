# SV07 one-shot A: operator approval and German PDF activation

The operator accepted the shown SV07 German panorama on 2026-10-16. The
attached JPEG has SHA-256
`ee09319fe849837c7747ec69b9c0a317aac85af0b4388b27c94556f9e8d11660`.
After resizing the retained German previews to its 927 × 1280 dimensions,
candidate A's per-channel mean absolute difference was approximately 2.6–3.0
JPEG values; candidate B's was 17.5–27.5. This identifies A, not B, as the
approved visual. The previous agent concern about the left-pointing ground
shadow remains recorded in the trial report; the user's later image-specific
acceptance is the release decision for A, not a general tolerance rule.

| Evidence | SHA-256 |
| --- | --- |
| Approved 2368 × 3268 text-free, 300-dpi master | `3023482cd91a579d7562ca65d93a4cf5e88b55b4ed4ddc8d07a045aee80838c6` |
| Raw one-shot output | `135c8fe2f9cf9d7c28d9042af10b2865aad1845bdec3942b478304e2ce36e541` |
| Returned ComfyUI workflow | `c4105827101db81cd13db9cc8b6d42f0d9fc3db2acfad8bf65f3c24b1b77fb84` |
| Returned run metadata | `e32723830c17085a69ec8f082411a668d7c4c66f281a7e209036f0f33b1cb475` |
| Returned log | `91cf7862becbe0a74a721feda3ff113d0289bb4c6187673061ab3ec6cfc7536b` |
| Original German preview | `b4291dd08ef62e4d60b175ccf905e15bd0e345ea05dce193a2a2ce9512e6ff12` |

The source-detail renderer now appends the candidate's exact final shadow
instruction and uses its safe output filename prefix from the SV07 manifest.
The newly built canonical graph equals the returned graph node for node; all
four regenerated source-reference PNG hashes equal those in the immutable
job. The source figures remain Bisasam, Schiggy and Hopplo, with exact
reviewed source hashes bound in the manifest and promotion provenance.
The nine reviewed card-crop hashes, master, raw image, preview, run and log
were checked against the local trial evidence before promotion. Only the
reviewed text-free master and its truthful provenance were promoted; source
cutouts, logos, render jobs and previews remain ignored local cache files.
This is a genuine one-sampler, one-decode one-shot, not a masked composite.

The SV07 poster route is enabled. The German PDF was rebuilt at
`output/de/SV07_DE.pdf` (SHA-256
`2f2d7d0925c77359b80a79a0303a4ed058b39f85b0e4434ccd35d3e8fbadae2d`).
Poppler reports 22 A4 pages. Page 1 was rasterized and visually checked for
the correct German Stellarkrone logo, continuous 3 × 3 panorama, intact
three-Pokémon cast, card containment, title and information panel; page 2
was checked for ordinary card labels and margins. The previous PDF was
preserved only in the ignored local trial review directory. The PDF is a
local build artifact, not a committed release archive, deployment or
independent commercial-print approval. Candidate B remains rejected.
