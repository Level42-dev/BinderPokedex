"""Prepare, review and print an extended artwork page around a physical card."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from shutil import rmtree
from tempfile import NamedTemporaryFile, TemporaryDirectory

import yaml
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from .create_comfyui_poster_workflow import build_outpaint_workflow, node
from .layout import (
    DEFAULT_LAYOUT_NAME,
    PageLayout,
    build_print_layout,
    build_source_layout,
    latent_canvas_dimensions,
)
from .poster_io import poster_asset_slug
from .render_job import (
    load_json,
    prepare_job,
    safe_relative_path,
    sha256_file,
    verify_file,
)

ROOT = Path(__file__).resolve().parents[2]
LAYOUT_NAME = DEFAULT_LAYOUT_NAME
CENTER = (2, 2)
PRINT_DPI = 300
OUTPAINT_NAME = "outpaint.png"
MASK_NAME = "outpaint-mask.png"


def card_bounds(layout: PageLayout, position: tuple[int, int]) -> tuple[int, int, int, int]:
    cell = layout.cell(*position)
    return cell.x, cell.y, cell.x + cell.width, cell.y + cell.height


def match_palette(
    artwork: Image.Image,
    scan_size: tuple[int, int],
    layout: PageLayout,
    matches: list[dict],
) -> Image.Image:
    """Match one material to the card palette without changing its contours."""
    result = artwork.copy()
    cell = layout.cell(*CENTER)
    scale_x, scale_y = cell.width / scan_size[0], cell.height / scan_size[1]
    for match in matches:
        mask = Image.new("L", result.size)
        points = [(cell.x + x * scale_x, cell.y + y * scale_y) for x, y in match["points"]]
        draw = ImageDraw.Draw(mask)
        draw.polygon(points, fill=255)
        for cutout in match.get("cutouts", ()):
            points = [(cell.x + x * scale_x, cell.y + y * scale_y) for x, y in cutout]
            draw.polygon(points, fill=0)

        channel = match.get("dominant_channel")
        if channel:
            bands = dict(zip("RGB", result.split(), strict=True))
            selected = bands.pop(channel)
            others = ImageChops.lighter(*bands.values())
            dominance = ImageChops.subtract(selected, others)
            weight = dominance.point([max(0, min(255, (value - 4) * 23)) for value in range(256)])
            mask = ImageChops.multiply(mask, weight)

        contrast = match["contrast"]
        table = [
            max(0, min(255, round(target + contrast * (value - source))))
            for source, target in zip(match["source_rgb"], match["target_rgb"], strict=True)
            for value in range(256)
        ]
        result.paste(result.point(table), mask=mask)
    return result


def create_outpaint_inputs(
    scan: Image.Image,
    layout: PageLayout,
    *,
    inset: tuple[int, int, int, int],
    guide: dict | None = None,
) -> tuple[Image.Image, Image.Image]:
    """Place the borderless card art at its physical location on the canvas."""
    left, top, right, bottom = card_bounds(layout, CENTER)
    x_scale = (right - left) / scan.width
    y_scale = (bottom - top) / scan.height
    trim_left, trim_top, trim_right, trim_bottom = inset
    if min(inset) < 0 or trim_left + trim_right >= scan.width or trim_top + trim_bottom >= scan.height:
        raise ValueError("Artwork inset must leave a non-empty part of the card")
    bounds = (
        left + round(trim_left * x_scale),
        top + round(trim_top * y_scale),
        right - round(trim_right * x_scale),
        bottom - round(trim_bottom * y_scale),
    )
    card_art = scan.crop(
        (trim_left, trim_top, scan.width - trim_right, scan.height - trim_bottom)
    ).resize((bounds[2] - bounds[0], bounds[3] - bounds[1]), Image.Resampling.LANCZOS)
    canvas_size = (layout.width_px, layout.height_px)
    canvas = Image.new("RGB", canvas_size, guide["background"] if guide else (127, 127, 127))
    alpha = Image.new("L", canvas_size, 0)
    if guide:
        draw = ImageDraw.Draw(canvas)
        mask_draw = ImageDraw.Draw(alpha)
        for polygon in guide["polygons"]:
            points = [(left + x * x_scale, top + y * y_scale) for x, y in polygon["points"]]
            draw.polygon(points, fill=polygon["fill"])
        for region in guide.get("fixed_regions", ()):
            points = [(left + x * x_scale, top + y * y_scale) for x, y in region]
            mask_draw.polygon(points, fill=255)
    canvas.paste(card_art, bounds)
    alpha.paste(255, bounds)
    return canvas, alpha


def _read_scan(recipe: dict, scan_path: Path) -> Image.Image:
    verify_file(scan_path, recipe["card"]["sha256"], label="Reference card")
    with Image.open(scan_path) as loaded:
        return Image.alpha_composite(
            Image.new("RGBA", loaded.size, "white"), loaded.convert("RGBA"),
        ).convert("RGB")


def _read_recipe(path: Path) -> dict:
    recipe = yaml.safe_load(path.read_text(encoding="utf-8"))
    if recipe["id"] != poster_asset_slug(recipe["id"]):
        raise ValueError("Extended artwork ID must be a lowercase, filename-safe key")
    return recipe


def _source_layout(recipe: dict) -> PageLayout:
    width, height = latent_canvas_dimensions(LAYOUT_NAME, recipe["generation"]["megapixels"])
    return build_source_layout(LAYOUT_NAME, width_px=width, height_px=height)


def prepare(recipe_path: Path, scan_path: Path, job_dir: Path) -> Path:
    """Create an immutable BinderPokedex render job with a source canvas and mask."""
    recipe = _read_recipe(recipe_path)
    scan = _read_scan(recipe, scan_path)
    layout = _source_layout(recipe)
    generation = recipe["generation"]
    guide = recipe.get("guide")
    job_dir.mkdir(parents=True, exist_ok=False)
    try:
        with TemporaryDirectory() as temporary:
            staging = Path(temporary)
            source, mask = create_outpaint_inputs(
                scan, layout, inset=tuple(recipe["card"]["artwork_inset_px"]), guide=guide,
            )
            source.save(staging / OUTPAINT_NAME)
            mask_input = Image.new("RGBA", source.size)
            mask_input.putalpha(mask)
            mask_input.save(staging / MASK_NAME)

            workflow = build_outpaint_workflow(
                prompt=recipe["prompt"],
                stage_name=OUTPAINT_NAME,
                mask_name=MASK_NAME,
                width=layout.width_px,
                height=layout.height_px,
                seed=generation["seed"],
                unet_name=generation["model"],
                clip_name=generation["encoder"],
                vae_name=generation["vae"],
                steps=generation["steps"],
                filename_prefix=recipe["id"],
            )
            workflow_path = staging / "workflow_api.json"
            _write_json(workflow_path, workflow)
            models = [
                f"{folder}/{generation[key]}={generation[key + '_sha256']}"
                for folder, key in (
                    ("diffusion_models", "model"),
                    ("text_encoders", "encoder"),
                    ("vae", "vae"),
                )
            ]
            job = prepare_job(
                workflow_path, job_dir,
                [f"{staging / name}={name}" for name in (OUTPAINT_NAME, MASK_NAME)],
                models,
            )
            (job_dir / "recipe.sha256").write_text(
                sha256_file(recipe_path) + "\n", encoding="utf-8",
            )
    except Exception:
        rmtree(job_dir)
        raise
    return job


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare_composite(
    recipe_path: Path, scan_path: Path, job_dir: Path, layer_paths: dict[str, Path],
) -> Path:
    """Prepare a native image assembly job from individually reviewed render outputs."""
    recipe = _read_recipe(recipe_path)
    _read_scan(recipe, scan_path)
    records = recipe["render_composition"]
    if "painting" not in records or set(layer_paths) != set(records):
        raise ValueError(f"Composition requires these layers: {', '.join(records)}")
    layout = _source_layout(recipe)
    size = layout.width_px, layout.height_px
    inputs = []
    for name, record in records.items():
        if poster_asset_slug(name) != name:
            raise ValueError(f"Invalid layer name: {name}")
        path = layer_paths[name]
        verify_file(path, record["render_sha256"], label=f"Reviewed layer {name}")
        with Image.open(path) as image:
            if image.size != size:
                raise ValueError(f"Wrong canvas dimensions for layer {name}")
        inputs.append(f"{path}={name}.png")

    workflow = {"1": node("LoadImage", image="painting.png")}
    destination = "1"
    job_dir.mkdir(parents=True, exist_ok=False)
    try:
        with TemporaryDirectory() as temporary:
            staging = Path(temporary)
            for name, record in records.items():
                if name == "painting":
                    continue
                mask = Image.new("L", size)
                draw = ImageDraw.Draw(mask)
                draw.polygon([tuple(p) for p in record["polygon"]], fill=255)
                for cutout in record.get("cutouts", ()):
                    draw.polygon([tuple(p) for p in cutout], fill=0)
                mask = mask.filter(ImageFilter.GaussianBlur(record["feather_px"]))
                mask_input = Image.new("RGBA", size)
                mask_input.putalpha(ImageOps.invert(mask))
                mask_path = staging / f"{name}-mask.png"
                mask_input.save(mask_path)
                inputs.append(f"{mask_path}={mask_path.name}")

                first = len(workflow) + 1
                image_node, mask_node, compose_node = map(str, range(first, first + 3))
                workflow[image_node] = node("LoadImage", image=f"{name}.png")
                workflow[mask_node] = node("LoadImage", image=mask_path.name)
                workflow[compose_node] = node(
                    "ImageCompositeMasked", destination=[destination, 0],
                    source=[image_node, 0], mask=[mask_node, 1], x=0, y=0, resize_source=False,
                )
                destination = compose_node
            workflow[str(len(workflow) + 1)] = node(
                "SaveImage", images=[destination, 0], filename_prefix=recipe["id"],
            )
            path = staging / "workflow_api.json"
            _write_json(path, workflow)
            job = prepare_job(path, job_dir, inputs, [])
            (job_dir / "recipe.sha256").write_text(
                sha256_file(recipe_path) + "\n", encoding="utf-8",
            )
    except Exception:
        rmtree(job_dir)
        raise
    return job


def create_binder_preview(artwork: Image.Image, scan: Image.Image, layout: PageLayout) -> Image.Image:
    """Assemble the eight printable crops, physical gaps and original center scan."""
    preview = Image.new("RGB", artwork.size, "white")
    for row in range(1, layout.rows + 1):
        for column in range(1, layout.columns + 1):
            position = (row, column)
            bounds = card_bounds(layout, position)
            if position == CENTER:
                cell = layout.cell(*CENTER)
                card = scan.resize((cell.width, cell.height), Image.Resampling.LANCZOS)
            else:
                card = artwork.crop(bounds)
            preview.paste(card, bounds)
    return preview


def collect(
    recipe_path: Path, job_dir: Path, scan_path: Path, output_dir: Path,
) -> Path:
    """Verify returned render data and produce a print master and a private preview."""
    recipe_digest = (job_dir / "recipe.sha256").read_text(encoding="utf-8").strip()
    verify_file(recipe_path, recipe_digest, label="Recipe")
    recipe = _read_recipe(recipe_path)
    scan = _read_scan(recipe, scan_path)
    manifest = load_json(job_dir / "job.json")
    run = load_json(job_dir / "run.json")
    if not (job_dir / "comfyui.log").is_file():
        raise ValueError("Returned render has no ComfyUI log")
    if (
        run["workflow_sha256"] != manifest["workflow"]["sha256"]
        or run["inputs"] != manifest["inputs"]
        or run["models"] != manifest["models"]
        or run["comfyui_commit"] != manifest["comfyui_commit"]
    ):
        raise ValueError("Returned run differs from the prepared render job")
    verify_file(job_dir / "workflow_api.json", run["workflow_sha256"], label="Workflow")
    for entry in run["inputs"]:
        relative = safe_relative_path(entry["path"], field="input path")
        verify_file(job_dir / "input" / relative, entry["sha256"], label="Render input")
    output, = run["outputs"]
    artwork_path = job_dir / "output" / safe_relative_path(output["path"], field="output path")
    verify_file(artwork_path, output["sha256"], label="Rendered artwork")
    source_layout = _source_layout(recipe)
    layout = build_print_layout(LAYOUT_NAME, PRINT_DPI)
    bounds = card_bounds(layout, CENTER)
    with Image.open(artwork_path) as loaded:
        if loaded.size != (source_layout.width_px, source_layout.height_px):
            raise ValueError("Render size differs from the prepared canvas")
        artwork = loaded.convert("RGB")
    palette = recipe.get("guide", {}).get("palette_matches")
    if palette:
        artwork = match_palette(artwork, scan.size, source_layout, palette)
    artwork = artwork.resize((layout.width_px, layout.height_px), Image.Resampling.LANCZOS)

    output_dir.mkdir(parents=True, exist_ok=True)
    preview = create_binder_preview(artwork, scan, layout)
    preview.thumbnail((1290, 1780), Image.Resampling.LANCZOS)
    preview.save(output_dir / "preview-with-card.png", optimize=True)
    artwork.paste("white", bounds)
    master = output_dir / "master.png"
    artwork.save(master, dpi=(PRINT_DPI, PRINT_DPI), optimize=True)
    _write_json(output_dir / "provenance.json", {
        "artwork_sha256": sha256_file(master),
        "card": {key: recipe["card"][key] for key in ("id", "url", "sha256")},
        "comfyui_commit": run["comfyui_commit"],
        "device": run["device"],
        "inputs": run["inputs"],
        "models": run["models"],
        "recipe_sha256": recipe_digest,
        "render_sha256": output["sha256"],
        "workflow_sha256": run["workflow_sha256"],
    })
    return master


def export_artwork(
    slug: str, language: str, title: str, master: Path, output_dir: Path,
) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen.canvas import Canvas

    from scripts.pdf.lib.project_notice import PROJECT_URL, build_identity
    from scripts.pdf.lib.rendering.page_renderer import PageRenderer
    from scripts.pdf.lib.rendering.poster_page_renderer import draw_poster_cards

    from .slice_poster import slice_artwork

    layout = build_print_layout(LAYOUT_NAME, PRINT_DPI)
    with Image.open(master) as loaded:
        if loaded.size != (layout.width_px, layout.height_px):
            raise ValueError("Extended artwork master must use the 300 dpi print layout")
        center = loaded.crop(card_bounds(layout, CENTER)).convert("RGB")
        if center.getextrema() != ((255, 255),) * 3:
            raise ValueError("Extended artwork master must leave the middle cell blank")

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{slug}-{language}-a4-cards.pdf"
    with NamedTemporaryFile(dir=output_dir, suffix=".pdf", delete=False) as stream:
        staging = Path(stream.name)
    try:
        with TemporaryDirectory() as tiles:
            cards = slice_artwork(master, LAYOUT_NAME, Path(tiles), skip=frozenset({CENTER}))
            pdf = Canvas(str(staging), pagesize=A4, pageCompression=1, invariant=True, lang=language)
            version, source_ref = build_identity()
            pdf.setTitle(title)
            pdf.setCreator(f"BinderPokedex ({version})")
            pdf.setSubject(f"{PROJECT_URL} | {source_ref}")
            draw_poster_cards(
                pdf, PageRenderer(), cards, (layout.columns, layout.rows),
                include_footer=False, trim_marks=True,
            )
            pdf.showPage()
            pdf.save()
        staging.replace(target)
    finally:
        staging.unlink(missing_ok=True)
    return target


def export_reviewed_artwork(recipe_path: Path, output_dir: Path) -> Path:
    """Verify and export a checked-in Extended Artwork Page."""
    recipe = _read_recipe(recipe_path)
    bundle = ROOT / "assets" / "extended-artwork" / recipe["id"]
    master = bundle / "master.png"
    provenance = load_json(bundle / "provenance.json")
    verify_file(master, provenance["artwork_sha256"], label="Reviewed artwork")
    verify_file(recipe_path, provenance["recipe_sha256"], label="Reviewed recipe")
    return export_artwork(recipe["id"], recipe["language"], recipe["title"], master, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_command = commands.add_parser("prepare", help="Prepare an immutable render job")
    compose_command = commands.add_parser("compose", help="Prepare a job to combine reviewed layers")
    compose_command.add_argument("--layer", action="append", required=True, metavar="NAME=PNG")
    collect_command = commands.add_parser("collect", help="Collect a run for visual review")
    for command in (prepare_command, compose_command, collect_command):
        command.add_argument("--scan", type=Path, required=True)
        command.add_argument("--job-dir", type=Path, required=True)
    collect_command.add_argument("--output-dir", type=Path, required=True)
    export_command = commands.add_parser("export", help="Export eight A4 cards with cutting guides")
    export_command.add_argument(
        "--output-dir", type=Path, default=ROOT / "output" / "extended-artwork",
    )

    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.recipe, args.scan, args.job_dir)
    elif args.command == "compose":
        layers = {}
        for item in args.layer:
            name, separator, path = item.partition("=")
            if not name or not separator or not path or name in layers:
                compose_command.error("--layer must specify a unique NAME=PNG")
            layers[name] = Path(path)
        result = prepare_composite(args.recipe, args.scan, args.job_dir, layers)
    elif args.command == "collect":
        result = collect(args.recipe, args.job_dir, args.scan, args.output_dir)
    else:
        result = export_reviewed_artwork(args.recipe, args.output_dir)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
