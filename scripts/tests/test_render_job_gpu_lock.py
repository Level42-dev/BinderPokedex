from concurrent.futures import ThreadPoolExecutor
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import pytest

from scripts.poster_assets import render_job


def test_render_job_does_not_launch_while_another_client_holds_gpu(tmp_path, monkeypatch):
    lock = tmp_path / "gpu.lock"
    monkeypatch.setenv("COMFYUI_GPU_LOCK", str(lock))
    job = tmp_path / "job"
    workflow = tmp_path / "workflow.json"
    workflow.write_text(json.dumps({"1": {"class_type": "SaveImage", "inputs": {}}}))
    render_job.prepare_job(workflow, job, [], [])
    comfy = tmp_path / "comfy"
    (comfy / "models").mkdir(parents=True)
    monkeypatch.setattr(render_job, "comfyui_commit", lambda *_: render_job.COMFYUI_COMMIT)
    launched = threading.Event()
    def process_start(*args, **kwargs):
        launched.set()
        raise RuntimeError("intercepted_process_start")
    monkeypatch.setattr(render_job.subprocess, "Popen", process_start)
    with lock.open("w") as held, ThreadPoolExecutor(max_workers=1) as pool:
        fcntl.flock(held, fcntl.LOCK_EX)
        future = pool.submit(render_job.run_job, job, comfy, Path(sys.executable), comfy / "models", 8188, 10)
        try:
            assert not launched.wait(0.25), "Binder launched a render while another client owns the GPU"
        finally:
            fcntl.flock(held, fcntl.LOCK_UN)
        with pytest.raises(RuntimeError, match="intercepted_process_start"):
            future.result(timeout=3)
    assert launched.is_set()


def test_binder_render_child_keeps_gpu_lock_if_runner_dies(tmp_path):
    lock = tmp_path / "gpu.lock"
    ready = tmp_path / "ready"
    comfy = tmp_path / "comfy"
    (comfy / "models").mkdir(parents=True)
    (comfy / "main.py").write_text("import os,pathlib,time\npathlib.Path(" + repr(str(ready)) + ").write_text(str(os.getpid()))\ntime.sleep(30)\n")
    job = tmp_path / "job"
    workflow = tmp_path / "workflow.json"
    workflow.write_text(json.dumps({"1": {"class_type": "SaveImage", "inputs": {}}}))
    render_job.prepare_job(workflow, job, [], [])
    code = "from scripts.poster_assets import render_job as r;from pathlib import Path;import sys,time\nr.comfyui_commit=lambda *_:r.COMFYUI_COMMIT;r.wait_for_server=lambda *_:time.sleep(30)\nr.run_job(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.executable),Path(sys.argv[2])/'models',8188,60)"
    runner = subprocess.Popen([sys.executable, "-c", code, str(job), str(comfy)], env={**os.environ, "COMFYUI_GPU_LOCK": str(lock)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    child_pid = None
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert ready.exists(), "fixture render did not start"
        child_pid = int(ready.read_text())
        runner.kill()
        runner.wait(timeout=3)
        with lock.open("rb") as probe:
            with pytest.raises(BlockingIOError):
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        if runner.poll() is None:
            runner.kill()
            runner.wait()
        if child_pid:
            try:
                os.kill(child_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
