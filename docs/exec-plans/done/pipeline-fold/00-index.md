# Plan: pipeline-fold — index

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fewer hand-overs in the SpecAgent pipeline, each change measured by one run score before and after.

**Architecture:** Seven tasks on the skill `.claude/skills/running-specagent-pipelines` and `harness plan-lint`: a run
score script (Task 1); a watcher that launches a fresh session only when work waits (Task 2); the plan file split into
steps and blocks (Task 3); the planner answering its own findings with the fixer launched on demand (Task 4); the critic
on the plan only and the verifier reading the code (Task 5); the measurement run that decides what is kept (Task 6); the manager-build judge's conditions, fixed before that run (Task 7).
Each task ends with the skill's suite, the harness suite and `ruff` green, and one commit.

**Tech Stack:** Python 3.12 standard library only (the skill's scripts run under `python3 -I`); pytest; `uv run
harness` for the harness; markdown briefs under `example/`.

**Spec:** `docs/design-docs/pipeline-fold.md` (status draft; the owner's decisions of 2026-10-30 are quoted there).

## Global Constraints

- English only in every file of the template; `uv run harness validate` refuses a letter of a refused block.
- No brief, config or script names a model; models sit in the settings files only (`test_skill_example.py`).
- The skill's scripts import only the standard library and each other; they are run as `python3 -I <script>`.
- A task file has at most 1,500 lines (`harness plan-lint`); an index or generated page at most 12,000 bytes.
- Every waiter a brief names is given in full, with a placeholder for each word the agent fills in.
- Old run folders (2026-10-26 to 2026-10-29) still parse: `check_formats.py`, `findings_report.py` and
  `usage_report.py` keep their outputs on them; new fields in `agents.json` are optional.
- Before a task's done line: the task's own test files by name, with the counts of its closing step, then
  `uv run ruff check .` and `uv run ruff format --check .`; the full suites (`uv run pytest -q`, `just validate`,
  `uv run harness docs-check`, `uv run harness wiki-lint`) are the verifier's at M1 and M2 (C1, 662e5c0).
- The owner's rules of the skill stay as written in `SKILL.md` ("Owner rules"); the sandbox and blindness rules change
  nowhere.
- Nothing is launched without the owner's yes; Task 6 asks once, in one message, before its run.

## Review Focus

1. A role hands over while its STATUS is not final and nothing waits for it, then a request line or a new task appears
   minutes later: the watcher must launch the fresh session then, not never (Task 2, `work_check` re-run each round).
2. A `task-NN.code.md` whose task file is missing, or a step naming `Block 3b` that no `## Block 3b` defines, or a block
   defined twice: each is one plan-lint problem, named with its file (Task 3).
3. The planner and an on-demand fixer answer the same id in the same minute: a reused `<id>:` line counts as answered
   once and the second answer is a `check_formats.py` error, not a silent overwrite (Task 4, append-only answers).
4. `score_run.py` on a run folder with no `build-log-*.md`, no `_watch.log` or no transcripts on this machine: every
   missing source is one `n/a` cell, never an exception (Task 1).
5. A session that wrote unit lines for two tasks: its cost is split by the documented rule, and the rule is the same
   for the baseline and the measured run (Task 1, `--json` shows the attribution).

## Task order

| Task | title | builder | depends_on | files | milestone |
| --- | --- | --- | --- | --- | --- |
| 1 | The run score, `score_run.py` | a | — | `scripts/manager/score_run.py`, `scripts/tests/test_score_run.py`, `scripts/docs/score_run.md`, `scripts/README.md` | M1 |
| 2 | The watcher launches only when work waits | a | 1 | `scripts/watch_agents.py`, `scripts/open_ids.py`, `scripts/wait_for_task.py`, `scripts/wait_for_ready.py`, `scripts/wait_for_log.py`, `scripts/tests/test_watch_agents.py`, `scripts/tests/test_open_ids.py`, `scripts/docs/watch_agents.md`, `scripts/docs/open_ids.md`, `scripts/docs/wait_for_task.md`, `scripts/docs/wait_for_ready.md`, `scripts/docs/wait_for_log.md`, `scripts/README.md`, `example/agents.json`, `example/README.md`, `wiki/decisions/no-fresh-session-after-a-finished-hand-off.md`, `wiki/decisions/no-fresh-session-after-a-finished-hand-off.summary.md`, `wiki/index.md` and `wiki/log.md` (index-like: own lines appended at the end; both lanes' lines kept at the merge) | M1 |
| 3 | The plan file split: steps and blocks | b | — | `packages/harness/src/harness/plans.py`, `packages/harness/tests/test_plan_lint.py`, `docs/exec-plans/active/README.md`, `example/planner-assignment.md`, `example/critic-assignment.md`, `example/builder-a-assignment.md`, `example/builder-b-assignment.md`, `example/verifier-assignment.md`, `example/common.md`, `wiki/decisions/plan-steps-and-blocks-in-two-files.md`, `wiki/decisions/plan-steps-and-blocks-in-two-files.summary.md`, `wiki/index.md` and `wiki/log.md` (index-like: own lines appended at the end; both lanes' lines kept at the merge) | M2 |
| 4 | The planner answers its findings; the fixer on demand | a | 2, 3 | `scripts/watch_agents.py`, `scripts/check_formats.py`, `scripts/tests/test_watch_agents.py`, `scripts/tests/test_check_formats.py`, `scripts/tests/test_skill_example.py`, `scripts/README.md`, `scripts/docs/watch_agents.md`, `scripts/docs/check_formats.md`, `SKILL.md`, `example/agents.json`, `example/README.md`, `example/planner-assignment.md`, `example/plan-fixer-assignment.md`, `example/common.md`, `example/launch.md`, `wiki/decisions/planner-answers-its-findings-fixer-on-demand.md`, `wiki/decisions/planner-answers-its-findings-fixer-on-demand.summary.md`, `wiki/index.md`, `wiki/log.md` | M2 |
| 5 | The critic on the plan, the verifier on the code | b | 3, 4 | `example/critic-assignment.md`, `example/verifier-assignment.md`, `example/plan-fixer-assignment.md`, `example/builder-a-assignment.md`, `example/builder-b-assignment.md`, `example/judge-assignment.md`, `example/handoff-rule.md`, `example/planner-assignment.md`, `example/common.md`, `example/README.md`, `SKILL.md`, `scripts/wait_for_log.py`, `scripts/docs/wait_for_log.md`, `scripts/tests/test_open_ids.py`, `scripts/tests/test_skill_md.py`, `scripts/tests/test_skill_example.py`, `README.md`, `wiki/decisions/critic-on-the-plan-verifier-on-the-code.md`, `wiki/decisions/critic-on-the-plan-verifier-on-the-code.summary.md`, `wiki/index.md`, `wiki/log.md` | M2 |
| 6 | The measurement: Task 10 rebuilt with the folded pipeline — cancelled (owner, 2026-10-30) | a | 1, 2, 3, 4, 5, 7 | a run folder outside the repository; `docs/design-docs/pipeline-fold.md` (status); Step 0 (V5, R4): `scripts/manager/score_run.py`, `scripts/tests/test_score_run.py`, `scripts/manager/README.md` | M3 |
| 7 | The judge's conditions on the manager: J4-J11 of the manager-build run | b | 4, 5 | the seven `example/*-settings.json`, `example/sim_bwrap.py`, `example/README.md`, `example/common.md`, `example/lessons.md`, `example/critic-assignment.md`, `example/verifier-assignment.md`, `scripts/manager/preflight.py`, `scripts/watch_agents.py`, `scripts/docs/watch_agents.md`, `SKILL.md`, `scripts/collect_run.py`, `scripts/docs/collect_run.md`, `scripts/check_formats.py`, `scripts/docs/check_formats.md`, `scripts/manager/surface.py`, `scripts/manager/README.md`, `scripts/README.md`, `references/preflight-and-capacity.md`, `references/sandbox-and-blindness.md`, `references/measuring.md`, `references/choosing-roles-and-skills.md`, their tests and `scripts/tests/test_skill_md.py`, `scripts/tests/test_skill_example.py`, `docs/exec-plans/done/manager-build/task-11.md` | M2 |

## Milestones

| Milestone | after | checks |
| --- | --- | --- |
| M1 | Tasks 1, 2 | the verifier's full suites (`uv run pytest -q`, which collects the skill's tests, `just validate`, `uv run harness docs-check`, `uv run harness wiki-lint`; `_verifier-assignment.md:23-27`) green; the baseline line of `score_run.py` on `manager-build-2026-10-29` recorded in the owner's vault |
| M2 | Tasks 3, 4, 5, 7 | both suites, ruff, docs-check, `harness validate`, `harness plan-lint` green on `main` |
| M3 | Task 6 | cancelled with Task 6; the comparison table is not written |

## Coverage of the design

| Design section | Task |
| --- | --- |
| Decided 1, one score per run | 1 |
| Decided 5, no fresh session after a finished role's hand-off | 2 |
| Decided 4, the plan file split | 3 |
| Decided 2, the planner answers; the fixer on demand | 4 |
| Decided 3, the critic on the plan only; one critic by default | 5 |
| Decided 6, a role loads what its brief names | D10, not this plan (prerequisite; the briefs keep their `Spec:` and `Skills:` lines) |
| Measurement 1-4 | 1 (baseline), 6 (the run, the comparison, the plain-session baseline) |
| The manager-build judge's conditions (J4-J11; 2026-10-30, `judge.md` of that run) | 7 |
