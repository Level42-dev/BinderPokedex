"""P16 physical card region contract, derived from print layout geometry."""
from __future__ import annotations

import math

from scripts.poster_assets.layout import build_print_layout, build_source_layout

from .eligibility import P16_SCOPE


CONTRACT_VERSION = 3
GENERATION_WH = (1200, 1664)
LATENT_PIXEL_SIZE = 16
# The pinned FLUX.2 transformer uses patch_size=1: one 16px latent cell per
# main-image token. The older Qwen 2x2 packing assumption was superseded by
# the observed P16 pilot C token counts (see its review record).
IMAGE_TOKEN_SIZE = 16


def build_p16_region_contract() -> dict:
    """Describe exactly two print-safe subject regions in a shared canvas."""
    width, height = GENERATION_WH
    source = build_source_layout("standard_3x3", width_px=width, height_px=height)
    printed = build_print_layout("standard_3x3", dpi=300)
    guard = math.ceil(0.08 * source.card_width_px / IMAGE_TOKEN_SIZE) * IMAGE_TOKEN_SIZE

    def subject(column: int, subject_id: str) -> dict:
        card = source.cell(3, column)
        card_rect = [card.x, card.y, card.x + card.width, card.y + card.height]
        inner = [card.x + guard, card.y + guard, card.x + card.width - guard, card.y + card.height - guard]
        if inner[0] >= inner[2] or inner[1] >= inner[3]:
            raise ValueError("P16 guard eliminates subject card interior")
        return {
            "subject_id": subject_id,
            "card": f"r3c{column}",
            "card_xyxy": card_rect,
            "inner_xyxy": inner,
        }

    left = subject(1, "pokeapi:official-artwork:10077")
    right = subject(3, "pokeapi:official-artwork:10078")
    if left["inner_xyxy"][2] > right["inner_xyxy"][0]:
        raise ValueError("P16 subject regions overlap")
    return {
        "version": CONTRACT_VERSION,
        "scope": P16_SCOPE,
        "layout": "standard_3x3",
        "token_order": "text_main_references",
        "generation_wh": [width, height],
        "latent_pixel_size": LATENT_PIXEL_SIZE,
        "image_token_size": IMAGE_TOKEN_SIZE,
        "source_columns": [list(span) for span in source.column_spans],
        "source_rows": [list(span) for span in source.row_spans],
        "print_wh": [printed.width_px, printed.height_px],
        "print_columns": [list(span) for span in printed.column_spans],
        "print_rows": [list(span) for span in printed.row_spans],
        "latent_hw": [height // LATENT_PIXEL_SIZE, width // LATENT_PIXEL_SIZE],
        "token_hw": [math.ceil(height / IMAGE_TOKEN_SIZE), math.ceil(width / IMAGE_TOKEN_SIZE)],
        "guard_px": guard,
        "left": left,
        "right": right,
    }


def validate_p16_region_contract(contract: dict) -> dict:
    """Reject any altered rectangle, grid or subject identity in a job graph."""
    expected = build_p16_region_contract()
    if contract != expected:
        raise ValueError("P16 region contract differs from physical source/print geometry")
    return expected
