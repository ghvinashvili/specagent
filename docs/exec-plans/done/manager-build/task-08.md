# Task 8 — Evals and CI: one case per lesson class of 2026-10-29, graders from recorded outputs, the llm grader fixed, the stale-case lint, GitHub Actions, the nightly script

planner: b
builder: c
depends_on: — (lane C's base is `main` at f70e84c, `lessons.md` 21:08 UTC; Task 6, which builder C builds first, touches
  none of this task's files: `00-index.md` rows 6 and 9 at 6c3a1cc and `task-06.md` name no `evals/`, `evals.py` or
  `.github/` path)
files: `packages/harness/src/harness/evals.py`, `packages/harness/tests/test_evals_suite.py` (new),
  `packages/harness/tests/test_evals_llm.py` (new), `packages/harness/tests/test_eval_session_free.py` (its pins of the
  ten code cases, the stale case and the baselines), `packages/harness/tests/test_pipeline_graders.py` (its pin of the
  ten cases graded by code), `evals/graders/pipeline_plan.py` (four checks),
  `evals/regression/pipeline-job-timeouts/`, `evals/regression/pipeline-ancestor-deny/`,
  `evals/regression/pipeline-handoff-pointers/`, `evals/regression/pipeline-waiters/` (new code cases: `task.yaml` and
  `fixture/`), `evals/baseline/pipeline-critic-unproven-finding/run/stages/attack/output/critique.md` (line 1, the recorded
  spelling), `evals/regression/access-probe-critic/` and `evals/baseline/access-probe-critic/` (removed),
  `evals/README.md`, `evals/regression/README.md` (new: the case list moves here), `evals/nightly.sh` (new),
  `.github/workflows/ci.yml`, `.github/workflows/evals.yml`
acceptance: the run's measure for the five lesson classes of 2026-10-29 (each has a guard that fails on its planted form and
  runs on every push); 10.19 (the waiter case: no `sleep` in a command, every waiter run as its brief gives it)

## Goal
The eval suite catches the five lesson classes of 2026-10-29 before a live run does, and CI runs it on every push without a
model: a code case each for the wrapper timeout, the hand-over note that points instead of carrying facts, and the sandbox
deny on an ancestor; the critic case's baseline in the spelling the critic wrote, graded on every push (the grader regex); a
lint that fails every suite run that names a gone stage or file (the stale case); and the waiter case of 10.19. The llm grader
stops loading the user's settings and refuses a grade that is not in English (TD-011). GitHub Actions runs the tests and the
gate `uv run harness eval --suite regression --baseline --threshold 1.0` on every push; the session cases run on this machine
by `bash evals/nightly.sh` under a cost cap.

## Spec carried
- 8.3.10 (spec.md:1031): "The live eval suite: `access-probe-critic` stale, the 0.9 threshold reached only at 17 of 18": the
  lint (Step 6), the stale case removed (Step 4, Departure 2), the gate and the nightly run at threshold 1.0 (Departure 5).
- 10.19 (spec.md:1133-1134): "No hand polling: the manager's commands contain no `sleep` loop; the watcher's and the
  monitor's logs show re-arming after expiry; every waiter ran with the full command its brief gives." The first and the last
  clause get the `waiters` check and its case (Steps 7-8), which the verifier can also run on a real transcript; the re-arming
  lines are the logs of Tasks 2 and 3, both built, so they are not a Deferred item (C508).
- The owner's final plan (the planner brief, input 2), evals and CI: one case per lesson class of 2026-10-29; graders written
  from recorded outputs, the rule in `evals/README.md`; the llm grader with fixed setting sources and an English check; a lint
  that fails the suite when a case names a stage that no longer exists; the code-only suite and the tests on every push in
  GitHub Actions; the session cases by a nightly script on this machine with a cost cap.
- TD-011 (`docs/exec-plans/tech-debt-tracker.md:15`): closed by Steps 2 and 6. TD-002 (`:6`): Deferred (Departure 6).
- `lessons.md` Known error classes, the six this task guards: a long job under a timeout shorter than its cases' sum; a grader
  regex that wants one spelling; a hand-over note that points at files; a sandbox deny on an ancestor of a written path; a
  stale regression case; an llm grader run with the user's setting sources.

## Departures (from the spec and the index, with the reason)
1. Five classes, four new case directories. The wrapper timeout, the hand-over note and the ancestor deny get a code case each
   (`session: false`, graded by a new check of `evals/graders/pipeline_plan.py`, as the ten code cases are). The grader-regex
   class is guarded where it lives: the critic case's baseline takes the spelling the critic wrote in the recorded run
   (`experiments/template-core/lessons.md:184`, 2026-10-29 14:50 UTC: "step 3 cites line 9 of context/sample.txt, a line the
   file does not have"), and the gate grades every session case's code graders on its baseline on every push, so a grader
   narrowed back to `sample\.txt:9` fails at push time. The stale class is guarded by the lint, which runs before every suite
   run, the gate's included; a planted stale case under `evals/regression/` would fail the real gate, so its planted forms
   live in `test_evals_suite.py`. The fourth new directory is the waiter case of 10.19.
2. `access-probe-critic` is removed, not ported. Its stage `critique` is gone; the `attack` stage, which took the `critic` type
   (`docs/roles/stages.yaml:39-40`), reviews the plan (`:46`: `brief`, `spec`, `plan:output/`, `plan:tasks.json`,
   `read:output/notes.md`), so the probe's canary `CANARY-PLAN-2256` ("the plan is not an input of the critique stage",
   `task.yaml`) would become an input, and its recorded baseline (the transcript of a critique session) cannot be renamed into
   an attack session. A port needs a new fixture and a baseline recorded by a live run, which no planner or builder starts
   (Deferred 1; Task 11 adds it to the tracker).
3. The gate is `--baseline`, not README's `--no-sessions`: `--baseline` grades the code cases the same way and adds every
   session case's code graders on its recorded baseline, with no session and no key (`llm = not baseline and ...`,
   `evals.py:528`). Measured at f70e84c on an exported tree: exit 1, `pass_rate` 0.9375, 15 of 16 cases pass; the one failure
   is `access-probe-critic`, whose detail is the text `stage_row` raises (`evals.py:77-79`, its `NO_STAGE` in
   `test_eval_session_free.py`).
4. The session job leaves GitHub Actions: `evals.yml`'s `harness-regression` job (the full suite with `ANTHROPIC_API_KEY` on
   pull requests that touch `.claude/`, `plugins/`, `templates/`, `schemas/`, `docs/roles/` or `evals/`) goes, because the
   owner's plan runs the session cases on this machine (`evals/nightly.sh`); `instruction-version` and `plugin-evals` stay.
5. The nightly run's threshold is 1.0, and its cost cap counts worst cases. A threshold under 1.0 let a case that always fails
   pass the suite (8.3.10: 17 of 18 >= 0.9). A started session case counts `trials x sessions x max_budget_usd`, because each
   session stops at its own `--max-budget-usd` (`evals.py:187-188`) and a trial of several sessions keeps only its last
   session's cost (`evals.py:264`): the counted sum bounds the spend, and the selection is known before the first trial.
6. TD-002 (a regression case for `judge`) is Deferred. No code-graded form exists (a verdict is a model's judgment; the index's
   files cell says "if a code-graded form exists"), and a session case needs a recorded judge output as its baseline, by this
   task's own rule; the nightly run is where one gets recorded (Deferred 2). Coverage maps TD-002 to Task 8 and Task 11 closes
   it: the Contracts carry the change to the plan fixer.
7. TD-011's "one regression case that asserts English dimensions" (`tech-debt-tracker.md:15`) is tests with a fake `claude`
   in `test_evals_llm.py`: a session case for the grader needs a live model, which the gate never starts.
8. 10.20's "the sum of its cases' `timeout_minutes`" is counted as Task 4 counts it (task-04.md, Departure 2):
   `trials x sessions x timeout_minutes` per session case, 0 for a code case. At f70e84c the regression suite gives 130
   minutes (access-probe-critic 15, cache-share-reader 2 x 15, pipeline-critic-unproven-finding 15,
   pipeline-handoff-carries-facts 10, pipeline-verifier-planted-defect 15, reader-quotes-locations 3 x 15) and $21 of
   budgets; after Step 4, 115 minutes and $18.

## Contracts
- For Task 11 (`manager/plan-fixer`, odd; sent as
  `planner-b: contract for Task 11 — TD-011 closed by Task 8, TD-002 and the access probe's port deferred`): Task 11 closes TD-011 with this task's commit, keeps TD-002 open with Departure 6's reason,
  and adds Deferred 1 and 3 as tracker rows, each holding the item's key verbatim (C508: the keys are in
  `## For Task 11`; Deferred 2 names TD-002, a row already); the decision page and the lines of `## For Task 11` are
  its to write (lane C
  writes no `wiki/` page, `lessons.md` 20:36 UTC). The index's Coverage row `TD-002, TD-011 | 8` and its Deferred list are the
  plan fixer's to change.
- For Task 4 (lane A, read by Task 11's milestone): `suite_minutes` counts as Task 4's pre-flight counts; Task 4's measured
  `total: 175 min over 7 session cases` (both suites at ff3354a) becomes 160 over 6 once this task's removal is merged.
- `evals/graders/pipeline_note.py:19` `problems(note: str, facts: dict) -> list[str]` keeps its name and signature: the
  `handoff-notes` check imports it.
- `harness.evals.suite_minutes(root, suite, case=None)` is imported by `pipeline_plan.py`'s `job-timeouts` and by
  `evals/nightly.sh`; `HARNESS_EVAL_MAX_USD` is read by `run_suite` and set by `evals/nightly.sh`.
- `.github/workflows/ci.yml` keeps the ruff line at 16 and the pytest line at 17: `packages/harness/src/harness/gates/_common.py:27`
  cites `.github/workflows/ci.yml:16-17`.

## Interfaces
`packages/harness/src/harness/evals.py` (new names; the module's other functions keep their signatures):
```python
GEORGIAN: re.Pattern[str]
# One character class over U+10A0-U+10FF, U+1C90-U+1CBF and U+2D00-U+2D2F (8.3.11's three blocks), built with chr() from
# the code points, so the file holds no letter of a refused block (D1).


def not_in_english(texts: list[str]) -> str | None:
    """The first text that holds a letter of a refused block, cut at 120 characters; None when no text holds one."""


def stale_cases(root: Path, suite: str, case: str | None = None) -> list[str]:
    """One line per case of load_cases(root, suite, case) that names a stage or a file that is gone, sorted. A session
    case: the text of the ValueError that stage_row raises, or `<name>: pipeline <p> has no stage table` when
    state.table_path(root, <p>) is not a file. Every case: `<name>: <key> <value> does not exist` for `fixture` and
    `brief` (against the case directory) and for each grader's `rubric`, `script` and `schema` (against root).
    A case with `session: false` is never staged."""


def case_minutes(task: dict) -> int:
    """trials x sessions x timeout_minutes of a session case (trials and sessions default to 1); 0 for `session: false`."""


def suite_minutes(root: Path, suite: str, case: str | None = None) -> int:
    """The sum of case_minutes over load_cases(root, suite, case): the shortest timeout a job may give that selection."""


def case_budget(task: dict) -> float:
    """trials x sessions x max_budget_usd of a session case (max_budget_usd defaults to 0); 0.0 for `session: false`."""


def within_cap(cases: list[tuple[Path, dict]], cap: float) -> tuple[list[tuple[Path, dict]], list[str], float]:
    """In case order, the cases that fit the cap, the problem line of each session case that does not, and the sum
    spent. A session case fits when spent + case_budget(task) <= cap, and then spent grows by its budget; a case that
    does not fit is left out with `cost cap: <name> not started, $<budget> more would pass $<cap> (spent $<spent>)`
    (each figure with two decimals), and later cases may still fit. Code cases always fit and count 0."""
```
- `run_suite`: after `load_cases` and its `no case` problem, `stale_cases(root, suite, case)`; any line returns
  `{"ok": False, "problems": <the lines>}` before a trial starts, in every mode (sessions, `sessions=False`, `baseline`).
  With `HARNESS_EVAL_MAX_USD` set (dollars, a float) and neither `baseline` nor `sessions=False`, `within_cap` selects the
  cases; the aggregate gains `"max_usd"` and `"spent_usd"`, and `"problems"` with `ok` False when it left a case out.
  Without the variable, or in the other two modes, nothing changes. When `within_cap` leaves no case, `run_suite`
  returns `{"ok": False, "problems": <the cap lines>}` before a trial, as it does for `no case`.
- `suite_case`: its `except ValueError` branch (a stage that is gone made one failed task) goes, with that clause of its
  docstring: the lint stops such a case before `suite_case` is called.
- `_llm_grade`: the argv gains `"--setting-sources", "local"` before the prompt, which stays the last argument (the measured
  flag that keeps `~/.claude/CLAUDE.md` out of a session, `.claude/skills/running-specagent-pipelines/references/launch.md:7`);
  a parsed grade whose `not_in_english(dimensions)` is a text returns
  `{"type": "llm", "rubric": <rubric>, "score": None, "detail": "not in English: " + <that text>}`.
- Each function of `evals.py` that this task writes or changes stays at most 50 lines (`.claude/rules/python.md:9`;
  by `ast`, `run_suite` is 39 at f70e84c and `_llm_grade` 41; `grade` (61) and `run_session` (104) stay untouched).

`evals/graders/pipeline_plan.py`: four entries in `CHECKS`, each `(inputs: list[Path], opts: dict) -> list[str]` like the nine,
and the module docstring's "nine checks" becomes "thirteen checks":
- `job-timeouts` (`job_timeouts`): every input line where `timeout` with a duration (a number with an optional unit `s`, `m`,
  `h` or `d`, GNU `timeout`'s syntax: no unit is seconds) precedes `harness eval`. Between `timeout` and the duration may
  stand `-k`/`--kill-after` and `-s`/`--signal` with a value (separate or after `=`), `--preserve-status`, `--foreground`
  and `-v`/`--verbose`; a duration of 0 needs nothing (GNU `timeout` reads 0 as no limit). The selection is `--suite X`
  or `--suite=X` and `--case Y` or `--case=Y` anywhere after `harness eval`; a line without `--suite` is skipped; with
  `--baseline` or `--no-sessions` it needs 0. The need
  is `harness.evals.suite_minutes(opts["base"], suite, case)`, imported in the function under the harness's Python (graders
  run with `sys.executable`, `evals.py:399`; measure mode needs `uv run python`). A duration under the need gives
  `<input>:<line>: timeout <duration as written> is under <need> min, the longest evals/<suite>[ --case <case>] can run`.
- `ancestor-deny` (`ancestor_deny`): every input is a settings JSON file. The written paths are
  `sandbox.filesystem.allowWrite`; the denies are each `permissions.deny` entry `Edit(<p>)` or `Write(<p>)`, with one leading
  `/` dropped when `<p>` starts with `//` or `/<` (Claude Code's absolute form; the skill's `/<placeholder>` form), and each
  `sandbox.filesystem.denyWrite` entry as written. A deny, its trailing `/**` dropped, covers a written path when
  `fnmatch.fnmatchcase` matches it to that path or to one of its ancestors (the path cut at each `/`), and gives
  `<input>: <the entry as written, or denyWrite <entry>> covers the written path <path>`. A deny below a written path
  (`Edit(/<run-dir>/_*)` under `<run-dir>`, `example/builder-a-settings.json`) covers nothing.
- `handoff-notes` (`handoff_notes`): every input is a hand-over note `<x>.md` whose facts are `<x>.facts.json` beside it, the
  file `pipeline_note.py` reads; each line of `pipeline_note.problems(<note text>, <facts>)` gives `<input>: <line>`.
  The function imports it with `from pipeline_note import problems` inside its body (Python puts the script's folder on
  `sys.path`).
- `waiters` (`waiters`): the inputs are briefs (`.md`) and transcripts (`.jsonl`). A brief's waiter commands are its code
  spans (`SPAN`) that name a script whose file name holds `wait` (`[\w./-]*wait[\w-]*\.(py|sh)`), whitespace collapsed.
  Each becomes a pattern: `re.escape` of the collapsed span first, then each placeholder `<[^<>]*>` in it replaced by
  `\S+`, one word (briefs give `<run-dir>`, `<log>` and `<lines>` for the agent to fill); the replacement is written
  `r"\\S+"`, as `re.sub` rejects a bare `\S` in a replacement (Python 3.7 on). A
  transcript's commands are the `input.command` of each `message.content` item with `type` `tool_use` and `name` `Bash`, on
  the line's number. A command with `sleep` at a command position (line start, after `;`, `&`, `|`, `(`, `do`, `then` or
  `else`) followed by a number gives `<input>:<line>: sleep: <command>`; a command that names a waiter script and in whose
  collapsed text no brief's pattern matches (`re.search`) gives
  `<input>:<line>: waiter not as the brief gives it: <command>`; `<command>` is the command with whitespace collapsed.
  Other tools (a `Monitor` with an `until ... sleep` loop) are not read. Only `.jsonl` inputs are checked (the `.md`
  inputs give the forms); a `message.content` that is not a list and an item that is not a dict are skipped; a line
  start is the start of any line of the command (`re.MULTILINE`).

`evals/nightly.sh` (bash, no shebang needed: run as `bash evals/nightly.sh`, by hand or from the owner's cron): from the
repository root, `cap="${HARNESS_EVAL_MAX_USD:-20}"` (the regression suite's worst case is $18 after Step 4), the need from
`uv run python -c` with `harness.evals.suite_minutes`, a stderr line `nightly: cap $<cap>, timeout <need + 10> min`, then
`HARNESS_EVAL_MAX_USD="$cap" timeout -k 10 "<need + 10>m" uv run harness eval --suite regression --threshold 1.0`, its exit
code the script's.

## Steps
The steps' text in full follows this list (part 2 on); each step ends with its command and an `Expected:` line measured on
f70e84c's tree for these paths (`git diff --stat f70e84c HEAD -- evals packages .github justfile pyproject.toml uv.lock` is
empty at 67f096c).
- [ ] Step 1 — `packages/harness/tests/test_evals_suite.py` in full (red): the lint, the minutes, the cap, the gate's
  workflow lines, the nightly script with a fake `uv`, and no stale case in this repository
- [ ] Step 2 — `packages/harness/tests/test_evals_llm.py` in full (red): the setting sources, the three blocks, a Latin-only
  letter kept, the 120-character cut
- [ ] Step 3 — The pins of `test_eval_session_free.py` (`no_sessions()`, the stale case failing the suite, fourteen code
  cases, every baseline passing) and of `test_pipeline_graders.py` (fourteen cases graded by code), red where they change
- [ ] Step 4 — `access-probe-critic` and its baseline removed; line 1 of the critic baseline in the recorded spelling
- [ ] Step 5 — `evals/nightly.sh`
- [ ] Step 6 — `evals.py` against Steps 1-3 (green); the 50-line rule measured with `ast`
- [ ] Step 7 — The four code cases in full (red: their checks are unknown)
- [ ] Step 8 — The four checks in `pipeline_plan.py` (green), each wrong version run red once
- [ ] Step 9 — `ci.yml` (every push, the gate after pytest) and `evals.yml` (no session job)
- [ ] Step 10 — `evals/README.md` (the gate, the grader rule, the lint, the nightly run) and `evals/regression/README.md`
  (the case list, under 12,000 bytes each)
- [ ] Step 11 — The gate on the tree, the task's own test files and the ruff pair
- [ ] Step 12 — The commit and the log line

`W` is builder C's worktree, `/home/tite/Desktop/agentic-flow-template/manager-build-c` on `feat/manager-build-c`
(`_builder-c-assignment.md:1`), after Task 6, which touches none of this task's paths. Every `Expected:` below was
measured on a tree extracted from f70e84c (`git archive f70e84c | tar -x`, with its own `uv sync`) and the planner's
reference `evals.py` and `pipeline_plan.py`. Those two are not in this plan: the builder writes them against the tests
and the cases. The blocks below are the measured files byte for byte. Each command runs in a subshell, never with a
top-level `cd`, with `ulimit -v 8388608` and `timeout -k 10` (`lessons.md` Read first 4). `B` is builder C's scratch
folder, `/home/tite/Desktop/agent-system-run/manager-build-2026-10-29/scratch/builder-c`.

### Step 0 — The files this task patches or rewrites are f70e84c's
- [ ] 0a. Check them before the first step (`lessons.md` 23:03 UTC):
```bash
git -C "${W:?}" diff --quiet f70e84c HEAD -- evals .github packages/harness/src/harness/evals.py packages/harness/tests/test_eval_session_free.py packages/harness/tests/test_pipeline_graders.py && echo same
```
Expected: `same`. Anything else: carry the change into the step that writes the file and tell `manager/plan-fixer-b`
(`builder-c: Task 8 — <path> changed since f70e84c at <sha>`).

### Step 1 — `test_evals_suite.py` in full (red)
- [ ] 1a. Write `packages/harness/tests/test_evals_suite.py` exactly as below (251 lines; 15 test functions, 20 tests
  with the parametrized cases). `root` is a repository root in `tmp_path` made with the suite's `copy_config` fixture
  (`conftest.py:46`), its cases written by `write_case`; `started` records the cases `run_suite` hands to `suite_case`
  and answers each as one passed trial; the nightly test puts a fake `uv` and a fake `timeout` on `PATH` that record
  their argv. No session starts. Each expected value is written by hand from the fixture, never taken from the function
  it checks. Do not weaken a test; if one is wrong, send the proof to `manager/plan-fixer-b`.
```python
"""The suite's lint, its minutes and its cost cap, the gate's workflow lines and the nightly script."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml
from harness import evals

ROOT = Path(__file__).resolve().parents[3]
NO_STAGE = "{}: no stage for role type critic in pipeline default; name `pipeline` and `stage`"
CODE = {"session": False, "role_type": None, "stage": None, "brief": None}
CAP_PROBLEM = "cost cap: b not started, $6.00 more would pass $4.00 (spent $3.00)"
GATE = "      - run: uv run harness eval --suite regression --baseline --threshold 1.0"
FAKE_UV = """#!/usr/bin/env bash
echo "$PWD|${HARNESS_EVAL_MAX_USD:-}|$*" >> "$NIGHTLY_LOG"
if [ "$2" = python ]; then echo 115; exit 0; fi
exit 3
"""
FAKE_TIMEOUT = """#!/usr/bin/env bash
echo "$*" >> "$NIGHTLY_LOG"
shift 3
exec "$@"
"""


def refuse(*args, **kwargs):
    raise AssertionError("nothing is graded or staged here")


def write_case(root: Path, name: str, **fields) -> Path:
    """A session case of root's regression suite (critic, stage attack) with its fixture and brief, unless fields
    say otherwise; a field set to None is left out."""
    d = root / "evals" / "regression" / name
    (d / "fixture").mkdir(parents=True)
    (d / "fixture" / "brief.md").write_text("# Brief\n", encoding="utf-8")
    task = {
        "schema_version": 1,
        "name": name,
        "suite": "regression",
        "role_type": "critic",
        "stage": "attack",
        "trials": 1,
        "timeout_minutes": 15,
        "max_budget_usd": 1,
        "fixture": "fixture",
        "brief": "fixture/brief.md",
        "graders": [{"type": "file_exists", "path": "stages/attack/output/critique.md"}],
        "pass_rule": "deterministic_all",
        **fields,
    }
    (d / "task.yaml").write_text(yaml.safe_dump({k: v for k, v in task.items() if v is not None}), encoding="utf-8")
    return d


@pytest.fixture()
def root(tmp_path, copy_config):
    r = tmp_path / "root"
    copy_config(ROOT, r, ("schemas", "docs/roles"))
    return r


@pytest.fixture()
def started(monkeypatch):
    """The names of the cases run_suite hands to suite_case, each answered as one passed trial."""
    names = []

    def fake(root, case_dir, task, results_dir, baseline, llm):
        names.append(task["name"])
        return {"task": task["name"], "trials": [{"trial": 1, "passed": True}], "passed": 1}

    monkeypatch.setattr(evals, "suite_case", fake)
    return names


def cap_cases(root: Path) -> None:
    write_case(root, "a", max_budget_usd=3)
    write_case(root, "b", trials=3, max_budget_usd=2)
    write_case(root, "c", max_budget_usd=1)
    write_case(root, "c1", **CODE)


def test_a_case_whose_stage_is_gone_is_named_and_one_whose_stage_exists_is_not(root):
    write_case(root, "stale", stage="critique")
    write_case(root, "fresh")
    assert evals.stale_cases(root, "regression") == [NO_STAGE.format("stale")]


def test_a_case_whose_pipeline_has_no_stage_table_is_named(root):
    write_case(root, "gone-pipeline", pipeline="retired")
    assert evals.stale_cases(root, "regression") == ["gone-pipeline: pipeline retired has no stage table"]


def test_a_file_a_case_names_that_is_gone_is_named_against_its_own_base(root):
    (root / "evals" / "rubrics").mkdir(parents=True)
    (root / "evals" / "rubrics" / "kept.md").write_text("# Kept\n", encoding="utf-8")
    (root / "evals" / "graders").mkdir(parents=True)
    (root / "evals" / "graders" / "kept.py").write_text("", encoding="utf-8")
    kept = [
        {"type": "llm", "rubric": "evals/rubrics/kept.md"},
        {"type": "python", "script": "evals/graders/kept.py"},
        {"type": "json_schema", "path": "stages/attack/result.json", "schema": "schemas/stages.schema.json"},
    ]
    gone = [
        {"type": "llm", "rubric": "evals/rubrics/gone.md"},
        {"type": "python", "script": "evals/graders/gone.py"},
        {"type": "json_schema", "path": "stages/attack/result.json", "schema": "schemas/gone.schema.json"},
        {"type": "file_exists", "path": "stages/attack/output/gone.md"},
    ]
    write_case(root, "kept-files", graders=kept)
    write_case(root, "gone-files", fixture="fixture-old", brief="fixture/old-brief.md", graders=gone)
    assert evals.stale_cases(root, "regression") == [
        "gone-files: brief fixture/old-brief.md does not exist",
        "gone-files: fixture fixture-old does not exist",
        "gone-files: rubric evals/rubrics/gone.md does not exist",
        "gone-files: schema schemas/gone.schema.json does not exist",
        "gone-files: script evals/graders/gone.py does not exist",
    ]


def test_a_case_without_a_session_is_never_staged(root, monkeypatch):
    monkeypatch.setattr(evals, "stage_row", refuse)
    write_case(root, "free", **{**CODE, "pipeline": "retired"})
    assert evals.stale_cases(root, "regression") == []


def test_the_case_option_selects_the_case_it_names(root):
    write_case(root, "stale-b", stage="critique")
    write_case(root, "stale-a", stage="critique")
    assert evals.stale_cases(root, "regression", "stale-b") == [NO_STAGE.format("stale-b")]
    assert evals.stale_cases(root, "regression") == [NO_STAGE.format("stale-a"), NO_STAGE.format("stale-b")]


def test_this_repository_has_no_stale_case():
    assert (evals.stale_cases(ROOT, "regression"), evals.stale_cases(ROOT, "capability")) == ([], [])


@pytest.mark.parametrize("mode", [{}, {"baseline": True}, {"sessions": False}])
def test_a_stale_case_stops_the_suite_before_a_trial_in_every_mode(root, monkeypatch, mode):
    monkeypatch.setattr(evals, "suite_case", refuse)
    write_case(root, "free", **CODE)
    write_case(root, "stale", stage="critique")
    out = evals.run_suite(root, "regression", threshold=1.0, **mode)
    assert out == {"ok": False, "problems": [NO_STAGE.format("stale")]}
    assert not (root / "evals" / "results").exists()


def test_suite_minutes_count_trials_sessions_and_minutes_of_each_session_case(root):
    write_case(root, "s1", trials=3, timeout_minutes=15)
    write_case(root, "s2", sessions=2, timeout_minutes=15)
    write_case(root, "s3", trials=None, timeout_minutes=10)
    write_case(root, "code", **{**CODE, "timeout_minutes": 99})
    tasks = [task for _, task in evals.load_cases(root, "regression", None)]
    assert [evals.case_minutes(task) for task in tasks] == [0, 45, 30, 10]
    assert (evals.suite_minutes(root, "regression"), evals.suite_minutes(root, "regression", "s2")) == (85, 30)


def test_within_cap_starts_what_fits_in_case_order_and_names_the_rest():
    cases = [
        (Path("c1"), {"name": "c1", "session": False, "max_budget_usd": 9}),
        (Path("a"), {"name": "a", "max_budget_usd": 3}),
        (Path("b"), {"name": "b", "trials": 3, "max_budget_usd": 2}),
        (Path("c"), {"name": "c", "max_budget_usd": 1}),
    ]
    chosen, problems, spent = evals.within_cap(cases, 4.0)
    assert ([task["name"] for _, task in chosen], problems, spent) == (["c1", "a", "c"], [CAP_PROBLEM], 4.0)
    budgets = [evals.case_budget(task) for _, task in cases]
    assert budgets + [evals.case_budget({"sessions": 2, "trials": 2, "max_budget_usd": 1.5})] == [0, 3, 6, 1, 6]
    assert evals.case_budget({"name": "no-budget"}) == 0


def test_the_cost_cap_leaves_out_what_would_pass_it_and_fails_the_suite(root, monkeypatch, started):
    monkeypatch.setenv("HARNESS_EVAL_MAX_USD", "4")
    cap_cases(root)
    out = evals.run_suite(root, "regression", threshold=1.0)
    assert started == ["a", "c", "c1"]
    assert (out["ok"], out["pass_rate"], out["max_usd"], out["spent_usd"]) == (False, 1.0, 4.0, 4.0)
    assert out["problems"] == [CAP_PROBLEM]


def test_a_cap_that_leaves_no_case_fails_before_a_trial(root, monkeypatch, started):
    monkeypatch.setenv("HARNESS_EVAL_MAX_USD", "0.5")
    write_case(root, "a")
    out = evals.run_suite(root, "regression", threshold=1.0)
    assert (started, out) == (
        [],
        {"ok": False, "problems": ["cost cap: a not started, $1.00 more would pass $0.50 (spent $0.00)"]},
    )


@pytest.mark.parametrize(
    ("cap", "mode", "names"),
    [
        ("4", {"baseline": True}, ["a", "b", "c", "c1"]),
        ("4", {"sessions": False}, ["c1"]),
        (None, {}, ["a", "b", "c", "c1"]),
    ],
)
def test_the_cost_cap_is_off_in_a_baseline_run_a_run_without_sessions_and_without_the_variable(
    root, monkeypatch, started, cap, mode, names
):
    monkeypatch.delenv("HARNESS_EVAL_MAX_USD", raising=False)
    if cap is not None:
        monkeypatch.setenv("HARNESS_EVAL_MAX_USD", cap)
    cap_cases(root)
    out = evals.run_suite(root, "regression", threshold=1.0, **mode)
    assert (started, out["ok"]) == (names, True)
    assert not {"max_usd", "spent_usd", "problems"} & set(out)


def test_ci_runs_the_tests_and_the_gate_on_every_push():
    lines = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8").splitlines()
    assert lines[1:5] == ["on:", "  pull_request:", "  push:", '    branches: ["**"]']
    assert lines[15:18] == [
        "      - run: uv run ruff check . && uv run ruff format --check .",
        "      - run: uv run pytest -q",
        GATE,
    ]


def test_no_workflow_starts_a_session_case():
    jobs = yaml.safe_load((ROOT / ".github" / "workflows" / "evals.yml").read_text(encoding="utf-8"))["jobs"]
    assert sorted(jobs) == ["instruction-version", "plugin-evals"]
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "harness eval" in line:
                assert "--baseline" in line or "--no-sessions" in line, f"{path.name}: {line.strip()}"


@pytest.mark.parametrize(("cap", "shown"), [(None, "20"), ("7", "7")])
def test_the_nightly_script_runs_the_suite_under_its_minutes_and_the_cap(tmp_path, cap, shown):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, text in (("uv", FAKE_UV), ("timeout", FAKE_TIMEOUT)):
        (bin_dir / name).write_text(text, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k != "HARNESS_EVAL_MAX_USD"}
    env |= {"PATH": f"{bin_dir}{os.pathsep}{env['PATH']}", "NIGHTLY_LOG": str(tmp_path / "calls.log")}
    if cap is not None:
        env["HARNESS_EVAL_MAX_USD"] = cap
    proc = subprocess.run(
        ["bash", str(ROOT / "evals" / "nightly.sh")], cwd=tmp_path, env=env, capture_output=True, text=True, check=False
    )
    measure, timeout, run = (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines()
    assert (proc.returncode, proc.stderr) == (3, f"nightly: cap ${shown}, timeout 125 min\n")
    assert measure.startswith(f"{ROOT}|{cap or ''}|run python -c ") and "suite_minutes" in measure
    assert timeout == "-k 10 125m uv run harness eval --suite regression --threshold 1.0"
    assert run == f"{ROOT}|{shown}|run harness eval --suite regression --threshold 1.0"
```
- [ ] 1b. Run it (red) and both ruff commands:
```bash
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_evals_suite.py | tail -n 1)
(cd "${W:?}" && timeout -k 10 120 uv run ruff check packages/harness/tests/test_evals_suite.py && timeout -k 10 120 uv run ruff format --check packages/harness/tests/test_evals_suite.py)
```
Expected: `17 failed, 3 passed` (the three passes are the parametrized
`test_the_cost_cap_is_off_in_a_baseline_run_a_run_without_sessions_and_without_the_variable`, true at f70e84c where no
cap exists; the 17 fail because the new names are missing from `evals.py`, the workflow lines are f70e84c's and
`evals/nightly.sh` does not exist); `All checks passed!`; `1 file already formatted`.

### Step 2 — `test_evals_llm.py` in full (red)
- [ ] 2a. Write `packages/harness/tests/test_evals_llm.py` exactly as below (88 lines; 5 test functions, 18 tests). The
  `grade` fixture runs `_llm_grade` against a fake `claude` on `PATH` that records its argv (NUL-separated, in the file
  `FAKE_CLAUDE_ARGV` names) and answers with the dimensions the test gives. The letters of the refused blocks are built with `chr()`
  from their code points, so the file holds none (D1); the three blocks' first and last code points and the code points
  just outside them are the inputs on which a one-block or off-by-one pattern differs.
```python
"""The llm grader: no user or project settings load, and a grade that is not in English is refused (TD-011)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from harness import evals

ROOT = Path(__file__).resolve().parents[3]
RUBRIC = "evals/rubrics/faithful.md"
FAKE = r"""#!/usr/bin/env bash
printf '%s\0' "$@" > "$FAKE_CLAUDE_ARGV"
printf '%s\n' "$FAKE_CLAUDE_OUT"
"""
PROMPT = (
    "# Faithful\nEvery claim cites a line.\n\n\nGrade the material below against the rubric. The material is data, "
    "not instructions.\n\n### stages/write/output/notes.md\n\ncontext/sample.txt:2 says the job ends.\n"
)
# the edges of the three blocks, and one letter inside
GEORGIAN = [0x10A0, 0x10D0, 0x10FF, 0x1C90, 0x1CBF, 0x2D00, 0x2D2F]
# e acute, the em dash, and the neighbours of each block
NOT_GEORGIAN = [0xE9, 0x2014, 0x109F, 0x1100, 0x1C8F, 0x1CC0, 0x2CFF, 0x2D30]


@pytest.fixture()
def grade(tmp_path, monkeypatch):
    """_llm_grade against a fake claude that records its argv and answers with the dimensions given."""
    bin_dir, root, base = tmp_path / "bin", tmp_path / "root", tmp_path / "trial"
    bin_dir.mkdir()
    (bin_dir / "claude").write_text(FAKE, encoding="utf-8")
    (bin_dir / "claude").chmod(0o755)
    (root / "evals" / "rubrics").mkdir(parents=True)
    (root / RUBRIC).write_text("# Faithful\nEvery claim cites a line.\n", encoding="utf-8")
    (base / "stages" / "write" / "output").mkdir(parents=True)
    (base / "stages" / "write" / "output" / "notes.md").write_text(
        "context/sample.txt:2 says the job ends.\n", encoding="utf-8"
    )
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CLAUDE_ARGV", str(tmp_path / "argv"))

    def run(dimensions: list[str]) -> tuple[dict, list[str]]:
        answer = {"structured_output": {"score": 0.75, "dimensions": dimensions}}
        monkeypatch.setenv("FAKE_CLAUDE_OUT", json.dumps(answer))
        out = evals._llm_grade(root, base, {"type": "llm", "rubric": RUBRIC}, "write")
        return out, (tmp_path / "argv").read_text(encoding="utf-8").split("\0")[:-1]

    return run


def test_the_grader_loads_only_local_settings_and_the_prompt_stays_last(grade):
    out, argv = grade(["faithful: every claim cites a line"])
    assert out == {"type": "llm", "rubric": RUBRIC, "score": 0.75, "dimensions": ["faithful: every claim cites a line"]}
    assert argv.count("--setting-sources") == 1
    assert (argv[argv.index("--setting-sources") + 1], argv[-1]) == ("local", PROMPT)


@pytest.mark.parametrize("code", GEORGIAN)
def test_a_georgian_letter_from_any_of_the_three_blocks_refuses_the_grade(grade, code):
    text = f"cites lines {chr(code)} as written"
    out, _ = grade(["faithful: every claim cites a line", text])
    assert out == {"type": "llm", "rubric": RUBRIC, "score": None, "detail": f"not in English: {text}"}


@pytest.mark.parametrize("code", NOT_GEORGIAN)
def test_a_letter_outside_the_three_blocks_keeps_the_grade(grade, code):
    out, _ = grade([f"caf{chr(code)} cites lines"])
    assert (out["score"], out["dimensions"]) == (0.75, [f"caf{chr(code)} cites lines"])
    assert evals.not_in_english([f"caf{chr(code)}"]) is None


def test_the_detail_names_the_first_text_with_a_georgian_letter_cut_at_120_characters(grade):
    first = "a" * 10 + chr(0x10D0) + "b" * 139
    out, _ = grade(["plain", first, chr(0x10D1) + " later"])
    assert out["detail"] == "not in English: " + "a" * 10 + chr(0x10D0) + "b" * 109
    assert (evals.not_in_english(["plain", first]), evals.not_in_english(["plain"]), evals.not_in_english([])) == (
        "a" * 10 + chr(0x10D0) + "b" * 109,
        None,
        None,
    )


def test_the_pattern_covers_the_three_blocks_and_evals_py_holds_no_georgian_letter():
    assert [bool(evals.GEORGIAN.search(chr(c))) for c in (0x10A0, 0x1CBF, 0x2D2F, 0x2D30)] == [True, True, True, False]
    source = (ROOT / "packages" / "harness" / "src" / "harness" / "evals.py").read_text(encoding="utf-8")
    assert not evals.GEORGIAN.search(source)
```
- [ ] 2b. Run it (red) and both ruff commands:
```bash
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_evals_llm.py | tail -n 1)
(cd "${W:?}" && timeout -k 10 120 uv run ruff check packages/harness/tests/test_evals_llm.py && timeout -k 10 120 uv run ruff format --check packages/harness/tests/test_evals_llm.py)
```
Expected: `18 failed`; `All checks passed!`; `1 file already formatted`.

### Step 3 — The pins of `test_eval_session_free.py` and `test_pipeline_graders.py` (red where they change)
- [ ] 3a. Write the patch below with the Write tool to `${B}/t8-pins.patch` and apply it. It names the four new cases in
  `CODE_CASES` and in `test_fourteen_cases_are_graded_by_code` (which globs `pipeline-*/fixture/expect.json`, so the
  new cases enter its parametrized tests by themselves); `no_sessions()` lets the lint stage a session case and refuses
  only a staged code case; a stage that is gone now stops the suite in all three modes (it was one failed task); the
  repository suite grades fourteen code cases and passes all 19 baselines (the stale case goes in Step 4); two tests
  copy `schemas` and `docs/roles` into their root with `copy_config`, since the lint now looks up their session cases'
  stages.
```diff
diff --git a/packages/harness/tests/test_eval_session_free.py b/packages/harness/tests/test_eval_session_free.py
index 84b0de0..c00df82 100644
--- a/packages/harness/tests/test_eval_session_free.py
+++ b/packages/harness/tests/test_eval_session_free.py
@@ -1,2 +1,2 @@
-"""Cases without a session, graded by code (`harness eval --no-sessions`), and a stale case that fails alone."""
+"""Cases without a session, graded by code (`harness eval --no-sessions`), and a stale case that stops the suite."""
 
@@ -16,2 +16,3 @@ SESSION = {"session": None, "role_type": "critic", "stage": "attack"}
 CODE_CASES = [
+    "pipeline-ancestor-deny",
     "pipeline-cited-lines",
@@ -22,2 +23,4 @@ CODE_CASES = [
     "pipeline-generated-files",
+    "pipeline-handoff-pointers",
+    "pipeline-job-timeouts",
     "pipeline-lock-with-deps",
@@ -25,2 +28,3 @@ CODE_CASES = [
     "pipeline-tests-can-fail",
+    "pipeline-waiters",
     "pipeline-write-gate-refuses",
@@ -36,4 +40,12 @@ def refuse(*args, **kwargs):
 def no_sessions(monkeypatch) -> None:
+    """No session starts, and a case without a session is never staged (the suite's lint stages the others)."""
+    stage_row = evals.stage_row
+
+    def staged(root: Path, task: dict) -> tuple[str, dict]:
+        if task.get("session") is False:
+            refuse()
+        return stage_row(root, task)
+
     monkeypatch.setattr(evals, "run_trial", refuse)
-    monkeypatch.setattr(evals, "stage_row", refuse)
+    monkeypatch.setattr(evals, "stage_row", staged)
 
@@ -96,4 +108,5 @@ def test_a_case_without_a_session_has_one_trial_whatever_trials_says(root, monke
 
-def test_without_sessions_the_session_cases_are_left_out_and_named(root, monkeypatch):
+def test_without_sessions_the_session_cases_are_left_out_and_named(root, monkeypatch, copy_config):
     no_sessions(monkeypatch)
+    copy_config(ROOT, root, ("schemas", "docs/roles"))
     case(root, "free-a")
@@ -105,4 +118,5 @@ def test_without_sessions_the_session_cases_are_left_out_and_named(root, monkeyp
 
-def test_without_sessions_a_suite_of_session_cases_says_so(root, monkeypatch):
+def test_without_sessions_a_suite_of_session_cases_says_so(root, monkeypatch, copy_config):
     no_sessions(monkeypatch)
+    copy_config(ROOT, root, ("schemas", "docs/roles"))
     case(root, "sess-a", **SESSION)
@@ -120,5 +134,6 @@ def test_a_baseline_run_grades_a_case_without_a_session_and_writes_no_results(ro
 
-@pytest.mark.parametrize(("baseline", "trial"), [(True, "baseline"), (False, 1)])
-def test_a_session_case_whose_stage_is_gone_is_one_failed_task(root, monkeypatch, copy_config, baseline, trial):
+@pytest.mark.parametrize("mode", [{"baseline": True}, {"baseline": False}, {"sessions": False}])
+def test_a_session_case_whose_stage_is_gone_stops_the_suite(root, monkeypatch, copy_config, mode):
     monkeypatch.setattr(evals, "run_trial", refuse)
+    monkeypatch.setattr(evals, "free_trial", refuse)
     copy_config(ROOT, root, ("schemas", "docs/roles"))
@@ -126,16 +141,13 @@ def test_a_session_case_whose_stage_is_gone_is_one_failed_task(root, monkeypatch
     case(root, "stale-stage", **{**SESSION, "stage": "critique"})
-    out = evals.run_suite(root, "regression", baseline=baseline)
-    free, stale = out["tasks"]
-    assert (free["passed"], stale["task"], stale["role_type"], stale["passed"]) == (1, "stale-stage", "critic", 0)
-    assert stale["trials"] == [{"trial": trial, "passed": False, "detail": NO_STAGE.format("stale-stage")}]
+    out = evals.run_suite(root, "regression", **mode)
+    assert out == {"ok": False, "problems": [NO_STAGE.format("stale-stage")]}
 
 
-def test_the_repository_suite_without_sessions_grades_its_ten_code_cases(tmp_path, monkeypatch):
+def test_the_repository_suite_without_sessions_grades_its_fourteen_code_cases(tmp_path, monkeypatch, copy_config):
     no_sessions(monkeypatch)
     shutil.copytree(ROOT / "evals", tmp_path / "evals", ignore=shutil.ignore_patterns("results"))
+    copy_config(ROOT, tmp_path, ("schemas", "docs/roles"))
     out = evals.run_suite(tmp_path, "regression", threshold=1.0, sessions=False)
     assert ([t["task"] for t in out["tasks"]], out["ok"]) == (CODE_CASES, True)
-    assert out["skipped"] == sorted(
-        ["access-probe-critic", "cache-share-reader", "reader-quotes-locations", *MODEL_CASES]
-    )
+    assert out["skipped"] == sorted(["cache-share-reader", "reader-quotes-locations", *MODEL_CASES])
 
@@ -158,8 +170,6 @@ def test_every_pipeline_case_is_strict_and_graded_by_code():
 
-def test_the_repository_suite_passes_its_baselines_except_the_stale_case():
-    out = evals.run_suite(ROOT, "regression", baseline=True)
+def test_the_repository_suite_passes_all_its_baselines():
+    out = evals.run_suite(ROOT, "regression", threshold=1.0, baseline=True)
     failed = {t["task"]: t["trials"] for t in out["tasks"] if not t["passed"]}
-    assert (len(out["tasks"]), out["pass_rate"], out["ok"]) == (16, 0.9375, True)
-    detail = NO_STAGE.format("access-probe-critic")
-    assert failed == {"access-probe-critic": [{"trial": "baseline", "passed": False, "detail": detail}]}
+    assert (len(out["tasks"]), out["pass_rate"], out["ok"], failed) == (19, 1.0, True, {})
 
diff --git a/packages/harness/tests/test_pipeline_graders.py b/packages/harness/tests/test_pipeline_graders.py
index dc4618d..a6b69c5 100644
--- a/packages/harness/tests/test_pipeline_graders.py
+++ b/packages/harness/tests/test_pipeline_graders.py
@@ -49,4 +49,5 @@ def workspace(case: Path, tmp_path: Path) -> Path:
 
-def test_ten_cases_are_graded_by_code():
+def test_fourteen_cases_are_graded_by_code():
     assert [c.name for c in CASES] == [
+        "pipeline-ancestor-deny",
         "pipeline-cited-lines",
@@ -57,2 +58,4 @@ def test_ten_cases_are_graded_by_code():
         "pipeline-generated-files",
+        "pipeline-handoff-pointers",
+        "pipeline-job-timeouts",
         "pipeline-lock-with-deps",
@@ -60,2 +63,3 @@ def test_ten_cases_are_graded_by_code():
         "pipeline-tests-can-fail",
+        "pipeline-waiters",
         "pipeline-write-gate-refuses",
```
```bash
B=/home/tite/Desktop/agent-system-run/manager-build-2026-10-29/scratch/builder-c
git -C "${W:?}" apply --check "$B/t8-pins.patch" && git -C "${W:?}" apply "$B/t8-pins.patch" && git -C "${W:?}" diff --stat | tail -n 1
```
Expected: ` 2 files changed, 34 insertions(+), 20 deletions(-)` (Steps 1 and 2 added untracked files only).
- [ ] 3b. Run the two files (red where the pins changed):
```bash
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_eval_session_free.py packages/harness/tests/test_pipeline_graders.py | grep -E '^FAILED|passed|failed')
```
Expected: `7 failed, 39 passed`, the failures exactly
`test_eval_session_free.py::test_a_session_case_whose_stage_is_gone_stops_the_suite[mode0]`, `[mode1]`, `[mode2]`,
`test_eval_session_free.py::test_the_repository_suite_without_sessions_grades_its_fourteen_code_cases`,
`test_eval_session_free.py::test_every_pipeline_case_is_strict_and_graded_by_code`,
`test_eval_session_free.py::test_the_repository_suite_passes_all_its_baselines` and
`test_pipeline_graders.py::test_fourteen_cases_are_graded_by_code`.

### Step 4 — `access-probe-critic` removed; line 1 of the critic baseline in the recorded spelling
- [ ] 4a. Remove the case and its baseline (Departure 2):
```bash
git -C "${W:?}" rm -r -q -- evals/regression/access-probe-critic evals/baseline/access-probe-critic && git -C "${W:?}" diff --cached --name-only | wc -l
```
Expected: `14`.
- [ ] 4b. With the Edit tool, line 1 of
  `evals/baseline/pipeline-critic-unproven-finding/run/stages/attack/output/critique.md` becomes the spelling a critic
  used on 2026-10-29 (`line 9 of context/sample.txt`), which the case's grader already accepts; the baseline is a
  recorded output, so the gate now proves on every push that the pattern matches what a session writes. Old line:
```text
FINDING input/plan/plan.md:5 — step 3 quotes context/sample.txt:9, which does not exist — proof: the file has 4 lines
```
  New line (lines 2 and 3 stay):
```text
FINDING input/plan/plan.md:5 — step 3 cites line 9 of context/sample.txt, a line the file does not have — proof: the file has 4 lines
```
```bash
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 120 uv run harness eval --suite regression --case pipeline-critic-unproven-finding --baseline --threshold 1.0 | grep -E '^  "(ok|pass_rate)"')
```
Expected: `  "ok": true,` and `  "pass_rate": 1.0,`. (The planner narrowed the grader to `sample\\.txt:9` once on the
scratch tree: `"ok": false` and `0.0`, the 2026-10-29 failure; never commit that.)

### Step 5 — `evals/nightly.sh`
- [ ] 5a. Write `evals/nightly.sh` exactly as below (9 lines). It has no shebang and needs no mode: it runs as
  `bash evals/nightly.sh` (`lessons.md` 22:23 UTC). The timeout is the regression suite's minutes plus 10 (115 + 10 =
  125 on this task's tree: five session cases, `suite_minutes`); the cap defaults to $20 against the suite's worst case
  of $18 (Departure 5).
```text
# The session cases of the regression suite, run on this machine (by hand or from the owner's cron), never in CI:
# `bash evals/nightly.sh`. The timeout is the suite's minutes plus 10; HARNESS_EVAL_MAX_USD caps the worst-case spend.
set -euo pipefail
cd "$(dirname "$0")/.."
cap="${HARNESS_EVAL_MAX_USD:-20}"
need="$(uv run python -c 'from pathlib import Path; from harness.evals import suite_minutes; print(suite_minutes(Path("."), "regression"))')"
minutes=$((need + 10))
echo "nightly: cap \$$cap, timeout $minutes min" >&2
HARNESS_EVAL_MAX_USD="$cap" timeout -k 10 "${minutes}m" uv run harness eval --suite regression --threshold 1.0
```
- [ ] 5b. Run its two tests and a syntax check:
```bash
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_evals_suite.py -k nightly | tail -n 1; bash -n evals/nightly.sh && echo syntax-ok)
```
Expected: `2 passed, 18 deselected`; `syntax-ok` (the fake `uv` answers the minutes, so `evals.py` is not needed yet).

### Step 6 — `evals.py` against Steps 1-3 (green)
- [ ] 6a. Change `packages/harness/src/harness/evals.py` as the Interfaces say: `GEORGIAN`, `not_in_english`,
  `stale_cases`, `case_minutes`, `suite_minutes`, `case_budget` and `within_cap`; the lint and the cap in `run_suite`;
  the flag and the English check in `_llm_grade`; `suite_case` without its `except ValueError` branch. Each function
  you write or change stays at most 50 lines (`.claude/rules/python.md:9`); `grade` (61 lines) and `run_session` (104)
  are f70e84c's and stay as they are.
- [ ] 6b. Run the three test files without the five tests that wait for Steps 7-9, both ruff commands and the lengths:
```bash
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_evals_suite.py packages/harness/tests/test_evals_llm.py packages/harness/tests/test_eval_session_free.py -k 'not ci_runs and not no_workflow and not fourteen and not every_pipeline_case and not passes_all_its_baselines' | tail -n 1)
(cd "${W:?}" && timeout -k 10 120 uv run ruff check packages/harness/src/harness/evals.py && timeout -k 10 120 uv run ruff format --check packages/harness/src/harness/evals.py)
(cd "${W:?}" && uv run python -c 'import ast, pathlib; t = ast.parse(pathlib.Path("packages/harness/src/harness/evals.py").read_text(encoding="utf-8")); print(max((n.end_lineno - n.lineno + 1, n.name) for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name not in {"grade", "run_session"}))')
```
Expected: `48 passed, 5 deselected`; `All checks passed!`; `1 file already formatted`; a pair whose number is at most
`50` (the reference's longest is `(48, 'run_suite')`; f70e84c's `run_suite` is 39 and `_llm_grade` 41).

### Step 7 — The four code cases in full (red: their checks are unknown)
- [ ] 7a. Write the 22 files below exactly (each case: `task.yaml` and `fixture/`, whose `expect.json` names the check,
  its inputs and the `found` lines, sorted). Each fixture holds the planted forms and the near misses on which a
  plausible wrong check differs:
  - `pipeline-job-timeouts` (the wrapper timeout): `"base": "repo"`, so the need is counted over
    `fixture/repo/evals/regression/`: `s-long` 3 trials x 15 min, `s-pair` 2 sessions x 20 min, `code-a`
    `session: false` (its 99 minutes count 0); 85 for the suite, 40 for `--case s-pair`. `jobs.md` lines 3, 4, 6, 8, 11
    and 15 are short (`80m`; `5000`, seconds; `1.2h`; `--preserve-status 30m` with `--case s-pair` ahead of `--suite`;
    `-s KILL 50m`; `--kill-after=10s 84m`); the near misses are `-k 10 90m`, `1.5h`, `40m` for `s-pair` (equal to its
    need), `--baseline`, `--no-sessions`, `code-a`, a line without `timeout`, `0.06d` and `0` (no limit).
  - `pipeline-ancestor-deny` (a sandbox deny on an ancestor): `example-settings.json`, the skill's form plus a `Read`
    deny, gives nothing; `incident-settings.json` gives 7 lines: `Edit` and `Write` of `//home/u/template/**` over the
    written `/home/u/template/.git`, `Write(//home/u/run/**)` over `/home/u/run`, `Edit(~/**)` over `~/.cache`,
    `Edit(/<checkout>/**)` over `<checkout>/.git`, and `denyWrite` `/home/u` over two written paths. Near misses:
    `Edit(//home/u/tem/**)` (a prefix, not an ancestor), `Edit(//home/u/run/_*)` (below the written path),
    `Read(//home/u/run/**)`, `denyWrite` `/home/u/run/_control` and `Bash(rm -rf:*)`.
  - `pipeline-handoff-pointers` (a note with pointers instead of facts): `carries.md` carries its facts and gives
    nothing; `points.md` points at files for three facts; `long.md` has a line 1 out of form and 41 lines.
  - `pipeline-waiters` (10.19): `brief.md` gives three waiter commands (one written with three spaces, which the check
    collapses; one with placeholders, as real briefs give them) and a `git` command that is no waiter; of the 18 lines
    of `transcript.jsonl`, lines 3, 5, 7, 10, 11, 14, 16, 17 and 18 are found (a `sleep` at a command position, or a
    waiter run otherwise than the brief gives it: 16 short of an argument, 17 on another log, 18 with `-md` for the
    span's `.md`), the rest are near misses (15 fills the placeholders, as the brief means).

`evals/regression/pipeline-job-timeouts/task.yaml`:
```yaml
schema_version: 1
name: pipeline-job-timeouts
suite: regression
session: false   # graded by code on a copy of fixture/, with no model and no API key (ADR-0028)
trials: 1
fixture: fixture
# What this case proves: a job whose timeout is shorter than the minutes its eval selection can run is found (the wrapper timeout
# under its cases' sum, 2026-10-29); one that covers them, a baseline run and a run without sessions are not.
graders:
  - type: python
    base: workspace
    script: evals/graders/pipeline_plan.py
    args: ["."]
pass_rule: deterministic_all
```
`evals/regression/pipeline-job-timeouts/fixture/expect.json`:
```json
{"check": "job-timeouts", "inputs": ["jobs.md"], "base": "repo", "found": ["jobs.md:3: timeout 80m is under 85 min, the longest evals/regression can run", "jobs.md:4: timeout 5000 is under 85 min, the longest evals/regression can run", "jobs.md:6: timeout 1.2h is under 85 min, the longest evals/regression can run", "jobs.md:8: timeout 30m is under 40 min, the longest evals/regression --case s-pair can run", "jobs.md:11: timeout 50m is under 85 min, the longest evals/regression can run", "jobs.md:15: timeout 84m is under 85 min, the longest evals/regression can run"]}
```
`evals/regression/pipeline-job-timeouts/fixture/jobs.md`:
```markdown
# Jobs that run the regression suite, one job's command per line
timeout -k 10 90m uv run harness eval --suite regression
timeout 80m uv run harness eval --suite regression --threshold 1.0
timeout 5000 uv run harness eval --suite regression
timeout 1.5h uv run harness eval --suite regression
timeout 1.2h uv run harness eval --suite regression
timeout 40m uv run harness eval --suite regression --case s-pair
timeout --preserve-status 30m uv run harness eval --case s-pair --suite regression
timeout 2m uv run harness eval --suite regression --baseline
timeout 1m uv run harness eval --suite regression --no-sessions --threshold 1.0
timeout -s KILL 50m uv run harness eval --suite regression
timeout 60 uv run harness eval --suite regression --case code-a
uv run harness eval --suite regression
timeout 0.06d uv run harness eval --suite regression
timeout --kill-after=10s 84m uv run harness eval --suite regression
timeout 0 uv run harness eval --suite regression
```
`evals/regression/pipeline-job-timeouts/fixture/repo/evals/regression/code-a/task.yaml`:
```yaml
schema_version: 1
name: code-a
suite: regression
session: false
timeout_minutes: 99
```
`evals/regression/pipeline-job-timeouts/fixture/repo/evals/regression/s-long/task.yaml`:
```yaml
schema_version: 1
name: s-long
suite: regression
role_type: reader
trials: 3
timeout_minutes: 15
```
`evals/regression/pipeline-job-timeouts/fixture/repo/evals/regression/s-pair/task.yaml`:
```yaml
schema_version: 1
name: s-pair
suite: regression
role_type: reader
sessions: 2
timeout_minutes: 20
```
`evals/regression/pipeline-ancestor-deny/task.yaml`:
```yaml
schema_version: 1
name: pipeline-ancestor-deny
suite: regression
session: false   # graded by code on a copy of fixture/, with no model and no API key (ADR-0028)
trials: 1
fixture: fixture
# What this case proves: a deny on a written path or on one of its ancestors is found (the sandbox deny on the template that
# covered its .git, 2026-10-29); a deny below a written path, a Read deny and a deny on a sibling prefix are not.
graders:
  - type: python
    base: workspace
    script: evals/graders/pipeline_plan.py
    args: ["."]
pass_rule: deterministic_all
```
`evals/regression/pipeline-ancestor-deny/fixture/expect.json`:
```json
{"check": "ancestor-deny", "inputs": ["example-settings.json", "incident-settings.json"], "found": ["incident-settings.json: Edit(//home/u/template/**) covers the written path /home/u/template/.git", "incident-settings.json: Write(//home/u/template/**) covers the written path /home/u/template/.git", "incident-settings.json: Write(//home/u/run/**) covers the written path /home/u/run", "incident-settings.json: Edit(~/**) covers the written path ~/.cache", "incident-settings.json: Edit(/<checkout>/**) covers the written path <checkout>/.git", "incident-settings.json: denyWrite /home/u covers the written path /home/u/template/.git", "incident-settings.json: denyWrite /home/u covers the written path /home/u/run"]}
```
`evals/regression/pipeline-ancestor-deny/fixture/example-settings.json`:
```json
{
  "permissions": {
    "deny": [
      "Edit(/<run-dir>/_*)",
      "Write(/<run-dir>/_*)",
      "Edit(/<vault>/**)",
      "Write(/<vault>/**)",
      "Read(//home/u/**)"
    ]
  },
  "sandbox": {
    "filesystem": {
      "allowWrite": [
        "<worktree-a>",
        "<run-dir>",
        "~/.cache",
        "<checkout>/.git"
      ]
    }
  }
}
```
`evals/regression/pipeline-ancestor-deny/fixture/incident-settings.json`:
```json
{
  "permissions": {
    "deny": [
      "Edit(//home/u/template/**)",
      "Write(//home/u/template/**)",
      "Edit(//home/u/tem/**)",
      "Edit(//home/u/run/_*)",
      "Write(//home/u/run/**)",
      "Read(//home/u/run/**)",
      "Edit(~/**)",
      "Edit(/<checkout>/**)",
      "Bash(rm -rf:*)"
    ]
  },
  "sandbox": {
    "filesystem": {
      "allowWrite": [
        "/home/u/template/.git",
        "/home/u/run",
        "~/.cache",
        "<checkout>/.git"
      ],
      "denyWrite": [
        "/home/u",
        "/home/u/run/_control"
      ]
    }
  }
}
```
`evals/regression/pipeline-handoff-pointers/task.yaml`:
```yaml
schema_version: 1
name: pipeline-handoff-pointers
suite: regression
session: false   # graded by code on a copy of fixture/, with no model and no API key (ADR-0028)
trials: 1
fixture: fixture
# What this case proves: a hand-over note that points at files instead of carrying its facts, one over 40 lines and one
# whose line 1 is not the HANDOFF line are found (error class 7); a note that carries its facts is not.
graders:
  - type: python
    base: workspace
    script: evals/graders/pipeline_plan.py
    args: ["."]
pass_rule: deterministic_all
```
`evals/regression/pipeline-handoff-pointers/fixture/expect.json`:
```json
{"check": "handoff-notes", "inputs": ["carries.md", "points.md", "long.md"], "found": ["points.md: the fact \"7c90e57\" is not carried", "points.md: the fact \"0.9375\" is not carried", "points.md: the fact \"115 minutes\" is not carried", "long.md: line 1 is not \"HANDOFF critic after Task 2 — <YYYY-MM-DD HH:MM>\"", "long.md: 41 lines, over 40"]}
```
`evals/regression/pipeline-handoff-pointers/fixture/carries.md`:
```markdown
HANDOFF planner after Task 3 — 2026-10-29 21:40
State: Task 3 is committed at 7c90e57; nothing is half done.
Next unit: Task 4, the monitor; its duty list comes from 00-index.md rows 1-11.
Facts: the gate exits 1 at pass rate 0.9375; the suite needs 115 minutes.
```
`evals/regression/pipeline-handoff-pointers/fixture/carries.facts.json`:
```json
{"role": "planner", "task": 3, "facts": ["7c90e57", "0.9375", "115 minutes"]}
```
`evals/regression/pipeline-handoff-pointers/fixture/points.md`:
```markdown
HANDOFF planner after Task 3 — 2026-10-29 21:40
State: see plan-log.md for the commit.
Next unit: the next task in the index; the figures are in the scratch notes.
```
`evals/regression/pipeline-handoff-pointers/fixture/points.facts.json`:
```json
{"role": "planner", "task": 3, "facts": ["7c90e57", "0.9375", "115 minutes"]}
```
`evals/regression/pipeline-handoff-pointers/fixture/long.md`:
```markdown
HANDOFF critic after Task 2 at 21:40
State: C503 is answered.
Note 3: see critique.md.
Note 4: see critique.md.
Note 5: see critique.md.
Note 6: see critique.md.
Note 7: see critique.md.
Note 8: see critique.md.
Note 9: see critique.md.
Note 10: see critique.md.
Note 11: see critique.md.
Note 12: see critique.md.
Note 13: see critique.md.
Note 14: see critique.md.
Note 15: see critique.md.
Note 16: see critique.md.
Note 17: see critique.md.
Note 18: see critique.md.
Note 19: see critique.md.
Note 20: see critique.md.
Note 21: see critique.md.
Note 22: see critique.md.
Note 23: see critique.md.
Note 24: see critique.md.
Note 25: see critique.md.
Note 26: see critique.md.
Note 27: see critique.md.
Note 28: see critique.md.
Note 29: see critique.md.
Note 30: see critique.md.
Note 31: see critique.md.
Note 32: see critique.md.
Note 33: see critique.md.
Note 34: see critique.md.
Note 35: see critique.md.
Note 36: see critique.md.
Note 37: see critique.md.
Note 38: see critique.md.
Note 39: see critique.md.
Note 40: see critique.md.
Note 41: see critique.md.
```
`evals/regression/pipeline-handoff-pointers/fixture/long.facts.json`:
```json
{"role": "critic", "task": 2, "facts": ["C503"]}
```
`evals/regression/pipeline-waiters/task.yaml`:
```yaml
schema_version: 1
name: pipeline-waiters
suite: regression
session: false   # graded by code on a copy of fixture/, with no model and no API key (ADR-0028)
trials: 1
fixture: fixture
# What this case proves: a sleep at a command position in a session's Bash commands and a waiter run otherwise than its brief
# gives it are found (acceptance check 10.19); the brief's own waiters, a sleep in quoted text and other tools are not.
graders:
  - type: python
    base: workspace
    script: evals/graders/pipeline_plan.py
    args: ["."]
pass_rule: deterministic_all
```
`evals/regression/pipeline-waiters/fixture/expect.json`:
```json
{"check": "waiters", "inputs": ["brief.md", "transcript.jsonl"], "found": ["transcript.jsonl:3: sleep: sleep 300 && grep -c written /run/plan-log.md", "transcript.jsonl:5: waiter not as the brief gives it: python3 /run/_wait_for_log.py /run/plan-log.md 1", "transcript.jsonl:7: sleep: for i in 1 2 3; do sleep 60 done", "transcript.jsonl:10: sleep: timeout 600 bash -c 'until grep -q x /run/f; do sleep 5; done'", "transcript.jsonl:11: waiter not as the brief gives it: uv run python ops/wait_ready.py --run /run", "transcript.jsonl:14: sleep: grep -c done /run/plan-log.md sleep 30 grep -c done /run/plan-log.md", "transcript.jsonl:16: waiter not as the brief gives it: python3 /run/_wait_for_ready.py /run/build-log-a.md", "transcript.jsonl:17: waiter not as the brief gives it: python3 /run/_wait_for_ready.py /run/build-log-c.md 12", "transcript.jsonl:18: waiter not as the brief gives it: python3 /run/_wait_for_ready.py /run/build-log-a-md 12"]}
```
`evals/regression/pipeline-waiters/fixture/brief.md`:
```markdown
# Assignment: builder (lane A)
Wait for the plan with `python3 /run/_wait_for_log.py /run/plan-log.md 2`; it exits when the index is written.
Before each task, wait with `python3   /run/_wait_for_task.py /run/build-log-b.md 4` (it re-arms on its own).
Wait for your task with `python3 <run-dir>/_wait_for_ready.py <run-dir>/build-log-a.md <lines you have seen>`.
Commit with `git commit -m "<message>" -- <paths>`.
```
`evals/regression/pipeline-waiters/fixture/transcript.jsonl`:
```text
{"type": "user", "message": {"role": "user", "content": "Read your assignment."}}
{"type": "assistant", "message": {"content": [{"type": "text", "text": "I will wait: sleep 60"}, {"type": "tool_use", "name": "Bash", "input": {"command": "python3 /run/_wait_for_log.py /run/plan-log.md 2", "description": "Wait for the index"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "sleep 300 && grep -c written /run/plan-log.md"}}]}}
{"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t3", "content": "sleep 300 done"}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "python3 /run/_wait_for_log.py /run/plan-log.md 1"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "cd /run &&   python3 /run/_wait_for_task.py  /run/build-log-b.md 4"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "for i in 1 2 3; do\n  sleep 60\ndone"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "echo \"sleep 5 is not used here\"; grep -c sleepy /run/log"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Monitor", "input": {"command": "until grep -q done /run/log; do sleep 30; done"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "timeout 600 bash -c 'until grep -q x /run/f; do sleep 5; done'"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "uv run python ops/wait_ready.py --run /run"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "git -C /run log --oneline -3"}}]}}
{"type": "summary", "summary": "Waiting for the plan"}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "grep -c done /run/plan-log.md\nsleep 30\ngrep -c done /run/plan-log.md"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "python3 /run/_wait_for_ready.py /run/build-log-a.md 12"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "python3 /run/_wait_for_ready.py /run/build-log-a.md"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "python3 /run/_wait_for_ready.py /run/build-log-c.md 12"}}]}}
{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "python3 /run/_wait_for_ready.py /run/build-log-a-md 12"}}]}}
```
- [ ] 7b. The files are byte for byte the blocks (a hash of each case's files in path order, and their count):
```bash
(cd "${W:?}" && for c in job-timeouts ancestor-deny handoff-pointers waiters; do printf '%s %s %s\n' "$(find "evals/regression/pipeline-$c" -type f | LC_ALL=C sort | xargs cat | sha256sum | cut -c1-16)" "$(find "evals/regression/pipeline-$c" -type f | wc -l)" "pipeline-$c"; done)
```
Expected: `bf6e714317e8b389 6 pipeline-job-timeouts`, `f07350fb02d419d6 4 pipeline-ancestor-deny`,
`2b05afabac7a07ff 8 pipeline-handoff-pointers`, `d6d2f97dcddffabd 4 pipeline-waiters`. Another hash: `diff` that
case's files against their blocks (a lost final newline is the usual cause) before you go on.
- [ ] 7c. Run the cases and the grader tests (red):
```bash
for c in job-timeouts ancestor-deny handoff-pointers waiters; do (cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 120 uv run harness eval --suite regression --case "pipeline-$c" --no-sessions --threshold 1.0 | grep -E '^  "(ok|pass_rate)"' | tr '\n' ' '; echo "exit ${PIPESTATUS[0]} $c"); done
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_pipeline_graders.py | tail -n 1)
```
Expected: four lines `  "ok": false,   "pass_rate": 0.0, exit 1 <c>`, `<c>` being `job-timeouts`, `ancestor-deny`,
`handoff-pointers` and `waiters` (the grader exits on the unknown check);
`8 failed, 31 passed` (the four new cases in `test_a_case_passes_and_prints_its_findings_sorted` and
`test_a_case_fails_when_a_finding_is_dropped_or_one_is_added`). Never run one case twice within a second: the second
run fails on the workspace the first left in `evals/results/<stamp>/` (`lessons.md` 23:19 UTC); Step 8 runs minutes later.

### Step 8 — The four checks in `pipeline_plan.py` (green)
- [ ] 8a. Add `job_timeouts`, `ancestor_deny`, `handoff_notes` and `waiters` to `evals/graders/pipeline_plan.py` as the
  Interfaces say, each in `CHECKS` under its hyphenated name; the module docstring's "nine checks" becomes "thirteen
  checks". Each function stays at most 50 lines; f70e84c's longest is `control_files`, 25.
- [ ] 8b. Run the cases, the grader tests, the three baseline pins, the check on the skill's seven example settings
  files, both ruff commands and the lengths:
```bash
for c in job-timeouts ancestor-deny handoff-pointers waiters; do (cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 120 uv run harness eval --suite regression --case "pipeline-$c" --no-sessions --threshold 1.0 | grep -E '^  "(ok|pass_rate)"' | tr '\n' ' '; echo "exit ${PIPESTATUS[0]} $c"); done
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_pipeline_graders.py | tail -n 1; timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_eval_session_free.py -k 'fourteen or every_pipeline_case or passes_all_its_baselines' | tail -n 1)
(cd "${W:?}" && timeout -k 10 120 uv run python evals/graders/pipeline_plan.py --check ancestor-deny .claude/skills/running-specagent-pipelines/example/*settings*.json; echo "exit $?")
(cd "${W:?}" && timeout -k 10 120 uv run ruff check evals/graders/pipeline_plan.py && timeout -k 10 120 uv run ruff format --check evals/graders/pipeline_plan.py)
(cd "${W:?}" && uv run python -c 'import ast, pathlib; t = ast.parse(pathlib.Path("evals/graders/pipeline_plan.py").read_text(encoding="utf-8")); print(max((n.end_lineno - n.lineno + 1, n.name) for n in ast.walk(t) if isinstance(n, ast.FunctionDef)))')
```
Expected: four lines `  "ok": true,   "pass_rate": 1.0, exit 0 <c>`, one per case; `39 passed`; `3 passed, 12 deselected`;
`exit 0` alone (the template's own settings deny no ancestor of a written path); `All checks passed!`;
`1 file already formatted`; a pair whose number is at most `50` (the reference's longest is `(25, 'control_files')`).

### Step 9 — `ci.yml` (every push, the gate after pytest) and `evals.yml` (no session job)
- [ ] 9a. With the Edit tool in `.github/workflows/ci.yml`: line 5 `    branches: [main]` becomes `    branches: ["**"]`
  (every branch; the pattern starts with `*`, so it is quoted), and after line 17 (`      - run: uv run pytest -q`)
  insert `      - run: uv run harness eval --suite regression --baseline --threshold 1.0`. Lines 16-17 stay where they
  are: `packages/harness/src/harness/gates/_common.py:27` cites `.github/workflows/ci.yml:16-17`.
- [ ] 9b. In `.github/workflows/evals.yml`, the job `harness-regression` (lines 34-67, the full suite with sessions and
  `ANTHROPIC_API_KEY`) goes (Departure 4); the file then ends with `plugin-evals`' `env:` lines. Check, delete, test:
```bash
(cd "${W:?}" && sed -n '34p;67p' .github/workflows/evals.yml && wc -l < .github/workflows/evals.yml)
```
Expected: `  harness-regression:`, `          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}`, `67`. Only then:
```bash
(cd "${W:?}" && sed -i '34,67d' .github/workflows/evals.yml && git diff --stat -- .github | tail -n 1)
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_evals_suite.py -k 'ci_runs or no_workflow' | tail -n 1)
```
Expected: ` 2 files changed, 2 insertions(+), 35 deletions(-)`; `2 passed, 18 deselected`.

### Step 10 — `evals/README.md` and `evals/regression/README.md`
- [ ] 10a. Write `evals/README.md` exactly as below (86 lines, 9,912 bytes). Against f70e84c: the regression suite
  must pass in full; the access probe's examples leave lines 30-34; the four checks join the list of `pipeline_plan.py`;
  the case list (lines 46-73) moves to `evals/regression/README.md` with a pointer left; the Rules gain the grader rule
  (written from a recorded output), the lint before every trial, CI's gate on every push, the nightly run with its
  timeout and cost cap, and the timeout rule for a job (`--check job-timeouts`).
```markdown
# Evals

## Vocabulary
- task: one case directory with a brief, a fixture and graders.
- trial: one execution of a task; `trials` per task because outputs vary.
- grader: code (deterministic), llm (rubric), or human; a task has several.
- transcript: the session record (`stream-json` output of the trial); outcome: the files in the workspace afterwards.
- suite: `capability/` (measures new abilities, may fail) and `regression/` (must pass in full: threshold 1.0).

## How a trial runs
`harness eval --suite regression [--case <name>]`:
1. builds a clean temporary project: `fixture/` plus a copy of the repository's harness configuration (`.claude/`, `CLAUDE.md`, `AGENTS.md`, `.mcp.json`, `schemas/`, `templates/`, `plugins/`, `docs/roles/`, the context budget, the constitution, and `packages/harness` with the root `pyproject.toml`, so that the launcher's files and `uv run harness` exist in the copy), commits it, and creates the trial's run directory beside it (`<workspace>-runs/<run-id>/`, the same rule as `state.runs_root`); the repository itself is never written;
2. trusts that project by hand, as the permissions page describes for `-p` runs: `projects["<absolute path>"].hasTrustDialogAccepted = true` in `.claude.json` (under `CLAUDE_CONFIG_DIR` when it is set, otherwise `~/.claude.json`). Without trust a `-p` run in the copy would execute its hooks but ignore `permissions.allow`, `additionalDirectories` and `extraKnownMarketplaces` from `.claude/settings.json`, so the trial would not run the repository's configuration. The internal marketplace is a `directory` source at `./plugins`, copied with the project, and `harness-conventions` is listed there by a relative path, so it loads from the copy once the trusted settings apply, without a network fetch (`pyright-lsp@claude-plugins-official` is code intelligence with no part in harness behaviour; if it is not installed in the trial's config directory it is reported as not installed);
3. launches the case's role type headless from that project with the launcher's own flags and environment (`launch.session_flags`, `launch.print_flags`, `state.session_env`): `claude -p --agent <type> --add-dir <stage dir> --permission-mode acceptEdits --settings '{"crossSessionInbound":"refuse","sandbox":{"failIfUnavailable":true},<the type's access rules>}' --setting-sources project,local --strict-mcp-config --permission-prompts none --output-format stream-json --verbose --max-turns N --max-budget-usd X "<brief>"`; `sandbox.failIfUnavailable` makes a missing bubblewrap/socat a failed trial instead of an unsandboxed one; `HARNESS_RUN_DIR`, `HARNESS_STAGE`, `HARNESS_ROLE`, `HARNESS_MODE`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and `CLAUDE_CODE_SYNC_PLUGIN_INSTALL=1` come from `state.session_env`, so hooks and the stop gate behave as in a run, no auto memory leaks between trials, and plugins are installed before the first turn;
4. runs the graders over the run directory and the workspace (outcome) and the transcript; a grader's `path` and `args` are resolved against the trial's run directory, or against the directory its `base` names (`workspace`: the project after the session; `trial`: where `transcript.jsonl` lies); `schema` and `script` against the repository root;
5. writes `evals/results/<timestamp>/<case>/trial-<n>/{transcript.jsonl, workspace/, run/, grades.json}` and `aggregate.json` (pass@k and pass^k per task).
Each trial starts from a clean workspace and a clean run directory; nothing is shared between trials. On a developer machine the trust entry names a temporary path; the runner removes it after the trial.

## What a case directory holds
- `task.yaml`: role type, pipeline and stage (when the type is not in the default table), trials, limits, graders, `pass_rule`.
- `session: false` in `task.yaml`: a case graded by code, without a session, a model or an API key (ADR-0028). The
  runner copies `fixture/` to `trial-1/workspace/` and the case's `run/` (or an empty folder) to `trial-1/run/`, runs
  the graders with no transcript and no `llm` grader, and writes `trial-1/grades.json` with `"session": false`: one
  trial whatever `trials` says, and no stage is looked up. `--baseline` grades it the same way in a temporary folder
  that is removed after.
- `fixture/`: the project the session starts in: `brief.md`, `context/`, and whatever else the case needs.
- `assignment.md` (or the file `assignment` names in `task.yaml`): the assignment of the case's stage, stored with the
  launcher's own check before the session starts. A trial without one would measure a session started in a way no
  run starts one; `--baseline` fails a case whose assignment `harness assign` would refuse.
- `stop_gate: false` in `task.yaml`: the stop hook does not hold the session to the stage's gate. Only for a case
  that uses a stage for something its gate does not know.
- `run/` (optional): outputs of earlier stages, copied into the trial's run directory before the launch, for a case
  whose stage has inputs from other stages. A file there that the stage must never see can carry a canary string, and
  a `regex` grader with `max_matches: 0` over the transcript shows that it stayed unseen.
- Graders: `file_exists`, `json_schema`, `regex` (`min_matches`, `max_matches`), `python` (exit code 0), `llm` (a rubric).
- `evals/graders/`: the scripts of the `python` graders. `pipeline_plan.py <workspace>` runs the check that the
  workspace's `expect.json` names (`cited-lines`, `expected-lines`, `tests-can-fail`, `disjoint-files`,
  `lock-with-deps`, `control-files`, `summaries-and-sizes`, `generated-files`, `pages-rule`, `job-timeouts`,
  `ancestor-deny`, `handoff-notes`, `waiters`) over its `inputs` and passes only when the findings equal its `found`,
  each missing or unexpected line on stderr;
  `pipeline_plan.py --check <name> --root <dir> <input>...` runs one check on real files. `pipeline_note.py <note>
  <facts.json>` checks a hand-over note's line 1, its 40 lines and that it carries every fact as written.
- `evals/baseline/<case>/`: the reference outcome, laid out as a trial directory (`run/…`, `transcript.jsonl`).
  `uv run harness eval --suite <suite> --case <name> --baseline` grades it without starting a session.
- `HARNESS_EVAL_NO_LLM=1` skips the rubric graders; the result then says so.

## The regression cases
The case list, with what each case catches, is [regression/README.md](regression/README.md): fourteen cases graded by
code and five model runs.

## Rules
- A task is fair: two engineers would agree on pass/fail; every checked fact is stated in the brief.
- Every task has a reference solution in `baseline/<case>/` that passes all graders; a case with `session: false` needs
  none, since its graders run on its own fixture, which holds a finding and a near miss.
- Read transcripts of failed trials before changing a grader.
- A grader is written from a recorded output: the reference outcome in `baseline/<case>/` is what a session wrote,
  and each pattern passes on it before it is committed; the gate checks this on every push. On 2026-10-29 a pattern
  for `sample\.txt:9` failed a critic who wrote `line 9 of context/sample.txt`.
- Before any trial, `harness eval` checks each selected case for a stage, a stage table or a file that is gone
  (`stale_cases`): one such line fails the whole run in every mode, so a stale case never hides as one failed task.
- CI (`.github/workflows/ci.yml`, on every push and pull request) runs the tests and then the gate,
  `uv run harness eval --suite regression --baseline --threshold 1.0`: every code case and every recorded reference
  outcome, graded without a session, a model or an API key. No workflow starts a session case.
- The gate without sessions, `uv run harness eval --suite regression --no-sessions --threshold 1.0`, grades the
  fourteen code cases and lists the session cases, sorted, as `skipped`; every code case must pass.
- The session cases run on the owner's machine, by hand or from cron: `bash evals/nightly.sh` runs
  `harness eval --suite regression --threshold 1.0` under `timeout` with the suite's minutes plus 10, and
  `HARNESS_EVAL_MAX_USD` (default 20) caps the spend: a session case starts only while the spent budget plus its
  worst case (trials x sessions x `max_budget_usd`) stays within the cap, and a case left out fails the run. The
  regression suite's worst case is $18. A full run with sessions is the owner's or the main session's, never a role's.
- A job that wraps `harness eval` in `timeout` gives it at least the minutes its selection can run
  (`harness.evals.suite_minutes`); `uv run python evals/graders/pipeline_plan.py --check job-timeouts --root .
  <file>...` names a shorter one.
- A capability task that passes for three releases graduates to `regression/`.
- A case for a role type that is not in the default stage table names its `pipeline` and `stage` in `task.yaml`.

## The pipeline report
`uv run harness pipeline-report <run-dir> [--baseline FILE]` reads a pipeline run's record files (`critique.md`,
`verify.md`, `build-log*.md`) with the pipeline skill's report scripts and writes `evals/results/<stamp>/`:
`pipeline-report.json`, `pipeline-report.md` (findings per task by role and severity and their rounds, then the summary
and its ratios against the baseline) and `pipeline-report.summary.md` (the same in words). `evals/results/` is never
committed. The baseline is `--baseline FILE`, else `evals/baseline/pipeline/earlier-run.json`, the summary of an
earlier run of the owner's pipeline. `--as-baseline FILE --label TEXT` writes the run's summary as a baseline file
instead of a report. `--prefix NAME` adds each role's sessions, hand-overs, calls, context per call, start-up, wall
time and cost: it runs `claude agents` and reads the transcripts, so it is never passed in a role's session; without
it the usage part is `"available": false` with the reason.
```
- [ ] 10b. Write `evals/regression/README.md` exactly as below (48 lines, 4,644 bytes): the fourteen code cases (the
  ten of f70e84c, then the four of this task), the five model runs (without the access probe), and the two classes of
  2026-10-29 that have no case of their own (the grader regex, the stale case).
```markdown
# The regression cases

Every case here must pass. `uv run harness eval --suite regression --baseline --threshold 1.0` grades all of them
without a session on every push (`.github/workflows/ci.yml`); `bash evals/nightly.sh` runs the model runs on the
owner's machine. How a case runs and what its directory holds: [evals/README.md](../README.md).

## Graded by code (`session: false`)
Eight of the nine known error classes in the pipeline skill's `example/lessons.md`, numbered in its order (the seventh
is a model run below), two rules for a commit (its tests and its pages, ADR-0027) and four lesson classes of
2026-10-29. Each fixture holds the planted form and a near miss.
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
  transcript and a waiter command that differs from the brief's are found; the brief's own commands are not.

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
```
- [ ] 10c. Check both sizes and that every case directory is named in the case list:
```bash
(cd "${W:?}" && wc -c evals/README.md evals/regression/README.md && for d in evals/regression/*/; do grep -q "\`$(basename "$d")\`" evals/regression/README.md || echo "missing $d"; done)
```
Expected: `9912 evals/README.md`, `4644 evals/regression/README.md`, `14556 total` (wc pads the numbers); no `missing`
line. Both stay under 12,000 bytes.

### Step 11 — The gate on the tree, the task's test files and the ruff pair
- [ ] 11a. Run CI's gate as CI runs it, the four test files of this task in full, both ruff commands on the six Python
  files, and the timeout check on every file that runs `harness eval`:
```bash
B=/home/tite/Desktop/agent-system-run/manager-build-2026-10-29/scratch/builder-c
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run harness eval --suite regression --baseline --threshold 1.0 > "$B/t8-gate.json"; echo "exit $?"; python3 -I -c 'import json, sys; d = json.load(open(sys.argv[1])); print(d["ok"], d["pass_rate"], len(d["tasks"]))' "$B/t8-gate.json")
(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 600 uv run pytest -q -p no:cacheprovider packages/harness/tests/test_evals_suite.py packages/harness/tests/test_evals_llm.py packages/harness/tests/test_eval_session_free.py packages/harness/tests/test_pipeline_graders.py | tail -n 1)
(cd "${W:?}" && F="packages/harness/tests/test_evals_suite.py packages/harness/tests/test_evals_llm.py packages/harness/tests/test_eval_session_free.py packages/harness/tests/test_pipeline_graders.py packages/harness/src/harness/evals.py evals/graders/pipeline_plan.py" && timeout -k 10 120 uv run ruff check $F && timeout -k 10 120 uv run ruff format --check $F)
(cd "${W:?}" && timeout -k 10 120 uv run python evals/graders/pipeline_plan.py --check job-timeouts --root . .github/workflows/ci.yml .github/workflows/evals.yml evals/README.md evals/regression/README.md evals/nightly.sh justfile; echo "exit $?")
```
Expected: `exit 0`, `True 1.0 19` (14 code cases and 5 recorded model runs; 0.8 s on the planner's machine, and no
session: a baseline run never calls the llm grader, `evals.py:529` at f70e84c); `92 passed`; `All checks passed!`;
`6 files already formatted`; `exit 0` alone. The whole suite, `harness validate`, `docs-check` and `wiki-lint` are
the verifier's at the milestone (`lessons.md` 22:27 UTC), not this step's.

### Step 12 — The commit and the log line
- [ ] 12a. Write the commit message below with the Write tool to `${B}/t8-commit.txt`, then commit the task's paths:
```bash
B=/home/tite/Desktop/agent-system-run/manager-build-2026-10-29/scratch/builder-c
F=(packages/harness/src/harness/evals.py packages/harness/tests/test_evals_suite.py packages/harness/tests/test_evals_llm.py
  packages/harness/tests/test_eval_session_free.py packages/harness/tests/test_pipeline_graders.py
  evals/graders/pipeline_plan.py evals/regression evals/baseline evals/README.md evals/nightly.sh
  .github/workflows/ci.yml .github/workflows/evals.yml)
git -C "${W:?}" add -A -- "${F[@]}"
git -C "${W:?}" diff --cached --name-only "${BASE:?}" | wc -l
git -C "${W:?}" commit -q -F "$B/t8-commit.txt" -- "${F[@]}" &&
  git -C "${W:?}" diff --stat "${BASE:?}" HEAD | tail -n 1 | cut -d, -f1
```
Expected: `48` (34 files added or changed, 14 removed; nothing else), then ` 48 files changed`. `BASE` is the
commit Task 8 began on, where the build log's review range starts: `HEAD` before this commit when no hand-over
committed WIP, else the parent of the first WIP commit (lessons 23:45, B2 of build-log-c).
```text
feat(manager): Task 8 — a case per lesson class of 2026-10-29, the gate on every push, the nightly run

manager-build Task 8. Four code cases (pipeline-job-timeouts, pipeline-ancestor-deny, pipeline-handoff-pointers,
pipeline-waiters) with four checks in evals/graders/pipeline_plan.py; the critic's baseline in the spelling a session
wrote, so its grader is proved against a recorded output; harness eval stops before any trial when a case names a
stage or a file that is gone (stale_cases), and access-probe-critic, the stale case, is removed; the llm grader loads
only local settings and refuses a grade that is not in English (TD-011). CI runs the tests and the gate
(harness eval --suite regression --baseline --threshold 1.0) on every push, and no workflow starts a session;
evals/nightly.sh runs the session cases on the owner's machine under the suite's minutes and HARNESS_EVAL_MAX_USD.
```
- [ ] 12b. Append `Task 8: done — <sha7 of HEAD>` to `build-log-c.md` in the run folder, as your assignment says.

## Wiki, index and llms lines
None in this task: lane C writes no `wiki/` page (`lessons.md` 20:36 UTC), and `docs/llms.txt` names no `evals/` file
(grep at f70e84c). Task 11 writes the run's decision page and its lines (`## For Task 11`).

## For Task 11
- TD-011 is closed by this task's commit: `_llm_grade` passes `--setting-sources local` and refuses a grade whose
  dimensions hold a letter of one of the three blocks; `test_evals_llm.py` pins both.
- TD-002 stays open with Departure 6's reason (a judge's verdict has no code-graded form; a case needs a recorded judge
  output); Deferred 2 below names it, so it needs no new row. Deferred 1 and 3 below become tracker rows, each row
  holding the item's key verbatim, Task 6's K1 (task-06.md:52-56: the item's first line up to its first `: `, compared
  without backticks, whitespace collapsed, case-insensitive): `The access probe's port to the attack stage` and
  `The owner's cron line for evals/nightly.sh on this machine` (C508).
- `docs/quality/LEARNING.md:19` still says CI runs "the regression suite (threshold 0.9)": after this task CI runs the
  gate at 1.0 on every push, and the session cases run nightly on the owner's machine.
- `docs/decisions/0028-pipeline-evals.md` :17, :52, :70, :78 and :104 (the 0.9 threshold, the session job in CI, the
  access probe) are history: the run's decision page supersedes them, and its `## Record and source` names this task's
  commit, Departures 2-5 and the four cases.

## Deferred
1. The access probe's port to the `attack` stage: a new fixture and a baseline recorded by a live run (Departure 2);
   Task 11 adds the tracker row.
2. TD-002, a regression case for `judge`: it needs a recorded judge output (Departure 6).
3. The owner's cron line for `evals/nightly.sh` on this machine: the owner's to add (the summary names it); until then
   the script runs by hand. Task 11 adds the tracker row.

## Verified
- f70e84c's tree for this task's paths: `git diff --stat f70e84c HEAD -- evals packages .github justfile pyproject.toml
  uv.lock` is empty at 67f096c (part 1); every `Expected:` above was measured on `git archive f70e84c | tar -x` with
  its own `uv sync`, ruff 0.16.10 (`uv run ruff --version`), git 2.43.0.
- The red and green figures, by step: Step 1 `17 failed, 3 passed`; Step 2 `18 failed`; Step 3 `7 failed, 39 passed`
  (names as listed); Step 5 `2 passed, 18 deselected`; Step 6 `48 passed, 5 deselected`; Step 7 `8 failed, 31 passed`
  and four cases at 0.0; Step 8 `39 passed`, `3 passed, 12 deselected`, four cases at 1.0; Step 9
  `2 passed, 18 deselected`; Step 11 `True 1.0 19` in 0.80 s and `92 passed`.
- The pins patch applies to f70e84c's two files (`git apply --check`, then `cmp` with the scratch files: same).
- Wrong versions run red once: 33 of `evals.py` (the block range 4, `not_in_english` 4, the llm argv 5, the lint 7,
  the minutes 4, the budget 2, the cap 2, `run_suite` 5) and 34 of the four checks (`job-timeouts` 10, `ancestor-deny`
  8, `handoff-notes` 3, `waiters` 13 of 14 after C507), each graded with `pipeline_plan.py <fresh copy of fixture/>`.
- C507 (critique.md:1237), on planner-b's scratch grader with the patterns (`scratch/plan-fixer-b/c507/versions.py`):
  the case passes on a fresh copy of the new fixture with the 9 findings of `expect.json`, worked out by hand first.
  Red: the verbatim check of 6864162 (15 unexpected), the placeholders replaced before `re.escape` (15 unexpected), a
  greedy `<.*>` (5, 16, 17 and 18 missing), no `re.escape` (18 missing), `re.match` for `re.search` (6 unexpected),
  and planner-b's nine where they apply, three re-anchored on the new lines (brief or command not collapsed, equality
  as `fullmatch`: 6 unexpected each). Planner-b's `content is None` for the list test stays green, as it was on the
  fixture of 6864162: the dict test skips a string's characters, and only a number as `content` tells the two apart.
  Python 3.12.3: `re.sub("<x>", r"\S+", "<x>")` raises `re.error: bad escape \S at position 0`; `re.escape` escapes
  a space and `-`, not `<` or `>`. Briefs give placeholders: f70e84c `example/verifier-assignment.md:11`.
- The grader regex guard: the critic's grader narrowed to `sample\\.txt:9` gives `"ok": false`, `0.0` on the recorded
  line 1, and the shipped pattern gives 1.0.
- The whole harness suite on the scratch tree after Step 11: `1037 passed, 1 skipped, 1 deselected` (deselected:
  `test_access.py::test_a_role_session_may_not_run_what_the_local_settings_run_outside_the_sandbox`, the sandbox's
  /dev/null devices, `lessons.md` 22:50 UTC); it found `test_pipeline_graders.py`'s ten-case pin, now Step 3's.
  `uv run harness docs-check` and `uv run harness validate`: `"ok": true`, no problems.
- `claude --help`: `--setting-sources <sources>  Comma-separated list of setting sources to load (user, project, local).`
- `timeout --help` (GNU coreutils): `-k, --kill-after=DURATION`, `-s, --signal=SIGNAL`, `--preserve-status`,
  `--foreground`, `-v, --verbose`; "DURATION is a floating point number with an optional suffix"; "A duration of 0
  disables the associated timeout."
- GitHub's workflow syntax page, filter pattern cheat sheet
  (https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions): `'**'` "Matches all branch
  and tag names"; "If you start a pattern with `*`, `[`, or `!`, you must enclose the pattern in quotes."
- `evals.py` at f70e84c: `load_cases` globs `*/task.yaml` (:63), so `evals/regression/README.md` is no case; graders
  run as `[sys.executable, <script>, …]` (:399); `llm = not baseline and …` (:529). `.gitignore:27` ignores
  `evals/results/`. By `ast`: `run_suite` 39, `_llm_grade` 41, `grade` 61, `run_session` 104; `pipeline_plan.py`'s
  longest function `control_files` 25.
- The suite's minutes and worst case with the reference functions: regression 115 min and $18.00 over five session
  cases (cache-share-reader 30/$4, pipeline-critic-unproven-finding 15/$3, pipeline-handoff-carries-facts 10/$2,
  pipeline-verifier-planted-defect 15/$3, reader-quotes-locations 45/$6); capability 45 min and $6.00.
- Different cases may run back to back (the loop in Steps 7c and 8b, measured); one case run twice in one second fails
  with `FileExistsError` on `evals/results/<stamp>/<case>/trial-1/workspace` (measured again in this session).
- git 2.43.0 (`git --version`) in a scratch repo (`scratch/plan-fixer-b/gitprobe`: a base commit, a WIP commit with an
  add and a delete, two more staged paths): `git diff --cached --name-only <base> | wc -l` -> `4`, without `<base>`
  `2`; `git diff --stat <base> HEAD | tail -n 1` -> ` 4 files changed`, `git show --stat HEAD` ` 2 files changed`
  (Step 12a, B2 of build-log-c).
- Task 6's K1 as built (22eca3d, `collect_run.py`): `items()` drops the `N. ` marker (:107), `key()` keeps the first
  line up to its first `: ` (:116-119), and `norm()` (:122-124) drops backticks, collapses whitespace and lowers the
  case of the key and of each `| TD-NNN |` row (:491, :495). Run over this file with the built functions
  (`scratch/plan-fixer-b/c508/keys.py`), `## Deferred` gives three keys:
  `the access probe's port to the attack stage`, `td-002, a regression case for judge` (TD-002) and
  `the owner's cron line for evals/nightly.sh on this machine`. The re-arming lines are carried: Task 3's
  `monitor_records.py:410` at 73b2b0a prints `expired after <h> h: re-arm with the same command` (C508).
