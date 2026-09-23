"""One shared latent step with hard P16 attention and prediction boundaries."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest
import torch
from torch.nn import functional as F

from scripts.poster_assets.region_joint.geometry import build_p16_region_contract
from scripts.poster_assets.region_joint.comfy_extension import NODE_CLASS_MAPPINGS
from scripts.poster_assets.region_joint.comfy_extension.guider import (
    P16_CONTRACT_SHA256,
    RegionAttentionOverride,
    make_region_guider,
    preflight_mask_budget,
    with_region_override,
)
from scripts.poster_assets.region_joint.comfy_extension.mixer import mix_predictions


def _contract_json() -> str:
    return json.dumps(build_p16_region_contract(), sort_keys=True)


def _conditioning(text_tokens: int, reference_count: int):
    return [[
        torch.zeros((1, text_tokens, 4)),
        {"reference_latents": [torch.zeros((1, 4, 2, 2)) for _ in range(reference_count)]},
    ]]


def test_extension_contract_hash_matches_physical_layout():
    canonical = json.dumps(build_p16_region_contract(), sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(canonical.encode()).hexdigest() == P16_CONTRACT_SHA256
    assert "RegionConstrainedJointGuider" in NODE_CLASS_MAPPINGS


def test_zero_weight_outside_is_exact_global():
    base = torch.ones((1, 1, 4, 4))
    local = torch.full_like(base, 7)
    weight = torch.zeros_like(base)
    weight[..., 1:3, 1:3] = 1
    result = mix_predictions(base, (local,), (weight,))
    assert torch.equal(result[..., 0, :], base[..., 0, :])
    assert torch.equal(result[..., 1:3, 1:3], local[..., 1:3, 1:3])


def test_mixer_rejects_overlapping_or_nonfinite_branch():
    base = torch.zeros((1, 1, 2, 2))
    local = torch.ones_like(base)
    with pytest.raises(ValueError, match="overlap"):
        mix_predictions(base, (local, local), (torch.ones_like(base), torch.ones_like(base)))
    local[0, 0, 0, 0] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        mix_predictions(base, (local,), (torch.ones_like(base),))


def test_override_applies_mask_at_actual_attention_and_preserves_text_key_mask():
    left = torch.tensor([[True, False, False]])
    right = torch.tensor([[False, False, True]])
    override = RegionAttentionOverride("left", (1, 3), left, right, expected_counts=(1, (1, 1)))
    q = k = torch.zeros((1, 1, 6, 1))
    v = torch.tensor([0, 100, 0, 0, 1000, 2000], dtype=torch.float32).view(1, 1, 6, 1)
    text_mask = torch.zeros((1, 1, 6))
    text_mask[..., 0] = -torch.inf
    seen = []

    def attention(q, k, v, heads, mask=None, **kwargs):
        assert heads == 1
        seen.append(mask)
        return F.scaled_dot_product_attention(q, k, v, attn_mask=mask)

    result = override(
        attention, q, k, v, 1, text_mask,
        transformer_options={"reference_image_num_tokens": [1, 1], "block_type": "double"},
        skip_reshape=True,
    )
    assert result[0, 0, 2, 0].item() == 0  # exterior cannot read own subject or references
    assert result[0, 0, 1, 0].item() > 0  # own protected figure can read its references
    assert torch.isneginf(seen[0][0, 0, 2, 0])  # original text mask remains effective
    assert torch.isneginf(seen[0][0, 0, 2, 1])
    assert torch.isneginf(seen[0][0, 0, 2, 4])
    assert override.block_types == {"double"}
    assert override.calls == 1


def test_override_rejects_changed_token_order_or_reference_count():
    mask = torch.tensor([[True, False, False]])
    override = RegionAttentionOverride("left", (1, 3), mask, ~mask, expected_counts=(1, (1, 1)))
    q = k = v = torch.ones((1, 1, 6, 2))
    attention = lambda *_args, **_kwargs: q
    with pytest.raises(ValueError, match="token"):
        override(attention, q[..., :-1, :], k[..., :-1, :], v[..., :-1, :], 1,
                 transformer_options={"reference_image_num_tokens": [1, 1], "block_type": "double"}, skip_reshape=True)
    with pytest.raises(ValueError, match="reference"):
        override(attention, q, k, v, 1,
                 transformer_options={"reference_image_num_tokens": [2], "block_type": "double"}, skip_reshape=True)
    with pytest.raises(ValueError, match="block"):
        override(attention, q, k, v, 1,
                 transformer_options={"reference_image_num_tokens": [1, 1], "block_type": "single"}, skip_reshape=True)


def test_model_options_clone_does_not_mutate_original_and_rejects_existing_hook():
    original = {"transformer_options": {"patches": {"other": ["kept"]}}}
    override = object()
    result = with_region_override(original, override, clone_fn=copy.deepcopy)
    assert original["transformer_options"]["patches"] == {"other": ["kept"]}
    assert result["transformer_options"]["optimized_attention_override"] is override
    with pytest.raises(ValueError, match="conflicting"):
        with_region_override({"transformer_options": {"optimized_attention_override": object()}},
                             override, clone_fn=copy.deepcopy)
    with pytest.raises(ValueError, match="conflicting"):
        with_region_override({"transformer_options": {"patches": {"attn1_patch": [object()]}}},
                             override, clone_fn=copy.deepcopy)


def test_preflight_rejects_wrong_reference_count_and_oversized_masks():
    conditionings = {"global": _conditioning(1, 0), "left": _conditioning(1, 2), "right": _conditioning(1, 2)}
    assert preflight_mask_budget(conditionings, (52, 38), torch.float32) < 1024**3
    conditionings["left"] = _conditioning(1, 1)
    with pytest.raises(ValueError, match="two references"):
        preflight_mask_budget(conditionings, (52, 38), torch.float32)
    conditionings["left"] = [[torch.zeros((1, 1, 4)), {"reference_latents": [torch.zeros((1, 4, 160, 160)) for _ in range(2)]}]]
    with pytest.raises(MemoryError):
        preflight_mask_budget(conditionings, (52, 38), torch.float32)


def test_guider_uses_same_x_and_timestep_for_three_branches_and_one_prediction():
    conditionings = {"global": _conditioning(1, 0), "left": _conditioning(1, 2), "right": _conditioning(1, 2)}
    calls = []

    class FakeModel:
        def model_dtype(self):
            return torch.float32

    class FakeBase:
        def __init__(self, model):
            self.model_patcher = model
            self.inner_model = model
            self.conds = {}

        def inner_set_conds(self, values):
            self.conds.update(values)

    class FakeOverride:
        def __init__(self, branch, *_args, **_kwargs):
            self.branch = branch
            self.calls = 0
            self.block_types = set()

    def sampler(_model, x, timestep, uncond, cond, scale, *, model_options, seed):
        override = model_options["transformer_options"]["optimized_attention_override"]
        calls.append((override.branch, x, timestep, uncond, scale, seed))
        override.calls = 2
        override.block_types.add("double")
        return torch.full_like(x, {"global": 1, "left": 3, "right": 5}[override.branch])

    guider = make_region_guider(
        FakeModel(), conditionings, _contract_json(), base_cls=FakeBase,
        sampling_fn=sampler, clone_fn=copy.deepcopy, override_factory=FakeOverride,
    )
    x = torch.zeros((1, 1, 104, 75))
    timestep = torch.tensor([0.7])
    result = guider.predict_noise(x, timestep, seed=99)
    assert [item[0] for item in calls] == ["global", "left", "right"]
    assert all(item[1] is x and item[2] is timestep and item[3] is None and item[4] == 1.0 and item[5] == 99 for item in calls)
    assert result[..., 10, 70].item() == 1
    assert result[..., 80, 12].item() == 3
    assert result[..., 80, 62].item() == 5


def test_guider_fails_when_attention_hook_is_not_called():
    conditionings = {"global": _conditioning(1, 0), "left": _conditioning(1, 2), "right": _conditioning(1, 2)}

    class FakeModel:
        def model_dtype(self):
            return torch.float32

    class FakeBase:
        def __init__(self, model):
            self.inner_model = model
            self.conds = {}

        def inner_set_conds(self, values):
            self.conds.update(values)

    guider = make_region_guider(
        FakeModel(), conditionings, _contract_json(), base_cls=FakeBase,
        sampling_fn=lambda _model, x, *_args, **_kwargs: x,
        clone_fn=copy.deepcopy,
    )
    with pytest.raises(RuntimeError, match="not invoked"):
        guider.predict_noise(torch.zeros((1, 1, 104, 75)), torch.tensor([0.7]))
