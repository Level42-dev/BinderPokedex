# Binder Pokédex v10.0 Data and PDF Quality Design

## Decision

Binder Pokédex v10.0 is a reviewed data refresh and print-quality release, not a
small patch to the v9.0 PDFs. The release will refresh every configured data
scope once, record and review the resulting differences, add the published
Mega-Evolution set ME05, fix the known German naming, numbering, logo, layout,
and poster defects, and then build release assets only from the committed
snapshot.

The release date boundary is 2026-09-12. Data published after that boundary is
not silently pulled into v10.0.

## Baseline Evidence

- The German TCGdex SVP response contains 216 card records even though the
  greatest listed number is 224. The missing printed numbers between 001 and
  224 are 085, 102, 190, 191, 192, 213, 214, and 215.
- TCGdex does not currently expose the German `Terapagos & Freunde` card. The
  operator-provided photographs show both the German and English physical SVP
  cards without a printed promo number. The upstream English identifier
  `svp-500` is therefore an internal source identity, not a printable number.
- German MEP currently contains 88 records numbered 001 through 088. In
  particular, Serpiroyal is 064 and Glutexo is 079.
- The release workflow currently runs a live fetch before rendering. A tag can
  therefore produce different PDFs at different times even when the tagged
  repository contents are unchanged.
- The current repository already contains ME01 through ME04. TCGdex lists the
  released German main set ME05, `Dunkelnacht`, with 120 records and a release
  date of 2026-07-17. It is the missing main-set scope for v10.0.
- TCGdex also exposes the separate eight-card energy group `MEE`. Binder
  Pokédex has not treated the analogous `SVE` energy group as a standalone set,
  so neither energy-only group enters the v10.0 main-set scope.
- The announced `Pokémon-Sammelkartenspiel: 30 Jahre` expansion releases after
  the snapshot boundary and has no reviewed Binder Pokédex scope. It is outside
  v10.0.

## Release Scope

### Included

- Refresh every currently configured Pokédex, variant, and TCG scope.
- Add `ME05` as a full TCG scope with data, poster configuration, output, and
  release coverage.
- Add the German unnumbered `Terapagos & Freunde` card to SVP as a curated
  language-specific record. Keep `svp-500` as its stable source identity and
  render no number.
- Rebuild every output whose reviewed data or renderer input changes.
- Add v10.0 release notes, changelog material, and release-workflow coverage.

### Excluded

- `MEE` and `SVE` as standalone energy-only scopes.
- The not-yet-released 30-year anniversary expansion.
- Automatic acceptance of upstream removals, language substitutions, or
  identity changes.
- Publishing a GitHub release or pushing a tag. This work produces a reviewed
  local v10.0 release candidate; publication remains a separate explicit act.

## Data Snapshot and Refresh Audit

The normal maintenance path has two distinct phases:

1. An explicit maintainer refresh contacts the configured APIs and updates the
   checked-in source and transformed data.
2. Release builds consume only those checked-in files and fail if snapshot
   metadata or consistency checks do not match.

Every refreshed TCG output records:

- the UTC refresh timestamp and date boundary;
- the TCGdex set identifier and language endpoints queried;
- set-level language availability;
- per-card language availability;
- upstream record counts by language;
- the applied curated-override revision.

A deterministic audit compares the refreshed tree with the pre-refresh Git
state. For every scope it reports added and removed card identities, changed
printed numbers, changed localized names, changed Pokédex identities, language
availability changes, set metadata changes, and logo-source changes. The audit
exits non-zero for unexplained removals, duplicate printed numbers, a numbered
card without a stable identity, or a foreign-language fallback presented as a
native translation.

The v10.0 audit report is retained under `tmp/` for operator review but is not
committed as product data. A concise reviewed summary belongs in the v10.0
release notes.

## Card Identity, Language, and Numbering

Each TCG card keeps separate concepts:

- `id`: stable internal identity, normally the TCGdex ID;
- `localId`: upstream identifier used for matching API responses;
- `printed_number`: the label printed on the physical card, which may be null;
- `available_languages`: languages in which that exact card record was
  observed or explicitly curated.

PDF ordering uses numeric `printed_number` values first and unnumbered cards
after them in stable ID order. Rendering uses `printed_number`; it never uses a
section position as a substitute. `Terapagos & Freunde` therefore remains
internally traceable as `svp-500` while its insert has an empty number field.

For v10.0 German SVP consists of the 216 German TCGdex records plus the curated
unnumbered `Terapagos & Freunde` record. Missing upstream numbers remain gaps;
they are not invented or compacted. German MEP consists of the 88 current
TCGdex records and preserves 001 through 088 exactly.

## Localized Names

Naming authority depends on the output type:

- Pokédex PDFs use canonical species/form names. They never gain a Trainer
  owner prefix or card-mechanic suffix merely because a TCG card has one.
- TCG-set PDFs use the exact localized card name for that card and language,
  including legitimate owner prefixes such as `Ns`, `Enigmaras`, `Lillys`,
  `Hops`, `Team Rockets`, `Cynthias`, `Marys`, and `Troys`, plus suffixes such
  as `-ex`.
- Pokédex enrichment may add identity, types, artwork, and missing canonical
  metadata to a TCG card, but it must not overwrite an already observed
  localized card name.
- A missing language record is not filled with English and labeled as German.
  The card is absent from that language's PDF unless a reviewed curated record
  supplies the localized value.

Curated corrections live in a dedicated, reviewed enrichment file and are
applied after multilingual TCGdex collection but before Pokédex identity
enrichment. The v10.0 German corrections include:

- SV01 257: `Basis-Elektro-Energie`
- SV01 258: `Basis-Kampf-Energie`
- SV02 278: `Basis-Pflanzen-Energie`
- SV02 279: `Basis-Wasser-Energie`
- SV03 230: `Basis-Feuer-Energie`
- SV06.5 098: `Basis-Finsternis-Energie`
- SV06.5 099: `Basis-Metall-Energie`
- SVP unnumbered: `Terapagos & Freunde`

## Localized Set Logos

Logo selection is exact-language only. A missing German logo may be supplied
by a curated source mapping, but it must never silently fall back to English.
If no exact-language logo exists, the renderer uses localized text.

The v10.0 curated mappings use the official German Pokémon assets:

- Schwarze Blitze:
  `https://www.pokemon.com/static-assets/content-assets/cms2-de-de/img/trading-card-game/series/sv_series/sv10pt5/blk/sv10pt5_logo_169_de.png`
- Weiße Flammen:
  `https://www.pokemon.com/static-assets/content-assets/cms2-de-de/img/trading-card-game/series/sv_series/sv10pt5/wht/sv10pt5_logo_169_de.png`

The downloaded source files remain reproducible ignored cache inputs. Their
hashes are recorded by poster provenance; the artwork master itself remains
text-free. Only the localized overlay and derived PDF pages change.

## Card-Label Layout

All insert labels render inside a horizontal safe area inset from both card
edges. The label renderer follows one deterministic policy:

1. Use the normal bold name size when the text fits.
2. Reduce the size to the configured readable minimum when that preserves one
   line.
3. Otherwise split at word or hyphen boundaries into at most two balanced,
   centered lines and fit each line to the same safe width.
4. Fail PDF generation when the text cannot fit at the minimum size rather
   than drawing across an insert or cut line.

The policy applies to Pokémon, Trainer, and Energy labels. Regression fixtures
cover SV04 159, 176, 177, and 179 plus SV05 140. A whole-dataset geometry check
ensures every rendered label remains within the safe area.

## Poster Artwork

### SV10.5B and SV10.5W

The existing text-free panorama masters remain unchanged. Their German title
overlays are rebuilt from the official German logo sources, and the provenance
and PDFs are regenerated.

### SV07 Stellarkrone

The current Hopplo rendering is rejected because it contains an extra long
ear. The configured renderer target in the private workspace marker is reused
without exposing its values. The first candidate uses the canonical graph with
a new seed. If the extra-ear defect remains, the next candidate changes only
the subject-control mode to the repository-supported identity-lock path.

No candidate is promoted merely because rendering succeeds. Promotion requires
visual approval of the complete text-free panorama and all nine physical card
crops, including a direct comparison of Hopplo with its correct two-ear source
artwork. The render job must return `run.json`, `comfyui.log`, and every output
image.

### ME05 Dunkelnacht

ME05 receives the same manifest, reproducible source cache, reviewed text-free
master, provenance, localized overlays, and physical-crop review as existing
main sets. Featured subjects come from the refreshed ME05 data and must resolve
to exact allowlisted artwork identities before a GPU job starts.

## Release Pipeline

`build-release.yml` no longer calls the data fetcher. It validates committed
snapshot metadata, downloads reproducible poster source assets, validates every
promoted poster, builds all PDFs, creates language archives, builds the release
manifest, and verifies the candidate.

The explicit data-refresh command remains documented for maintainers. Its
output must be reviewed and committed before a release candidate can consume
it. This makes a v10.0 tag byte-stable with respect to upstream API drift.

## Verification and Acceptance

The release candidate is acceptable only when all of these checks pass:

- Unit tests demonstrate the red/green regression cycle for name authority,
  per-card language availability, nullable printed numbers, logo-source
  selection, and label fitting.
- The complete Python test suite passes.
- The refresh audit contains no unexplained removal or identity conflict.
- German PDF text extraction contains all seven corrected Energy names,
  legitimate SV09 Trainer-owned names, MEP 064/079, and an unnumbered
  `Terapagos & Freunde` entry.
- Rendered SV04 pages 19 and 21 and SV05 page 17 contain no text crossing an
  insert boundary or cut line.
- German SV10.5B and SV10.5W poster pages contain the German official logos and
  no English `BLACK BOLT` or `WHITE FLARE` logo.
- The complete SV07 and ME05 panoramas and every corresponding physical crop
  pass visual inspection.
- Every changed or new German PDF is rendered to PNG and inspected at the
  affected pages; automated page-count, text, and geometry checks cover the
  whole refreshed German set.
- The full release-candidate build and verification scripts exit successfully.

## Deliverables

- Committed v10.0 data snapshot and structured correction sources.
- ME05 data, scope, poster configuration, reviewed artwork, and provenance.
- Corrected renderer and fetch/enrichment behavior with regression tests.
- Corrected and visually reviewed German PDFs for every changed scope.
- v10.0 release notes, changelog, documentation, and a locally verified release
  candidate.
