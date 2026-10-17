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

The operator subsequently accepted this exact `JUNGLE` logo composition for
the German P02 cover, acknowledging that no wholly German standalone logo is
available and the historical mark has already been used for this set. This
decision is bound to the logo and German preview hashes above. It does not
approve the unrelated release-date value in the info panel or the PDF. The P02
PDF route remains disabled. Before release, the project also needs a truthful
masked-fallback promotion contract, print/PDF validation, and review of the
currently displayed `16. Juni 1999`: this is the source set's global/English
date, while German booster references date the German edition to June 2000.

Source references:

- TCGdex set mark: <https://assets.tcgdex.net/fr/base/base2/logo.png>
- Historical German booster image: <https://zadoys.ch/en/products/pokemon-dschungel-sealed-1st-edition-booster-deutsch>
- Independent German set gallery: <https://pokezentrum.de/pokemon-kartengalerien/>

## Technical master adoption and corrected information panel

The exact accepted H master was adopted on 25 September with a schema-3
`masked_fallback` provenance record. Its SHA-256 remains
`26d6a468e59b7dd1ea21931d85ae016ed220324d23eee1fd8aacb642001a07f6`.
The stored record identifies the original one-shot A separately from the two
bounded Pikachu/Evoli foreground repairs; its print-pixel audit found 10,548
changed pixels within 11,121 editable pixels and zero changes outside the
masks. This is a technical master adoption, not a claim that H is an untouched
one-shot output. The other seven physical card areas remain unchanged from A.

The new German overlay displays the accepted historical `JUNGLE` mark and
`Juni 2000` in the information panel, without inventing a day. The new preview
SHA-256 is `9ddd07346a37db94b236418b55e73f1ea0712caa341b3fc8b515a4406f3a9012`;
its overlay fingerprint is
`60cfdded286b73d0cdf758f0974533da4c8a501ee37e7eadd8efe50973482e12`.
The full preview and all nine 750 × 1050 physical card crops were inspected;
the three Pokémon cards were compared side by side with their official source
art. At this technical-adoption checkpoint, the new localized overlay had
not yet been accepted and PDF routing remained false; the later approval and
print checks are recorded below.

## Exact overlay acceptance and local PDF checks

The operator accepted the displayed corrected Dschungel panorama on
25 September 2026. The approval is bound to German preview SHA-256
`9ddd07346a37db94b236418b55e73f1ea0712caa341b3fc8b515a4406f3a9012`
and overlay-fingerprint SHA-256
`60cfdded286b73d0cdf758f0974533da4c8a501ee37e7eadd8efe50973482e12`.
The earlier accepted logo-only preview remains historical evidence, not this
release gate. Schema-3 validation now accepts the localized overlay and the
P02 PDF route is enabled.

Only de, en, fr and it are available for Base2 in the current source data.
All four have 64 cards; the PDF generator deliberately skips the five other
generic renderer languages for this set. Their four title and information
cards were inspected in physical card crops. German keeps the approved
`JUNGLE` mark and `Juni 2000`; English and French use their configured logos,
while Italian uses the explicit text-title path. The English TCGdex logo is
160 × 111 pixels and consequently softer than the 500 × 410 French/German
mark, but legible and wholly inside the title card.

The canonical local PDFs were rebuilt after preserving byte-identical copies
of the preceding outputs in the ignored Base2 workspace. Each new PDF has
10 A4 pages and text extraction finds each of the 64 card numbers. The German
poster page was rendered at 300 dpi and its r2c2 information card inspected
at print size; the other three poster pages were also rendered and inspected.
The German second and final pages were sampled for the card-page transition
and notices. The new local PDF SHA-256 values are:

- de: `a42dd5f9d885d2b269e97d53f0e6ec7a9b9aa4e281f93ad6aeaf02d1290960d3`
- en: `cd5dc472c3ca3133a4ee9313b330b34f005c6c262cd85b64ead5b8951fb5f42e`
- fr: `f40766e0e767077c22f6d41424f5584159c5d7dd0cf26f3dbc2e12e802d5d109`
- it: `0c00c2bd9b228db35f95a2fb9cd0bc770e093e7ebbb89fda3b142e0be249e794`

These are locally generated candidate PDFs, not a published v10 release.
The notices page explicitly excludes third-party Pokémon material from the
project-design CC BY-NC license; no new commercial-use right is asserted here.
