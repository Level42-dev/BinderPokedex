"""P16 masks follow the real card raster, not equal image thirds."""
from __future__ import annotations

import torch

from scripts.poster_assets.region_joint.geometry import (
    build_p16_region_contract,
    validate_p16_region_contract,
)
from scripts.poster_assets.region_joint.comfy_extension.region_math import latent_weight


def test_contract_uses_exact_source_and_print_card_spans():
    contract = build_p16_region_contract()
    assert contract["generation_wh"] == [1200, 1664]
    assert contract["source_columns"] == [[0, 380], [410, 790], [820, 1200]]
    assert contract["source_rows"] == [[0, 535], [565, 1099], [1129, 1664]]
    assert contract["print_wh"] == [2368, 3268]
    assert contract["print_columns"] == [[0, 750], [809, 1559], [1618, 2368]]
    assert contract["print_rows"] == [[0, 1050], [1109, 2159], [2218, 3268]]
    assert contract["version"] == 3
    assert contract["latent_pixel_size"] == 16
    assert contract["image_token_size"] == 16
    assert contract["latent_hw"] == [104, 75]
    assert contract["token_hw"] == [104, 75]


def test_p16_subject_regions_are_inset_from_their_own_physical_cards():
    contract = build_p16_region_contract()
    assert contract["left"]["subject_id"] == "pokeapi:official-artwork:10077"
    assert contract["left"]["card"] == "r3c1"
    assert contract["left"]["card_xyxy"] == [0, 1129, 380, 1664]
    assert contract["left"]["inner_xyxy"] == [32, 1161, 348, 1632]
    assert contract["right"]["subject_id"] == "pokeapi:official-artwork:10078"
    assert contract["right"]["card"] == "r3c3"
    assert contract["right"]["card_xyxy"] == [820, 1129, 1200, 1664]
    assert contract["right"]["inner_xyxy"] == [852, 1161, 1168, 1632]


def test_latent_figures_have_exact_zero_outside_inner_rectangles_and_no_overlap():
    contract = build_p16_region_contract()
    left = latent_weight(tuple(contract["left"]["inner_xyxy"]), (104, 75))
    right = latent_weight(tuple(contract["right"]["inner_xyxy"]), (104, 75))
    assert left.shape == (1, 1, 104, 75)
    assert right.shape == left.shape
    assert torch.all(left[..., :72, :] == 0)
    assert torch.all(left[..., :, 22:] == 0)
    assert torch.all(right[..., :, :53] == 0)
    assert torch.max(left + right).item() <= 1.0
    assert left[..., 80, 12].item() == 1.0
    assert right[..., 80, 62].item() == 1.0
    assert 0 < left[..., 73, 2].item() < 1
    assert 0 < right[..., 73, 53].item() < 1


def test_latent_weight_rejects_rectangles_outside_canvas():
    import pytest

    with pytest.raises(ValueError, match="canvas"):
        latent_weight((32, 0, 1201, 80), (104, 75))


def test_mutated_or_overlapping_contract_is_rejected():
    import pytest

    contract = build_p16_region_contract()
    contract["right"]["inner_xyxy"] = list(contract["left"]["inner_xyxy"])
    with pytest.raises(ValueError, match="P16 region contract"):
        validate_p16_region_contract(contract)
