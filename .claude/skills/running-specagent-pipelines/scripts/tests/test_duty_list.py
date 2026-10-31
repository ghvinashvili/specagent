"""Tests of duty_list.py on a synthetic plan folder.

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_duty_list.py
"""

import ast
import datetime
import importlib.util
import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "duty_list.py"
HEADER = "# Duty list (spec 5.1.2): each duty is ticked with its date -u time when done; the monitor ticks the merges."
INDEX = """\
# Plan index
Prose: the main session merges `Merged: main->plan at <sha>` first.

## Task order
| Task | title | planner | builder | depends_on | files |
|---|---|---|---|---|---|
| 1 | `a|b` one | a | b | — | `x.py` |
| 2 | two | b | a | 1 | `y.py` |
| 3 | three | c | a | 2 | `z.py` |
| 4 | four | d | b | 2, 3 | `w.py` |
| 5 | five | a | a | 1-4 (`Merged: a+b`) | `v.py` |

Placed already: `Merged: a+b at <sha>`; not placed: `Merged: a→c at <sha>` and `Merged: a->c at <sha>`.
"""
TASK_02 = """\
# Task 2 — two
Steps:
Request point: COPY-REQUEST — copy the vault form from the main checkout
    assert "COPY-REQUEST: x" in out
- Request point: FF-REQUEST — not at a line start, so not a point
Request point: FF-REQUEST — fast-forward the plan branch
Request point: COPY-REQUEST — a second COPY point of the same task counts once
"""
DUTIES = [
    "Merged: b->a — blocks Task 2 (builder a) — due when Task 1 done — 00-index.md:8",
    "Merged: a->b — blocks Task 4 (builder b) — due when Tasks 2, 3 done — 00-index.md:10",
    "Merged: a+b — blocks Task 5 (builder a) — due when Tasks 1-4 done — 00-index.md:11",
    "Merged: main->plan — blocks: see 00-index.md:2 (a marker the task table does not place)",
    "Merged: a→c — blocks: see 00-index.md:13 (a marker the task table does not place)",
    "COPY-REQUEST point — blocks Task 2 (builder a) — task-02.md:3",
    "FF-REQUEST point — blocks Task 2 (builder a) — task-02.md:6",
    "CHECKOUT-REQUEST point — blocks Task 5 (builder a) — task-05.md:2",
    "judge approval — blocks the judge — due when every record's STATUS is final",
]
TABLE = """\
| Task | title | planner | builder | depends_on | files |
|---|---|---|---|---|---|
| 1 | one | a | a | — | x |
| 2 | two | b | b | — | y |
| 3 | three | c | c | — | z |
| 4 | four | b | b | {cell} | w |
"""
TWO_LANES = [
    "- [ ] D1 Merged: a->b — blocks Task 4 (builder b) — due when Task 1 done — 00-index.md:6",
    "- [ ] D2 Merged: c->b — blocks Task 4 (builder b) — due when Task 3 done — 00-index.md:6",
    f"- [ ] D3 {DUTIES[-1]}",
]


@pytest.fixture
def plan(tmp_path):
    path = tmp_path / "plan"
    path.mkdir()
    (path / "00-index.md").write_text(INDEX, encoding="utf-8")
    (path / "task-02.md").write_text(TASK_02, encoding="utf-8")
    (path / "task-04.md").write_text(
        "# Task 4 — four\nThe builder writes `COPY-REQUEST: <path>` on need.\n"
        "````python\nTASK = '''\n```bash\nRequest point: FF-REQUEST — a test's fixture, inside a fence\n'''\n````\n"
    )
    (path / "task-05.md").write_text("# Task 5 — five\nRequest point: CHECKOUT-REQUEST — check out the merge\n")
    return path


def dl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True, timeout=30, check=False
    )


def module():
    spec = importlib.util.spec_from_file_location("duty_list", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def minutes() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M UTC")


def test_extract_prints_merges_prose_markers_points_and_the_judge(plan):
    p = dl("extract", str(plan))
    assert (p.returncode, p.stderr) == (0, "")
    assert p.stdout.splitlines() == [f"- [ ] D{k} {text}" for k, text in enumerate(DUTIES, 1)]


def test_extract_out_creates_the_file_then_appends_only_new_duties(plan, tmp_path):
    out = tmp_path / "run" / "_control" / "duties.md"
    before = minutes()
    p = dl("extract", str(plan), "--out", str(out))
    after = minutes()
    assert (p.returncode, p.stdout, p.stderr) == (0, f"{out}: 9 new duties\n", "")
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[:2] == [HEADER, ""]
    assert lines[2] in {f"Extracted {t} from {plan / '00-index.md'}: 9 new duties." for t in (before, after)}
    assert lines[3:] == [f"- [ ] D{k} {text}" for k, text in enumerate(DUTIES, 1)]
    first = out.read_bytes()
    p = dl("extract", str(plan), "--out", str(out))
    assert (p.returncode, p.stdout, out.read_bytes()) == (0, f"{out}: 0 new duties\n", first)
    out.write_text(out.read_text(encoding="utf-8").replace("- [ ] D1 ", "- [x] 20:01 UTC (by hand) D1 "))
    moved = INDEX.replace("## Task order\n", "## Task order\n\n").replace(
        "| 5 | five | a | a | 1-4 (`Merged: a+b`) | `v.py` |\n",
        "| 5 | five | a | a | 1-4 (`Merged: a+b`) | `v.py` |\n| 6 | six | d | b | 5 | `u.py` |\n",
    )
    (plan / "00-index.md").write_text(moved, encoding="utf-8")
    p = dl("extract", str(plan), "--out", str(out))
    assert (p.returncode, p.stdout) == (0, f"{out}: 1 new duties\n")
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[3] == "- [x] 20:01 UTC (by hand) D1 " + DUTIES[0]
    assert lines[-2].startswith("Extracted ") and lines[-2].endswith(": 1 new duties.")
    assert lines[-1] == "- [ ] D10 Merged: a->b — blocks Task 6 (builder b) — due when Task 5 done — 00-index.md:13"
    assert len(lines) == 3 + 9 + 2


def test_tick_writes_the_utc_time_and_the_evidence(plan, tmp_path):
    out = tmp_path / "duties.md"
    assert dl("extract", str(plan), "--out", str(out)).returncode == 0
    before = minutes()
    p = dl("tick", str(out), "D2", "lessons.md:4, abc1234")
    after = minutes()
    assert (p.returncode, p.stdout, p.stderr) == (0, "ticked D2\n", "")
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[4] in {f"- [x] {t} (lessons.md:4, abc1234) D2 {DUTIES[1]}" for t in (before, after)}
    assert lines[3] == f"- [ ] D1 {DUTIES[0]}" and lines[5] == f"- [ ] D3 {DUTIES[2]}"
    when = lines[4][len("- [x] ") : lines[4].index(" UTC") + len(" UTC")]
    p = dl("tick", str(out), "D2", "again")
    assert (p.returncode, p.stdout, p.stderr) == (2, "", f"{out}: D2 is ticked already ({when})\n")
    p = dl("tick", str(out), "D99", "nothing")
    assert (p.returncode, p.stderr) == (2, f"{out}: no D99\n")


def test_a_plan_without_a_task_table_exits_2(tmp_path):
    (tmp_path / "00-index.md").write_text("# Plan\n| a | b |\n|---|---|\n| 1 | 2 |\n", encoding="utf-8")
    p = dl("extract", str(tmp_path))
    assert (p.returncode, p.stdout) == (2, "")
    assert p.stderr == f"{tmp_path / '00-index.md'}: no task table with Task, builder and depends_on columns\n"


def test_parse_duties_reads_hand_written_lines_too():
    text = "# Duties\n- [x] 19:54 UTC (merged by hand) D0 Merged: main->plan\n- [ ] D3 COPY-REQUEST point — x\n- [x] D4 y\n"
    assert module().parse_duties(text) == [
        {
            "n": 0,
            "done": True,
            "when": "19:54 UTC",
            "evidence": "merged by hand",
            "text": "Merged: main->plan",
            "line": 2,
        },
        {"n": 3, "done": False, "when": None, "evidence": None, "text": "COPY-REQUEST point — x", "line": 3},
        {"n": 4, "done": True, "when": None, "evidence": None, "text": "y", "line": 4},
    ]


def test_numbers_and_span():
    mod = module()
    assert mod.numbers("1-3, 5 (`Merged: a+b at 90ab`)") == [1, 2, 3, 5]
    assert mod.numbers("—") == []
    assert [mod.span(n) for n in ([2], [2, 3, 6, 8], list(range(1, 11)), [1, 2, 3, 5, 6])] == [
        "Task 2",
        "Tasks 2, 3, 6, 8",
        "Tasks 1-10",
        "Tasks 1-3, 5, 6",
    ]
    assert mod.norm("b→a") == "b->a"


def test_two_markers_in_one_cell_each_wait_for_the_tasks_of_their_own_lane(tmp_path):
    cell = "1, 2, 3 (`Merged: a->b` after 1, `Merged: c->b` after 3)"
    (tmp_path / "00-index.md").write_text(TABLE.format(cell=cell), encoding="utf-8")
    assert module().numbers(cell) == [1, 2, 3]
    p = dl("extract", str(tmp_path))
    assert (p.returncode, p.stdout.splitlines(), p.stderr) == (0, TWO_LANES, "")


def test_implied_merges_from_two_other_lanes_give_one_duty_per_lane(tmp_path):
    (tmp_path / "00-index.md").write_text(TABLE.format(cell="1, 2, 3"), encoding="utf-8")
    p = dl("extract", str(tmp_path))
    assert (p.returncode, p.stdout.splitlines(), p.stderr) == (0, TWO_LANES, "")


def test_every_function_is_under_50_lines():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    long = [
        (f.name, f.end_lineno - f.lineno + 1)
        for f in ast.walk(tree)
        if isinstance(f, ast.FunctionDef) and f.end_lineno - f.lineno + 1 >= 50
    ]
    assert long == []
