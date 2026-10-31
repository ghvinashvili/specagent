---
title: The manager runs without the sandbox, with four guards
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: the manager does what the sandbox refuses the roles (merges in any worktree, .claude and .git administration, sessions launched and stopped, transcripts read, the vault pushed); every role stays sandboxed and blind
would_change_if: a sandbox can grant those operations to one session without opening them to the roles, or a guard fails once
decision_status: decided
scope: global
tags:
  - decision
---
# The manager runs without the sandbox, with four guards

Every role of a pipeline runs sandboxed and blind. The manager does what that sandbox refuses the roles: merges in any
worktree, `.claude/` and `.git` administration, data moved between disks, sessions launched and stopped, transcripts
read for measurements and the vault pushed. On 2026-10-29 at 17:03 UTC the owner chose answer (a) to question 2 of the
manager spec, the rule the owner had set at 14:32 UTC: the manager runs without the sandbox, and four guards take its
place. They are the permission rules (never read the credentials under `~/.config`, never push the template), the
auto-mode classifier (an irreversible deletion is refused and left to the owner), the owner's launch rule (agents and
the judge start only with the owner's yes) and the rule that the manager never runs project code or tests itself.
Answer (b), the template's project sandbox with `excludedCommands` extended from `claude *` to merges and git
administration, was not taken; it would hold only if every exclusion could be listed and simulated first.

The template ships the guards as the `## No sandbox, four guards` section of `docs/roles/manager-chat.md`. The project
session's own sandbox stays as it is (the `sandbox` block of `.claude/settings.json`), and a role's refusal is answered
by supplying the path, the host or the material into the run folder, never by weakening a sandbox.

## Record and source
- [The manager in chat](../../docs/roles/manager-chat.md)
- [The sandbox sets itself up, and a refusal is reported](the-sandbox-sets-itself-up-and-a-refusal-is-reported.md)
- [Roles are blind to models and authors](roles-are-blind-to-models-and-authors.md)
