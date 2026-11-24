"""Build and describe the standalone cutting PDFs shipped with a release."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import yaml


OUTPUT = Path("output/release-artwork")
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ArtworkPDF:
    scope: str
    language: str
    title: str
    recipe: Path | None = None

    @property
    def name(self) -> str:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.scope):
            raise ValueError(f"Invalid standalone artwork ID: {self.scope!r}")
        if not re.fullmatch(r"[a-z]{2}(?:_[a-z]+)?", self.language):
            raise ValueError(f"Invalid standalone artwork language: {self.language!r}")
        return f"{self.scope}-{self.language}-a4-cards.pdf"


def artwork_pdf_specs(project_dir: Path) -> list[ArtworkPDF]:
    """Discover standalone collection manifests and Extended Artwork recipes."""
    specs = []
    for path in sorted((project_dir / "config/posters").glob("*/poster.yaml")):
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        collection = manifest.get("source", {}).get("collection")
        if collection is not None:
            for language, title in sorted(collection["title"].items()):
                specs.append(ArtworkPDF(path.parent.name, language, title))
    for path in sorted((project_dir / "config/extended-artwork").glob("*.yaml")):
        recipe = yaml.safe_load(path.read_text(encoding="utf-8"))
        specs.append(ArtworkPDF(recipe["id"], recipe["language"], recipe["title"], path))
    if len({spec.name for spec in specs}) != len(specs):
        raise ValueError("Duplicate standalone artwork release filename")
    return specs


def artwork_pdf_records(project_dir: Path) -> list[dict]:
    """Require exactly the expected files and record their sizes and hashes."""
    specs = artwork_pdf_specs(project_dir)
    output_dir = project_dir / OUTPUT
    actual = {p.name for p in output_dir.glob("*.pdf") if p.is_file()}
    expected = {spec.name for spec in specs}
    if actual != expected:
        raise ValueError(
            f"Unexpected standalone artwork PDF set. Missing: {sorted(expected - actual)}. "
            f"Extra: {sorted(actual - expected)}."
        )

    records = []
    for spec in specs:
        path = output_dir / spec.name
        with path.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise ValueError(f"Invalid standalone artwork PDF: {spec.name}")
            stream.seek(0)
            digest = sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        records.append({
            "name": spec.name,
            "language": spec.language,
            "title": spec.title,
            "size_bytes": path.stat().st_size,
            "sha256": digest.hexdigest(),
        })
    return records


def main() -> int:
    from scripts.pdf.generate_artwork_pdf import export_artwork as export_collection
    from scripts.poster_assets.extended_artwork import export_reviewed_artwork

    specs = artwork_pdf_specs(ROOT)
    output_dir = ROOT / OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir.parent) as temporary:
        rendered = []
        for spec in specs:
            if spec.recipe is None:
                pdf = export_collection(spec.scope, spec.language, Path(temporary), page_mode="cards")
            else:
                pdf = export_reviewed_artwork(spec.recipe, Path(temporary))
            if pdf.name != spec.name:
                raise ValueError(f"Unexpected export name for {spec.scope}: {pdf.name}")
            rendered.append(pdf)
        for pdf in rendered:
            pdf.replace(output_dir / pdf.name)
    print(f"Built {len(artwork_pdf_records(ROOT))} standalone cutting PDFs in {OUTPUT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
