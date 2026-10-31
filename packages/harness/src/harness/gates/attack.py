"""harness/gates/attack.py — the critic's stage before the work (specs/002-run-loop): the plan and its trial attacked,
every blocking finding proven by a command, attack tests under their repository paths as new files a writer may add,
and a one-page summary in English for the human who approves the plan."""

from __future__ import annotations

import re
from pathlib import Path

from .. import access
from ..catalog import GEORGIAN
from ._common import TEST_PATH, base_commit, check, closed_to, critique_table, git, result, test_modules, text, unproven
from .critique import critique_checks
from .verify import claimed_tasks

BLOCKING = {"blocks", "must fix"}
PAGE = 6000  # characters: one page of the summary
NO_TEST = re.compile(r"(?im)^\s*No attack test:\s*\S")


def attack_tests(stage_dir: Path) -> list[str]:
    """The test files under output/tests/, by the repository path they will have; a link is no test."""
    tests = stage_dir / "output" / "tests"
    if not tests.is_dir() or tests.is_symlink():
        return []
    files = [p.relative_to(tests).as_posix() for p in tests.rglob("*") if p.is_file() and not p.is_symlink()]
    return sorted(f for f in files if TEST_PATH.search(f))


def taken_paths(root: Path, run_dir: Path, tests: list[str]) -> list[str]:
    """The attack tests a writer could not add as given: a path that exists at the run's base (the given file would
    replace a test file whole, and its own tests would vanish) or one closed to a writer (_common.closed_to)."""
    base = base_commit(root, run_dir)
    shut = closed_to(root, access.load_policy(root), run_dir, "writer")
    return [t for t in tests if shut(t) or (base and git(root, "cat-file", "-e", f"{base}:{t}").returncode == 0)]


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    doc = text(stage_dir, "output/critique.md")
    res = result(stage_dir)
    decision = (res.get("verdict") or {}).get("decision")
    blocking = [r["no"] for r in critique_table(doc) or [] if r["severity"] in BLOCKING]
    lacking = unproven(res, stage_dir.relative_to(run_dir / "stages").parts[0], blocking)
    tests = attack_tests(stage_dir)
    taken = taken_paths(root, run_dir, tests)
    modules = test_modules(root, base_commit(root, run_dir), tests)  # a helper or a conftest.py is no attack test
    summary = text(stage_dir, "output/summary.md")
    unnamed = [t for t in claimed_tasks(stage_dir) if t not in doc]
    return [
        *critique_checks(run_dir, stage_dir),
        check("result.json proposes accept or revise", decision in ("accept", "revise"), str(decision)),
        check("revise names a blocks or must fix finding, accept none", (decision == "revise") == bool(blocking),
              f"{len(blocking)} blocks or must fix rows, verdict {decision}"),
        check("every blocks or must fix finding has its evidence entry in result.json", not lacking,
              "no entry with a command, its exit code and `<stage>#<n>` in its claim for row " + ", ".join(lacking[:8])),
        check("output/tests/ holds attack tests under their repository paths", bool(modules) or bool(NO_TEST.search(doc)),
              "write pytest files under output/tests/<path in the repository>, or a line `No attack test: <reason>`"),
        check("every attack test is a new file a writer may add", not taken, ", ".join(taken[:5])),
        check("every task of the plan is named in the critique", not unnamed, ", ".join(unnamed[:8])),
        check("output/summary.md is a one-page summary in English",
              bool(summary.strip()) and not GEORGIAN.search(summary) and len(summary) <= PAGE,
              f"{len(summary)} characters"),
    ]  # fmt: skip
