# Manual PR Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make release announcement PRs use canonical download links and wait for explicit user approval after Codex review before a manual merge.

**Architecture:** The announcement generator derives asset links from the release page URL passed by the workflow. The workflow creates a PR without requesting an automatic merge. Repository protection keeps the PR path while allowing the single account's chat-approved manual merge.

**Tech Stack:** Python, pytest, GitHub Actions YAML, GitHub repository ruleset.

**Spec:** `docs/superpowers/specs/2026-10-24-manual-pr-merge-design.md`

## Global Constraints

- Preserve the existing release announcement content, nine language archives, and v10.0 tag.
- Keep PR requirement, linear history, deletion and force-push restrictions, and conversation resolution enabled.
- Do not merge a PR without explicit user approval of its final head commit.
- Do not automatically request Copilot review or enable auto-merge.

## Review Focus

- A moved repository URL produces downloads under the new owner; add this case to the announcer test.
- Repeated announcer runs keep one news block; retain the existing idempotence test.
- A later release announcement must not enable auto-merge; inspect the workflow and test its configuration.
- The final PR head must match the Codex review and user go before merge; verify live immediately before merge.
- Existing local release artifacts must remain untouched; use this isolated worktree.

---

### Task 1: Canonical announcement links

**Files:** `scripts/release/announce_release.py`, `scripts/tests/test_announce_release.py`, `README.md`, `README.de.md`.

**Interfaces:** `language_links` consumes the release page URL already passed to the script; it produces the nine archive links in each README.

- [x] Change the announcer test to use the current repository release URL and assert every generated download link uses that repository.
- [x] Run the test and observe the old-owner link failure.
- [x] Derive download links from the supplied release URL and update the two v10.0 READMEs.
- [x] Run the announcer test again and confirm it passes.

### Task 2: Manual merge workflow

**Files:** `.github/workflows/announce-release.yml`, `.github/workflows/test-project-notices.yml`, `docs/RELEASE_WORKFLOW.md`, `AGENTS.md`.

**Interfaces:** The workflow still creates the README PR and runs its checks; it no longer schedules a merge.

- [x] Remove the workflow's Enable auto-merge step.
- [x] Include the announcer test in the existing notices check and document the manual-go sequence.
- [x] Run the workflow and announcement tests; inspect the YAML for a surviving auto-merge action.

### Task 3: GitHub protection and PR #18

**Files:** GitHub ruleset 21906213 and PR #18.

**Interfaces:** The ruleset requires a PR but zero formal approvals. The agent merges the exact reviewed head only after the user's final go.

- [x] Verify auto-merge is disabled on PR #18.
- [ ] Save the confirmed ruleset change: zero required approvals, automatic Copilot review off, other protections retained.
- [ ] Verify the ruleset via live API readback and verify the PR remains open.
- [ ] Push the corrections, run relevant tests and Codex review on the final head, and present the resulting diff for the user's go.
- [ ] After that go, verify head SHA and checks again, then manually squash merge and read back `main`.
