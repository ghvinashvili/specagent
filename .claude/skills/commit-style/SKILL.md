---
name: commit-style
description: Write a Conventional Commits message for the staged changes and commit. Use when Claude is about to commit.
allowed-tools: Bash(git diff *) Bash(git status *) Bash(git commit *)
---
# Commit style

1. `git status --short` and `git diff --cached --stat`.
2. Header `<type>(<scope>): <description>`: type from feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert; scope = package or area; description in the imperative, at most 72 characters.
3. Body: what and why, not how. Footer: `BREAKING CHANGE: <text>` when applicable; `Refs: <spec or ADR>`.
4. `git commit -m "<header>" -m "<body>"`. Commitizen's commit-msg stage rejects a header that does not match, where the project installed it (`.pre-commit-config.yaml`).
