# The regression cases

Every case here must pass. `uv run harness eval --suite regression --baseline --threshold 1.0` grades all of them
without a session on every push (`.github/workflows/ci.yml`); `bash evals/nightly.sh` runs the model runs on the
owner's machine. How a case runs and what its directory holds: [evals/README.md](../README.md).

## Graded by code (`session: false`)
Eight of the ten known error classes in the pipeline skill's `example/lessons.md`, numbered in its order (the seventh
is a model run below; the tenth, a settings file that leaves the credentials file readable, is the pre-flight's `blind`
check), two rules for a commit (its tests and its pages, ADR-0027) and four lesson classes of 2026-10-29. Each fixture
holds the planted form and a near miss.
- `pipeline-cited-lines` (error class 1): a line cited in a plan that does not exist at the base is found, and one that exists is not.
- `pipeline-expected-lines` (2): a command block of a plan without an `Expected:` line is found; a text block is no command.
- `pipeline-tests-can-fail` (3): a test that asserts nothing, asserts a constant or needs a fixture nobody defines is found.
- `pipeline-disjoint-files` (4): two tasks of different builders that list the same file are found; one builder may list it twice.
- `pipeline-lock-with-deps` (5): a commit that adds a dependency without changing uv.lock is found.
- `pipeline-control-files` (6): a changed control file, a task file whose heading names another task and one written ahead are found.
- `pipeline-summaries-and-sizes` (8): a page without its .summary.md summary, a page over the size limit and an index over it are found.
- `pipeline-generated-files` (9): a generated artifact in the tracked files is found; the three Obsidian settings files are not.
- `pipeline-commit-has-pages`: a commit with code shows its tests and its pages; one without tests is found.
- `pipeline-write-gate-refuses`: the write gate refuses a code commit without pages unless every task says docs: none with a reason.
- `pipeline-job-timeouts` (the wrapper timeout): a `timeout` before `harness eval` that is shorter than the minutes its
  selection can run (trials x sessions x `timeout_minutes` of each session case, `harness.evals.suite_minutes`) is
  found; one as long, a `--baseline` or `--no-sessions` run and a line without `--suite` are not.
- `pipeline-ancestor-deny` (a sandbox deny on an ancestor): an `Edit`, `Write` or `denyWrite` deny that covers a path
  the settings let the session write, or an ancestor of it, is found; a deny below a written path is not.
- `pipeline-handoff-pointers` (a hand-over note with pointers instead of facts): a note that names files instead of
  carrying their facts, a bad line 1 and a 41st line are found; a note that carries the facts is not.
- `pipeline-waiters` (a waiter not run as the brief gives it): a `sleep` at a command position in a Bash call of a
  transcript and a waiter command that differs from the brief's are found; the brief's own commands are not, one in a
  code span over a line end among them (a span inside a fenced block is the block's text, not a command).

## Model runs
Each with its reference outcome, a recorded output, in `evals/baseline/<case>/`:
- `pipeline-handoff-carries-facts` (error class 7; planner): a hand-over note carries the session's facts, not pointers to files.
- `pipeline-critic-unproven-finding` (critic): the critic reports the defect it can prove and refuses the claim it cannot.
- `pipeline-verifier-planted-defect` (verifier): the verifier finds the one defect planted in the writer's page and reports no other.
- `cache-share-reader` (reader, two sessions): the second session of the same stage finds the system prompt, knowledge pack included, in the prompt cache on its first request (`cache_share.py`).
- `reader-quotes-locations` (reader, three trials): the notes cite `context/sample.txt:<n>` at least three times, hold no opinion words and are faithful by the rubric `rubrics/notes-faithful.md`.
The three `pipeline-*` model runs have `trials: 1` and are graded by rules in code (file, schema, regex and the note
grader), never by a rubric; in the critic's and the verifier's case a `FINDING` or `DEFECT` line without `— proof:`
fails.

## The other two classes of 2026-10-29
- The grader regex: a grader is written from a recorded output, never from the brief's wording. The critic's
  baseline holds the session's own spelling, `line 9 of context/sample.txt`; a pattern for `sample\.txt:9` alone
  misses it and the gate fails at 0.0.
- A stale case: a case whose stage, stage table or file is gone stops the suite before any trial (`stale_cases`).
  The access probe's case was one (its stage `critique` left the default table) and is removed; its port to the
  `attack` stage waits in `docs/exec-plans/tech-debt-tracker.md`.
