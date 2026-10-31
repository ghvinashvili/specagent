"""make_pack.py (spec B1, B13): a role's startup pack, built from the run folder's files that a packs config names. The
pack holds those files in full and the named sections of the lessons file, carries no time stamp, and is written only
when its text changed, so a cached prefix stays the same while nothing changed.

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests/test_make_pack.py
"""

import json
import os
import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "make_pack.py"
LESSONS = """# Lessons

## Read first
1. Read by ranges.

## Known error classes
- A path that does not exist.

## Lessons from this run
- 2026-10-28: a rule added later.
"""


def make_run(tmp_path: pathlib.Path, **config: object) -> pathlib.Path:
    """A run folder with three brief files, lessons.md and `_packs.json` (`config` merged over its two roles)."""
    run = tmp_path / "demo-run"
    run.mkdir()
    (run / "_common.md").write_text("# Common brief\n\nShared rules.\n\n", encoding="utf-8")
    (run / "_planner-assignment.md").write_text("# Planner\n\nWrite the plan.\n", encoding="utf-8")
    (run / "_critic-assignment.md").write_text("# Critic\n\nReview the plan.\n", encoding="utf-8")
    (run / "lessons.md").write_text(LESSONS, encoding="utf-8")
    roles = {"planner": ["_common.md", "_planner-assignment.md"], "critic": ["_common.md", "_critic-assignment.md"]}
    packs = {"_note": "keys that start with _ are comments", "roles": roles, **config}
    (run / "_packs.json").write_text(json.dumps(packs), encoding="utf-8")
    return run


def make_pack(run: pathlib.Path, *roles: str, flags: tuple[str, ...] = ()) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *flags, str(run / "_packs.json"), *roles],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_a_pack_holds_the_role_s_files_in_order_and_the_two_lessons_sections(tmp_path):
    run = make_run(tmp_path)
    r = make_pack(run, "planner")
    assert r.returncode == 0, r.stderr
    pack = (run / "_pack-planner.md").read_text(encoding="utf-8")
    assert r.stdout == f"_pack-planner.md: {len(pack.encode()) // 1024} KB\n"
    assert pack.splitlines()[0] == "# Your standing orders (startup pack of demo-run/planner)"
    assert [line for line in pack.splitlines() if line.startswith("## File: ")] == [
        "## File: _common.md",
        "## File: _planner-assignment.md",
        '## File: lessons.md ("Read first" and "Known error classes" only)',
    ]
    assert "\n---\n\n## File: _common.md\n\n# Common brief\n\nShared rules.\n\n---\n" in pack
    lessons = pack.split("## File: lessons.md", 1)[1]
    assert "## Read first\n1. Read by ranges.\n" in lessons
    assert "## Known error classes\n- A path that does not exist.\n" in lessons
    assert "Lessons from this run" not in lessons and "a rule added later" not in pack
    assert "_critic-assignment.md" not in pack and not (run / "_pack-critic.md").exists()


def test_an_unchanged_pack_is_not_rewritten_and_a_changed_file_rewrites_it(tmp_path):
    run = make_run(tmp_path)
    assert make_pack(run, "critic").returncode == 0
    pack = run / "_pack-critic.md"
    before = pack.read_bytes()
    os.utime(pack, (1_000_000_000, 1_000_000_000))
    assert make_pack(run, "critic").returncode == 0
    assert (pack.read_bytes(), pack.stat().st_mtime) == (before, 1_000_000_000)
    (run / "_critic-assignment.md").write_text("# Critic\n\nReview the plan and the diff.\n", encoding="utf-8")
    assert make_pack(run, "critic").returncode == 0
    assert pack.stat().st_mtime != 1_000_000_000
    assert "Review the plan and the diff." in pack.read_text(encoding="utf-8")


def test_without_roles_every_role_is_built_in_the_config_s_order_with_its_name_lessons_and_sections(tmp_path):
    run = make_run(tmp_path, name="demo", lessons="notes.md", sections=["Known error classes"])
    (run / "lessons.md").rename(run / "notes.md")
    r = make_pack(run)
    assert r.returncode == 0, r.stderr
    assert [line.split(":")[0] for line in r.stdout.splitlines()] == ["_pack-planner.md", "_pack-critic.md"]
    critic = (run / "_pack-critic.md").read_text(encoding="utf-8")
    assert critic.splitlines()[0] == "# Your standing orders (startup pack of demo/critic)"
    assert '## File: notes.md ("Known error classes" only)' in critic
    assert "- A path that does not exist." in critic and "1. Read by ranges." not in critic


@pytest.mark.parametrize(
    ("case", "named"),
    [("unknown role", "nobody"), ("missing file", "_critic-assignment.md"), ("missing section", "No such section")],
)
def test_an_unknown_role_a_missing_file_or_a_missing_section_exits_2_and_writes_no_pack(tmp_path, case, named):
    sections = ["Read first", "No such section"] if case == "missing section" else ["Read first"]
    run = make_run(tmp_path, sections=sections)
    if case == "missing file":
        (run / "_critic-assignment.md").unlink()
    r = make_pack(run, *(["planner", "nobody"] if case == "unknown role" else ["planner", "critic"]))
    assert (r.returncode, r.stdout) == (2, "")
    assert r.stderr.startswith("make_pack.py: ") and named in r.stderr
    assert sorted(run.glob("_pack-*.md")) == []


# Spec 005, requirement 7b: "stable first, unique last". A hand-over note is unique to one session, so `--no-note` leaves
# every `handoff-*.md` out of the packs; the hand-over rule (`_handoff-rule.md`) is byte-identical across sessions and stays.
NOTE_ROLES = {"planner": ["_common.md", "_handoff-rule.md", "_planner-assignment.md", "handoff-planner.md"]}
FILES = ["## File: _common.md", "## File: _handoff-rule.md", "## File: _planner-assignment.md"]
LESSONS_HEADING = '## File: lessons.md ("Read first" and "Known error classes" only)'


def make_run_with_a_note(tmp_path: pathlib.Path) -> pathlib.Path:
    run = make_run(tmp_path, roles=NOTE_ROLES)
    (run / "_handoff-rule.md").write_text("# Hand-over rule\n\nHand over at a unit's end.\n", encoding="utf-8")
    (run / "handoff-planner.md").write_text("HANDOFF planner after Task 3\n\nNext: Task 4.\n", encoding="utf-8")
    return run


def file_headings(pack: str) -> list[str]:
    return [line for line in pack.splitlines() if line.startswith("## File: ")]


def test_without_the_option_a_note_that_the_config_names_is_in_the_pack(tmp_path):
    run = make_run_with_a_note(tmp_path)
    assert make_pack(run, "planner").returncode == 0
    pack = (run / "_pack-planner.md").read_text(encoding="utf-8")
    assert file_headings(pack) == [*FILES, "## File: handoff-planner.md", LESSONS_HEADING]
    assert "Next: Task 4." in pack and "is not in this pack" not in pack


def test_no_note_leaves_the_notes_out_keeps_the_hand_over_rule_and_says_where_the_note_is(tmp_path):
    run = make_run_with_a_note(tmp_path)
    r = make_pack(run, "planner", flags=("--no-note",))
    assert r.returncode == 0, r.stderr
    pack = (run / "_pack-planner.md").read_text(encoding="utf-8")
    assert file_headings(pack) == [*FILES, LESSONS_HEADING]
    assert "Hand over at a unit's end." in pack
    assert "Next: Task 4." not in pack and "handoff-planner" not in pack
    assert "Your hand-over note is not in this pack" in pack.split("\n---\n", 1)[0]


def test_no_note_builds_the_pack_before_a_note_exists_and_a_note_written_later_does_not_change_it(tmp_path):
    run = make_run_with_a_note(tmp_path)
    (run / "handoff-planner.md").unlink()
    refused = make_pack(run, "planner")  # the note is a file the config names: without the option it must exist
    assert (refused.returncode, refused.stdout) == (2, "") and "handoff-planner.md" in refused.stderr
    assert make_pack(run, "planner", flags=("--no-note",)).returncode == 0
    pack = run / "_pack-planner.md"
    before = pack.read_bytes()
    os.utime(pack, (1_000_000_000, 1_000_000_000))
    (run / "handoff-planner.md").write_text("HANDOFF planner after Task 1\n", encoding="utf-8")
    assert make_pack(run, "planner", flags=("--no-note",)).returncode == 0
    assert (pack.read_bytes(), pack.stat().st_mtime) == (before, 1_000_000_000)


def test_a_role_with_nothing_left_after_the_notes_are_dropped_exits_2_and_writes_no_pack(tmp_path):
    run = make_run(tmp_path, roles={"planner": ["handoff-planner.md"]})
    (run / "handoff-planner.md").write_text("HANDOFF planner after Task 3\n", encoding="utf-8")
    r = make_pack(run, "planner", flags=("--no-note",))
    assert (r.returncode, r.stdout) == (2, "")
    assert r.stderr.startswith("make_pack.py: ") and "planner" in r.stderr and "no file left" in r.stderr
    assert sorted(run.glob("_pack-*.md")) == []
