import json
import shutil
import zipfile
from pathlib import Path

import pytest

from scripts.release.build_manifest import LANGUAGES
from scripts.release.package_archives import package_archives
from scripts.release.verify_release_candidate import verify


def _release_candidate(tmp_path: Path) -> Path:
    repo = Path(__file__).resolve().parents[2]
    for name in ("NOTICE.md", "LICENSE", "LICENSE-CODE", "LICENSE-CONTENT.md", "LICENSES/CC-BY-NC-4.0.txt"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / name, target)
    for language in LANGUAGES:
        output_dir = tmp_path / "output" / language
        output_dir.mkdir(parents=True)
        (output_dir / "scope.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    package_archives(tmp_path, "pr-42-deadbeef", "a" * 40)
    assets = []
    pdf_counts = {}
    for language, info in LANGUAGES.items():
        output_dir = tmp_path / "output" / language
        pdf_path = output_dir / "scope.pdf"

        archive_path = tmp_path / info["zip"]

        pdf_counts[language] = 1
        assets.append(
            {
                "language": language,
                "name": info["zip"],
                "exists": True,
                "size_bytes": archive_path.stat().st_size,
            }
        )

    manifest = {
        "schema_version": 1,
        "tag": "pr-42-deadbeef",
        "scopes": ["Base1"],
        "scope_count": 1,
        "card_counts": {"Base1": 102},
        "pdfs": {
            "total": len(LANGUAGES),
            "by_language": pdf_counts,
        },
        "assets": assets,
    }
    manifest_path = tmp_path / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_verify_release_candidate_checks_every_language_archive(
    tmp_path: Path,
):
    manifest_path = _release_candidate(tmp_path)

    assert verify(manifest_path) == {
        language: 1 for language in LANGUAGES
    }


def test_verify_release_candidate_rejects_missing_archive(
    tmp_path: Path,
):
    manifest_path = _release_candidate(tmp_path)
    (tmp_path / LANGUAGES["de"]["zip"]).unlink()

    with pytest.raises(ValueError, match="Missing or invalid release archive"):
        verify(manifest_path)


def test_verify_release_candidate_checks_rendered_release_notes(tmp_path: Path):
    manifest_path = _release_candidate(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["release_notes"] = {
        "whats_new": {
            "en": {"title": "Poster Artwork for Every Binder"},
            "de": {"title": "Poster-Artwork für jeden Binder"},
        }
    }
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    archive_names = "\n".join(info["zip"] for info in LANGUAGES.values())
    release_notes_path = tmp_path / "release-notes.md"
    release_notes_path.write_text(
        "# Binder Pokédex pr-42-deadbeef\n"
        "Poster Artwork for Every Binder\n"
        "Poster-Artwork für jeden Binder\n"
        f"{archive_names}\n",
        encoding="utf-8",
    )

    assert verify(manifest_path, release_notes_path)


def test_verify_release_candidate_rejects_notes_for_another_tag(tmp_path: Path):
    manifest_path = _release_candidate(tmp_path)
    release_notes_path = tmp_path / "release-notes.md"
    release_notes_path.write_text("# Binder Pokédex v0.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="do not match the release tag"):
        verify(manifest_path, release_notes_path)


def test_release_downloads_include_offline_notices_and_exact_source(tmp_path):
    _release_candidate(tmp_path)
    for language, info in LANGUAGES.items():
        with zipfile.ZipFile(tmp_path / info["zip"]) as archive:
            assert archive.read(f"{language}/scope.pdf").startswith(b"%PDF")
            for name in ("NOTICE.md", "LICENSE", "LICENSE-CODE", "LICENSE-CONTENT.md", "LICENSES/CC-BY-NC-4.0.txt"):
                assert archive.read(f"{language}/{name}") == (tmp_path / name).read_bytes()
            source = json.loads(archive.read(f"{language}/SOURCE.json"))
            assert source["repository"] == "https://github.com/Level42-dev/BinderPokedex"
            assert source["commit"] == "a" * 40
            assert source["tag"] == "pr-42-deadbeef"


@pytest.mark.parametrize("missing", ["NOTICE.md", "LICENSES/CC-BY-NC-4.0.txt", "SOURCE.json"])
def test_verification_rejects_stripped_notices(tmp_path, missing):
    manifest_path = _release_candidate(tmp_path)
    path = tmp_path / LANGUAGES["de"]["zip"]
    with zipfile.ZipFile(path) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    del members[f"de/{missing}"]
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    manifest = json.loads(manifest_path.read_text())
    next(asset for asset in manifest["assets"] if asset["language"] == "de")["size_bytes"] = path.stat().st_size
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Missing release notice"):
        verify(manifest_path)


def test_packaging_refuses_missing_license_before_writing_archives(tmp_path):
    _release_candidate(tmp_path)
    for info in LANGUAGES.values():
        (tmp_path / info["zip"]).unlink()
    (tmp_path / "LICENSE-CONTENT.md").unlink()
    with pytest.raises(ValueError, match="Missing or empty notice"):
        package_archives(tmp_path, "test", "b" * 40)
    assert not list(tmp_path.glob("*.zip"))
