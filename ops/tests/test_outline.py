"""outline.py (spec B2): the layered outline of a large live file, so an agent reads only the lines it needs. Its line
numbers are those of grep -n and sed: a line ends at "\\n" only, never at a U+2028 or U+2029 inside it (an earlier plan
read with str.splitlines() put the outline 8-10 lines ahead).

  python3 -m pytest -q -p no:cacheprovider ops/tests/test_outline.py
"""

import pathlib
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "outline.py"
# Line 3 holds a line separator and a paragraph separator: 19 lines for grep -n and sed, 21 for str.splitlines().
PLAN = (
    "# Plan\n\nIntro" + chr(0x2028) + "text" + chr(0x2029) + "more.\n\n## Task 1 — Setup\n\n- [ ] **Step 1: copy**\n\n"
    "```bash\n## not a heading, inside a fence\n```\n\n- [ ] **Step 2: test**\n\n## Task 2 — Build\n\n"
    "1. **Decision one**\n\nWhy.\n"
)


def outline(tmp: pathlib.Path, *args: str) -> list[str]:
    """Write PLAN to tmp/plan.md, run outline.py on it with args and return the printed lines."""
    plan = tmp / "plan.md"
    plan.write_text(PLAN, encoding="utf-8")
    out = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "plan.md", *args], cwd=tmp, capture_output=True, text=True, check=False
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.splitlines()


def test_the_top_layer_names_each_heading_with_its_line_range(tmp_path):
    lines = outline(tmp_path)
    assert lines[0] == "plan.md: 19 lines, 0 KB, 6 headings"
    assert "in: # Plan  [lines 1-19, 0 KB, 5 sub-headings]" in lines
    assert "## Task 1 — Setup  [lines 5-14, 0 KB, 2 sub-headings]" in lines
    assert "## Task 2 — Build  [lines 15-19, 0 KB, 1 sub-headings]" in lines
    assert not [line for line in lines if "not a heading" in line]  # a heading inside a code fence is text


def test_a_line_separator_inside_a_line_moves_no_line_number(tmp_path):
    assert PLAN.count("\n") == 19 and len(PLAN.splitlines()) == 21
    assert PLAN.split("\n")[14] == "## Task 2 — Build"  # line 15 for grep -n and sed
    lines = outline(tmp_path, "--show", "Task 2")
    assert lines[1] == "show: ## Task 2 — Build  [lines 15-19, 0 KB, 1 sub-headings]"
    assert lines[2:] == ["15: ## Task 2 — Build", "16: ", "17: 1. **Decision one**", "18: ", "19: Why."]


def test_under_and_grep_go_down_one_layer(tmp_path):
    under = outline(tmp_path, "--under", "Task 1")
    assert under[1] == "under: ## Task 1 — Setup  [lines 5-14, 0 KB, 2 sub-headings]"
    assert under[-2:] == ["- step Step 1: copy  [lines 7-12, 0 KB]", "- step Step 2: test  [lines 13-14, 0 KB]"]
    assert outline(tmp_path, "--grep", "decision")[1:] == ["  - 1. Decision one  [lines 17-19, 0 KB]"]
