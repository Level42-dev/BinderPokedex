from __future__ import annotations

import copy
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from scripts.poster_assets.poster_subject import PosterSubject


def _grounding():
    return importlib.import_module("scripts.poster_assets.grounding")


def _region(
    subject_key: str = "pokeapi:official-artwork:25",
    *,
    polygon: list[list[float]] | None = None,
    anchors: list[list[float]] | None = None,
) -> dict:
    return {
        "subject_key": subject_key,
        "contact": "grounded",
        "polygon": polygon
        or [[0.40, 0.70], [0.60, 0.70], [0.60, 0.90], [0.40, 0.90]],
        "anchors": anchors or [[0.50, 0.85]],
    }


def _manifest(*regions: dict, feather_ratio: float = 0.02) -> dict:
    return {
        "artwork": {
            "identity_lock": {
                "grounding": {
                    "schema_version": 1,
                    "prompt": "Blend only the explicitly approved ground.",
                    "feather_ratio": feather_ratio,
                    "regions": list(regions) or [_region()],
                }
            }
        }
    }


def _placement(
    pokemon_id: int = 25,
    *,
    image: Image.Image | None = None,
    x: int = 40,
    y: int = 70,
    poster_subject: dict | None = None,
) -> dict:
    item = {"pokemon_id": pokemon_id}
    if poster_subject is not None:
        item["poster_subject"] = poster_subject
    if image is None:
        image = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
        image.putpixel((10, 10), (255, 255, 255, 1))
    return {
        "item": item,
        "image": image,
        "x": x,
        "y": y,
        "cell": SimpleNamespace(x=0, y=0, width=100, height=100),
    }


def _save(path: Path, image: Image.Image) -> Path:
    image.save(path, format="PNG")
    return path


def test_grounding_config_returns_a_normalized_explicit_contract():
    config = _grounding().grounding_config(_manifest(_region()))

    assert config == {
        "schema_version": 1,
        "prompt": "Blend only the explicitly approved ground.",
        "feather_ratio": 0.02,
        "regions": [
            {
                "subject_key": "pokeapi:official-artwork:25",
                "contact": "grounded",
                "polygon": [
                    [0.4, 0.7],
                    [0.6, 0.7],
                    [0.6, 0.9],
                    [0.4, 0.9],
                ],
                "anchors": [[0.5, 0.85]],
            }
        ],
    }


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda value: value.update(extra=True), "unknown"),
        (lambda value: value.update(schema_version=2), "schema_version"),
        (lambda value: value.update(prompt="  "), "prompt"),
        (lambda value: value.update(feather_ratio=True), "feather_ratio"),
        (lambda value: value.update(feather_ratio=float("nan")), "feather_ratio"),
        (lambda value: value.update(feather_ratio=0.021), "feather_ratio"),
        (lambda value: value.update(regions=[]), "regions"),
        (lambda value: value["regions"][0].update(extra=True), "unknown"),
        (lambda value: value["regions"][0].update(subject_key=""), "subject_key"),
        (lambda value: value["regions"][0].update(contact="flying"), "contact"),
        (
            lambda value: value["regions"][0].update(
                polygon=[[0.1, 0.1], [0.2, 0.2]]
            ),
            "polygon",
        ),
        (
            lambda value: value["regions"][0].update(
                polygon=[[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]]
            ),
            "degenerate",
        ),
        (
            lambda value: value["regions"][0].update(
                polygon=[[False, 0.1], [0.2, 0.1], [0.2, 0.2]]
            ),
            "coordinate",
        ),
        (
            lambda value: value["regions"][0].update(
                polygon=[[0.1, 0.1], [1.1, 0.1], [0.2, 0.2]]
            ),
            "range",
        ),
        (lambda value: value["regions"][0].update(anchors=[]), "anchors"),
        (
            lambda value: value["regions"][0].update(anchors=[[0.2, 0.2]]),
            "inside",
        ),
    ],
)
def test_grounding_config_rejects_invalid_or_ambiguous_values(mutate, match):
    raw = copy.deepcopy(_manifest()["artwork"]["identity_lock"]["grounding"])
    mutate(raw)
    manifest = {"artwork": {"identity_lock": {"grounding": raw}}}

    with pytest.raises(ValueError, match=match):
        _grounding().grounding_config(manifest)


def test_grounding_config_rejects_duplicate_subject_regions():
    with pytest.raises(ValueError, match="Duplicate"):
        _grounding().grounding_config(_manifest(_region(), _region()))


def test_build_masks_use_inverse_alpha_and_exclude_every_visible_source_pixel(
    tmp_path: Path,
):
    source = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    source.putpixel((10, 10), (255, 0, 0, 1))

    record = _grounding().build_grounding_masks(
        100,
        100,
        [_placement(image=source)],
        _manifest(),
        tmp_path,
    )

    feather = Image.open(tmp_path / "grounding_mask.png").convert("RGBA")
    sampling = Image.open(tmp_path / "grounding_sampling_mask.png").convert(
        "RGBA"
    )
    # ComfyUI's LoadImage mask output is inverse alpha: transparent is editable.
    assert feather.getpixel((50, 80)) == (0, 0, 0, 255)
    assert sampling.getpixel((50, 80)) == (0, 0, 0, 255)
    assert feather.getpixel((20, 20)) == (0, 0, 0, 255)
    assert sampling.getpixel((20, 20)) == (0, 0, 0, 255)
    assert 0 < 255 - feather.getpixel((45, 80))[3] <= 255
    assert sampling.getpixel((45, 80))[3] == 0
    # Blur must stay clipped to the hand-approved polygon, never expanding it.
    assert feather.getpixel((39, 80))[3] == 255
    assert sampling.getpixel((39, 80))[3] == 255

    metadata = json.loads((tmp_path / "grounding_mask.json").read_text())
    assert record == metadata
    assert metadata["dimensions"] == {"width": 100, "height": 100}
    assert metadata["counts"]["source_visible_pixels"] == 1
    assert metadata["anchor_pixels"] == [
        {
            "subject_key": "pokeapi:official-artwork:25",
            "pixels": [[50, 85]],
        }
    ]
    for key, filename in (
        ("grounding_mask_sha256", "grounding_mask.png"),
        ("grounding_sampling_mask_sha256", "grounding_sampling_mask.png"),
    ):
        assert metadata[key] == hashlib.sha256(
            (tmp_path / filename).read_bytes()
        ).hexdigest()


def test_positive_feather_starts_at_zero_and_rises_inward_without_a_seam(
    tmp_path: Path,
):
    source = Image.new("RGBA", (21, 21), (0, 0, 0, 0))
    source.putpixel((10, 10), (255, 0, 0, 1))
    _grounding().build_grounding_masks(
        100,
        100,
        [_placement(image=source)],
        _manifest(feather_ratio=0.02),
        tmp_path,
    )

    mask = Image.open(tmp_path / "grounding_mask.png").convert("RGBA")
    # A two-pixel inward ramp is hand-derived as 0, 128, 255 edit weight.
    edit_weights = [255 - mask.getpixel((x, 80))[3] for x in (40, 41, 42)]
    assert edit_weights == [0, 128, 255]
    assert edit_weights == sorted(edit_weights)
    # The alpha=1 source pixel stays protected even in the full-weight interior.
    assert 255 - mask.getpixel((50, 80))[3] == 0


def test_zero_feather_uses_the_binary_sampling_mask(tmp_path: Path):
    _grounding().build_grounding_masks(
        100,
        100,
        [_placement()],
        _manifest(feather_ratio=0),
        tmp_path,
    )

    feather = Image.open(tmp_path / "grounding_mask.png").convert("RGBA")
    sampling = Image.open(tmp_path / "grounding_sampling_mask.png").convert(
        "RGBA"
    )
    assert feather.tobytes() == sampling.tobytes()


def test_build_masks_resolves_exact_form_subject_identity(tmp_path: Path):
    subject = PosterSubject(6, 10034)
    region = _region(subject.subject_key)
    record = _grounding().build_grounding_masks(
        100,
        100,
        [
            _placement(
                6,
                poster_subject=subject.as_mapping(),
            )
        ],
        _manifest(region),
        tmp_path,
    )

    assert record["source_identities"] == [subject.as_mapping()]


def test_build_masks_rejects_missing_and_unmatched_subject_regions(tmp_path: Path):
    placements = [_placement()]
    with pytest.raises(ValueError, match="do not match"):
        _grounding().build_grounding_masks(
            100,
            100,
            placements,
            _manifest(_region("pokeapi:official-artwork:6")),
            tmp_path,
        )


def test_build_masks_rejects_duplicate_placement_subjects(tmp_path: Path):
    with pytest.raises(ValueError, match="Duplicate"):
        _grounding().build_grounding_masks(
            100,
            100,
            [_placement(), _placement(x=60)],
            _manifest(),
            tmp_path,
        )


def test_build_masks_rejects_polygon_union_over_twelve_percent(tmp_path: Path):
    region = _region(
        polygon=[[0.1, 0.1], [0.5, 0.1], [0.5, 0.5], [0.1, 0.5]],
        anchors=[[0.2, 0.2]],
    )
    with pytest.raises(ValueError, match="12%"):
        _grounding().build_grounding_masks(
            100,
            100,
            [_placement()],
            _manifest(region),
            tmp_path,
        )


def test_build_masks_rejects_source_coverage_that_leaves_no_editable_ground(
    tmp_path: Path,
):
    source = Image.new("RGBA", (100, 100), (10, 20, 30, 1))
    with pytest.raises(ValueError, match="no editable ground"):
        _grounding().build_grounding_masks(
            100,
            100,
            [_placement(image=source, x=0, y=0)],
            _manifest(),
            tmp_path,
        )


def test_positive_feather_rejects_each_region_without_full_edit_weight(
    tmp_path: Path,
):
    thin = _region(
        polygon=[[0.40, 0.70], [0.43, 0.70], [0.43, 0.90], [0.40, 0.90]],
        anchors=[[0.42, 0.80]],
    )
    wide = _region(
        "pokeapi:official-artwork:6",
        polygon=[[0.05, 0.05], [0.15, 0.05], [0.15, 0.15], [0.05, 0.15]],
        anchors=[[0.10, 0.10]],
    )

    with pytest.raises(
        ValueError,
        match="pokeapi:official-artwork:25.*full edit weight",
    ):
        _grounding().build_grounding_masks(
            100,
            100,
            [_placement(), _placement(6, x=0, y=0)],
            _manifest(thin, wide, feather_ratio=0.02),
            tmp_path,
        )


def test_build_masks_rejects_anchor_rounded_outside_its_region_raster(
    tmp_path: Path,
):
    region = _region(
        polygon=[[0.12, 0.507], [0.779, 0.46], [0.483, 0.667]],
        anchors=[[0.4495, 0.4835]],
    )

    with pytest.raises(ValueError, match="anchor.*raster"):
        _grounding().build_grounding_masks(
            1280,
            720,
            [_placement()],
            _manifest(region),
            tmp_path,
        )


def test_audit_grounding_pixels_reports_exact_protection_counts(tmp_path: Path):
    reference = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    reference.putpixel((5, 5), (255, 0, 0, 1))
    baseline = Image.new("RGBA", (10, 10), (20, 30, 40, 255))
    artwork = baseline.copy()
    artwork.putpixel((1, 1), (22, 33, 44, 255))
    mask = Image.new("RGBA", (10, 10), (0, 0, 0, 255))
    mask.putpixel((1, 1), (0, 0, 0, 0))
    paths = [
        _save(tmp_path / name, image)
        for name, image in (
            ("reference.png", reference),
            ("baseline.png", baseline),
            ("artwork.png", artwork),
            ("mask.png", mask),
        )
    ]

    result = _grounding().audit_grounding_pixels(*paths)

    assert result == {
        "method": "exact_grounding_protected_pixels",
        "passed": True,
        "dimensions": {"width": 10, "height": 10},
        "reference_sha256": hashlib.sha256(paths[0].read_bytes()).hexdigest(),
        "baseline_sha256": hashlib.sha256(paths[1].read_bytes()).hexdigest(),
        "artwork_sha256": hashlib.sha256(paths[2].read_bytes()).hexdigest(),
        "mask_sha256": hashlib.sha256(paths[3].read_bytes()).hexdigest(),
        "editable_pixels": 1,
        "changed_editable_pixels": 1,
        "source_visible_pixels": 1,
        "changed_source_pixels": 0,
        "outside_mask_pixels": 99,
        "changed_outside_mask_pixels": 0,
    }


def _audit_fixture(tmp_path: Path) -> list[Path]:
    reference = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    reference.putpixel((5, 5), (255, 0, 0, 1))
    baseline = Image.new("RGBA", (10, 10), (20, 30, 40, 255))
    artwork = baseline.copy()
    artwork.putpixel((1, 1), (22, 33, 44, 255))
    mask = Image.new("RGBA", (10, 10), (0, 0, 0, 255))
    mask.putpixel((1, 1), (0, 0, 0, 0))
    return [
        _save(tmp_path / name, image)
        for name, image in (
            ("reference.png", reference),
            ("baseline.png", baseline),
            ("artwork.png", artwork),
            ("mask.png", mask),
        )
    ]


def test_audit_rejects_mask_source_overlap(tmp_path: Path):
    paths = _audit_fixture(tmp_path)
    mask = Image.open(paths[3]).convert("RGBA")
    mask.putpixel((5, 5), (0, 0, 0, 254))
    mask.save(paths[3])

    with pytest.raises(ValueError, match="source pixels"):
        _grounding().audit_grounding_pixels(*paths)


def test_audit_rejects_any_changed_source_pixel(tmp_path: Path):
    paths = _audit_fixture(tmp_path)
    artwork = Image.open(paths[2]).convert("RGBA")
    artwork.putpixel((5, 5), (21, 30, 40, 255))
    artwork.save(paths[2])

    with pytest.raises(ValueError, match="source pixels changed"):
        _grounding().audit_grounding_pixels(*paths)


def test_audit_rejects_any_changed_pixel_outside_the_mask(tmp_path: Path):
    paths = _audit_fixture(tmp_path)
    artwork = Image.open(paths[2]).convert("RGBA")
    artwork.putpixel((8, 8), (20, 31, 40, 255))
    artwork.save(paths[2])

    with pytest.raises(ValueError, match="outside"):
        _grounding().audit_grounding_pixels(*paths)


def test_audit_rejects_an_unchanged_editable_region(tmp_path: Path):
    paths = _audit_fixture(tmp_path)
    Image.open(paths[1]).save(paths[2])

    with pytest.raises(ValueError, match="unchanged"):
        _grounding().audit_grounding_pixels(*paths)


def test_audit_rejects_dimension_mismatch(tmp_path: Path):
    paths = _audit_fixture(tmp_path)
    _save(paths[2], Image.new("RGBA", (9, 10), (20, 30, 40, 255)))

    with pytest.raises(ValueError, match="dimensions"):
        _grounding().audit_grounding_pixels(*paths)
