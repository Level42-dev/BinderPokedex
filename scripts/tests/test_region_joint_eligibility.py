"""A P16 fallback is permitted only by its exact failed-trial evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.poster_assets.region_joint.eligibility import (
    P16_SCOPE,
    REQUIRED_VARIANTS,
    require_p16_evidence,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(root: Path) -> Path:
    records = []
    for variant in REQUIRED_VARIANTS:
        review = root / "tmp/oneshot-trials" / variant / "review"
        review.mkdir(parents=True)
        (review / "poster-de.png").write_bytes(variant.encode())
        (review / "evidence.json").write_bytes((variant + " evidence").encode())
        records.append({
            "variant": variant,
            "failure": "physical card cut",
            "poster_sha256": _sha256(review / "poster-de.png"),
            "evidence_sha256": _sha256(review / "evidence.json"),
        })
    path = root / "docs/reviews/p16-region-evidence.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "schema_version": 1,
        "scope": P16_SCOPE,
        "failed_trials": records,
    }), encoding="utf-8")
    return path


def test_valid_evidence_binds_four_failed_trials(tmp_path):
    record = _fixture(tmp_path)
    assert require_p16_evidence(tmp_path, record) == _sha256(record)


def test_missing_review_image_refuses_fallback(tmp_path):
    record = _fixture(tmp_path)
    (tmp_path / "tmp/oneshot-trials" / REQUIRED_VARIANTS[0] / "review/poster-de.png").unlink()
    with pytest.raises(FileNotFoundError, match="poster-de.png"):
        require_p16_evidence(tmp_path, record)


def test_changed_review_image_refuses_fallback(tmp_path):
    record = _fixture(tmp_path)
    (tmp_path / "tmp/oneshot-trials" / REQUIRED_VARIANTS[1] / "review/poster-de.png").write_bytes(b"changed")
    with pytest.raises(ValueError, match="poster-de.png SHA-256 mismatch"):
        require_p16_evidence(tmp_path, record)


@pytest.mark.parametrize("mutation", [
    lambda data: data.update(scope="ME03"),
    lambda data: data["failed_trials"][0].update(variant="../foreign"),
    lambda data: data["failed_trials"][0].update(failure=" "),
])
def test_wrong_scope_foreign_trial_or_unexplained_failure_refuses_fallback(tmp_path, mutation):
    record = _fixture(tmp_path)
    data = json.loads(record.read_text(encoding="utf-8"))
    mutation(data)
    record.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        require_p16_evidence(tmp_path, record)


def test_symlinked_review_image_outside_trial_refuses_fallback(tmp_path):
    record = _fixture(tmp_path)
    image = tmp_path / "tmp/oneshot-trials" / REQUIRED_VARIANTS[0] / "review/poster-de.png"
    image.unlink()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"external")
    image.symlink_to(outside)
    with pytest.raises(ValueError, match="outside expected trial"):
        require_p16_evidence(tmp_path, record)
