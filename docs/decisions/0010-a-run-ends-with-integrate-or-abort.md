---
status: accepted
date: 2026-10-03
decision-makers: the human, with two role-less sessions (server-19, server-e6) that drafted it apart and merged it
consulted: harness maintainers
informed: all package owners
---

# A run ends with integrate or abort, and what a run leaves behind is reported

## Context and Problem Statement
A run that is not taken to the end left everything it started behind it. On 2026-10-03 the machine held fourteen
unfinished runs, twenty background sessions of earlier runs (six of them idle processes of about 300 MB each, four
woken together by Claude Code's service after an update), two checkouts with uncommitted work and a marketplace
registered at a folder that no longer existed. The documents promised a way out that did not exist: the manager may
"abort a run" (`MANAGER.md`), a stage out of attempts is offered "resume with a message, refreeze, or abort", the run
state schema has `aborted`, and no code wrote it. A loop whose last run was abandoned waited for ever, because a run
that is not finished counts as active. `harness integrate --clean`, the one cleanup, refused every run that was not
finished, and it removed checkouts with `git worktree remove -f -f`, which discards uncommitted work unasked.

## Decision Drivers
* Nothing a run started may stay behind it unnoticed, and nothing it produced may be lost.
* The human decides when a run is over; no age or rule decides it for them.
* A mechanical step is a command, not a rule the manager must remember (tokens, forgetting).
* The run folder and the transcripts are the record and stay.

## Considered Options
* A command that ends a run (`harness abort`), with guards, prevention and a report of leftovers
* A one-time cleanup and a manager rule
* Automatic expiry: a run untouched for a day is aborted and its files removed

## Decision Outcome
Chosen option: "a command that ends a run", because the documents already name it, a loop cannot recover without a
final status, and a rule would be forgotten as it was.

* `harness abort --run <id> --reason "<text>"` ends a run that was not integrated: every session of the run is stopped
  and taken out of the session list (the transcript stays), every checkout of the run is removed after its uncommitted
  work (tracked and untracked files; ignored files are not kept) is saved as a commit under
  `refs/harness/salvage/<run-id>/<checkout>`, branches with commits stay, the run folder stays, and the state records
  `status: aborted` with `aborted: {at, reason, from}`. A second abort reports what is there and changes nothing. A run
  whose `run/<run-id>` exists was integrated: abort refuses and names `harness integrate --run <id> --clean`.
* No command changes an aborted run: every command that takes `--run` is declared as reading or changing a run in
  `cli.RUN_COMMANDS`, a changing command refuses an aborted run (`run_aborted`) before it does anything, and a test
  takes the commands from the parser itself, so that a new command must be declared. `poll` reports an aborted run
  without writing, `watch` returns at once, and a loop counts an aborted run as a failure. A role session does not
  steer its run: with `HARNESS_ROLE` set, every changing command and `abort` refuse (`role_session`), save the gate
  preview its stop hook asks for; every session may run `uv run *`, and abort and integrate run outside the sandbox.
  The launcher also denies a role session, by permission rules, every command of `sandbox.excludedCommands` (of the
  project's `.claude/settings.json` and `.claude/settings.local.json`, which Claude Code merges): such a command runs
  code a writer can change in its own checkout, so it was a way out of the sandbox for any of them.
* `harness integrate` never rewrites an existing `run/<run-id>`: with `--clean` it only cleans, and the branch is built
  again only after the human deleted it. Its cleanup saves uncommitted work the same way as abort, and a run that
  committed nothing (a planning run) is closed by `--clean` alone. A checkout whose work cannot be saved, or that
  git cannot remove, stays and is named (`not_removed`). Both commands take the stages the run was made with.
* `poll` stops (does not remove) the idle session of a unit whose stage is done and needs no approval; `harness
  resume` continues a stopped session, so nothing is lost.
* The state records `changed_at`, the time of the last change of what matters (statuses, gates, approvals, attempts,
  escalations); `updated_at` keeps meaning "last looked at", which the status line and loops read. A run made
  before `changed_at` existed takes the time of its last write.
* `harness.leftovers` names what a run left behind: an open run unchanged for 24 hours with no unit working; a live
  session of an aborted run or of a finished stage, by the job ids the runs recorded; a checkout under
  `.claude/worktrees/` that belongs to no open or finished run and a prunable checkout record; a finished run
  unchanged for 24 hours whose sessions or checkouts are still there (`unclosed_run`); a registration of this project's
  marketplaces (its own and `harness-internal`) or plugin install at a path that is gone; another checkout beside a
  marked `runs/`. `harness run` returns the open runs (`open_runs`) and the manager asks the human about each in one
  line; `harness doctor` shows the leftovers as an optional check with the command that removes each.

### Consequences
* Good, because an abandoned run ends with one command, a loop recovers, and finished sessions no longer hold memory.
* Good, because no work is discarded unasked: uncommitted work becomes a ref the human can restore.
* Bad, because every command that takes `--run` must be declared, and refs under `refs/harness/salvage/` stay until the
  human deletes them (`git update-ref -d`).
* Bad, because a session moved to a new folder by a move of the checkout is not attributed to any run; such leftovers of
  a move are cleaned once, by hand.

### Confirmation
Tests in `packages/harness/tests/test_abort.py`; `harness doctor` shows the leftovers check.

## Pros and Cons of the Options

### A one-time cleanup and a manager rule
* Good, because nothing is built.
* Bad, because the next abandoned run leaves the same, the rule spends tokens and is forgotten, and a loop still waits for
  ever: no command can write a final status.

### Automatic expiry
* Good, because nothing piles up.
* Bad, because a run may rightly wait days for a human, and removing files nobody asked to remove loses work.

## More Information
The design was written by two sessions apart and merged (2026-10-03); the facts it rests on were checked on this machine:
`claude rm` keeps the transcript and refuses to remove a worktree with unpushed commits; `claude stop` keeps the
conversation, and `harness resume` continues with `claude --resume <session-id> --bg`.
- Amended on 2026-10-04 by `docs/decisions/0019-a-role-session-runs-only-the-harness-commands-listed-for-it.md`: a
  role session runs only the harness commands listed for it.
