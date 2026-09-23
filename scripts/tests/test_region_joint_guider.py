"""One shared latent step with hard P16 attention and prediction boundaries."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest
import torch

from scripts.poster_assets.region_joint.geometry import build_p16_region_contract
from scripts.poster_assets.region_joint.comfy_extension import NODE_CLASS_MAPPINGS
from scripts.poster_assets.region_joint.comfy_extension.guider import (
    P16_CONTRACT_SHA256,
    RegionAttentionPatch,
    make_region_guider,
    preflight_mask_budget,
    with_region_patch,
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


def test_patch_covers_both_flux_block_types_and_restricts_local_references():
    left = torch.tensor([[True, False, False]])
    right = torch.tensor([[False, False, True]])
    patch = RegionAttentionPatch("left", (1, 3), left, right, expected_counts=(1, (1, 1)))
    q = k = v = torch.ones((1, 1, 6, 2))
    options = {"img_slice": [1, 6], "reference_image_num_tokens": [1, 1], "block_type": "double"}
    bias = patch(q, k, v, pe=None, attn_mask=None, extra_options=options)["attn_mask"]
    assert torch.isneginf(bias[0, 1])
    assert torch.isneginf(bias[2, 1])
    assert bias[1, 4] == 0
    assert torch.isneginf(bias[2, 4])
    assert torch.isneginf(bias[4, 5])
    options["block_type"] = "single"
    patch(q, k, v, pe=None, attn_mask=None, extra_options=options)
    assert patch.block_types == {"double", "single"}
    assert patch.calls == 2


def test_patch_rejects_changed_token_order_or_reference_count():
    mask = torch.tensor([[True, False, False]])
    patch = RegionAttentionPatch("left", (1, 3), mask, ~mask, expected_counts=(1, (1, 1)))
    q = k = v = torch.ones((1, 1, 6, 2))
    with pytest.raises(ValueError, match="token"):
        patch(q, k, v, pe=None, attn_mask=None,
              extra_options={"img_slice": [2, 6], "reference_image_num_tokens": [1, 1], "block_type": "double"})
    with pytest.raises(ValueError, match="reference"):
        patch(q, k, v, pe=None, attn_mask=None,
              extra_options={"img_slice": [1, 6], "reference_image_num_tokens": [2], "block_type": "single"})


def test_model_options_clone_does_not_mutate_original_and_rejects_existing_hook():
    original = {"transformer_options": {"patches": {"other": ["kept"]}}}
    patch = object()
    result = with_region_patch(original, patch, clone_fn=copy.deepcopy)
    assert original["transformer_options"]["patches"] == {"other": ["kept"]}
    assert result["transformer_options"]["patches"]["attn1_patch"] == [patch]
    with pytest.raises(ValueError, match="conflicting"):
        with_region_patch({"transformer_options": {"patches": {"attn1_patch": [object()]}}},
                          patch, clone_fn=copy.deepcopy)


def test_preflight_rejects_wrong_reference_count_and_oversized_masks():
    conditionings = {"global": _conditioning(1, 0), "left": _conditioning(1, 2), "right": _conditioning(1, 2)}
    assert preflight_mask_budget(conditionings, (104, 75), torch.float32) < 1024**3
    conditionings["left"] = _conditioning(1, 1)
    with pytest.raises(ValueError, match="two references"):
        preflight_mask_budget(conditionings, (104, 75), torch.float32)
    conditionings["left"] = [[torch.zeros((1, 1, 4)), {"reference_latents": [torch.zeros((1, 4, 160, 160)) for _ in range(2)]}]]
    with pytest.raises(MemoryError):
        preflight_mask_budget(conditionings, (104, 75), torch.float32)


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

    class FakePatch:
        def __init__(self, branch, *_args, **_kwargs):
            self.branch = branch
            self.calls = 0
            self.block_types = set()

    def sampler(_model, x, timestep, uncond, cond, scale, *, model_options, seed):
        patch = model_options["transformer_options"]["patches"]["attn1_patch"][0]
        calls.append((patch.branch, x, timestep, uncond, scale, seed))
        patch.calls = 2
        patch.block_types.update(("double", "single"))
        return torch.full_like(x, {"global": 1, "left": 3, "right": 5}[patch.branch])

    guider = make_region_guider(
        FakeModel(), conditionings, _contract_json(), base_cls=FakeBase,
        sampling_fn=sampler, clone_fn=copy.deepcopy, patch_factory=FakePatch,
    )
    x = torch.zeros((1, 1, 208, 150))
    timestep = torch.tensor([0.7])
    result = guider.predict_noise(x, timestep, seed=99)
    assert [item[0] for item in calls] == ["global", "left", "right"]
    assert all(item[1] is x and item[2] is timestep and item[3] is None and item[4] == 1.0 and item[5] == 99 for item in calls)
    assert result[..., 10, 70].item() == 1
    assert result[..., 160, 20].item() == 3
    assert result[..., 160, 130].item() == 5


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
        guider.predict_noise(torch.zeros((1, 1, 208, 150)), torch.tensor([0.7]))
