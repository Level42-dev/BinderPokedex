from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _load_workflow(name: str) -> dict:
    return yaml.load(
        (WORKFLOWS / name).read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


def test_pull_request_release_check_is_read_only_and_never_publishes():
    workflow = _load_workflow("verify-release.yml")
    source = (WORKFLOWS / "verify-release.yml").read_text(encoding="utf-8")

    assert "pull_request" in workflow["on"]
    pull_request = workflow["on"]["pull_request"]
    assert pull_request["branches"] == ["main"]
    assert set(pull_request["types"]) == {
        "opened",
        "reopened",
        "synchronize",
        "labeled",
        "unlabeled",
    }
    assert workflow["permissions"] == {"contents": "read"}
    candidate = workflow["jobs"]["build-release-candidate"]
    assert candidate["uses"] == (
        "./.github/workflows/build-release.yml"
    )
    assert candidate["with"]["release_notes_tag"] == "v10.0"
    condition = candidate["if"]
    assert "github.event_name == 'workflow_dispatch'" in condition
    assert "startsWith(github.head_ref, 'release/')" in condition
    assert "startsWith(github.head_ref, 'hotfix/')" in condition
    assert "full-release-check" in condition
    assert "contents: write" not in source
    assert "softprops/action-gh-release" not in source


def test_reusable_release_build_only_creates_a_candidate_artifact():
    workflow = _load_workflow("build-release.yml")
    source = (WORKFLOWS / "build-release.yml").read_text(encoding="utf-8")

    assert set(workflow["on"]) == {"workflow_call"}
    assert workflow["permissions"] == {"contents": "read"}
    assert "validate_promoted_poster.py --all-enabled" in source
    assert "verify_release_candidate.py" in source
    assert "actions/upload-artifact@v4" in source
    assert "contents: write" not in source
    assert "softprops/action-gh-release" not in source


def test_release_build_uses_verified_snapshot_instead_of_mutable_fetch():
    source = (WORKFLOWS / "build-release.yml").read_text(encoding="utf-8")

    assert "fetch.py --scope all" not in source
    assert "verify_data_snapshot.py" in source


def test_tag_release_reuses_candidate_build_before_publishing():
    workflow = _load_workflow("release.yml")
    source = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")

    assert workflow["on"]["push"]["tags"] == ["v*"]
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["build-release-candidate"]["uses"] == (
        "./.github/workflows/build-release.yml"
    )
    publish = workflow["jobs"]["publish"]
    assert publish["needs"] == "build-release-candidate"
    assert publish["permissions"] == {"contents": "write"}
    assert "actions/download-artifact@v4" in source
    assert "softprops/action-gh-release@v2" in source
