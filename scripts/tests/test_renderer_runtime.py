from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.poster_assets.renderer_runtime import (
    LOCK_PATH,
    MODEL_DIRECTORIES,
    RUNTIME_MARKER,
    bind_model_cache,
    comfyui_commit,
    destroy_runtime,
    load_runtime_marker,
    validate_runtime,
    validate_runtime_lock,
)


ROOT = Path(__file__).resolve().parents[2]


def make_runtime(tmp_path: Path) -> tuple[Path, Path]:
    runtime = tmp_path / "ephemeral" / "renderer"
    (runtime / "ComfyUI" / "models").mkdir(parents=True)
    python = runtime / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"test interpreter")
    models = tmp_path / "persistent-model-cache"
    bind_model_cache(runtime, models)
    return runtime, models


def test_renderer_lock_pins_downloads_and_hashed_requirements() -> None:
    lock = validate_runtime_lock()

    assert lock["platform"] == {"machine": "arm64", "system": "Darwin"}
    assert lock["python"]["version"] == "3.11.13"
    assert len(lock["uv"]["archive_sha256"]) == 64
    assert len(lock["comfyui"]["archive_sha256"]) == 64
    requirements = (ROOT / lock["requirements"]["lock_path"]).read_text()
    assert "--hash=sha256:" in requirements
    assert "torch==" in requirements


def test_bootstrap_uses_portable_python_and_external_model_cache() -> None:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    bootstrap = (
        ROOT / "scripts/poster_assets/bootstrap_macos_renderer.sh"
    ).read_text(encoding="utf-8")

    assert lock["uv"]["archive_sha256"] in bootstrap
    assert lock["comfyui"]["archive_sha256"] in bootstrap
    assert '"$UV_BIN" python install "$PYTHON_VERSION"' in bootstrap
    assert '"$SCRIPT_DIR/renderer_runtime.py" validate-lock' in bootstrap
    assert "--require-hashes" in bootstrap
    assert 'ln -s "$MODEL_ROOT" "$COMFY_ROOT/models"' in bootstrap
    assert "/opt/homebrew" not in bootstrap
    assert "git clone" not in bootstrap


def test_model_cache_binding_lives_outside_runtime(tmp_path: Path) -> None:
    runtime, models = make_runtime(tmp_path)

    assert (runtime / "ComfyUI" / "models").is_symlink()
    assert (runtime / "ComfyUI" / "models").resolve() == models.resolve()
    assert all((models / name).is_dir() for name in MODEL_DIRECTORIES)
    marker = load_runtime_marker(runtime)
    assert marker["model_root"] == str(models.resolve())
    assert comfyui_commit(runtime / "ComfyUI") == marker["comfyui_commit"]
    assert validate_runtime(runtime) == marker


def test_binding_rejects_model_cache_inside_ephemeral_runtime(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "renderer"
    (runtime / "ComfyUI").mkdir(parents=True)
    python = runtime / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"test interpreter")

    with pytest.raises(ValueError, match="outside the ephemeral runtime"):
        bind_model_cache(runtime, runtime / "models")


def test_destroy_removes_only_runtime_and_preserves_models(tmp_path: Path) -> None:
    runtime, models = make_runtime(tmp_path)
    model = models / "diffusion_models" / "reviewed.safetensors"
    model.write_bytes(b"model payload remains external")

    destroy_runtime(runtime)

    assert not runtime.exists()
    assert model.read_bytes() == b"model payload remains external"


def test_destroy_refuses_unmarked_directory(tmp_path: Path) -> None:
    runtime = tmp_path / "not-a-renderer" / "nested"
    runtime.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        destroy_runtime(runtime)


def test_runtime_marker_is_not_a_tracked_machine_configuration() -> None:
    assert not (ROOT / RUNTIME_MARKER).exists()
    tracked_runtime_files = subprocess.run(
        ["git", "ls-files", "--", RUNTIME_MARKER, "*.safetensors"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert tracked_runtime_files == []


def test_local_launcher_has_no_machine_specific_default_path() -> None:
    launcher = (
        ROOT / "scripts/poster_assets/start_comfyui_poster.sh"
    ).read_text(encoding="utf-8")

    assert "/Volumes/" not in launcher
    assert 'COMFY_ROOT="${COMFY_ROOT:-$ROOT_DIR/.local_ai/ComfyUI}"' in launcher
