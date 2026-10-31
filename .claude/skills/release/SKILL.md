---
name: release
description: Prepare a release from Conventional Commits since the last tag (CHANGELOG.md, versions, tag). Use only when the human asks for one.
disable-model-invocation: true
argument-hint: "[major|minor|patch]"
allowed-tools: Bash(git log *) Bash(git tag *) Bash(uv version *) Read Edit
---
# Release

1. `git log --oneline <last-tag>..HEAD`; group by type: `feat` → Added, `fix` → Fixed, `BREAKING CHANGE`/`!` → Breaking.
2. The bump is `$0`; a `BREAKING CHANGE` footer or `!` forces `major`, `feat` forces at least `minor`.
3. Write the section in `CHANGELOG.md` (newest first), bump versions with `uv version`, commit `chore(release): vX.Y.Z`, tag `vX.Y.Z`.
4. Do not push; the human pushes the tag.
