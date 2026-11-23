#!/usr/bin/env python3
"""Export a finished poster as one printable image per binder card cell."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

try:
    from .layout import build_image_layout
    from .poster_io import POSTER_ASSETS, poster_bundle
except ImportError:
    from layout import build_image_layout
    from poster_io import POSTER_ASSETS, poster_bundle


ROOT = Path(__file__).resolve().parents[2]


def slice_poster(scope: str, source: Path, output_dir: Path | None = None) -> list[Path]:
    """Crop the card areas and discard the physical binder gaps between them."""
    manifest = poster_bundle(
        scope,
        poster_assets=POSTER_ASSETS,
    ).manifest
    paths = slice_artwork(source, manifest.get("layout", {}).get("name", "standard_3x3"), output_dir)
    return [path for path in paths if path is not None]


def slice_artwork(
    source: Path,
    layout_name: str,
    output_dir: Path | None = None,
    *,
    skip: frozenset[tuple[int, int]] = frozenset(),
) -> list[Path | None]:
    """Crop a row-major physical layout, leaving skipped slots empty."""
    with Image.open(source) as loaded:
        source_dpi = loaded.info.get("dpi")
        image = loaded.convert("RGB")
    layout = build_image_layout(
        layout_name,
        width_px=image.width,
        height_px=image.height,
        dpi=source_dpi,
    )

    target_dir = output_dir or source.with_name(f"{source.stem}_cards")
    target_dir.mkdir(parents=True, exist_ok=True)
    for stale_path in target_dir.glob("card_r*_c*.png"):
        stale_path.unlink()
    outputs: list[Path | None] = []
    for row in range(1, layout.rows + 1):
        for column in range(1, layout.columns + 1):
            if (row, column) in skip:
                outputs.append(None)
                continue
            cell = layout.cell(row, column)
            card = image.crop(
                (
                    cell.x,
                    cell.y,
                    cell.x + cell.width,
                    cell.y + cell.height,
                )
            )
            path = target_dir / f"card_r{row}_c{column}.png"
            save_options = {"format": "PNG", "optimize": True}
            if source_dpi:
                save_options["dpi"] = source_dpi
            card.save(path, **save_options)
            outputs.append(path)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", default="Base1")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    outputs = slice_poster(args.scope, args.input, args.output_dir)
    print(f"Wrote {len(outputs)} card images to {outputs[0].parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
