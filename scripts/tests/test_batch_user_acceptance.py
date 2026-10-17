"""Accepted artwork is bound to its unchanged review and review-only archive."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "docs/reviews/2026-09-23-panorama-batch-user-acceptance.json"
INDEX = ROOT / "assets/reviewed-candidates/v10-batch-20260923/archive-index.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def test_exact_batch_acceptance_and_archived_masters():
    record = json.loads(RECORD.read_text())
    index = json.loads(INDEX.read_text())
    evidence = json.loads((ROOT / record["evidence"]["path"]).read_text())
    assert record["human_approval"] is True
    assert record["candidate_count"] == len(record["candidates"]) == 29
    assert index["kind"] == "review_archive_not_production_provenance"
    assert index["promoted"] is False
    assert index["production_routing_enabled_by_archive"] is False
    assert len(index["masters"]) == 29
    assert {"P16", "P37"}.isdisjoint(case["review_id"] for case in record["candidates"])
    for key in ("gallery", "evidence"):
        assert sha256(ROOT / record[key]["path"]) == record[key]["sha256"]
    assert sha256(RECORD) == index["acceptance_record"]["sha256"]
    assert sha256(ROOT / index["evidence_report"]["path"]) == index["evidence_report"]["sha256"]
    by_id = {case["review_id"]: case for case in evidence["cases"]}
    archive_by_id = {item["review_id"]: item for item in index["masters"]}
    assert set(by_id) == set(archive_by_id) == {item["review_id"] for item in record["candidates"]}
    for approved in record["candidates"]:
        case = by_id[approved["review_id"]]
        archived = archive_by_id[approved["review_id"]]
        assert (approved["scope"], approved["variant"]) == (case["scope"], case["variant"])
        assert approved["master_sha256"] == case["files"]["master"]["sha256"] == archived["sha256"]
        assert approved["preview_sha256"] == case["files"]["preview"]["sha256"]
        assert archived["archive_path"].startswith("assets/reviewed-candidates/v10-batch-20260923/")
        assert sha256(ROOT / archived["archive_path"]) == archived["sha256"]
