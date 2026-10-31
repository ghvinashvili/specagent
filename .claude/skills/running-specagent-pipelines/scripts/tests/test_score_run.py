"""score_run.py (pipeline-fold Task 1): one line and one table per run folder: findings per task by kind with the
`(plan)` V ids the critic missed, sessions, cap hand-overs and idle restarts per role, cost attributed to tasks by
the `Task N:` lines a session wrote, request lines with their minutes, and the lesson classes repeated.

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_score_run.py
"""

import datetime
import json
import os
import re
import sys

import pytest
from transcript_home import SCRIPTS, TEXT, Home, bash, read, tool, write

sys.path.insert(0, str(SCRIPTS / "manager"))
import score_run

PLANNER = "11111111-2222-3333-4444-555555555555"
BUILDER = "66666666-7777-8888-9999-000000000000"
CRITIC = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
VERIFIER = "ffffffff-0000-1111-2222-333333333333"

CRITIQUE = (
    "STATUS: reviewed through Task 2\n\n## Task 1\n#### C1 — x\nChecklist: lessons.md:12\n#### A1 — y\n\n"
    "## Task 2 (diff)\n#### R1 — (code) z\n"
)
RESPONSE = "STATUS: plan complete\nC1: applied — a\nA1: added to Task 1 — t\n"
VERIFY = (
    "STATUS: verified through Task 2\n\n## Task 1 — abc1234\nCHECKOUT-REQUEST: abc1234 — 2026-10-30 03:35 UTC\n"
    "CHECKED-OUT: abc1234 — detached — 2026-10-30 03:39 UTC\n#### V1 — (plan) major, w\nChecklist: lessons.md:12\n\n"
    "## Task 2 — def5678\n#### V2 — (code) minor, u\nChecklist: lessons.md:30\n"
)
BUILD_LOG = (
    "STATUS: done\nB1: sent to planner\nTask 1: done — abc1234\nR1: fixed — def5678\n"
    "COPY-REQUEST: a -> b\nCOPIED: a -> b\nV1: fixed — 0123456\nV2: fixed — 0123456\n"
)
WATCH = (
    "19:01 fresh t/planner after note: HANDOFF planner after Task 1 — 2026-10-30 19:00 | s 11111111\n"
    "19:40 cap t/planner 201,000 tokens; ordered to hand over | so this started a copy as 22222222.\n"
)
LESSONS = "STATUS: lessons\n## Known error classes\n12. a fence indented five spaces -> keep fences at 0-3 spaces\n"


def planner_calls(run):
    return [(30_000, 10, [TEXT, bash(f"printf 'Task 1: written — abc1234\\n' >> {run}/plan-log.md")])]


def builder_calls(run):
    return [
        (20_000, 10, [read(f"{run}/_builder-a-assignment.md")]),
        (40_000, 10, [bash(f"printf 'Task 1: done — abc1234\\n' >> {run}/build-log-a.md")]),
    ]


@pytest.fixture
def home(tmp_path, monkeypatch) -> Home:
    h = Home(tmp_path)
    monkeypatch.setenv("HOME", str(h.root / "home"))
    monkeypatch.setenv("PATH", f"{h.root / 'bin'}:{os.environ['PATH']}")
    monkeypatch.setenv("STUB_DIR", str(h.stub))
    return h


@pytest.fixture
def run(tmp_path, home):
    run = tmp_path / "run"
    run.mkdir()
    for name, text in (
        ("critique.md", CRITIQUE),
        ("critique-response.md", RESPONSE),
        ("verify.md", VERIFY),
        ("build-log-a.md", BUILD_LOG),
        ("_watch.log", WATCH),
        ("lessons.md", LESSONS),
        ("plan-log.md", "STATUS: done\nTask 1: written — abc1234\n"),
    ):
        (run / name).write_text(text, encoding="utf-8")
    home.session("t/planner", PLANNER, planner_calls(run), start="2026-10-30T19:01:00")
    home.session("t/builder-a", BUILDER, builder_calls(run), start="2026-10-30T19:10:00")
    return run


def listed(home: Home, name: str, sid: str, start: str = "2026-10-30T19:01:00") -> None:
    """An agent row whose transcript is not on this machine (another machine's session, or a removed file)."""
    started = datetime.datetime.fromisoformat(start).replace(tzinfo=datetime.UTC)
    row = {"name": name, "sessionId": sid, "state": "done", "kind": "background"}
    home.rows.append({**row, "startedAt": int(started.timestamp() * 1000)})
    home.save_rows()


@pytest.fixture
def idle_transcript(run, home):
    calls = [(25_000, 10, [read(f"{run}/_critic-assignment.md"), write(f"{run}/handoff-critic.md")])]
    home.session("t/critic", CRITIC, calls, start="2026-10-30T19:20:00")


@pytest.fixture
def two_task_transcript(run, home):
    calls = [
        (50_000, 10, [bash(f"printf '## Task 1 — abc1234\\n' >> {run}/verify.md")]),
        (60_000, 10, [bash(f"printf 'Task 2: passed\\n' >> {run}/verify.md")]),
    ]
    home.session("t/verifier", VERIFIER, calls, start="2026-10-30T19:30:00")


def test_findings_per_task_count_each_kind_once_and_mark_the_missed_plan_finding(run):
    d = score_run.score(run, "t/", None)
    t1 = d["tasks"]["1"]
    assert (t1["C"], t1["A"], t1["R"], t1["V"], t1["V_plan"], t1["missed"], t1["B"]) == (1, 1, 0, 1, 1, 1, 1)
    t2 = d["tasks"]["2"]
    assert (t2["R"], t2["V"], t2["V_plan"], t2["missed"]) == (1, 1, 0, 0)


def test_missed_counts_a_plan_finding_on_a_task_the_critic_reviewed_without_a_finding(tmp_path):
    (tmp_path / "critique.md").write_text("STATUS: x\n\n## Task 1\nChecked and fine: y\n", encoding="utf-8")
    (tmp_path / "verify.md").write_text("## Task 1 — abc1234\n#### V1 — (plan) major, w\n", encoding="utf-8")
    assert score_run.task_counts(tmp_path)["1"]["missed"] == 1


def test_a_b_id_counts_once_for_the_task_its_text_names_or_the_next_done_line_below(tmp_path):
    log = (
        "Task 1: done — a\nB1: sent to plan-fixer — task-02.md:40 says x\nTask 2: done — b\nB1: answered — y\n"
        "B2: fixed in code — Task 1 Step 3 x\nB3: sent to plan-fixer — the suite\n"
    )
    (tmp_path / "build-log.md").write_text(log, encoding="utf-8")
    assert {t: r["B"] for t, r in score_run.task_counts(tmp_path).items()} == {"1": 1, "2": 1, "none": 1}


def test_roles_count_sessions_caps_idle_first_call_and_cache_ratio(run):
    d = score_run.score(run, "t/", None)
    planner = d["roles"]["planner"]
    assert (planner["sessions"], planner["cap"], planner["idle"], planner["first_call"]) == (1, 1, 0, 30_000)
    assert planner["cache_ratio"] > 0.99  # the Home writes input 3, cache write 7, cache read context - 10
    assert d["roles"]["builder-a"]["first_call"] == 20_000


def test_an_idle_session_wrote_no_record_line_and_no_commit(run, idle_transcript):
    d = score_run.score(run, "t/", None)
    assert d["roles"]["critic"]["idle"] == 1 and d["roles"]["critic"]["sessions"] == 1


def test_cost_is_attributed_by_the_task_lines_a_session_wrote_and_split_between_two(run, two_task_transcript):
    d = score_run.score(run, "t/", None)
    assert d["tasks"]["1"]["cost"] > 0 and d["tasks"]["2"]["cost"] > 0
    assert abs(d["tasks"]["1"]["cost"] + d["tasks"]["2"]["cost"] + d["tasks"]["none"]["cost"] - d["cost"]) < 1e-9
    v = d["attribution"][VERIFIER]
    assert v["tasks"] == ["1", "2"] and abs(v["cost"] / 2 - v["per_task"]) < 1e-12


def test_request_minutes_need_a_time_on_both_lines(run):
    d = score_run.score(run, "t/", None)
    kinds = {(r["kind"], r["minutes"]) for r in d["requests"]}
    assert ("CHECKOUT-REQUEST", 4) in kinds and ("COPY-REQUEST", None) in kinds


def test_repeated_lesson_classes_are_the_findings_that_cite_a_lessons_md_line(run):
    with (run / "verify.md").open("a", encoding="utf-8") as f:
        f.write(
            "#### V3 — (code) minor, s\nIt quotes `Checklist: lessons.md:12`.\n"
            "Checklist: .claude/ecc/agents/pr-test-analyzer.md:30\n"
            "#### V4 — (code) minor, t\nChecklist: .claude/ecc/agents/pr-test-analyzer.md:30\n"
        )
    assert score_run.repeated(run) == {"lessons.md:12": ["C1", "V1"], "lessons.md:30": ["V2"]}


def test_missing_sources_give_n_a_cells_not_an_exception(tmp_path, home):
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "critique.md").write_text("STATUS: reviewing\n", encoding="utf-8")
    d = score_run.score(empty, "t/", None)
    assert d["roles"] == {} and d["requests"] == [] and "n/a: _watch.log" in d["line"]


def test_the_line_names_the_run_and_the_totals(run):
    line = score_run.score(run, "t/", None)["line"]
    assert line.startswith(
        "score run: tasks 2, findings C 1 A 1 R 1 V 2 (plan 1, missed 1), rejected 0, sessions 2 (cap 1, idle 0)"
    )


def test_main_prints_the_line_then_the_table_and_json_on_request(run, capsys):
    assert score_run.main([str(run), "--prefix", "t/"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("score run: ") and "| task | C | A | R | V |" in out
    assert score_run.main([str(run), "--prefix", "t/", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["run"] == "run"


def test_the_agent_rows_and_the_watch_log_count_when_no_transcript_is_on_the_machine(tmp_path, home):
    # V1: the role rows come from the agent rows and _watch.log first; only the transcript cells are n/a
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "_watch.log").write_text(WATCH, encoding="utf-8")
    listed(home, "t/planner", PLANNER)
    listed(home, "t/builder-a", BUILDER)
    d = score_run.score(bare, "t/", None)
    planner, builder = d["roles"]["planner"], d["roles"]["builder-a"]
    assert (planner["sessions"], planner["fresh"], planner["cap"]) == (1, 1, 1)
    assert (builder["sessions"], builder["fresh"], builder["cap"]) == (1, 0, 0)
    assert [planner[k] for k in ("idle", "first_call", "cache_ratio", "cost")] == [None, None, None, None]
    assert "sessions 2 (cap 1, idle n/a), cost n/a, cache-read n/a (n/a: transcripts)" in d["line"]
    assert "| planner | 1 | 1 | 1 | n/a | n/a | n/a | n/a |" in score_run.table(d)


def test_without_the_watch_log_the_cap_and_fresh_cells_are_n_a(run):
    (run / "_watch.log").unlink()
    d = score_run.score(run, "t/", None)
    assert (d["roles"]["planner"]["cap"], d["roles"]["planner"]["fresh"]) == (None, None)
    assert "(cap n/a, idle 0)" in d["line"] and d["line"].endswith("(n/a: _watch.log)")


def test_a_read_with_a_stderr_redirection_or_the_read_tool_writes_no_record(run, home):
    # V2: `2>/dev/null` and `2>&1` redirect stderr, and a Read names a file without writing it
    critic = [
        bash(f"head -1 {run}/critique.md 2>/dev/null"),
        read(f"{run}/verify.md"),
        write(f"{run}/handoff-critic.md"),
    ]
    home.session("t/critic", CRITIC, [(25_000, 10, critic)], start="2026-10-30T19:20:00")
    reader = [bash(f"grep -n '^## Task 3' {run}/verify.md 2>&1 | head -3"), write(f"{run}/handoff-verifier.md")]
    home.session("t/verifier", VERIFIER, [(26_000, 10, reader)], start="2026-10-30T19:30:00")
    d = score_run.score(run, "t/", None)
    assert d["roles"]["critic"]["idle"] == 1 and d["roles"]["verifier"]["idle"] == 1
    assert d["attribution"][VERIFIER]["tasks"] == [] and "3" not in d["tasks"]


@pytest.mark.parametrize(
    ("command", "writes"),
    [
        ("head -1 /r/critique.md 2>/dev/null", False),
        ("grep -n '^## Task 3' /r/verify.md 2>&1 | head -3", False),
        ("grep -c x /r/verify.md &>/dev/null", False),
        ("cat /r/build-log.md >&2", False),
        ("sed -n '1,5p' /r/verify.md > /r/scratch/x.txt", False),
        ("printf 'Task 1: done\\n' >> /r/build-log-a.md", True),
        ("echo 'STATUS: x' > /r/verify.md", True),
        ("printf 'C1: applied\\n' | tee -a /r/critique-response.md", True),
        ("sed -i '1s/.*/STATUS: done/' /r/fixer-log.md", True),
        ("/r/critique.md", True),  # an Edit or a Write: its text is the bare path
    ],
)
def test_a_write_is_a_stdout_redirection_tee_or_sed_i_naming_a_record_file(command, writes):
    assert score_run.writes_record(command) is writes


def test_request_minutes_cross_a_month_end_and_an_impossible_date_is_n_a():
    # V3: the minutes come from the two datetimes, not from the day-of-month digits
    request, answer = "CHECKOUT-REQUEST: abc1234 — 2026-10-31 23:50 UTC", "CHECKED-OUT: abc1234 — 2026-11-01 00:05 UTC"
    assert score_run.minutes(request, answer) == 15
    assert score_run.minutes("SANDBOX: x — 2026-10-32 10:00 UTC", "SUPPLIED: x — 2026-11-01 10:00 UTC") is None


def test_the_docstring_names_the_section_that_holds_the_table_columns_and_an_example_line(run):
    # V4: scripts/docs/ holds the pages of scripts/*.py only (test_docs.py); manager/README.md documents this script
    readme = (SCRIPTS / "manager" / "README.md").read_text(encoding="utf-8")
    section = readme.split("\n## score_run.py\n", 1)[1].split("\n## ", 1)[0]
    assert "scripts/manager/README.md" in str(score_run.__doc__) and "scripts/docs/" not in str(score_run.__doc__)
    table = score_run.table(score_run.score(run, "t/", None)).splitlines()
    headers = [line for line in table if line.startswith(("| task |", "| role |", "| request |"))]
    assert len(headers) == 3 and [h for h in headers if h not in section] == []
    assert re.search(r"(?m)^score [\w.-]+: tasks \d+, findings C \d+ A \d+ R \d+ V \d+ \(plan \d+", section)


def test_repeated_counts_only_a_line_that_starts_with_checklist_as_measure_manager_does(run):  # judge J1
    (run / "critique.md").write_text(
        CRITIQUE + "#### C2 — p\nIts cause is C1's Checklist: lessons.md:12 again.\n"
        "#### C3 — q\nChecklist: lessons.md:12\nChecklist: lessons.md:12 twice\n",
        encoding="utf-8",
    )
    assert score_run.repeated(run) == {"lessons.md:12": ["C1", "C3", "V1"], "lessons.md:30": ["V2"]}


# Task 6 Step 0 (V5, R4, C31, A16, A17): every session of a task in its cost row, rejected ids, idle by unit lines.
FIXER = "12121212-3434-5656-7878-909090909090"
EARLY = "13131313-2424-3535-4646-575757575757"
LATE = "14141414-2525-3636-4747-585858585858"
BUILDER_B = "15151515-2626-3737-4848-595959595959"


def test_a_line_written_with_edit_or_write_names_the_task(run, home):
    write_call = tool("Write", file_path=f"{run}/critique.md", content="## Task 2\n#### C2 — x\n")
    home.session("t/critic", CRITIC, [(30_000, 10, [write_call])], start="2026-10-30T19:20:00")
    old = "#### V1 — (plan) major, w"
    edit_call = tool("Edit", file_path=f"{run}/verify.md", old_string=old, new_string=f"{old}\n\n## Task 2 — def5678")
    home.session("t/verifier", VERIFIER, [(30_000, 10, [edit_call])], start="2026-10-30T19:30:00")
    d = score_run.score(run, "t/", None)
    assert (d["attribution"][CRITIC]["tasks"], d["attribution"][CRITIC]["by"]) == (["2"], "lines")
    assert d["attribution"][VERIFIER]["tasks"] == ["2"]  # V1's line is in old_string: not written by this call


def test_an_answer_or_fix_line_names_the_task_its_id_is_filed_under(run, home):
    answer = bash(f"printf '%s\\n' 'V1: applied — t' >> {run}/critique-response.md")
    home.session("t/plan-fixer", FIXER, [(30_000, 10, [answer])], start="2026-10-30T19:40:00")
    fix = bash(f"printf 'R1: fixed — def5678\\n' >> {run}/build-log-a.md")
    home.session("t/builder-a", LATE, [(30_000, 10, [fix])], start="2026-10-30T19:50:00")
    d = score_run.score(run, "t/", None)
    assert d["attribution"][FIXER]["tasks"] == ["1"]  # V1 is filed under ## Task 1 in verify.md
    assert d["attribution"][LATE]["tasks"] == ["2"]  # R1 under ## Task 2 (diff) in critique.md


def test_a_session_that_names_no_task_takes_the_tasks_of_its_roles_next_session(run, home):
    home.session("t/builder-a", EARLY, [(30_000, 10, [bash("git commit -m 'wip'")])], start="2026-10-30T19:05:00")
    note = write(f"{run}/handoff-builder-a.md")
    home.session("t/builder-a", LATE, [(30_000, 10, [note])], start="2026-10-30T19:55:00")
    d = score_run.score(run, "t/", None)
    early, late = d["attribution"][EARLY], d["attribution"][LATE]
    assert (early["tasks"], early["by"]) == (["1"], "next")  # the 19:10 builder-a session wrote Task 1: done
    assert (late["tasks"], late["by"]) == ([], "none")
    assert abs(sum(t["cost"] for t in d["tasks"].values()) - d["cost"]) < 1e-9


def test_rejected_counts_each_id_once_under_its_task_from_the_response_and_the_build_logs(tmp_path):
    critique = "STATUS: x\n\n## Task 1\n#### C1 — x\n#### A1 — y\n\n## Task 2 (diff)\n#### R1 — (code) z\n"
    (tmp_path / "critique.md").write_text(critique, encoding="utf-8")
    (tmp_path / "verify.md").write_text("## Task 2 — def5678\n#### V1 — (code) minor, u\n", encoding="utf-8")
    response = "STATUS: x\nC1: rejected — a\nC1: rejected — b\nA1: added to Task 1 — t\nB1: rejected — c\n"
    (tmp_path / "critique-response.md").write_text(response, encoding="utf-8")
    log = "Task 1: done — a\nB1: sent to plan-fixer — x\nTask 2: done — b\nR1: rejected — p\nV1: rejected — q\n"
    (tmp_path / "build-log.md").write_text(log, encoding="utf-8")
    (tmp_path / "build-log-b.md").write_text("B1: fixed in code — Task 1 Step 2, y\n", encoding="utf-8")
    assert {t: r["rejected"] for t, r in score_run.task_counts(tmp_path).items()} == {"1": 1, "2": 3}


@pytest.mark.parametrize(
    ("line", "idle", "tasks", "by"),
    [
        ("ACK 1234abcd", True, [], "none"),
        ("R1: fixed — def5678", False, ["2"], "lines"),
    ],
)
def test_a_session_whose_record_writes_hold_no_unit_line_is_idle(run, home, line, idle, tasks, by):
    write_line = bash(f"printf '{line}\\n' >> {run}/build-log-a.md")
    home.session("t/builder-a", LATE, [(30_000, 10, [write_line])], start="2026-10-30T19:55:00")
    late = score_run.score(run, "t/", None)["attribution"][LATE]
    assert (late["idle"], late["tasks"], late["by"]) == (idle, tasks, by)


def test_a_b_line_names_the_task_of_its_own_log_and_an_answer_the_task_of_the_b_sent_to_a_fixer(run, home):
    (run / "build-log-b.md").write_text("B1: fixed in code — x\nTask 2: done — def5678\n", encoding="utf-8")
    fix = bash(f"printf 'B1: fixed in code — x\\n' >> {run}/build-log-b.md")
    home.session("t/builder-b", BUILDER_B, [(30_000, 10, [fix])], start="2026-10-30T19:45:00")
    answer = bash(f"printf '%s\\n' 'B1: applied — t' >> {run}/critique-response.md")
    home.session("t/plan-fixer", FIXER, [(30_000, 10, [answer])], start="2026-10-30T19:40:00")
    d = score_run.score(run, "t/", None)
    assert d["attribution"][BUILDER_B]["tasks"] == ["2"]  # B1 above Task 2: done in build-log-b.md
    assert d["attribution"][FIXER]["tasks"] == ["1"]  # build-log-a.md's B1 is the one sent to the planner


ECONOMY = (
    "| units | cost per unit | cache write $ per unit | sessions per unit | copies per unit | findings per unit "
    "| escaped |"
)
CAP_ORDER = "19:40 cap t/planner 201,000 tokens; ordered to hand over | so this started a copy as 22222222.\n"
UNIT_END_ORDER = (
    "20:00 unit end t/builder-a 181,000 tokens; ordered to hand over | so this started a copy as 33333333.\n"
)
GRACE = (
    "19:50 grace t/builder-a: new line 1 at 181,000 tokens; the unit-end order comes in 300 s unless the note does\n"
)


def test_economy_copies_are_the_cap_and_unit_end_lines_of_the_watch_log_under_the_prefix(run):
    other = CAP_ORDER.replace("t/planner", "other/planner")
    (run / "_watch.log").write_text(CAP_ORDER + GRACE + UNIT_END_ORDER + other, encoding="utf-8")
    economy = score_run.score(run, "t/", None)["economy"]  # the two numbered tasks of the fixture are its units
    assert (economy["units"], economy["copies"], economy["copies_per_unit"]) == (2, 2, 1.0)


def test_economy_row_is_one_row_of_per_unit_cells_after_the_tables(run):
    d = score_run.score(run, "t/", None)
    economy = d["economy"]  # 2 units; 2 sessions; 5 findings (C 1 A 1 R 1 V 2); one cap line; no M, J or O id
    assert (economy["sessions_per_unit"], economy["findings_per_unit"], economy["copies_per_unit"]) == (1.0, 2.5, 0.5)
    assert economy["escaped"] == 0 and economy["cost_per_unit"] == pytest.approx(d["cost"] / 2, abs=1e-4)
    head, rule, row = score_run.table(d).splitlines()[-3:]
    assert (head, rule) == (ECONOMY, "|---:|---:|---:|---:|---:|---:|---:|")
    cells = f"${economy['cost_per_unit']:.2f} | ${economy['cache_write_per_unit']:.2f}"
    assert row == f"| 2 | {cells} | 1.0 | 0.5 | 2.5 | 0 |"


def test_economy_copies_read_the_older_watch_out_without_a_watch_log_and_are_n_a_without_both(run):
    (run / "_watch.log").unlink()
    assert score_run.score(run, "t/", None)["economy"]["copies"] is None
    (run / "_control").mkdir()
    watch_out = run / "_control" / "watch.out"
    watch_out.write_text(CAP_ORDER + UNIT_END_ORDER + UNIT_END_ORDER, encoding="utf-8")
    economy = score_run.score(run, "t/", None)["economy"]
    assert (economy["copies"], economy["copies_per_unit"]) == (3, 1.5)
    (run / "_watch.log").write_text(CAP_ORDER, encoding="utf-8")  # the named source wins over the older one
    assert score_run.score(run, "t/", None)["economy"]["copies"] == 1


def test_economy_escaped_counts_the_m_j_and_o_ids_and_is_n_a_without_lessons_and_judge(run):
    assert score_run.score(run, "t/", None)["economy"]["escaped"] == 0
    (run / "lessons.md").write_text(LESSONS + "13. M1 (main session): x\n14. O1 (owner): y\n", encoding="utf-8")
    (run / "judge.md").write_text("STATUS: done\n#### J1 — z\n", encoding="utf-8")
    assert score_run.score(run, "t/", None)["economy"]["escaped"] == 3
    (run / "lessons.md").unlink()
    (run / "judge.md").unlink()
    assert score_run.score(run, "t/", None)["economy"]["escaped"] is None


def test_economy_cost_is_n_a_when_a_transcript_is_missing(run, home):
    listed(home, "t/critic", CRITIC)  # an agent row whose transcript is not on this machine: a partial cost is none
    economy = score_run.score(run, "t/", None)["economy"]
    assert (economy["cost_per_unit"], economy["sessions_per_unit"]) == (None, 1.5)


def test_economy_row_is_n_a_without_a_unit_and_without_its_sources(tmp_path, home):
    empty = tmp_path / "empty"
    empty.mkdir()
    d = score_run.score(empty, "t/", None)
    assert d["economy"]["units"] == 0 and d["economy"]["escaped"] is None
    assert [v for k, v in d["economy"].items() if k.endswith("_per_unit") or k == "copies"] == [None] * 6
    assert score_run.table(d).splitlines()[-1] == "| 0 | n/a | n/a | n/a | n/a | n/a | n/a |"


def test_economy_row_closes_the_printed_output_and_json_carries_it(run, capsys):
    assert score_run.main([str(run), "--prefix", "t/"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert printed[-3] == ECONOMY and printed[-1].startswith("| 2 | $")
    assert score_run.main([str(run), "--prefix", "t/", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["economy"]["units"] == 2


def test_economy_row_is_documented_in_the_readme_section_and_the_docstring():
    readme = (SCRIPTS / "manager" / "README.md").read_text(encoding="utf-8")
    section = readme.split("\n## score_run.py\n", 1)[1].split("\n## ", 1)[0]
    assert ECONOMY in section and "unit end" in section and "economy" in str(score_run.__doc__)


# Spec 005, requirement 7a: the cache is measured in money. Per role the dollars of the cache reads, the cache writes
# and the output beside the cost; in the economy row the cache write dollars per unit.
def priced(home: Home, sid: str, usage: dict) -> None:
    """Every assistant line of the transcript `sid` gets `usage` (the Home writes Opus calls with input 3, cache write
    7, cache read context - 10 and the call's output)."""
    path = home.projects / f"{sid}.jsonl"
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d["type"] == "assistant":
            d["message"]["usage"] = usage
        out.append(json.dumps(d) + "\n")
    path.write_text("".join(out), encoding="utf-8")


def big(write: int = 200_000, read: int = 7_000_000, output: int = 300_000) -> dict:
    return {
        "input_tokens": 0,
        "output_tokens": output,
        "cache_creation_input_tokens": write,
        "cache_read_input_tokens": read,
    }


def test_a_role_s_cost_splits_into_cache_read_cache_write_and_output_dollars(run, home):
    """The planner's one call (Opus, per 1M tokens read $0.20, write $8, output $20): read 7,000,000 = 1.40, write
    200,000 = 1.60, output 300,000 = 6.00, the cost 9.00; the builder keeps the Home's own usage."""
    priced(home, PLANNER, big())
    d = score_run.score(run, "t/", None)
    planner, builder = d["roles"]["planner"], d["roles"]["builder-a"]
    parts = ("cache_read_cost", "cache_write_cost", "output_cost", "cost")
    assert [planner[k] for k in parts] == pytest.approx([1.40, 1.60, 6.00, 9.00])
    opus = score_run.ur.PRICE["opus"]  # input, output, cache read, cache write
    assert builder["cache_read_cost"] == pytest.approx((19_990 + 39_990) * opus[2] / 1e6)  # contexts 20,000 and 40,000
    assert builder["cache_write_cost"] == pytest.approx(2 * 7 * opus[3] / 1e6)
    assert builder["output_cost"] == pytest.approx(2 * 10 * opus[1] / 1e6)
    table = score_run.table(d).splitlines()
    assert (
        "| role | sessions | fresh | cap | idle | first call | cache read | cost | read $ | write $ | output $ |"
        in table
    )
    assert "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|" in table
    row = next(x for x in table if x.startswith("| planner |"))
    assert row.endswith("| 7,200,000 | 97% | 9.00 | 1.40 | 1.60 | 6.00 |")


def test_a_resumed_copy_s_inherited_calls_count_once_in_the_dollars_too(run, home):
    """`seen` is shared across sessions: the calls a resumed session copied are priced under the session that began."""
    priced(home, PLANNER, big())
    home.session("t/planner", BUILDER_B, [(10_000, 10, [TEXT])], start="2026-10-30T19:40:00", resumes=PLANNER)
    d = score_run.score(run, "t/", None)
    assert d["roles"]["planner"]["cache_write_cost"] == pytest.approx(1.60 + 7 * 8 / 1e6, abs=1e-6)


def test_the_dollar_cells_are_n_a_without_a_transcript(tmp_path, home):
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "_watch.log").write_text(WATCH, encoding="utf-8")
    listed(home, "t/planner", PLANNER)
    d = score_run.score(bare, "t/", None)
    planner = d["roles"]["planner"]
    assert [planner[k] for k in ("cache_read_cost", "cache_write_cost", "output_cost")] == [None] * 3
    assert "| planner | 1 | 1 | 1 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |" in score_run.table(d)


def test_economy_row_gets_a_cache_write_dollars_per_unit_cell_after_the_cost(run, home):
    """The planner's call writes 1,000,000 tokens (Opus $8 per 1M) and the builder's two calls 14: $8.000112 over the
    two units of the fixture is $4.00 a unit; the cost per unit is $4.01 (the builder's calls add $0.0125 to the $8)."""
    priced(home, PLANNER, big(write=1_000_000, read=0, output=0))
    d = score_run.score(run, "t/", None)
    assert d["economy"]["cache_write_per_unit"] == pytest.approx(4.000056, abs=1e-4)
    assert d["economy"]["cost_per_unit"] == pytest.approx(4.006266, abs=1e-4)
    assert score_run.table(d).splitlines()[-1] == "| 2 | $4.01 | $4.00 | 1.0 | 0.5 | 2.5 | 0 |"


def test_the_cache_write_cell_is_n_a_when_a_transcript_is_missing(run, home):
    listed(home, "t/critic", CRITIC)  # an agent row whose transcript is not on this machine: a partial total is none
    d = score_run.score(run, "t/", None)
    assert d["economy"]["cache_write_per_unit"] is None and d["roles"]["critic"]["cache_write_cost"] is None
    assert d["roles"]["planner"]["cache_write_cost"] is not None  # a role that was read keeps its own
    assert score_run.table(d).splitlines()[-1].split(" | ")[2] == "n/a"
