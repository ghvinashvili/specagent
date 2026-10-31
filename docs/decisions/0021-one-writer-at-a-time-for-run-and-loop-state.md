---
status: accepted
date: 2026-10-04
decision-makers: the human, who approved the brief and the plan of run 20261004-121154-fix-w2-state-and-loops
consulted: harness maintainers
informed: all package owners
---

# One writer at a time for the state of a run and of a loop

## Context and Problem Statement
Run state lives in JSON files on disk (ADR-0002), and several commands write the same file: `harness watch` polls in
the background every 20 seconds while the manager launches, resumes, approves and aborts. The audit of 2026-10-04
showed what nothing stopped: `harness poll` wrote back the copy of `state.json` it had read before it gated a unit (a
write stage's gate runs the whole suite for up to 1800 s) and undid an approval and an abort recorded meanwhile; launch
and resume did the same around a print session; two saves shared one temporary file, `state.json.tmp`, so a save raised
and readers met half a file, which then made every later save raise; `logs/notified.json` was written in place and two
polls could announce one action twice; two ticks of one loop both started an iteration.

## Decision Drivers
* A recorded approval, abort or answer is never undone by a command that did not change it.
* A reader meets the old file or the new one, never half of one.
* No lock is held while a session or a gate runs: the human's approval must not wait half an hour for a test suite.
* A lock left by a process that died stops nobody.
* One rule for every writer, so that a new command follows it without a decision of its own.

## Considered Options
* One flock per state file around read, change and write; a writer that ran a session or a gate since it read the
  file reads it again under the lock and carries over only what it did itself
* One lock per run, held for the whole command
* No lock: compare the file's time before the rename and try again
* Lock files made with O_EXCL that carry the holder's process id

## Decision Outcome
Chosen option: the first.

* The files: a run's `state.json`, its `logs/notified.json`, and a loop's `_loops/<name>/state.json`. Each has one lock,
  an exclusive `flock` on `<file>.lock` beside it (`state.locked`). The kernel drops it when its holder's process ends,
  so a lock left by a process that died stops no later writer; the lock file stays and holds nothing.
* Every write goes through a temporary file of its own, `<file>.<pid>.<random>.tmp`, and a rename, the only step that
  touches the file (`state.write_atomic`, used by `state.save`).
* The writers of a run's `state.json` and what each does under the lock: `state.approve` and `state.refreeze` read,
  change and write, and refuse an aborted run; `harness gate` runs the gate first and then reads, records the verdict
  and writes; `harness poll` reads first without the lock, gates and looks, then under the lock reads again and takes
  its record of a unit only where no other command changed that unit since it read it (a unit changed meanwhile keeps
  the other command's record and poll's actions for it are dropped); approvals, aggregates and the run's status come
  from the merged state; `harness launch` and `harness resume` run `claude` without the lock and then carry over what
  they did to their unit (its changed fields, the ids they added, the escalation they marked answered, the print cost,
  the run's status and time); the wave split of a sharded launch writes its shard records under the lock;
  `harness abort` stops sessions and removes checkouts without the lock and then records `aborted` over the file as it
  is. `state.create_run` writes a file nobody else knows yet. No writer changes a run that is aborted when it takes
  the lock: an aborted run is a record (ADR-0010).
* `logs/notified.json`: `notify.after_poll` decides and records what to announce under the lock and sends the lines
  after it has let the lock go.
* A loop's state: `harness loop tick` holds the lock from its read of the loop state to its write. A tick runs no
  session and no gate (a `command` action's command runs under it), so a second tick of the same loop waits and then
  sees the first tick's iteration: one tick of a loop at a time.

### Consequences
* Good, because what a command records stays, whoever writes next, and a reader never meets half a file.
* Good, because the manager's commands never wait for a gate or a session, only for another command's few
  milliseconds of read, change and write.
* Bad, because `fcntl.flock` is POSIX: Linux, macOS and WSL2, the platforms `harness doctor` accepts. A holder that is
  stopped (not dead) keeps its lock until it goes on or ends.
* Bad, because a lock file stays beside each state file, and a poll whose unit was changed meanwhile drops its finding
  for that unit until the next poll.

### Confirmation
`packages/harness/tests/test_state_writers.py` (a dead holder, a temporary file per save, writers at once, approve and
abort while poll gates, a unit changed meanwhile, every writer waits for the lock, launch and resume around a print
session), `packages/harness/tests/test_notify.py` and `packages/harness/tests/test_loops.py` (two ticks at once); the
audit's probes `p03_stale_state_saved.py`, `lost_update.py` and `save_tmp_race.py` exit 0 on the work.

## Pros and Cons of the Options

### One lock per run, held for the whole command
* Good, because a command sees no other writer from its first read to its last write.
* Bad, because poll would hold it through every gate, and an approval or an abort would wait up to 1800 s.

### No lock: compare the file's time and try again
* Good, because nothing is held.
* Bad, because the check and the rename are two steps another writer can come between; every writer needs a retry
  loop.

### Lock files made with O_EXCL
* Good, because they work on every platform.
* Bad, because a holder that died leaves a lock that only a guess about its process id can clear, and process ids are
  used again.

## More Information
Amends [ADR-0002](0002-state-on-disk.md): run state stays in JSON files on disk, and every writer of a state file now
holds its one lock. The findings it answers are 01/F03, 02/F01, 02/F02, 02/F09 and 05/F30 of the audit of 2026-10-04
(`context/fix-20261004/wave-2-concurrency-and-loops.md`).
