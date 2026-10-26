# MEP data refresh - 2026-10-26

This is a bounded update of MEP. Other collections and previously built release
archives are outside this refresh.

## Source review

- [English TCGdex MEP](https://api.tcgdex.net/v2/en/sets/mep) supplies 112 cards,
  adding 089-110 and 120 to the previous 89-card snapshot. Every listed card's
  complete detail endpoint was fetched successfully.
- [Bulbapedia's MEP list](https://bulbapedia.bulbagarden.net/w/index.php?title=MEP_Black_Star_Promos_(TCG)&oldid=4636730)
  supplies eight further confirmed identities: 111-117 and 131. The direct
  scraper returned HTTP 403; these entries were transcribed from the accessible
  page and checked against their individual card pages below. Existing
  supplement entries remain intact and TCGdex takes precedence for overlaps.
- Blank slots 118-119 and 121-130 remain absent. Neither the supplement nor the
  PDF assigns replacement numbers to those gaps.
- The resulting English collection contains 120 records: numbered 001-117,
  120, and 131, plus the existing Museum card. Some confirmed promos precede
  their product's release; inclusion records an announced identity and does
  not claim current retail availability.

| Promo | Exact English name | TCG type | National Dex | Verification |
| --- | --- | --- | --- | --- |
| 111 | Masquerain | Grass | 284 | [Card](https://bulbapedia.bulbagarden.net/wiki/Masquerain_(MEP_Promo_111)) |
| 112 | Magmortar | Fire | 467 | [Card](https://bulbapedia.bulbagarden.net/wiki/Magmortar_(MEP_Promo_112)) |
| 113 | Enamorus | Psychic | 905 | [Card](https://bulbapedia.bulbagarden.net/wiki/Enamorus_(MEP_Promo_113)) |
| 114 | Kommo-o | Dragon | 784 | [Card](https://bulbapedia.bulbagarden.net/wiki/Kommo-o_(MEP_Promo_114)) |
| 115 | Spritzee | Psychic | 682 | [Card](https://bulbapedia.bulbagarden.net/wiki/Spritzee_(MEP_Promo_115)) |
| 116 | Seel | Water | 86 | [Card](https://bulbapedia.bulbagarden.net/wiki/Seel_(MEP_Promo_116)) |
| 117 | Kyogre | Water | 382 | [Card](https://bulbapedia.bulbagarden.net/wiki/Kyogre_(MEP_Promo_117)) |
| 131 | Pokémon RUN Pikachu | Lightning | 25 | [Card](https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_RUN_Pikachu_(MEP_Promo_131)) |

## Previously observed localizations

The current German, French, Spanish, and Italian endpoints each list only 80
cards. They omit 005, 006, 018, 019, 028, 068, 078, and 086, and sampled omitted
detail endpoints also return 404. This absence is insufficient evidence to
remove the earlier reviewed localized records.

The exact localized names for those eight identities are retained in
`enrichments/tcg_card_overrides.json`, copied from the reviewed
`data/output/MEP.json` at commit `7ee65ebb`. No new translations or language
availability are inferred. The earlier observation and 88-card German boundary
are also recorded in the v10 data-quality design's baseline evidence.

Each of these four localized PDFs therefore keeps its existing 88 cards and
original numbers. All 31 newly added records are English-only. The existing
Museum card remains English-only as before.

## Rendering boundary

The featured cast remains Zacian, Bulbasaur, and Charmander. The reviewed
text-free poster artwork is reused. Any changed English card-count overlay is
rebuilt deterministically; this refresh does not generate new artwork.

## Validation

- The refresh audit checked all 67 source/output files. Only the MEP source,
  supplement, and output changed; there were no blockers, removed identities,
  or edits to any of the 89 existing output records.
- All 103 existing snapshot, override, TCG enrichment, and transformation tests
  passed after the refresh.
- The snapshot manifest verifies all 67 hashes at the October 26 assembly
  boundary. Other collections keep their earlier source refresh dates.
- Poster validation passed for all nine physical cards at 299.99 dpi. The
  text-free master is byte-identical to its prior promotion; only the English
  information text changes in the overlay fingerprint. The planner reports no
  outstanding action.
- Both PDFs built successfully. Text checks confirmed exactly 120 unique
  printed identities in the 16-page English PDF and 88 in the 12-page German
  PDF. The poster counts were checked visually because the poster is embedded
  as an image rather than extractable PDF text.
- Visual review covered both localized nine-card poster openings, all English
  pages containing the additions, the long Pokémon RUN Pikachu label, and the
  German first/last card pages. The original numbering and language separation
  are intact.

Reproduction commands:

```bash
python scripts/fetcher/fetch.py --scope MEP
python scripts/data/audit_data_refresh.py --baseline-ref HEAD --output tmp/mep-refresh-audit.json
python scripts/release/verify_data_snapshot.py
python -m pytest scripts/tests/test_data_snapshot.py scripts/tests/test_tcg_card_overrides.py scripts/tests/test_tcg_enrichment.py scripts/tests/test_tcg_transform.py -q
```

The reviewed PDF builds are in the ignored `output/mep-refresh-2026-10-26/`
directory. Existing release archives and their manifest were not rewritten.
