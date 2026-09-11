from unittest.mock import MagicMock

import pytest

from scripts.pdf import generate_pdf
from scripts.pdf.lib.generation_options import (
    pdf_output_filename,
    prepare_variant_data,
    validate_poster_page_mode,
)
from scripts.pdf.lib.variant_pdf_generator import VariantPDFGenerator


def _card(card_id: int) -> dict:
    return {
        "pokemon_id": card_id,
        "name": {"en": f"Pokemon {card_id}"},
        "image_url": f"https://example.test/{card_id}.png",
    }


def test_no_options_preserve_original_mapping():
    source = {"sections": {"all": {"cards": [_card(1)]}}}

    assert prepare_variant_data(source) is source


def test_language_filter_keeps_only_observed_cards_without_mutating_source():
    source = {
        "sections": {
            "all": {
                "cards": [
                    {
                        **_card(1),
                        "available_languages": ["de", "en"],
                    },
                    {
                        **_card(2),
                        "available_languages": ["en"],
                    },
                    _card(3),
                ]
            }
        }
    }

    filtered = generate_pdf.filter_variant_data_for_language(source, "de")

    assert [
        card["pokemon_id"]
        for card in filtered["sections"]["all"]["cards"]
    ] == [1, 3]
    assert [
        card["pokemon_id"]
        for card in source["sections"]["all"]["cards"]
    ] == [1, 2, 3]


def test_variant_pdf_generation_filters_language_specific_cards(
    monkeypatch,
    tmp_path,
):
    source = {
        "set_id": "SVP",
        "sections": {
            "all": {
                "cards": [
                    {
                        **_card(1),
                        "available_languages": ["de", "en"],
                    },
                    {
                        **_card(2),
                        "available_languages": ["en"],
                    },
                ]
            }
        },
    }
    generator = MagicMock()
    generator.generate.return_value = True
    generator_factory = MagicMock(return_value=generator)
    monkeypatch.setattr(generate_pdf, "VariantPDFGenerator", generator_factory)

    result = generate_pdf._generate_variant_pdf(
        variant_data=source,
        language="de",
        output_dir=tmp_path,
        script_dir=tmp_path,
        scope_name="SVP",
    )

    prepared = generator_factory.call_args.kwargs["variant_data"]
    assert result is True
    assert [
        card["pokemon_id"]
        for card in prepared["sections"]["all"]["cards"]
    ] == [1]
    assert generator_factory.call_args.kwargs["poster_source_data"] is source


def test_pdf_output_filename_keeps_diagnostic_runs_separate():
    assert pdf_output_filename("Base1", "de") == "Base1_DE.pdf"
    assert (
        pdf_output_filename("Base1", "de", test_mode=True)
        == "Base1_DE_TEST.pdf"
    )
    assert (
        pdf_output_filename("Base1", "de", skip_images=True)
        == "Base1_DE_NO_IMAGES.pdf"
    )
    assert (
        pdf_output_filename("Base1", "de", skip_poster=True)
        == "Base1_DE_NO_POSTER.pdf"
    )
    assert (
        pdf_output_filename(
            "Base1",
            "de",
            poster_page_mode="full-page",
        )
        == "Base1_DE_POSTER_FULL_PAGE.pdf"
    )
    assert (
        pdf_output_filename(
            "Base1",
            "de",
            skip_images=True,
            skip_poster=True,
            test_mode=True,
        )
        == "Base1_DE_TEST_NO_IMAGES_NO_POSTER.pdf"
    )


def test_poster_page_mode_validation_rejects_unknown_values():
    with pytest.raises(
        ValueError,
        match="poster_page_mode must be one of cards, full-page",
    ):
        validate_poster_page_mode("spread")


def test_test_mode_limits_cards_globally_in_render_order():
    source = {
        "set_id": "Example",
        "sections": {
            "second": {
                "section_order": 2,
                "cards": [_card(card_id) for card_id in range(7, 13)],
            },
            "first": {
                "section_order": 1,
                "cards": [_card(card_id) for card_id in range(1, 7)],
            },
            "third": {
                "section_order": 3,
                "cards": [_card(card_id) for card_id in range(13, 19)],
            },
        },
    }

    prepared = prepare_variant_data(source, test_mode=True)

    assert list(prepared["sections"]) == ["first", "second"]
    assert [
        card["pokemon_id"]
        for section in prepared["sections"].values()
        for card in section["cards"]
    ] == list(range(1, 10))
    assert len(source["sections"]["second"]["cards"]) == 6
    assert list(source["sections"]) == ["second", "first", "third"]


def test_skip_images_removes_only_remote_card_sources():
    source = {
        "logo_urls": {"en": "https://example.test/logo.png"},
        "sections": {
            "all": {
                "featured_elements": [
                    {"local_image_path": "data/featured-card.png"}
                ],
                "cards": [
                    {
                        **_card(1),
                        "image_path": "data/local-card.png",
                    }
                ],
            }
        },
    }

    prepared = prepare_variant_data(source, skip_images=True)
    card = prepared["sections"]["all"]["cards"][0]

    assert "image_url" not in card
    assert card["image_path"] == "data/local-card.png"
    assert prepared["logo_urls"] == source["logo_urls"]
    assert prepared["sections"]["all"]["featured_elements"] == [
        {"local_image_path": "data/featured-card.png"}
    ]
    assert "image_url" in source["sections"]["all"]["cards"][0]


def test_skip_images_removes_remote_cover_image_tags_only_from_copy():
    source = {
        "sections": {
            "all": {
                "title": {"en": "Set title"},
                "subtitle": {
                    "en": (
                        "[image]https://example.test/logo.png[/image]"
                    ),
                    "de": (
                        "Sammlung "
                        "[image]https://example.test/logo-de.png[/image]"
                    ),
                },
                "description": {
                    "en": "Keeps local [image]images/logo.png[/image]",
                },
                "cards": [_card(1)],
            }
        }
    }

    prepared = prepare_variant_data(source, skip_images=True)
    section = prepared["sections"]["all"]

    assert section["subtitle"] == {"en": "", "de": "Sammlung"}
    assert section["description"] == source["sections"]["all"][
        "description"
    ]
    assert "https://example.test/logo.png" in source["sections"]["all"][
        "subtitle"
    ]["en"]


def test_options_support_legacy_flat_pokemon_data():
    source = {"pokemon": [_card(card_id) for card_id in range(1, 13)]}

    prepared = prepare_variant_data(
        source,
        skip_images=True,
        test_mode=True,
    )

    assert len(prepared["pokemon"]) == 9
    assert all("image_url" not in card for card in prepared["pokemon"])
    assert len(source["pokemon"]) == 12


def test_variant_pdf_generation_applies_cli_options(monkeypatch, tmp_path):
    source = {
        "set_id": "Example",
        "sections": {
            "all": {
                "cards": [_card(card_id) for card_id in range(1, 13)],
            }
        },
    }
    generator = MagicMock()
    generator.generate.return_value = True
    generator_factory = MagicMock(return_value=generator)
    monkeypatch.setattr(generate_pdf, "VariantPDFGenerator", generator_factory)

    result = generate_pdf._generate_variant_pdf(
        variant_data=source,
        language="de",
        output_dir=tmp_path,
        script_dir=tmp_path,
        skip_images=True,
        skip_poster=True,
        test_mode=True,
        scope_name="Example",
    )

    prepared = generator_factory.call_args.kwargs["variant_data"]
    assert result is True
    assert generator_factory.call_args.kwargs["output_file"] == (
        tmp_path / "Example_DE_TEST_NO_IMAGES_NO_POSTER.pdf"
    )
    assert generator_factory.call_args.kwargs["include_poster"] is False
    assert generator_factory.call_args.kwargs["poster_page_mode"] == "cards"
    assert generator_factory.call_args.kwargs["scope_name"] == "Example"
    assert generator_factory.call_args.kwargs["poster_source_data"] is source
    assert len(prepared["sections"]["all"]["cards"]) == 9
    assert all(
        "image_url" not in card
        for card in prepared["sections"]["all"]["cards"]
    )
    generator.generate.assert_called_once_with()


def test_variant_pdf_generation_propagates_full_page_mode(
    monkeypatch,
    tmp_path,
):
    source = {
        "set_id": "Example",
        "sections": {"all": {"cards": [_card(1)]}},
    }
    generator = MagicMock()
    generator.generate.return_value = True
    generator_factory = MagicMock(return_value=generator)
    monkeypatch.setattr(generate_pdf, "VariantPDFGenerator", generator_factory)

    result = generate_pdf._generate_variant_pdf(
        variant_data=source,
        language="en",
        output_dir=tmp_path,
        script_dir=tmp_path,
        poster_page_mode="full-page",
        scope_name="Example",
    )

    assert result is True
    assert generator_factory.call_args.kwargs["output_file"] == (
        tmp_path / "Example_EN_POSTER_FULL_PAGE.pdf"
    )
    assert (
        generator_factory.call_args.kwargs["poster_page_mode"]
        == "full-page"
    )


def test_legacy_flat_variant_normalizes_pokemon_to_renderable_cards():
    generator = VariantPDFGenerator.__new__(VariantPDFGenerator)
    generator.variant_data = {
        "variant_name": "Legacy Collection",
        "pokemon": [{"pokemon_id": 1}, {"pokemon_id": 4}],
    }
    generator.pokemon_list = generator.variant_data["pokemon"]

    sections = generator._sections_for_rendering()

    assert len(sections) == 1
    assert sections[0]["title"] == "Legacy Collection"
    assert sections[0]["cards"] == generator.pokemon_list


def test_scope_generation_counts_false_renderer_result_as_failure(
    monkeypatch,
    tmp_path,
):
    scope_data = {
        "set_id": "Example",
        "available_languages": ["de"],
        "sections": {"all": {"cards": [_card(1)]}},
    }
    scope_file = tmp_path / "Example.json"
    scope_file.write_text(__import__("json").dumps(scope_data), encoding="utf-8")
    monkeypatch.setattr(generate_pdf, "_generate_variant_pdf", lambda **_kwargs: False)

    result = generate_pdf.generate_scope_pdf(
        scope_name="Example",
        scope_file=scope_file,
        languages=["de"],
        output_dir=tmp_path / "output",
        script_dir=tmp_path,
    )

    assert result == 1
