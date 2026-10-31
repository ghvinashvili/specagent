---
name: doc-gardening
description: Find stale statements and broken links under docs/ and open a fix-up pull request. Use on the gardening run or to tidy the docs.
allowed-tools: Bash(uv run harness docs-check *) Bash(git *) Bash(gh pr create *) Read Edit Write
---
# Doc gardening

1. `uv run harness docs-check` prints documents missing from `docs/llms.txt`, broken relative links and generated files older than their sources.
2. Fix each finding in place; never change the meaning of a decision (ADRs are superseded, not edited).
3. Branch `chore/doc-gardening-<date>`, commit with a `docs:` header, `gh pr create --fill`.
