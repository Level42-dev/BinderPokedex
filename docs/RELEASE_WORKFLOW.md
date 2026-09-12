# Release Workflow

BinderPokedex uses one shared release-candidate build for tagged releases and
selected pull requests. Release and hotfix branches always rehearse the full
payload before merging into `main`; an ordinary feature pull request does so
only when it carries the `full-release-check` label. A pull-request rehearsal
never publishes a GitHub Release.

## Workflow boundary

```text
Build Release Candidate (reusable, read-only)
  -> verify the committed source/output snapshot byte-for-byte
  -> fetch only reproducible poster logo sources
  -> validate every PDF-enabled promoted poster
  -> generate every scope in every supported language
  -> create all language ZIP archives
  -> build and verify release-manifest.json
  -> render and verify versioned GitHub release notes
  -> upload one temporary Actions artifact

Verify Release Build (release/hotfix PR, labeled PR, or manual)
  -> call Build Release Candidate
  -> stop after the temporary artifact

Create Release (v* tag only)
  -> call Build Release Candidate
  -> download the verified artifact
  -> publish the GitHub Release
```

The reusable build never contacts mutable card-data APIs. It consumes the
reviewed files bound by `data/snapshot.json`; any missing, additional, or
changed source/output JSON file stops the job before rendering. Refreshes use
the single audited command sequence documented in
[Data Fetcher](DATA_FETCHER.md#canonical-reviewed-refresh).

The reusable build and pull-request caller have only `contents: read`
permission. Only the `publish` job in `Create Release` has `contents: write`.
The PR workflow cannot create tags, releases, commits, announcement changes, or
repository pull requests.

## Release communication

Release communication has three deliberately separate roles:

- `CHANGELOG.md` is the complete technical history for maintainers and
  contributors. It records implementation, compatibility, verification, and
  fallback details.
- `config/release_notes/<tag>.yaml` contains collector-facing feature news. It
  supplies the concise, benefit-led copy for the GitHub Release and must avoid
  internal review, CI, model, or repository terminology unless users need it.
- the marker-delimited `release-news` block near the top of both READMEs is the
  current storefront. Before publication it previews the next major feature;
  after publication the announcement workflow replaces that single block with
  the published release news and download link.

The README links to the changelog instead of duplicating technical release
history. This keeps the project record complete without turning the start page
into a maintainer log.

## Poster behavior

ComfyUI and agent-assisted authoring are not CI dependencies. Poster candidates
are generated and reviewed locally, then promoted as versioned repository
assets. The shared release build runs:

```bash
python scripts/poster_assets/validate_promoted_poster.py --all-enabled
```

after verifying the reviewed scope data and before generating PDFs. The build fails
when an enabled bundle has missing files, provenance or manifest drift, changed
prompt inputs, invalid source-pixel evidence, incorrect dimensions, or wrong
print metadata.

The normal PDF command then discovers every enabled legacy manifest and every
enabled aggregate binding from `posters.yaml`, adds localized logo/text, slices
the text-free masters, and embeds the cards at their configured section
positions. It never starts ComfyUI.

## Pull-request release rehearsal

`.github/workflows/verify-release.yml` listens to pull requests targeting
`main`, but calls the expensive reusable build only when at least one of these
conditions applies:

- the source branch starts with `release/`;
- the source branch starts with `hotfix/`;
- the pull request has the `full-release-check` label; or
- a maintainer starts the workflow manually.

The label is the explicit opt-in for feature branches that change PDF
rendering, release inputs, promoted assets, or other behavior that should be
proved against the complete payload before merge. Adding the label starts the
build immediately; subsequent commits retrigger it while the label remains.
Removing the label cancels an in-progress rehearsal through the workflow's
concurrency rule. Ordinary feature and documentation pull requests leave the
release-candidate job skipped and consume no release-build runner time.

When selected, the workflow calls the same reusable workflow as a tag release
and therefore builds:

- all configured scopes;
- all nine release languages;
- every language-specific ZIP;
- the release manifest;
- the exact file set consumed by the publish job.

The temporary manifest keeps its `pr-<number>-<sha>` build label while loading
the explicitly configured upcoming release-news contract (`v9.0` for the
current feature branch). A tagged release instead uses its own tag for both
fields. This makes missing or malformed major-release news fail before merge.

The resulting `release-candidate` is an ordinary short-lived Actions artifact,
not a GitHub Release. Its purpose is inspection and proof that publication
could succeed from that commit.

## Tagged release

`.github/workflows/release.yml` remains restricted to `v*` tags. Its publish
job cannot start until the shared candidate build succeeds. It publishes the
already verified artifact without rebuilding PDFs or archives and uses the
candidate's `release-notes.md` as the GitHub Release body. The announcement is
rendered from `config/release_notes/<tag>.yaml` and tagged repository images;
it is not hard-coded in the workflow.

After publication, `.github/workflows/announce-release.yml` consumes the
release manifest and prepares the separate README announcement pull request.

## Release-candidate verification

`scripts/release/verify_release_candidate.py` rejects a candidate unless:

- every configured scope has generated card-count data;
- every language has at least one PDF;
- total and per-language PDF counts agree;
- all nine expected ZIP files exist and match their manifest sizes;
- every ZIP is readable and contains the expected number of PDFs.
- the rendered release notes match the tag, contain English and German feature
  titles, and link all nine language archives.

`--skip-poster` remains a local diagnostic option. Official PR rehearsals and
tagged releases do not use it; an invalid enabled poster must fail the build
instead of silently disappearing from the release.
