"""Tests of audit_read_first.py on a synthetic run folder.

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
"""

import hashlib
import json
import pathlib
import re
import subprocess
import sys
import textwrap

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "audit_read_first.py"
TODAY = "2026-10-26"
LESSONS = """
    # Lessons: read before each task

    ## Read first (main session, 2026-10-20)
    Every role reads this section before each task.
    0. Task size (owner, 2026-10-25 09:20 ET). A task is at most 1,500 lines; Task 14 took 4.5 hours.
       Planner: split the work.
    1. The vault is read only (owner, 2026-10-25). Use `--under "Task 2"` to go down a layer; the hold of a
       rule is no marker, nor is a rule restated by the owner.
    2. Task 5 is on HOLD until the owner decides (main session, 2026-10-24).

    3. M3 RESTATED (main session, 2026-10-26): build it after item 6.
    4. The old cap of 600k (owner, 2026-10-10): superseded by the 200k cap.
       - Builder: keep the 200k cap.
    5. The plan text of built tasks is no longer rewritten to match fixes (owner, 2026-10-24).
    6. Withdrawn: the nightly check (owner, 2026-10-23).
    7. The builder runs Task 2 and Task 9 in one session (owner, 2026-10-24).
    8. Main session's O1 and M3 work: check the chips at 1440 px (owner, 2026-10-24).
    9. M5 waits for the planner (owner, 2026-10-19).
    10. Hand over at the cap: write the note last, once, after everything else is saved and committed, in English
        (owner, 2026-10-12; measured 2026-10-01).
    11. Hand over at the cap: write the note last, once, after everything else is saved and committed (owner, 2026-10-25).
    12. A rule with no date of its own, valid until 2026-11-30.

    ## Known error classes
    1. A HOLD outside the section is not read.
    """
BUILD_LOG = """
    STATUS: building Task 9
    # Build log
    Task 2: done — abc1234 — the first task
    - Task 5: done — def5678 — a list item, as an earlier run writes it
    M3: fixed — 1234abc — the H1 check
    - O1: fixed in code — 5678def — the chips wrap
    M5: waits for the planner
    """
FLAGGED_LINE = "Flagged (drop, merge or keep each after review; text verbatim, numbers kept):"


def write(run: pathlib.Path, name: str, text: str) -> None:
    (run / name).write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def audit(run: pathlib.Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(run), *extra], capture_output=True, text=True, timeout=30, check=False
    )


def data(run: pathlib.Path, today: str = TODAY) -> dict:
    p = audit(run, "--json", "--today", today)
    assert (p.returncode, p.stderr) == (0, "")
    return json.loads(p.stdout)


def flags(run: pathlib.Path, today: str = TODAY) -> dict[int, list[str]]:
    return {i["n"]: i["flags"] for i in data(run, today)["items"]}


@pytest.fixture
def run(tmp_path):
    path = tmp_path / "run"
    path.mkdir()
    write(path, "lessons.md", LESSONS)
    write(path, "build-log.md", BUILD_LOG)
    return path


def lessons_lines(run: pathlib.Path) -> list[str]:
    return (run / "lessons.md").read_text(encoding="utf-8").split("\n")


def test_items_of_the_section_only(run):
    d = data(run)
    assert [i["n"] for i in d["items"]] == list(range(13))  # not the preamble, not `1.` of Known error classes
    spans = {i["n"]: (i["start"], i["end"]) for i in d["items"]}
    assert spans[0] == (5, 6) and spans[2] == (9, 9) and spans[3] == (11, 11) and spans[4] == (12, 13)
    assert spans[10] == (19, 20) and spans[12] == (22, 22)
    assert d["section"] == {
        "heading": "## Read first (main session, 2026-10-20)",
        "start": 3,
        "end": 22,
        "date": "2026-10-20",
    }
    assert d["total"]["items"] == 13 and d["total"]["lines"] == 17


def test_marker_words(run):
    f = flags(run)
    assert f[2][0] == "HOLD" and f[3][0] == "RESTATED"
    assert f[4][0] == "superseded" and f[5] == ["no longer"] and f[6] == ["withdrawn"]  # `Withdrawn:` too
    assert f[1] == []  # a lowercase `hold` and `restated` are prose, no marker


def test_done_work(run):
    f = flags(run)
    assert "done: Task 5 (build-log.md:4)" in f[2]  # a `- Task N: done — <sha>` list item counts
    assert "done: M3 (build-log.md:5)" in f[3]
    assert f[8] == ["done: O1 (build-log.md:6), M3 (build-log.md:5)"]  # `O1: fixed in code` is fixed
    assert f[7] == []  # Task 2 is done, Task 9 is not: the item still names open work
    assert f[9] == []  # M5 has a line, but not `M5: fixed`
    assert f[0] == []  # Task 14 is not done
    # Task 2 in item 1 sits in a code span (an example in a command): no work the item names


def test_similar_pairs(run):
    d = data(run)
    assert [p["items"] for p in d["pairs"]] == [[10, 11]]
    assert d["pairs"][0]["ratio"] > 0.6
    f = flags(run)
    assert re.fullmatch(r"similar to 11 \(0\.\d\d\)", f[10][0]) and re.fullmatch(r"similar to 10 \(0\.\d\d\)", f[11][0])


def test_old_items(run):
    d = data(run)
    items = {i["n"]: i for i in d["items"]}
    assert items[4]["flags"][-1] == "old: 2026-10-10, 16 days"
    assert items[10]["date"] == "2026-10-12" and items[10]["flags"][-1] == "old: 2026-10-12, 14 days"  # the newest date
    assert (items[9]["date"], items[9]["age"], items[9]["flags"]) == ("2026-10-19", 7, [])  # 7 days is not over 7
    # Item 12 names only a future date: the heading's date stands for it.
    assert (items[12]["date"], items[12]["date_from"], items[12]["flags"]) == ("2026-10-20", "heading", [])
    later = {i["n"]: i for i in data(run, "2026-10-30")["items"]}
    assert later[12]["flags"] == ["old: 2026-10-20 (heading), 10 days"]


def test_proposal_keeps_every_item_verbatim(run):
    d = data(run)
    p = audit(run, "--today", TODAY)
    assert p.returncode == 0
    out = p.stdout.split("\n")
    start = out.index('## Proposed compacted "Read first"')
    fence_at = next(k for k in range(start, len(out)) if out[k].startswith("```"))
    fence = re.match(r"`+", out[fence_at]).group(0)
    proposal = out[fence_at + 1 : out.index(fence, fence_at + 1)]
    lines = lessons_lines(run)
    items = {i["n"]: i for i in d["items"]}

    def text(n: int) -> list[str]:
        return lines[items[n]["start"] - 1 : items[n]["end"]]

    def marked(n: int) -> list[str]:
        first = re.sub(
            r"^(\d+\.\s+)", lambda m: m.group(1) + "[flag: " + "; ".join(items[n]["flags"]) + "] ", text(n)[0]
        )
        return [first] + text(n)[1:]

    expected = lines[2:4]  # the heading and the preamble
    for n in (0, 1, 7, 9, 12):
        expected += text(n)
    expected += ["", FLAGGED_LINE]
    for n in (2, 3, 4, 5, 6, 8, 10, 11):
        expected += marked(n)
    assert proposal == expected


def test_markdown_report(run):
    p = audit(run, "--today", TODAY)
    assert (p.returncode, p.stderr) == (0, "")
    assert "| 2 | 9 | HOLD; done: Task 5 (build-log.md:4) | Task 5 is on HOLD" in p.stdout
    assert "| 4 | 12-13 | superseded; old: 2026-10-10, 16 days |" in p.stdout
    assert "Flagged: 8 of 13 items, 10 of 17 item lines" in p.stdout
    assert "| 0 |" not in p.stdout  # an unflagged item has no row


def test_nothing_flagged(run):
    write(run, "lessons.md", "## Read first (owner, 2026-10-25)\n1. A rule.\n2. Another one, for every role.\n")
    p = audit(run, "--today", TODAY)
    assert (p.returncode, p.stderr) == (0, "")
    assert "No item is flagged." in p.stdout and "| item |" not in p.stdout
    assert "Flagged: 0 of 2 items" in p.stdout and FLAGGED_LINE not in p.stdout


def test_never_edits(run):
    def snapshot() -> dict[str, str]:
        return {str(f.relative_to(run)): hashlib.sha256(f.read_bytes()).hexdigest() for f in run.rglob("*")}

    before = snapshot()
    assert audit(run, "--today", TODAY).returncode == 0 and audit(run, "--json").returncode == 0
    assert snapshot() == before


def test_missing_section_or_folder(run, tmp_path):
    write(run, "lessons.md", "# Lessons\n\n## Lessons from this plan\n1. A lesson.\n")
    p = audit(run)
    assert p.returncode == 1 and "no `## Read first` section" in p.stderr
    p = audit(tmp_path / "missing")
    assert p.returncode == 2 and "lessons.md" in p.stderr
