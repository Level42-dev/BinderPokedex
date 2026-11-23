from math import dist
from pathlib import Path

import pytest
import yaml
from PIL import Image
from pypdf import PdfReader
from pypdf.generic import ContentStream

from scripts.poster_assets.extended_artwork import (
    CENTER,
    LAYOUT_NAME,
    MASK_NAME,
    OUTPAINT_NAME,
    card_bounds,
    create_binder_preview,
    create_outpaint_inputs,
    export_artwork,
    prepare,
)
from scripts.poster_assets.layout import build_print_layout, build_source_layout
from scripts.poster_assets.render_job import load_json, sha256_file


def test_outpaint_mask_leaves_the_card_art_fixed_and_all_eight_slots_editable():
    layout = build_source_layout(LAYOUT_NAME, width_px=1200, height_px=1664)
    scan = Image.new("RGB", (600, 825), "red")
    source, mask = create_outpaint_inputs(scan, layout, inset=(24, 24, 24, 24))

    left, top, right, bottom = card_bounds(layout, CENTER)
    middle = ((left + right) // 2, (top + bottom) // 2)
    assert source.getpixel(middle) == (255, 0, 0)
    assert mask.getbbox() == (left + 15, top + 16, right - 15, bottom - 16)
    assert mask.getpixel((left, top)) == 0
    for row, column in ((1, 1), (1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2), (3, 3)):
        cell = layout.cell(row, column)
        assert mask.getpixel((cell.x + cell.width // 2, cell.y + cell.height // 2)) == 0


def test_render_job_conditions_and_masks_the_same_card_canvas(tmp_path: Path):
    recipe_path = Path("config/extended-artwork/bisasam-scr-143.yaml")
    recipe = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    scan = tmp_path / "scan.png"
    Image.new("RGB", (600, 825), "red").save(scan)
    recipe["card"]["sha256"] = sha256_file(scan)
    local_recipe = tmp_path / "recipe.yaml"
    local_recipe.write_text(yaml.safe_dump(recipe), encoding="utf-8")

    job = tmp_path / "render"
    manifest = load_json(prepare(local_recipe, scan, job))
    workflow = load_json(job / manifest["workflow"]["path"])
    assert {entry["path"] for entry in manifest["inputs"]} == {MASK_NAME, OUTPAINT_NAME}
    sampler, = [node for node in workflow.values() if node["class_type"] == "SamplerCustomAdvanced"]
    mask_id, _index = sampler["inputs"]["latent_image"]
    mask = workflow[mask_id]
    assert mask["class_type"] == "SetLatentNoiseMask"
    encoder_id, _index = mask["inputs"]["samples"]
    mask_image_id, mask_socket = mask["inputs"]["mask"]
    assert mask_socket == 1
    assert workflow[mask_image_id]["inputs"]["image"] == MASK_NAME
    assert any(
        node["class_type"] == "ReferenceLatent" and node["inputs"]["latent"] == [encoder_id, 0]
        for node in workflow.values()
    )


def test_geometry_uses_card_coordinates_without_moving_the_scan():
    layout = build_source_layout(LAYOUT_NAME, width_px=1200, height_px=1664)
    scan = Image.new("RGB", (600, 825), "red")
    source, mask = create_outpaint_inputs(
        scan, layout, inset=(24, 24, 24, 24),
        guide={
            "background": "#152550",
            "polygons": [
                {"fill": "#26a384", "points": [[0, 0], [1000, 0], [1000, 825], [0, 825]]},
            ],
        },
    )
    left, top, right, bottom = card_bounds(layout, CENTER)
    y = (top + bottom) // 2
    assert source.getpixel((left - 1, y)) == (21, 37, 80)
    assert source.getpixel((right + 1, y)) == (38, 163, 132)
    assert source.getpixel(((left + right) // 2, y)) == (255, 0, 0)
    assert mask.getpixel((right + 1, y)) == 0


def test_binder_preview_uses_full_center_scan_and_actual_gaps():
    layout = build_print_layout(LAYOUT_NAME)
    artwork = Image.new("RGB", (layout.width_px, layout.height_px), "blue")
    center = layout.cell(*CENTER)
    scan = Image.new("RGB", (center.width, center.height), "red")
    scan.putpixel((center.width - 1, center.height - 1), (255, 255, 0))

    preview = create_binder_preview(artwork, scan, layout)
    assert preview.getpixel((center.x, center.y)) == (255, 0, 0)
    assert preview.getpixel((center.x + center.width - 1, center.y + center.height - 1)) == (
        255, 255, 0,
    )
    assert preview.getpixel((center.x + center.width, center.y + 5)) == (255, 255, 255)
    neighbor = layout.cell(2, 3)
    assert preview.getpixel((neighbor.x, neighbor.y + 5)) == (0, 0, 255)


def test_fixed_guide_geometry_locks_only_its_registered_area():
    layout = build_source_layout(LAYOUT_NAME, width_px=1200, height_px=1664)
    scan = Image.new("RGB", (600, 825), "red")
    points = [[280, -160], [450, -160], [450, 23], [280, 23]]
    source, mask = create_outpaint_inputs(
        scan, layout, inset=(23, 23, 23, 23),
        guide={
            "background": "#f0d0b0",
            "polygons": [{"fill": "#a9575a", "points": points}],
            "fixed_regions": [points],
        },
    )
    left, top, right, bottom = card_bounds(layout, CENTER)
    scale_x = (right - left) / scan.width
    fixed_point = (round(left + scale_x * 360), top - 40)
    adjacent_point = (round(left + scale_x * 500), top - 40)
    assert source.getpixel(fixed_point) == (169, 87, 90)
    assert mask.getpixel(fixed_point) == 255
    assert mask.getpixel(adjacent_point) == 0


def test_composition_prepares_a_hash_checked_layer_and_mask(tmp_path):
    from scripts.poster_assets.extended_artwork import prepare_composite

    recipe = yaml.safe_load(Path("config/extended-artwork/bisasam-scr-143.yaml").read_text())
    scan = tmp_path / "card.png"
    Image.new("RGB", (600, 825), "red").save(scan)
    recipe["card"]["sha256"] = sha256_file(scan)
    inputs = {name: tmp_path / f"{name}.png" for name in ("painting", "wall")}
    for name, path in inputs.items():
        Image.new("RGB", (1200, 1664), "blue" if name == "wall" else "white").save(path)
    recipe["render_composition"] = {
        "painting": {"render_sha256": sha256_file(inputs["painting"])},
        "wall": {
            "render_sha256": sha256_file(inputs["wall"]),
            "polygon": [[10, 20], [50, 20], [50, 60], [10, 60]],
            "cutouts": [[[24, 24], [36, 24], [36, 36], [24, 36]]],
            "feather_px": 0,
        },
    }
    recipe_path = tmp_path / "recipe.yaml"
    recipe_path.write_text(yaml.safe_dump(recipe, sort_keys=False))
    job_dir = tmp_path / "job"
    manifest = load_json(prepare_composite(recipe_path, scan, job_dir, inputs))
    assert {entry["path"] for entry in manifest["inputs"]} == {
        "painting.png", "wall.png", "wall-mask.png",
    }
    workflow = load_json(job_dir / "workflow_api.json")
    assert sum(n["class_type"] == "ImageCompositeMasked" for n in workflow.values()) == 1
    with Image.open(job_dir / "input" / "wall-mask.png") as source:
        mask = source.getchannel("A")
        assert mask.getpixel((20, 40)) == 0
        assert mask.getpixel((30, 30)) == 255
        assert mask.getpixel((0, 0)) == 255


def test_palette_match_respects_shape_and_dominant_channel():
    from scripts.poster_assets.extended_artwork import match_palette

    layout = build_source_layout(LAYOUT_NAME, width_px=1200, height_px=1664)
    blue = (168, 161, 197)
    ochre = (200, 125, 75)
    canvas = Image.new("RGB", (layout.width_px, layout.height_px), blue)
    left, top, right, bottom = card_bounds(layout, CENTER)
    inside = (right + 3, (top + bottom) // 2)
    other_color = (inside[0] + 1, inside[1])
    canvas.putpixel(other_color, ochre)
    result = match_palette(canvas, (600, 825), layout, [{
        "points": [[600, 0], [1100, 0], [1100, 825], [600, 825]],
        "cutouts": [[[680, 300], [750, 300], [750, 500], [680, 500]]],
        "dominant_channel": "B",
        "source_rgb": list(blue),
        "target_rgb": [107, 116, 182],
        "contrast": 0.27,
    }])
    assert result.getpixel(inside) == (107, 116, 182)
    assert result.getpixel(other_color) == ochre
    assert result.getpixel((left, top)) == blue
    assert canvas.getpixel(inside) == blue
    protected_x = left + round((right - left) * 710 / 600)
    assert result.getpixel((protected_x, inside[1])) == blue


def test_a4_export_draws_eight_physical_cards_and_all_cutting_guides(tmp_path: Path):
    layout = build_print_layout(LAYOUT_NAME)
    master = tmp_path / "master.png"
    image = Image.new("RGB", (layout.width_px, layout.height_px), "steelblue")
    image.paste("white", card_bounds(layout, CENTER))
    image.save(master, dpi=(300, 300))

    output = export_artwork("test", "de", "Test", master, tmp_path)
    reader = PdfReader(output)
    assert len(reader.pages) == 1
    page = reader.pages[0]
    assert (float(page.mediabox.width), float(page.mediabox.height)) == pytest.approx(
        (595.276, 841.890), abs=0.001,
    )
    operations = ContentStream(page.get_contents(), reader).operations
    assert sum(op == b"Do" for _, op in operations) == 8
    assert sum(op == b"S" for _, op in operations) == 1
    transforms = [
        tuple(float(value) for value in operands)
        for operands, operator in operations
        if operator == b"cm" and float(operands[0]) == 180
    ]
    assert len(transforms) == 8
    assert all(matrix[:4] == (180, 0, 0, 252) for matrix in transforms)
    x_positions = sorted({matrix[4] for matrix in transforms})
    y_positions = sorted({matrix[5] for matrix in transforms})
    assert len(x_positions) == len(y_positions) == 3
    assert {(matrix[4], matrix[5]) for matrix in transforms} == {
        (x, y) for x in x_positions for y in y_positions
        if (x, y) != (x_positions[1], y_positions[1])
    }
    mark_starts = [tuple(map(float, values)) for values, op in operations if op == b"m"]
    mark_ends = [tuple(map(float, values)) for values, op in operations if op == b"l"]
    assert len(mark_ends) == len(mark_starts) == 8 * 8
    for _, _, _, _, left, bottom in transforms:
        for x in (left, left + 180):
            for y in (bottom, bottom + 252):
                aligned = [
                    (end_x, end_y)
                    for start, (end_x, end_y) in zip(mark_starts, mark_ends)
                    if dist(start, (x, y)) < 1
                ]
                assert len(aligned) == 2
                assert any(abs(end_x - x) < 0.001 for end_x, _ in aligned)
                assert any(abs(end_y - y) < 0.001 for _, end_y in aligned)


def test_a4_export_rejects_a_master_with_artwork_in_the_center(tmp_path: Path):
    layout = build_print_layout(LAYOUT_NAME)
    master = tmp_path / "master.png"
    Image.new("RGB", (layout.width_px, layout.height_px), "steelblue").save(master)

    with pytest.raises(ValueError, match="middle cell blank"):
        export_artwork("test", "de", "Test", master, tmp_path)
    assert not list(tmp_path.glob("*.pdf"))
