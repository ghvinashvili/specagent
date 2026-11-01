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
    first = ("--first", "STATUS: reviewed through Task 1", "--first", "STATUS: done")  # line 1 set in place
    line_one = write(tmp_path, "line-one.md", "STATUS: reviewed through Task 1\n## Task 1\n")
    assert run_script("wait_for_log.py", line_one, "2", *first, "--once").returncode == 0
    assert run_script("wait_for_log.py", log, "2", *first, "--once").returncode == 3
    done = write(tmp_path, "done.md", "STATUS: done\n## Task 1\n")  # the critic's last act: the second text counts
    assert run_script("wait_for_log.py", done, "2", *first, "--once").returncode == 0
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


def test_open_ids_by_kind_parity_and_task(tmp_path):  # C8, C9, A7, R7
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
    assert listed(run, "--kind", "C,R,B", "--parity", "even", "--no-shared") == (0, ["C3", "R1"])  # judge J3
    assert listed(run, "--kind", "C,B", "--parity", "odd", "--no-shared") == (0, ["C2"])
    assert listed(run, "--kind", "B", "--task", "1") == (3, [])
    assert listed(run, "--kind", "A,V") == (3, [])
    assert listed(run, "--kind", "C, R") == (2, [])  # an entry that is not a kind: a usage error, never "none"
    assert listed(run, "--kind", "c,r") == (2, [])


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


def test_open_ids_cause_code_and_tasks_give_a_builders_lane(tmp_path):
    """A builder's final_check (a project's run of 2026-11-01): the open (code) findings of its own tasks, nothing else."""
    run = tmp_path / "run"
    run.mkdir()
    write(
        run,
        "verify.md",
        "STATUS: verifying Task 3\n## Task 2 — abc1234\n#### V1 — (code) major: x\n#### V2 — (plan) major: y\n"
        "## Task 3 — def5678\n#### V3 — (code) minor: z\n",
    )
    write(run, "critique.md", "STATUS: reviewed through Task 3\n")
    write(run, "critique-response.md", "STATUS: writing Task 4\n")
    assert listed(run, "--kind", "V,R", "--cause", "code") == (0, ["V1", "V3"])
    assert listed(run, "--kind", "V,R", "--cause", "code", "--tasks", "2,4") == (0, ["V1"])
    assert listed(run, "--kind", "V,R", "--cause", "code", "--tasks", "4") == (3, [])
