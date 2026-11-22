"""Export a standalone collection using the BinderPokedex poster pipeline."""
from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from scripts.pdf.lib.generation_options import POSTER_PAGE_MODES
from scripts.pdf.lib.project_notice import PROJECT_URL, build_identity
from scripts.pdf.lib.rendering.page_renderer import PageRenderer
from scripts.pdf.lib.rendering.poster_page_renderer import PosterPageRenderer
from scripts.poster_assets.finalize_comfyui_poster import (
    SUPPORTED_LANGUAGES,
    readable_overlay_text,
    resolved_title_text,
)
from scripts.poster_assets.layout import DEFAULT_LAYOUT_NAME
from scripts.poster_assets.poster_io import load_poster_scope_data, poster_asset_slug, poster_bundle
from scripts.poster_assets.validate_promoted_poster import validate


ROOT = Path(__file__).resolve().parents[2]


def export_artwork(
    scope: str,
    language: str,
    output_dir: Path,
    *,
    candidate: Path | None = None,
    page_mode: str = "full-page",
) -> Path:
    bundle = poster_bundle(scope)
    scope_data = load_poster_scope_data(bundle)
    if "collection" not in bundle.manifest.get("source", {}):
        raise ValueError(f"{scope} is not a standalone collection poster")
    title = readable_overlay_text(resolved_title_text(scope_data, language))

    if candidate is None:
        result = validate(bundle)
        if result["overlay_fingerprint_current"] is not True:
            raise ValueError(f"{scope} has no current promoted title overlay")
        renderer = PosterPageRenderer.from_bundle(bundle, language, page_mode=page_mode)
    else:
        if not candidate.is_file():
            raise FileNotFoundError(f"Poster artwork not found: {candidate}")
        layout_name = bundle.manifest.get("layout", {}).get("name", DEFAULT_LAYOUT_NAME)
        renderer = PosterPageRenderer(
            bundle, language, candidate, layout_name, page_mode=page_mode,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "-cards" if page_mode == "cards" else ""
    destination = output_dir / f"{poster_asset_slug(scope)}-{language}-a4{suffix}.pdf"
    with NamedTemporaryFile(dir=output_dir, suffix=".pdf", delete=False) as stream:
        staging = Path(stream.name)
    try:
        pdf = Canvas(
            str(staging), pagesize=A4, pageCompression=1,
            invariant=True, lang=language.replace("_", "-"),
        )
        version, source_ref = build_identity()
        pdf.setTitle(title)
        pdf.setCreator(f"BinderPokedex ({version})")
        pdf.setSubject(f"{PROJECT_URL} | {source_ref}")
        renderer.render_page(pdf, PageRenderer(), include_footer=False)
        pdf.showPage()
        pdf.save()
        staging.replace(destination)
    finally:
        renderer.cleanup()
        staging.unlink(missing_ok=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True, help="Standalone poster scope")
    parser.add_argument("--language", choices=SUPPORTED_LANGUAGES, default="en")
    parser.add_argument("--poster-page-mode", choices=POSTER_PAGE_MODES, default="full-page")
    parser.add_argument("--artwork", type=Path, help="Text-free candidate image for a local proof")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output" / "artwork")
    args = parser.parse_args()
    try:
        print(export_artwork(
            args.scope, args.language, args.output_dir,
            candidate=args.artwork, page_mode=args.poster_page_mode,
        ))
    except (OSError, ValueError, yaml.YAMLError) as error:
        parser.exit(1, f"Artwork export failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
