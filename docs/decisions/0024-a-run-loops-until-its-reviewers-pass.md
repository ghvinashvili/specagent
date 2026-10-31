---
status: accepted
date: 2026-10-08
decision-makers: the human, who approved the scheme and specs/002-run-loop on 2026-10-08
consulted: harness maintainers; a critic subagent that attacked the plan (30 findings) before the work
informed: all package owners
---

# A run loops until its reviewers pass

## Context and Problem Statement
Fix waves 1 and 2 (runs of 2026-10-04) both ended with the judge's `revise`: 27 reasons, of which 9 were promises in
documents, 10 edges, concurrency and malformed input, 5 a wrong approach (guards that read a shell command's text) and
3 mechanical; in wave 2, 7 of 13 were one job done differently in several places. Every `revise` meant a human starting
a new run. The two runs cost about $250 and $209 at API prices, 81% of it reading context; every stage had run at max
because the effort of the session that created the run raised the table's (specs/001-chat-depth, part 1, ADR-0011).
How does a run find these defects before the work, and loop on the rest by itself, without running away?

## Decision Drivers
* Fewer findings reach the end of a run; the ones that stay are found before the writer starts.
* Fewer cycles through the human; a loop that cannot run away (counters, a bound on writer starts, no repeat).
* Only proven findings go back; a writer cannot weaken the tests the plan and the critic give.
* The effort a stage gets is decided by its table, not by whoever created the run.

## Considered Options
* A human restarts every `revise` (as before).
* A critic in parallel with the verifier, after the work (as before), with a loop added.
* The critic before the writer, attacking the plan and its trial with attack tests, and loops back to the plan and to
  the writer (chosen).

## Decision Outcome
Chosen option: "the critic before the writer, with loops", because the w1 and w2 findings the critic made (4 that the
verifier missed, all about the plan's promises and documents) are cheapest before the work, and a loop inside the run
removes the restart through the human.

- Order (default table; `fix` without `read`): read → plan → attack (a critic of the plan and its trial; the human
  approves the plan with its translated one-page summary) → write (one session) → verify → judge (the human approves).
- `returns_to` and the table's `loop` block: `attack` returns to `plan` on the counter `plan`; `verify` and `judge`
  return to `write` on the counter `work`; 3 rounds per counter, 5 starts of `write` per run (`max_runs`). A round is
  taken by `poll` under the lock of `state.json` (`harness/rounds.py`): the reviewer's result moves to `rounds/<n>/`,
  the stage it returns to gets `rework` with `rework.md` (its proven findings, whole), every launched stage after it
  `recheck`; `harness resume --rework` continues them, and a recheck rebuilds its inputs, the work's checkout and patch,
  and its Material. The round is saved before its files move; a crash between the two is finished by the next poll.
- The loop stops for the human on a bound (`loop_cap`), on a round that brings back the findings of the round before
  or none (`no_progress`), and on the judge's `replan` or `reject`; only the last stage stops a run, a verifier's
  `reject` is a proposal for the judge. A stop asks for the reviewer's approval: `harness approve --decision approved`
  goes on with the work as it is, `harness abort` ends the run.
- Proofs: a `blocks` or `must fix` row of the attack and a `refuted` entry of the verifier carry an evidence entry with
  the command, its exit code and the finding named as `<stage>#<n>` (gates `attack`, `verify`).
- Protected tests: the test files the planner's trial adds and the critic's attack tests (new files a writer may add)
  go over the writer's branch in the write gate's suite, and their test modules run once more by name in a checkout
  whose conftest.py files and pytest options are the base's, with the pytest plugins of the base's `uv.lock` named by
  `-p` and no other loaded; a given conftest.py, helper or data file goes over that checkout too and is not run by
  name. The gate names a copy the branch changed. The judge reads the plan and the change as `changes.patch`, without
  a checkout.
- Reviewers are no longer independent of the critic: the verifier and the judge read its findings, so a finding is
  checked rather than found twice. The critic itself still reads no other reviewer.
- Model and effort: a stage runs with the table's values exactly; the creating session is recorded in the manifest and
  changes nothing; `harness run --effort <stage>=<level>` changes one stage for one run. Every stage of every table runs
  Opus at max but `classifier` and `quarantine-reader`; `max_minutes` tripled where the effort rose. This amends part 1
  of specs/001-chat-depth and ADR-0011.

### Consequences
* Good, because a writer starts from a plan the critic attacked, with acceptance tests it cannot weaken.
* Good, because a revise reaches the writer by itself, with the proof of every finding, bounded by counters.
* Good, because one place takes a round, and it survives a crash.
* Bad, because a recheck rebuilds the Material once and misses the prompt cache once.
* Bad, because one writer session carries the whole change: a run should change one mechanism (MANAGER.md, section 1).
* Bad, because max everywhere costs more than high; it stays until the first runs measure the stages (spec, part 7).
* Bad, because the code under test runs in pytest's own process, in the environment the branch's own `uv.lock` makes:
  a change that forges pytest's report from inside the product code, or from a dependency it adds, is out of the
  gate's reach. The verifier runs everything again in its own checkout and the judge reads `changes.patch`.
* Bad, because a given test that needs a pytest plugin the base does not lock fails in the protected run: such a
  plugin comes in by a run of its own first.

### Confirmation
`packages/harness/tests/test_rounds.py` (rounds, stops, crash, `--rework`, recheck, tables, HANDOFF),
`packages/harness/tests/test_gates.py` (attack gate, proofs, replan, protected tests and their hardening),
`packages/harness/tests/test_work.py` (trial checkout, judge patch, closed trials), `harness validate`
(`rounds.loop_problems` over every table). The first run after this decision is wave 1's fix through the `fix` table:
its revise reasons per round, its rounds and its cost per stage are compared with w1 (14 reasons, about $250).

## Pros and Cons of the Options

### A human restarts every revise
* Good, because nothing new is built.
* Bad, because every revise costs a new run and a human's turn; the reasons of w1 and w2 stayed open for days.

### A critic in parallel with the verifier, with a loop
* Good, because the order of the stages stays.
* Bad, because the defects of the plan (wrong approach, missing requirements) are found after the work, when they cost
  a whole writer run each.

## More Information
specs/002-run-loop/spec.md; the run-loop plan (development records, outside the repository since 2026-10-29; the plan and the critic's 30 findings);
docs/quality/HAZARDS.md; ADR-0011 (part 1, amended here); ADR-0017 (the write gate's sandbox); ADR-0021 (one writer
at a time). Security reviews of the branch found eight ways around the new checks (links, quoted and case-changed
names, a trial changing `.claude/`, a conftest or an ini file of the branch, a writer's changed copy of its inputs);
each is closed by a test in the files above. Revisit the effort per stage after three runs measured with the new tables.

* Amended on 2026-10-29 by [ADR-0030](0030-the-template-is-english-only.md): the attack stage's summary is output/summary.md, in English.
