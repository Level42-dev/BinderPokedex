"""Render a localized poster as physical cards or one continuous page."""
from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm

try:
    from ..generation_options import validate_poster_page_mode
except ImportError:  # Compatibility with legacy direct lib imports.
    from generation_options import validate_poster_page_mode
from .page_renderer import PageRenderer


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[4]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.poster_assets.finalize_comfyui_poster import finalize  # noqa: E402
from scripts.poster_assets.layout import (  # noqa: E402
    DEFAULT_LAYOUT_NAME,
    physical_layout_size_mm,
    pdf_page_hint,
    resolve_layout_name,
)
from scripts.poster_assets.poster_io import (  # noqa: E402
    POSTER_ASSETS,
    PosterBundle,
    poster_asset_slug,
    poster_bundles_for_scope,
    select_poster_scope_data,
)
from scripts.poster_assets.slice_poster import slice_poster  # noqa: E402


def card_page_assignments(
    poster_grid: tuple[int, int],
    page_grid: tuple[int, int],
) -> list[list[tuple[int, int]]]:
    """Map row-major poster crops to their physical positions on PDF pages.

    Smaller posters preserve their row and column coordinates in the upper-left
    page slots, so a 2x2 artwork leaves the A4 grid's right column and bottom
    row empty. A poster that is only wider than the printable page is split
    into vertical column bands. This keeps the first three columns of a 4x3
    poster assembled on page one and places its fourth column vertically in
    page two's first column. Other oversized layouts retain sequential
    pagination.
    """
    poster_columns, poster_rows = poster_grid
    page_columns, page_rows = page_grid
    if min(poster_columns, poster_rows, page_columns, page_rows) <= 0:
        raise ValueError("Poster and PDF page grids must be positive")

    if poster_columns <= page_columns and poster_rows <= page_rows:
        return [
            [
                (
                    row * poster_columns + column,
                    row * page_columns + column,
                )
                for row in range(poster_rows)
                for column in range(poster_columns)
            ]
        ]

    if poster_columns > page_columns and poster_rows <= page_rows:
        pages: list[list[tuple[int, int]]] = []
        for first_column in range(0, poster_columns, page_columns):
            last_column = min(first_column + page_columns, poster_columns)
            page: list[tuple[int, int]] = []
            for row in range(poster_rows):
                for column in range(first_column, last_column):
                    source_index = row * poster_columns + column
                    page_index = row * page_columns + column - first_column
                    page.append((source_index, page_index))
            pages.append(page)
        return pages

    expected = poster_columns * poster_rows
    cards_per_page = page_columns * page_rows
    return [
        [
            (source_index, page_index)
            for page_index, source_index in enumerate(
                range(page_start, min(page_start + cards_per_page, expected))
            )
        ]
        for page_start in range(0, expected, cards_per_page)
    ]


class PosterPageRenderer:
    """Prepare and draw an optional scope poster page."""

    def __init__(
        self,
        bundle: PosterBundle,
        language: str,
        artwork_path: Path,
        layout_name: str = DEFAULT_LAYOUT_NAME,
        page_mode: str = "cards",
    ):
        validate_poster_page_mode(page_mode)
        self.scope = bundle.asset_key
        self.section_id = bundle.section_id
        self.poster_id = bundle.poster_id
        self.language = language
        self.artwork_path = artwork_path
        self.insertion = bundle.insertion
        self.layout_name = layout_name
        self.page_mode = page_mode
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self._localized_path: Path | None = None
        self._card_paths: list[Path] | None = None

    @classmethod
    def from_variant_data(
        cls,
        variant_data: dict,
        language: str,
        *,
        include_poster: bool = True,
        page_mode: str = "cards",
    ) -> "PosterPageRenderer | None":
        if not include_poster:
            return None
        scope = variant_data.get("set_id") or variant_data.get("scope")
        if not scope:
            return None
        collection = PosterPageCollection.from_scope(
            str(scope),
            variant_data,
            language,
            include_poster=include_poster,
            page_mode=page_mode,
        )
        if len(collection.renderers) > 1:
            collection.cleanup()
            raise ValueError(
                "from_variant_data() cannot return multiple poster renderers; "
                "use PosterPageCollection.from_scope()"
            )
        return collection.renderers[0] if collection.renderers else None

    @classmethod
    def from_bundle(
        cls,
        bundle: PosterBundle,
        language: str,
        *,
        page_mode: str = "cards",
    ) -> "PosterPageRenderer":
        artwork_path = bundle.asset_dir / bundle.artwork_file
        if not artwork_path.is_file():
            raise FileNotFoundError(f"Poster PDF artwork not found: {artwork_path}")
        layout_name = bundle.manifest.get("layout", {}).get(
            "name",
            DEFAULT_LAYOUT_NAME,
        )
        resolve_layout_name(layout_name)
        return cls(
            bundle,
            language,
            artwork_path,
            layout_name,
            page_mode=page_mode,
        )

    def _prepare_localized_poster(self) -> Path:
        if self._localized_path is not None:
            return self._localized_path
        if self._temp_dir is None:
            temp_root = PROJECT_ROOT / "tmp" / "pdfs"
            temp_root.mkdir(parents=True, exist_ok=True)
            self._temp_dir = tempfile.TemporaryDirectory(
                prefix=(
                    f"poster-{poster_asset_slug(self.scope)}-"
                    f"{self.language}-"
                ),
                dir=temp_root,
            )
        self._localized_path = (
            Path(self._temp_dir.name)
            / f"{poster_asset_slug(self.scope)}_{self.language}.png"
        )
        finalize(
            self.scope,
            self.artwork_path,
            self._localized_path,
            self.language,
        )
        return self._localized_path

    def _prepare_cards(self) -> list[Path]:
        if self._card_paths is not None:
            return self._card_paths
        localized_poster = self._prepare_localized_poster()
        self._card_paths = slice_poster(
            self.scope,
            localized_poster,
            localized_poster.parent / "cards",
        )
        return self._card_paths

    def render_page(self, canvas_obj, page_renderer: PageRenderer) -> None:
        """Render one poster, adding page breaks when its cards exceed A4."""
        if self.page_mode == "full-page":
            self._render_full_page(canvas_obj, page_renderer)
            return
        card_paths = self._prepare_cards()
        layout = resolve_layout_name(self.layout_name)
        poster_grid = (int(layout["columns"]), int(layout["rows"]))
        expected = poster_grid[0] * poster_grid[1]
        if len(card_paths) != expected:
            raise ValueError(
                f"Poster layout produced {len(card_paths)} cards, expected {expected}"
            )
        page_grid = (
            int(page_renderer.style.CARDS_PER_ROW),
            int(page_renderer.style.CARDS_PER_COLUMN),
        )
        cards_per_page = int(page_renderer.style.CARDS_PER_PAGE)
        if cards_per_page <= 0:
            raise ValueError("PDF page renderer must accept at least one card")
        if page_grid[0] * page_grid[1] != cards_per_page:
            raise ValueError("PDF page card grid does not match CARDS_PER_PAGE")

        pages = card_page_assignments(poster_grid, page_grid)
        for page_number, page_assignments in enumerate(pages):
            page_renderer.create_page(canvas_obj)
            for source_index, page_index in page_assignments:
                card_path = card_paths[source_index]
                x, y = page_renderer.calculate_card_position(page_index)
                canvas_obj.drawImage(
                    ImageReader(str(card_path)),
                    x,
                    y,
                    width=page_renderer.style.CARD_WIDTH,
                    height=page_renderer.style.CARD_HEIGHT,
                    preserveAspectRatio=False,
                    mask="auto",
                )
            page_renderer.draw_cutting_guides(canvas_obj)
            page_renderer.add_footer(canvas_obj)
            if page_number + 1 < len(pages):
                canvas_obj.showPage()

    def _render_full_page(
        self,
        canvas_obj,
        page_renderer: PageRenderer,
    ) -> None:
        """Draw one continuous poster at its exact physical layout size."""
        width_mm, height_mm = physical_layout_size_mm(self.layout_name)
        width = width_mm * mm
        height = height_mm * mm
        if (
            width > page_renderer.style.PAGE_WIDTH
            or height > page_renderer.style.PAGE_HEIGHT
        ):
            paper, orientation = pdf_page_hint(self.layout_name)
            raise ValueError(
                f"Poster layout {self.layout_name} needs a {paper} "
                f"{orientation} full-page renderer"
            )
        page_renderer.create_page(canvas_obj)
        x = (page_renderer.style.PAGE_WIDTH - width) / 2
        y = (page_renderer.style.PAGE_HEIGHT - height) / 2
        canvas_obj.drawImage(
            ImageReader(str(self._prepare_localized_poster())),
            x,
            y,
            width=width,
            height=height,
            preserveAspectRatio=False,
            mask="auto",
        )
        page_renderer.add_footer(canvas_obj)

    def cleanup(self) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None
        self._localized_path = None
        self._card_paths = None


class PosterPageCollection:
    """Own and route every enabled poster page for one PDF scope."""

    def __init__(self, renderers: list[PosterPageRenderer] | None = None):
        self.renderers = renderers or []

    @classmethod
    def from_scope(
        cls,
        scope: str | None,
        variant_data: dict,
        language: str,
        *,
        include_poster: bool = True,
        page_mode: str = "cards",
    ) -> "PosterPageCollection":
        validate_poster_page_mode(page_mode)
        if not include_poster or not scope:
            return cls()
        bundles = poster_bundles_for_scope(
            str(scope),
            poster_assets=POSTER_ASSETS,
        )
        renderers: list[PosterPageRenderer] = []
        try:
            for bundle in bundles:
                # Validate every binding against the complete source data even
                # while disabled; --skip-poster intentionally bypasses this.
                select_poster_scope_data(
                    bundle,
                    variant_data,
                    source_name=f"PDF scope {scope}",
                )
                if bundle.pdf_enabled:
                    renderers.append(
                        PosterPageRenderer.from_bundle(
                            bundle,
                            language,
                            page_mode=page_mode,
                        )
                    )
        except Exception:
            for renderer in renderers:
                renderer.cleanup()
            raise
        return cls(renderers)

    def for_section(
        self,
        section_id: str | None,
        section_index: int,
    ) -> list[PosterPageRenderer]:
        """Return configured pages in routing order for the rendered section."""
        return [
            renderer
            for renderer in self.renderers
            if (
                renderer.insertion == "after_first_section_cover"
                and section_index == 0
            )
            or (
                renderer.insertion == "after_section_cover"
                and renderer.section_id == section_id
            )
        ]

    def cleanup(self) -> None:
        for renderer in self.renderers:
            renderer.cleanup()
