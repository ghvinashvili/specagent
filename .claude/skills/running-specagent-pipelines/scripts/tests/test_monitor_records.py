"""Tests of monitor_records.py on a run folder in tmp_path; a fake `claude` first on PATH records its argv and must never run.

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_monitor_records.py
"""

import ast
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import time

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SCRIPTS / "monitor_records.py"
GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.org",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.org",
}
MINUTE = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}"
DUTIES = """\
# Duty list (spec 5.1.2): each duty is ticked with its date -u time when done; the monitor ticks the merges.

Extracted 2026-10-29 20:00 UTC from 00-index.md: 3 new duties.
- [ ] D1 Merged: a->b — blocks Task 3 (builder b) — due when Tasks 1, 2 done — 00-index.md:20
- [ ] D2 judge approval — blocks the judge — due when every record's STATUS is final
- [ ] D3 Merged: b→a — blocks Task 4 (builder a) — due when Task 5 done — 00-index.md:22
"""
D1 = "D1 Merged: a->b — blocks Task 3 (builder b) — due when Tasks 1, 2 done — 00-index.md:20"


def iso(seconds_ago: float) -> str:
    t = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=seconds_ago)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def shown(stamp: str, seconds: bool = True) -> str:
    return stamp[: 19 if seconds else 16].replace("T", " ")


def git(cwd: pathlib.Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(cwd), *args], check=True, env=GIT_ENV, capture_output=True, text=True)
    return out.stdout.strip()


def commit(repo: pathlib.Path, message: str) -> str:
    git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def run(tmp_path):
    """Two builders with a git checkout each, a judge, a plan log, `_common.md` with a 10-minute bound."""
    run = tmp_path / "run"
    (run / "_control").mkdir(parents=True)
    agents = {}
    for lane, task in (("a", 2), ("b", 3)):
        repo = tmp_path / f"repo-{lane}"
        git(tmp_path, "init", "-q", "-b", "main", str(repo))
        commit(repo, f"base {lane}")
        agents[f"manager/builder-{lane}"] = {
            "cwd": str(repo),
            "status": f"build-log-{lane}.md",
            "final": "STATUS: done",
        }
        (run / f"build-log-{lane}.md").write_text(f"STATUS: building Task {task}\n", encoding="utf-8")
    agents["manager/judge"] = {"cwd": str(tmp_path), "status": "judge.md", "final": "STATUS: done"}
    (run / "_control" / "_agents.json").write_text(json.dumps({"agents": agents}), encoding="utf-8")
    (run / "_common.md").write_text("# Common rules\nRequest-line bound: 10 minutes\n", encoding="utf-8")
    (run / "judge.md").write_text("STATUS: waiting\n", encoding="utf-8")
    (run / "plan-log.md").write_text("STATUS: writing Task 3\n", encoding="utf-8")
    fake = tmp_path / "bin" / "claude"
    fake.parent.mkdir()
    fake.write_text(f"#!/bin/sh\necho \"$@\" >> '{tmp_path / 'claude-argv.txt'}'\n", encoding="utf-8")
    fake.chmod(0o755)
    yield run
    assert not (tmp_path / "claude-argv.txt").exists(), "the monitor ran claude"


def env_of(run: pathlib.Path) -> dict:
    return {**GIT_ENV, "PATH": f"{run.parent / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}"}


def argv(run: pathlib.Path, command: str, *rest: str) -> list[str]:
    return [sys.executable, "-I", str(SCRIPT), command, str(run), *rest]


def mon(run: pathlib.Path, command: str, *rest: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv(run, command, *rest), capture_output=True, text=True, env=env_of(run), timeout=120, check=False
    )


def add(run: pathlib.Path, name: str, *lines: str) -> None:
    with (run / name).open("a", encoding="utf-8") as f:
        f.write("".join(line + "\n" for line in lines))


def state(run: pathlib.Path) -> dict:
    return json.loads((run / "_control" / "monitor.json").read_text(encoding="utf-8"))


def plant(run: pathlib.Path, **fields) -> None:
    (run / "_control" / "monitor.json").write_text(json.dumps(fields), encoding="utf-8")


def alarms(run: pathlib.Path) -> list[tuple[str, bool]]:
    return [(a["id"], a["open"]) for a in state(run)["alarms"]]


def logged(run: pathlib.Path) -> list[str]:
    """The monitor log's messages, each stripped of its `YYYY-MM-DD HH:MM:SS UTC ` stamp (checked)."""
    lines = (run / "_control" / "monitor.log").read_text(encoding="utf-8").splitlines()
    assert all(re.match(rf"{MINUTE}:\d\d UTC ", line) for line in lines), lines
    return [line[24:] for line in lines]


def wait_for(check, seconds: float = 20) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            if check():
                return
        except (OSError, ValueError, KeyError, TypeError):
            pass
        time.sleep(0.05)
    raise AssertionError("timed out")


def repo_of(run: pathlib.Path, lane: str) -> pathlib.Path:
    agents = json.loads((run / "_control" / "_agents.json").read_text(encoding="utf-8"))["agents"]
    return pathlib.Path(agents[f"manager/builder-{lane}"]["cwd"])


def test_once_wakes_each_new_request_with_its_requester_and_task_then_stays_silent(run):
    add(run, "build-log-b.md", "Working.", "SANDBOX: allow writes to /srv/x")
    add(
        run,
        "build-log-a.md",
        "- COPY-REQUEST: wiki/a.md from the main checkout",
        "COPIED: wiki/a.md — 2026-10-29 20:10 UTC",
    )
    (run / "extra.md").write_text("STATUS: open\nFF-REQUEST: feat/a 1234567 -> feat/b 89abcde\n", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in run.glob("*.md")}
    r = mon(run, "once")
    assert (r.returncode, r.stdout) == (
        0,
        (
            "WAKE request build-log-b.md:SANDBOX:1 SANDBOX build-log-b.md:3 (manager/builder-b, Task 3): allow writes to /srv/x\n"
            "WAKE request extra.md:FF-REQUEST:1 FF-REQUEST extra.md:2 (-, -): feat/a 1234567 -> feat/b 89abcde\n"
            "woke: 2\n"
        ),
    ), r.stderr
    found = {e["id"]: e for e in state(run)["requests"]}
    late = found["build-log-a.md:COPY-REQUEST:1"]
    assert (late["late"], late["answered"]) == (True, late["seen"])
    sandbox = found["build-log-b.md:SANDBOX:1"]
    assert (sandbox["line"], sandbox["answered"], sandbox["late"]) == (3, None, False)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", sandbox["seen"])
    assert mon(run, "once").stdout == "woke: 0\n"
    assert {p.name: p.read_bytes() for p in run.glob("*.md")} == before


def test_watch_exits_0_on_the_first_wake_and_on_a_line_planted_after_it_started(run):
    add(run, "build-log-b.md", "SANDBOX: allow writes to /srv/x")
    r = mon(run, "watch", "--interval", "0.2", "--hours", "0.01")
    assert (r.returncode, r.stdout.splitlines()[-1]) == (0, "woke: 1"), r.stderr
    proc = subprocess.Popen(
        argv(run, "watch", "--interval", "0.2", "--hours", "0.05"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env_of(run),
    )
    try:
        wait_for(lambda: state(run)["watch"]["ended"] is None and state(run)["watch"]["last_round"])
        add(run, "build-log-a.md", "CHECKOUT-REQUEST: 1234567")
        out, err = proc.communicate(timeout=20)
    finally:
        proc.kill()
    assert (proc.returncode, out) == (
        0,
        (
            "WAKE request build-log-a.md:CHECKOUT-REQUEST:1 CHECKOUT-REQUEST build-log-a.md:2 (manager/builder-a, Task 2): 1234567\n"
            "woke: 1\n"
        ),
    ), err
    assert [m for m in logged(run) if not m.startswith("WAKE ")] == [
        f"armed {run} interval=0.2 s hours=0.01 bound=10 min",
        "woke: 1",
        f"armed {run} interval=0.2 s hours=0.05 bound=10 min",
        "woke: 1",
    ]
    assert state(run)["watch"]["ended"] == "woke"


def test_watch_expires_with_exit_1_and_a_re_arm_logs_armed_again(run):
    for _ in range(2):
        r = mon(run, "watch", "--interval", "0.2", "--hours", "0.0002")
        assert (r.returncode, r.stdout) == (1, "expired after 0.0002 h: re-arm with the same command\n"), r.stderr
    assert logged(run) == [f"armed {run} interval=0.2 s hours=0.0002 bound=10 min", "expired after 0.0002 h"] * 2
    assert state(run)["watch"]["ended"] == "expired"


def test_every_command_exits_2_on_a_missing_run_folder_and_writes_no_bytecode(tmp_path):
    missing, copy = tmp_path / "nowhere", tmp_path / "copy"
    copy.mkdir()
    for name in ("monitor_records.py", "check_formats.py", "duty_list.py"):
        (copy / name).write_bytes((SCRIPTS / name).read_bytes())
    for cmd in (["watch"], ["once"], ["answer", "x.md:SANDBOX:1", "ok"], ["report"], ["status"]):
        argv = [sys.executable, "-I", str(copy / "monitor_records.py"), cmd[0], str(missing), *cmd[1:]]
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
        assert (r.returncode, r.stdout, r.stderr) == (2, "", f"{missing}: no such run folder\n"), cmd
    assert sorted(p.name for p in copy.iterdir()) == ["check_formats.py", "duty_list.py", "monitor_records.py"]


def test_an_open_request_past_the_bound_of_common_md_wakes_once_and_opens_an_alarm(run):
    add(run, "build-log-b.md", "SANDBOX: allow writes to /srv/x")
    seen = iso(12 * 60 + 30)
    entry = {"id": "build-log-b.md:SANDBOX:1", "kind": "SANDBOX", "file": "build-log-b.md", "line": 2}
    plant(run, requests=[{**entry, "text": "allow writes to /srv/x", "seen": seen, "answered": None, "late": False}])
    text = "overdue build-log-b.md:SANDBOX:1 SANDBOX build-log-b.md:2: open 12 min, bound 10 min"
    r = mon(run, "once")
    assert r.stdout == f"WAKE {text}\nwoke: 1\n", r.stderr
    [alarm] = state(run)["alarms"]
    assert (alarm["id"], alarm["kind"], alarm["text"], alarm["open"]) == (
        f"overdue:{entry['id']}",
        "overdue",
        text,
        True,
    )
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", alarm["since"])
    assert mon(run, "once").stdout == "woke: 0\n"
    assert logged(run) == [f"WAKE {text}"]


def test_answer_appends_the_answer_line_with_the_clock_time_and_closes_the_alarm(run):
    add(run, "build-log-b.md", "SANDBOX: allow writes to /srv/x", "SANDBOX: allow writes to /srv/y")
    entry = {"id": "build-log-b.md:SANDBOX:1", "kind": "SANDBOX", "file": "build-log-b.md", "line": 2}
    plant(
        run,
        requests=[{**entry, "text": "allow writes to /srv/x", "seen": iso(11 * 60), "answered": None, "late": False}],
    )
    assert mon(run, "once").stdout.startswith("WAKE overdue build-log-b.md:SANDBOX:1 ")
    r = mon(run, "answer", "build-log-b.md:SANDBOX:2", "added /srv/y")
    assert (r.returncode, r.stderr) == (
        2,
        "build-log-b.md:SANDBOX:2: answer build-log-b.md:SANDBOX:1 first (build-log-b.md:2)\n",
    )
    r = mon(run, "answer", "build-log-b.md:SANDBOX:1", "added /srv/x to the write allow list")
    assert (r.returncode, r.stdout) == (0, "answered build-log-b.md:SANDBOX:1: build-log-b.md:4\n"), r.stderr
    last = (run / "build-log-b.md").read_text(encoding="utf-8").splitlines()[-1]
    m = re.fullmatch(rf"SUPPLIED: added /srv/x to the write allow list — ({MINUTE}) UTC", last)
    assert m, last
    when = datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=datetime.UTC)
    assert abs((datetime.datetime.now(datetime.UTC) - when).total_seconds()) < 120
    first = next(e for e in state(run)["requests"] if e["id"] == entry["id"])
    assert first["answered"] is not None and first["late"] is False
    assert alarms(run) == [(f"overdue:{entry['id']}", False)]
    assert logged(run)[-1] == "answered build-log-b.md:SANDBOX:1 (build-log-b.md:4)"
    check = subprocess.run(
        [sys.executable, "-I", str(SCRIPTS / "check_formats.py"), str(run)],
        capture_output=True,
        text=True,
        env=env_of(run),
        check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr
    again = mon(run, "answer", "build-log-b.md:SANDBOX:1", "twice")
    assert (again.returncode, again.stderr) == (2, "build-log-b.md:SANDBOX:1: answered already (build-log-b.md:4)\n")


def test_refuse_writes_the_refused_line_and_an_unknown_id_exits_2(run):
    add(run, "build-log-a.md", "FF-REQUEST: feat/a 1234567 -> feat/b 89abcde")
    r = mon(run, "answer", "build-log-a.md:FF-REQUEST:1", "the plan branch moved; rebase first", "--refuse")
    assert (r.returncode, r.stdout) == (0, "answered build-log-a.md:FF-REQUEST:1: build-log-a.md:3\n"), r.stderr
    last = (run / "build-log-a.md").read_text(encoding="utf-8").splitlines()[-1]
    assert re.fullmatch(rf"REFUSED: FF-REQUEST — the plan branch moved; rebase first — {MINUTE} UTC", last), last
    [entry] = state(run)["requests"]
    assert (entry["id"], entry["late"], entry["answered"] is not None) == ("build-log-a.md:FF-REQUEST:1", True, True)
    assert mon(run, "once").stdout == "woke: 0\n"
    r = mon(run, "answer", "build-log-a.md:FF-REQUEST:2", "no such line")
    assert (r.returncode, r.stdout, r.stderr) == (2, "", "build-log-a.md:FF-REQUEST:2: no such request\n")


def test_report_gives_a_row_per_request_with_whole_minutes_and_dashes_for_late_ones(run):
    add(
        run,
        "build-log-b.md",
        "SANDBOX: allow writes to /srv/x",
        "SUPPLIED: added — 2026-10-29 20:08 UTC",
        "COPY-REQUEST: wiki/a.md",
    )
    add(run, "build-log-a.md", "CHECKOUT-REQUEST: 1234567", "CHECKED-OUT: 1234567 — 2026-10-29 20:01 UTC")
    sandbox = {"id": "build-log-b.md:SANDBOX:1", "kind": "SANDBOX", "file": "build-log-b.md", "line": 2, "text": "x"}
    copy = {
        "id": "build-log-b.md:COPY-REQUEST:1",
        "kind": "COPY-REQUEST",
        "file": "build-log-b.md",
        "line": 4,
        "text": "y",
    }
    seen = iso(3 * 60 + 30)
    plant(
        run,
        requests=[
            {**sandbox, "seen": "2026-10-29T20:00:00Z", "answered": "2026-10-29T20:07:59Z", "late": False},
            {**copy, "seen": seen, "answered": None, "late": False},
        ],
    )
    assert mon(run, "once").stdout == "woke: 0\n"
    r = mon(run, "report")
    assert (r.returncode, r.stdout.splitlines()) == (
        0,
        [
            "| kind | file:line | asked (UTC) | answered (UTC) | minutes |",
            "|---|---|---|---|---|",
            "| SANDBOX | build-log-b.md:2 | 2026-10-29 20:00 | 2026-10-29 20:07 | 7 |",
            f"| COPY-REQUEST | build-log-b.md:4 | {shown(seen, False)} | open | 3 |",
            "| CHECKOUT-REQUEST | build-log-a.md:2 | — | — | — |",
        ],
    ), r.stderr


def test_a_second_claim_of_one_task_wakes_in_the_first_round_and_its_release_closes_the_alarm(run):
    add(
        run,
        "plan-log.md",
        "Task 3: started by planner-d",
        "Task 3: started by manager/planner-d",
        "Task 4: started by planner",
        "- Task 4: started by manager/planner-b",
    )
    text = "claim-race Task 4: planner (plan-log.md:4) and planner-b (plan-log.md:5)"
    r = mon(run, "once")
    assert r.stdout == f"WAKE {text}\nwoke: 1\n", r.stderr
    assert alarms(run) == [("claim-race:4:planner-b", True)]
    assert mon(run, "once").stdout == "woke: 0\n"
    add(run, "plan-log.md", "Task 4: claim released by manager/planner-b")
    assert mon(run, "once").stdout == "woke: 0\n"
    assert alarms(run) == [("claim-race:4:planner-b", False)]


def test_a_claim_whose_claimant_stopped_wakes_after_the_grace_and_closes_when_written(run):
    add(run, "plan-log.md", "Task 7: started by planner-d")
    registry = run / "_control" / "registry.json"
    registry.write_text(json.dumps({"roles": {"manager/planner-d": {"state": "stopped"}}}), encoding="utf-8")
    kept = registry.read_bytes()
    assert mon(run, "once").stdout == "woke: 0\n"
    assert list(state(run)["stalls"]) == ["7"]
    text = "stalled-claim Task 7: planner-d is stopped and Task 7 is not written (plan-log.md:2)"
    assert mon(run, "once", "--grace", "0").stdout == f"WAKE {text}\nwoke: 1\n"
    assert mon(run, "once", "--grace", "0").stdout == "woke: 0\n"
    add(run, "plan-log.md", "Task 7: written — abc1234")
    assert mon(run, "once", "--grace", "0").stdout == "woke: 0\n"
    assert (alarms(run), state(run)["stalls"]) == ([("stalled-claim:7", False)], {})
    assert registry.read_bytes() == kept


def test_a_due_merge_duty_wakes_and_a_verified_merged_line_ticks_it_but_a_quoted_one_never(run):
    repo_a, repo_b = repo_of(run, "a"), repo_of(run, "b")
    t1, t2, merged = commit(repo_b, "task 1"), commit(repo_b, "task 2"), commit(repo_b, "merge a into b")
    t5, back = commit(repo_a, "task 5"), commit(repo_a, "merge b into a")
    (run / "_control" / "duties.md").write_text(DUTIES, encoding="utf-8")
    add(run, "build-log-a.md", f"Task 1: done — {t1}")
    add(run, "build-log-b.md", f"Task 5: done — {t5}")
    (run / "lessons.md").write_text(
        f"# Lessons\nMerged: b->a at {back}\nA waiter: `Merged: a->b at {merged}`.\n", encoding="utf-8"
    )
    assert mon(run, "once").stdout == "woke: 0\n"
    lines = (run / "_control" / "duties.md").read_text(encoding="utf-8").splitlines()
    assert re.fullmatch(rf"- \[x\] {MINUTE} UTC \(lessons\.md:2, {back[:7]}\) D3 Merged: b→a — .*", lines[5]), lines[5]
    add(run, "build-log-a.md", f"Task 2: done — {t2}")
    r = mon(run, "once")
    assert r.stdout == "WAKE duty D1 due: Merged: a->b — blocks Task 3 (builder b)\nwoke: 1\n", r.stderr
    add(run, "lessons.md", f"Merged: a->b at {merged[:9]}")
    assert mon(run, "once").stdout == "woke: 0\n"
    line = (run / "_control" / "duties.md").read_text(encoding="utf-8").splitlines()[3]
    assert re.fullmatch(rf"- \[x\] {MINUTE} UTC \(lessons\.md:4, {merged[:7]}\) {re.escape(D1)}", line), line
    assert [m for m in logged(run) if m.startswith("ticked ")] == [
        f"ticked D3 (lessons.md:2, {back[:7]})",
        f"ticked D1 (lessons.md:4, {merged[:7]})",
    ]


def test_a_merged_line_that_misses_a_done_task_or_head_wakes_with_the_reason(run):
    repo_b = repo_of(run, "b")
    t1 = commit(repo_b, "task 1")
    git(repo_b, "checkout", "-q", "-b", "side")
    side = commit(repo_b, "lacks task 2")
    git(repo_b, "checkout", "-q", "main")
    t2 = commit(repo_b, "task 2")
    git(repo_b, "checkout", "-q", "-b", "later")
    ahead = commit(repo_b, "holds both, not in HEAD")
    git(repo_b, "checkout", "-q", "main")
    (run / "_control" / "duties.md").write_text(DUTIES, encoding="utf-8")
    add(run, "build-log-a.md", f"Task 1: done — {t1}", f"Task 2: done — {t2}")
    (run / "lessons.md").write_text(f"# Lessons\nMerged: a->b at {side}\n- Merged: a→b at {ahead}\n", encoding="utf-8")
    r = mon(run, "once")
    assert r.stdout == (
        "WAKE duty D1 due: Merged: a->b — blocks Task 3 (builder b)\n"
        f"WAKE merge-check D1: lessons.md:2 Merged: a->b at {side[:7]} fails: Task 2's {t2[:7]} is not in it\n"
        f"WAKE merge-check D1: lessons.md:3 Merged: a→b at {ahead[:7]} fails: not an ancestor of HEAD in {repo_b}\n"
        "woke: 3\n"
    ), r.stderr
    assert mon(run, "once").stdout == "woke: 0\n"
    add(run, "lessons.md", f"Merged: a->b at {t2}")
    assert mon(run, "once").stdout == "woke: 0\n"
    assert alarms(run) == [("merge-check:D1:2", False), ("merge-check:D1:3", False)]


def test_a_merge_duty_ticks_on_its_own_marker_only_never_on_a_shorter_or_a_longer_one(run):
    repo_b = repo_of(run, "b")
    t1, t2, t5 = commit(repo_b, "task 1"), commit(repo_b, "task 2"), commit(repo_b, "task 5")
    merged = commit(repo_b, "merge the four lanes")
    duties = DUTIES.replace("a->b — blocks Task 3", "a+b+c+d — blocks Task 3")
    duties = duties.replace("b→a — blocks Task 4 (builder a)", "a+b — blocks Task 4 (builder b)")
    (run / "_control" / "duties.md").write_text(duties, encoding="utf-8")
    add(run, "build-log-b.md", f"Task 5: done — {t5}")
    (run / "lessons.md").write_text(f"# Lessons\nMerged: a+b+c+d at {merged}\n", encoding="utf-8")
    r = mon(run, "once")
    assert r.stdout == "WAKE duty D3 due: Merged: a+b — blocks Task 4 (builder b)\nwoke: 1\n", r.stderr
    add(run, "build-log-a.md", f"Task 1: done — {t1}", f"Task 2: done — {t2}")
    (run / "lessons.md").write_text(f"# Lessons\nMerged: a+b at {merged}\n", encoding="utf-8")
    r = mon(run, "once")
    assert r.stdout == "WAKE duty D1 due: Merged: a+b+c+d — blocks Task 3 (builder b)\nwoke: 1\n", r.stderr
    add(run, "lessons.md", f"Merged: a+b+c+d at {merged}")
    assert mon(run, "once").stdout == "woke: 0\n"
    assert [m for m in logged(run) if m.startswith("ticked ")] == [
        f"ticked D3 (lessons.md:2, {merged[:7]})",
        f"ticked D1 (lessons.md:3, {merged[:7]})",
    ]


def test_a_due_duty_left_unticked_past_the_bound_wakes_overdue_duty_once(run):
    (run / "_control" / "duties.md").write_text(DUTIES, encoding="utf-8")
    add(run, "build-log-a.md", "Task 1: done — 1111111", "Task 2: done — 2222222")
    plant(run, duties={"D1": {"due": iso(11 * 60 + 30)}})
    r = mon(run, "once")
    assert r.stdout == "WAKE overdue-duty D1: open 11 min since due, bound 10 min\nwoke: 1\n", r.stderr
    assert alarms(run) == [("overdue-duty:D1", True)]
    assert mon(run, "once").stdout == "woke: 0\n"


def test_a_verdict_wakes_once_and_the_judge_duty_waits_for_every_final_status_but_the_judge_s(run):
    (run / "_control" / "duties.md").write_text(DUTIES, encoding="utf-8")
    add(run, "judge.md", "VERDICT: approve the run")
    (run / "build-log-a.md").write_text("STATUS: done\n", encoding="utf-8")
    r = mon(run, "once")
    assert r.stdout == "WAKE verdict judge.md:2: approve the run\nwoke: 1\n", r.stderr
    (run / "build-log-b.md").write_text("STATUS: done — Tasks 3 and 10\n", encoding="utf-8")
    r = mon(run, "once")
    assert r.stdout == "WAKE duty D2 due: judge approval — blocks the judge\nwoke: 1\n", r.stderr
    assert mon(run, "once").stdout == "woke: 0\n"


def test_done_and_written_lines_are_logged_once_and_never_wake(run):
    add(run, "build-log-b.md", "Task 3: done — 89abcde0")
    add(run, "plan-log.md", "Task 0: index written — 7ffa2b7", "- Task 3: written — b997318")
    assert mon(run, "once").stdout == "woke: 0\n"
    assert mon(run, "once").stdout == "woke: 0\n"
    assert logged(run) == [
        "done Task 3 89abcde (build-log-b.md:2)",
        "written Task 0 7ffa2b7 (plan-log.md:2)",
        "written Task 3 b997318 (plan-log.md:3)",
    ]


def test_status_says_armed_only_while_a_watch_runs_with_a_fresh_heartbeat(run):
    r = mon(run, "status")
    assert (r.returncode, r.stdout) == (1, "not armed: no watch recorded\n")
    proc = subprocess.Popen(
        argv(run, "watch", "--interval", "0.2", "--hours", "0.02"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env_of(run),
    )
    try:
        wait_for(lambda: state(run)["watch"]["last_round"])
        first = state(run)["watch"]["last_round"]
        wait_for(lambda: state(run)["watch"]["last_round"] != first)
        r = mon(run, "status")
        assert r.returncode == 0, r.stdout
        assert re.fullmatch(
            rf"armed since {MINUTE}:\d\d UTC, last round {MINUTE}:\d\d UTC, interval 0\.2 s\n", r.stdout
        )
        add(run, "build-log-b.md", "SANDBOX: allow writes to /srv/x")
        proc.communicate(timeout=20)
    finally:
        proc.kill()
    assert proc.returncode == 0
    ended = state(run)["watch"]["ended_at"]
    r = mon(run, "status")
    assert (r.returncode, r.stdout) == (
        1,
        f"not armed: the last watch woke at {shown(ended)} UTC; re-arm with the same command\n",
    )
    last = iso(600)
    plant(run, watch={"armed": iso(3600), "last_round": last, "interval": 60.0, "ended": None, "ended_at": None})
    r = mon(run, "status")
    assert (r.returncode, r.stdout) == (
        1,
        f"not armed: no round since {shown(last)} UTC (interval 60 s); re-arm with the same command\n",
    )


def test_every_function_of_the_monitor_is_under_50_lines():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    sizes = {n.name: n.end_lineno - n.lineno + 1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert sizes and {name: size for name, size in sizes.items() if size >= 50} == {}
