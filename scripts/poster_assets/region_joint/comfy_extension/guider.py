"""One-state P16 FLUX guider with checked, branch-local attention."""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable

import torch

from .mixer import mix_predictions
from .region_math import MAX_ATTENTION_MASK_BYTES, attention_bias, latent_weight


P16_CONTRACT_SHA256 = "2499accfd70d8d2e5fe6e94669cd4fda866f2b80adc16f6fe283eb74b332bdd7"
MAX_ALL_MASKS_BYTES = 1024**3
BRANCHES = ("global", "left", "right")


def _checked_contract(value: str) -> dict:
    if not isinstance(value, str):
        raise ValueError("P16 region contract must be JSON")
    contract = json.loads(value)
    if not isinstance(contract, dict):
        raise ValueError("P16 region contract must be an object")
    canonical = json.dumps(contract, sort_keys=True, separators=(",", ":"))
    if hashlib.sha256(canonical.encode()).hexdigest() != P16_CONTRACT_SHA256:
        raise ValueError("P16 region contract differs from the approved physical layout")
    return contract


def _token_mask(rect: list[int], token_hw: tuple[int, int]) -> torch.Tensor:
    x0, y0, x1, y1 = rect
    height, width = token_hw
    x = (torch.arange(width, dtype=torch.float32) + 0.5) * 16
    y = (torch.arange(height, dtype=torch.float32) + 0.5) * 16
    return ((x >= x0) & (x < x1))[None, :] & ((y >= y0) & (y < y1))[:, None]


def _conditioning_counts(conditioning: list, expected_refs: int) -> tuple[int, tuple[int, ...]]:
    if not isinstance(conditioning, list) or len(conditioning) != 1:
        raise ValueError("P16 branch must have exactly one conditioning entry")
    entry = conditioning[0]
    if not isinstance(entry, (list, tuple)) or len(entry) != 2 or not isinstance(entry[0], torch.Tensor) or not isinstance(entry[1], dict):
        raise ValueError("P16 conditioning has an unsupported shape")
    context, options = entry
    if context.ndim != 3 or context.shape[0] != 1 or context.shape[1] <= 0:
        raise ValueError("P16 text token geometry is invalid")
    refs = options.get("reference_latents", [])
    if not isinstance(refs, list) or len(refs) != expected_refs:
        raise ValueError("P16 local branch requires exactly two references" if expected_refs else "P16 global branch must have no references")
    counts = []
    for latent in refs:
        if not isinstance(latent, torch.Tensor) or latent.ndim != 4 or latent.shape[0] != 1 or min(latent.shape[-2:]) <= 0:
            raise ValueError("P16 reference latent geometry is invalid")
        counts.append(math.ceil(latent.shape[-2] / 2) * math.ceil(latent.shape[-1] / 2))
    return int(context.shape[1]), tuple(counts)


def preflight_mask_budget(conditionings: dict, main_hw: tuple[int, int], dtype: torch.dtype) -> int:
    """Prove all three masks fit before the first denoising step."""
    if set(conditionings) != set(BRANCHES) or not dtype.is_floating_point:
        raise ValueError("P16 branch or model dtype is invalid")
    if len(main_hw) != 2 or any(type(part) is not int or part <= 0 for part in main_hw):
        raise ValueError("P16 main token geometry is invalid")
    element_bytes = torch.empty((), dtype=dtype).element_size()
    main_count = math.prod(main_hw)
    total_bytes = 0
    for branch in BRANCHES:
        text_count, refs = _conditioning_counts(conditionings[branch], 0 if branch == "global" else 2)
        tokens = text_count + main_count + sum(refs)
        size = tokens * tokens * element_bytes
        if size > MAX_ATTENTION_MASK_BYTES:
            raise MemoryError(f"P16 {branch} attention mask exceeds 384 MiB")
        total_bytes += size
    if total_bytes > MAX_ALL_MASKS_BYTES:
        raise MemoryError("P16 attention masks exceed 1 GiB combined")
    return total_bytes


class RegionAttentionPatch:
    """Add a FLUX double-/single-stream Q/K gate without changing Q, K or V."""

    def __init__(
        self,
        branch: str,
        token_hw: tuple[int, int],
        left_mask: torch.Tensor,
        right_mask: torch.Tensor,
        *,
        expected_counts: tuple[int, tuple[int, ...]] | None = None,
        expected_dtype: torch.dtype | None = None,
    ) -> None:
        if branch not in BRANCHES or left_mask.shape != token_hw or right_mask.shape != token_hw:
            raise ValueError("P16 attention region geometry is invalid")
        if left_mask.dtype != torch.bool or right_mask.dtype != torch.bool or torch.any(left_mask & right_mask):
            raise ValueError("P16 attention regions overlap or are not boolean")
        self.branch = branch
        self.token_hw = token_hw
        self.left_mask = left_mask
        self.right_mask = right_mask
        self.expected_counts = expected_counts
        self.expected_dtype = expected_dtype
        self.calls = 0
        self.block_types: set[str] = set()
        self._cached_bias: dict[tuple, torch.Tensor] = {}

    def __call__(self, q, k, v, *, pe, attn_mask, extra_options):
        if attn_mask is not None:
            raise ValueError("P16 refuses a pre-existing attention mask")
        if not all(isinstance(tensor, torch.Tensor) and tensor.ndim == 4 for tensor in (q, k, v)):
            raise ValueError("P16 attention tensors are invalid")
        if q.shape[:3] != k.shape[:3] or q.shape[:3] != v.shape[:3] or q.device != k.device or q.device != v.device:
            raise ValueError("P16 attention Q/K/V token geometry differs")
        if self.expected_dtype is not None and q.dtype != self.expected_dtype:
            raise ValueError("P16 attention dtype differs from preflight")
        if not isinstance(extra_options, dict) or extra_options.get("block_type") not in {"double", "single"}:
            raise ValueError("P16 FLUX block metadata is missing")
        image_slice = extra_options.get("img_slice")
        if not isinstance(image_slice, (list, tuple)) or len(image_slice) != 2 or image_slice[1] != q.shape[2]:
            raise ValueError("P16 token order or image slice differs")
        text_count = image_slice[0]
        refs = extra_options.get("reference_image_num_tokens", [])
        if not isinstance(refs, (list, tuple)) or any(type(count) is not int or count <= 0 for count in refs):
            raise ValueError("P16 reference token counts are invalid")
        refs = tuple(refs)
        if self.branch == "global" and refs or self.branch != "global" and len(refs) != 2:
            raise ValueError("P16 reference count differs from branch")
        if self.expected_counts is not None and (text_count, refs) != self.expected_counts:
            raise ValueError("P16 reference or text token count differs from preflight")
        if text_count + math.prod(self.token_hw) + sum(refs) != q.shape[2]:
            raise ValueError("P16 token count differs from text/main/reference order")

        protected = self.left_mask | self.right_mask if self.branch == "global" else (self.left_mask if self.branch == "left" else self.right_mask)
        allowed = None if self.branch == "global" else protected
        key = (q.device, q.dtype, text_count, refs)
        bias = self._cached_bias.get(key)
        if bias is None:
            bias = attention_bias(text_count, self.token_hw, refs, protected, allowed, dtype=q.dtype, device=q.device)
            self._cached_bias[key] = bias
        self.calls += 1
        self.block_types.add(extra_options["block_type"])
        return {"attn_mask": bias}


def with_region_patch(model_options: dict, patch: RegionAttentionPatch, *, clone_fn: Callable | None = None) -> dict:
    """Clone existing ComfyUI options and attach only this branch's hook."""
    if clone_fn is None:
        import comfy.model_patcher

        clone_fn = comfy.model_patcher.create_model_options_clone
    options = clone_fn(model_options)
    transformer = options.setdefault("transformer_options", {})
    patches = transformer.setdefault("patches", {})
    if any(name.startswith("attn1") for name in patches) or transformer.get("patches_replace"):
        raise ValueError("P16 has a conflicting attention patch")
    patches["attn1_patch"] = [patch]
    return options


def make_region_guider(
    model,
    conditionings: dict,
    region_contract: str,
    *,
    base_cls: type,
    sampling_fn: Callable,
    clone_fn: Callable,
    patch_factory: Callable = RegionAttentionPatch,
):
    """Create a CFGGuider subclass that shares x/t across three branches."""
    contract = _checked_contract(region_contract)
    token_hw = tuple(contract["token_hw"])
    latent_hw = tuple(contract["latent_hw"])
    dtype = model.model_dtype()
    preflight_mask_budget(conditionings, token_hw, dtype)
    expected_counts = {
        branch: _conditioning_counts(conditionings[branch], 0 if branch == "global" else 2)
        for branch in BRANCHES
    }
    left_mask = _token_mask(contract["left"]["inner_xyxy"], token_hw)
    right_mask = _token_mask(contract["right"]["inner_xyxy"], token_hw)
    if torch.any(left_mask & right_mask) or not torch.any(left_mask) or not torch.any(right_mask):
        raise ValueError("P16 token regions are empty or overlapping")
    weights = (
        latent_weight(tuple(contract["left"]["inner_xyxy"]), latent_hw),
        latent_weight(tuple(contract["right"]["inner_xyxy"]), latent_hw),
    )
    if torch.any(weights[0] + weights[1] > 1):
        raise ValueError("P16 latent regions overlap")

    class P16RegionGuider(base_cls):
        def __init__(self):
            super().__init__(model)
            self.inner_set_conds(conditionings)
            self.region_contract = contract

        def predict_noise(self, x, timestep, model_options=None, seed=None):
            if tuple(x.shape[-2:]) != latent_hw:
                raise ValueError("P16 latent canvas does not match region contract")
            options = model_options or {}
            predictions = []
            for branch in BRANCHES:
                patch = patch_factory(
                    branch, token_hw, left_mask, right_mask,
                    expected_counts=expected_counts[branch], expected_dtype=dtype,
                )
                branch_options = with_region_patch(options, patch, clone_fn=clone_fn)
                prediction = sampling_fn(
                    self.inner_model, x, timestep, None, self.conds[branch], 1.0,
                    model_options=branch_options, seed=seed,
                )
                if patch.calls == 0 or patch.block_types != {"double", "single"}:
                    raise RuntimeError("Region attention patch was not invoked in both FLUX block types")
                predictions.append(prediction)
            on_device = tuple(weight.to(device=x.device, dtype=x.dtype) for weight in weights)
            return mix_predictions(predictions[0], tuple(predictions[1:]), on_device)

    return P16RegionGuider()


def create_guider(model, global_conditioning, left_conditioning, right_conditioning, region_contract: str):
    import comfy.model_patcher
    import comfy.samplers

    return make_region_guider(
        model,
        {"global": global_conditioning, "left": left_conditioning, "right": right_conditioning},
        region_contract,
        base_cls=comfy.samplers.CFGGuider,
        sampling_fn=comfy.samplers.sampling_function,
        clone_fn=comfy.model_patcher.create_model_options_clone,
    )
