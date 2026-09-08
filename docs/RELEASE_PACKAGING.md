# Release packages and provenance

The current renderer appends one A4 notice page to each PDF, with a
63.5 × 88.9 mm cuttable source card. It also records the project source in PDF
metadata and page footers. The German edition has German introductory notes;
other editions use English. The detailed legal summary is English in every
PDF. Full English/German guidance is included as `NOTICE.md` in each ZIP.

The new page identifies the limited licence scope described in
[LICENSE-CONTENT.md](../LICENSE-CONTENT.md); it does not claim rights in
third-party material, unprotectable elements, or independently created custom
content. The software remains [MIT](../LICENSE-CODE). Existing published PDFs
and valid earlier licence grants are not changed by this build process.

## Building current release candidates

The reusable `build-release.yml` workflow supplies the release label and
checked-out commit to both PDF generation and packaging. For a local build,
set these before generating the PDFs:

```bash
export BINDER_POKEDEX_BUILD_VERSION="candidate-name"
export BINDER_POKEDEX_BUILD_REF="$(git rev-parse HEAD)"
python scripts/pdf/generate_pdf.py --scope all
python scripts/release/package_archives.py \
  --tag "$BINDER_POKEDEX_BUILD_VERSION" \
  --source-ref "$BINDER_POKEDEX_BUILD_REF"
```

Use a clean checkout for a release whose commit should reproduce the source.
Without explicit build variables, a PDF is marked `local / unversioned` with
an unrecorded source commit. No previous release number is inferred.

Packaging requires nonempty PDFs in all nine `output/<language>/` folders,
the release tag, a full source SHA, and the notice files. Each ZIP keeps the
PDFs, `LICENSE`, `LICENSE-CODE`, `LICENSE-CONTENT.md`, `NOTICE.md`, the full
`LICENSES/CC-BY-NC-4.0.txt`, and `SOURCE.json` together inside its language
folder. Build the manifest and render release notes after packaging, then run
`scripts/release/verify_release_candidate.py` as in the workflow. Current
candidate verification rejects missing/empty notices or inconsistent source
identity; it is not a verifier for historical archives lacking those files.

## Focused checks without downloading Pokémon data

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q \
  scripts/tests/test_project_notices.py \
  scripts/tests/test_release_candidate.py \
  scripts/tests/test_release_workflows.py \
  scripts/tests/test_pdf_rendering.py \
  scripts/tests/test_pdf_generation_options.py
```

These checks inspect real PDF pages/metadata and every language archive. They
do not replace validation of a complete release's downloaded assets and all
production scopes.
