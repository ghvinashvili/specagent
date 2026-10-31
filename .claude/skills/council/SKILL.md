---
name: council
description: Convene five independent advisors, a blind peer review and one verdict on a framed decision. Use for high-stakes, uncertain choices.
argument-hint: "[slug]"
allowed-tools: Bash(uv run harness run *) Bash(uv run harness status *) Read Write
---
# Convene a council

Argument: `$0` = slug of the decision.

1. Check the three conditions before anything is launched. If the question has an answer in the repository or its documents, answer it or run a stage for it. If it is creative work, or the human has already decided, say that a council does not fit and stop.
2. Ask the human at most one clarifying question. Then write `<runs root>/_briefs/$0.md` from `templates/project-brief.md`: the goal is the decision in neutral wording with no preferred option; the material is paths; the constraints name the perspectives (default: contrarian, first principles, expansionist, outsider, executor) and the cost (eight sessions). The human confirms the brief.
3. `uv run harness run --slug $0 --brief <runs root>/_briefs/$0.md --pipeline council`, then launch `frame` with the run-stage skill and continue as docs/roles/MANAGER.md describes: `advise` (one shard per perspective), `review`, `verdict`.
4. When the `verdict` gate passed, point the human to `stages/verdict/output/verdict.md`. The decision is theirs; `harness approve` records it.

Never summarise the verdict from memory, never add your own position and never tell an advisor what another advisor wrote.
