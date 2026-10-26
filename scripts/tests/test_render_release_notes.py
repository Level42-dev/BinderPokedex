import json
from pathlib import Path

import yaml

from scripts.release.build_manifest import LANGUAGES, main as build_manifest
from scripts.release.render_release_notes import render_release_notes


def test_render_release_notes_builds_bilingual_versioned_body():
    manifest = {
        "tag": "v9.0",
        "languages": LANGUAGES,
        "release_notes": {
            "summary": {
                "en": "Every binder now has poster artwork.",
                "de": "Jeder Binder besitzt jetzt Poster-Artwork.",
            },
            "hero": {
                "path": "docs/images/key.png",
                "alt": "Binder key visual",
            },
            "preview": {
                "path": "docs/images/output.png",
                "alt": "Actual output",
            },
            "whats_new": {
                "en": {
                    "title": "Poster Artwork for Every Binder",
                    "body": ["All scopes covered."],
                },
                "de": {
                    "title": "Poster-Artwork für jeden Binder",
                    "body": ["Alle Scopes abgedeckt."],
                },
            },
        },
    }

    result = render_release_notes(manifest)

    assert result.startswith("# Binder Pokédex v9.0\n")
    assert "/v9.0/docs/images/key.png" in result
    assert "/v9.0/docs/images/output.png" in result
    assert "Poster Artwork for Every Binder" in result
    assert "Poster-Artwork für jeden Binder" in result
    for info in LANGUAGES.values():
        assert info["zip"] in result
        assert (
            "https://github.com/Level42-dev/BinderPokedex/releases/download/"
            f"v9.0/{info['zip']}"
        ) in result
    assert "DerFlash/BinderPokedex" not in result


def test_build_manifest_can_exercise_planned_news_for_a_pr(tmp_path: Path, monkeypatch):
    (tmp_path / "config/scopes").mkdir(parents=True)
    (tmp_path / "config/scopes/Base1.yaml").write_text("scope: Base1\n")
    (tmp_path / "config/release_notes").mkdir(parents=True)
    (tmp_path / "config/release_notes/v9.0.yaml").write_text(
        yaml.safe_dump({"summary": {"en": "Poster artwork"}}),
        encoding="utf-8",
    )
    (tmp_path / "data/output").mkdir(parents=True)
    (tmp_path / "data/output/Base1.json").write_text(
        json.dumps({"sections": {"main": {"cards": [1, 2]}}}),
        encoding="utf-8",
    )
    output = tmp_path / "manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_manifest.py",
            "--tag",
            "pr-7-deadbeef",
            "--release-notes-tag",
            "v9.0",
            "--project-dir",
            str(tmp_path),
            "--output",
            output.name,
        ],
    )

    assert build_manifest() == 0
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["tag"] == "pr-7-deadbeef"
    assert manifest["release_notes_tag"] == "v9.0"
    assert manifest["release_notes"]["summary"]["en"] == "Poster artwork"


def test_v10_manifest_groups_anniversary_scopes_separately(tmp_path: Path, monkeypatch):
    for directory in ("config/scopes", "config/release_notes", "data/output"):
        (tmp_path / directory).mkdir(parents=True)
    for scope in ("30C", "30CClassic"):
        (tmp_path / "config/scopes" / f"{scope}.yaml").write_text(f"scope: {scope}\n")
        (tmp_path / "data/output" / f"{scope}.json").write_text(
            json.dumps({"sections": {"main": {"cards": []}}}), encoding="utf-8"
        )
    (tmp_path / "config/release_notes/v10.0.yaml").write_text("summary: {}\n")
    monkeypatch.setattr(
        "sys.argv",
        ["build_manifest.py", "--tag", "v10.0", "--project-dir", str(tmp_path)],
    )

    assert build_manifest() == 0
    manifest = json.loads((tmp_path / "release-manifest.json").read_text())
    assert manifest["scope_groups"]["anniversary"] == ["30C", "30CClassic"]


def test_v9_release_news_uses_collector_language_not_project_language():
    project_dir = Path(__file__).resolve().parents[2]
    notes = yaml.safe_load(
        (project_dir / "config/release_notes/v9.0.yaml").read_text(encoding="utf-8")
    )
    copy = json.dumps(notes, ensure_ascii=False).lower()

    for internal_term in (
        "reviewed",
        "geprüft",
        "comfyui",
        "repository",
        "deterministic",
        "reproduzierbar",
        "fallback",
        "skip-poster",
    ):
        assert internal_term not in copy

    assert (
        notes["whats_new"]["en"]["title"]
        == "One Artwork. Nine Cards. Your Binder."
    )
    assert (
        notes["whats_new"]["de"]["title"]
        == "Ein Motiv. Neun Karten. Dein Binder."
    )


def test_v10_release_news_covers_the_collector_visible_refresh():
    project_dir = Path(__file__).resolve().parents[2]
    notes = yaml.safe_load(
        (project_dir / "config/release_notes/v10.0.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert notes["display_date"] == {
        "en": "October 2026",
        "de": "Oktober 2026",
    }
    assert (
        notes["whats_new"]["en"]["title"]
        == "30 Years. Complete Panoramas. Correct Card Lists."
    )
    assert (
        notes["whats_new"]["de"]["title"]
        == "30 Jahre. Alle Panoramen. Korrekte Kartenlisten."
    )

    copy = json.dumps(notes, ensure_ascii=False)
    for required in (
        "Dunkelnacht",
        "Terapagos & Freunde",
        "Ns Zoroark-ex",
        "Schwarze Blitze",
        "Weiße Flammen",
        "Stellarkrone",
        "30 Jahre",
        "Klassische Sammlung",
    ):
        assert required in copy

    for internal_term in (
        "API",
        "renderer",
        "fallback",
        "seed",
        "ComfyUI",
        "repository",
    ):
        assert internal_term.casefold() not in copy.casefold()
