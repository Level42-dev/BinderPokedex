"""A P16 pilot can be reviewed only from exact returned and print artifacts."""
from __future__ import annotations

import hashlib
import json
from contextlib import nullcontext

from PIL import Image
import pytest
import yaml

from scripts.poster_assets.region_joint.review_p16_trial import (
    audit_p16_trial,
    verify_print_crops,
    verify_print_raster,
    verify_pinned_models,
)
from scripts.poster_assets.region_joint.comfy_extension.guider import P16_CONTRACT_SHA256
from scripts.poster_assets.render_job import COMFYUI_COMMIT
from scripts.poster_assets.region_joint import review_p16_trial as review_module


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _trial_with_records(tmp_path):
    job = tmp_path / "tmp/oneshot-trials/p16-region-20260923-a/job"
    job.mkdir(parents=True)
    (job / "run.json").write_text("{}", encoding="utf-8")
    (job / "comfyui.log").write_text("Device: mps\n", encoding="utf-8")
    master = tmp_path / "assets/posters/ExGen2/sections/primal/poster-flux2-artwork.png"
    master_records = []
    for scope in ("ExGen2/sections/primal", "ME03"):
        for name in ("poster-flux2-artwork.png", "poster-flux2-provenance.json"):
            path = tmp_path / "assets/posters" / scope / name
            path.parent.mkdir(parents=True, exist_ok=True)
            content = f"{scope}/{name}".encode()
            path.write_bytes(content)
            master_records.append({"path": path.relative_to(tmp_path).as_posix(), "sha256": _sha(content)})
    source = tmp_path / "tmp/poster-workspaces/P16/sources/cutouts/source.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"source cutout")
    provenance = {
        "variant": "p16-region-20260923-a",
        "scope": "ExGen2/sections/primal",
        "region_contract_sha256": P16_CONTRACT_SHA256,
        "production_masters_before": master_records,
        "source_cutouts": [
            {"subject_id": subject, "path": source.relative_to(tmp_path).as_posix(), "sha256": _sha(b"source cutout")}
            for subject in ("pokeapi:official-artwork:10077", "pokeapi:official-artwork:10078")
        ],
    }
    (job.parent / "trial_provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    return job, master, source


def test_review_requires_all_nine_exact_cards(tmp_path):
    cards = tmp_path / "cards"
    cards.mkdir()
    for row in range(1, 4):
        for col in range(1, 4):
            Image.new("RGB", (750, 1050)).save(cards / f"card_r{row}_c{col}.png", dpi=(300, 300))
    (cards / "card_r3_c2.png").unlink()
    with pytest.raises(FileNotFoundError, match="card_r3_c2"):
        verify_print_crops(cards)


def test_review_rejects_wrong_card_raster(tmp_path):
    cards = tmp_path / "cards"
    cards.mkdir()
    for row in range(1, 4):
        for col in range(1, 4):
            size = (749, 1050) if (row, col) == (3, 2) else (750, 1050)
            Image.new("RGB", size).save(cards / f"card_r{row}_c{col}.png", dpi=(300, 300))
    with pytest.raises(ValueError, match="card_r3_c2"):
        verify_print_crops(cards)


def test_review_rejects_non_300dpi_poster(tmp_path):
    poster = tmp_path / "poster.png"
    Image.new("RGB", (2368, 3268)).save(poster, dpi=(72, 72))
    with pytest.raises(ValueError, match="300 dpi"):
        verify_print_raster(poster)


def test_review_requires_run_and_log_before_output(tmp_path):
    job = tmp_path / "tmp/oneshot-trials/p16-region-20260923-a/job"
    job.mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="run.json"):
        audit_p16_trial(job, tmp_path)
    (job / "run.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="comfyui.log"):
        audit_p16_trial(job, tmp_path)


def test_review_rejects_symlink_output_directory_without_touching_target(tmp_path):
    job = tmp_path / "tmp/oneshot-trials/p16-region-20260923-a/job"
    job.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    marker = elsewhere / "card_r1_c1.png"
    marker.write_bytes(b"untouched")
    (job / "review").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(FileExistsError, match="review directory already exists"):
        audit_p16_trial(job, tmp_path)
    assert marker.read_bytes() == b"untouched"


def test_review_rejects_symlinked_raw_output_base(tmp_path):
    job, _master, _source = _trial_with_records(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    raw = elsewhere / "poster.png"
    Image.new("RGB", (1200, 1664)).save(raw)
    (job / "output").symlink_to(elsewhere, target_is_directory=True)
    (job / "run.json").write_text(json.dumps({
        "outputs": [{"path": "poster.png", "sha256": _sha(raw.read_bytes())}],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="base escapes pilot job"):
        audit_p16_trial(job, tmp_path)
    assert not (job / "review").exists()


def test_review_rejects_changed_production_master(tmp_path):
    job, master, _source = _trial_with_records(tmp_path)
    master.write_bytes(b"changed production master")
    with pytest.raises(ValueError, match="production master"):
        audit_p16_trial(job, tmp_path)
    assert not (job / "review").exists()


def test_review_rejects_missing_p37_master_record(tmp_path):
    job, _master, _source = _trial_with_records(tmp_path)
    provenance_path = job.parent / "trial_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["production_masters_before"] = provenance["production_masters_before"][:-1]
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    with pytest.raises(ValueError, match="production master inventory"):
        audit_p16_trial(job, tmp_path)
    assert not (job / "review").exists()


def test_review_rejects_changed_source_cutout(tmp_path):
    job, _master, source = _trial_with_records(tmp_path)
    source.write_bytes(b"changed source cutout")
    with pytest.raises(ValueError, match="source cutout"):
        audit_p16_trial(job, tmp_path)
    assert not (job / "review").exists()


@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_review_rejects_incomplete_source_inventory_before_writing(tmp_path, mutation):
    job, _master, _source = _trial_with_records(tmp_path)
    provenance_path = job.parent / "trial_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if mutation == "missing":
        provenance["source_cutouts"].pop()
    else:
        provenance["source_cutouts"][1]["subject_id"] = provenance["source_cutouts"][0]["subject_id"]
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    with pytest.raises(ValueError, match="source cutout inventory"):
        audit_p16_trial(job, tmp_path)
    assert not (job / "review").exists()


def test_review_rejects_missing_output_without_creating_review(tmp_path):
    job, _master, _source = _trial_with_records(tmp_path)
    with pytest.raises(ValueError, match="one final ComfyUI image"):
        audit_p16_trial(job, tmp_path)
    assert not (job / "review").exists()


def test_review_rejects_wrong_raw_canvas_before_print_resize(tmp_path):
    job, _master, _source = _trial_with_records(tmp_path)
    raw = job / "output/poster.png"
    raw.parent.mkdir()
    Image.new("RGB", (1024, 1024)).save(raw)
    (job / "run.json").write_text(json.dumps({
        "outputs": [{"path": "poster.png", "sha256": _sha(raw.read_bytes())}],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="generation dimensions"):
        audit_p16_trial(job, tmp_path)
    assert not (job / "review").exists()


def test_review_requires_all_three_pinned_model_records():
    generation = {
        "model": "flux-2-klein-4b.safetensors", "model_sha256": "a" * 64,
        "encoder": "qwen_3_4b.safetensors", "encoder_sha256": "b" * 64,
        "vae": "flux2-vae.safetensors", "vae_sha256": "c" * 64,
    }
    records = [
        {"path": f"{folder}/{generation[name]}", "sha256": generation[sha]}
        for folder, name, sha in review_module.MODEL_NAMES
    ]
    verify_pinned_models(records, generation)
    with pytest.raises(ValueError, match="pinned model inventory"):
        verify_pinned_models(records[:-1], generation)
    records[1]["sha256"] = "d" * 64
    with pytest.raises(ValueError, match="pinned model inventory"):
        verify_pinned_models(records, generation)
    changed_generation = {**generation, "model": "flux-2-klein-9b.safetensors"}
    with pytest.raises(ValueError, match="pinned model names"):
        verify_pinned_models(records, changed_generation)


def test_review_binds_successful_return_to_nine_cards_and_two_source_pairs(tmp_path, monkeypatch):
    job, _master, source = _trial_with_records(tmp_path)
    Image.new("RGBA", (80, 100), "red").save(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    provenance_path = job.parent / "trial_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["source_cutouts"] = [
        {"subject_id": subject, "path": source.relative_to(tmp_path).as_posix(), "sha256": source_hash}
        for subject in ("pokeapi:official-artwork:10077", "pokeapi:official-artwork:10078")
    ]
    workflow_bytes = b"{}"
    (job / "workflow_api.json").write_bytes(workflow_bytes)
    inputs = []
    for name in sorted(review_module.EXPECTED_INPUTS):
        path = job / "input" / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"reference")
        inputs.append({"path": name, "sha256": _sha(b"reference")})
    extension = job / "extensions/binder_region_joint/__init__.py"
    extension.parent.mkdir(parents=True)
    extension.write_bytes(b"NODE_CLASS_MAPPINGS = {}\n")
    extension_files = [{"path": "__init__.py", "sha256": _sha(extension.read_bytes())}]
    generation = {
        "model": "flux-2-klein-4b.safetensors", "model_sha256": "a" * 64,
        "encoder": "qwen_3_4b.safetensors", "encoder_sha256": "b" * 64,
        "vae": "flux2-vae.safetensors", "vae_sha256": "c" * 64,
    }
    models = [
        {"path": f"{folder}/{generation[name]}", "sha256": generation[sha]}
        for folder, name, sha in review_module.MODEL_NAMES
    ]
    job_record = {
        "format_version": 2,
        "comfyui_commit": COMFYUI_COMMIT,
        "workflow": {"path": "workflow_api.json", "sha256": _sha(workflow_bytes)},
        "inputs": inputs,
        "models": models,
        "extensions": {"name": "binder_region_joint", "files": extension_files},
    }
    (job / "job.json").write_text(json.dumps(job_record), encoding="utf-8")
    manifest = tmp_path / "tmp/review-batch-manifests/p16-region-20260923-a/poster.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(yaml.safe_dump({
        "asset_key": "ExGen2/sections/primal", "artwork": {"generation": generation},
    }), encoding="utf-8")
    provenance.update({
        "workflow_sha256": job_record["workflow"]["sha256"],
        "input_references": inputs,
        "models": models,
        "extension_files": extension_files,
        "manifest_path": manifest.relative_to(tmp_path).as_posix(),
        "manifest_sha256": _sha(manifest.read_bytes()),
    })
    provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
    raw = job / "output/poster.png"
    raw.parent.mkdir()
    Image.new("RGB", (1200, 1664), "blue").save(raw)
    run = {
        "format_version": 2,
        "comfyui_commit": COMFYUI_COMMIT,
        "device": "mps",
        "workflow_sha256": job_record["workflow"]["sha256"],
        "inputs": inputs,
        "models": models,
        "outputs": [{"path": "poster.png", "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}],
    }
    (job / "run.json").write_text(json.dumps(run), encoding="utf-8")
    monkeypatch.setattr(review_module, "trial_manifest_bundle", lambda *args, **kwargs: nullcontext())

    def fake_raster(_scope, _input, destination, *args):
        destination.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (2368, 3268), "blue").save(destination, dpi=(300, 300))
        return destination

    def fake_cards(_scope, _poster, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        for row in range(1, 4):
            for col in range(1, 4):
                Image.new("RGB", (750, 1050), "blue").save(
                    output_dir / f"card_r{row}_c{col}.png", dpi=(300, 300),
                )

    monkeypatch.setattr(review_module, "resize_artwork_to_dpi", fake_raster)
    monkeypatch.setattr(review_module, "finalize", fake_raster)
    monkeypatch.setattr(review_module, "slice_poster", fake_cards)
    evidence = audit_p16_trial(job, tmp_path)
    assert evidence["status"] == "technical_pass_visual_pending"
    assert len(evidence["cards"]) == 9
    assert len(evidence["comparisons"]) == 2
    assert (job / "review/evidence.json").is_file()
    assert "hostname" not in (job / "review/evidence.json").read_text(encoding="utf-8")
