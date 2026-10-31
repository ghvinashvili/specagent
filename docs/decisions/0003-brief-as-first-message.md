---
status: accepted
date: 2026-09-25
decision-makers: platform team
consulted: harness maintainers
informed: all package owners
---

# The default instruction is the agent file; the project brief is the first user message

## Context and Problem Statement
Prompt caching matches an exact prefix in the order tools → system → messages. A per-type default instruction must be cached across projects; a project brief changes per run.

## Decision Drivers
* Cache hits on the system prefix across projects and resumes
* System prompt flag text is recorded on the conversation's first request and reused on `--resume` only until compaction; after compaction a brief passed with `--append-system-prompt` would leave the system prompt unless every resume passes it again, while `--agent` is restored by `--resume`

## Considered Options
* Brief appended to the system prompt (`--append-system-prompt`)
* Brief as the first user message; default instruction in `.claude/agents/<type>.md`

## Decision Outcome
Chosen option: brief as first user message, because the system prefix stays byte-identical per type and `--resume` restores the agent automatically.

### Consequences
* Good, because a resumed session keeps its instruction without re-passing flags.
* Bad, because the brief competes with other user turns for attention; it is therefore also on disk (`brief.md`) and re-pointed to by the SessionStart hook after compaction.

### Confirmation
`harness launch` never passes `--append-system-prompt`; the configuration fingerprint check in `harness launch`/`resume` (settings, `.mcp.json`, agents, skills, hooks, rules) and the ConfigChange hook keep the tool set unchanged during a run.

## More Information
Tool definition changes invalidate the whole cache; plugins are enabled per project, not toggled mid-run.

The layers of a role session's request, and where the knowledge pack sits, are in
[ADR-0004](0004-rules-and-pack-in-the-system-prompt.md), which moved the pack from the first message into the system prompt.

The match is exact and from the start only. Each model has its own
cache. The lifetime counts from the start of a request; a pause longer than it makes the next request reprocess the
whole conversation, and that is the largest measured loss (rule in `.claude/rules/harness.md`). The lifetime is chosen
per role type (`cache_ttl` in `docs/roles/need-to-know.yaml`, set through `CLAUDE_CODE_PROMPT_CACHE_TTL`): five
minutes for every type, because a one-hour write costs 2 times the base input price and a five-minute write 1.25 times,
and a session that backgrounds its long commands never pauses past five minutes (measured on 2026-10-02: a planner at
one hour paid 1.06 $ more and paused 212 seconds at most). A type that waits longer sets one hour in its row. `harness cache-report` reads the usage blocks of the session
transcripts and prints the hit ratio, every miss and its likely cause.
- Amended on 2026-10-04 by `docs/decisions/0016-a-stage-at-max-effort-keeps-its-cache-for-an-hour.md`: one hour
  for every type but the two that keep a low effort of their own.
