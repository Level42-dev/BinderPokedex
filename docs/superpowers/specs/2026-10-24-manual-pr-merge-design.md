# Manual PR merge after Codex review

PRs remain mandatory for `main`. The repository owner asks Codex to review the final commit, checks applicable tests and release evidence, and gives an explicit go in the chat. The agent merges only that reviewed commit after the go; automated merging is disabled.

GitHub's required approval count is zero because the single account cannot approve its own PR. Automatic Copilot review is disabled to avoid its separate cost. This makes the chat go an operating procedure rather than a GitHub-enforced approval; the remaining rules keep linear history, protect against deletion and force pushes, and require review conversations to be resolved.

The release announcement workflow creates a PR but does not merge it. Its download URLs must derive from the canonical release URL, so a repository move cannot leave links pointing at the former owner.
