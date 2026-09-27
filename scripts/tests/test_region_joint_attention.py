"""A branch cannot read protected figure pixels or foreign references."""
from __future__ import annotations

import pytest
import torch
from torch.nn import functional as F

from scripts.poster_assets.region_joint.comfy_extension.region_math import attention_bias


def test_text_and_other_card_queries_cannot_read_subject_keys():
    protected = torch.tensor([[False, True, False]])
    own_card = torch.tensor([[False, True, False]])
    bias = attention_bias(
        1, (1, 3), (1, 1), protected, own_card,
        dtype=torch.float32, device=torch.device("cpu"),
    )
    assert bias.shape == (6, 6)
    assert torch.isneginf(bias[0, 2])
    assert torch.isneginf(bias[1, 2])
    assert bias[2, 2] == 0
    assert torch.isneginf(bias[1, 4])
    assert bias[2, 4] == 0
    assert torch.isneginf(bias[0, 4])
    assert torch.isneginf(bias[4, 5])
    assert bias[5, 5] == 0


def test_global_branch_has_no_reference_keys_and_protects_both_subject_areas():
    bias = attention_bias(
        2, (1, 4), (), torch.tensor([[True, False, False, True]]), None,
        dtype=torch.float32, device=torch.device("cpu"),
    )
    assert bias.shape == (6, 6)
    assert torch.isneginf(bias[0, 2])
    assert torch.isneginf(bias[4, 5])
    assert bias[2, 2] == 0


def test_attention_mask_executes_finite_small_sdpa_on_cpu():
    bias = attention_bias(
        1, (1, 2), (1,), torch.tensor([[False, True]]),
        torch.tensor([[False, True]]), dtype=torch.float32,
        device=torch.device("cpu"),
    )
    q = k = v = torch.ones((1, 1, 4, 4), dtype=torch.float32)
    result = F.scaled_dot_product_attention(q, k, v, attn_mask=bias)
    assert torch.isfinite(result).all()


@pytest.mark.parametrize("text_count,main_hw,refs,protected,allowed", [
    (0, (1, 2), (), torch.zeros((1, 2), dtype=torch.bool), None),
    (1, (1, 2), (), torch.zeros((2, 1), dtype=torch.bool), None),
    (1, (1, 2), (1,), torch.zeros((1, 2), dtype=torch.bool), None),
    (1, (1, 2), (1,), torch.zeros((1, 2), dtype=torch.bool), torch.zeros((2, 1), dtype=torch.bool)),
])
def test_attention_mask_rejects_mismatched_token_geometry(text_count, main_hw, refs, protected, allowed):
    with pytest.raises(ValueError):
        attention_bias(
            text_count, main_hw, refs, protected, allowed,
            dtype=torch.float32, device=torch.device("cpu"),
        )


def test_attention_mask_rejects_oversized_allocation_before_allocating():
    with pytest.raises(MemoryError, match="384 MiB"):
        attention_bias(
            1, (1, 12000), (), torch.zeros((1, 12000), dtype=torch.bool), None,
            dtype=torch.float32, device=torch.device("cpu"),
        )
