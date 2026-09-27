from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.poster_assets import render_job

from scripts.poster_assets.render_job import (
    COMFYUI_COMMIT,
    executable_path,
    prepare_job,
    require_custom_node,
    run_job,
    sha256_file,
    validate_job,
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_executable_path_preserves_virtualenv_symlink(tmp_path: Path) -> None:
    target = tmp_path / "python3.11"
    target.write_bytes(b"")
    virtualenv_python = tmp_path / "venv" / "bin" / "python"
    virtualenv_python.parent.mkdir(parents=True)
    virtualenv_python.symlink_to(target)

    assert executable_path(virtualenv_python) == virtualenv_python.absolute()


def test_prepare_and_validate_portable_render_job(tmp_path: Path) -> None:
    workflow = tmp_path / "source_workflow.json"
    write_json(
        workflow,
        {
            "1": {
                "class_type": "LoadImage",
                "inputs": {"image": "scene.png"},
            }
        },
    )
    source = tmp_path / "scene.png"
    source.write_bytes(b"exact input")
    models_root = tmp_path / "models"
    model = models_root / "diffusion_models" / "model.safetensors"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"exact model")

    job_dir = tmp_path / "job"
    manifest_path = prepare_job(
        workflow,
        job_dir,
        [f"{source}=scene.png"],
        [f"diffusion_models/model.safetensors={sha256_file(model)}"],
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["format_version"] == 1
    assert manifest["comfyui_commit"] == COMFYUI_COMMIT
    assert manifest["inputs"] == [
        {"path": "scene.png", "sha256": sha256_file(source)}
    ]
    assert validate_job(job_dir, models_root) == manifest


def test_validate_rejects_changed_render_input(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.json"
    write_json(
        workflow,
        {"1": {"class_type": "SaveImage", "inputs": {}}},
    )
    source = tmp_path / "scene.png"
    source.write_bytes(b"before")
    job_dir = tmp_path / "job"
    prepare_job(workflow, job_dir, [str(source)], [])
    (job_dir / "input" / "scene.png").write_bytes(b"after")

    with pytest.raises(ValueError, match="input SHA-256 mismatch"):
        validate_job(job_dir, tmp_path / "models")


def test_prepare_requires_every_load_image_input(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.json"
    write_json(
        workflow,
        {
            "1": {
                "class_type": "LoadImage",
                "inputs": {"image": "scene.png"},
            }
        },
    )

    with pytest.raises(ValueError, match="missing LoadImage inputs: scene.png"):
        prepare_job(workflow, tmp_path / "job", [], [])


@pytest.mark.parametrize(
    "spec",
    (
        "source.png=../escape.png",
        "source.png=/absolute.png",
    ),
)
def test_prepare_rejects_unsafe_input_destination(
    tmp_path: Path,
    spec: str,
) -> None:
    workflow = tmp_path / "workflow.json"
    write_json(
        workflow,
        {"1": {"class_type": "SaveImage", "inputs": {}}},
    )
    source = tmp_path / "source.png"
    source.write_bytes(b"input")
    expanded_spec = spec.replace("source.png", str(source), 1)

    with pytest.raises(ValueError, match="safe relative path"):
        prepare_job(workflow, tmp_path / "job", [expanded_spec], [])


def test_prepare_does_not_overwrite_existing_job(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.json"
    write_json(
        workflow,
        {"1": {"class_type": "SaveImage", "inputs": {}}},
    )
    job_dir = tmp_path / "job"
    prepare_job(workflow, job_dir, [], [])

    with pytest.raises(FileExistsError, match="already exists"):
        prepare_job(workflow, job_dir, [], [])


def _extension_fixture(tmp_path: Path) -> tuple[Path, Path]:
    workflow = tmp_path / "workflow.json"
    write_json(workflow, {"1": {"class_type": "SaveImage", "inputs": {}}})
    extension = tmp_path / "comfy_extension"
    extension.mkdir()
    (extension / "__init__.py").write_text("NODE_CLASS_MAPPINGS = {}\n", encoding="utf-8")
    (extension / "region_math.py").write_text("VALUE = 1\n", encoding="utf-8")
    return workflow, extension


def test_extension_job_is_portable_and_hashes_every_python_file(tmp_path: Path) -> None:
    workflow, extension = _extension_fixture(tmp_path)
    job_dir = tmp_path / "job"
    manifest_path = prepare_job(workflow, job_dir, [], [], extension_source=extension)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["format_version"] == 2
    assert manifest["extensions"]["name"] == "binder_region_joint"
    assert [item["path"] for item in manifest["extensions"]["files"]] == [
        "__init__.py", "region_math.py",
    ]
    assert str(tmp_path) not in manifest_path.read_text(encoding="utf-8")
    assert validate_job(job_dir, tmp_path / "models") == manifest


def test_extension_job_rejects_tampered_or_unlisted_code(tmp_path: Path) -> None:
    workflow, extension = _extension_fixture(tmp_path)
    job_dir = tmp_path / "job"
    prepare_job(workflow, job_dir, [], [], extension_source=extension)
    code = job_dir / "extensions/binder_region_joint/region_math.py"
    code.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="extension SHA-256 mismatch"):
        validate_job(job_dir, tmp_path / "models")
    code.write_text("VALUE = 1\n", encoding="utf-8")
    (code.parent / "unlisted.py").write_text("BAD = True\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unlisted extension"):
        validate_job(job_dir, tmp_path / "models")


def test_extension_job_rejects_source_and_job_symlinks(tmp_path: Path) -> None:
    workflow, extension = _extension_fixture(tmp_path)
    (extension / "region_math.py").unlink()
    outside = tmp_path / "outside.py"
    outside.write_text("VALUE = 1\n", encoding="utf-8")
    (extension / "region_math.py").symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        prepare_job(workflow, tmp_path / "job", [], [], extension_source=extension)

    (extension / "region_math.py").unlink()
    (extension / "region_math.py").write_text("VALUE = 1\n", encoding="utf-8")
    job_dir = tmp_path / "job-2"
    prepare_job(workflow, job_dir, [], [], extension_source=extension)
    code = job_dir / "extensions/binder_region_joint/region_math.py"
    code.unlink()
    code.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        validate_job(job_dir, tmp_path / "models")


@pytest.mark.parametrize("tamper", ["../escape.py", "duplicate"])
def test_extension_job_rejects_unsafe_or_duplicate_manifest_paths(tmp_path: Path, tamper: str) -> None:
    workflow, extension = _extension_fixture(tmp_path)
    job_dir = tmp_path / "job"
    manifest_path = prepare_job(workflow, job_dir, [], [], extension_source=extension)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if tamper == "duplicate":
        manifest["extensions"]["files"].append(dict(manifest["extensions"]["files"][0]))
    else:
        manifest["extensions"]["files"][0]["path"] = tamper
    write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="extension path"):
        validate_job(job_dir, tmp_path / "models")


@pytest.mark.parametrize("with_extension", [False, True])
def test_only_format_two_starts_with_job_local_extension_flags(tmp_path: Path, monkeypatch, with_extension: bool) -> None:
    workflow, extension = _extension_fixture(tmp_path)
    job_dir = tmp_path / "job"
    prepare_job(
        workflow, job_dir, [], [], extension_source=extension if with_extension else None,
    )
    comfyui_root = tmp_path / "ComfyUI"
    (comfyui_root / "models").mkdir(parents=True)
    (comfyui_root / "main.py").write_text("", encoding="utf-8")
    python_bin = tmp_path / "python"
    python_bin.write_text("", encoding="utf-8")
    monkeypatch.setattr(render_job, "comfyui_commit", lambda _root: COMFYUI_COMMIT)

    class StartupObserved(Exception):
        pass

    def inspect_start(command, **_kwargs):
        assert command[2:4] == ["--listen", "127.0.0.1"]
        if with_extension:
            assert "--extra-model-paths-config" in command
            assert "--disable-all-custom-nodes" in command
            assert command[-2:] == ["--whitelist-custom-nodes", "binder_region_joint"]
            config = Path(command[command.index("--extra-model-paths-config") + 1])
            assert yaml.safe_load(config.read_text(encoding="utf-8"))["pilot"]["custom_nodes"] == str(job_dir / "extensions")
        else:
            assert "--extra-model-paths-config" not in command
            assert "--disable-all-custom-nodes" not in command
            assert "--whitelist-custom-nodes" not in command
        raise StartupObserved

    monkeypatch.setattr(render_job.subprocess, "Popen", inspect_start)
    with pytest.raises(StartupObserved):
        run_job(job_dir, comfyui_root, python_bin, comfyui_root / "models", 8188, 1)


def test_format_two_rejects_existing_worker_node_name_before_start(tmp_path: Path, monkeypatch) -> None:
    workflow, extension = _extension_fixture(tmp_path)
    job_dir = tmp_path / "job"
    prepare_job(workflow, job_dir, [], [], extension_source=extension)
    comfyui_root = tmp_path / "ComfyUI"
    (comfyui_root / "models").mkdir(parents=True)
    (comfyui_root / "custom_nodes/binder_region_joint").mkdir(parents=True)
    python_bin = tmp_path / "python"
    python_bin.write_text("", encoding="utf-8")
    monkeypatch.setattr(render_job, "comfyui_commit", lambda _root: COMFYUI_COMMIT)
    with pytest.raises(ValueError, match="collision"):
        run_job(job_dir, comfyui_root, python_bin, comfyui_root / "models", 8188, 1)


def test_missing_custom_node_refuses_queueing(monkeypatch) -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b"{}"

    monkeypatch.setattr(render_job.urllib.request, "urlopen", lambda *_args, **_kwargs: Response())
    with pytest.raises(RuntimeError, match="RegionConstrainedJointGuider"):
        require_custom_node("http://127.0.0.1:8188", "RegionConstrainedJointGuider")
