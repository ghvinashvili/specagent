---
title: What loads in a session is the manager's decision, never a global install
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [main]
sources: []
decided: 2026-10-30
by: owner
review: 2027-10-31
why: a plugin enabled at user scope loads its skills and hooks into the manager chat and every plain session, whether or not that session needs it
decision_status: decided
would_change_if: Claude Code gains a per-session enable that needs no launch flag and no project settings
---
# What loads in a session is the manager's decision, never a global install

**Rule.** Which plugins a session loads is the manager's decision, session by session. A plugin installed at user scope must not load into the manager chat or into the agents: being installed is not being loaded.

**Why.** A plugin enabled at user scope loads its skills and hooks into the manager chat and every plain session, whether or not that session needs it. The owner decided that a global install must not decide what the chat and the agents load; the manager decides when and what is loaded.

**How to apply.**
- A plugin's files may sit in the user's plugin cache (the harness installs every plugin there, the template's own included); only enabling it loads it.
- Enable nothing from a project at user scope, which keeps only the owner's own chat tools; a plugin an install enabled there by itself is disabled there.
- Enable a project's plugins in that project's own settings, so they load in that checkout alone.
- An agent loads what its launch gives it: a plugin directory for a plugin outside its project, a settings-sources limit that keeps user settings out, a strict flag for MCP; the watcher config (`_agents.json`, `common`) records what a run's sessions load.
- The manager chat loads only user scope plus the checkout's project settings; a plugin under evaluation is never enabled for it.

Related: [[sessions-close-by-the-watcher]].
