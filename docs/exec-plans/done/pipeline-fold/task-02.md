# Task 2 — The watcher launches only when work waits

builder: a
depends_on: 1
milestone: M1

## Goal
A hand-off note starts a fresh session only when the role has a unit to take. The role's own waiter, run once, is the
test: exit 0 means work waits, exit 3 means nothing waits, and any other exit is a broken check, which launches (C5).
A note that answers the watcher's own hand-over order launches as today: that hand-over is in the middle of a unit
(C4). Otherwise the watcher logs `idle` once and re-runs the check every round, launching the moment the check passes
(Review Focus 1).

**Files:**
- Modify: `scripts/watch_agents.py` (`handoff_note`, `decide`, `launched`, `entry`, `restore`, `RUN_STATE`,
  `AGENT_TYPES`, the docstring's hand-over rule)
- Modify: `scripts/wait_for_task.py`, `scripts/wait_for_ready.py`, `scripts/wait_for_log.py` (`--once`; the `--log`
  form of `wait_for_task.py`)
- Create: `scripts/open_ids.py`
- Modify: `scripts/tests/test_watch_agents.py`
- Create: `scripts/tests/test_open_ids.py` (Step 1's tests of `open_ids.py` and of the waiters' `--once`, with its
  helpers `run_script`, `write` and `listed`, all given in full in Step 1; `test_check_formats.py`'s `run` is an empty
  folder, `test_check_formats.py:22-26`, so Task 2 leaves that file alone)
- Modify: `scripts/docs/watch_agents.md`, `scripts/docs/wait_for_task.md`, `scripts/docs/wait_for_ready.md`,
  `scripts/docs/wait_for_log.md`, `scripts/README.md` (the agent field row and the new script's line)
- Modify: `example/agents.json` (a `work_check` for the critic and the plan fixer), `example/README.md` (the
  placeholders it uses)
- Create: `scripts/docs/open_ids.md`
- Create (repository): `wiki/decisions/no-fresh-session-after-a-finished-hand-off.md`,
  `wiki/decisions/no-fresh-session-after-a-finished-hand-off.summary.md`
- Modify (repository): `wiki/index.md` (one line at the end of `## Decisions`), `wiki/log.md` (one section at the end)

All paths under `.claude/skills/running-specagent-pipelines/` except the (repository) ones.

**Interfaces:**
- Consumes: `Watcher.handoff_note(name, row, role, events)`, `Watcher.decide(name, row, events, budget)` (True ends
  the agent's acts of the round: `unit_end` and `send_due` do not run, `watch_agents.py:719-721`),
  `Watcher.launch_fresh(...)`, `Watcher.launched(name, output, fresh)` (a fresh launch clears `pending`, `:1003`),
  `Watcher.tell(name, text)`, `Watcher.fill(text, **values)` (fills `{run}` and every key given, `:541-544`),
  `Watcher.entry(name)` and `Watcher.restore()` (the registry's per-role object, `:1111-1142`, `:1165-1189`),
  `RUN_STATE` (`:235-250`), `STRINGS` (`:269`), `check_types` (`:314-318`: each type is a `(kind, test)` pair);
  `check_formats.ids(run)` (`:149-215`), `check_formats.CAUSE` (`:60`), `check_formats.read` (`:79-80`).
- Produces: the optional agent field `work_check` (a list of strings, argv; `{run}` and `{skill}` filled: the run
  folder and the watcher's own folder, `os.path.dirname(os.path.abspath(__file__))`); the registry's per-role field
  `idle` (the first line of the note the role is idle on, else null); the waiters' flag `--once` (one check, no
  polling, the polling form's message; exit 0 when the condition holds now, 3 when not: 2 stays argparse's usage
  error and the interpreter's missing script, 1 an uncaught exception, C5); `scripts/open_ids.py <run-dir> [--kind
  C,A,B,V,R] [--cause plan] [--parity odd|even] [--task N]` printing one id per line, in the order of `--kind` and
  each kind's ids in reading order, and exiting 0 when any is open, 3 when none; `open_ids(run, kinds, parity=None,
  task=None, cause=None) -> list[str]`; `wait_for_task.py --log <plan-log> --critique <critique> --response
  <response> [--once]` (the lanes' form of the critic's wait, C7): work when (a) a `Task N: written` line of the log
  names a task that is neither at most line 1's N (`STATUS: reviewed|caught up through Task N`, as
  `wait_for_ready.py:32` reads it; `STATUS: done` covers every task) nor listed on line 2 (`Reviewed: <list>`), or
  (b) the response's line 1 is `STATUS: plan complete` or `STATUS: done`, every `#### C<n>` and `#### A<n>` of the
  critique has a `<id>:` line in the response and the critique's line 1 is not `STATUS: done` (the summary is due,
  `example/critic-assignment.md:34-37`); the log lines `idle <agent>: nothing to take (<last line>)`, `fresh <agent>
  after idle: work waits`, `work_check failed (exit <n>): <last line>` and `work_check failed to run: <error>`, where
  `<last line>` is the last non-empty line of the check's stdout followed by its stderr (the launch line keeps its
  present form `fresh <agent> after note: ...`).

## The rule
In `handoff_note`, after `note_from` is true and before `launch_fresh`:
1. A note that answers the watcher's own hand-over order (`name in self.pending`: the cap or unit-end order, a
   hand-over in the middle of a unit, `example/handoff-rule.md:20-21`) launches as today, without the check (C4).
2. Else, when the agent has a `work_check`, run it: `subprocess.run` of the list with each item through
   `self.fill(item, skill=<the watcher's folder>)`, `capture_output=True`, `text=True`, `timeout=60`, `cwd` the run
   folder. Exit 0 launches as today. Exit 3 logs `idle <agent>: nothing to take (<last line>)` once per note, records
   the note's first line in `self.idle[name]` and returns True, so the round's other acts for the agent (`revive`, a
   nudge, `waiting`'s timeout launch) do not run (C4). Any other exit, an `OSError` or the timeout `tell`s
   `work_check failed (exit <n>): <last line>` or `work_check failed to run: <error>` and launches as exit 0 does, so
   a broken check never silences a role (C5).
3. In `decide`, right after the `handoff_note`/`milestone` line (`watch_agents.py:768`), a name in `self.idle` has the
   re-check as its whole turn and `decide` returns True: exit 0 (or a failed check, as in 2) drops the name and
   launches with the why `fresh <agent> after idle: work waits`; exit 3 does nothing and logs nothing (no `revive`, no
   nudge, no `waiting`). A newer note goes through 1-2 first, since `handoff_note` runs before this line.
4. A fresh launch drops `self.idle[name]` in `launched`, beside `self.pending` (`:1003`). `"idle"` joins `RUN_STATE`,
   so a config reload keeps it (the reload replaces every other attribute, `:594-597`). The registry's per-role
   object gains `"idle": self.idle.get(name)` (`entry`); `restore` sets `self.idle[name]` and `self.seen[name]` from a
   string `idle`, so a restarted watcher re-checks the role instead of taking its note as new.

- [ ] **Step 1: Write the failing tests for the waiters' `--once` and for `open_ids.py`**

`scripts/tests/test_open_ids.py`, in full:

```python
"""Tests of open_ids.py and of the waiters' --once on synthetic run folders (Task 2 of the pipeline-fold run)."""

import pathlib
import subprocess
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]


def run_script(name: str, *args: str) -> subprocess.CompletedProcess:
    """One run of a script of the skill, as a work_check runs it; a waiter that polls instead fails at 30 s."""
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPTS / name), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def write(folder: pathlib.Path, name: str, text: str) -> str:
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def listed(run: pathlib.Path, *args: str) -> tuple[int, list[str]]:
    r = run_script("open_ids.py", str(run), *args)
    return r.returncode, r.stdout.split()


def test_once_exits_0_when_the_condition_holds_and_3_when_not(tmp_path):
    log = write(tmp_path, "build-log.md", "STATUS: x\nTask 1: done — abc1234\n")
    assert run_script("wait_for_log.py", log, "1", "--once").returncode == 0
    assert run_script("wait_for_log.py", log, "2", "--once").returncode == 3
    plan = write(tmp_path, "plan.md", "### Task 1\n### Task 2\n")  # Task 1 is complete once Task 2's heading exists
    response = write(tmp_path, "critique-response.md", "STATUS: writing Task 3\nC1: applied — x\n")
    assert run_script("wait_for_task.py", "--plan", plan, "--response", response, "0", "--once").returncode == 0
    assert run_script("wait_for_task.py", "--plan", plan, "--response", response, "1", "--once").returncode == 3
    critique = write(tmp_path, "critique.md", "STATUS: reviewed through Task 1\n## Task 1\n#### C1 — x\n")
    for task, code in (("1", 0), ("2", 3)):  # Task 2 is past line 1's N
        ready = run_script("wait_for_ready.py", "--critique", critique, "--response", response, task, "--once")
        assert ready.returncode == code
    answers = ("wait_for_task.py", "--critique", critique, "--response", response, "--answers", "--once")
    assert run_script(*answers).returncode == 0
    write(tmp_path, "critique.md", "STATUS: reviewed through Task 1\n## Task 1\n#### C1 — x\n#### A1 — y\n")
    assert run_script(*answers).returncode == 3  # A1 has no answer line


def test_the_critics_check_reads_the_lanes_a_cut_round_and_the_summary(tmp_path):  # C7, A6
    lines = "STATUS: x\nTask 1: written — a1\nTask 3: written — c3\nTask 2: written — b2\n"  # the lanes' order
    log = write(tmp_path, "plan-log.md", lines)
    critique, response = str(tmp_path / "critique.md"), str(tmp_path / "critique-response.md")
    check = ("wait_for_task.py", "--log", log, "--critique", critique, "--response", response, "--once")
    sections = "## Task 1\n#### C1 — x\n## Task 2\n## Task 3\n"  # Task 2's round was cut by a cap order
    write(tmp_path, "critique.md", "STATUS: reviewed through Task 1\nReviewed: 3\n" + sections)
    write(tmp_path, "critique-response.md", "STATUS: writing Task 4\n")
    assert run_script(*check).returncode == 0  # Task 2 is written, past line 1's N and not on line 2
    write(tmp_path, "critique.md", "STATUS: reviewed through Task 3\nReviewed: \n" + sections)
    assert run_script(*check).returncode == 3
    write(tmp_path, "critique-response.md", "STATUS: plan complete\n")
    assert run_script(*check).returncode == 3  # C1 has no answer line yet
    write(tmp_path, "critique-response.md", "STATUS: plan complete\nC1: applied — y\n")
    assert run_script(*check).returncode == 0  # the summary is due
    write(tmp_path, "critique.md", "STATUS: done\n" + sections)
    assert run_script(*check).returncode == 3


def test_open_ids_by_kind_parity_and_task(tmp_path):  # C8, C9, A7
    run = tmp_path / "run"
    run.mkdir()
    critique = "## Index\n#### C1 — a\n## Task 1\n#### C2 — b\n## Task 2\n#### C3 — c\n#### C4 — d\n"
    write(run, "critique.md", "STATUS: reviewed through Task 2\n" + critique + "## Task 2 (diff)\n#### R1 — (plan) e\n")
    write(run, "critique-response.md", "STATUS: writing Task 3\nC4: applied — x\n")
    write(run, "build-log.md", "STATUS: building Task 3\nB1: sent to plan-fixer — z\n")
    assert listed(run, "--kind", "C,R", "--parity", "even") == (0, ["C1", "C3", "R1"])  # C1 is shared: every parity
    assert listed(run, "--kind", "C,R", "--parity", "odd") == (0, ["C1", "C2"])
    assert listed(run, "--kind", "R,C", "--task", "2") == (0, ["R1", "C3"])  # the order of --kind; no shared id
    assert listed(run, "--kind", "B", "--parity", "odd") == (0, ["B1"])  # a build log's B line is shared
    assert listed(run, "--kind", "B", "--task", "1") == (3, [])
    assert listed(run, "--kind", "A,V") == (3, [])


def test_open_ids_cause_plan_drops_the_code_findings(tmp_path):  # C6, A5
    run = tmp_path / "run"
    run.mkdir()
    verify = "STATUS: verifying Task 2\n## Task 2 — abc1234\n#### V1 — (code) major: x\n"
    write(run, "verify.md", verify)
    write(run, "critique.md", "STATUS: reviewed through Task 2\n## Task 2 (diff)\n#### R1 — (code) x\n")
    write(run, "critique-response.md", "STATUS: writing Task 3\n")
    assert listed(run, "--kind", "C,A,B,V,R", "--cause", "plan") == (3, [])
    write(run, "verify.md", verify + "#### V2 — (plan) major: y\n")
    assert listed(run, "--kind", "C,A,B,V,R", "--cause", "plan") == (0, ["V2"])
    assert listed(run, "--kind", "V,R") == (0, ["V1", "V2", "R1"])
```

- [ ] **Step 2: Run them to verify they fail**

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_open_ids.py)`
Expected: FAIL, 4 failed: `wait_for_log.py` ignores `--once` and polls (`subprocess.TimeoutExpired` after 30 s);
`--log` and `--once` are unrecognized arguments of `wait_for_task.py`, `--once` of `wait_for_ready.py` (exit 2);
`open_ids.py` does not exist (exit 2).

- [ ] **Step 3: Implement `--once` in the three waiters and `open_ids.py`**

`open_ids.py` imports `check_formats` from its own folder (as `watch_agents.py:115` does).
`open_ids(run, kinds, parity=None, task=None, cause=None) -> list[str]`: for each kind of `kinds` in that order, the
ids of `check_formats.ids(run)["open"]` of that kind in their reading order, kept by these rules. An id's task: the
four heading files of `ids()` (`critique.md`, `verify.md`, `judge.md`, `verify-kb.md`) are read line by line as
`wait_for_ready.py:37-42` reads the critique: a `##` or `###` heading whose text starts `Task <n>` opens task n
(`## Task 2 (diff)`, `## Task 2 — abc1234`), any other `##` or `###` heading opens a shared section, and a
`#### <id>` line takes the section it is in; an id with no heading (a build log's `B<n>` line) is shared; an id's
first heading wins (C9: `check_formats.sections()` yields the `####` sections only, `check_formats.py:139-146`).
`parity` keeps the ids of tasks of that parity and every shared id; `task` keeps task n's ids only, no shared one;
`cause="plan"` drops a V or R whose heading line names the cause `code` (`check_formats.CAUSE.search` on that line; C,
A and B have no cause and stay, C6). `main(argv) -> int`: argparse with `run_dir`, `--kind` (default `C,A,B,V,R`),
`--cause` (`choices=["plan"]`), `--parity` (`choices=["odd", "even"]`), `--task` (an int); prints one id per line and
returns 0 when it printed any, 3 when none (C5). The waiters: `--once` runs one `check()` (one `state(args.task)` in
`wait_for_ready.py`), prints its line and exits 0 when the condition holds, 3 when not. `wait_for_log.py` gains
`argparse` (`file`, `lines` as an int, `--once`; its positional form stays). `wait_for_task.py` gains `--log` and
`--once`; the `--log` form (Interfaces) reads the log's `^Task (\d+): written\b` lines, the critique's line 1 by the
regex of `wait_for_ready.py:32` (`STATUS: done` covers every task), its line 2's numbers when that line starts
`Reviewed:`, and for (b) the regexes of `--answers` (`wait_for_task.py:34-35`).

- [ ] **Step 4: Run them to verify they pass**

Run: the Step 2 command. Expected: 4 passed.

- [ ] **Step 5: Write the failing watcher tests**

In `test_watch_agents.py`, after its last test, with its `Pipeline` fixture `p`, `row`, `note`, `registry` and `SCRIPT`
(`test_watch_agents.py:73`, `:96`, `:222`, `:258`, `:20`), in full:

```python
NOTHING = [sys.executable, "-c", "raise SystemExit(3)"]  # a work_check that reports nothing to take
FLAG = "import os, sys; sys.exit(0 if os.path.exists(sys.argv[1]) else 3)"  # work waits once the file exists


def test_a_note_with_nothing_to_take_logs_idle_and_launches_nothing(p):
    p.config["agents"]["t/builder"]["work_check"] = NOTHING
    p.transcript()
    line = note(p)
    r = p.watch(rounds=2)
    assert r.stdout.count("idle t/builder: nothing to take") == 1 and p.launches() == [], r.stdout + r.stderr
    assert registry(p)["roles"]["t/builder"]["idle"] == line


def test_an_idle_role_is_launched_when_its_check_passes_later(p, tmp_path):
    flag = tmp_path / "flag"
    p.config["agents"]["t/builder"]["work_check"] = [sys.executable, "-c", FLAG, str(flag)]
    p.transcript()
    note(p)
    p.watch(rounds=1)
    assert p.launches() == []
    flag.write_text("")
    r = p.watch(rounds=1)  # a restarted watcher: the registry's `idle`, not the note, brings the role back
    assert "fresh t/builder after idle: work waits" in r.stdout and len(p.launches()) == 1, r.stdout + r.stderr


@pytest.mark.parametrize(
    "check, line",
    [
        (["/no/such/check"], "work_check failed to run"),
        ([sys.executable, "{skill}/open_ids.py", "{run}", "--no-such-flag"], "work_check failed (exit 2)"),
        ([sys.executable, "{skill}/no_such_script.py"], "work_check failed (exit 2)"),
    ],
)
def test_a_work_check_that_fails_or_cannot_run_launches(p, check, line):  # C5, A4
    p.config["agents"]["t/builder"]["work_check"] = check
    p.transcript()
    note(p)
    r = p.watch(rounds=1)
    assert len(p.launches()) == 1 and line in r.stdout, r.stdout + r.stderr


def test_work_check_fills_run_and_skill(p):  # A1: unfilled, the check finds no folder `{run}` and exits 1
    record = "import pathlib, sys; pathlib.Path(sys.argv[1], 'argv.txt').write_text(sys.argv[2])"
    p.config["agents"]["t/builder"]["work_check"] = [sys.executable, "-c", record, "{run}", "{skill}/watch_agents.py"]
    p.transcript()
    note(p)
    r = p.watch(rounds=1)
    assert "work_check failed" not in r.stdout and len(p.launches()) == 1, r.stdout + r.stderr
    assert pathlib.Path((p.run / "argv.txt").read_text()).samefile(SCRIPT)


def test_work_check_must_be_a_list_of_strings(p):  # C9
    p.config["agents"]["t/builder"]["work_check"] = "not a list"
    r = p.watch(rounds=1)
    assert r.returncode == 2 and "config error: t/builder: work_check is not a list of strings" in r.stdout


def test_an_idle_role_whose_session_stopped_is_not_revived(p):  # C4, A2
    p.config["agents"]["t/builder"]["work_check"] = NOTHING
    p.rounds([row(state="stopped", status=None, pid=None)])
    p.transcript()
    note(p)
    r = p.watch(rounds=2)
    assert p.launches() == [] and "continued t/builder" not in r.stdout, r.stdout + r.stderr
    assert r.stdout.count("idle t/builder") == 1


def test_a_note_after_a_hand_over_order_launches_without_the_work_check(p):  # C4, A3 (a)
    p.config["handoff_wait"] = 0
    p.config["agents"]["t/builder"]["work_check"] = NOTHING
    p.transcript(context=250_000)
    text = "HANDOFF builder after Task 3 — 2026-10-26 06:00\nState: in the middle of Step 4.\n"
    p.rounds([row()], {"rows": [row()], "write": {str(p.run / "handoff-builder.md"): text}})
    r = p.watch(rounds=2)
    assert "fresh t/builder after note" in r.stdout and "without a note (timeout)" not in r.stdout, r.stdout + r.stderr
    assert "idle t/builder" not in r.stdout and len(p.launches()) == 2  # the order's resume, then the fresh session


def test_an_idle_role_survives_a_config_reload(p, tmp_path):  # C4, A3 (b)
    flag = tmp_path / "flag"
    p.config["agents"]["t/builder"]["work_check"] = [sys.executable, "-c", FLAG, str(flag)]
    config = str(p.run / "_agents-v2.json")
    p.rounds(
        {"rows": [row()], "write": {config: json.dumps({**p.config, "nudges": 5})}},
        {"rows": [row()], "write": {str(flag): ""}},
        [row()],
    )
    p.transcript()
    note(p)
    r = p.watch(rounds=3)
    assert r.stdout.count("config reloaded: _agents-v2.json") == 1, r.stdout + r.stderr
    assert "fresh t/builder after idle: work waits" in r.stdout and len(p.launches()) == 1
```

- [ ] **Step 6: Run them to verify they fail**

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_watch_agents.py -k "idle or work_check")`
Expected: FAIL, 9 failed and 1 passed: today `work_check` is ignored and every note launches. The one that passes,
`test_a_note_after_a_hand_over_order_launches_without_the_work_check`, pins today's launch on an ordered hand-over,
which Step 7 must keep.

- [ ] **Step 7: Implement the rule in `watch_agents.py`**

`AGENT_TYPES["work_check"] = STRINGS` (`watch_agents.py:269`; `check_types` unpacks every entry as a `(kind, test)`
pair, `:314-318`, so a bare `list` there raises `TypeError` on every config load, C9); optional, not in
`AGENT_FIELDS`. `self.idle: dict[str, str] = {}` in `__init__` beside `self.seen` (`:506`); `"idle"` in `RUN_STATE`;
`launched`, `entry` and `restore` as in The rule, 4; The rule's 1-3 in `handoff_note` and `decide`, with one helper
that runs the check for both; the docstring's hand-over paragraph gains two sentences (the check and its exit codes;
the idle re-check).

- [ ] **Step 8: Run the task's own tests**

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_open_ids.py tests/test_watch_agents.py)`
Expected: 93 passed (Step 1's 4; `test_watch_agents.py`'s 79 at 4fbf4cf and Step 5's 10).
Checks once each (`_common.md`, "Checks once each"): the full suites (`uv run pytest -q`, which collects the skill's tests by
`pyproject.toml:25`, `just validate`, `uv run harness docs-check`, `uv run harness wiki-lint`) are the verifier's at
M1, not this task's; for this task this replaces the index's Global Constraints line on them (`00-index.md:28-29`).

- [ ] **Step 9: Configs and pages**

`example/agents.json`: a `work_check` for the two roles whose hand-overs can leave nothing to take. The critic:
`["python3", "{skill}/wait_for_task.py", "--log", "{run}/plan-log.md", "--critique", "{run}/critique.md",
"--response", "{run}/critique-response.md", "--once"]` (a written task not yet reviewed, or the summary due, C7). The
plan fixer: `["python3", "{skill}/open_ids.py", "{run}", "--kind", "C,A,B,V,R", "--cause", "plan"]` (the ids its
brief collects, no `(code)` V or R: `example/plan-fixer-assignment.md:17-20`, C6). The builders and the verifier get
none in the example: their hand-overs follow a unit by design. `example/README.md` names the placeholder `{skill}`
beside `{run}`. `scripts/README.md`: the row `work_check` in the agent fields table and the index line of
`open_ids.py`; `scripts/docs/watch_agents.md`: the rule under its hand-over section, with the exit codes (0 work
waits, 3 nothing to take, any other a failed check that launches) and the order's exception; the three waiter pages:
`--once` (exit 0 or 3) and the `--log` form; `scripts/docs/open_ids.md` (its flags and exit codes). `test_docs.py`
and `test_skill_example.py` stay green: the configs name only files the example has, and the briefs' waiter lines
are unchanged (`--once` is the config's, not a brief's).

The decision page (spec Decided 5, `docs/design-docs/pipeline-fold.md:117-124`; one decision per page, in the commit
with its code, `_common.md`, "Documentation with the code"): `wiki/decisions/no-fresh-session-after-a-finished-hand-off.md`,
titled "No fresh
session after a finished role's hand-off", front matter with the keys of `wiki/decisions/skill-script-pages.md:1-13`
(`type: decision`, `status: draft`, `decided: 2026-10-30`, `by: owner`, `decision_status: decided`, `scope: global`);
the decision: a hand-off note launches a fresh session only when the role's `work_check` passes, else the watcher logs
`idle` and re-checks every round (a note that answers the watcher's own hand-over order launches as before); `why` from the spec's Intent (`:8-25`); `would_change_if` from Measurement 3
(`:147-148`: the measurement run loses quality and this pair is unfolded); under 12,000 bytes. Its `.summary.md`: four
lines, the first `Decision (owner, 2026-10-30): ...`. `wiki/index.md`: one line at the end of `## Decisions`, in the
form of `wiki/index.md:35`. `wiki/log.md`: a section at the end in the form of `wiki/log.md:48-63`: `## 2026-10-30
pages written with Task 2 of the pipeline-fold run`, `- commit: Task 2 of the pipeline-fold run`, `- created:
decisions/no-fresh-session-after-a-finished-hand-off.md`, `- updated: index.md`. Both files are index-like: a task
appends its own lines at the end and never reorders another task's; Task 3 (lane b) appends to both in parallel and
the main session keeps both lanes' lines at the merge (the rule of the manager-build run, `lessons.md`, 22:45 UTC).

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_docs.py tests/test_skill_example.py)`; then at the repository
root `uv run ruff check .`; `uv run ruff format --check .`; `wc -c wiki/decisions/no-fresh-session-after-a-finished-hand-off*.md`;
`grep -c 'decisions/no-fresh-session-after-a-finished-hand-off.md' wiki/index.md wiki/log.md`
Expected: 20 passed (8 + 12, the counts at 4fbf4cf); ruff clean; each page under 12,000 bytes; `wiki/index.md:1`,
`wiki/log.md:1`.

- [ ] **Step 10: Commit**

```bash
git add .claude/skills/running-specagent-pipelines wiki/decisions/no-fresh-session-after-a-finished-hand-off.md \
  wiki/decisions/no-fresh-session-after-a-finished-hand-off.summary.md wiki/index.md wiki/log.md
git commit -m "feat(skill): the watcher launches a fresh session only when the role's work_check passes; waiters --once; open_ids.py"
```

## Verified (plan fixer, C4-C9, in lane a at 0bfdff3; these files are as at 4fbf4cf)
- `handoff_note` is True only when it launched; on False `decide` goes on to `waiting` and `revive`:
  `watch_agents.py:768-782`, `:789-799`; `round` skips `unit_end` and `send_due` when `decide` is True: `:719-721`.
- `waiting` launches `fresh <agent> without a note (timeout)` past `handoff_wait`: `:840-847`; the cap and unit-end
  orders set `pending`, a fresh launch clears it: `:832`, `:893`, `:1003`.
- A reload keeps `RUN_STATE` and `hashes` only: `:235-250`, `:594-597`; `self.seen` is set in `__init__`: `:506`.
- The registry keeps each role under `"roles"`: `:1155`, from `entry` (`:1111-1142`); `restore`: `:1165-1189`;
  the tests read `registry(p)["roles"]`: `test_watch_agents.py:795`.
- `check_types` unpacks `(kind, test)`: `:314-318`; `STRINGS`: `:269`; only the config's own keys are checked for
  unknown names: `:368-370`; a config error exits 2 and prints `config error: ...` on stdout:
  `test_watch_agents.py:712-716`.
- `fill` replaces `{run}` and every key given: `:541-544`; the script's folder is put on `sys.path`: `:115`.
- `python3 -I <missing script>` and an argparse error exit 2, `raise SystemExit(3)` exits 3 (run 2026-10-30); the
  waiters exit 1 after 8 hours: `wait_for_log.py:19`, `wait_for_task.py:50`, `wait_for_ready.py:57`.
- `wait_for_log.py` reads `sys.argv[1:3]` and polls: `wait_for_log.py:11-17`; `wait_for_task.py` requires
  `--response` (`:20`) and reads the answers at `:34-35`; `wait_for_ready.py` reads line 1 at `:32` and the task
  headings at `:37-42`.
- `check_formats.ids()` gives `open` by kind in reading order, a B id only when sent and not answered in
  `critique-response.md`: `check_formats.py:149-215`; `sections()` yields the `####` sections only: `:139-146`;
  `CAUSE`: `:60`.
- The critic's last unit is the summary: `example/critic-assignment.md:34-37`; the fixer collects no `(code)` id:
  `example/plan-fixer-assignment.md:17-20`; a hand-over on the order is mid-unit: `example/handoff-rule.md:20-21`;
  the plan log's line `Task N: written — <sha>`: `example/planner-assignment.md:39`.

## Deferred
- A `work_check` for the builders from the index's task order (needs the plan folder path in the config).
- An order (`--order`, a reload order) to an idle role waits until its check passes: `decide` is True for an idle
  name, so `send_due` does not run (`watch_agents.py:719-721`); an order as a unit line is a later change.
