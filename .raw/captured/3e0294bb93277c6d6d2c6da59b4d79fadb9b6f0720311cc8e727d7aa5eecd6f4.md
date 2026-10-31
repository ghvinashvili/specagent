---
title: The plan fixer and the translator are role types
type: decision
status: draft
updated: 2026-10-29
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: the catalogue's arithmetic counts only roles with an agent file and a contract; the plan fixer ran as a skill brief only, and the translator's work was done by hand
would_change_if: a run shows that an existing type does either job with no loss
decision_status: decided
scope: global
tags:
  - decision
---
# The plan fixer and the translator are role types

Both have an agent file under `.claude/agents/`, a contract under `docs/roles/types/` and a row in
`docs/roles/need-to-know.yaml`, so the catalogue counts them. The plan fixer answers the critic's and the verifier's
findings by editing the task files not yet built; the translator renders a finished document into
`<stem>.<language>.md` beside its source in the run folder, never a tracked file (manager spec, question 13, answer (a)).

## Record and source
- [Plan fixer contract](../../docs/roles/types/plan-fixer.md)
- [Translator contract](../../docs/roles/types/translator.md)
