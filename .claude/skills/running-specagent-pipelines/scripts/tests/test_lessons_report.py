"""lessons_report.py: whether a lesson lowers the error it was written for (owner, 2026-11-02)."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "lessons_report.py"
LESSONS = """# Lessons
## Read first (main session, 2026-11-01)
1. Read late and narrow.
## Known error classes (from earlier runs; check each task against them)
- A test list is no task.
## Lessons from this run
(planner and builders add one-line rules here, with the finding ids)
- Every task carries its tests in full (C3, C4).
- A name a task creates is grepped first
  in its module at the base commit (B1).
"""


def run_folder(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    (run / "lessons.md").write_text(LESSONS, encoding="utf-8")
    (run / "build-log-a.md").write_text(
        "STATUS: done\nTask 1: done — abc1234\nTask 2: done — def5678\n", encoding="utf-8"
    )
    (run / "critique.md").write_text(
        "## Task 3\n#### C3 — (plan) no tests\nChecklist: lessons.md:8\n"
        "#### C9 — (plan) the tests again\nLesson: lessons.md:8\n#### C10 — (plan) a list again\nChecklist: lessons.md:5\n",
        encoding="utf-8",
    )
    (run / "verify.md").write_text("#### V2 — (code) a second def\nLesson: lessons.md:10\n", encoding="utf-8")
    return run


def report(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, timeout=60, check=False
    )


def test_a_finding_that_names_a_lesson_and_is_not_its_source_is_a_recurrence_and_flags_it_to_become_code(tmp_path):
    run = run_folder(tmp_path)
    r = report(str(run), "--json")
    assert r.returncode == 0, r.stderr
    [d] = json.loads(r.stdout)["runs"]
    items = {i["line"]: i for i in d["items"]}
    assert d["units"] == 2 and d["lessons"] == {"read first": 1, "carried": 1, "this run": 2}
    assert items[8]["sources"] == ["C3", "C4"] and items[8]["recurrences"] == ["C9"]
    assert items[9]["recurrences"] == ["V2"]  # the continuation line 10 belongs to the item of line 9
    assert d["make_code"] == [5, 8, 9] and d["unmeasured"] == [3]
    assert d["carried"] == {"classes": 1, "recurrences": 1, "per_10_units": 5.0}


def test_an_id_a_carried_or_read_first_lesson_names_is_an_earlier_run_s_finding_so_this_run_s_finding_of_that_id_is_a_recurrence(
    tmp_path,
):  # V7 of the verifier: finding ids restart per run, so the J6 a carried class names is not this run's J6
    run = tmp_path / "run"
    run.mkdir()
    (run / "lessons.md").write_text(
        "# Lessons\n"
        "## Read first (main session, 2026-11-02)\n"
        "1. Read late and narrow (V3 of an earlier run).\n"
        "## Known error classes (from earlier runs; check each task against them)\n"
        "- A settings file that leaves the credentials readable (J6 of an earlier judge).\n"
        "- A test that asserts a constant (V1 of an earlier run).\n"
        "## Lessons from this run\n"
        "- Every task carries its tests in full (C3, C4).\n",
        encoding="utf-8",
    )
    (run / "build-log.md").write_text("Task 1: done — abc1234\nTask 2: done — def5678\n", encoding="utf-8")
    (run / "judge.md").write_text(
        "#### J6 — (code) the settings leave the file readable\nChecklist: lessons.md:5\n", encoding="utf-8"
    )
    (run / "verify.md").write_text(
        "#### V1 — (code) a test that asserts a constant\nChecklist: lessons.md:6\n"
        "#### V3 — (code) a whole file read\nLesson: lessons.md:3\n",
        encoding="utf-8",
    )
    (run / "critique.md").write_text(
        "#### C3 — (plan) no tests\nChecklist: lessons.md:8\n#### C9 — (plan) the tests again\nLesson: lessons.md:8\n",
        encoding="utf-8",
    )
    r = report(str(run), "--json")
    assert r.returncode == 0, r.stderr
    [d] = json.loads(r.stdout)["runs"]
    items = {i["line"]: i for i in d["items"]}
    assert [items[n]["recurrences"] for n in (3, 5, 6, 8)] == [["V3"], ["J6"], ["V1"], ["C9"]]
    assert items[5]["sources"] == ["J6"] and items[8]["sources"] == ["C3", "C4"]  # the column keeps what a text names
    assert d["make_code"] == [3, 5, 6, 8]
    assert d["carried"] == {"classes": 2, "recurrences": 2, "per_10_units": 10.0}


def test_the_markdown_names_the_lessons_to_make_code_and_the_unmeasured(tmp_path):
    r = report(str(run_folder(tmp_path)))
    assert "then one or more recurrences): lessons.md:5, lessons.md:8, lessons.md:9" in r.stdout
    assert "unmeasured (no finding names them): 1 of 4" in r.stdout


def test_two_runs_follow_a_lesson_across_them_and_a_folder_without_lessons_exits_2(tmp_path):
    first = run_folder(tmp_path)
    second = tmp_path / "second"
    second.mkdir()
    (second / "lessons.md").write_text(LESSONS, encoding="utf-8")
    r = report(str(first), str(second))
    assert (
        "## Across runs (recurrences / units)" in r.stdout
        and "| every task carries its tests in full | 1/2 | 0/0 |" in r.stdout
    )
    assert report(str(tmp_path / "nowhere")).returncode == 2


def test_the_vault_pages_a_transcript_read_are_counted(tmp_path):
    lines = [
        {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/h/vault/INDEX.md"}}]},
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/h/vault/INDEX.md"}}]},
        },
        {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": "/h/repo/README.md"}}]},
        },
    ]
    t = tmp_path / "s.jsonl"
    t.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    r = report(str(run_folder(tmp_path)), "--transcript", str(t), "--json")
    assert json.loads(r.stdout)["vault_reads"] == {"INDEX.md": 2}


HELD_LESSONS = """# Lessons
## Read first (main session, 2026-11-02)
1. Read late and narrow.
## Lessons from this run
- A task quotes its base by file:line (C3), added 2026-11-02T02:00Z.
- A check meets every recorded answer (C4), added 2026-11-02T05:00Z.
"""


def git(repo: Path, *args: str, date: str = "", env: dict | None = None) -> str:
    extra = {"GIT_COMMITTER_DATE": date, "GIT_AUTHOR_DATE": date} if date else {}
    base = {"PATH": "/usr/bin:/bin", "HOME": str(repo), "GIT_CONFIG_NOSYSTEM": "1"}
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        capture_output=True,
        text=True,
        env={**base, **extra, **(env or {})},
        check=True,
    )
    return done.stdout.strip()


def held_world(tmp_path: Path) -> tuple[Path, Path, Path, str, str]:
    """A run whose two findings break lessons added before and after the builder session started (02:30Z)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "commit", "-q", "--allow-empty", "-m", "Task 1", date="2026-11-02T03:00:00Z")
    first = git(repo, "rev-parse", "--short", "HEAD")
    git(
        repo,
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "Task 2\n\nRole-Session: 22222222-0000",
        date="2026-11-02T03:30:00Z",
    )
    second = git(repo, "rev-parse", "--short", "HEAD")
    run = tmp_path / "run"
    (run / "_control").mkdir(parents=True)
    (run / "lessons.md").write_text(HELD_LESSONS, encoding="utf-8")
    (run / "build-log-a.md").write_text(
        f"Task 1: committed — {first}\nTask 1: done\nV4: fixed — {second}\nTask 2: done\n", encoding="utf-8"
    )
    (run / "verify.md").write_text(
        f"## Task 1 — {first}\n#### V5 — (code) the base unquoted\nLesson: lessons.md:5\n"
        f"#### V6 — (code) an answer unmet\nLesson: lessons.md:6\n"
        f"## Task 2 — {second}\n#### V7 — (code) an answer unmet again\nLesson: lessons.md:6\n",
        encoding="utf-8",
    )
    # a copy of 11111111 (its original's history, so its start within a second) and lane b's session overlap Task 1
    sessions = {
        "11111111-0000": ("02:30:00", "04:00:00"),
        "11111111-copy": ("02:30:01", "03:50:00"),
        "22222222-0000": ("06:00:00", "07:00:00"),
        "33333333-0000": ("02:40:00", "04:00:00"),
    }
    registry = {
        "roles": {
            "run/builder-a": {"session_ids": ["11111111-0000", "11111111-copy", "22222222-0000"]},
            "run/builder-b": {"session_ids": ["33333333-0000"]},
        }
    }
    (run / "_control" / "registry.json").write_text(json.dumps(registry), encoding="utf-8")
    projects = tmp_path / "projects"
    (projects / "-w").mkdir(parents=True)
    for sid, (start, end) in sessions.items():
        lines = [json.dumps({"timestamp": f"2026-11-02T{t}.000Z"}) for t in (start, end)]
        (projects / "-w" / f"{sid}.jsonl").write_text("\n".join(lines), encoding="utf-8")
    return run, repo, projects, first, second


def test_a_recurrence_counts_only_when_the_erring_session_held_the_lesson(tmp_path):
    """v2: V6 breaks a lesson added at 05:00, after the session that made Task 1 (by its time, 03:00, inside the
    02:30-04:00 transcript of builder-a and its copy; builder-b's overlapping session is another lane's) started: not
    held, so no recurrence. V7 breaks it in Task 2, whose Role-Session trailer
    names a session started at 06:00: held, a recurrence. V5's lesson was added at 02:00: held."""
    run, repo, projects, _, _ = held_world(tmp_path)
    r = report(str(run), "--repo", str(repo), "--projects", str(projects), "--json")
    assert r.returncode == 0, r.stderr
    items = {i["line"]: i for i in json.loads(r.stdout)["runs"][0]["items"]}
    assert items[5]["recurrences"] == ["V5"] and items[5]["not_held"] == [] and items[5]["added"] == "2026-11-02T02:00Z"
    assert items[6]["recurrences"] == ["V7"] and items[6]["not_held"] == ["V6"] and items[6]["held_unknown"] == []
    md = report(str(run), "--repo", str(repo), "--projects", str(projects)).stdout
    assert "| 6 | this run | C4 | V7 | 5.0 | V6 | - |" in md


def test_without_the_repository_a_recurrence_still_counts_and_is_listed_as_unknown(tmp_path):
    run, _, projects, _, _ = held_world(tmp_path)
    items = {
        i["line"]: i
        for i in json.loads(report(str(run), "--projects", str(projects), "--json").stdout)["runs"][0]["items"]
    }
    assert items[6]["recurrences"] == ["V6", "V7"] and items[6]["held_unknown"] == ["V6", "V7"]
    assert items[5]["held_unknown"] == ["V5"] and items[6]["not_held"] == []


def test_a_lesson_of_read_first_was_held_by_every_session_of_the_run(tmp_path):
    run, repo, projects, first, _ = held_world(tmp_path)
    with (run / "verify.md").open("a", encoding="utf-8") as f:
        f.write(f"## Task 3 — {first}\n#### V8 — (code) read the whole file\nLesson: lessons.md:3\n")
    items = {
        i["line"]: i
        for i in json.loads(report(str(run), "--repo", str(repo), "--projects", str(projects), "--json").stdout)[
            "runs"
        ][0]["items"]
    }
    assert items[3]["recurrences"] == ["V8"] and items[3]["held_unknown"] == [] and items[3]["not_held"] == []
