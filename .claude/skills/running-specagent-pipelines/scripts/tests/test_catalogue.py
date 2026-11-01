"""Tests of scripts/manager/catalogue.py (manager-build Task 1; spec 3 and 4.6-4.7): the catalogue in bytes and tokens,
one role's start-up prefix against the bounds of spec 3.8, and the domain section of every brief; and
scripts/manager/README.md documents every script of its folder.

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_catalogue.py
"""

import importlib.util
import re
import subprocess
import sys

import pytest
from transcript_home import SCRIPTS

sys.dont_write_bytecode = True
MANAGER = SCRIPTS / "manager"
CHECKOUT = SCRIPTS.parents[3]
SKILL_REL = ".claude/skills/running-specagent-pipelines"
SPEC = importlib.util.spec_from_file_location("catalogue", MANAGER / "catalogue.py")
catalogue = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = catalogue  # dataclasses look string annotations up in sys.modules
SPEC.loader.exec_module(catalogue)

A = ".claude/ecc/agents/a.md"  # 40 lines in the fixture
B = ".claude/ecc/agents/b.md"  # 30 lines
TS = ".claude/skills/python-testing/SKILL.md"
SPEC_OK = f"Spec: {A}:1-30, {B}:5-20 — the checks of the role"  # 30 + 16 = 46 lines
SKILLS_OK = f"Skills: {TS} (before the first test)"
SLOT = "<!-- launch: paste the Spec ranges here -->"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run(*args):
    command = [sys.executable, "-I", str(MANAGER / "catalogue.py"), *map(str, args)]
    return subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)


def brief(*section):
    lines = "".join(f"{x}\n" for x in section)
    return f"# Planner\n\n## Work\nWrite the plan.\n\n## Domain checklist and skills\n{lines}\n## Done when\nAll is written.\n"


@pytest.fixture
def checkout(tmp_path):
    write(tmp_path / A, "a\n" * 40)
    write(tmp_path / B, "b\n" * 30)
    for name in ("python-testing", "python-patterns", "k1", "k2", "k3", "k4", "k5", "k6"):
        write(tmp_path / ".claude" / "skills" / name / "SKILL.md", f"---\nname: {name}\n---\n")
    return tmp_path


@pytest.mark.parametrize(("size", "expected"), [(0, 0), (4, 1), (5, 1), (6, 2), (7, 2), (10, 3)])
def test_tokens_are_bytes_over_four_rounded_half_up(size, expected):
    # Spec 3.1. Floor is red on 6 (1), ceiling on 5 (2), round() on 10 (2, half to even).
    assert catalogue.tokens(size) == expected


@pytest.mark.parametrize(
    ("count", "expected"), [(10_000, "within"), (10_001, "near"), (13_000, "near"), (13_001, "over")]
)
def test_the_verdict_holds_the_bounds_of_spec_3_8(count, expected):
    assert catalogue.verdict(count) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("---\nname: k\ndescription: Use when testing.\n---\nbody\n", "description: Use when testing.\n"),
        ("---\nname: k\n---\ndescription: in the body\n", ""),
        ("description: no frontmatter\n", ""),
        ("---\nname: k\ndescription: never closed\n", ""),
        ("---\nname: k\ndescription: first\ndescription: second\n---\n", "description: first\n"),
    ],
)
def test_the_description_line_comes_from_the_frontmatter_only(text, expected):
    assert catalogue.description_line(text) == expected


def test_measure_lists_each_kind_sorted_and_skips_readmes_and_skills_without_a_description(tmp_path):
    write(tmp_path / ".claude/agents/b.md", "b" * 7)
    write(tmp_path / ".claude/agents/a.md", "a" * 5)
    write(tmp_path / "docs/roles/types/a.md", "c" * 3)
    write(tmp_path / SKILL_REL / "example/planner-assignment.md", "p" * 11)
    write(tmp_path / SKILL_REL / "example/README.md", "r" * 13)
    write(tmp_path / SKILL_REL / "example/agents.json", "{}")
    write(tmp_path / ".claude/skills/k/SKILL.md", "---\nname: k\ndescription: dd\n---\nbody\n")  # 4+8+16+4+5 = 37
    write(tmp_path / ".claude/skills/n/SKILL.md", "no frontmatter\n")  # 15
    write(tmp_path / ".claude/ecc/agents/e.md", "e" * 17)
    write(tmp_path / ".claude/ecc/agents/README.md", "r" * 19)
    assert [(i.kind, i.name, i.path, i.size) for i in catalogue.measure(tmp_path)] == [
        ("type", "a", ".claude/agents/a.md", 5),
        ("type", "b", ".claude/agents/b.md", 7),
        ("contract", "a", "docs/roles/types/a.md", 3),
        ("brief", "planner-assignment", f"{SKILL_REL}/example/planner-assignment.md", 11),
        ("skill", "k", ".claude/skills/k/SKILL.md", 37),
        ("skill", "n", ".claude/skills/n/SKILL.md", 15),
        ("description", "k", ".claude/skills/k/SKILL.md", 16),  # "description: dd\n"
        ("ecc", "e", ".claude/ecc/agents/e.md", 17),
    ]


def test_the_table_groups_by_kind_totals_from_bytes_and_marks_half_use_items_over_2500_tokens():
    # Not in KINDS order on input. Totals from bytes: 10 -> 3 tokens, not 1 + 1. 10,001 bytes = 2,500 tokens is not
    # over (`>=` is red); 10,002 = 2,501 is.
    item = catalogue.Item
    items = [
        item("ecc", "e", ".claude/ecc/agents/e.md", 10_002),
        item("type", "a", ".claude/agents/a.md", 5),
        item("skill", "k", ".claude/skills/k/SKILL.md", 10_001),
        item("type", "b", ".claude/agents/b.md", 5),
    ]
    head = "| name | bytes | tokens | half-use |\n| --- | ---: | ---: | --- |\n"
    assert catalogue.table(items) == (
        f"### type (2)\n{head}| a | 5 | 1 |  |\n| b | 5 | 1 |  |\n| total | 10 | 3 |  |\n\n"
        f"### skill (1)\n{head}| k | 10001 | 2500 |  |\n| total | 10001 | 2500 |  |\n\n"
        f"### ecc (1)\n{head}| e | 10002 | 2501 | over |\n| total | 10002 | 2501 |  |\n"
    )


def test_the_prefix_counts_files_whole_skills_by_their_description_line_and_ecc_texts_whole(tmp_path):
    path = write(tmp_path / "run" / "planner-assignment.md", "x" * 40_000)
    description = "description: " + "d" * 86 + "\n"  # 13 + 86 + 1 = 100 bytes
    write(tmp_path / ".claude/skills/k/SKILL.md", "---\nname: k\n" + description + "---\n" + "b" * 12_000)
    write(tmp_path / ".claude/ecc/agents/e.md", "e" * 2_000)
    # 40,000 + 100 + 2,000 = 42,100 bytes = 10,525 tokens: near. The whole skill (12,116 bytes) would give 13,529: over.
    assert catalogue.prefix(tmp_path, [path], ["k"], ["e"]) == {
        "bytes": 42_100,
        "tokens": 10_525,
        "verdict": "near",
        "parts": [(str(path), 40_000), ("k (description)", 100), (".claude/ecc/agents/e.md", 2_000)],
    }


@pytest.mark.parametrize(
    ("size", "tokens", "verdict", "code"), [(52_000, 13_000, "near", 0), (52_004, 13_001, "over", 1)]
)
def test_the_prefix_command_prints_each_part_and_fails_only_over_13000_tokens(tmp_path, size, tokens, verdict, code):
    path = write(tmp_path / "brief.md", "x" * size)
    result = run("prefix", path, "--checkout", tmp_path)
    assert result.stdout == f"{size}\t{path}\ntotal: {size} bytes, {tokens} tokens, {verdict}\n"
    assert result.returncode == code


def test_parse_spec_and_parse_skills_return_the_parts_of_a_line():
    assert catalogue.parse_spec("Spec: docs/a.md:1-30, docs/b.md:5-20 — why — and more") == {
        "ranges": [("docs/a.md", 1, 30), ("docs/b.md", 5, 20)],
        "why": "why — and more",
    }
    assert catalogue.parse_spec("Spec: none — no text fits") == {"ranges": [], "why": "no text fits"}
    assert catalogue.parse_skills(f"Skills: {TS} (before x); .claude/skills/k1/SKILL.md (before y (twice))") == {
        "skills": [(TS, "before x"), (".claude/skills/k1/SKILL.md", "before y (twice)")],
        "why": "",
    }
    assert catalogue.parse_skills("Skills: none — no skill serves it") == {"skills": [], "why": "no skill serves it"}


SIX = "; ".join(f".claude/skills/k{i}/SKILL.md (step {i})" for i in range(1, 7))
FIVE = "; ".join(f".claude/skills/k{i}/SKILL.md (step {i})" for i in range(1, 6))
CASES = {
    "valid": ([SPEC_OK, SKILLS_OK, SLOT], []),
    "none and none need no slot": (["Spec: none — no ECC text covers it", "Skills: none — no skill serves it"], []),
    "two Spec lines": ([SPEC_OK, SPEC_OK, SKILLS_OK, SLOT], ["2 `Spec:` lines (one expected)"]),
    "no Skills line": ([SPEC_OK, SLOT], ["0 `Skills:` lines (one expected)"]),
    "Spec without why": ([f"Spec: {A}:1-30", SKILLS_OK, SLOT], ["Spec: line without ` — <why>`"]),
    "Spec with an empty why": ([f"Spec: {A}:1-30 — ", SKILLS_OK, SLOT], ["Spec: line without ` — <why>`"]),
    "range backwards": ([f"Spec: {A}:5-1 — why", SKILLS_OK, SLOT], [f"Spec range not <file>:<a>-<b>: {A}:5-1"]),
    "range from 0": ([f"Spec: {A}:0-3 — why", SKILLS_OK, SLOT], [f"Spec range not <file>:<a>-<b>: {A}:0-3"]),
    "missing Spec file": (
        ["Spec: .claude/ecc/agents/c.md:1-5 — why", SKILLS_OK, SLOT],
        ["Spec file missing: .claude/ecc/agents/c.md"],
    ),
    "range past its file": (
        [f"Spec: {A}:1-30, {B}:5-31 — why", SKILLS_OK, SLOT],  # 30 + 27 = 57 lines: only the range is wrong
        [f"Spec range outside its file: {B}:5-31 (30 lines)"],
    ),
    "ranges of 60 lines": (
        [f"Spec: {A}:1-40, {B}:1-20 — why", SKILLS_OK, SLOT],
        ["Spec ranges hold 60 lines (under 60)"],
    ),
    "ranges of 59 lines": ([f"Spec: {A}:1-40, {B}:1-19 — why", SKILLS_OK, SLOT], []),
    "Skills none without why": ([SPEC_OK, "Skills: none", SLOT], ["Skills: none without ` — <why>`"]),
    "Skills item without its step": ([SPEC_OK, f"Skills: {TS}", SLOT], [f"Skills item not <path> (<step>): {TS}"]),
    "skill outside .claude/skills": (
        [SPEC_OK, "Skills: docs/x/SKILL.md (before x)", SLOT],
        ["skill not under .claude/skills/: docs/x/SKILL.md"],
    ),
    "missing skill": (
        [SPEC_OK, "Skills: .claude/skills/nope/SKILL.md (before x)", SLOT],
        ["skill missing: .claude/skills/nope/SKILL.md"],
    ),
    "skill named twice": ([SPEC_OK, f"Skills: {TS} (before x); {TS} (before y)", SLOT], [f"skill named twice: {TS}"]),
    "six skills": ([SPEC_OK, f"Skills: {SIX}", SLOT], ["6 skills (at most 5)"]),
    "five skills": ([SPEC_OK, f"Skills: {FIVE}", SLOT], []),
    "60 pasted lines": ([SPEC_OK, SKILLS_OK, *["pasted"] * 60], ["domain section holds 60 lines (under 60)"]),
    "59 pasted lines": ([SPEC_OK, SKILLS_OK, *["pasted"] * 59], []),
    "neither slot nor text": (
        [SPEC_OK, SKILLS_OK],
        ["Spec names ranges but the section holds neither the launch slot nor the pasted text"],
    ),
}


@pytest.mark.parametrize("case", CASES)
def test_check_brief_reports_exactly_the_one_problem_of_each_case(checkout, case):
    section, expected = CASES[case]
    assert catalogue.check_brief(brief(*section), checkout) == expected


def test_check_brief_reports_the_spec_then_the_skills_then_the_section_size(checkout):
    section = ["Spec: .claude/ecc/agents/c.md:1-5 — why", f"Skills: {TS} (before x); {TS} (before y)"]
    assert catalogue.check_brief(brief(*section, *["pasted"] * 60), checkout) == [
        "Spec file missing: .claude/ecc/agents/c.md",
        f"skill named twice: {TS}",
        "domain section holds 60 lines (under 60)",
    ]


def test_the_section_ends_at_the_next_heading(checkout):
    assert catalogue.check_brief(brief(SPEC_OK, SLOT) + SKILLS_OK + "\n", checkout) == [
        "0 `Skills:` lines (one expected)"
    ]


def test_a_brief_needs_exactly_one_domain_section(checkout):
    expected = ["no `## Domain checklist and skills` section"]
    assert (
        catalogue.check_brief("# Planner\n\n## Work\nWrite.\n### Domain checklist and skills\n", checkout) == expected
    )
    twice = brief(SPEC_OK, SKILLS_OK, SLOT) + "\n## Domain checklist and skills\n" + SPEC_OK + "\n"
    assert catalogue.check_brief(twice, checkout) == ["2 `## Domain checklist and skills` sections (one expected)"]


def test_check_briefs_names_the_file_of_each_problem_and_reads_only_assignments(checkout):
    folder = checkout / "run"
    write(folder / "planner-assignment.md", brief(SPEC_OK, SKILLS_OK, SLOT))
    write(folder / "critic-assignment.md", "# Critic\n")
    write(folder / "common.md", "# Common\n")
    assert catalogue.check_briefs(folder, checkout) == [
        "critic-assignment.md: no `## Domain checklist and skills` section"
    ]


def test_the_briefs_command_prints_the_problems_or_the_count(checkout):
    folder = checkout / "run"
    write(folder / "planner-assignment.md", brief(SPEC_OK, SKILLS_OK, SLOT))
    ok = run("briefs", folder, "--checkout", checkout)
    assert (ok.returncode, ok.stdout) == (0, "ok: 1 briefs checked\n")
    write(folder / "critic-assignment.md", "# Critic\n")
    bad = run("briefs", folder, "--checkout", checkout)
    assert (bad.returncode, bad.stdout) == (1, "critic-assignment.md: no `## Domain checklist and skills` section\n")


def test_the_table_command_prints_the_table_exactly(tmp_path):
    write(tmp_path / ".claude/agents/a.md", "a" * 5)
    result = run("table", "--checkout", tmp_path)
    head = "| name | bytes | tokens | half-use |\n| --- | ---: | ---: | --- |\n"
    assert (result.returncode, result.stdout) == (0, f"### type (1)\n{head}| a | 5 | 1 |  |\n| total | 5 | 1 |  |\n")


def test_the_table_command_on_the_checkout_lists_every_agent_file_as_a_type():
    # No --checkout: default_checkout() is the checkout this skill sits in (parents[5] of the script).
    result = run("table")
    assert result.returncode == 0
    block = result.stdout.split("### type (", 1)[1].split("\n\n", 1)[0]
    names = [row.split(" | ")[0].removeprefix("| ") for row in block.splitlines()[3:-1]]
    assert names == sorted(p.stem for p in (CHECKOUT / ".claude" / "agents").glob("*.md"))
    assert {"plan-fixer", "translator"} <= set(names)


def test_the_manager_readme_documents_every_script_of_its_folder():
    readme = (MANAGER / "README.md").read_text(encoding="utf-8")
    assert len(readme.encode()) <= 12_000
    for script in sorted(MANAGER.glob("*.py")):
        assert f"## {script.name}" in readme.splitlines(), script.name
        assert re.search(rf"(?m)^Usage: .*scripts/manager/{re.escape(script.name)}\b", readme), script.name


def test_a_run_brief_with_its_launch_slot_unfilled_is_refused(checkout):  # owner, 2026-11-01
    folder = checkout / "run"
    write(folder / "_planner-assignment.md", brief(SPEC_OK, SKILLS_OK, SLOT))
    problems = catalogue.check_briefs(folder, checkout)
    assert "_planner-assignment.md: the launch slot is not filled (`catalogue.py fill <run>`)" in problems
    assert any("is not pasted" in p for p in problems)


def test_fill_pastes_each_range_word_for_word_and_drops_a_subagent_s_tools_and_model_lines(checkout):
    write(checkout / A, "---\ntools: Read\nmodel: big\n---\n## Checklist\n- one\n" + "a\n" * 34)
    folder = checkout / "run"
    write(folder / "_planner-assignment.md", brief(SPEC_OK, SKILLS_OK, SLOT))
    r = run("fill", folder, "--checkout", checkout)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.startswith("filled _planner-assignment.md\n")
    text = (folder / "_planner-assignment.md").read_text(encoding="utf-8")
    assert SLOT not in text and "tools: Read" not in text and "model: big" not in text
    assert "## Checklist\n- one\n" in text and text.endswith("## Done when\nAll is written.\n")
    assert catalogue.check_briefs(folder, checkout) == []
    again = run("fill", folder, "--checkout", checkout)
    assert (again.returncode, again.stdout) == (0, "nothing to fill\n")


def test_a_pasted_block_that_differs_from_the_pinned_copy_is_refused(checkout):
    folder = checkout / "run"
    write(folder / "_planner-assignment.md", brief(SPEC_OK, SKILLS_OK, SLOT))
    catalogue.fill_briefs(folder, checkout)
    path = folder / "_planner-assignment.md"
    path.write_text(path.read_text(encoding="utf-8").replace("a\n", "x\n", 1), encoding="utf-8")
    [problem] = catalogue.check_briefs(folder, checkout)
    assert problem.startswith("_planner-assignment.md: the pasted block ") and problem.endswith("pinned copy")


def test_an_example_brief_keeps_its_slot(checkout):
    folder = checkout / "run"
    write(folder / "planner-assignment.md", brief(SPEC_OK, SKILLS_OK, SLOT))
    assert catalogue.check_briefs(folder, checkout) == []
