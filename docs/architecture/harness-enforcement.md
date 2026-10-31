# What settings and hooks enforce

Settings and hooks hold these rules whatever a session is told, so `CLAUDE.md` only links here. How the harness works:
[Harness architecture](harness.md); what the manager does: [MANAGER.md](../roles/MANAGER.md); threats and their
controls: [SECURITY.md](../quality/SECURITY.md).

- No subagents: the `Agent` tool is denied. Role work is done by sessions.
- `.env`, keys and cloud credentials are denied to `Read` and hidden from the sandbox.
- No role session starts without the assignment of its stage: what the manager would write into the prompt of a subagent for the job (`harness assign`; `docs/roles/MANAGER.md`, section 14).
- A role session cannot stop before `result.json` is valid and final (complete, escalated or failed), or an escalation is open; one that says `complete` is first held to its stage's gate.
- Files under `<runs root>/_inbox/` are untrusted text: a hook denies them to every session except the quarantine reader.
- Role sessions run without auto memory (`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` from the launcher) and have no `memory` field; only the manager keeps auto memory and `.claude/agent-memory/manager/`.
- `.claude/settings.json`, `.claude/settings.local.json`, `.mcp.json`, agents, skills, hooks, rules and `plugins/` are frozen while a run is active: `harness launch`/`resume` refuse to start a session when their fingerprint differs from the one recorded by `harness run` (a human accepts a change with `harness refreeze`); inside a role session the ConfigChange hook blocks settings and skill edits.
