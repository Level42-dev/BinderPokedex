# Remote Apple Silicon poster render worker

The poster generator can submit self-contained ComfyUI jobs to another Apple
Silicon Mac without turning that host into a manually maintained workstation.
The render worker is deliberately native: Docker Desktop runs Linux in a VM
and does not expose the macOS Metal/MPS backend required by this workflow.

## Architecture

1. The repository creates a job directory containing one ComfyUI API workflow,
   its input images, and SHA-256 records for every workflow, input, and model.
2. A disposable native runtime provides pinned Python, ComfyUI, and Python
   packages without installing them globally. A separate model cache is linked
   read-only by convention and is never packaged with the runtime.
3. The job is copied to an isolated job root over SSH or `rsync`. The remote
   worker validates every hash, the pinned runtime, and the available model
   files before starting ComfyUI.
4. ComfyUI listens on remote loopback only. The worker requires the startup log
   to report `Device: mps`, queues the workflow, and stops ComfyUI afterwards.
   Before queueing, it also verifies that the server reports this job's exact
   input directory; a different ComfyUI process already using the port is
   rejected instead of receiving the workflow.
5. `run.json`, `comfyui.log`, and the generated images are copied back for
   visual review. Nothing is promoted automatically.

The job is the interface. Prompt text may be embedded in the API workflow, and
all scene data or reference images consumed by `LoadImage` travel under the
job's `input/` directory. Models stay cached on the render host and are named
and hash-pinned by each job rather than copied for every run.

The repository stores only bootstrap code, the runtime lock, dependency hashes,
and expected model hashes. It does not store Python distributions, ComfyUI
archives, installed packages, model weights, credentials, or built bundles.
Runtime and model lifecycles are deliberately independent:

- deleting the runtime removes Python, ComfyUI, uv, and installed packages;
- deleting a job removes only that workflow, its inputs, logs, and outputs;
- the operator-selected model cache remains reusable until explicitly removed.

`Device: mps` proves that ComfyUI selected Metal as its primary accelerator;
it does not prove that every auxiliary model used MPS. For example, a text
encoder may run once on CPU while the diffusion model samples on MPS. Keep and
review `comfyui.log` whenever per-stage device placement matters.

## Shared GPU scheduling

Current render jobs acquire a per-user, per-host file lock before starting
ComfyUI. The private image worker uses the same lock, so both entry points can
accept work while native rendering proceeds one job at a time. The default is
the user's native cache directory under `comfyui-worker/gpu.lock`;
`COMFYUI_GPU_LOCK` can select one common private path for controlled operations.
Do not point the two clients at different locks.

The ComfyUI child inherits the locked descriptor. A runner crash therefore
does not release the GPU while that child still runs. Jobs retain their
isolated input/output directories, loopback listener, pinned models and
complete returned evidence. Existing immutable job packages are not modified;
ensure older uncoordinated runs have completed before activating a new client.

## Agent/operator handshake

Each poster-assets workspace chooses **local** or **remote** generation once.
An artwork-generating agent first checks the workspace's ignored
`renderer.local.yaml`. A complete marker is reused without another question.
The agent asks only for a fresh workspace, missing values, an unreachable
configured worker, or an explicit target change. Conversation history,
unrelated SSH state, and running ComfyUI processes are not configuration. If
local is selected, return to the local launcher in
[Poster Workflow](POSTER_WORKFLOW.md).

After the choice, store the target and any private connection paths in
`renderer.local.yaml` at the active workspace root with user-only file
permissions. This is `tmp/poster-workspaces/` by default and
`$BINDER_POKEDEX_POSTER_ASSETS` for a custom combined workspace. The marker is
ignored local operator state and must never be
staged, committed, included in a render job, copied into provenance, or quoted
in a report. Passwords, access tokens, and private keys remain outside both the
marker and repository; SSH authentication stays in the operator's existing SSH
setup.

## Bind a worker without committing host details

Keep connection values in the ignored workspace marker, the current shell, or
the operator's private SSH configuration. A marker uses this private shape;
the placeholders are deliberately not real endpoints:

```yaml
schema_version: 1
target: remote
ssh_alias: SSH_CONFIG_ALIAS
runtime_root: /absolute/path/to/ephemeral/BinderPokedex-runtime
model_root: /absolute/path/to/persistent/BinderPokedex-models
job_root: /absolute/path/to/ephemeral/BinderPokedex-jobs
repository_root: /absolute/path/to/BinderPokedex-checkout
```

Export those values for the commands below without printing them:

```bash
export BINDER_RENDER_SSH="SSH_CONFIG_ALIAS"
export BINDER_RUNTIME_ROOT="/absolute/path/to/ephemeral/BinderPokedex-runtime"
export BINDER_MODEL_ROOT="/absolute/path/to/persistent/BinderPokedex-models"
export BINDER_JOB_ROOT="/absolute/path/to/ephemeral/BinderPokedex-jobs"
export BINDER_RENDER_REPO="/absolute/path/to/BinderPokedex-checkout"
```

To remember the selection for one workspace, store the target and these values
in `.poster-renderer.env` with owner-only permissions. The file is ignored.
Source it for a render session; do not copy it into render jobs or a different
checkout.

Probe the selected host before transferring a job:

```bash
ssh "$BINDER_RENDER_SSH" 'uname -s; uname -m'
ssh "$BINDER_RENDER_SSH" \
  "git -C '$BINDER_RENDER_REPO' status --short --branch"
```

The expected platform is `Darwin` on `arm64`; the remote checkout should be on
the intended commit or feature branch. This probe does not grant permission to
install software, download models, or start a render. Confirm those separately
when needed.

Do not add these values to `.env`, Git configuration, tracked manifests, run
metadata, or documentation. The ignored `renderer.local.yaml` is the sole
repository-workspace exception. Do not expose port 8188 publicly and do not
point the normal local runner's `--server` option at a public remote URL.
`render_job.py run` starts loopback-only ComfyUI and queues the workflow on the
worker, which also keeps job-local input-path validation intact.

## Build an ephemeral native runtime

Transfer or clone the selected repository revision on the render host, then run:

```bash
scripts/poster_assets/bootstrap_macos_renderer.sh \
  "$BINDER_RUNTIME_ROOT" \
  "$BINDER_MODEL_ROOT"
```

The command downloads a checksum-pinned standalone `uv`, installs a pinned
portable Python inside the runtime, syncs the hash-locked ComfyUI dependencies,
extracts a checksum-pinned ComfyUI source archive, applies the repository's
version-checked Apple-MPS compatibility patch, and verifies native MPS. It does
not require Homebrew Python or Git, install global packages, download models,
or write to shell profiles.

`ComfyUI/models` is a symbolic link to `BINDER_MODEL_ROOT`. The cache must be
outside `BINDER_RUNTIME_ROOT`; the bootstrap and destroy commands reject nested
paths. A typical private cache contains:

```text
BINDER_MODEL_ROOT/
├── diffusion_models/
├── text_encoders/
├── vae/
└── upscale_models/
```

The concrete cache path is operator state. Never add it to tracked config,
documentation examples with real values, provenance, or a render job.

Gated Hugging Face models require a one-time login performed by the host owner:

```bash
"$BINDER_RUNTIME_ROOT/venv/bin/hf" auth login
```

Never put a Hugging Face token in the repository, workflow, job manifest, or
chat. Download approved model files into the corresponding directory below
`BINDER_MODEL_ROOT`, then record their relative paths and SHA-256 values in the
job. Model binaries never enter a Git commit or runtime bundle.

## Optional runtime bundle transfer

Building directly on the worker avoids transferring installed packages. For an
offline worker, build the same native runtime on a compatible Apple Silicon Mac
and package it without dereferencing the external model-cache link:

```bash
scripts/poster_assets/package_macos_renderer.sh \
  "$BINDER_RUNTIME_ROOT" \
  tmp/renderer-runtime.tar.gz
```

After transfer and extraction, bind that worker's private model cache and
rewrite only the ignored runtime marker:

```bash
"$BINDER_RUNTIME_ROOT/venv/bin/python" \
  "$BINDER_RENDER_REPO/scripts/poster_assets/renderer_runtime.py" \
  bind-models \
  --runtime-root "$BINDER_RUNTIME_ROOT" \
  --model-root "$BINDER_MODEL_ROOT"
```

The archive is a disposable ignored artifact, not a release or repository
asset. Its model entry is a symlink, so model weights are not copied into it.

## Prepare a job locally

The command refuses to overwrite an existing job directory:

```bash
python scripts/poster_assets/render_job.py prepare \
  --workflow path/to/workflow_api.json \
  --job-dir tmp/render-jobs/exgen2-normal-kontext-bf16 \
  --input path/to/scene.png=scene.png \
  --model diffusion_models/flux1-kontext-dev.safetensors=SHA256 \
  --model text_encoders/clip_l.safetensors=SHA256 \
  --model text_encoders/t5xxl_fp16.safetensors=SHA256 \
  --model vae/ae.safetensors=SHA256
```

Every `LoadImage` filename in the workflow must match the destination name on
the right side of an `--input SOURCE=DESTINATION` argument.

## Transfer and run

Choose a local job name and transfer the immutable directory to the worker:

```bash
export JOB_NAME="reviewed-job-name"
export LOCAL_JOB_DIR="tmp/render-jobs/$JOB_NAME"

rsync -a "$LOCAL_JOB_DIR/" \
  "$BINDER_RENDER_SSH:$BINDER_JOB_ROOT/$JOB_NAME/"
```

Open an SSH session and run the job with the already bootstrapped worker. The
paths remain runtime values and are not copied into tracked project files:

```bash
ssh "$BINDER_RENDER_SSH"
```

On the render host:

```bash
"$BINDER_RUNTIME_ROOT/venv/bin/python" \
  "$BINDER_RENDER_REPO/scripts/poster_assets/render_job.py" run \
  --job-dir "$BINDER_JOB_ROOT/JOB_NAME" \
  --comfyui-root "$BINDER_RUNTIME_ROOT/ComfyUI" \
  --python "$BINDER_RUNTIME_ROOT/venv/bin/python" \
  --models-root "$BINDER_RUNTIME_ROOT/ComfyUI/models"
```

Copy the completed job back and review `run.json`, `comfyui.log`, the whole
poster, and every physical card crop. A successful remote process is evidence
of reproducibility, not visual approval.

After leaving the SSH session, retrieve the entire completed job:

```bash
rsync -a \
  "$BINDER_RENDER_SSH:$BINDER_JOB_ROOT/$JOB_NAME/" \
  "$LOCAL_JOB_DIR/"
```

Keep the returned job ignored until review. Promotion still happens through the
normal local review and promotion gate; a remote worker never promotes assets.

When no further render is pending, remove the runtime through its validated
marker. This leaves the external model cache untouched:

```bash
scripts/poster_assets/destroy_macos_renderer.sh "$BINDER_RUNTIME_ROOT"
```

Dependency updates are deliberate maintenance changes. Run
`scripts/poster_assets/refresh_renderer_lock.sh`, update the two printed hashes
in `renderer-runtime.lock.json`, run the renderer tests, and perform one native
MPS smoke render. Never silently replace a pinned model or runtime underneath a
reviewed job.
