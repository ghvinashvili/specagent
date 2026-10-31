# Connections between chats

One rule: sessions talk through files with schemas, and `harness` decides who runs when. A role session receives exactly
two kinds of message: its first prompt and a resume. It sends none; it writes files.

| Group | How it is done here | Where |
| --- | --- | --- |
| Message | first prompt (the brief, the stage's assignment written by the manager as it would write the prompt of a subagent, the input paths); resume with the gate's failing checks or an escalation answer; the stop hook's answer when the stage's gate would refuse a `complete`; no session-to-session messages (`crossSessionInbound: refuse`) | `launch.render_prompt`, `launch.assign`, `resume.py`, `launch.session_flags`, `.claude/hooks/stop-gate.py` |
| Shared state | the run directory beside the repository, written only by `harness`, validated by `schemas/` | `docs/roles/RUNS.md`, `state.py` |
| Tool layer | the `harness` CLI; one read-only MCP server for the manager; per-type `tools`; no MCP in role sessions | `cli.py`, `.mcp.json`, `.claude/agents/` |
| Task handoff | stage to stage through a gate; outputs by path; `result.json` by schema; untrusted text only as a digest | `docs/roles/stages.yaml`, `docs/roles/pipelines/`, `gates.py`, `intake.py` |
| Events | hooks; `harness poll` over `claude agents --json`; `/loop`, the night tick and CI cron as time triggers | `.claude/settings.json`, `poll.py`, `docs/loops/README.md` |
| Orchestration | one manager, stage tables as patterns, loops above runs; no subagents, teams or workflows inside a run | `docs/roles/MANAGER.md`, `docs/roles/PATTERNS.md`, `loops.py` |
| Failure handling | retry is resume; `max_attempts`, `max_minutes`; limits wait; escalation files; runbooks | `docs/quality/RELIABILITY.md`, `docs/quality/LIMITS.md`, `docs/runbooks/` |
| Cost | model and effort per stage; budgets on print stages and loops; frozen configuration for the cache; context audit | `docs/quality/OBSERVABILITY.md`, `docs/quality/CONTEXT_BUDGET.md` |

## Mechanisms that are deliberately absent
Subagent returns, agent teams, `SendMessage` to roles, channels, cloud routines for runs, A2A, a message queue or event bus,
a shared vector store, `/batch` and dynamic workflows inside a run. The reasons are in
`docs/decisions/0001-role-chats-are-sessions.md` (sessions, not subagents), `docs/decisions/0002-state-on-disk.md` (files, not
messages), `docs/architecture/knowledge.md` (no vector store) and `docs/roles/PATTERNS.md` (what does not transfer).
