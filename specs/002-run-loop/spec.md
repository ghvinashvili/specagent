# A loop inside the run and a new arrangement of checking: design

Date: 2026-10-08. Status: on 2026-10-08 the user approved the scheme. Implementation plan:
the run-loop plan (development records, outside the repository since 2026-10-29). Base branch: `stage1` (`main`, wave 1 and wave 2; the reasons of both waves' judge for
`revise` are open and are passed on to the next runs).

## 1. What we want

A run should let fewer errors through and need fewer loops. A loop that is still needed should happen inside the run on
its own, with a cap and with a warning to the human.

**How we know it worked**

1. Every stage works with the model and effort that are in the table. The session that creates the run no longer changes them.
   `harness run --effort <stage>=<level>` changes one stage in one run, as today.
2. The critic (the `attack` stage) checks the plan before write on the checkout of the planner's trial, writes attack tests and
   gives the human a translated one-page summary. The human approves the plan by this summary.
3. A `revise` of `attack` goes back to planner, and a `revise` of verify or judge goes back to write. After a return, every
   stage that has already worked and depends on the returned stage checks again.
4. The loop stops and tells the human: after the third return (on the `plan` and `work` counters separately),
   after the fifth run of write, or when a round repeats the findings of the previous round.
5. The gate runs the tests of the planner's trial and the critic's attack tests as they were written. A copy changed by write
   changes nothing, and the gate names the change with a separate check.
6. Work goes back only with a proven finding: a `refuted` entry of verify and a `blocks` or
   `must fix` row of the critic come with a command and an exit code.
7. judge reads the plan, both reports and `changes.patch`. `replan` is added to the decisions.

## 2. What we know

- The judges of w1 and w2 named 27 reasons for `revise`, although every stage worked at max: documentation promises
  9, edge cases, concurrency and wrong input 10, a wrong approach 5 (the guards analyse the shell's
  text), mechanical 3. In 7 of the 13 reasons of w2, different places in the code do one and the same thing in different
  ways.
- The cost at API prices: w1 ≈ $250, w2 ≈ $209. ~81% went to loading the context and reading it again, ~19% to thinking
  and answering. Of the stages, write (~46%) and plan (24–32%) cost the most.
- The judge of w1 spent 126 066 tokens in one answer, out of a limit of 128 thousand.
- In w2 the critic found 4 defects that verify missed. All four concerned a promise of the plan or the documentation.
- By the measurement of ADR-0008 on the reader stage, max found every fact and high missed one, and the cost was four times as much.

## 3. The scheme

`read` (in the default table) → `plan` ⇄ `attack` (the human approves) → `write` ⇄ `verify` → `judge` (the human
approves). The `fix` table has no `read`. Every stage works at Opus max, except `classifier` and
`quarantine-reader`. write is one session: there are no more shards in the default and `fix` tables.

| Stage | What it does | Whom it returns to |
| --- | --- | --- |
| `plan` | The plan, the tasks, the trial (`trial.patch`) and its tests, which are the acceptance tests | — |
| `attack` | Checks whether the requirements can be carried out and what is missing. Checks one owner per concern and the guard at the boundary. Attacks the trial with the hazard list. Writes `output/tests/` and `output/summary.<language>.md` | `plan` (`plan` counter) |
| `write` | Does the work. Keeps the protected tests unchanged. Writes in the documentation only what a test has confirmed | — |
| `verify` | Runs everything again in a clean checkout. Checks the claims of the documentation and the hazard list | `write` (`work` counter) |
| `judge` | Compares the diff with the plan and the reports. Blocks only with what is proven | `write` (`work` counter); `replan` and `reject` stop the run |

## 4. Requirements

- R1. `state.choose_stage` takes the table exactly. The session's model and effort are written into `manifest.json` for information.
- R2. The table gets a `loop` block (`counters`, `max_runs`) and the stage field `returns_to`. `harness validate`
  names a `returns_to` that is not a predecessor of the stage, a counter without a cap and a `per_task` target.
- R3. `poll`, under the lock of state.json, takes every `revise` once. The reviewer's output moves to
  `rounds/<n>/`. The target gets the status `rework` and the file `rework.md`. The stages after it that have already run get
  the status `recheck`. poll prints the actions `rework`, `recheck`, `loop_cap`, `no_progress`, `rejected` and `replan`.
- R4. `harness resume --rework` continues a unit with the status `rework` or `recheck`. On `recheck`, `input/` and
  `pack.md` are assembled again. A plain `resume` does not touch such a unit. Attempts are counted per round
  (`round_start`), and the runs of write are capped by `max_runs`.
- R5. `attack` gets a checkout where `trial.patch` lies on top of base. judge gets only `changes.patch`, without a
  checkout. The checkout of the planner's trial disappears when a stage that changes the repository starts.
- R6. A new gate for `attack`: the verdict is `accept` or `revise`; `revise` ⇔ at least one `blocks`/`must fix` row;
  every such row comes with evidence; there are attack tests or `No attack test:` is written; every task of the plan
  is named; there is a translated summary (≤ 6000 characters).
- R7. The gate of verify: `revise` ⇔ at least one `refuted` entry; every `refuted` entry comes with evidence.
  The gate of judge: `replan` is allowed; the source of a reason may be a `` `path:line` `` from the patch.
- R8. The gate of write runs the test suite with the tests of the planner and the critic laid on top. A separate check
  names every protected test that differs on the branch.
- R9. The default and `fix` tables have the new arrangement. In the other tables every stage moves to Opus max (except
  FIXED_TYPES), and `max_minutes` triples where effort went up.
- R10. need-to-know: the critic gets the output of planner and reader, writer and verifier get the critic's, and judge
  gets planner's and writer's.
- R11. The types' instructions (planner, critic, writer, verifier, judge) and the hazard list
  `docs/quality/HAZARDS.md` reflect the new rules. Every new step has its own `check:` rule.
- R12. The manager's `loop.md`, MANAGER.md, HUMAN.md, RUNS.md, `resume-stage` and `run-stage` reflect the new actions.
  HANDOFF.md lists the rounds. ADR-0024 replaces the first part of specification 001 (the inheritance of effort).

## 5. What is not included

- The mutation check and the „the test fails on base“ check: in the next wave.
- A loop of a stage with shards: `harness validate` does not let such a table through.
- A general script for the one-function rule: every plan checks this rule with its own acceptance command.
- A cost report by stage (`harness cost`) and stopping by a limit.
- Shrinking the planner's trial.

## 6. Risks

- judge may exceed the 128K limit in one answer. In that case the print run fails and poll brings it back with
  `resume`. `max_budget_usd` grows to 15 and the instruction asks for short reasons.
- If a round repeats the same findings in other words, `no_progress` does not recognise it. In that case the cap stops
  the loop.
- On `recheck`, assembling `pack.md` again loses the cache once.
- One write session fills the context in a big run. So a run should touch one mechanism (MANAGER.md, part 1).

## 7. Measurement

The first run after the wave will be the fix of wave 1 with the new scheme. We count the reasons for `revise` per
round, the number of rounds and the cost per stage. We compare with w1: 14 reasons and ≈ $250.
