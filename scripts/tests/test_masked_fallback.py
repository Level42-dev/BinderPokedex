"""Pixel-level proof for explicitly reviewed masked poster fallbacks."""

from pathlib import Path

import pytest
from PIL import Image

from scripts.poster_assets.layout import Cell
from scripts.poster_assets.masked_fallback import (
    alpha_edit_mask,
    audit_masked_merge,
    card_mask_to_canvas,
    decode_mask,
    encode_mask,
    outside_pixel_digest,
)


def _save(tmp_path: Path, name: str, image: Image.Image) -> Path:
    path = tmp_path / name
    image.save(path)
    return path


def _merge_fixture(tmp_path: Path):
    base = Image.new("RGB", (4, 4), (10, 20, 30))
    first = base.copy()
    first.putpixel((1, 1), (40, 20, 30))
    second = base.copy()
    second.putpixel((2, 2), (10, 50, 30))
    final = base.copy()
    final.putpixel((1, 1), (40, 20, 30))
    final.putpixel((2, 2), (10, 50, 30))
    first_mask = Image.new("L", base.size, 0)
    first_mask.putpixel((1, 1), 255)
    second_mask = Image.new("L", base.size, 0)
    second_mask.putpixel((2, 2), 255)
    return (
        _save(tmp_path, "base.png", base),
        _save(tmp_path, "final.png", final),
        [(_save(tmp_path, "first.png", first), first_mask),
         (_save(tmp_path, "second.png", second), second_mask)],
    )


def test_padded_card_mask_maps_exactly_to_physical_cell():
    padded = Image.new("L", (8, 6), 0)
    padded.putpixel((2, 1), 255)
    padded.putpixel((5, 4), 255)
    cell = Cell(row=3, column=1, x=3, y=5, width=4, height=4)
    canvas = card_mask_to_canvas(padded, cell, (10, 10))
    assert canvas.getbbox() == (3, 5, 7, 9)
    assert canvas.getpixel((3, 5)) == 255
    assert canvas.getpixel((6, 8)) == 255
    assert sum(value == 255 for value in canvas.get_flattened_data()) == 2


def test_padded_mask_rejects_editable_padding_and_odd_offset():
    cell = Cell(row=1, column=1, x=0, y=0, width=4, height=4)
    padded = Image.new("L", (8, 6), 0)
    padded.putpixel((0, 0), 255)
    with pytest.raises(ValueError, match="padding"):
        card_mask_to_canvas(padded, cell, (4, 4))
    with pytest.raises(ValueError, match="center"):
        card_mask_to_canvas(Image.new("L", (7, 6), 0), cell, (4, 4))


def test_historical_top_left_card_padding_maps_without_center_shift():
    padded = Image.new("L", (8, 6), 0)
    padded.putpixel((1, 1), 255)
    cell = Cell(row=3, column=1, x=3, y=5, width=4, height=4)
    canvas = card_mask_to_canvas(padded, cell, (10, 10), padding_origin="top_left")
    assert canvas.getbbox() == (4, 6, 5, 7)
    padded.putpixel((7, 5), 255)
    with pytest.raises(ValueError, match="padding"):
        card_mask_to_canvas(padded, cell, (10, 10), padding_origin="top_left")


def test_historical_black_rgba_alpha_encoding_normalizes_to_binary_edit_mask():
    source = Image.new("RGBA", (4, 4), (0, 0, 0, 255))
    source.putpixel((1, 1), (0, 0, 0, 254))
    source.putpixel((2, 2), (0, 0, 0, 0))
    mask = alpha_edit_mask(source)
    assert mask.mode == "L"
    assert mask.getpixel((1, 1)) == 255
    assert mask.getpixel((2, 2)) == 255
    assert mask.getpixel((0, 0)) == 0


def test_binary_mask_rle_roundtrip_and_malformed_runs():
    mask = Image.new("L", (4, 3), 0)
    for index in (1, 2, 6, 7, 8):
        mask.putpixel((index % 4, index // 4), 255)
    record = encode_mask(mask)
    assert record == {"width": 4, "height": 3, "runs": [[1, 2], [6, 3]]}
    assert decode_mask(record).tobytes() == mask.tobytes()
    with pytest.raises(ValueError, match="overlap|order"):
        decode_mask({"width": 4, "height": 3, "runs": [[6, 3], [1, 2]]})
    mask.putpixel((0, 0), 128)
    with pytest.raises(ValueError, match="binary"):
        encode_mask(mask)


def test_masked_merge_proves_two_disjoint_repairs_and_outside_digest(tmp_path):
    base, final, repairs = _merge_fixture(tmp_path)
    audit = audit_masked_merge(base, final, repairs)
    assert audit["editable_pixels"] == 2
    assert audit["changed_editable_pixels"] == 2
    assert audit["changed_outside_mask_pixels"] == 0
    assert [item["changed_editable_pixels"] for item in audit["repairs"]] == [1, 1]
    with Image.open(base) as source, Image.open(final) as merged:
        assert outside_pixel_digest(source, audit["union_mask"]) == audit["outside_base_pixel_sha256"]
        assert outside_pixel_digest(merged, audit["union_mask"]) == audit["outside_base_pixel_sha256"]


def test_overlapping_repair_masks_are_rejected(tmp_path):
    base, final, repairs = _merge_fixture(tmp_path)
    repairs[1][1].putpixel((1, 1), 255)
    with pytest.raises(ValueError, match="overlap"):
        audit_masked_merge(base, final, repairs)


def test_one_channel_outside_change_is_rejected(tmp_path):
    base, final, repairs = _merge_fixture(tmp_path)
    with Image.open(final) as loaded:
        changed = loaded.copy()
    changed.putpixel((3, 3), (11, 20, 30))
    changed.save(final)
    with pytest.raises(ValueError, match="outside"):
        audit_masked_merge(base, final, repairs)


def test_repair_change_outside_its_own_mask_is_rejected(tmp_path):
    base, final, repairs = _merge_fixture(tmp_path)
    with Image.open(repairs[0][0]) as loaded:
        changed = loaded.copy()
    changed.putpixel((0, 0), (11, 20, 30))
    changed.save(repairs[0][0])
    with pytest.raises(ValueError, match="outside"):
        audit_masked_merge(base, final, repairs)


def test_missing_repair_and_wrong_final_pixels_are_rejected(tmp_path):
    base, final, repairs = _merge_fixture(tmp_path)
    repairs[0][0].unlink()
    with pytest.raises(FileNotFoundError):
        audit_masked_merge(base, final, repairs)
    base, final, repairs = _merge_fixture(tmp_path)
    with Image.open(final) as loaded:
        changed = loaded.copy()
    changed.putpixel((1, 1), (41, 20, 30))
    changed.save(final)
    with pytest.raises(ValueError, match="reconstruct"):
        audit_masked_merge(base, final, repairs)
