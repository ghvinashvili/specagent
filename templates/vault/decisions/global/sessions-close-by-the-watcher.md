---
title: Sessions close by the watcher, never by the owner
type: decision
scope: global
kind: lesson
template: yes
status: verified
updated: 2026-10-31
audience: [main]
sources: []
decided: 2026-10-30
by: owner
proof: [context/measurements/2026-10-30-pipeline-fold.md]
why: closing a background session must never wait for the owner; the auto-mode classifier refuses `claude stop` to the main session
decision_status: decided
would_change_if: the main session is allowed `claude stop` by a permission rule and the watcher's stop proves unneeded in three runs
---
# Sessions close by the watcher, never by the owner

**Rule.** The template's watcher closes the sessions that are done; the owner is never asked to. The main session does not run `claude stop` itself.

**Why.** In a seven-task run, four idle sessions waited for a `claude stop` that the auto-mode classifier refused the main session, so the owner had to step in (the run's measurement page records the two owner-dependent stops). Closing sessions is the template's job.

**How to apply.**
- The watcher stops a final agent's live session: at its prompt at once; busy (a waiter shell shows as busy) once its record is `final_stop_minutes` (10) old, so a last commit is not cut. The end exit (`every STATUS line is final`) waits until every such session is stopped; `final_stop_minutes: null` leaves them live. The script is `watch_agents.py` of the template's pipeline skill (commit 9499e13, 2026-10-30).
- The classifier refuses the main session's `claude stop` (reason `Interfere With Workloads`) and the refusal holds for the same outcome by any other means. With no watcher running, one round of the watcher does the stops: `python3 -I scripts/watch_agents.py <agents.json> 1`.
- A session the main session cannot stop (one outside any watcher's config) is given to the owner as one command to run, never as a question.
- The owner's standing fix for the main session itself is the permission rule `Bash(claude stop *)` in `permissions.allow` of the user-level settings (added by the owner on 2026-10-30 as `Bash(claude stop:*)`): the main session may then stop a session itself; the watcher's stop stays the default.
