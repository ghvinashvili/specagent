---
status: accepted
date: 2026-10-29
decision-makers: the owner, in the spec of the template-core run (section 5) and the order on evals of 2026-10-29
consulted: the template-core run's planner, critic and plan fixer
informed: every project created from this template
---

# Pipeline evals

## Context and Problem Statement

The regression suite had three cases, each a model session, and none checked the errors that the pipeline's own roles
repeat from run to run: a cited line that does not exist, a command without an `Expected:` line, a test that cannot
fail, two builders on one file, a dependency without its lock, a changed control file, a hand-over note of pointers, a
page without its summary, a generated file committed. Reviewers found them late or not at all. One stale case,
`access-probe-critic`, whose stage left the default stage table, ended the whole suite with a ValueError, and no figure
compared one run with another. How does every run measure the pipeline, by code wherever code can judge, and compare
itself with a real earlier run?

## Decision Drivers

* Deterministic over probabilistic: code grades whatever code can judge.
* A case runs without a model, an API key or a session wherever it can, so a role and CI run it in seconds.
* Strict rules: each case holds a finding and a near miss, and a changed case fails.
* A role never reads transcripts; the figures only transcripts hold are the main session's.
* A stale case fails alone; the rest of the suite still runs.

## Considered Options

* Model runs under a model rubric, three trials each
* Ten code cases and three model runs
* Review only

## Decision Outcome

Chosen option: "Ten code cases and three model runs", because code judges eight of the nine error classes and two
rules of the spec exactly and at no cost, and only a session's own judgement needs a session.

* Ten cases under `evals/regression/pipeline-*/` say `session: false` in their `task.yaml`: error classes 1-6, 8 and 9,
  numbered as the pipeline skill's `example/lessons.md` lists them, and two rules of the spec (a commit shows code,
  tests and pages; the write gate refuses code without pages). The
  runner copies the case's `fixture/` to the trial's `workspace/` and its `run/` (or an empty folder) to `run/` and
  grades them by code only, one trial whatever `trials` says; `--baseline` grades them the same way in a temporary
  folder and writes nothing. The graders are `evals/graders/pipeline_plan.py` (nine checks; a case's `expect.json`
  names the check, its inputs and the exact findings) and `evals/graders/pipeline_note.py` (a hand-over note against
  its facts), standard library only but the pages check, which is the write gate's own (ADR-0027).
* Three cases are model runs with `trials: 1`, graded by rules in code (file, schema, regex and the note grader), never
  by a rubric: the critic reports the defect it can prove and refuses the claim it cannot; the verifier finds the one
  defect planted in a page and reports no other (exactly one `DEFECT` line); a hand-over note carries the session's
  facts, not pointers (error class 7). A `FINDING` or `DEFECT` line without `— proof:` fails.
* `uv run harness eval --suite regression --no-sessions --threshold 1.0` grades the ten code cases and names the
  session cases it left out; the 1.0 gate holds for the code cases only. A session case whose stage is gone is one
  failed task with the error's text as its detail, and the suite goes on.
* `uv run harness pipeline-report <run-dir>` reads a run's record files (`critique.md`, `verify.md`, `build-log*.md`)
  through the pipeline skill's report scripts: findings per task by role (C, A and R ids are the critic's, V ids the
  verifier's) and severity, rounds per finding and done tasks, with ratios against a baseline, by default
  `evals/baseline/pipeline/earlier-run.json`, filled from an earlier run of the owner's pipeline. It writes
  `evals/results/<stamp>/pipeline-report.json`, `.md` and `.<language>.md`, never committed. Only with `--prefix NAME` does it
  add each role's sessions, hand-overs, calls, context per call, start-up, wall time and cost from the transcripts
  (`claude agents` and `~/.claude/projects`); without it, or when no transcript is readable, the usage part says
  `"available": false` and why, never zeros. No role passes `--prefix`.

### Consequences

* Good, because every run is measured by the same strict cases in seconds, with no model and no key, and compared
  with a real run.
* Good, because a stale case no longer hides the results of the others.
* Bad, because three judgements still need a session, which a role may not start: CI's full suite,
  `uv run harness eval --suite regression --threshold 0.9`, is the main session's.
* Bad, because usage is counted per role, not per task: no record file links a session to a task, and the baseline
  holds the earlier run's record-file summary until the main session runs the report on it with `--prefix`.

### Confirmation

`packages/harness/tests/test_pipeline_graders.py` (each check on its finding and its near miss, and a changed copy of
every case), `packages/harness/tests/test_eval_session_free.py` and `packages/harness/tests/test_pipeline_report.py`;
`uv run harness eval --suite regression --no-sessions --threshold 1.0` and `--baseline` on the repository.

## Pros and Cons of the Options

### Model runs under a model rubric, three trials each

* Good, because one form fits every case, and three trials show how much a session varies.
* Bad, because a rubric is probabilistic where code is exact, and every run costs sessions, a key and minutes.

### Ten code cases and three model runs

* Good, because code judges ten cases exactly, without a model, and a role or CI runs them.
* Bad, because the rules of the three model runs see a text's form, not all of its meaning.

### Review only

* Good, because it costs no code.
* Bad, because a reviewer finds an error class late or not at all, and no figure compares one run with another.

## More Information

* How a case runs and what a case directory holds: [evals/README.md](../../evals/README.md).
* The grader rules follow ECC at 25278e7 (its skills `eval-harness`, `agent-eval` and `agent-self-evaluation`, and its
  agent `agent-evaluator`): deterministic over probabilistic, show the gap and not only its name, no penalty for what
  was not asked, completeness and conciseness. Not taken: scores from 1 to 5, the model rubric, ECC's report format,
  commands and layout, three trials per case, and cost and time beside the pass rate.
* Porting `access-probe-critic` to the `attack` stage is left for later: `attack` receives the plan, so two of its
  graders would invert.
* Source: the owner's spec of the template-core run (section 5) and the owner's order on evals of 2026-10-29.
* Revisit when a model case could be judged by code, or when a run's record files link sessions to tasks.
* Amended on 2026-10-29 by [ADR-0030](0030-the-template-is-english-only.md): the case pipeline-summaries-and-sizes checks `<name>.summary.md`.
