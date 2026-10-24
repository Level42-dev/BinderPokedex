# Repository agent guidance

## Pull request review and merge

Keep auto-merge disabled. For a PR you intend to merge, check the applicable
tests and request `@codex review` on the final head commit. Check for unresolved
review findings and confirm the PR head has not changed. Merge only after the
operator explicitly approves that PR and final commit in the chat; then read
back the merged state. A clean Codex review alone is not merge authorization.

## Poster artwork generation

Before starting GPU-intensive poster artwork generation, resolve the active
poster workspace and look for its ignored `renderer.local.yaml` marker. The
default marker lives in `tmp/poster-workspaces/`; a custom combined workspace
uses its `$BINDER_POKEDEX_POSTER_ASSETS` root.
If that marker contains a complete local or remote configuration, reuse it for
the current workspace without asking again. Ask the operator to choose local or
remote only when the workspace is fresh, the marker is missing or incomplete,
the configured worker is unreachable, or the operator explicitly requests a
different target. Do not infer a target from conversation history, unrelated
SSH state, or a running ComfyUI process.

After the operator chooses a target, write or update that workspace marker and
restrict it to the current user. The marker may contain the target plus private SSH alias and runtime,
model-cache, job, and repository paths. It is workspace-local operator state:
never stage, commit, quote in reports, or copy it into render jobs or
provenance. A newly created custom workspace has no marker and therefore asks
once.

- For a local Apple Metal/MPS render, follow
  `docs/POSTER_WORKFLOW.md` and keep the ComfyUI input/output directories scoped
  to the selected poster asset key.
- For a remote render, follow `docs/POSTER_RENDER_WORKER.md`. Ask only for
  configuration values absent from the active workspace marker. Help probe,
  bootstrap or transfer the disposable runtime, execute and retrieve the
  immutable render job, and clean up the runtime, but leave authentication to
  the operator's existing SSH setup.
- Never commit or report real hostnames, IP addresses, usernames, SSH aliases,
  machine-specific paths, tokens, or keys. Private connection values may exist
  only in the ignored local marker or the operator's SSH configuration. Never
  print secret material such as private keys or access tokens. Do not expose
  ComfyUI on a public interface; the remote worker must bind to loopback and
  queue the workflow on that host.
- Always bring back `run.json`, `comfyui.log`, and every output image. A
  successful render is not approval: inspect the full poster and all physical
  card crops before any promotion.
- Treat downloaded cutouts and set logos as reproducible source-cache files.
  Fetch them with `fetch_poster_sources.py` below the ignored
  `tmp/poster-workspaces/<asset-key>/sources/` tree and never commit them.
  Promotion commits only the reviewed text-free master and its provenance;
  provenance retains the exact source hashes used for the review.

This choice applies only to artwork generation. Fetching data, deterministic
localization, slicing, PDF rendering, and release validation do not require a
render worker. TCG PDF builds must fetch their configured title logos with
`fetch_poster_sources.py --kind logos`; Pokédex posters use deterministic text
titles and do not require that download.
