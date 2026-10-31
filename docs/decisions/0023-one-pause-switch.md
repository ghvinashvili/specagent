---
status: accepted
date: 2026-10-04
decision-makers: the human, who approved the brief and the plan of run 20261004-121154-fix-w2-state-and-loops
consulted: harness maintainers
informed: all package owners
---

# One pause switch

## Context and Problem Statement
The human can end a run (`harness abort`, ADR-0010) but cannot hold the harness: a usage window, a machine going to
repair or a night away left the night path, the loops and the manager starting and resuming sessions. The documents
promised a pause ("Control: pause, resume, stop a run", `docs/roles/MANAGER.md`), and no command made one.

## Decision Drivers
* While the human holds the harness, no session, loop iteration or night session starts or resumes.
* The state stays as it is, so that the same work goes on when the hold is lifted.
* Only the human holds and lifts it; a role session can do neither.
* Nothing that runs is cut off in the middle of its work.

## Considered Options
* One flag in the runs root, set and lifted by the human, honoured by every command that starts or resumes work
* A pause per run
* A switch that also stops every running session

## Decision Outcome
Chosen option: the first.

* The switch is `<runs root>/_pause.json` with the time and the human's reason, written through a temporary file of its
  own (ADR-0021). `harness pause set --reason "<words>"` sets it, `harness pause lift` removes it, `harness pause
  status` shows it. With HARNESS_ROLE set, `set` and `lift` refuse (`role_session`) and change nothing. A flag that
  cannot be read still pauses.
* While it is set: `harness launch` and `harness resume` refuse with `paused` before anything starts; `harness poll`
  answers `paused` with no action and writes nothing (no unit is looked at, gated or stopped, and nothing is sent);
  `harness poll --all-active` polls no run; `harness watch` returns at once; `harness loop tick` answers `wait` with
  `paused` and leaves the loop state as it is; `harness loop due`, and so `ops/night-tick.sh`, starts no night session.
* Sessions that run when it is set are left as they are: a background session finishes its turn and waits, a print
  session runs to its end. When the switch is lifted, the next poll sees how each ended and prints its actions. A
  human who wants a session to stop now stops it with `claude stop <job>`; `harness resume` continues it afterwards.
* `harness approve`, `harness gate`, `harness abort`, `harness integrate` and `harness run` are not held: they start
  no session, and the human's decisions are recorded while everything waits. `harness abort` stays per run and final.

### Consequences
* Good, because one command holds every run and every loop of the checkout's runs root, and one lifts it.
* Good, because nothing is lost: no state changes while it is set, and running work ends as it would have.
* Bad, because a session that runs when the switch is set still spends until its turn ends.

### Confirmation
`packages/harness/tests/test_state_writers.py` (launch, resume and poll while paused; a role session neither sets nor
lifts it), `packages/harness/tests/test_loops.py` (a paused tick; the CLI with HARNESS_ROLE set) and
`packages/harness/tests/test_night_tick.py` (a paused fire starts no session).

## Pros and Cons of the Options

### A pause per run
* Good, because one run can wait while another goes on.
* Bad, because the loops and the night path start runs and sessions of their own, which a per-run flag does not hold.

### A switch that also stops every running session
* Good, because nothing spends from the moment it is set.
* Bad, because a session cut off in the middle of an edit resumes from its checkpoint and redoes the work; a human
  who wants that stops the session by hand.

## More Information
`docs/roles/MANAGER.md` (section 1) and `docs/roles/HUMAN.md` name the switch; `.claude/agents/manager.md` names it
after the manager's change that the plan of run 20261004-121154-fix-w2-state-and-loops lists.
