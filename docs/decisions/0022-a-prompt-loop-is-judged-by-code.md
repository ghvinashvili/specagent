---
status: accepted
date: 2026-10-04
decision-makers: the human, who approved the brief and the plan of run 20261004-121154-fix-w2-state-and-loops
consulted: harness maintainers
informed: all package owners
---

# A prompt loop is judged by code, and the night path ticks once and only when there is work

## Context and Problem Statement
`harness loop tick` judges an iteration by the run it created (`docs/loops/README.md`), and a `prompt` loop creates
none: the poll loop counted neither progress nor spend, and its `exit.success` ("no run has the status created,
running, waiting_human or paused") was never checked. At night `ops/night-tick.sh poll` started a manager session on
every fire, 54 times a night, also when no run was open; that session ticked through the loop-tick skill, and the poll
loop's prompt file `.claude/loop.md` ticked again, so every fire counted two iterations.

## Decision Drivers
* A loop's goal, its hard stops and its progress are checked by code, not by a session's reading of a sentence.
* A night with nothing to do costs no model session.
* One fire is one iteration.
* `.claude/loop.md` stays the poll loop's prompt: Claude Code's `/loop` runs that file itself, and no run's branch
  changes it.

## Considered Options
* `exit.check`, a closed list of conditions code checks (today one, `no_active_runs`), required for a prompt loop; a
  deterministic pre-check, `harness loop due`, before every night session
* `exit.command`, a shell command whose exit code says whether the goal holds
* Count a second tick within a short time as the first one, and keep a session on every fire

## Decision Outcome
Chosen option: the first.

* A loop file states the success of a prompt loop as `exit.check` (`schemas/loop.schema.json`; required when
  `action.kind` is `prompt`). `harness loop tick` checks it at every tick of a prompt loop and prints `exit` with rule
  `success` when it holds. The one condition, `no_active_runs`, is what the poll loop's sentence says; a new condition
  is code and schema, added when a loop needs it (Article IV of `specs/constitution.md`).
* Progress of a prompt iteration: what it leaves on disk is the state of the runs it acted on. Its key is the sha256 of
  every readable run's id, status and `changed_at` (which moves only when a status, gate, approval, attempt or
  escalation changed, ADR-0010), taken at the next tick; the same key `no_progress_after` times in a row ends the
  episode with `no_progress`, as for a pipeline loop. The loop state keeps the last `no_progress_after` keys.
* Spend of a prompt iteration: the part that can be measured is the cost of the sessions the night path starts. Each
  fire writes the session's JSON output to `<runs root>/_audit/night-tick/<loop>-<UTC time>.json`, named when the
  session ended; a tick sets `spent_usd` to the sum of `total_cost_usd` of the files of its loop dated in the episode,
  and `max_usd` binds on it. An iteration run in the open manager session (`/loop`) leaves its cost nowhere the harness
  reads (OpenTelemetry `claude_code.cost.usage` carries it, `docs/quality/OBSERVABILITY.md`); it counts as nothing.
* `harness loop due --name <loop>` decides, without a model and without a tick (the loop state is neither written nor
  counted), whether a night session has anything to do: not while the pause switch is set (ADR-0023), nor for a loop
  that is disabled, not ready, has a context entry a tick cannot read, or runs in CI; not for a prompt loop whose exit
  check holds; and for the loop that acts on runs (exit check `no_active_runs`) only when `harness poll --all-active`,
  run there, printed an action the manager carries out (`resume`, `gate`). That poll sends its notifications
  (`HARNESS_NOTIFY_CMD`) as every `harness poll` does, so the human is told at night without a session. With
  `--plain` it prints the message for the session, or why there is none as one JSON line.
* The message: a prompt loop's file ("Read `<file>` and do exactly what it says in this turn."), which ticks by itself,
  and `/loop-tick <loop>` for any other loop, so that one fire ticks once. A passed gate is printed by one poll only, so
  the gate actions of the pre-check's poll are handed to the session in the message.
* `ops/night-tick.sh` runs the pre-check first and starts `claude` only when it says due; the reason of a fire without
  a session goes to `<runs root>/_audit/night-tick-<date>.jsonl`.

### Consequences
* Good, because a night with no open run, or with every unit still working, starts no session, and every fire counts
  one iteration.
* Good, because the poll loop ends by code when no run is open, and a week of polls that changed nothing ends it too.
* Bad, because the pre-check runs gates at night as any poll does, and a passed gate reaches the session through its
  message rather than through its own poll.
* Bad, because the spend of the open session's `/loop` is not counted; `max_minutes` and the OpenTelemetry cost alert
  bound it.

### Confirmation
`packages/harness/tests/test_loops.py` (exit check, progress, night spend, `loop due`) and
`packages/harness/tests/test_night_tick.py` (the script with stand-ins for `uv` and `claude`).

## Pros and Cons of the Options

### `exit.command`
* Good, because any condition a command can check fits.
* Bad, because no second condition is named, and a command would run at every tick of a loop that ticks every five
  minutes.

### Count a second tick as the first, keep a session on every fire
* Good, because no file changes but loops.py.
* Bad, because "a short time" is a guess, and the 54 sessions a night stay.

## More Information
The wording of `.claude/loop.md` after an `exit`, and two lines of `.claude/skills/loop-tick/SKILL.md`, are changed by
the manager after the run is integrated (the plan of run 20261004-121154-fix-w2-state-and-loops, "Changes for the
manager"): no run's branch changes a file under `.claude/` (ADR-0015).
