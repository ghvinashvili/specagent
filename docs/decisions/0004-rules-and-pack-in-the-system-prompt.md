---
status: accepted
date: 2026-10-02
decision-makers: platform team
consulted: harness maintainers
informed: all package owners
---

# Role rules and the knowledge pack follow the agent file in the system prompt

## Context and Problem Statement
ADR-0003 put the knowledge pack at the top of the first user message and left the project's root instruction files
(`CLAUDE.md`, `AGENTS.md`, `.claude/rules/harness.md`) to Claude Code's own loading. Measured on a live reader
session, those files were 3,895 of the 14,030 tokens of the first request, written for the manager and the human,
and every session wrote them to the cache again. Sessions of one type shared nothing beyond the tools and the
agent file, because the cache is shared between sessions only up to the end of the system prompt.

## Decision Drivers
* What every session of a type needs should be read from the cache by the second session of the type.
* A role session should not load a map written for somebody else.
* The system prompt of a session must not change during a run.

## Considered Options
* Pack in the first user message (ADR-0003)
* Pack and role rules appended to the system prompt with `--append-system-prompt-file`

## Decision Outcome
Chosen option: appended to the system prompt. At launch the harness writes `<stage dir>/pack.md` once: the role
rules (`role_rules` in `docs/roles/need-to-know.yaml`), then the type's pack (`pack_files` and the wiki pages for its
audience). The file is passed with `--append-system-prompt-file` on launch and on every resume. The root instruction
files are excluded from Claude Code's own loading for role sessions (`claudeMdExcludes`), and the git snapshot is off
(`includeGitInstructions`). Since ADR-0006 the two root files reach every role session through `pack_files`: a
session may not know less about the project than a subagent would, and in the system prompt they are shared.
The brief stays the first user message, as ADR-0003 decided.

### Consequences
* Good, because the second session of a type reads the rules and the pack from the cache: measured, its first
  request read 13,819 tokens and wrote 8,595, against 4,831 read and 18,546 written before.
* Good, because a role session's first request is smaller: 12,899 tokens against 16,375 for a background reader.
* Bad, because the flag must be passed again on every resume; `launch.session_flags` is the one place that does it.
* Bad, because a rule or wiki change during a run does not reach running sessions. That is intended: `pack.md` is
  written once, and a human accepts a configuration change with `harness refreeze`.

### Confirmation
`packages/harness/tests/test_access.py` checks the exclusions and the pack; `harness pack --check` checks every pack
against the budget; `harness cache-report --run <id>` shows `first_request_read` per session.

## More Information
Layers of a role session's request, most stable first:

| Layer | Content | Shared between |
| --- | --- | --- |
| tools | the tool list of the agent file | every session of the type on the same model |
| system prompt | agent file, role rules, knowledge pack | every session of the type in this repository while the pack is unchanged |
| first message | brief, stage, input paths | nobody; within one session, every later request |
| conversation | tool calls and results | nobody |

Compressing the text of the pack is not done: the cost of a session is dominated by cache writes and output, and
shortening instructions by rewriting them lowers accuracy more than it saves (design record, `CACHE-DESIGN.md` in the owner's vault, `context/design-record/CACHE-DESIGN/`; was `design/CACHE-DESIGN.md`).
What is done instead: a type gets only the pages written for it, and test output goes to a file.
