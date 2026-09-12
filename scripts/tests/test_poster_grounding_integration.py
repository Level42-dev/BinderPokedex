"""Grounded identity graph, immutable inputs, and approval boundary tests."""
import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from PIL import Image, PngImagePlugin

from scripts.poster_assets import create_comfyui_poster_workflow as workflow
from scripts.poster_assets import prepare_comfyui_poster as preparation
from scripts.poster_assets import provenance, run_comfyui_poster as runner
from scripts.poster_assets.generation_contract import requires_generation_fingerprint
from scripts.tests.test_poster_fingerprints import _write_fixture


@pytest.fixture
def grounded(tmp_path, monkeypatch):
    repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    manifest = copy.deepcopy(bundle.manifest)
    manifest["artwork"]["generation"]["reference_mode"] = "grounded_source_pixels"
    manifest["artwork"]["generation"]["generation_megapixels"] = 0.05
    manifest["artwork"]["identity_lock"]["grounding"] = {
        "schema_version": 1, "prompt": "Paint subtle contact shadows on the ground.",
        "feather_ratio": 0.0,
        "regions": [
            {"subject_key": f"pokeapi:official-artwork:{number}", "contact": "grounded",
             "polygon": [[x, .91], [x + .12, .91], [x + .12, .98], [x, .98]],
             "anchors": [[x + .06, .96]]}
            for number, x in [(1, .1), (4, .43), (7, .76)]
        ],
    }
    bundle.manifest_path.write_text(yaml.safe_dump(manifest))
    bundle = replace(bundle, manifest=manifest)
    for module in (workflow, preparation, provenance, runner):
        monkeypatch.setattr(module, "poster_bundle", lambda *a, **kw: bundle)
    monkeypatch.setattr(provenance, "ROOT", repository)
    monkeypatch.setattr(provenance, "SCOPE_DATA", output)
    for module in (workflow, preparation):
        monkeypatch.setattr(module, "load_poster_scope_data", lambda b: json.loads((output / "Example.json").read_text()))
    return bundle, output


def test_grounded_graph_restores_baseline_with_separate_prompt_and_masks(grounded):
    bundle, _ = grounded
    graph = workflow.build_workflow("Example", 123, .05, generation_mode="identity_lock", reference_mode="grounded_source_pixels")
    classes = [n["class_type"] for n in graph.values()]
    assert "VAEEncodeForInpaint" not in classes
    assert graph["21"]["class_type"] == "VAEEncode"
    assert graph["21"]["inputs"]["pixels"] == ["19", 0]
    assert graph["25"]["inputs"]["destination"] == ["19", 0]
    assert graph["25"]["inputs"]["mask"] == ["20", 1]
    assert graph["20"]["inputs"]["image"] == "grounding_mask.png"
    assert graph["28"]["inputs"]["image"] == "grounding_sampling_mask.png"
    noise_mask = next(n for n in graph.values() if n["class_type"] == "SetLatentNoiseMask")
    assert noise_mask["inputs"] == {"samples": ["21", 0], "mask": ["28", 1]}
    reference = next(n for n in graph.values() if n["class_type"] == "ReferenceLatent")
    assert reference["inputs"]["latent"] == ["21", 0]
    texts = [n["inputs"]["text"] for n in graph.values() if n["class_type"] == "CLIPTextEncode"]
    assert bundle.manifest["artwork"]["identity_lock"]["grounding"]["prompt"] in texts
    saves = [n for n in graph.values() if n["class_type"] == "SaveImage"]
    assert len(saves) == 2
    assert {n["inputs"]["images"][0] for n in saves} == {"19", "25"}
    assert all(n["inputs"]["steps"] == 4 for n in graph.values() if n["class_type"] == "Flux2Scheduler")


def test_grounded_fingerprint_tracks_consumed_settings_and_rebuilds(grounded):
    bundle, output = grounded
    generation = bundle.manifest["artwork"]["generation"]
    assert requires_generation_fingerprint(generation)
    original = provenance.build_generation_fingerprint(bundle, scope_data_dir=output)
    assert original["components"]["pipeline_contract"]["version"] == 4
    rebuilt = provenance.rebuild_generation_fingerprint_from_recorded_sources(bundle, original, scope_data_dir=output)
    assert rebuilt == original
    for field in ("prompt", "anchors", "overscan_ratio"):
        manifest = copy.deepcopy(bundle.manifest)
        config = manifest["artwork"]["identity_lock"]
        if field == "prompt":
            config["grounding"][field] += " Keep warm light."
        elif field == "anchors":
            config["grounding"]["regions"][0][field] = [[.17, .96]]
        else:
            config[field] = .08
        assert provenance.build_generation_fingerprint(replace(bundle, manifest=manifest), scope_data_dir=output)["sha256"] != original["sha256"]
    manifest = copy.deepcopy(bundle.manifest)
    manifest["artwork"]["identity_lock"]["transition_ratio"] = .03
    assert provenance.build_generation_fingerprint(replace(bundle, manifest=manifest), scope_data_dir=output) == original


def _prepare(grounded):
    bundle, _ = grounded
    preparation.build_identity_lock_references("Example", .05, reference_mode="grounded_source_pixels")
    path = workflow.write_workflow("Example", 123, .05, generation_mode="identity_lock", reference_mode="grounded_source_pixels", unet_name="model.safetensors", clip_name="encoder.safetensors", vae_name="vae.safetensors")
    return bundle, path


def test_grounded_inputs_exclude_upper_masks_and_reject_stale_metadata(grounded):
    bundle, path = _prepare(grounded)
    generation = bundle.manifest["artwork"]["generation"]
    inputs = provenance.generation_input_records("Example", path, generation)
    assert {Path(r["file"]).name for r in inputs["references"]} == {"inpaint_reference.png", "grounding_mask.png", "grounding_sampling_mask.png"}
    assert not (bundle.work_dir / "upper_context_mask.png").exists()
    mask_metadata = bundle.work_dir / "grounding_mask.json"
    metadata = json.loads(mask_metadata.read_text())
    metadata["counts"]["source_visible_pixels"] += 1
    mask_metadata.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="[Gg]rounding"):
        provenance.generation_input_records("Example", path, generation)


def _outputs(grounded):
    bundle, path = _prepare(grounded)
    graph = json.loads(path.read_text())
    reference = Image.open(bundle.work_dir / "inpaint_reference.png").convert("RGBA")
    baseline = Image.new("RGBA", reference.size, (90, 120, 80, 255))
    baseline.alpha_composite(reference)
    final = baseline.copy()
    mask = Image.open(bundle.work_dir / "grounding_mask.png").getchannel("A")
    edit = next((x, y) for y in range(mask.height) for x in range(mask.width) if mask.getpixel((x, y)) < 255)
    final.putpixel(edit, (40, 70, 40, 255))
    outputs = []
    for node in graph.values():
        if node["class_type"] != "SaveImage":
            continue
        is_baseline = node["inputs"]["images"] == ["19", 0]
        filename = node["inputs"]["filename_prefix"] + "_00001_.png"
        destination = bundle.work_dir / "output" / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("prompt", json.dumps(graph))
        (baseline if is_baseline else final).save(destination, pnginfo=pnginfo)
        outputs.append({"type": "output", "filename": filename, "subfolder": ""})
    return bundle, path, list(reversed(outputs))


def test_grounded_output_roles_bind_baseline_to_this_graph(grounded):
    bundle, path, outputs = _outputs(grounded)
    roles = runner.select_generation_outputs(outputs, path, bundle.work_dir, bundle.manifest["artwork"]["generation"])
    assert set(roles) == {"final", "baseline"}
    assert "baseline" in roles["baseline"].name
    Image.new("RGB", (20, 20)).save(roles["baseline"])
    with pytest.raises(ValueError, match="[Ww]orkflow|[Jj]ob"):
        runner.select_generation_outputs(outputs, path, bundle.work_dir, bundle.manifest["artwork"]["generation"])


def test_grounded_pixel_evidence_is_bound_and_still_requires_visual_review(grounded):
    bundle, path, outputs = _outputs(grounded)
    generation = bundle.manifest["artwork"]["generation"]
    roles = runner.select_generation_outputs(outputs, path, bundle.work_dir, generation)
    run = provenance.audit_grounded_generation("Example", path, generation, roles["final"], roles["baseline"])
    provenance.require_grounding_pixel_validation(run)
    with pytest.raises(ValueError, match="visual identity approval"):
        provenance.require_joint_scene_visual_review(run)
    for section, field, value in [
        ("grounding", "changed_source_pixels", 1), ("grounding", "changed_outside_mask_pixels", 1),
        ("grounding", "changed_editable_pixels", 0), ("grounding", "baseline_sha256", "a" * 64),
        ("grounding", "mask_sha256", "a" * 64), ("grounding", "reference_sha256", "a" * 64),
        ("grounding", "artwork_sha256", "a" * 64), ("grounding", "source_visible_pixels", 1),
        ("source_pixels", "changed_pixels", 1),
    ]:
        damaged = copy.deepcopy(run)
        damaged["validation"][section][field] = value
        with pytest.raises(ValueError):
            provenance.require_grounding_pixel_validation(damaged)
    damaged = copy.deepcopy(run)
    del damaged["baseline_artwork"]
    with pytest.raises(ValueError):
        provenance.require_grounding_pixel_validation(damaged)


def test_grounded_rejects_another_graph_even_when_output_pngs_match_it(grounded):
    bundle, path, outputs = _outputs(grounded)
    graph = json.loads(path.read_text())
    graph["25"]["inputs"]["mask"] = ["28", 1]
    path.write_text(json.dumps(graph))
    with pytest.raises(ValueError, match="[Gg]rounding.*workflow"):
        provenance.generation_input_records("Example", path, bundle.manifest["artwork"]["generation"])


def test_grounded_visual_approval_binds_baseline_and_workflow(grounded):
    bundle, path, outputs = _outputs(grounded)
    generation = bundle.manifest["artwork"]["generation"]
    roles = runner.select_generation_outputs(outputs, path, bundle.work_dir, generation)
    run = provenance.audit_grounded_generation("Example", path, generation, roles["final"], roles["baseline"])
    provenance.approve_joint_scene_visual_review(run, artwork_path=roles["final"], raw_artwork_path=roles["final"], reviewer_kind="human")
    provenance.require_joint_scene_visual_review(run)
    for field in ("baseline_sha256", "workflow_sha256"):
        damaged = copy.deepcopy(run)
        damaged["validation"][provenance.JOINT_SCENE_REVIEW_KEY][field] = "f" * 64
        with pytest.raises(ValueError, match="[Gg]rounding"):
            provenance.require_joint_scene_visual_review(damaged)


def test_grounded_visual_approval_rechecks_the_actual_baseline(grounded):
    bundle, path, outputs = _outputs(grounded)
    generation = bundle.manifest["artwork"]["generation"]
    roles = runner.select_generation_outputs(outputs, path, bundle.work_dir, generation)
    run = provenance.audit_grounded_generation("Example", path, generation, roles["final"], roles["baseline"])
    Image.new("RGB", (20, 20)).save(roles["baseline"])
    with pytest.raises(ValueError, match="[Gg]rounding"):
        provenance.approve_joint_scene_visual_review(run, artwork_path=roles["final"], raw_artwork_path=roles["final"], reviewer_kind="human")


def test_grounded_sidecar_retains_unapproved_baseline_and_rechecks_files(grounded):
    bundle, path, outputs = _outputs(grounded)
    generation = bundle.manifest["artwork"]["generation"]
    roles = runner.select_generation_outputs(outputs, path, bundle.work_dir, generation)
    run = provenance.audit_grounded_generation("Example", path, generation, roles["final"], roles["baseline"])
    sidecar = provenance.write_run_metadata(
        "Example", roles["final"], path, generation,
        raw_artwork_path=roles["final"], baseline_artwork_path=roles["baseline"],
        validation=run["validation"],
    )
    loaded = provenance.load_run_metadata(sidecar, roles["final"])
    assert loaded["baseline_artwork"]["role"] == "baseline"
    assert provenance.JOINT_SCENE_REVIEW_KEY not in loaded["validation"]
    with pytest.raises(ValueError, match="visual identity approval"):
        provenance.require_joint_scene_visual_review(loaded)
    Image.new("RGB", (20, 20)).save(roles["baseline"])
    with pytest.raises(ValueError, match="[Gg]rounding"):
        provenance.load_run_metadata(sidecar, roles["final"])


@pytest.mark.parametrize("filename", ["grounding_sampling_mask.png", "grounding_mask.json"])
def test_grounded_rechecks_every_consumed_input_file(grounded, filename):
    bundle, path, outputs = _outputs(grounded)
    generation = bundle.manifest["artwork"]["generation"]
    roles = runner.select_generation_outputs(outputs, path, bundle.work_dir, generation)
    run = provenance.audit_grounded_generation("Example", path, generation, roles["final"], roles["baseline"])
    source = bundle.work_dir / filename
    if source.suffix == ".png":
        Image.new("RGBA", (20, 20)).save(source)
    else:
        source.write_text("{}")
    with pytest.raises(ValueError):
        provenance.require_grounding_pixel_validation(run, verify_files=True)


@pytest.mark.parametrize("corrupt", [False, True])
def test_runner_audits_grounded_outputs_before_upscale(grounded, monkeypatch, corrupt):
    bundle, path, outputs = _outputs(grounded)
    roles = runner.select_generation_outputs(outputs, path, bundle.work_dir, bundle.manifest["artwork"]["generation"])
    if corrupt:
        with Image.open(roles["final"]) as source:
            image = source.copy()
            metadata = PngImagePlugin.PngInfo()
            metadata.add_text("prompt", source.info["prompt"])
        image.putpixel((0, 0), (1, 2, 3, 255))
        image.save(roles["final"], pnginfo=metadata)
    comfy = bundle.work_dir / "fake-runtime"
    for directory, name in [("diffusion_models", "model.safetensors"), ("text_encoders", "encoder.safetensors"), ("vae", "vae.safetensors"), ("upscale_models", "upscale.pth")]:
        model = comfy / "models" / directory / name
        model.parent.mkdir(parents=True, exist_ok=True)
        model.write_bytes(b"test artifact")
    monkeypatch.setattr(runner, "prepare", lambda *a, **kw: bundle.work_dir)
    monkeypatch.setattr(runner, "validate_server_input_directory", lambda *a: None)
    monkeypatch.setattr(runner, "server_comfyui_root", lambda *a: comfy)
    monkeypatch.setattr(runner, "queue_workflow", lambda *a, **kw: outputs)
    upscaled = []

    def fake_upscale(scope, source, **kwargs):
        upscaled.append(source)
        return source, path

    monkeypatch.setattr(runner, "upscale", fake_upscale)
    monkeypatch.setattr(runner, "finalize", lambda *a: None)
    monkeypatch.setattr(runner, "slice_poster", lambda *a: None)
    args = dict(flux_mode="identity_lock", flux_reference_mode="grounded_source_pixels", flux_model="model.safetensors", flux_clip="encoder.safetensors", flux_vae="vae.safetensors", output_dpi=10, upscale_model="upscale.pth")
    if corrupt:
        with pytest.raises(ValueError, match="outside"):
            runner.run("Example", 123, .05, "http://unused.test", 1, "de", **args)
        assert upscaled == []
    else:
        raw, artwork, final, sidecar = runner.run("Example", 123, .05, "http://unused.test", 1, "de", **args)
        assert upscaled == [roles["final"]]
        loaded = provenance.load_run_metadata(sidecar, artwork)
        assert loaded["validation"]["grounding"]["passed"] is True
        assert loaded["generation"]["output_method"] == "model_upscale"
