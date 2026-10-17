"""Blend per-branch denoised predictions within print-safe regions."""
from __future__ import annotations

import torch


def mix_predictions(
    base: torch.Tensor,
    local_predictions: tuple[torch.Tensor, ...],
    weights: tuple[torch.Tensor, ...],
) -> torch.Tensor:
    """Keep all pixels outside local weights bit-identical to the base."""
    if not local_predictions or len(local_predictions) != len(weights) or base.ndim != 4:
        raise ValueError("Invalid regional prediction set")
    if not torch.isfinite(base).all():
        raise ValueError("Predictions must be finite")
    total_weight = torch.zeros((1, 1, *base.shape[-2:]), dtype=base.dtype, device=base.device)
    for local, weight in zip(local_predictions, weights, strict=True):
        if local.shape != base.shape or local.dtype != base.dtype or local.device != base.device:
            raise ValueError("Local prediction does not match shared latent shape")
        if weight.shape != total_weight.shape or weight.device != base.device or weight.dtype != base.dtype:
            raise ValueError("Regional weight does not match latent shape")
        if not torch.isfinite(local).all() or not torch.isfinite(weight).all():
            raise ValueError("Predictions and weights must be finite")
        if torch.any(weight < 0) or torch.any(weight > 1):
            raise ValueError("Regional weights must be within 0..1")
        total_weight = total_weight + weight
    if torch.any(total_weight > 1):
        raise ValueError("Regional weights overlap")
    result = base
    for local, weight in zip(local_predictions, weights, strict=True):
        result = result + weight * (local - base)
    if not torch.isfinite(result).all():
        raise ValueError("Mixed prediction must be finite")
    return result
