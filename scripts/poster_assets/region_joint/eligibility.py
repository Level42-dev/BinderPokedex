"""Gate the opt-in P16 fallback on prior failed trials."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


P16_SCOPE = "ExGen2/sections/primal"
REQUIRED_VARIANTS = (
    "p16-batch-20260922-a",
    "p16-batch-20260922-b",
    "p16-batch-20260922-e",
    "p16-batch-20260923-f",
)


def require_p16_evidence(root: Path, evidence_path: Path) -> str:
    """Return the evidence digest only if all four failed trials still match."""
    root = Path(root).resolve()
    evidence_path = Path(evidence_path)
    allowed_record_root = root / "docs/reviews"
    if evidence_path.is_symlink() or not evidence_path.resolve().is_relative_to(allowed_record_root):
        raise ValueError("P16 evidence must stay in the repository review directory")
    record = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("P16 fallback evidence is incomplete")
    trials = record.get("failed_trials")
    if (
        record.get("schema_version") != 1
        or record.get("scope") != P16_SCOPE
        or not isinstance(trials, list)
        or len(trials) != len(REQUIRED_VARIANTS)
        or tuple(item.get("variant") for item in trials if isinstance(item, dict)) != REQUIRED_VARIANTS
    ):
        raise ValueError("P16 fallback evidence is incomplete")

    trial_root = root / "tmp/oneshot-trials"
    for item in trials:
        if not isinstance(item.get("failure"), str) or not item["failure"].strip():
            raise ValueError("Unsafe or unexplained P16 trial")
        review = trial_root / item["variant"] / "review"
        if review.resolve() != review or not review.is_relative_to(trial_root):
            raise ValueError("P16 review outside expected trial")
        for name, field in (("poster-de.png", "poster_sha256"), ("evidence.json", "evidence_sha256")):
            candidate = review / name
            if candidate.is_symlink() or candidate.resolve() != candidate:
                raise ValueError("P16 review outside expected trial")
            digest = _sha256(candidate)
            if digest != item.get(field):
                raise ValueError(f"{name} SHA-256 mismatch")
    return _sha256(evidence_path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
