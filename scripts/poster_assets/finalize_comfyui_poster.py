#!/usr/bin/env python3
"""Add deterministic poster panels and typography to ComfyUI artwork."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

try:
    from .layout import build_image_layout
    from .poster_io import (
        POSTER_ASSETS,
        load_poster_scope_data,
        poster_bundle,
    )
    from .scope_language import filter_variant_data_for_language
    from .typography import (
        draw_text_centered,
        load_font,
        wrap_text,
    )
except ImportError:
    from layout import build_image_layout
    from poster_io import POSTER_ASSETS, load_poster_scope_data, poster_bundle
    from scope_language import filter_variant_data_for_language
    from typography import (
        draw_text_centered,
        load_font,
        wrap_text,
    )


ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_LANGUAGES = (
    "de",
    "en",
    "fr",
    "es",
    "it",
    "ja",
    "ko",
    "zh_hans",
    "zh_hant",
)
CARD_LABELS = {
    "de": "Karten",
    "en": "cards",
    "fr": "cartes",
    "es": "cartas",
    "it": "carte",
    "ja": "枚",
    "ko": "장",
    "zh_hans": "张",
    "zh_hant": "張",
}
POKEMON_LABELS = {
    "de": "Pokémon",
    "en": "Pokémon",
    "fr": "Pokémon",
    "es": "Pokémon",
    "it": "Pokémon",
    "ja": "ポケモン",
    "ko": "포켓몬",
    "zh_hans": "宝可梦",
    "zh_hant": "寶可夢",
}
RELEASE_LABELS = {
    "de": "Veröffentlicht",
    "en": "Released",
    "fr": "Sortie",
    "es": "Publicado",
    "it": "Pubblicato",
    "ja": "発売日",
    "ko": "출시일",
    "zh_hans": "发行日期",
    "zh_hant": "發行日期",
}
MONTHS = {
    "de": ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"),
    "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"),
    "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"),
    "it": ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"),
}
OVERLAY_TOKEN_TEXT = {
    "[EX_NEW]": "ex",
    "[EX_TERA]": "Tera ex",
    "[EX]": "EX",
    "[M]": "Mega",
}
INLINE_TITLE_LOGOS = {
    "[EX_NEW]": ROOT / "images" / "logos" / "ex_new" / "default.png",
    "[EX_TERA]": ROOT / "images" / "logos" / "ex_tera" / "default.png",
    "[EX]": ROOT / "images" / "logos" / "ex" / "default.png",
    "[M]": ROOT / "images" / "logos" / "m_pokemon" / "default.png",
}
PLAIN_TITLE_RENDERER_CONTRACT = "direct_outlined_v1"


def readable_overlay_text(value: object) -> str:
    """Replace internal card-format tokens only in user-facing poster text."""
    text = str(value)
    for token, replacement in OVERLAY_TOKEN_TEXT.items():
        text = text.replace(token, replacement)
    return text


def localized_raw_value(value: object, language: str, *, default: str = "") -> str:
    """Resolve a localized scalar while preserving inline-logo tokens."""
    if isinstance(value, dict):
        selected = value.get(language) or value.get("en")
        if selected is None:
            selected = next((item for item in value.values() if item), default)
        return str(selected)
    return str(default if value is None else value)


def inline_title_logo(value: str) -> tuple[str, Path] | None:
    """Resolve one supported trailing logo token, otherwise use plain text."""
    matches = [
        (token, path)
        for token, path in INLINE_TITLE_LOGOS.items()
        if token in value
    ]
    if len(matches) != 1 or value.count(matches[0][0]) != 1:
        return None
    token, path = matches[0]
    label = value.removesuffix(token).strip()
    return (token, path) if label and value == f"{label} {token}" else None


def draw_title_logo(canvas: Image.Image, cell, logo_path: Path) -> None:
    logo = Image.open(logo_path).convert("RGBA")
    scale = min((cell.width * 0.94) / logo.width, (cell.height * 0.62) / logo.height)
    logo = logo.resize(
        (max(1, round(logo.width * scale)), max(1, round(logo.height * scale))),
        Image.Resampling.LANCZOS,
    )
    x = cell.x + (cell.width - logo.width) // 2
    y = cell.y + (cell.height - logo.height) // 2
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_alpha = logo.getchannel("A").filter(ImageFilter.GaussianBlur(max(2, canvas.width // 280)))
    shadow_shape = Image.new("RGBA", logo.size, (8, 18, 28, 105))
    shadow_shape.putalpha(shadow_alpha.point(lambda value: round(value * 0.42)))
    shadow.alpha_composite(shadow_shape, (x + max(2, canvas.width // 280), y + max(3, canvas.width // 220)))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(logo, (x, y))


def title_logo_file(manifest: dict, language: str) -> str | None:
    """Resolve only a title logo explicitly configured for this language."""
    config = manifest.get("title_logo", {})
    files = config.get("files")
    if isinstance(files, dict):
        return files.get(language)
    return config.get("file")


def localized_set_name(scope_data: dict, language: str) -> str:
    for section in scope_data.get("sections", {}).values():
        title = section.get("title")
        if isinstance(title, dict):
            return title.get(language) or title.get("en") or next(iter(title.values()))
    name = scope_data.get("name")
    if isinstance(name, dict):
        return str(name.get(language) or name.get("en") or next(iter(name.values())))
    return str(name or "Poster")


def resolved_title_text(scope_data: dict, language: str) -> str:
    """Resolve the one source-owned textual header before choosing its renderer."""
    if scope_data.get("type") == "pokedex":
        return localized_raw_value(scope_data.get("name"), language)
    return localized_set_name(scope_data, language)


def canonical_overlay_text(value: object) -> str:
    """Normalize rendered text only for semantic duplicate detection."""
    return " ".join(readable_overlay_text(value).split()).casefold()


def localized_value(value: object, language: str, *, default: str = "") -> str:
    """Resolve one localized scalar with a stable English/first-value fallback."""
    return readable_overlay_text(
        localized_raw_value(value, language, default=default)
    )


def selected_section(scope_data: dict) -> dict:
    sections = scope_data.get("sections", {})
    if isinstance(sections, dict):
        section = next(iter(sections.values()), None)
    elif isinstance(sections, list):
        section = next(iter(sections), None)
    else:
        section = None
    if not isinstance(section, dict):
        raise ValueError("Section-summary poster source has no selected section")
    return section


def card_count(scope_data: dict) -> int:
    return sum(
        len(section.get("cards", []))
        for section in scope_data.get("sections", {}).values()
        if isinstance(section.get("cards"), list)
    )


def localized_date(value: str, language: str) -> str:
    parsed = date.fromisoformat(value)
    if language in ("ja", "zh_hans", "zh_hant"):
        return f"{parsed.year}年{parsed.month}月{parsed.day}日"
    if language == "ko":
        return f"{parsed.year}년 {parsed.month}월 {parsed.day}일"
    month = MONTHS[language][parsed.month - 1]
    if language == "en":
        return f"{month} {parsed.day}, {parsed.year}"
    return f"{parsed.day}. {month} {parsed.year}" if language == "de" else f"{parsed.day} {month} {parsed.year}"


def info_panel_values(
    scope_data: dict,
    language: str,
    content_mode: str,
    *,
    header_text: str | None = None,
) -> tuple[str, ...]:
    """Resolve the deterministic text rows for one poster overlay profile."""
    scope_data = filter_variant_data_for_language(scope_data, language)
    if content_mode == "set_summary":
        values = (
            localized_set_name(scope_data, language),
            f"{card_count(scope_data)} {CARD_LABELS[language]}",
            RELEASE_LABELS[language],
            localized_date(str(scope_data["release_date"]), language),
        )
    elif content_mode == "section_summary":
        section = selected_section(scope_data)
        cards = section.get("cards")
        section_card_count = len(cards) if isinstance(cards, list) else 0
        values = (
            localized_value(section.get("title"), language),
            localized_value(section.get("subtitle"), language),
            f"{section_card_count} {POKEMON_LABELS[language]}",
            localized_value(section.get("description"), language),
        )
    else:
        raise ValueError(f"Unsupported text_content.mode: {content_mode}")
    if (
        header_text is not None
        and canonical_overlay_text(header_text) == canonical_overlay_text(values[0])
    ):
        return values[1:]
    return values


def info_panel_box(cell, config: dict | None = None) -> tuple[int, int, int, int]:
    """Return a centered panel constrained to configurable maximum dimensions."""
    config = config or {}
    max_width_ratio = float(config.get("max_width_ratio", 0.92))
    max_height_ratio = float(config.get("max_height_ratio", 0.68))
    if not 0.4 <= max_width_ratio <= 1.0:
        raise ValueError("set_info.max_width_ratio must be between 0.4 and 1.0")
    if not 0.4 <= max_height_ratio <= 0.9:
        raise ValueError("set_info.max_height_ratio must be between 0.4 and 0.9")

    width = round(cell.width * max_width_ratio)
    height = round(cell.height * max_height_ratio)
    center_x, center_y = cell.center
    left = center_x - width // 2
    top = center_y - height // 2
    return left, top, left + width, top + height


def fitted_font(
    text: str,
    box: tuple[int, int, int, int],
    *,
    preferred_size: int,
    minimum_size: int,
    bold: bool,
    language: str | None = None,
    avoid_short_last_line: bool = False,
):
    """Choose the largest font whose wrapped text stays inside ``box``."""
    max_width = box[2] - box[0]
    max_height = box[3] - box[1]
    for size in range(preferred_size, minimum_size - 1, -1):
        font = load_font(size, bold=bold, language=language)
        lines = wrap_text(text, font, max_width)
        if (
            avoid_short_last_line
            and len(lines) > 1
            and len(lines[-1].split()) == 1
            and len(lines[-1]) <= 3
        ):
            continue
        line_heights = [
            bounds[3] - bounds[1]
            for bounds in (font.getbbox(line) for line in lines)
        ]
        line_widths = [
            bounds[2] - bounds[0]
            for bounds in (font.getbbox(line) for line in lines)
        ]
        spacing = max(0, len(lines) - 1) * round(size * 0.28)
        if (
            max(line_widths, default=0) <= max_width
            and sum(line_heights) + spacing <= max_height
        ):
            return font
    raise ValueError(f"Text does not fit its bounded info-panel row: {text!r}")


def draw_info_panel(
    canvas: Image.Image,
    cell,
    scope_data: dict,
    language: str,
    config: dict | None = None,
    *,
    content_mode: str = "set_summary",
    header_text: str | None = None,
) -> None:
    box = info_panel_box(cell, config)
    scale = canvas.width / 1400
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    radius = max(8, round(24 * scale))
    shadow_box = (box[0] + max(3, round(8 * scale)), box[1] + max(4, round(10 * scale)), box[2] + max(3, round(8 * scale)), box[3] + max(4, round(10 * scale)))
    draw.rounded_rectangle(shadow_box, radius=radius, fill=(4, 15, 14, 115))
    overlay = overlay.filter(ImageFilter.GaussianBlur(max(2, round(5 * scale))))
    draw = ImageDraw.Draw(overlay, "RGBA")
    draw.rounded_rectangle(box, radius=radius, fill=(18, 50, 43, 226), outline=(224, 190, 98, 245), width=max(2, round(3 * scale)))
    inner = (box[0] + max(3, round(7 * scale)), box[1] + max(3, round(7 * scale)), box[2] - max(3, round(7 * scale)), box[3] - max(3, round(7 * scale)))
    draw.rounded_rectangle(inner, radius=max(5, radius - 5), outline=(255, 244, 190, 75), width=max(1, round(2 * scale)))
    canvas.alpha_composite(overlay)

    values = info_panel_values(
        scope_data,
        language,
        content_mode,
        header_text=header_text,
    )

    text_draw = ImageDraw.Draw(canvas, "RGBA")
    pad_x = max(5, round((box[2] - box[0]) * 0.04))
    height = box[3] - box[1]
    if content_mode == "set_summary" and len(values) == 4:
        rows = (
            (values[0], (box[0] + pad_x, box[1] + round(height * 0.05), box[2] - pad_x, box[1] + round(height * 0.34)), max(11, cell.height // 13), max(9, cell.height // 20), True, (255, 244, 190, 255)),
            (values[1], (box[0] + pad_x, box[1] + round(height * 0.34), box[2] - pad_x, box[1] + round(height * 0.57)), max(9, cell.height // 18), max(8, cell.height // 24), True, (232, 213, 151, 255)),
            (values[2], (box[0] + pad_x, box[1] + round(height * 0.57), box[2] - pad_x, box[1] + round(height * 0.76)), max(8, cell.height // 24), max(7, cell.height // 28), False, (185, 210, 190, 255)),
            (values[3], (box[0] + pad_x, box[1] + round(height * 0.75), box[2] - pad_x, box[3] - 4), max(8, cell.height // 21), max(7, cell.height // 27), False, (244, 238, 207, 255)),
        )
    elif content_mode == "set_summary":
        rows = (
            (values[0], (box[0] + pad_x, box[1] + round(height * 0.10), box[2] - pad_x, box[1] + round(height * 0.38)), max(10, cell.height // 16), max(8, cell.height // 23), True, (232, 213, 151, 255)),
            (values[1], (box[0] + pad_x, box[1] + round(height * 0.38), box[2] - pad_x, box[1] + round(height * 0.62)), max(9, cell.height // 20), max(7, cell.height // 27), False, (185, 210, 190, 255)),
            (values[2], (box[0] + pad_x, box[1] + round(height * 0.61), box[2] - pad_x, box[3] - round(height * 0.08)), max(10, cell.height // 17), max(8, cell.height // 24), False, (244, 238, 207, 255)),
        )
    elif len(values) == 4:
        rows = (
            (values[0], (box[0] + pad_x, box[1] + round(height * 0.05), box[2] - pad_x, box[1] + round(height * 0.29)), max(11, cell.height // 13), max(9, cell.height // 20), True, (255, 244, 190, 255)),
            (values[1], (box[0] + pad_x, box[1] + round(height * 0.28), box[2] - pad_x, box[1] + round(height * 0.48)), max(9, cell.height // 18), max(8, cell.height // 24), False, (185, 210, 190, 255)),
            (values[2], (box[0] + pad_x, box[1] + round(height * 0.47), box[2] - pad_x, box[1] + round(height * 0.67)), max(9, cell.height // 18), max(8, cell.height // 24), True, (232, 213, 151, 255)),
            (values[3], (box[0] + pad_x, box[1] + round(height * 0.66), box[2] - pad_x, box[3] - round(height * 0.05)), max(8, cell.height // 22), max(7, cell.height // 28), False, (244, 238, 207, 255)),
        )
    else:
        rows = (
            (values[0], (box[0] + pad_x, box[1] + round(height * 0.08), box[2] - pad_x, box[1] + round(height * 0.36)), max(10, cell.height // 16), max(8, cell.height // 23), False, (185, 210, 190, 255)),
            (values[1], (box[0] + pad_x, box[1] + round(height * 0.36), box[2] - pad_x, box[1] + round(height * 0.61)), max(10, cell.height // 16), max(8, cell.height // 23), True, (232, 213, 151, 255)),
            (values[2], (box[0] + pad_x, box[1] + round(height * 0.60), box[2] - pad_x, box[3] - round(height * 0.06)), max(9, cell.height // 19), max(7, cell.height // 27), False, (244, 238, 207, 255)),
        )
    for text, text_box, preferred_size, minimum_size, bold, color in rows:
        font = fitted_font(
            text,
            text_box,
            preferred_size=preferred_size,
            minimum_size=minimum_size,
            bold=bold,
            language=language,
        )
        draw_text_centered(
            text_draw,
            text,
            text_box,
            font,
            color,
            shadow_fill=None,
        )


def draw_project_signature(canvas: Image.Image) -> None:
    text = "Binder Pokedex"
    font = load_font(max(8, canvas.width // 72), bold=True)
    bbox = font.getbbox(text)
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = max(8, round(canvas.width * 0.018))
    x = canvas.width - margin - width
    y = canvas.height - margin - height
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.text((x + 1, y + 1), text, font=font, fill=(8, 20, 16, 175))
    draw.text((x, y), text, font=font, fill=(246, 239, 207, 215))


def draw_title_text(
    canvas: Image.Image,
    title_cell,
    title: str,
    language: str,
) -> tuple[int, int, int, int]:
    """Draw a localized, outlined title directly on the artwork."""
    text_box = title_cell.inset(0.05, 0.31)
    font = fitted_font(
        title,
        text_box,
        preferred_size=max(14, title_cell.height // 7),
        minimum_size=max(10, title_cell.height // 24),
        bold=True,
        language=language,
        avoid_short_last_line=True,
    )
    stroke_width = max(1, round(font.size / 28))
    draw_text_centered(
        ImageDraw.Draw(canvas, "RGBA"),
        title,
        text_box,
        font,
        (255, 248, 215, 255),
        shadow_fill=(5, 16, 22, 145),
        stroke_width=stroke_width,
        stroke_fill=(32, 68, 57, 245),
        shadow_offset=max(2, round(canvas.width / 390)),
    )
    return text_box


def draw_inline_logo_title(
    canvas: Image.Image,
    title_cell,
    title: str,
    language: str,
) -> tuple[int, int, int, int]:
    """Draw localized title text and one real logo directly on the artwork."""
    resolved = inline_title_logo(title)
    if resolved is None:
        raise ValueError(f"Inline title has no supported logo token: {title!r}")
    token, logo_path = resolved
    if not logo_path.is_file():
        raise FileNotFoundError(f"Inline title logo not found: {logo_path}")

    label = title.removesuffix(token).strip()
    max_width = round(title_cell.width * 0.90)
    max_height = round(title_cell.height * 0.38)
    preferred_size = max(14, title_cell.height // 7)
    minimum_size = max(10, title_cell.height // 24)
    with Image.open(logo_path) as loaded_logo:
        logo_source = loaded_logo.convert("RGBA")

    fitted = None
    for size in range(preferred_size, minimum_size - 1, -1):
        font = load_font(size, bold=True, language=language)
        text_box = font.getbbox(label)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        logo_height = max(1, round(size * 0.92))
        logo_width = max(
            1,
            round(logo_source.width * logo_height / logo_source.height),
        )
        gap = max(4, round(size * 0.16))
        total_width = text_width + gap + logo_width
        total_height = max(logo_height, text_height)
        if total_width <= max_width and total_height <= max_height:
            fitted = (
                font,
                text_box,
                text_width,
                text_height,
                logo_width,
                logo_height,
                gap,
                total_width,
                total_height,
            )
            break
    if fitted is None:
        raise ValueError(f"Inline title does not fit its cell: {title!r}")

    (
        font,
        text_box,
        text_width,
        text_height,
        logo_width,
        logo_height,
        gap,
        total_width,
        total_height,
    ) = fitted
    x = title_cell.x + (title_cell.width - total_width) // 2
    center_y = title_cell.y + title_cell.height // 2
    box = (
        x,
        center_y - total_height // 2,
        x + total_width,
        center_y + (total_height + 1) // 2,
    )
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    stroke_width = max(1, round(font.size / 28))
    shadow_offset = max(2, round(canvas.width / 390))
    text_y = center_y - text_height // 2 - text_box[1]
    draw.text(
        (x + shadow_offset, text_y + shadow_offset),
        label,
        font=font,
        fill=(5, 16, 22, 145),
        stroke_width=stroke_width + 1,
        stroke_fill=(5, 16, 22, 115),
    )
    draw.text(
        (x, text_y),
        label,
        font=font,
        fill=(255, 248, 215, 255),
        stroke_width=stroke_width,
        stroke_fill=(32, 68, 57, 245),
    )

    logo_x = x + text_width + gap
    logo_y = center_y - logo_height // 2
    logo = logo_source.resize(
        (logo_width, logo_height),
        Image.Resampling.LANCZOS,
    )
    shadow_alpha = logo.getchannel("A").filter(
        ImageFilter.GaussianBlur(max(2, canvas.width // 320))
    )
    shadow = Image.new("RGBA", logo.size, (5, 16, 22, 110))
    shadow.putalpha(shadow_alpha.point(lambda alpha: round(alpha * 0.50)))
    overlay.alpha_composite(
        shadow,
        (logo_x + shadow_offset, logo_y + shadow_offset),
    )
    overlay.alpha_composite(logo, (logo_x, logo_y))
    canvas.alpha_composite(overlay)
    return box


def draw_final_text_cells(canvas, layout, manifest, scope_data, scope_dir: Path, language: str) -> None:
    text_cells = manifest.get("text_cells", {})
    title_cfg = text_cells.get("title", {"row": 1, "column": 2})
    info_cfg = text_cells.get("set_info", {"row": 2, "column": 2})
    title_cell = layout.cell(int(title_cfg["row"]), int(title_cfg["column"]))
    info_cell = layout.cell(int(info_cfg["row"]), int(info_cfg["column"]))
    content_config = manifest.get("text_content", {})
    if not isinstance(content_config, dict):
        raise ValueError("text_content must be a mapping")
    logo_file = title_logo_file(manifest, language)
    header_text: str | None = None
    if logo_file:
        logo_path = scope_dir / logo_file
        if not logo_path.is_file():
            raise FileNotFoundError(f"Title logo not found: {logo_path}")
        draw_title_logo(canvas, title_cell, logo_path)
    else:
        header_text = resolved_title_text(scope_data, language)
        if inline_title_logo(header_text) is not None:
            draw_inline_logo_title(
                canvas,
                title_cell,
                header_text,
                language,
            )
        else:
            draw_title_text(
                canvas,
                title_cell,
                readable_overlay_text(header_text),
                language,
            )
    draw_info_panel(
        canvas,
        info_cell,
        scope_data,
        language,
        info_cfg,
        content_mode=content_config.get("mode", "set_summary"),
        header_text=header_text,
    )
    draw_project_signature(canvas)


def finalize(scope: str, input_path: Path, output_path: Path | None = None, language: str = "en") -> Path:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    bundle = poster_bundle(scope, poster_assets=POSTER_ASSETS)
    scope_dir = bundle.source_dir
    manifest = bundle.manifest
    scope_data = load_poster_scope_data(bundle)

    with Image.open(input_path) as source:
        source_dpi = source.info.get("dpi")
        canvas = source.convert("RGBA")
    layout = build_image_layout(
        manifest.get("layout", {}).get("name", "standard_3x3"),
        width_px=canvas.width,
        height_px=canvas.height,
        dpi=source_dpi,
    )

    draw_final_text_cells(canvas, layout, manifest, scope_data, scope_dir, language)
    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}_final.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_options = {"format": "PNG", "optimize": True}
    if source_dpi:
        save_options["dpi"] = source_dpi
    canvas.convert("RGB").save(output_path, **save_options)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", default="Base1")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--language", choices=SUPPORTED_LANGUAGES, default="en")
    args = parser.parse_args()
    print(finalize(args.scope, args.input, args.output, args.language))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
