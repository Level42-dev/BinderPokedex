"""Opt-in source-detail contract exercises real reference files and graphs."""
import copy
import hashlib
import json
from pathlib import Path
from dataclasses import replace

import pytest
import yaml
from PIL import Image

from scripts.poster_assets import create_comfyui_poster_workflow as workflow
from scripts.poster_assets import prepare_comfyui_poster as preparation
from scripts.poster_assets import provenance, run_comfyui_poster as runner
from scripts.poster_assets.generation_contract import validate_generation_reference_contract, validate_generation_output_contract
from scripts.tests.test_poster_fingerprints import _write_fixture

MODE = "spatial_source_detail_joint"


@pytest.fixture
def detailed(tmp_path, monkeypatch):
    repository, assets, output, scope_dir, bundle = _write_fixture(tmp_path)
    manifest = copy.deepcopy(bundle.manifest)
    generation = manifest["artwork"]["generation"]
    generation.update(mode="joint_scene", reference_mode=MODE, generation_megapixels=2.0, output_method="lanczos", output_dpi=300)
    for key in ("upscale_model", "upscale_model_sha256"):
        generation.pop(key)
    items = json.loads((scope_dir / "cutouts/manifest.json").read_text())["items"]
    manifest["artwork"]["source_details"] = {
        f"pokeapi:official-artwork:{item['pokemon_id']}": {
            "sha256": hashlib.sha256((scope_dir / "cutouts" / item["file"]).read_bytes()).hexdigest(),
            "traits": trait,
        }
        for item, trait in zip(items, ("A broad green bulb.", "An orange tail flame.", "A blue round shell."))
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


def test_real_reference_preparation_and_one_shot_graph(detailed):
    bundle, _ = detailed
    preparation.prepare("Example", 2.0, generation_mode="joint_scene", reference_mode=MODE)
    graph = workflow.build_workflow("Example", 123, 2.0, generation_mode="joint_scene", reference_mode=MODE)
    classes = [node["class_type"] for node in graph.values()]
    assert classes.count("LoadImage") == 4
    for name in ("EmptyFlux2LatentImage", "SamplerCustomAdvanced", "VAEDecode", "SaveImage"):
        assert classes.count(name) == 1
    assert not any(word in name for name in classes for word in ("Composite", "Mask", "Upscale"))
    latent = next(node["inputs"] for node in graph.values() if node["class_type"] == "EmptyFlux2LatentImage")
    assert (latent["width"], latent["height"]) == (1200, 1664)
    assert all(node["inputs"]["steps"] == 4 for node in graph.values() if node["class_type"] == "Flux2Scheduler")
    refs = [node["inputs"]["image"] for node in graph.values() if node["class_type"] == "LoadImage"]
    assert refs == ["joint_scene_cast_reference.png", "identity_reference_1.png", "identity_reference_2.png", "identity_reference_3.png"]
    assert all((bundle.work_dir / name).is_file() for name in refs)
    text = graph["4"]["inputs"]["text"]
    assert text.startswith("COUNT AND LAYOUT FIRST")
    for index, value in enumerate(bundle.manifest["artwork"]["source_details"].values(), 2):
        paragraph = next(p for p in text.split("\n\n") if value["traits"] in p)
        assert f"IMAGE {index}:" in paragraph
        assert text.count(value["traits"]) == 1
    assert "foreground overlaps" in text


def test_large_exact_source_is_padded_without_resampling(detailed):
    bundle, _ = detailed
    source_path = bundle.source_dir / "cutouts/pokemon_001.png"
    source = Image.new("RGBA", (534, 534), (40, 90, 140, 255))
    source.putpixel((0, 0), (11, 22, 33, 255))
    source.putpixel((533, 533), (201, 202, 203, 255))
    source.save(source_path)
    bundle.manifest["artwork"]["source_details"]["pokeapi:official-artwork:1"]["sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()

    preparation.prepare("Example", 2.0, generation_mode="joint_scene", reference_mode=MODE)
    with Image.open(bundle.work_dir / "identity_reference_1.png") as loaded:
        detail = loaded.convert("RGB")
        assert detail.size == (576, 576)
        assert detail.getpixel((0, 0)) == (226, 224, 211)
        assert detail.crop((21, 21, 555, 555)).tobytes() == source.convert("RGB").tobytes()
    with Image.open(bundle.work_dir / "identity_reference_2.png") as loaded:
        assert loaded.size == (512, 512)


@pytest.mark.parametrize("problem", ["missing", "extra", "empty", "hash", "source", "duplicate"])
def test_invalid_source_details_fail_before_preparation_or_graph(detailed, problem):
    bundle, _ = detailed
    details = bundle.manifest["artwork"]["source_details"]
    key = next(iter(details))
    if problem == "missing":
        details.pop(key)
    elif problem == "extra":
        details["pokeapi:official-artwork:999"] = details[key]
    elif problem == "empty":
        details[key]["traits"] = "  "
    elif problem == "hash":
        details[key]["sha256"] = "no"
    elif problem == "source":
        Image.new("RGBA", (18, 18), "red").save(bundle.source_dir / "cutouts/pokemon_001.png")
    else:
        path = bundle.source_dir / "cutouts/manifest.json"
        data = json.loads(path.read_text())
        data["items"].append(data["items"][0])
        path.write_text(json.dumps(data))
    for action in (preparation.prepare, workflow.build_workflow):
        args = ("Example", 2.0) if action == preparation.prepare else ("Example", 123, 2.0)
        with pytest.raises(ValueError):
            action(*args, generation_mode="joint_scene", reference_mode=MODE)


@pytest.mark.parametrize("field,value", [("steps", 5), ("generation_megapixels", 1.0), ("output_method", "model_upscale"), ("output_dpi", 150)])
def test_fixed_generation_and_print_contract(detailed, field, value):
    generation = dict(detailed[0].manifest["artwork"]["generation"], **{field: value})
    with pytest.raises(ValueError):
        validate_generation_reference_contract(generation)
        validate_generation_output_contract(generation)


def test_fingerprint_changes_with_traits_and_source_and_rebuilds(detailed):
    bundle, output = detailed
    original = copy.deepcopy(provenance.build_generation_fingerprint(bundle, scope_data_dir=output))
    assert original["components"]["pipeline_contract"]["version"] == 11
    assert provenance.rebuild_generation_fingerprint_from_recorded_sources(bundle, original, scope_data_dir=output) == original
    details = bundle.manifest["artwork"]["source_details"]
    details[next(iter(details))]["traits"] += " A pointed leaf."
    changed = provenance.build_generation_fingerprint(bundle, scope_data_dir=output)
    assert changed["sha256"] != original["sha256"]
    assert provenance.rebuild_generation_fingerprint_from_recorded_sources(bundle, original, scope_data_dir=output)["sha256"] != original["sha256"]
    path = bundle.source_dir / "cutouts/pokemon_001.png"
    Image.new("RGBA", (18, 18), "red").save(path)
    with pytest.raises(ValueError):
        provenance.build_generation_fingerprint(bundle, scope_data_dir=output)
    details[next(iter(details))]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert provenance.build_generation_fingerprint(bundle, scope_data_dir=output)["sha256"] != changed["sha256"]


def test_two_special_forms_keep_separate_exact_detail_roles(detailed):
    from scripts.poster_assets.poster_subject import PosterSubject
    bundle, _ = detailed
    path = bundle.source_dir / "cutouts/manifest.json"
    data = json.loads(path.read_text())
    data["items"] = data["items"][:2]
    details = {}
    for item, species, artwork, trait in zip(data["items"], (382, 383), (10077, 10078), ("Translucent blue fins.", "Bright yellow magma seams.")):
        subject = PosterSubject(species, artwork)
        item.update(pokemon_id=species, url=subject.image_url, poster_subject=subject.as_mapping())
        details[subject.subject_key] = {"sha256": hashlib.sha256((path.parent / item["file"]).read_bytes()).hexdigest(), "traits": trait}
    path.write_text(json.dumps(data))
    bundle.manifest["artwork"]["source_details"] = details
    bundle.manifest["layout"]["name"] = "standard_2x2"
    preparation.prepare("Example", 2.0, generation_mode="joint_scene", reference_mode=MODE)
    graph = workflow.build_workflow("Example", 123, 2.0, generation_mode="joint_scene", reference_mode=MODE)
    assert sum(node["class_type"] == "LoadImage" for node in graph.values()) == 3
    text = graph["4"]["inputs"]["text"]
    assert "exactly 2 Pokemon" in text
    for index, key in enumerate(details, 2):
        paragraph = next(p for p in text.split("\n\n") if details[key]["traits"] in p)
        assert f"IMAGE {index}:" in paragraph and key in paragraph


def test_input_records_reject_noncanonical_graph_and_snapshot(detailed):
    bundle, _ = detailed
    preparation.prepare("Example", 2.0, generation_mode="joint_scene", reference_mode=MODE)
    path = workflow.write_workflow("Example", 123, 2.0, generation_mode="joint_scene", reference_mode=MODE, unet_name="model.safetensors", clip_name="encoder.safetensors", vae_name="vae.safetensors")
    generation = bundle.manifest["artwork"]["generation"]
    records = provenance.generation_input_records("Example", path, generation)
    assert len(records["references"]) == 4
    graph = json.loads(path.read_text())
    graph["4"]["inputs"]["text"] += " Experimental override."
    path.write_text(json.dumps(graph))
    with pytest.raises(ValueError, match="workflow"):
        provenance.generation_input_records("Example", path, generation)


def test_duplicate_source_detail_yaml_keys_fail_closed(tmp_path):
    from scripts.poster_assets.poster_io import load_yaml
    path = tmp_path / "poster.yaml"
    path.write_text("artwork:\n  source_details:\n    pokeapi:official-artwork:1: {sha256: a, traits: First}\n    pokeapi:official-artwork:1: {sha256: b, traits: Second}\n")
    with pytest.raises(ValueError, match="Duplicate source_details"):
        load_yaml(path)


def test_runner_rejects_wrong_print_target_before_server_access(detailed, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("invalid source-detail settings reached preparation/server access")
    monkeypatch.setattr(runner, "prepare", unexpected)
    with pytest.raises(ValueError, match="300 dpi"):
        runner.run("Example", 123, 2.0, "http://unused", 1, "en", flux_mode="joint_scene", flux_reference_mode=MODE, output_dpi=150)


def test_stale_snapshot_is_rejected(detailed):
    bundle, _ = detailed
    preparation.prepare("Example", 2.0, generation_mode="joint_scene", reference_mode=MODE)
    path = workflow.write_workflow("Example", 123, 2.0, generation_mode="joint_scene", reference_mode=MODE, unet_name="model.safetensors", clip_name="encoder.safetensors", vae_name="vae.safetensors")
    generation = bundle.manifest["artwork"]["generation"]
    provenance.prompt_path_for_generation(bundle.work_dir, generation, path).write_text("stale")
    with pytest.raises(ValueError, match="snapshot"):
        provenance.generation_input_records("Example", path, generation)


@pytest.mark.parametrize("field,value", [("steps", 8), ("output_method", "model_upscale"), ("output_dpi", 150)])
def test_prepare_rejects_incompatible_configured_contract(detailed, field, value):
    bundle, _ = detailed
    bundle.manifest["artwork"]["generation"][field] = value
    with pytest.raises(ValueError):
        preparation.prepare("Example", 2.0, generation_mode="joint_scene", reference_mode=MODE)


def test_graph_rejects_incompatible_output_contract(detailed):
    detailed[0].manifest["artwork"]["generation"]["output_method"] = "model_upscale"
    with pytest.raises(ValueError, match="Lanczos"):
        workflow.build_workflow("Example", 123, 2.0, generation_mode="joint_scene", reference_mode=MODE)


def _pilot_a():
    return json.loads((Path(__file__).parent / "fixtures/source_detail_v10_pilot_a.json").read_text())


def _pilot_prompt_inputs():
    components = _pilot_a()["fingerprint"]["components"]
    manifest = {"layout": {"name": "standard_3x3"}, "artwork": {"scene": components["scene"], "source_details": components["source_details"]}}
    items = [{"pokemon_id": number, "name_en": name} for number, name in [(1, "Bulbasaur"), (7, "Squirtle"), (813, "Scorbunny")]]
    placements = [dict(left_per_mille=l, right_per_mille=r, top_per_mille=t, bottom_per_mille=936) for l,r,t in [(35,281,770),(381,618,758),(780,902,758)]]
    return manifest, items, placements


def test_v10_pilot_prompt_is_byte_exact_and_v11_changes_only_leading_roles():
    from scripts.poster_assets.source_detail import build_source_detail_prompt, format_prompt_snapshot
    manifest, items, placements = _pilot_prompt_inputs()
    old = build_source_detail_prompt(manifest, items, placement_contract=placements, pipeline_contract_version=10)
    assert format_prompt_snapshot(old, pipeline_contract_version=10) + "\n" == _pilot_a()["prompt_snapshot"]
    new = build_source_detail_prompt(manifest, items, placement_contract=placements)
    assert new.split("\n\n")[2:] == old.split("\n\n")[2:]
    assert "ONE Bulbasaur at bottom-left" in new
    assert "ONE Squirtle at bottom-center" in new
    assert "ONE Scorbunny at bottom-right" in new
    assert "TOTAL: 3 Pokemon" in new
    assert "same single bottom row" in new
    assert "upper 75.8%" in new and "absolutely no Pokemon pixels" in new
    assert "y75.8% to y93.6%" in new
    assert "Bulbasaur: 16.6%" in new and "Scorbunny: 17.8%" in new
    assert "large scale MUST NOT be transferred" in new
    assert format_prompt_snapshot(new).startswith("SOURCE DETAIL JOINT SCENE - VERSION 11")


def test_v11_inventory_uses_actual_columns_for_two_subjects():
    from scripts.poster_assets.source_detail import build_source_detail_prompt
    manifest, items, placements = _pilot_prompt_inputs()
    items = items[:2]
    placements = [placements[0], placements[2]]
    manifest["artwork"]["source_details"].pop("pokeapi:official-artwork:813")
    manifest["layout"]["name"] = "wide_4x3"
    text = build_source_detail_prompt(manifest, items, placement_contract=placements)
    assert "ONE Bulbasaur at bottom-left" in text
    assert "ONE Squirtle at bottom-right" in text
    assert "TOTAL: 2 Pokemon" in text
    assert "bottom-center" not in text


def test_v11_rejects_unknown_version_and_accepts_historical_v10(detailed):
    generation = detailed[0].manifest["artwork"]["generation"]
    provenance.validate_generation_pipeline_contract_version(generation, 10)
    provenance.validate_generation_pipeline_contract_version(generation, 11)
    assert provenance.current_generation_pipeline_contract_version(generation) == 11
    with pytest.raises(ValueError):
        provenance.validate_generation_pipeline_contract_version(generation, 12)


def test_actual_v10_pilot_fingerprint_rebuild_remains_byte_exact(detailed):
    bundle, output = detailed
    recorded = _pilot_a()["fingerprint"]
    assert provenance.fingerprint_record_is_valid(recorded)
    components = recorded["components"]
    manifest = copy.deepcopy(bundle.manifest)
    manifest["pokemon"] = components["pokemon"]
    manifest["artwork"].update({key: components[key] for key in ("scene", "generation", "source_details")})
    bundle = replace(bundle, manifest=manifest)
    path = output / "Example.json"
    data = json.loads(path.read_text())
    data["sections"]["main"]["featured_elements"] = [{"pokemon_id": n} for n in (1, 7, 813)]
    path.write_text(json.dumps(data))
    rebuilt = provenance.rebuild_generation_fingerprint_from_recorded_sources(bundle, recorded, scope_data_dir=output)
    assert rebuilt == recorded
    from scripts.poster_assets.source_detail import build_source_detail_prompt, format_prompt_snapshot
    prompt_manifest, items, placements = _pilot_prompt_inputs()
    prompt = build_source_detail_prompt(prompt_manifest, items, placement_contract=placements, pipeline_contract_version=10)
    snapshot = format_prompt_snapshot(prompt, pipeline_contract_version=10)
    assert hashlib.sha256(snapshot.encode()).hexdigest() == recorded["components"]["effective_prompt"]["sha256"]


def test_current_workflow_and_snapshot_use_v11(detailed):
    bundle, _ = detailed
    preparation.prepare("Example", 2.0, generation_mode="joint_scene", reference_mode=MODE)
    path = workflow.write_workflow("Example", 123, 2.0, generation_mode="joint_scene", reference_mode=MODE, unet_name="model.safetensors", clip_name="encoder.safetensors", vae_name="vae.safetensors")
    generation = bundle.manifest["artwork"]["generation"]
    snapshot = provenance.prompt_path_for_generation(bundle.work_dir, generation, path).read_text()
    assert snapshot.startswith("SOURCE DETAIL JOINT SCENE - VERSION 11")
    assert "EXACT SCENE INVENTORY" in json.loads(path.read_text())["4"]["inputs"]["text"]
    assert provenance.generation_input_records("Example", path, generation)["prompt"]["sha256"] == hashlib.sha256(snapshot.encode()).hexdigest()


def test_fresh_historical_fingerprint_uses_v10_prompt(detailed):
    bundle, output = detailed
    old = provenance.build_generation_fingerprint(bundle, scope_data_dir=output, pipeline_contract_version=10)
    new = provenance.build_generation_fingerprint(bundle, scope_data_dir=output)
    assert old["components"]["pipeline_contract"]["version"] == 10
    assert new["components"]["pipeline_contract"]["version"] == 11
    assert old["components"]["effective_prompt"] != new["components"]["effective_prompt"]
    assert {k: v for k, v in old["components"].items() if k not in {"effective_prompt", "pipeline_contract"}} == {k: v for k, v in new["components"].items() if k not in {"effective_prompt", "pipeline_contract"}}


def test_gen2_one_shot_prompt_binds_starter_anatomy_to_exact_references():
    from scripts.poster_assets.poster_io import load_yaml
    from scripts.poster_assets.source_detail import build_source_detail_prompt

    manifest = load_yaml(Path("config/posters/Pokedex/sections/gen2/poster.yaml"))
    generation = manifest["artwork"]["generation"]
    assert generation["reference_mode"] == MODE
    assert generation["generation_megapixels"] == 2.0
    items = [
        {"pokemon_id": 152, "name_en": "Chikorita"},
        {"pokemon_id": 155, "name_en": "Cyndaquil"},
        {"pokemon_id": 158, "name_en": "Totodile"},
    ]
    placements = [
        {"left_per_mille": 50, "right_per_mille": 290, "top_per_mille": 750, "bottom_per_mille": 940},
        {"left_per_mille": 380, "right_per_mille": 620, "top_per_mille": 750, "bottom_per_mille": 940},
        {"left_per_mille": 710, "right_per_mille": 950, "top_per_mille": 750, "bottom_per_mille": 940},
    ]
    prompt = build_source_detail_prompt(manifest, items, placement_contract=placements)
    assert "IMAGE 2: exact individual detail reference for Chikorita (pokeapi:official-artwork:152)." in prompt
    assert "leaf stem separate from the green collar buds" in prompt
    assert "three round front collar buds" in prompt
    assert "IMAGE 3: exact individual detail reference for Cyndaquil (pokeapi:official-artwork:155)." in prompt
    assert "IMAGE 4: exact individual detail reference for Totodile (pokeapi:official-artwork:158)." in prompt
    assert "one broad planted foot with three rounded toe lobes" in prompt
