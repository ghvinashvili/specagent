# librarian — contract
## Receives
- `prompt.md` with the brief and the material paths under `context/`; the wiki under `wiki/` on its worktree branch.
## Returns
- New and updated pages under `wiki/` from `templates/wiki/page.md`, `wiki/index.md`, one entry appended to `wiki/log.md`, committed on the worktree branch; `output/changes.md`: pages created, updated, marked `disputed`; `result.json`.
## When it stops
- `uv run harness wiki-lint` exits 0 on the branch and every changed source is reflected; or an escalation (two sources contradict each other, a page should be deleted).
## Never
- Edits `context/`; writes a claim without `path:line`; duplicates a page instead of updating it; deletes a page; pushes. Keeps notes for a later run (no auto memory, no `memory` field).
