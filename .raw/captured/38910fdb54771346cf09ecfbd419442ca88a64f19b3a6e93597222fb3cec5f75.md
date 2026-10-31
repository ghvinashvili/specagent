---
title: ECC texts live under .claude/ecc
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-30
audience: [all]
decided: 2026-10-30
by: owner
why: the owner asked why ECC's skills sit under .claude while its agent texts sit elsewhere; the manager never remembers material it does not find in one place
would_change_if: the manager reads the ECC texts reliably from another place, or the template stops carrying ECC texts
decision_status: decided
scope: global
tags:
  - decision
---
# ECC texts live under .claude/ecc

Every ECC text the template carries is in one place, `.claude/ecc/`: the 70 agent texts and their list in `agents/`, and the
pages about the pin (`sources.md`, `sources.summary.md`, `files.md`, `hook-recipes.md`). `.claude/ecc/README.md` is the
catalogue: one line per agent text, one per ECC skill with the role types it suits and when, and one for the rules. The
manager reads it before it writes a brief for a role with a domain. The skills stay in `.claude/skills/` and the rules in
`.claude/rules/ecc/`, where Claude Code loads them; the catalogue points to both. A type's row in
`docs/roles/need-to-know.yaml` may list `skills:`, which the harness adds to the skills of the agent file. The ECC texts are
not changed by the move (their sha256 at the pin is tested).

## Record and source
- [Spec 004 consolidation, item S2](../../specs/004-consolidation/spec.md)
- [ECC catalogue](../../.claude/ecc/README.md)
- [ECC content is pinned, never its mechanism](ecc-content-is-pinned-never-its-mechanism.md): the sentence of 2026-10-29 about where the agent texts sit, which this decision revises
- [ECC text reaches a brief by line range](ecc-text-reaches-a-brief-by-line-range.md): the folder of the copies a `Spec:` line names, which this decision revises
