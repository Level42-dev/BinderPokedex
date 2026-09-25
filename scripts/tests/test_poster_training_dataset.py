from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
import pytest

from scripts.poster_assets.provenance import image_pixel_record, sha256_file
from scripts.poster_assets.training_dataset import (
    audit_promoted_pairs,
    compose_aligned_teacher_target,
    compose_foreground_occlusion_target,
    immutable_image_record,
    materialize_gold_dataset,
    pair_status,
    validate_audit_manifest,
)


REQUIRED_GATES = [
    "exact_cast_count",
    "identity_and_form",
    "silhouette_and_stature",
    "anatomy_and_face",
    "colors_and_markings",
    "placement_and_card_safety",
    "natural_scene_integration",
    "coherent_landscape_occlusion",
    "text_free_safe_areas",
]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (16, 16), color)
    image.putpixel((0, 0), tuple(255 - value for value in color))
    image.save(path)


def fixture_manifest(tmp_path: Path, *, status: str = "gold") -> Path:
    config_path = tmp_path / "config.json"
    config = {
        "schema_version": 1,
        "profile": "test",
        "image_contract": {
            "width": 16,
            "height": 16,
            "divisible_by": 16,
            "minimum_channel_stddev": 1.0,
        },
        "dataset_contract": {"required_review_gates": REQUIRED_GATES},
        "caption_variants": ["Integrate without changing the subjects."],
    }
    write_json(config_path, config)
    input_path = tmp_path / "input.png"
    target_path = tmp_path / "target.png"
    write_image(input_path, (10, 20, 30))
    write_image(target_path, (30, 40, 50))
    manifest_path = tmp_path / "audit.json"
    manifest = {
        "format_version": 1,
        "kind": "poster_edit_training_audit",
        "profile": "test",
        "config": {
            "file": "config.json",
            "sha256": sha256_file(config_path),
        },
        "summary": {},
        "samples": [
            {
                "id": "scene__input01",
                "scene_key": "scene",
                "scope": "scene",
                "proposed_split": "train_candidate",
                "review_status": status,
                "occlusion_class": "avoid",
                "input": immutable_image_record(input_path, root=tmp_path),
                "target": immutable_image_record(target_path, root=tmp_path),
                "target_visual_review_passed": True,
                "source_pixel_audit": {
                    "passed": True,
                    "input_sha256": sha256_file(input_path),
                },
                "review": {gate: True for gate in REQUIRED_GATES},
            }
        ],
    }
    write_json(manifest_path, manifest)
    return manifest_path


def test_masked_fallback_is_not_a_raw_one_shot_training_target(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    write_json(config_path, {
        "schema_version": 1,
        "profile": "test",
        "split_policy": {"excluded_training_targets": {}, "holdout_scopes": []},
    })
    provenance_path = tmp_path / "assets" / "posters" / "Example" / "poster-flux2-provenance.json"
    provenance_path.parent.mkdir(parents=True)
    (provenance_path.parent / "poster.yaml").write_text(
        "scope: Example\nlayout:\n  name: standard_3x3\npdf:\n  enabled: false\n",
        encoding="utf-8",
    )
    write_json(provenance_path, {
        "schema_version": 3,
        "kind": "promoted_poster",
        "scope": "Example",
        "composition": {"kind": "masked_fallback"},
        "run": {"raw_artwork": {"file": "ignored-one-shot.png"}},
    })
    result = audit_promoted_pairs(
        config_path, root=tmp_path,
        poster_assets=tmp_path / "assets" / "posters",
    )
    assert result["summary"]["promoted_scenes"] == 0
    assert result["samples"] == []


def test_pair_status_never_auto_approves_a_pair() -> None:
    assert pair_status(
        target_exists=True,
        target_review=True,
        target_excluded=False,
        input_errors=[],
        source_pixel_match=True,
    ) == "candidate_pair_review"


def test_pair_status_requires_a_fresh_exact_input() -> None:
    assert pair_status(
        target_exists=True,
        target_review=True,
        target_excluded=False,
        input_errors=[],
        source_pixel_match=False,
    ) == "needs_fresh_exact_input"


def test_compose_aligned_teacher_target_restores_exact_subjects(
    tmp_path: Path,
) -> None:
    scene_path = tmp_path / "scene.png"
    reference_path = tmp_path / "source.png"
    output_path = tmp_path / "target.png"
    Image.new("RGB", (16, 16), (20, 30, 40)).save(scene_path)
    source = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for x in range(6, 10):
        for y in range(5, 11):
            source.putpixel((x, y), (200, 100, 50, 255))
    source.save(reference_path)

    result = compose_aligned_teacher_target(
        scene_path,
        reference_path,
        output_path,
    )

    assert result["source_pixel_audit"]["passed"] is True
    assert result["source_pixel_audit"]["changed_pixels"] == 0
    with Image.open(output_path) as output:
        assert output.getpixel((0, 0)) == (20, 30, 40)
        assert output.getpixel((7, 7)) == (200, 100, 50)


def test_compose_aligned_teacher_target_is_immutable(tmp_path: Path) -> None:
    scene_path = tmp_path / "scene.png"
    reference_path = tmp_path / "source.png"
    output_path = tmp_path / "target.png"
    Image.new("RGB", (16, 16), (20, 30, 40)).save(scene_path)
    Image.new("RGBA", (16, 16), (200, 100, 50, 255)).save(reference_path)
    Image.new("RGB", (16, 16), (0, 0, 0)).save(output_path)

    with pytest.raises(FileExistsError, match="already exists"):
        compose_aligned_teacher_target(
            scene_path,
            reference_path,
            output_path,
        )


def test_compose_foreground_occlusion_target_preserves_uncovered_source(
    tmp_path: Path,
) -> None:
    scene_path = tmp_path / "scene.png"
    reference_path = tmp_path / "source.png"
    foreground_path = tmp_path / "foreground.png"
    output_path = tmp_path / "target.png"
    Image.new("RGB", (16, 16), (20, 30, 40)).save(scene_path)
    source = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for x in range(4, 12):
        for y in range(4, 12):
            source.putpixel((x, y), (200, 100, 50, 255))
    source.save(reference_path)
    foreground = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y in range(8, 16):
        foreground.putpixel((7, y), (10, 80, 20, 255))
    foreground.save(foreground_path)

    result = compose_foreground_occlusion_target(
        scene_path,
        reference_path,
        foreground_path,
        output_path,
    )

    audit = result["source_pixel_audit"]
    assert audit["passed"] is True
    assert audit["intentionally_covered_opaque_pixels"] == 4
    assert audit["changed_uncovered_opaque_pixels"] == 0
    with Image.open(output_path) as output:
        assert output.getpixel((6, 9)) == (200, 100, 50)
        assert output.getpixel((7, 9)) == (10, 80, 20)


def test_compose_foreground_occlusion_target_requires_real_overlap(
    tmp_path: Path,
) -> None:
    scene_path = tmp_path / "scene.png"
    reference_path = tmp_path / "source.png"
    foreground_path = tmp_path / "foreground.png"
    output_path = tmp_path / "target.png"
    Image.new("RGB", (16, 16), (20, 30, 40)).save(scene_path)
    source = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    source.putpixel((8, 8), (200, 100, 50, 255))
    source.save(reference_path)
    foreground = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    foreground.putpixel((1, 1), (10, 80, 20, 255))
    foreground.save(foreground_path)

    with pytest.raises(ValueError, match="does not cover"):
        compose_foreground_occlusion_target(
            scene_path,
            reference_path,
            foreground_path,
            output_path,
        )


def test_materialize_gold_uses_ai_toolkit_pair_direction(tmp_path: Path) -> None:
    manifest_path = fixture_manifest(tmp_path)

    output_manifest = materialize_gold_dataset(
        manifest_path,
        tmp_path / "dataset",
        root=tmp_path,
    )

    value = json.loads(output_manifest.read_text(encoding="utf-8"))
    assert value["ai_toolkit"] == {
        "folder_path": "target",
        "control_path": "reference",
        "caption_ext": "txt",
        "match_target_res": True,
    }
    assert (tmp_path / "dataset/reference/scene__input01.png").is_file()
    assert (tmp_path / "dataset/target/scene__input01.png").is_file()
    assert (tmp_path / "dataset/target/scene__input01.txt").read_text(
        encoding="utf-8"
    ).startswith("Integrate")


def test_materialize_keeps_holdout_out_of_training_folders(
    tmp_path: Path,
) -> None:
    manifest_path = fixture_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    holdout = dict(manifest["samples"][0])
    holdout["id"] = "holdout__input01"
    holdout["scene_key"] = "holdout"
    holdout["proposed_split"] = "holdout"
    manifest["samples"].append(holdout)
    write_json(manifest_path, manifest)

    materialize_gold_dataset(
        manifest_path,
        tmp_path / "dataset",
        root=tmp_path,
    )

    assert not (tmp_path / "dataset/reference/holdout__input01.png").exists()
    assert not (tmp_path / "dataset/target/holdout__input01.png").exists()
    assert not (tmp_path / "dataset/target/holdout__input01.txt").exists()
    assert (
        tmp_path
        / "dataset/evaluation/holdout/reference/holdout__input01.png"
    ).is_file()
    assert (
        tmp_path
        / "dataset/evaluation/holdout/target/holdout__input01.png"
    ).is_file()
    assert (
        tmp_path
        / "dataset/evaluation/holdout/target/holdout__input01.txt"
    ).is_file()


def test_materialize_refuses_unreviewed_candidates(tmp_path: Path) -> None:
    manifest_path = fixture_manifest(
        tmp_path,
        status="candidate_pair_review",
    )

    with pytest.raises(ValueError, match="No gold training samples"):
        materialize_gold_dataset(
            manifest_path,
            tmp_path / "dataset",
            root=tmp_path,
        )


def test_validation_accepts_an_explicitly_rejected_pair(tmp_path: Path) -> None:
    manifest_path = fixture_manifest(tmp_path, status="rejected_pair")

    result = validate_audit_manifest(manifest_path, root=tmp_path)

    assert result["samples"][0]["review_status"] == "rejected_pair"


def test_validation_rejects_changed_training_pixels(tmp_path: Path) -> None:
    manifest_path = fixture_manifest(tmp_path)
    Image.new("RGB", (16, 16), (200, 210, 220)).save(tmp_path / "input.png")

    with pytest.raises(ValueError, match="Stale sha256"):
        validate_audit_manifest(manifest_path, root=tmp_path)


def test_validation_rejects_exact_pixels_with_wrong_occlusion(
    tmp_path: Path,
) -> None:
    manifest_path = fixture_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sample = manifest["samples"][0]
    assert sample["source_pixel_audit"]["passed"] is True
    sample["review"]["coherent_landscape_occlusion"] = False
    write_json(manifest_path, manifest)

    with pytest.raises(
        ValueError,
        match="coherent_landscape_occlusion",
    ):
        validate_audit_manifest(manifest_path, root=tmp_path)


def test_validation_rejects_scene_leakage(tmp_path: Path) -> None:
    manifest_path = fixture_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    duplicate = dict(manifest["samples"][0])
    duplicate["id"] = "scene__input02"
    duplicate["proposed_split"] = "holdout"
    manifest["samples"].append(duplicate)
    write_json(manifest_path, manifest)

    with pytest.raises(ValueError, match="leaks across splits"):
        validate_audit_manifest(manifest_path, root=tmp_path)
