---
status: accepted
date: 2026-09-25
decision-makers: platform team
consulted: harness maintainers
informed: all package owners
---

# Role chats are full Claude Code sessions; subagents are denied

## Context and Problem Statement
Role work (read, plan, write, verify, critique, judge) must survive crashes and limits, be resumable by id, and be observable from the shell. Subagents cannot be resumed from another session and their transcripts are internal.

## Decision Drivers
* Resumability by session id (`claude --resume <id> --bg`)
* Observability from a script (`claude agents --json`)
* Independent permission and tool sets per role

## Considered Options
* Subagents in one session (`.claude/agents/` used through the Agent tool)
* Agent teams (experimental; interactive lead required, no resume)
* Full sessions launched with `claude --agent <type> --bg` or `claude -p --agent <type>`

## Decision Outcome
Chosen option: full sessions, because they are resumable, listable and isolated; the same agent files still define the role's instruction, tools and model.

### Consequences
* Good, because a crashed role continues from its own session and its files.
* Bad, because coordination is by files and polling; the manager cannot steer a role mid-turn.

### Confirmation
`permissions.deny: ["Agent"]` in `.claude/settings.json`; no role type lists `Agent` in `tools`, and `harness validate` rejects one that does. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` only turns nesting off and is not one of the controls.

## More Information
Anthropic's guidance warns that role-based decomposition raises coordination cost; artifacts are therefore always files, never chat summaries. Revisit when agent teams leave experimental status.
