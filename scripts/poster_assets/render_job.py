#!/usr/bin/env python3
"""Prepare, validate, and execute portable ComfyUI render jobs."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

try:
    from .queue_comfyui_workflow import (
        queue_workflow,
        validate_server_input_directory,
    )
    from .renderer_runtime import comfyui_commit
except ImportError:
    from queue_comfyui_workflow import (
        queue_workflow,
        validate_server_input_directory,
    )
    from renderer_runtime import comfyui_commit


FORMAT_VERSION = 1
EXTENSION_FORMAT_VERSION = 2
REGION_EXTENSION_NAME = "binder_region_joint"
REGION_NODE_NAME = "RegionConstrainedJointGuider"
COMFYUI_COMMIT = "87d23b81765161624889febfb3b81f19f3c8435b"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def require_custom_node(server: str, node_name: str) -> None:
    """Refuse a pilot workflow unless ComfyUI registered its job-local node."""
    try:
        with urllib.request.urlopen(f"{server}/object_info/{node_name}", timeout=10) as response:
            info = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not verify custom node {node_name}") from exc
    if not isinstance(info, dict) or node_name not in info:
        raise RuntimeError(f"Custom node {node_name} is not registered")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def executable_path(path: Path) -> Path:
    """Return an absolute executable path without resolving a venv symlink."""
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def safe_relative_path(value: str, *, field: str) -> Path:
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise ValueError(f"{field} must be a safe relative path: {value!r}")
    return Path(*pure.parts)


def parse_copy_spec(value: str) -> tuple[Path, Path]:
    source_text, separator, destination_text = value.partition("=")
    source = Path(source_text).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"Render input does not exist: {source}")
    destination = safe_relative_path(
        destination_text if separator else source.name,
        field="input destination",
    )
    return source, destination


def parse_model_spec(value: str) -> dict[str, str]:
    model_path, separator, digest = value.partition("=")
    relative = safe_relative_path(model_path, field="model path")
    if len(relative.parts) < 2:
        raise ValueError("model path must include its ComfyUI model folder")
    if not separator or not SHA256_RE.fullmatch(digest):
        raise ValueError("model spec must be FOLDER/FILENAME=SHA256")
    return {"path": relative.as_posix(), "sha256": digest}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _checked_extension_source(source: Path) -> list[Path]:
    source = Path(source).expanduser()
    if source.is_symlink() or not source.is_dir():
        raise ValueError("extension source must be a symlink-free directory")
    source = source.resolve()
    files: list[Path] = []
    for item in sorted(source.iterdir()):
        if item.is_symlink():
            raise ValueError("extension source contains a symlink")
        if item.name == "__pycache__" and item.is_dir():
            continue
        if not item.is_file() or item.suffix != ".py":
            raise ValueError("extension source may contain only Python files")
        files.append(item)
    if not any(item.name == "__init__.py" for item in files):
        raise ValueError("extension source requires __init__.py")
    return files


def prepare_job(
    workflow_path: Path,
    job_dir: Path,
    input_specs: list[str],
    model_specs: list[str],
    *,
    extension_source: Path | None = None,
) -> Path:
    extension_files = _checked_extension_source(extension_source) if extension_source is not None else None
    workflow_path = workflow_path.expanduser().resolve()
    workflow = load_json(workflow_path)
    if not workflow or not all(
        isinstance(node, dict) and isinstance(node.get("class_type"), str)
        for node in workflow.values()
    ):
        raise ValueError("workflow must be a non-empty ComfyUI API graph")

    job_dir = job_dir.expanduser().resolve()
    manifest_path = job_dir / "job.json"
    if manifest_path.exists():
        raise FileExistsError(f"Render job already exists: {job_dir}")
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    bundled_workflow = job_dir / "workflow_api.json"
    shutil.copy2(workflow_path, bundled_workflow)
    inputs = []
    destinations: set[str] = set()
    for spec in input_specs:
        source, relative = parse_copy_spec(spec)
        relative_text = relative.as_posix()
        if relative_text in destinations:
            raise ValueError(f"Duplicate render input: {relative_text}")
        destinations.add(relative_text)
        destination = input_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        inputs.append(
            {
                "path": relative_text,
                "sha256": sha256_file(destination),
            }
        )

    required_inputs = {
        str(node.get("inputs", {}).get("image"))
        for node in workflow.values()
        if node.get("class_type") == "LoadImage"
    }
    missing_inputs = sorted(required_inputs - destinations)
    if missing_inputs:
        raise ValueError(
            "Render job is missing LoadImage inputs: "
            + ", ".join(missing_inputs)
        )

    manifest = {
        "format_version": EXTENSION_FORMAT_VERSION if extension_files is not None else FORMAT_VERSION,
        "comfyui_commit": COMFYUI_COMMIT,
        "workflow": {
            "path": bundled_workflow.name,
            "sha256": sha256_file(bundled_workflow),
        },
        "inputs": sorted(inputs, key=lambda item: item["path"]),
        "models": sorted(
            (parse_model_spec(spec) for spec in model_specs),
            key=lambda item: item["path"],
        ),
    }
    if extension_files is not None:
        extension_dir = job_dir / "extensions" / REGION_EXTENSION_NAME
        extension_dir.mkdir(parents=True, exist_ok=False)
        copied = []
        for source in extension_files:
            destination = extension_dir / source.name
            shutil.copy2(source, destination)
            copied.append({"path": source.name, "sha256": sha256_file(destination)})
        manifest["extensions"] = {"name": REGION_EXTENSION_NAME, "files": copied}
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def verify_file(path: Path, expected_sha256: str, *, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label}: {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ValueError(
            f"{label} SHA-256 mismatch for {path}: "
            f"expected {expected_sha256}, got {actual}"
        )


def validate_job(job_dir: Path, models_root: Path) -> dict[str, Any]:
    job_dir = job_dir.expanduser().resolve()
    models_root = models_root.expanduser().resolve()
    manifest = load_json(job_dir / "job.json")
    if manifest.get("format_version") not in (FORMAT_VERSION, EXTENSION_FORMAT_VERSION):
        raise ValueError("Unsupported render-job format_version")
    if manifest.get("comfyui_commit") != COMFYUI_COMMIT:
        raise ValueError("Render job uses an unsupported ComfyUI commit")

    workflow = manifest.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("Render job has no workflow record")
    workflow_path = safe_relative_path(
        str(workflow.get("path", "")),
        field="workflow path",
    )
    verify_file(
        job_dir / workflow_path,
        str(workflow.get("sha256", "")),
        label="workflow",
    )

    for item in manifest.get("inputs", []):
        relative = safe_relative_path(str(item["path"]), field="input path")
        verify_file(
            job_dir / "input" / relative,
            str(item["sha256"]),
            label="input",
        )
    for item in manifest.get("models", []):
        relative = safe_relative_path(str(item["path"]), field="model path")
        verify_file(
            models_root / relative,
            str(item["sha256"]),
            label="model",
        )
    if manifest["format_version"] == EXTENSION_FORMAT_VERSION:
        _validate_extension(job_dir, manifest.get("extensions"))
    elif "extensions" in manifest:
        raise ValueError("Format-1 render job cannot include an extension")
    return manifest


def _validate_extension(job_dir: Path, record: object) -> None:
    if not isinstance(record, dict) or record.get("name") != REGION_EXTENSION_NAME:
        raise ValueError("Render job has no approved regional extension")
    entries = record.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Render job has no extension files")
    root = job_dir / "extensions"
    folder = root / REGION_EXTENSION_NAME
    if root.is_symlink() or folder.is_symlink() or not folder.is_dir():
        raise ValueError("Render job extension is missing or contains a symlink")
    names: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid extension path record")
        value = entry.get("path")
        if not isinstance(value, str):
            raise ValueError("Invalid extension path")
        try:
            relative = safe_relative_path(value, field="extension path")
        except ValueError as exc:
            raise ValueError("Invalid extension path") from exc
        if len(relative.parts) != 1 or relative.suffix != ".py" or value != relative.as_posix() or value in names:
            raise ValueError("Invalid or duplicate extension path")
        names.add(value)
        path = folder / relative
        if path.is_symlink():
            raise ValueError("Render job extension contains a symlink")
        verify_file(path, str(entry.get("sha256", "")), label="extension")
    if "__init__.py" not in names:
        raise ValueError("Render job extension has no __init__.py")
    actual = set()
    for path in folder.iterdir():
        if path.is_symlink():
            raise ValueError("Render job extension contains a symlink")
        if not path.is_file() or path.suffix != ".py":
            raise ValueError("Render job contains unlisted extension content")
        actual.add(path.name)
    if actual != names:
        raise ValueError("Render job contains unlisted extension files")


def wait_for_server(server: str, log_path: Path, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"ComfyUI stopped during startup; inspect {log_path}"
            )
        try:
            with urllib.request.urlopen(
                f"{server}/system_stats",
                timeout=2,
            ) as response:
                response.read()
            log_text = ANSI_RE.sub(
                "",
                log_path.read_text(encoding="utf-8", errors="replace"),
            )
            if "Device: mps" in log_text:
                return
            if re.search(r"Device:\s+\S+", log_text):
                raise RuntimeError(
                    f"ComfyUI did not report Device: mps; inspect {log_path}"
                )
            time.sleep(1)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    raise TimeoutError(f"Timed out waiting for ComfyUI; inspect {log_path}")


def run_job(
    job_dir: Path,
    comfyui_root: Path,
    python_bin: Path,
    models_root: Path,
    port: int,
    timeout: int,
) -> Path:
    job_dir = job_dir.expanduser().resolve()
    comfyui_root = comfyui_root.expanduser().resolve()
    python_bin = executable_path(python_bin)
    if not python_bin.is_file():
        raise FileNotFoundError(f"Python executable does not exist: {python_bin}")
    models_root = models_root.expanduser().resolve()
    expected_models_root = (comfyui_root / "models").resolve()
    if models_root != expected_models_root:
        raise ValueError(
            "models-root must be the selected ComfyUI installation's "
            f"models directory: {expected_models_root}"
        )
    manifest = validate_job(job_dir, models_root)
    actual_commit = comfyui_commit(comfyui_root)
    if actual_commit != manifest["comfyui_commit"]:
        raise ValueError(
            f"ComfyUI commit mismatch: expected {manifest['comfyui_commit']}, "
            f"got {actual_commit}"
        )
    if manifest["format_version"] == EXTENSION_FORMAT_VERSION:
        collision = comfyui_root / "custom_nodes" / REGION_EXTENSION_NAME
        if collision.exists() or collision.is_symlink():
            raise ValueError("Regional extension name collision in worker custom_nodes")

    output_dir = job_dir / "output"
    temp_dir = job_dir / "temp"
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / "comfyui.log"
    server = f"http://127.0.0.1:{port}"
    command = [
        str(python_bin),
        str(comfyui_root / "main.py"),
        "--listen",
        "127.0.0.1",
        "--port",
        str(port),
        "--input-directory",
        str(job_dir / "input"),
        "--output-directory",
        str(output_dir),
        "--temp-directory",
        str(temp_dir),
    ]
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    started = time.time()
    with contextlib.ExitStack() as stack:
        if manifest["format_version"] == EXTENSION_FORMAT_VERSION:
            temporary = stack.enter_context(tempfile.TemporaryDirectory(prefix="binder-region-node-"))
            config = Path(temporary) / "extra_model_paths.yaml"
            config.write_text(
                yaml.safe_dump({"pilot": {"custom_nodes": str(job_dir / "extensions")}}),
                encoding="utf-8",
            )
            command.extend((
                "--extra-model-paths-config", str(config),
                "--disable-all-custom-nodes", "--whitelist-custom-nodes", REGION_EXTENSION_NAME,
            ))
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                command,
                cwd=comfyui_root,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                wait_for_server(server, log_path, process)
                if manifest["format_version"] == EXTENSION_FORMAT_VERSION:
                    require_custom_node(server, REGION_NODE_NAME)
                validate_server_input_directory(server, job_dir / "input")
                outputs = queue_workflow(
                    job_dir / manifest["workflow"]["path"],
                    server=server,
                    timeout=timeout,
                )
            finally:
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

    output_records = []
    for item in outputs:
        if item.get("type") != "output":
            continue
        relative = safe_relative_path(
            str(Path(str(item.get("subfolder", ""))) / str(item["filename"])),
            field="output path",
        )
        path = output_dir / relative
        output_records.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256_file(path),
            }
        )
    if not output_records:
        raise RuntimeError("ComfyUI completed without an output image")

    record = {
        "format_version": manifest["format_version"],
        "started_at_unix": started,
        "finished_at_unix": time.time(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "device": "mps",
        "comfyui_commit": actual_commit,
        "workflow_sha256": manifest["workflow"]["sha256"],
        "inputs": manifest["inputs"],
        "models": manifest["models"],
        "outputs": sorted(output_records, key=lambda item: item["path"]),
    }
    run_path = job_dir / "run.json"
    run_path.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return run_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--workflow", type=Path, required=True)
    prepare_parser.add_argument("--job-dir", type=Path, required=True)
    prepare_parser.add_argument("--input", action="append", default=[])
    prepare_parser.add_argument("--model", action="append", default=[])
    prepare_parser.add_argument("--extension-source", type=Path)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--job-dir", type=Path, required=True)
    validate_parser.add_argument("--models-root", type=Path, required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--job-dir", type=Path, required=True)
    run_parser.add_argument("--comfyui-root", type=Path, required=True)
    run_parser.add_argument("--python", type=Path, required=True)
    run_parser.add_argument("--models-root", type=Path, required=True)
    run_parser.add_argument("--port", type=int, default=8188)
    run_parser.add_argument("--timeout", type=int, default=3600)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "prepare":
        print(
            prepare_job(
                args.workflow,
                args.job_dir,
                args.input,
                args.model,
                extension_source=args.extension_source,
            )
        )
        return 0
    if args.command == "validate":
        validate_job(args.job_dir, args.models_root)
        print("render job valid")
        return 0
    if args.command == "run":
        print(
            run_job(
                args.job_dir,
                args.comfyui_root,
                args.python,
                args.models_root,
                args.port,
                args.timeout,
            )
        )
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
