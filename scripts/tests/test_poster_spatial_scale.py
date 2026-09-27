"""Per-subject size changes affect spatial guidance, never source identities."""
import json

import pytest
from PIL import Image, ImageChops

from scripts.poster_assets import create_comfyui_poster_workflow as workflow
from scripts.poster_assets import prepare_comfyui_poster as preparation
from scripts.poster_assets import provenance
from scripts.poster_assets.poster_io import load_yaml
from scripts.poster_assets.composition import joint_scene_canvas_placements
from scripts.poster_assets.source_detail import spatial_reference_scales
from scripts.poster_assets.poster_subject import PosterSubject
from scripts.tests.test_poster_source_detail import MODE, detailed

KEY = "pokeapi:official-artwork:4"


def _prepare():
    preparation.prepare("Example", 2.0, generation_mode="joint_scene", reference_mode=MODE)


def _graph():
    return workflow.build_workflow("Example", 123, 2.0, generation_mode="joint_scene", reference_mode=MODE)


def _orange_bounds(image):
    mask = image.convert("RGB")
    pixels = mask.load()
    points = [(x, y) for y in range(mask.height) for x in range(mask.width)
              if pixels[x, y] == (235, 120, 50)]
    return (min(x for x, _ in points), min(y for _, y in points),
            max(x for x, _ in points) + 1, max(y for _, y in points) + 1)


def test_only_selected_spatial_subject_shrinks_and_prompt_agrees(detailed):
    bundle, _ = detailed
    source_bytes = {p.name: p.read_bytes() for p in (bundle.source_dir / "cutouts").glob("*.png")}
    _prepare()
    before = Image.open(bundle.work_dir / "joint_scene_cast_reference.png").copy()
    identities = {p.name: p.read_bytes() for p in bundle.work_dir.glob("identity_reference_*.png")}
    old_graph = _graph()
    bundle.manifest["artwork"]["spatial_reference_scales"] = {KEY: 0.8}
    _prepare()
    after = Image.open(bundle.work_dir / "joint_scene_cast_reference.png").copy()
    old_box, new_box = _orange_bounds(before), _orange_bounds(after)
    assert new_box[2] - new_box[0] == round((old_box[2] - old_box[0]) * 0.8)
    assert new_box[3] - new_box[1] == round((old_box[3] - old_box[1]) * 0.8)
    assert new_box[3] == old_box[3]
    assert abs(new_box[0] + new_box[2] - old_box[0] - old_box[2]) <= 1
    diff = ImageChops.difference(before, after).getbbox()
    assert diff and old_box[0] <= diff[0] < diff[2] <= old_box[2]
    assert old_box[1] <= diff[1] < diff[3] <= old_box[3]
    assert identities == {p.name: p.read_bytes() for p in bundle.work_dir.glob("identity_reference_*.png")}
    assert source_bytes == {p.name: p.read_bytes() for p in (bundle.source_dir / "cutouts").glob("*.png")}
    graph = _graph()
    # Hand-derived full-canvas square: 319 -> 255 px, centered at x600,
    # bottom baseline 1557 on a 1200 x 1664 raster (integer centering).
    assert f"{KEY}: x 39.3–60.6%, y 78.2–93.6%" in graph["4"]["inputs"]["text"]
    old_paragraphs = old_graph["4"]["inputs"]["text"].split("\n\n")
    assert graph["4"]["inputs"]["text"].split("\n\n")[2:] == old_paragraphs[2:]
    graph["4"]["inputs"]["text"] = old_graph["4"]["inputs"]["text"]
    assert graph == old_graph


def test_empty_override_is_byte_compatible_and_fingerprint_binds_scale(detailed):
    bundle, output = detailed
    _prepare()
    references = {p.name: p.read_bytes() for p in bundle.work_dir.glob("*.png")}
    graph = _graph()
    original = provenance.build_generation_fingerprint(bundle, scope_data_dir=output)
    bundle.manifest["artwork"]["spatial_reference_scales"] = {}
    _prepare()
    assert graph == _graph()
    assert references == {p.name: p.read_bytes() for p in bundle.work_dir.glob("*.png")}
    assert original == provenance.build_generation_fingerprint(bundle, scope_data_dir=output)
    bundle.manifest["artwork"]["spatial_reference_scales"] = {KEY: 0.8}
    scaled = provenance.build_generation_fingerprint(bundle, scope_data_dir=output)
    assert scaled["sha256"] != original["sha256"]
    assert scaled["components"]["spatial_reference"] == {"version": 1, "subject_scales": {KEY: 0.8}}
    assert provenance.rebuild_generation_fingerprint_from_recorded_sources(bundle, scaled, scope_data_dir=output) == scaled
    # Rebuilding approval evidence must catch even subpixel configuration drift.
    bundle.manifest["artwork"]["spatial_reference_scales"][KEY] = 0.800001
    assert provenance.rebuild_generation_fingerprint_from_recorded_sources(bundle, scaled, scope_data_dir=output)["sha256"] != scaled["sha256"]


@pytest.mark.parametrize("override", [None, [], {KEY: True}, {KEY: "0.8"}, {KEY: 0},
                                     {KEY: -1}, {KEY: 1.1}, {KEY: float("nan")},
                                     {KEY: float("inf")}, {"4": 0.8},
                                     {"pokeapi:official-artwork:384": 0.8}])
def test_invalid_scales_fail_before_reference_writes(detailed, override):
    bundle, output = detailed
    bundle.manifest["artwork"]["spatial_reference_scales"] = override
    for action in (_prepare, _graph, lambda: provenance.build_generation_fingerprint(bundle, scope_data_dir=output)):
        with pytest.raises(ValueError, match="spatial_reference_scales"):
            action()
    assert not (bundle.work_dir / "joint_scene_cast_reference.png").exists()


def test_non_source_detail_modes_cannot_silently_ignore_scales(detailed):
    bundle, output = detailed
    bundle.manifest["artwork"]["spatial_reference_scales"] = {KEY: 0.8}
    for mode in ("spatial_identity_joint", "individual_spatial_joint", "regional_identity_joint"):
        bundle.manifest["artwork"]["generation"]["reference_mode"] = mode
        for action in (
            lambda: preparation.prepare("Example", 2.0, generation_mode="joint_scene", reference_mode=mode),
            lambda: workflow.build_workflow("Example", 123, 2.0, generation_mode="joint_scene", reference_mode=mode),
            lambda: provenance.build_generation_fingerprint(bundle, scope_data_dir=output),
        ):
            with pytest.raises(ValueError, match="spatial_reference_scales"):
                action()


def test_duplicate_yaml_scale_keys_are_rejected(tmp_path):
    path = tmp_path / "poster.yaml"
    path.write_text(f"artwork:\n  spatial_reference_scales:\n    {KEY}: 0.8\n    {KEY}: 0.7\n")
    with pytest.raises(ValueError, match="Duplicate spatial_reference_scales"):
        load_yaml(path)


def test_scaling_preserves_asymmetric_visible_center_and_baseline(detailed):
    bundle, _ = detailed
    source = Image.new("RGBA", (30, 20), (0, 0, 0, 0))
    source.paste((235, 120, 50, 255), (12, 2, 28, 16))
    source.save(bundle.source_dir / "cutouts/pokemon_004.png")
    args = dict(layout_name="standard_3x3", canvas_size=(1200, 1664))
    before = joint_scene_canvas_placements(bundle.source_dir, **args)[1]
    after = joint_scene_canvas_placements(bundle.source_dir, subject_scales={KEY: 0.8}, **args)[1]
    a, b = (p["image"].getchannel("A").getbbox() for p in (before, after))
    assert abs((2 * before["x"] + a[0] + a[2]) - (2 * after["x"] + b[0] + b[2])) <= 1
    assert before["y"] + a[3] == after["y"] + b[3]
    assert after["image"].width == round(before["image"].width * 0.8)
    assert after["image"].height == round(before["image"].height * 0.8)


def test_special_form_scale_key_never_falls_back_to_species():
    items = [{"pokemon_id": 384, "poster_subject": PosterSubject(384, 10079).as_mapping()}]
    manifest = {"artwork": {"spatial_reference_scales": {"pokeapi:official-artwork:10079": 0.8}}}
    assert spatial_reference_scales(manifest, items, reference_mode=MODE) == {"pokeapi:official-artwork:10079": 0.8}
    manifest["artwork"]["spatial_reference_scales"] = {"pokeapi:official-artwork:384": 0.8}
    with pytest.raises(ValueError, match="canonical cast keys"):
        spatial_reference_scales(manifest, items, reference_mode=MODE)


def test_special_form_fingerprint_rebuild_without_source_files(detailed):
    bundle, output = detailed
    subject = PosterSubject(384, 10079)
    path = bundle.source_dir / "cutouts/manifest.json"
    data = json.loads(path.read_text())
    data["items"][1].update(pokemon_id=384, url=subject.image_url, poster_subject=subject.as_mapping())
    path.write_text(json.dumps(data))
    scope_path = output / "Example.json"
    scope = json.loads(scope_path.read_text())
    scope["sections"]["main"]["featured_elements"][1] = {"pokemon_id": 384, "poster_subject": subject.as_mapping()}
    scope_path.write_text(json.dumps(scope))
    details = bundle.manifest["artwork"]["source_details"]
    details[subject.subject_key] = details.pop(KEY)
    bundle.manifest["artwork"]["spatial_reference_scales"] = {subject.subject_key: 0.8}
    fingerprint = provenance.build_generation_fingerprint(bundle, scope_data_dir=output)
    for image in path.parent.glob("*.png"):
        image.unlink()
    rebuilt = provenance.rebuild_generation_fingerprint_from_recorded_sources(bundle, fingerprint, scope_data_dir=output)
    assert rebuilt == fingerprint
