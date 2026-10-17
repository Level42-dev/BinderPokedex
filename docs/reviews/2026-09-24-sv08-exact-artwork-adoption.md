# SV08 exact-artwork adoption — 2026-09-24

The operator's [22 September shortlist feedback](2026-09-22-shortlist-user-feedback.json)
accepts the exact existing SV08 text-free master, including the disclosed small
Ho-Oh eye and line differences. This is artwork acceptance, not blanket PDF or
release approval. The accepted master SHA-256 is
`d931776dc062cc9f9db4b632fab658ce678ad6fe2afcc73d33e363f1e51fe7f8`.
The earlier agent revocation remains documented in the
[original panorama audit](2026-09-12-panorama-audit-late-tcg.json) and
[second review](2026-09-12-panorama-audit-me05-sv08-second-review.json);
the later human decision resolves only the displayed, disclosed differences
for these exact pixels. Re-promotion replaces the historical revocation field
inside the active production provenance, not those immutable review reports.

The original 300-dpi candidate and installed production master had that same
byte hash. The original raw image had SHA-256
`038d4f2e3df89aa08644e57d9bb1bbd1649b386eed25fb74636bda62241dc73c`.
The three exact source hashes agree with the feedback record. The full master,
all nine existing physical crops, and the three bottom-row source/crop pairs
were visually rechecked before technical adoption. The operator is not claimed
to have separately inspected all nine crops.

The normal promotion path re-bound the existing raw and print images to the
recorded source, generation fingerprint and explicit human artwork decision.
No generation or replacement image was used. Only provenance changed; the
production master retained its byte hash. The PDF route was then enabled.
The production validator reports 2368 × 3268 pixels, nine cards and 299.99 dpi;
the planner reports `current` with `pdf_enabled: true`.

A German `--test --skip-images` PDF was generated without overwriting the
ordinary release PDF. Its first A4 page was rasterized and visually checked:
all nine panorama cards, the German title logo, information card and cut lines
are present and contained. This test PDF omits remote ordinary card scans and
is not a complete release proof. The focused poster routing, PDF, fingerprint
and planning tests report 183 passed. A complete release build and independent
PR review remain open. The attempted complete local test collection stopped
on five P16 region-test modules because this local audit environment has no
PyTorch; the four scoped SV08 test groups completed without failures.
