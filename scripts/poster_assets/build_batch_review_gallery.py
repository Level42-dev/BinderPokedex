"""Index sealed local panorama trials for a source-versus-print approval round.

The generated gallery deliberately links to ignored local trial/source caches.
It does not promote artwork or make an approval decision.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "docs/reviews"
TRAITS = REVIEW / "2026-09-22-panorama-source-traits.yaml"
OUTPUT_MD = REVIEW / "2026-09-22-panorama-batch-gallery.md"
OUTPUT_JSON = REVIEW / "2026-09-22-panorama-batch-evidence.json"

# Variants are the exact images under review, never the latest file in a folder.
CASES = {
    "P07": "b", "P08": "a", "P09": "a", "P11": "a", "P12": "a",
    "P13": "a", "P14": "b", "P16": "a", "P17": "b", "P18": "b",
    "P19": "b", "P20": "b", "P21": "b", "P22": "b", "P23": "d",
    "P24": "b", "P25": "b", "P26": "b", "P28": "b", "P29": "b",
    "P30": "b", "P31": "b", "P32": "b", "P33": "b", "P34": "b",
    "P35": "b", "P36": "b", "P37": "d", "P38": "b", "P39": "b",
}
NOTES = {
    "P07": "Panflams stützende Hand: Variante A verworfen; bitte die Finger von B prüfen.",
    "P23": "Lapras: dunkle Flecken nach zwei verworfenen Versuchen in D wieder sichtbar.",
    "P24": "Flamiaus hintere Bein-/Hüftpartie bitte besonders prüfen.",
    "P33": "Nur Artwork: Promo-Anzahl und Nummern sind hier nicht freigegeben.",
    "P34": "Endivies Körper-/Pfotenform bitte besonders prüfen.",
    "P37": "Mega-Zygarde muss mit vollständigem Kopf/Kanonenfortsatz innerhalb von r3c3 liegen.",
    "P39": "Bisasams Mund leicht vereinfacht. Promo-Anzahl und Nummern sind nicht freigegeben.",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def gallery_link(path: Path) -> str:
    return "../../" + rel(path)


def verified_record(record: dict, *, key: str | None = None) -> dict:
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise ValueError(f"Missing sealed {key or 'file'} record")
    path = ROOT / record["path"]
    if not path.is_relative_to(ROOT / "tmp") or not path.is_file():
        raise ValueError(f"Missing or unsafe {key or 'file'}")
    if sha256(path) != record.get("sha256"):
        raise ValueError(f"Changed sealed {key or 'file'}")
    return {"path": rel(path), "sha256": record["sha256"]}


def indexed_case(review_id: str, suffix: str, scope: str) -> dict:
    variant = f"{review_id.lower()}-batch-20260922-{suffix}"
    trial = ROOT / "tmp/oneshot-trials" / variant
    state = json.loads((trial / "experiment.json").read_text())
    evidence_path = trial / "review/evidence.json"
    if state.get("variant") != variant or state.get("scope") != scope:
        raise ValueError(f"{review_id}: trial identity differs")
    if (state.get("review_evidence", {}).get("path") != rel(evidence_path)
            or state["review_evidence"].get("sha256") != sha256(evidence_path)):
        raise ValueError(f"{review_id}: review seal differs")
    evidence = json.loads(evidence_path.read_text())
    if (evidence.get("scope"), evidence.get("variant"), evidence.get("human_approval")) != (
        scope, variant, "pending"
    ):
        raise ValueError(f"{review_id}: not a pending exact-image trial")
    files = {key: verified_record(evidence[key], key=key) for key in (
        "raw", "master", "preview", "run_sidecar", "worker_run", "worker_log"
    )}
    cards = [verified_record(card, key="card") for card in evidence["cards"]]
    if len(cards) != 9 or any(
        cards[i]["path"] != rel(trial / "review/cards" / f"card_r{i // 3 + 1}_c{i % 3 + 1}.png")
        for i in range(9)
    ):
        raise ValueError(f"{review_id}: incomplete physical-card set")
    source_dir = ROOT / "tmp/poster-workspaces" / scope / "sources/cutouts"
    source_manifest = json.loads((source_dir / "manifest.json").read_text())
    trial_manifest = yaml.safe_load((ROOT / "tmp/review-batch-manifests" / variant / "poster.yaml").read_text())
    bound = trial_manifest["artwork"]["source_details"]
    items = source_manifest["items"]
    if len(items) not in (2, 3) or len(bound) != len(items):
        raise ValueError(f"{review_id}: source cast differs")
    columns = (1, 3) if len(items) == 2 else (1, 2, 3)
    sources = []
    for item, column in zip(items, columns):
        path = source_dir / item["file"]
        key = item.get("poster_subject", {}).get("subject_key") or f"pokeapi:official-artwork:{item['pokemon_id']}"
        digest = sha256(path)
        if bound.get(key, {}).get("sha256") != digest:
            raise ValueError(f"{review_id}: source hash differs for {key}")
        sources.append({
            "name_de": item["name_de"], "subject_key": key,
            "source": {"path": rel(path), "sha256": digest},
            "card": cards[6 + column - 1], "slot": f"r3c{column}",
        })
    return {
        "review_id": review_id, "scope": scope, "variant": variant,
        "human_approval": "pending", "note": NOTES.get(review_id, ""),
        "files": files, "cards": cards, "sources": sources,
    }


def generate() -> tuple[dict, str]:
    scopes = yaml.safe_load(TRAITS.read_text())["scopes"]
    cases = [indexed_case(review_id, suffix, scopes[review_id]) for review_id, suffix in CASES.items()]
    report = {
        "schema_version": 1,
        "purpose": "local_exact_artwork_approval_only",
        "human_approval": "pending",
        "candidate_count": len(cases),
        "source_card_pair_count": sum(len(case["sources"]) for case in cases),
        "all_physical_card_count": sum(len(case["cards"]) for case in cases),
        "cases": cases,
    }
    lines = [
        "# V10: gesammelte Panorama-Abnahme", "",
        "Alle Bilder sind **neue, unveröffentlichte Prüfkandidaten**. Eine Freigabe bezieht sich nur",
        "auf die hier per SHA-256 gebundene Variante. Weder produktive Poster noch PDFs wurden damit ersetzt.",
        "Die Bildlinks verweisen auf lokale, ignorierte Render- und Quellcaches; das JSON neben",
        "dieser Seite hält die genauen Dateihashes fest.", "",
        f"**Umfang:** {len(cases)} Panoramen, {report['source_card_pair_count']} Quellbild-/Kartenausschnitt-Paare,",
        f"{report['all_physical_card_count']} technisch verifizierte physische Kartenausschnitte.", "",
        "Für jede Zeile bitte **freigeben** oder die konkrete Abweichung nennen. Ein Einwand zu einem",
        "Pokémon sperrt das ganze Panorama, bis eine neue exakte Variante vorliegt.", "",
        "| ID | Set/Teil | Genaue Variante | Prüffokus |", "| --- | --- | --- | --- |",
    ]
    for case in cases:
        lines.append(f"| [{case['review_id']}](#{case['review_id'].lower()}) | `{case['scope']}` | `{case['variant']}` | {case['note'] or 'Gesamtbild und Quellenvergleich'} |")
    lines += [
        "", "## Bereits teilweise freigegeben oder separat offen", "",
        "- **P01 / Stellarkrone:** genaue B-Figuren/Komposition angenommen; der unpassende schmale Hopplo-Bodenschatten und technische Übernahme bleiben offen. [Vergleich](2026-09-15-sv07-source-detail-review.md).",
        "- **P02 / Dschungel:** Pikachu samt korrigierter Vordergrund-Halme angenommen; Relaxo und Evoli sind nicht mitfreigegeben. [Vergleich](2026-09-14-panorama-shortlist.md).",
        "- **P05 / Gen 2:** bestehender genauer D-Kandidat bleibt zur separaten Freigabe. [Status](../POSTER_ARTWORK_STATUS.md).",
        "- **P06 / Gen 3:** kein neuer Kandidat in dieser Charge; offener Identitäts-/Detailcheck. [Status](../POSTER_ARTWORK_STATUS.md).",
        "- **P03, P04, P10, P15, P27, P40:** bereits spezifisch angenommen bzw. übernommen; nicht erneut generiert oder neu zur Abstimmung gestellt.",
        "- **Base1 B und ExGen3 Mega C:** Bildfreigabe vorhanden, technische Übernahme weiterhin separat offen.",
        "- **SVP/MEP:** Die sichtbaren Infokarten-Zahlen und die Promo-Nummerierung werden durch diese Bildabnahme ausdrücklich **nicht** bestätigt.",
        "", "## Neue Kandidaten mit Quellenvergleich", "",
    ]
    for case in cases:
        review_id, variant = case["review_id"], case["variant"]
        preview = ROOT / case["files"]["preview"]["path"]
        lines += [f"### {review_id} · {case['scope']}", "", f"**Variante:** `{variant}` · **Entscheidung:** offen", ""]
        if case["note"]:
            lines += [f"**Genauer Blick:** {case['note']}", ""]
        lines += [f"![{review_id} vollständiges Panorama]({gallery_link(preview)})", "", "| Pokémon · Einleger | Genaues Quellbild | Tatsächlicher Kartenausschnitt |", "| --- | --- | --- |"]
        for source in case["sources"]:
            source_path = ROOT / source["source"]["path"]
            card_path = ROOT / source["card"]["path"]
            lines.append(
                f"| {source['name_de']} · {source['slot']} | "
                f"![{review_id} {source['name_de']} Quelle]({gallery_link(source_path)}) | "
                f"![{review_id} {source['name_de']} Einleger]({gallery_link(card_path)}) |"
            )
        lines += [""]
    return report, "\n".join(lines)


def main() -> None:
    report, markdown = generate()
    OUTPUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    OUTPUT_MD.write_text(markdown)
    print(f"Indexed {report['candidate_count']} panoramas, {report['source_card_pair_count']} exact-source pairs")


if __name__ == "__main__":
    main()
