---
status: accepted
date: 2026-10-02
decision-makers: platform team
consulted: harness maintainers
informed: all package owners
---

# A conversation hands itself off before Claude Code compacts it

## Context and Problem Statement
The manager's conversation runs for hours. When it reaches the point where Claude Code compacts it, the summary keeps
the outline and loses the detail: which decision was made and why, what was tried, the exact next step. Sessions that
already work well over long stretches write a handoff first: before the compaction the session writes what a fresh
context needs into a file of the project, and after it reads the file back. A project started from this template had
that only where the person's own user settings supplied it.

## Decision Drivers
* A project started from the template goes on after a compaction on any machine.
* The manager's notes name who did what, the budget and the models: no role session may read them.
* The notice comes before the compaction wherever the compaction point is: windows differ (200,000 tokens, 1M), and
  so do the settings that move the point.
* A session is asked once, also where the person's own settings already run such a hook.
* The conversation goes on after the compaction from its main points, and no copy of it is kept. What is kept is
  read again: a transcript fills the next context with talk instead of the documents, instructions and sources the
  work needs, while the main points are what the conversation needs to go on.

## Considered Options
* Leave it to each person's user settings.
* A hook of the project, for the manager's and a human's sessions.
* The same hook for role sessions too.

## Decision Outcome
Chosen option: "A hook of the project, for the manager's and a human's sessions" (`.claude/hooks/handoff.py`),
because it travels with every project and leaves the rules of role sessions as they are.
* At 92 % of the compaction point it asks for `docs/handoff/<date>-<time>-handoff.md`: the goal, what is done and in
  progress, the decisions and why, the open problems, the exact next steps, the files and commands that matter. At
  97 % it asks to bring the file up to date. The point is computed from the window the status line reports,
  `CLAUDE_CODE_AUTO_COMPACT_WINDOW` and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`; with auto-compact at 60 % the notices come
  at 55 % and 58 % of the auto-compact window.
* The handoff holds the main points of the conversation (what the user wants and why, what was agreed, what is
  still open) and the state of the work; it is never a copy of the conversation, and no transcript is kept. After
  the compaction the hook asks the session to read the newest handoff, and a manager the run's `HANDOFF.md` too.
* `docs/handoff/` is not committed and is closed to every role type. The project's permissions let a session write
  there without a prompt (`Edit(./docs/handoff/**)`), so a notice does not stop the human.
* A role session is left out: its handoff is its checkpoint, `progress.md`, which the SessionStart hook gives back
  after a compaction.
* When the person's user settings already run a hook whose command names `handoff`, the project's hook stays silent.

### Consequences
* Good, because a compaction no longer loses what the conversation decided, on any machine.
* Good, because the notices follow the real compaction point; a fixed share of the window misses it when the window
  or the settings change.
* Bad, because the notices need the numbers of the status line: a session without the project's status line gets
  the reminder after the compaction and no notice before it.
* Neutral: the session writes the handoff in its own words; no script summarises anything.

### Confirmation
`packages/harness/tests/test_hooks.py` covers the notices, the compaction point, the sessions left alone, the main
points the handoff asks for, and that no copy of the conversation is kept; `harness docs-check` does not treat a
handoff as a document.
