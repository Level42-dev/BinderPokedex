"""Check provenance in the files readers actually download and print."""

import pytest
from pypdf import PdfReader

from scripts.pdf.lib import pdf_generator
from scripts.pdf.lib.variant_pdf_generator import VariantPDFGenerator


@pytest.mark.parametrize("language", ["de", "en", "ja"])
@pytest.mark.parametrize("generator_kind", ["legacy", "variant"])
def test_generated_pdf_preserves_cards_and_includes_printable_notice(
    tmp_path, monkeypatch, language, generator_kind
):
    monkeypatch.setenv("BINDER_POKEDEX_BUILD_VERSION", "test-release")
    monkeypatch.setenv("BINDER_POKEDEX_BUILD_REF", "a" * 40)
    pokemon = [{"name": "Sample", "types": ["normal"]}]
    if generator_kind == "legacy":
        monkeypatch.setattr(pdf_generator, "OUTPUT_DIR", tmp_path)
        generator = pdf_generator.PDFGenerator(language, 1)
        path = generator.generate(pokemon)
    else:
        path = tmp_path / f"sample-{language}.pdf"
        generator = VariantPDFGenerator(
            {"name": "Sample collection", "pokemon": pokemon},
            language,
            path,
            include_poster=False,
        )
        assert generator.generate()

    pdf = PdfReader(path)
    assert len(pdf.pages) == 3  # Cover, original card sheet, printable notice.
    assert "Sample" in pdf.pages[1].extract_text()
    for page in pdf.pages:
        assert "github.com/Level42-dev/BinderPokedex" in page.extract_text()
    notice = pdf.pages[-1].extract_text()
    for expected in (
        "Björn Teichmann", "BinderPokedex Contributors", "CC BY-NC 4.0", "third-party",
        "test-release", "a" * 12, "creativecommons.org/licenses/by-nc/4.0/",
    ):
        assert expected in notice
    assert "github.com/Level42-dev/BinderPokedex" in pdf.metadata.subject
    if generator_kind == "legacy":
        assert generator.page_count == len(pdf.pages)
