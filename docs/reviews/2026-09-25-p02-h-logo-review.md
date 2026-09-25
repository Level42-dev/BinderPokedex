# P02 Dschungel — H artwork approval and localized logo review

On 25 September 2026 the operator accepted the Pokémon depiction in the
displayed P02 candidate H, text-free master SHA-256
`26d6a468e59b7dd1ea21931d85ae016ed220324d23eee1fd8aacb642001a07f6`.
The original German preview's plain `Dschungel` heading was explicitly **not**
accepted as a correct set logo. This approval applies only to the exact
text-free master, not to a localized overlay or PDF release.

The root cause was a missing German `title_logo` mapping for Base2; the
renderer correctly fell back to title text. TCGdex's German Base2 record has
no logo URL. A third-party German gallery labels a small image as a Dschungel
logo, but inspection showed the image says **JUNGLE**. A physical German
booster reference instead has `Dschungel` as pack text and the Pokémon
Sammelkartenspiel brand above it; it does not establish a separate transparent
German wordmark. The flower and `JUNGLE` are the recognizable vintage set
mark. Therefore this review candidate maps German to the same higher-resolution
500 × 410 set mark TCGdex supplies for French, while the information panel
continues to identify the set in German as `Dschungel`. This is an explicit
source decision, not a claim that `JUNGLE` is a German translation.

The cached normalized logo SHA-256 is
`2c3c710607f45c54a2e7ed05f492e82a2ccfe9d021b9511cccf07f9053a0bbfc`;
the temporary German preview SHA-256 is
`1bb691e4fb60eadb98d10dc579a82df3e1399770fcd92c25a40bac2928ae565a`.
The H master SHA-256 stayed unchanged. The preview is in the ignored review
workspace, and the configured logo is reproducibly fetched there; neither the
source logo nor preview is production-promoted or checked in as a source asset.
Compared with the earlier H preview, the entire lower panorama through row
`y=3209` is pixel-identical. Only the deterministic `Binder Pokedex`
signature at the extreme lower-right edge is newly typeset.
All nine physical card crops were produced; the top-center logo crop was
visually inspected at its full 750 × 1050 pixel size and stays within the
cutting area.

The operator has not yet approved this replacement logo composition. The P02
PDF route remains disabled. Before release, the project also needs a truthful
masked-fallback promotion contract, print/PDF validation, and review of the
currently displayed `16. Juni 1999`: this is the source set's global/English
date, while German booster references date the German edition to June 2000.

Source references:

- TCGdex set mark: <https://assets.tcgdex.net/fr/base/base2/logo.png>
- Historical German booster image: <https://zadoys.ch/en/products/pokemon-dschungel-sealed-1st-edition-booster-deutsch>
- Independent German set gallery: <https://pokezentrum.de/pokemon-kartengalerien/>
