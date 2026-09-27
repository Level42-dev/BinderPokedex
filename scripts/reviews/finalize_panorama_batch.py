"""Finalize the v10 approval gallery without changing frozen poster-renderer inputs."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.poster_assets import build_batch_review_gallery as base


def carried_p05() -> dict:
    variant = "p05-source-detail-20260922-d"
    trial = ROOT / "tmp/oneshot-trials" / variant
    state = json.loads((trial / "experiment.json").read_text())
    evidence_path = trial / "review/evidence.json"
    evidence = json.loads(evidence_path.read_text())
    if (state.get("scope"), state.get("variant"), evidence.get("human_approval")) != (
        "Pokedex/sections/gen2", variant, "pending"
    ) or state.get("review_evidence") != {"path": base.rel(evidence_path), "sha256": base.sha256(evidence_path)}:
        raise ValueError("P05 exact review seal differs")
    files = {key: base.verified_record(evidence[key], key=f"P05 {key}") for key in (
        "raw", "master", "preview", "run_sidecar", "worker_run", "worker_log"
    )}
    cards = [base.verified_record(item, key="P05 card") for item in evidence["cards"]]
    if len(cards) != 9:
        raise ValueError("P05 physical-card set incomplete")
    source_dir = ROOT / "tmp/poster-workspaces/Pokedex/sections/gen2/sources/cutouts"
    source_manifest = json.loads((source_dir / "manifest.json").read_text())
    review_record = json.loads((ROOT / "docs/reviews/2026-09-22-p05-gen2-candidate-d.json").read_text())
    if review_record.get("candidate") != variant or review_record.get("status") != "agent_reviewed_pending_exact_user_approval":
        raise ValueError("P05 review status differs")
    sources = []
    for column, item in enumerate(source_manifest["items"], 1):
        source = source_dir / item["file"]
        key = item.get("poster_subject", {}).get("subject_key") or f"pokeapi:official-artwork:{item['pokemon_id']}"
        digest = base.sha256(source)
        if review_record["source_sha256"].get(key) != digest:
            raise ValueError("P05 exact source changed")
        sources.append({
            "name_de": item["name_de"], "subject_key": key,
            "source": {"path": base.rel(source), "sha256": digest},
            "card": cards[6 + column - 1], "slot": f"r3c{column}",
        })
    return {
        "review_id": "P05", "scope": "Pokedex/sections/gen2", "variant": variant,
        "human_approval": "pending", "note": "Karnimanis breite Zehenform und Endivies Blattansatz genau prüfen.",
        "files": files, "cards": cards, "sources": sources,
    }


def rejected(review_id: str, variant: str, slot: str, reason: str) -> dict:
    trial = ROOT / "tmp/oneshot-trials" / variant
    evidence = json.loads((trial / "review/evidence.json").read_text())
    return {
        "review_id": review_id, "variant": variant, "reason": reason,
        "preview": base.verified_record(evidence["preview"], key="rejected preview"),
        "card": base.verified_record(
            next(card for card in evidence["cards"] if card["path"].endswith(f"card_{slot}.png")),
            key="rejected crop",
        ),
    }


def main() -> None:
    # Keep the implementation module byte-identical to the frozen B/D render jobs.
    base.CASES.pop("P16")
    base.CASES.pop("P37")
    report, markdown = base.generate()
    p05 = carried_p05()
    report["cases"].insert(0, p05)
    report["candidate_count"] += 1
    report["source_card_pair_count"] += len(p05["sources"])
    report["all_physical_card_count"] += len(p05["cards"])
    report["rejected_trials"] = [
        rejected("P16", "p16-batch-20260922-b", "r3_c1", "Kyogre und Groudon überschreiten ihre Einlegergrenzen"),
        rejected("P37", "p37-batch-20260922-d", "r3_c3", "Mega-Zygardes violettes Kanonen-Emblem wird links abgeschnitten"),
    ]
    old_count = report["candidate_count"] - 1
    old_pairs = report["source_card_pair_count"] - 3
    old_cards = report["all_physical_card_count"] - 9
    markdown = markdown.replace(
        "Alle Bilder sind **neue, unveröffentlichte Prüfkandidaten**.",
        "Alle zur Freigabe aufgeführten Bilder sind **unveröffentlichte Prüfkandidaten**.",
        1,
    )
    markdown = markdown.replace(
        f"**Umfang:** {old_count} Panoramen, {old_pairs} Quellbild-/Kartenausschnitt-Paare,\n{old_cards} technisch verifizierte physische Kartenausschnitte.",
        f"**Umfang:** {report['candidate_count']} Panoramen ({old_count} neue und P05 aus der vorigen Runde), "
        f"{report['source_card_pair_count']} Quellbild-/Kartenausschnitt-Paare,\n"
        f"{report['all_physical_card_count']} technisch verifizierte physische Kartenausschnitte.",
    )
    markdown = markdown.replace(
        "| [P07](#p07)",
        f"| [P05](#p05) | `Pokedex/sections/gen2` | `{p05['variant']}` | {p05['note']} |\n| [P07](#p07)",
        1,
    )
    markdown = markdown.replace(
        "- **P05 / Gen 2:** bestehender genauer D-Kandidat bleibt zur separaten Freigabe. [Status](../POSTER_ARTWORK_STATUS.md).",
        "- **P05 / Gen 2:** der genaue D-Kandidat ist unten mit allen drei Quell-/Einlegerpaaren in diese Sammelabnahme aufgenommen.",
    )
    markdown += "\n## P05 · Pokédex-Generation II (mit in dieser Abnahme)\n\n"
    markdown += f"**Variante:** `{p05['variant']}` · **Entscheidung:** offen · {p05['note']}\n\n"
    markdown += f"![P05 vollständiges Panorama]({base.gallery_link(ROOT / p05['files']['preview']['path'])})\n\n"
    markdown += "| Pokémon · Einleger | Genaues Quellbild | Tatsächlicher Kartenausschnitt |\n| --- | --- | --- |\n"
    for source in p05["sources"]:
        markdown += (
            f"| {source['name_de']} · {source['slot']} | "
            f"![P05 {source['name_de']} Quelle]({base.gallery_link(ROOT / source['source']['path'])}) | "
            f"![P05 {source['name_de']} Einleger]({base.gallery_link(ROOT / source['card']['path'])}) |\n"
        )
    markdown += "\n## Noch nicht freigabefähig\n\n"
    markdown += "P16 und P37 sind **keine** Freigabefälle. Auch die letzten One-shot-Versuche schneiden wesentliche Körperteile an physischen Kartengrenzen ab:\n\n"
    for item in report["rejected_trials"]:
        markdown += (
            f"- **{item['review_id']} · {item['variant']}** — {item['reason']}. "
            f"[Gesamtbild]({base.gallery_link(ROOT / item['preview']['path'])}) · "
            f"[angeschnittener Einleger]({base.gallery_link(ROOT / item['card']['path'])}).\n"
        )
    base.OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    base.OUTPUT_MD.write_text(markdown)
    print(f"Indexed {report['candidate_count']} approval candidates; 2 rejected scopes separated")


if __name__ == "__main__":
    main()
