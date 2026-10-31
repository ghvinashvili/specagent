"""Tests of findings_report.py on a synthetic run folder.

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
"""

import json
import pathlib
import subprocess
import sys
import textwrap

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "findings_report.py"
SEVERITIES = ("blocker", "major", "minor", "unknown")
CAUSES = ("code", "plan", "spec", "brief", "none")


def write(run: pathlib.Path, name: str, text: str) -> None:
    (run / name).write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def report(run: pathlib.Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(run), *extra], capture_output=True, text=True, timeout=30, check=False
    )


def data(run: pathlib.Path) -> dict:
    p = report(run, "--json")
    assert (p.returncode, p.stderr) == (0, "")
    return json.loads(p.stdout)


def matrix(cells: dict[tuple[str, str], int]) -> dict:
    return {c: {s: cells.get((c, s), 0) for s in SEVERITIES} for c in CAUSES}


@pytest.fixture
def run(tmp_path):
    """Every kind once or more, in the forms the live folders write them."""
    path = tmp_path / "run"
    path.mkdir()
    write(
        path,
        "critique.md",
        """
        STATUS: reviewing Task 3

        ## Shared sections

        ## Task 1

        #### C1 — a step names a file the plan never creates
        Text.

        ### Attack tests for Task 1

        #### A1 — Task 1: an empty file

        ## Task 2

        #### C2 — the test misses the second branch
        `test_two`: after line 12 (`"[[a]]",
        # a comment that wrapped to the line start`) add a case.

        #### A2 — Task 2: a file of one line

        ### Task 3 after `abc1234` (C2 applied)

        #### C3 — Task 3's step 2 contradicts step 4

        ## Task 2 (diff)

        #### R1 — (code) the built guard misses the empty list (minor)
        Fix: the test from A2.

        ## To check

        #### C4 — a doubt outside any task section
        """,
    )
    write(
        path,
        "critique-response.md",
        """
        STATUS: writing Task 4
        C1: applied — plan 1111111
        A1: applied — plan 1111111
        C2: applied — plan 2222222
        V2: applied — plan 3333333
        B2: applied — plan 3333333
        BK1: applied — plan 4444444
        P1: applied — the planner's own finding
        """,
    )
    write(
        path,
        "verify.md",
        """
        STATUS: verifying Task 3

        ## Task 1 — `1234567`

        #### V1 — a date-time without a zone passes (minor, code)
        Command: `pytest -q`

        #### V2 — the plan's step 3 asks for the wrong file
        Found by the run below.
        - Severity: major. Cause: (plan).

        #### B1 (the builder's report to the planner) — confirmed at 1234567
        The verifier's re-check of the builder's finding.

        ## Task 2 (7654321)

        #### V3 — a round that gains only a currency is a major "Amount" change
        Severity: blocker (the run stops)
        Cause (spec): the spec says otherwise.

        #### V4 — a log line without its time
        Neither a severity nor a cause.

        #### V1, round 2 — the fix still accepts a date without a zone (major, code)
        Text.

        ### Checked again

        #### V6 — a second item in the heading's list (code, minor)

        ## M6 — f7000bf (the main session's work)

        #### V5 — the summary counts a reused id twice (major, (plan))
        Text.
        """,
    )
    write(
        path,
        "verify-kb.md",
        """
        STATUS: waiting for Task 5

        ## Task 4

        #### VK1 — a name cut at a hyphen confirms the wrong place
        - Severity: minor. Cause: (code).
        """,
    )
    write(
        path,
        "build-log.md",
        """
        R1: fixed — 7654321
        STATUS: building Task 3
        Task 1: done — abc1234
        V1: fixed — abc1234
        - V3: fixed — def5678
        V6: fixed — def5678
        B1: sent to planner — the plan's step 2 names a missing file
        B2: sent to planner — the plan's step 5 contradicts the spec
        B3: fixed — my own test missed a branch; fixed at abc1234
        M1: fixed — abc1234
        - O1: fixed — def5678
        VK1: fixed — 9999999
        """,
    )
    write(
        path,
        "build-log-kb.md",
        """
        STATUS: waiting for Task 5
        BK1: sent to planner — the KB plan's step 1
        """,
    )
    write(
        path,
        "judge.md",
        """
        STATUS: done

        ## Task 1 — acceptance and requirements

        #### J1 — the report misses the owner's second question
        - Severity: major. Cause: (plan).

        #### J2 — a test name says the opposite of its assertion
        - Severity: minor. Cause: (code).

        ## Task 2 — the owner's decisions

        #### J3 — a decision is recorded twice
        Text without a severity.
        """,
    )
    write(
        path,
        "lessons.md",
        """
        # Lessons

        ## Read first
        1. M1 (the main session's finding, 2026-10-20): read the build log by id.
        2. M2 (2026-10-21): the summary is in English.
        3. O1 (the owner, 2026-10-22): no network.
        """,
    )
    return path


def test_per_kind_total_answered_open(run):
    kinds = data(run)["kinds"]
    assert kinds == {
        "C": {"total": 4, "answered": 2, "open": 2},
        "A": {"total": 2, "answered": 1, "open": 1},
        "R": {"total": 1, "answered": 1, "open": 0},
        # B1 sent and unanswered is open; B2 sent and answered; B3 the builder's own, fixed by itself.
        "B": {"total": 3, "answered": 2, "open": 1},
        "BK": {"total": 1, "answered": 1, "open": 0},
        # V1 and V6 answered in the build log, V3 by its list item, V2 by the planner.
        "V": {"total": 6, "answered": 4, "open": 2},
        "VK": {"total": 1, "answered": 1, "open": 0},
        "M": {"total": 2, "answered": 1, "open": 1},
        "O": {"total": 1, "answered": 1, "open": 0},
        "J": {"total": 3, "answered": 0, "open": 3},
        "P": {"total": 1, "answered": 1, "open": 0},
    }


def test_verifier_findings_by_cause_and_severity(run):
    d = data(run)
    # V1's severity and cause are its first section's (minor, code), not its round 2's (major, code); V3's heading
    # says "a major" in prose, its body says blocker; V5's cause is nested, `(major, (plan))`.
    assert d["causes"]["V"] == matrix(
        {("code", "minor"): 2, ("plan", "major"): 2, ("spec", "blocker"): 1, ("none", "unknown"): 1}
    )
    assert d["causes"]["VK"] == matrix({("code", "minor"): 1})
    assert {i: (f["severity"], f["cause"]) for i, f in d["findings"].items()} == {
        "V1": ("minor", "code"),
        "V2": ("major", "plan"),
        "V3": ("blocker", "spec"),
        "V4": ("unknown", "none"),
        "V5": ("major", "plan"),
        "V6": ("minor", "code"),
        "VK1": ("minor", "code"),
        "J1": ("major", "plan"),
        "J2": ("minor", "code"),
        "J3": ("unknown", "none"),
    }
    assert d["findings"]["V4"]["line"] == 21 and d["findings"]["V4"]["file"] == "verify.md"
    assert d["reused"] == ["V1"]


def test_a_brief_cause_is_counted_in_its_own_row(tmp_path):
    """R8 (specs/003-pipeline-economy): a run without a planner tags a finding `(brief)`, in the heading or after
    `Cause`; it is a cause of its own, not `none`, and the other causes count as before."""
    path = tmp_path / "run"
    path.mkdir()
    write(
        path,
        "verify.md",
        """
        STATUS: verified through Task 1
        ## Task 1
        #### V1 — the heading's cause (minor, brief)
        #### V2 — the body's cause
        Severity: major. Cause: (brief): the assignment contradicts the spec.
        #### V3 — the code
        Severity: minor. Cause: (code).
        """,
    )
    d = data(path)
    assert d["causes"]["V"] == matrix({("brief", "minor"): 1, ("brief", "major"): 1, ("code", "minor"): 1})
    assert {i: f["cause"] for i, f in d["findings"].items()} == {"V1": "brief", "V2": "brief", "V3": "code"}
    assert "| brief | 0 | 1 | 1 | 0 | 2 |" in report(path).stdout.splitlines()


def test_judge_findings_by_severity(run):
    assert data(run)["severity"]["J"] == {"blocker": 0, "major": 1, "minor": 1, "unknown": 1}


def test_counts_per_task_section(run):
    # `### Attack tests for Task 1` stays in Task 1; a wrapped line `# a comment …` in C2's body is no heading, A2
    # stays in Task 2; `### Task 3 …` inside `## Task 2` is Task 3; `### Checked again` stays in Task 2; `## To check`
    # and `## M6 …` are outside a task; the verifier's `#### B1` re-check and V1's round 2 add nothing.
    assert data(run)["tasks"] == {
        "1": {"C": 1, "A": 1, "R": 0, "V": 2, "open": 0},
        "2": {"C": 1, "A": 1, "R": 1, "V": 3, "open": 2},
        "3": {"C": 1, "A": 0, "R": 0, "V": 0, "open": 1},
        "none": {"C": 1, "A": 0, "R": 0, "V": 1, "open": 2},
    }


def test_escape_table(run):
    d = data(run)
    assert d["escape"] == [
        {"stage": "critic", "kinds": ["C", "A", "R"], "count": 7, "share": 29.2},
        {"stage": "builder's own", "kinds": ["B", "BK"], "count": 4, "share": 16.7},
        {"stage": "verifier", "kinds": ["V", "VK"], "count": 7, "share": 29.2},
        {"stage": "main session", "kinds": ["M"], "count": 2, "share": 8.3},
        {"stage": "judge", "kinds": ["J"], "count": 3, "share": 12.5},
        {"stage": "owner after the build", "kinds": ["O"], "count": 1, "share": 4.2},
    ]
    assert d["escapes"] == {"count": 4, "all": 24}
    assert d["not_in_table"] == {"P": 1}


def test_markdown_output(run):
    p = report(run)
    assert (p.returncode, p.stderr) == (0, "")
    out = p.stdout
    for line in (
        "| C | 4 | 2 | 2 |",
        "| B | 3 | 2 | 1 |",
        "| all | 25 | 15 | 10 |",
        "| plan | 0 | 2 | 0 | 0 | 2 |",
        "| total | 1 | 2 | 2 | 1 | 6 |",
        "| Task 2 | 1 | 1 | 1 | 3 | 2 |",
        "| no task section | 1 | 0 | 0 | 1 | 2 |",
        "| critic | C + A + R | 7 | 29.2% |",
        "| all | | 24 | 100% |",
        "escapes past the pipeline's gates: J + O = 4 of 24",
    ):
        assert line in out.splitlines(), line
    assert "unknown severity: V4 (verify.md:21)" in out
    assert "J3 (judge.md:13)" in out
    assert "reused headings, counted once: V1" in out


def test_empty_folder(tmp_path):
    d = data(tmp_path)
    assert all(v == {"total": 0, "answered": 0, "open": 0} for v in d["kinds"].values())
    assert d["escapes"] == {"count": 0, "all": 0}
    assert all(row["share"] == 0.0 for row in d["escape"])
    assert d["tasks"] == {}
    p = report(tmp_path)
    assert "escapes past the pipeline's gates: J + O = 0 of 0" in p.stdout.splitlines()


def test_missing_folder(tmp_path):
    p = report(tmp_path / "nowhere")
    assert p.returncode == 2 and p.stdout == "" and "nowhere" in p.stderr
