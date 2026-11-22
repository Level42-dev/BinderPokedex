import os
import subprocess
import sys
from pathlib import Path

import yaml
from PIL import Image, ImageChops
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
SCOPE = "zapdos-sammlung"


def collection_workspace(tmp_path):
    workspace = tmp_path / "posters"
    manifest = workspace / SCOPE / "poster.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        yaml.safe_dump({
            "scope": SCOPE,
            "source": {"collection": {"title": {"de": "Zapdos - Sammlung"}}},
            "layout": {"name": "standard_3x3"},
            "text_cells": {"title": {"row": 1, "column": 2}},
            "text_content": {"mode": "title_only"},
        }),
        encoding="utf-8",
    )
    return {**os.environ, "BINDER_POKEDEX_POSTER_ASSETS": str(workspace)}


def run_module(module, env, *args):
    return subprocess.run(
        [sys.executable, "-m", module, *map(str, args)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def run_export(env, artwork, output, *options):
    return run_module(
        "scripts.pdf.generate_artwork_pdf", env,
        "--scope", SCOPE, "--language", "de", "--artwork", artwork,
        "--output-dir", output, *options,
    )


def test_export_uses_the_native_poster_overlay_and_keeps_it_inside_the_title_card(tmp_path):
    env = collection_workspace(tmp_path)
    master = tmp_path / "scene.png"
    background = Image.new("RGB", (789, 1089), "#38285d")
    background.save(master, dpi=(100, 100))
    output = tmp_path / "output"

    result = run_export(env, master, output)

    assert result.returncode == 0, result.stderr
    files = list(output.iterdir())
    assert [file.name for file in files] == ["zapdos-sammlung-de-a4.pdf"]
    pdf = PdfReader(files[0])
    assert pdf.metadata.title == "Zapdos - Sammlung"
    assert len(pdf.pages) == 1
    page = pdf.pages[0]
    assert abs(float(page.mediabox.width) - 595.276) < 0.01
    assert abs(float(page.mediabox.height) - 841.89) < 0.01
    assert len(page.images) == 1
    assert not {b"l", b"S"} & {op for _, op in page.get_contents().operations}
    embedded = page.images[0].image.convert("RGB")
    left, top, right, bottom = ImageChops.difference(background, embedded).getbbox()
    # A 63.5 × 88.9 mm card in the top center, with a 5 mm gutter on its sides.
    assert 270 < left < right < 520
    assert 0 < top < bottom < 350

    localized = tmp_path / "localized.png"
    result = run_module(
        "scripts.poster_assets.finalize_comfyui_poster", env,
        "--scope", SCOPE, "--input", master, "--output", localized, "--language", "de",
    )
    assert result.returncode == 0, result.stderr
    with Image.open(localized) as poster:
        assert ImageChops.difference(poster.convert("RGB"), embedded).getbbox() is None


def test_missing_master_preserves_previous_export(tmp_path):
    env = collection_workspace(tmp_path)
    previous = tmp_path / "zapdos-sammlung-de-a4.pdf"
    previous.write_bytes(b"existing independent export")

    result = run_export(env, tmp_path / "missing.png", tmp_path)

    assert result.returncode != 0
    assert "Poster artwork not found:" in result.stderr
    assert "missing.png" in result.stderr
    assert previous.read_bytes() == b"existing independent export"


def test_cards_export_draws_nine_physical_artwork_tiles_and_cutting_guides(tmp_path):
    env = collection_workspace(tmp_path)
    master = tmp_path / "scene.png"
    Image.new("RGB", (789, 1089), "#38285d").save(master, dpi=(100, 100))

    result = run_export(env, master, tmp_path, "--poster-page-mode", "cards")

    assert result.returncode == 0, result.stderr
    pdf = PdfReader(tmp_path / "zapdos-sammlung-de-a4-cards.pdf")
    assert len(pdf.pages) == 1
    page = pdf.pages[0]
    assert abs(float(page.mediabox.width) - 595.276) < 0.01
    assert abs(float(page.mediabox.height) - 841.89) < 0.01
    operations = page.get_contents().operations
    assert sum(operator == b"Do" for _, operator in operations) == 9
    assert sum(
        operator == b"cm" and operands[0] == 180 and operands[3] == 252
        for operands, operator in operations
    ) == 9
    assert sum(operator == b"S" for _, operator in operations) == 8


def test_collection_description_and_wordmark_fit_their_own_cards(tmp_path):
    env = collection_workspace(tmp_path)
    manifest_path = Path(env["BINDER_POKEDEX_POSTER_ASSETS"]) / SCOPE / "poster.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["source"]["collection"].update(
        title={"de": "Zapdos"},
        description={"de": "Der Himmel bebt, wenn Zapdos seine Schwingen ausbreitet."},
    )
    manifest["text_content"] = {
        "mode": "collection_profile",
        "title_style": "cinzel_decorative",
    }
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    master = tmp_path / "scene.png"
    background = Image.new("RGB", (789, 1089), "#38285d")
    background.save(master, dpi=(100, 100))
    localized = tmp_path / "localized.png"

    result = run_module(
        "scripts.poster_assets.finalize_comfyui_poster", env,
        "--scope", SCOPE, "--input", master, "--output", localized, "--language", "de",
    )

    assert result.returncode == 0, result.stderr
    with Image.open(localized) as poster:
        difference = ImageChops.difference(background, poster.convert("RGB"))
    title = difference.crop((270, 0, 520, 350)).getbbox()
    description = difference.crop((270, 370, 520, 720)).getbbox()
    assert title is not None and description is not None
    left, top, right, bottom = difference.getbbox()
    assert 270 <= left < right <= 520
    assert 0 < top < 350 and 370 < bottom < 720


def test_collection_wordmark_supports_the_rounded_font_and_a_custom_palette(tmp_path):
    env = collection_workspace(tmp_path)
    manifest_path = Path(env["BINDER_POKEDEX_POSTER_ASSETS"]) / SCOPE / "poster.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["source"]["collection"]["title"]["de"] = "Zapdos"
    manifest["text_content"].update(
        title_style="lilita_one",
        title_colors={"fill": "#FFE3F2", "outline": "#783465"},
    )
    manifest_path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    master = tmp_path / "scene.png"
    Image.new("RGB", (789, 1089), "#38285d").save(master, dpi=(100, 100))
    localized = tmp_path / "localized.png"

    result = run_module(
        "scripts.poster_assets.finalize_comfyui_poster", env,
        "--scope", SCOPE, "--input", master, "--output", localized, "--language", "de",
    )

    assert result.returncode == 0, result.stderr
    with Image.open(localized) as poster:
        colors = poster.crop((270, 0, 520, 350)).getcolors(maxcolors=250 * 350)
    assert (255, 227, 242) in {color for _, color in colors}
    assert (120, 52, 101) in {color for _, color in colors}
