# P16 terrain-plate fallback: accepted master and German PDF

Date: 2026-10-16. Asset key: `ExGen2/sections/primal`.

The operator accepted the exact P16 terrain-B candidate after seeing the full
poster, all nine physical card crops, and Kyogre/Groudon source comparisons.
This is a scoped fallback after failed one-shot and bounded repair attempts.
It consists of a generated, upscaled landscape plate and exact-source Pokémon
composition; it is **not** represented as a one-shot in provenance.

| Evidence | SHA-256 |
| --- | --- |
| Accepted 300-dpi text-free master | `fb123a194a70c54f79e2ce1e247acda36bb97909e8d6a86f0107bee6d5bfa08d` |
| Promoted schema-4 provenance | `9c7a96d648747a9ac770897670539d2f0027b4f98dcbc5ceaca0ce761565c1e7` |
| German ExGen2 PDF, final local rebuild | `15f5688e3bef7fa0a55f2be6928b5c4e944b762126f988bc2a193b39b36ae5a0` |
| Prior German ExGen2 PDF, retained in ignored review backup | `c714da38608b7c414fd4f5301181cddc8f8f5cd627b72c0ec6d629dcb9522ebf` |

The immutable terrain and upscale jobs, including every image, `run.json` and
`comfyui.log`, remain in the ignored
`tmp/isolated-repair-trials/p16-terrain-20261016-b/` workspace. The promotion
record stores their stage and model hashes, source-cutout hashes, the exact
pixel-audit counts (24,992 opaque raw source pixels and 188,227 scaled print
source pixels, both with zero changed), the nine reviewed card hashes, and
the operator's image approval. It does not include private machine paths or
copy source-cache images into Git.

The promotion was re-run after independently pinning the reviewed source
cutout hashes, reconstructing and recomputing both exact-source pixel audits,
checking every render input byte and adding rollback for a failed paired
asset/provenance install. The print master and provenance hashes remained
unchanged. The final PDF was rebuilt through the hardened PDF validation gate;
its content and size were unchanged, while the file hash reflects the new
build metadata.

The first German PDF preview exposed a separate localization defect:
`Primal Kyogre`, `Primal Groudon`, and `Primal Pokémon` were still shown in
German. The source transform, checked-in data, and card-title renderer now
produce `Proto-Kyogre`, `Proto-Groudon`, and `Proto-Pokémon` in German while
preserving the English forms. [Pokémon's official German XY checklist](https://assets.pokemon.com/assets/cms2-de-de/pdf/trading-card-game/checklist/xy5_web_cardlist_de.pdf)
prints `Proto-Kyogre-EX` and `Proto-Groudon-EX`.

The rebuilt PDF has 20 A4 pages and 127 numbered Pokémon. Page 18 is the
nine-cell P16 panorama: title, information panel, Kyogre in `r3c1`, Groudon
in `r3c3`, and every cut line were inspected in a Poppler raster. Page 19's
two German card labels and card boundaries were inspected separately. A
72-dpi page-by-page raster comparison with the prior PDF found only pages
1, 13, 18, 19 and 20 changed. Pages 1 and 13 now reflect the already active
normal/mega poster masters that the older local PDF had not yet picked up;
page 18 is the new P16 panorama; page 19 is the Proto label correction;
page 20 differs in the regenerated local build/notices text. All other pages
were pixel-identical in that comparison. This PDF check is local technical
acceptance, not a new commercial or deployment approval.

SV07 remains disabled and unchanged. Its accepted scene still needs a clean
Hopplo-contact solution and a provenance-valid final master before PDF routing.
