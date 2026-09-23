"""Pure tensor masks shared by the job-local regional guider."""
from __future__ import annotations

import math

import torch


MAX_ATTENTION_MASK_BYTES = 384 * 1024**2


def latent_weight(rect: tuple[int, int, int, int], latent_hw: tuple[int, int]) -> torch.Tensor:
    """Rasterize an inset figure rectangle with a two-latent-pixel edge ramp."""
    if (
        len(rect) != 4 or len(latent_hw) != 2
        or any(type(value) is not int for value in (*rect, *latent_hw))
    ):
        raise ValueError("Invalid rectangle or latent canvas")
    x0, y0, x1, y1 = rect
    height, width = latent_hw
    if not (0 <= x0 < x1 <= width * 8 and 0 <= y0 < y1 <= height * 8):
        raise ValueError("Region rectangle is outside latent canvas")
    x = (torch.arange(width, dtype=torch.float32) + 0.5) * 8
    y = (torch.arange(height, dtype=torch.float32) + 0.5) * 8
    horizontal = torch.minimum(((x - x0) / 16).clamp(0, 1), ((x1 - x) / 16).clamp(0, 1))
    vertical = torch.minimum(((y - y0) / 16).clamp(0, 1), ((y1 - y) / 16).clamp(0, 1))
    return (vertical[:, None] * horizontal[None, :])[None, None]


def attention_bias(
    text_count: int,
    main_hw: tuple[int, int],
    reference_counts: tuple[int, ...],
    protected_main: torch.Tensor,
    allowed_reference_queries: torch.Tensor | None,
    *,
    dtype: torch.dtype,
    device: torch.device,
) -> torch.Tensor:
    """Build additive 0/-inf Q/K bias for text, main image and references."""
    if type(text_count) is not int or text_count <= 0:
        raise ValueError("text token count must be positive")
    if len(main_hw) != 2 or any(type(value) is not int or value <= 0 for value in main_hw):
        raise ValueError("main token geometry is invalid")
    if any(type(value) is not int or value <= 0 for value in reference_counts):
        raise ValueError("reference token counts are invalid")
    if not dtype.is_floating_point:
        raise ValueError("attention bias requires a floating-point dtype")
    if not isinstance(protected_main, torch.Tensor) or protected_main.dtype != torch.bool or tuple(protected_main.shape) != tuple(main_hw):
        raise ValueError("protected main token geometry is invalid")
    if reference_counts:
        if (
            not isinstance(allowed_reference_queries, torch.Tensor)
            or allowed_reference_queries.dtype != torch.bool
            or tuple(allowed_reference_queries.shape) != tuple(main_hw)
        ):
            raise ValueError("allowed reference query geometry is invalid")
    elif allowed_reference_queries is not None:
        raise ValueError("global branch has no reference queries")

    main_count = math.prod(main_hw)
    total = text_count + main_count + sum(reference_counts)
    bytes_needed = total * total * torch.empty((), dtype=dtype).element_size()
    if bytes_needed > MAX_ATTENTION_MASK_BYTES:
        raise MemoryError("Region attention mask exceeds 384 MiB")
    bias = torch.zeros((total, total), dtype=dtype, device=device)
    main = torch.arange(text_count, text_count + main_count, device=device)
    protected = protected_main.to(device=device).reshape(-1)
    exterior_queries = torch.cat((torch.arange(text_count, device=device), main[~protected]))
    protected_keys = main[protected]
    if protected_keys.numel():
        bias[exterior_queries[:, None], protected_keys] = -torch.inf

    if reference_counts:
        reference_keys = torch.arange(text_count + main_count, total, device=device)
        allowed = allowed_reference_queries.to(device=device).reshape(-1)
        denied_queries = torch.cat((torch.arange(text_count, device=device), main[~allowed]))
        bias[denied_queries[:, None], reference_keys] = -torch.inf
        bias[reference_keys[:, None], reference_keys] = -torch.inf
        bias[reference_keys, reference_keys] = 0
    return bias
