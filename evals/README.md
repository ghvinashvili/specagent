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
2. trusts that project by hand, as the permissions page describes for `-p` runs: `projects["<absolute path>"].hasTrustDialogAccepted = true` in `.claude.json` (under `CLAUDE_CONFIG_DIR` when it is set, otherwise `~/.claude.json`). Without trust a `-p` run in the copy would execute its hooks but ignore `permissions.allow`, `additionalDirectories` and `extraKnownMarketplaces` from `.claude/settings.json`, so the trial would not run the repository's configuration. The internal marketplace is a `directory` source at `./plugins`, copied with the project, and `code-intel` is listed there by a relative path, so it loads from the copy once the trusted settings apply, without a network fetch (`pyright-lsp@claude-plugins-official` is code intelligence with no part in harness behaviour; if it is not installed in the trial's config directory it is reported as not installed);
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
