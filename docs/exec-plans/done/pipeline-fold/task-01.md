# Task 1 — The run score, `score_run.py`

builder: a
depends_on: —
milestone: M1

## Goal
One line and one table per run folder, from the records and the transcripts the skill already parses, so every later
change of the pipeline is compared with the same numbers. Its first run on `manager-build-2026-10-29` is the baseline.

**Files:**
- Create: `.claude/skills/running-specagent-pipelines/scripts/manager/score_run.py`
- Create: `.claude/skills/running-specagent-pipelines/scripts/tests/test_score_run.py`
- Create: `.claude/skills/running-specagent-pipelines/scripts/docs/score_run.md`
- Modify: `.claude/skills/running-specagent-pipelines/scripts/README.md` (one index line under the manager scripts)

**Interfaces:**
- Consumes: `findings_report.report(run) -> dict` (`tasks`: task -> counts by kind C, A, R, V and `open`);
  `check_formats.ids(run)`, `check_formats.sections(text)`, `check_formats.REQUEST`, `check_formats.REPLY`;
  `usage_report.agent_rows(prefix)`, `usage_report.transcripts(sid)`, `usage_report.calls(path, seen)`,
  `usage_report.context(u)`, `usage_report.PRICE`, `usage_report.family(model)`;
  `measure_manager` (`scripts/manager/`): its `checklist` counting of findings per `Checklist:` item.
- Produces: `score(run: pathlib.Path, prefix: str, since: str | None) -> dict` with the keys `run`, `tasks`
  (task -> `{"C","A","R","V","V_plan","missed","B","cost"}`), `roles` (role -> `{"sessions","cap","idle",
  "first_call","cache_ratio","cost"}`), `requests` (list of `{"kind","file","line","minutes"}`; `minutes` is `None`
  when either line carries no `YYYY-MM-DD HH:MM UTC` time), `repeated` (checklist item -> findings), `cost`,
  `line` (the one-line summary); `main(argv) -> int`; the command
  `python3 -I scripts/manager/score_run.py <run-dir> [--prefix <name>/] [--since YYYY-MM-DD] [--json]`.

## Rules the script applies (documented on its page, applied alike to every run)
- A session belongs to the tasks whose numbers appear in `Task N:` at the start of a line inside the text of its
  tool calls that name a record file of the run (`critique.md`, `critique-response.md`, `verify.md`, `plan-log.md`,
  `fixer-log.md`, `build-log*.md`); a session with two tasks splits its cost equally; with none, its cost goes to the
  row `none`.
- A session is `idle` when none of its tool calls names a record file of the run or contains `git commit`, and it
  did not pass the cap: it only read and wrote its hand-off note.
- `cap` counts the lines `cap <agent>` of `_watch.log`; `sessions` the rows of `claude agents --json --all` under
  the prefix; `first_call` is the context of each session's first call (its median per role);
  `cache_ratio` is cache-read tokens over all context tokens of the role's calls.
- `missed` is a V finding with the `(plan)` cause on a task that has a `## Task N` section in `critique.md`.
- `cost` uses `usage_report.PRICE` on the calls' usage, like `usage_report.py`'s `$ equiv` column.

- [ ] **Step 1: Write the failing tests**

In `scripts/tests/test_score_run.py`, a fixture `run(tmp_path)` writes a run folder with `critique.md`
(`## Task 1` with `#### C1 — x` and `#### A1 — y`; `## Task 2 (diff)` with `#### R1 — (code) z`), `critique-response.md`
(`C1: applied`, `A1: added`), `verify.md` (`## Task 1`, `#### V1 — (plan) major, w` with `Checklist: lessons.md:12`;
`## Task 2`, `#### V2 — (code) minor, u`), `build-log-a.md` (`Task 1: done — abc1234`, `R1: fixed — def5678`,
`B1: sent to planner`), `_watch.log` (`19:01 fresh t/planner after note: HANDOFF planner after Task 1 — x | s aaaaaaaa`,
`19:40 cap t/planner 201,000 tokens; ordered to hand over | ...`), and `lessons.md` (a numbered item 12). A fake
`claude agents --json --all` (a stub on PATH, as `test_usage_report.py` does) lists two sessions `t/planner` and
`t/builder-a`; two transcripts under a fake HOME: the planner's has one call of 30,000 context tokens
(`cache_read_input_tokens` 27,000) and a Bash tool call whose command appends `Task 1: written — abc1234` to
`plan-log.md`; the builder's has two calls and a tool call `printf 'Task 1: done — abc1234\n' >> build-log-a.md`.

```python
def test_findings_per_task_count_each_kind_once_and_mark_the_missed_plan_finding(run):
    d = score_run.score(run, "t/", None)
    assert d["tasks"]["1"] == {"C": 1, "A": 1, "R": 0, "V": 1, "V_plan": 1, "missed": 1, "B": 1, "cost": d["tasks"]["1"]["cost"]}
    assert d["tasks"]["2"]["R"] == 1 and d["tasks"]["2"]["V"] == 1 and d["tasks"]["2"]["missed"] == 0

def test_roles_count_sessions_caps_idle_first_call_and_cache_ratio(run):
    d = score_run.score(run, "t/", None)
    assert d["roles"]["planner"]["sessions"] == 1 and d["roles"]["planner"]["cap"] == 1
    assert d["roles"]["planner"]["idle"] == 0 and d["roles"]["planner"]["first_call"] == 30000
    assert d["roles"]["planner"]["cache_ratio"] == 0.9

def test_an_idle_session_wrote_no_record_line_and_no_commit(run, idle_transcript):
    d = score_run.score(run, "t/", None)
    assert d["roles"]["critic"]["idle"] == 1

def test_cost_is_attributed_by_the_task_lines_a_session_wrote_and_split_between_two(run, two_task_transcript):
    d = score_run.score(run, "t/", None)
    assert abs(d["tasks"]["1"]["cost"] + d["tasks"]["2"]["cost"] + d["tasks"]["none"]["cost"] - d["cost"]) < 1e-9

def test_request_minutes_need_a_time_on_both_lines(run):
    d = score_run.score(run, "t/", None)
    kinds = {(r["kind"], r["minutes"]) for r in d["requests"]}
    assert ("CHECKOUT-REQUEST", 4) in kinds and ("COPY-REQUEST", None) in kinds

def test_missing_sources_give_n_a_cells_not_an_exception(tmp_path):
    (tmp_path / "critique.md").write_text("STATUS: reviewing\n")
    d = score_run.score(tmp_path, "t/", None)
    assert d["roles"] == {} and d["requests"] == [] and "n/a" in d["line"]

def test_the_line_names_the_run_and_the_totals(run):
    assert score_run.score(run, "t/", None)["line"].startswith("score run: tasks 2, findings C 1 A 1 R 1 V 2 (plan 1, missed 1), sessions 2 (cap 1, idle 0)")

def test_main_prints_the_line_then_the_table_and_json_on_request(run, capsys):
    assert score_run.main([str(run), "--prefix", "t/"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("score ") and "| task | C | A | R | V |" in out
    assert score_run.main([str(run), "--prefix", "t/", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["run"]
```

The `run` fixture writes `verify.md` with `CHECKOUT-REQUEST: abc1234 — 2026-10-30 03:35 UTC` and
`CHECKED-OUT: abc1234 — ... — 2026-10-30 03:39 UTC`, and `build-log-a.md` with `COPY-REQUEST: a -> b` and
`COPIED: a -> b` without times.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_score_run.py`
Expected: FAIL, `ModuleNotFoundError: No module named 'score_run'` (the tests import it as `test_measure_manager.py`
imports `measure_manager`).

- [ ] **Step 3: Implement `score_run.py`**

Functions, each pure over its inputs: `task_counts(run) -> dict`, `role_stats(run, prefix, since) -> dict`
(reads `_watch.log`, the agent rows and the transcripts), `attribute(sessions) -> dict` (the cost rule),
`request_minutes(run) -> list`, `repeated(run) -> dict`, `summary_line(d) -> str`, `table(d) -> str`, `score`, `main`.
The transcript tool calls come from the `tool_use` blocks of `message.content` (name `Bash`: `input.command`; `Edit`
and `Write`: `input.file_path`). `since` filters the agent rows as `usage_report.started` does. A missing source
leaves its cells `n/a` and the summary says `(n/a: _watch.log)` for each.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_score_run.py`
Expected: `8 passed`.

- [ ] **Step 5: Page and README line**

`scripts/docs/score_run.md`: usage, the five rules above, the columns of the table, one example line. `scripts/README.md`
gains `- [`manager/score_run.py`](docs/score_run.md): one score per run: findings, sessions, cost, requests` next
to the other manager scripts; `test_docs.py` checks the pair.

Run: `python3 -m pytest -q tests` (in `scripts/`) and `uv run pytest -q` (repository root)
Expected: all passed; `uv run ruff check .` and `uv run ruff format --check .` clean.

- [ ] **Step 6: The baseline**

Run: `python3 -I scripts/manager/score_run.py /home/tite/Desktop/agent-system-run/manager-build-2026-10-29 --prefix manager/`
Expected: one `score manager-build-2026-10-29: tasks 11, ...` line and the table; `--json` saved beside the vault's
measurement page of the run (`context/measurements/2026-10-29-manager-build.md` quotes the line). The per-task
findings must match the hand-counted ones (plan 3,4,5,4,4,2,4,4,3,1,1; diff 0,1,0,2,1,3,0,0,0,1,0; V 9): a
difference is a bug in the script, not in the hand count, until proven otherwise.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/running-specagent-pipelines/scripts/manager/score_run.py .claude/skills/running-specagent-pipelines/scripts/tests/test_score_run.py .claude/skills/running-specagent-pipelines/scripts/docs/score_run.md .claude/skills/running-specagent-pipelines/scripts/README.md
git commit -m "feat(skill): score_run.py — one score per run: findings, sessions, idle restarts, cost, requests"
```

## Deferred
- Attribution of a session's cost by token share per task (needs per-call task marks); the equal split is enough for
  one-task sessions, which are the rule.
