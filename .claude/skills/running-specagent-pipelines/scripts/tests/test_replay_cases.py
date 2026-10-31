"""Tests of replay_cases.py on a synthetic run folder and a tiny checkout (tmp_path).

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
"""

import collections
import os
import pathlib
import subprocess
import sys
import textwrap

import pytest

yaml = pytest.importorskip("yaml")

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "replay_cases.py"
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
Repo = collections.namedtuple("Repo", "path a b c")


def git(path: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        check=True,
        env=GIT_ENV,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path) -> Repo:
    """A: data.txt has no gamma; B, the fix, adds ten gamma lines; C changes notes.txt only."""
    path = tmp_path / "checkout"
    subprocess.run(["git", "init", "-q", str(path)], check=True, env=GIT_ENV)
    (path / "data.txt").write_text("alpha\nbeta\n")
    (path / "notes.txt").write_text("one\n")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "A")
    a = git(path, "rev-parse", "HEAD")
    (path / "data.txt").write_text("alpha\nbeta\n" + "gamma\n" * 10)
    git(path, "commit", "-q", "-am", "B: the fix")
    b = git(path, "rev-parse", "HEAD")
    (path / "notes.txt").write_text("two\n")
    git(path, "commit", "-q", "-am", "C")
    return Repo(path, a, b, git(path, "rev-parse", "HEAD"))


@pytest.fixture
def run(tmp_path) -> pathlib.Path:
    path = tmp_path / "run"
    path.mkdir()
    return path


def write(run: pathlib.Path, name: str, text: str) -> None:
    (run / name).write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def replay(run: pathlib.Path, repo: Repo, out: pathlib.Path, *extra: str, env: dict | None = None):
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(run), "--repo", str(repo.path), "--out", str(out), *extra],
        capture_output=True,
        text=True,
        timeout=60,
        env=env or GIT_ENV,
        check=False,
    )


def grade(case: pathlib.Path, *args: str) -> int:
    env = {**GIT_ENV, "TMPDIR": str(case.parent.parent)}
    return subprocess.run(
        ["sh", str(case / "grader.sh"), *args], capture_output=True, text=True, timeout=60, env=env, check=False
    ).returncode


def task(case: pathlib.Path) -> dict:
    return yaml.safe_load((case / "task.yaml").read_text(encoding="utf-8"))


def row(out: pathlib.Path, ident: str) -> str:
    rows = [
        line for line in (out / "index.md").read_text(encoding="utf-8").splitlines() if line.startswith(f"| {ident} |")
    ]
    assert len(rows) == 1, rows
    return rows[0]


def test_a_finding_becomes_a_case_with_a_grader_before_the_fix_and_one_at_it(run, repo, tmp_path):
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1

        ## Task 1

        #### V1 — data.txt has no gamma (minor, code)
        - Place: data.txt.
        - Command: `grep -c gamma data.txt`
        - Output: `0`.
        - Expected: gamma.
        """,
    )
    write(
        run,
        "build-log.md",
        f"""
        STATUS: building Task 2
        Task 1: done — {repo.a[:7]}
        V1: fixed — {repo.b[:7]} — gamma added.
        """,
    )
    out = tmp_path / "out"
    p = replay(run, repo, out)
    assert p.returncode == 0, p.stderr
    case = out / "V1"
    t = task(case)
    assert (t["schema_version"], t["name"], t["pass_rule"]) == (1, "replay-run-V1", "deterministic_all")
    assert t["fixture"] == {"repo": str(repo.path), "sha": repo.a, "paths": ["data.txt"]}
    assert (t["command"], t["recorded_output"]) == ("grep -c gamma data.txt", "0")
    assert [(g["script"], g["args"], g["sha"]) for g in t["graders"]] == [
        ("grader.sh", ["before"], repo.a),
        ("grader.sh", ["fix"], repo.b),
    ]
    # before: `0` appears at A; fix: B prints `10`, in which `0` is no whole word
    assert (grade(case, "before"), grade(case, "fix")) == (0, 0)
    assert (grade(case, "before", repo.b), grade(case, "fix", repo.a)) == (1, 1)
    assert repo.b[:7] in row(out, "V1") and "grep -c gamma data.txt" in row(out, "V1")


def test_each_section_that_cannot_be_replayed_is_listed_with_its_reason_and_gets_no_case(run, repo, tmp_path):
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1

        ## Task 1

        #### V2 — prose only (minor, code)
        - Place: data.txt.

        #### V3 — a Python call (minor, code)
        - Command: `llm.call(x)` with a stand-in CLI.
        - Output: `y`.

        #### V4 — the network (minor, code)
        - Command: `curl -s https://example.org/x`
        - Output: `0`.

        #### V5 — a model (minor, code)
        - Command: `claude -p hello`
        - Output: `hi`.

        #### V6 — a probe (minor, code)
        - Command: `.venv/bin/python -I probe.py`
        - Output: `ok`.

        #### V7 — a placeholder (minor, code)
        - Command: `grep -c x <dir>/a.txt`
        - Output: `0`.

        #### V8 — the output in prose (minor, code)
        - Command: `grep -c gamma data.txt`
        - Output: no gamma line.

        #### V10 — a file the checkout does not hold (minor, code)
        - Command: `grep -c x missing.txt`
        - Output: `0`.

        #### V11 — a redirection (minor, code)
        - Command: `grep -c gamma data.txt > out.txt`
        - Output: `0`.

        #### V12 — a path outside (minor, code)
        - Command: `sed -n 1p ../other/x.txt`
        - Output: `x`.

        #### V18 — an elided command (minor, code)
        - Command: `grep -c '…' data.txt`
        - Output: `0`.

        ## Notes

        #### V9 — no commit named anywhere (minor, code)
        - Command: `grep -c gamma data.txt`
        - Output: `0`.
        """,
    )
    write(
        run,
        "build-log.md",
        f"""
        STATUS: building Task 2
        Task 1: done — {repo.a[:7]}
        """,
    )
    out = tmp_path / "out"
    p = replay(run, repo, out)
    assert p.returncode == 0, p.stderr
    reasons = {
        "V2": "no command",
        "V3": "no shell command",
        "V4": "needs the network",
        "V5": "needs a model",
        "V6": "not a read-only tool",
        "V7": "a placeholder in the command",
        "V8": "no recorded output",
        "V9": "no sha",
        "V10": "not in the checkout at the sha",
        "V11": "writes a file",
        "V12": "reads outside the checkout",
        "V18": "cut short",
    }
    for ident, reason in reasons.items():
        assert reason in row(out, ident), ident
        assert not (out / ident).exists(), ident
    assert "| no command | 1 |" in (out / "index.md").read_text(encoding="utf-8")


def test_the_reasons_table_counts_a_section_once_for_each_reason(run, repo, tmp_path):
    write(
        run,
        "verify.md",
        f"""
        STATUS: verified through Task 1

        #### V1 — two files the checkout does not hold (minor, code)
        - Command (at {repo.a[:7]}): `grep -c x missing.txt gone.txt`
        - Output: `0`.
        """,
    )
    out = tmp_path / "out"
    assert replay(run, repo, out).returncode == 0
    assert "missing.txt" in row(out, "V1") and "gone.txt" in row(out, "V1")
    assert "| not in the checkout at the sha | 1 |" in (out / "index.md").read_text(encoding="utf-8")


def test_a_placeholder_in_words_is_a_placeholder_not_two_redirections(run, repo, tmp_path):
    write(
        run,
        "verify.md",
        f"""
        STATUS: verified through Task 1

        #### V1 — a placeholder of several words (minor, code)
        - Command (at {repo.a[:7]}): `grep -c gamma <a copy of the owner's checkout>/data.txt`
        - Output: `0`.
        """,
    )
    out = tmp_path / "out"
    assert replay(run, repo, out).returncode == 0
    assert "a placeholder in the command: <a copy of the owner's checkout>" in row(out, "V1")


def test_a_label_may_hold_a_code_span_but_a_colon_inside_a_code_span_ends_no_label(run, repo, tmp_path):
    write(
        run,
        "verify.md",
        f"""
        STATUS: verified through Task 1

        #### V1 — a Python call, the interpreter in the label (minor, code)
        - Command (demo-verify at {repo.a[:7]}, `.venv/bin/python -I`): `amounts("x")` [2026];

        #### V2 — probes in words, the flags in the label (minor, code)
        - Command (at {repo.a[:7]}, the package's python `-I -B`): probe.py, probe2.py

        #### V3 — a read-only command, its sha in a label with a code span (minor, code)
        - Command (at {repo.a[:7]}, `sh`): `grep -c gamma data.txt`
        - Output: `0`.

        #### V4 — no colon after the word (minor, code)
        - Command `grep -c gamma data.txt` → `x: 0`
        """,
    )
    out = tmp_path / "out"
    assert replay(run, repo, out).returncode == 0
    assert "no shell command: a Python name" in row(out, "V1")
    assert "no shell command: the Command line begins with no code span" in row(out, "V2")
    t = task(out / "V3")
    assert (t["fixture"]["sha"], t["command"], t["recorded_output"]) == (repo.a, "grep -c gamma data.txt", "0")
    assert row(out, "V4").endswith("| no command |")


def test_a_command_that_opens_a_sentence_of_a_paragraph_is_read_with_that_paragraph_s_output(run, repo, tmp_path):
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1

        ## Task 1

        #### V1 — prose, a read-only command (minor, code)
        Place: data.txt. It has no gamma. Command: `grep -c gamma
        data.txt` counts them. Output: `0`.

        #### V2 — prose, a probe in words (minor, code)
        The count is off (data.txt). Command:
        probe.py P2 (a fake reply). Output: `x`.

        #### V3 — prose, the output in the next paragraph (minor, code)
        Command: `grep -c gamma data.txt`.

        Output: `0`.

        #### V4 — the word inside a sentence (minor, code)
        The Command: `grep -c gamma data.txt` field. Output: `0`.
        """,
    )
    write(
        run,
        "build-log.md",
        f"""
        STATUS: building Task 2
        Task 1: done — {repo.a[:7]}
        """,
    )
    out = tmp_path / "out"
    assert replay(run, repo, out).returncode == 0
    t = task(out / "V1")
    assert (t["fixture"]["sha"], t["command"], t["recorded_output"]) == (repo.a, "grep -c gamma data.txt", "0")
    assert grade(out / "V1", "before") == 0
    assert "no shell command: the Command line begins with no code span" in row(out, "V2")
    assert "no recorded output" in row(out, "V3")
    assert row(out, "V4").endswith("| no command |")


def test_the_fix_sha_comes_from_the_section_its_heading_or_the_log_and_the_fixture_is_the_oldest_fix_s_parent(
    run, repo, tmp_path
):
    write(
        run,
        "verify.md",
        f"""
        STATUS: verified through Task 1

        ## Task 1

        #### V15 — the fix named in the section (minor, code)
        - Command: `grep -c gamma data.txt`
        - Output: `0`.
        - State: closed: fixed at `{repo.b[:7]}` and re-checked.

        #### V16 — two fixes in the log (minor, code)
        - Command: `grep -c gamma data.txt`
        - Output: `0`.

        ## The owner's amendments of 2026-10-23: V13, V14 closed at {repo.b[:7]}

        #### V13 — closed in the heading (minor, spec)
        - Command: `grep -c gamma data.txt`
        - Output: `0`.
        """,
    )
    write(
        run,
        "build-log.md",
        f"""
        STATUS: building Task 2
        Task 1: done — {repo.a[:7]}
        V16: fixed — {repo.c[:7]} — the later form.
        - V16: fixed — {repo.b[:7]} — the first form.
        """,
    )
    out = tmp_path / "out"
    assert replay(run, repo, out).returncode == 0
    for ident, fix in (("V13", repo.b), ("V15", repo.b), ("V16", repo.c)):
        t = task(out / ident)
        assert [g["sha"] for g in t["graders"]] == [repo.a, fix], ident
        assert grade(out / ident, "fix") == 0, ident


def test_a_judge_s_output_after_the_arrow_and_the_heading_s_sha_give_a_case_without_a_fix_grader(run, repo, tmp_path):
    write(
        run,
        "judge.md",
        f"""
        STATUS: judged

        #### J1 — {repo.a[:7]} leaves gamma out
        - Command: `grep -n beta data.txt` →
          `2:beta`, and nothing else.
        """,
    )
    out = tmp_path / "out"
    assert replay(run, repo, out).returncode == 0
    t = task(out / "J1")
    assert (t["fixture"]["sha"], t["recorded_output"], len(t["graders"])) == (repo.a, "2:beta", 1)
    assert (grade(out / "J1", "before"), grade(out / "J1", "fix")) == (0, 2)
    assert "no fix sha" in row(out, "J1")


def test_a_reused_heading_gets_its_own_folder_and_an_ellipsis_matches_any_text(run, repo, tmp_path):
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1

        ## Task 1

        #### V17 — alpha (minor, code)
        - Command: `grep -n alpha data.txt`
        - Output: `1:alpha`.

        #### V17, round 2 — alpha again (minor, code)
        - Command: `grep -n alpha data.txt`
        - Output: `1:al…a`.
        """,
    )
    write(run, "build-log.md", f"Task 1: done — {repo.a[:7]}\n")
    out = tmp_path / "out"
    assert replay(run, repo, out).returncode == 0
    assert task(out / "V17-2")["name"] == "replay-run-V17-2"
    assert (grade(out / "V17", "before"), grade(out / "V17-2", "before")) == (0, 0)


def test_no_command_of_a_finding_runs_without_try(run, repo, tmp_path):
    stubs = tmp_path / "bin"
    stubs.mkdir()
    for name in ("grep", "claude", "curl", "sed"):
        (stubs / name).write_text(f"#!/bin/sh\necho {name} >> {tmp_path / 'ran.log'}\n")
        (stubs / name).chmod(0o755)
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1

        ## Task 1

        #### V1 — data.txt has no gamma (minor, code)
        - Command: `grep -c gamma data.txt`
        - Output: `0`.
        """,
    )
    write(run, "build-log.md", f"Task 1: done — {repo.a[:7]}\nV1: fixed — {repo.b[:7]}\n")
    env = {**GIT_ENV, "PATH": f"{stubs}{os.pathsep}{GIT_ENV['PATH']}"}
    p = replay(run, repo, tmp_path / "out", env=env)
    assert p.returncode == 0, p.stderr
    assert not (tmp_path / "ran.log").exists()


def test_try_runs_each_grader_once_and_records_the_result(run, repo, tmp_path):
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1

        ## Task 1

        #### V1 — data.txt has no gamma (minor, code)
        - Command: `grep -c gamma data.txt`
        - Output: `0`.

        #### V19 — a recorded output that never appears (minor, code)
        - Command: `grep -c alpha data.txt`
        - Output: `7`.
        """,
    )
    write(run, "build-log.md", f"Task 1: done — {repo.a[:7]}\nV1: fixed — {repo.b[:7]}\nV19: fixed — {repo.b[:7]}\n")
    out = tmp_path / "out"
    p = replay(run, repo, out, "--try")
    assert p.returncode == 0, p.stderr
    assert "tried: before passes 1 of 2, fix passes 2 of 2; 1 of 2 cases replay (every grader passes)" in p.stdout
    assert row(out, "V1").endswith("| before passes, fix passes: replays |")
    assert row(out, "V19").endswith("| before fails, fix passes: does not replay |")
    assert not (out / ".tmp").exists()


def test_a_foreign_out_folder_is_refused_and_a_stale_case_is_removed(run, repo, tmp_path):
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1

        ## Task 1

        #### V1 — data.txt has no gamma (minor, code)
        - Command: `grep -c gamma data.txt`
        - Output: `0`.
        """,
    )
    write(run, "build-log.md", f"Task 1: done — {repo.a[:7]}\n")
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "keep.txt").write_text("x\n")
    p = replay(run, repo, foreign)
    assert (p.returncode, sorted(x.name for x in foreign.iterdir())) == (2, ["keep.txt"])
    assert "replay_cases.py" in p.stderr
    out = tmp_path / "out"
    assert replay(run, repo, out).returncode == 0 and (out / "V1" / "grader.sh").exists()
    (run / "verify.md").write_text((run / "verify.md").read_text().replace("- Output: `0`.\n", ""))
    assert replay(run, repo, out).returncode == 0
    assert not (out / "V1").exists() and "no recorded output" in row(out, "V1")
