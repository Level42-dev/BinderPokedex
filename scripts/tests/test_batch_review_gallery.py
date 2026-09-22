"""The collected approval index must not silently include rejected artwork."""
from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs/reviews/2026-09-22-panorama-batch-evidence.json"
GALLERY = ROOT / "docs/reviews/2026-09-22-panorama-batch-gallery.md"


def test_collected_candidates_are_exact_and_pending():
    report = json.loads(REPORT.read_text())
    cases = report["cases"]
    assert report["human_approval"] == "pending"
    assert report["candidate_count"] == len(cases) == 29
    assert report["source_card_pair_count"] == sum(len(case["sources"]) for case in cases) == 87
    assert report["all_physical_card_count"] == sum(len(case["cards"]) for case in cases) == 261
    ids = {case["review_id"] for case in cases}
    assert {"P05", "P23", "P33", "P39"} <= ids
    assert {"P16", "P37"}.isdisjoint(ids)
    assert all(case["human_approval"] == "pending" for case in cases)
    assert {item["review_id"] for item in report["rejected_trials"]} == {"P16", "P37"}
    assert next(case for case in cases if case["review_id"] == "P23")["variant"] == "p23-batch-20260922-d"


def test_every_gallery_link_resolves_to_a_local_review_or_source_file():
    markdown = GALLERY.read_text()
    links = re.findall(r"!?\[[^]]*\]\(([^)]+)\)", markdown)
    assert len(links) >= 200
    assert all((GALLERY.parent / link).exists() for link in links if not link.startswith("#"))
    assert "keine** Freigabefälle" in markdown
    assert "Promo-Nummerierung" in markdown
