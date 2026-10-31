---
name: wiki-ingest
description: Compile changed context/ material into wiki pages, update index and log, run the lint. Use when a librarian ingests into wiki/.
allowed-tools: Bash(git log *) Bash(git diff *) Bash(uv run harness wiki-lint) Read Glob Grep Write Edit
---
# Ingest into the wiki

1. Find the work. Use the paths in `prompt.md`; when it names `context` as a whole, list what changed since the commit recorded in the last entry of `wiki/log.md`: `git log --name-only <commit>..HEAD -- context/`.
2. For each changed source file, write or update `wiki/sources/<slug>.md`: `type: source`, `raw` with the `context/` path, `source_kind`, and what the file contains, with line locators.
3. For each fact or entity the source adds or changes, search `wiki/index.md` first. Update the existing page, or create one from `templates/wiki/page.md`. Never create a second page for the same thing. Keep one ingest to a handful of pages and list what remains in `output/changes.md`.
4. When two sources contradict each other, set `status: disputed`, quote both locations and write an escalation. Do not pick a side.
5. Update `wiki/index.md` and append one entry to `wiki/log.md`: date, the `context/` commit that was ingested, the run id, pages created, updated and disputed.
6. Run `uv run harness wiki-lint`; it must exit 0. Commit on the worktree branch, then write `output/changes.md` and `result.json`.

Never edit `context/`. Never delete a page without an answered escalation. Never copy a secret or personal data into a page.
