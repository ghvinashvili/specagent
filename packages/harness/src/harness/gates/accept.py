"""harness/gates/accept.py — the test-verifier stage gate: a row per criterion, tests green on its branch, no product code touched."""

from __future__ import annotations

import re
from pathlib import Path

from ._common import TEST_PATH, branch_of, changed_files, check, result, table_rows, tests_check, text
from .story import criteria

STATUS = re.compile(r"\b(passed|failed|not coverable)\b", re.IGNORECASE)


def session_checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    """The gate without the test suite it runs outside any session: what the stop hook holds the session to."""
    return checks(root, run_dir, stage_dir, suite=False)


def checks(root: Path, run_dir: Path, stage_dir: Path, suite: bool = True) -> list[dict]:
    doc = text(stage_dir, "output/acceptance.md")
    numbers = criteria(text(run_dir / "stages" / "story", "output/story.md"))
    rows = [r for r in table_rows(doc) if STATUS.search(" ".join(r))]
    covered = {m for r in rows for m in re.findall(r"\d+", r[0])}
    uncovered = [n for n in numbers if n not in covered]
    res = result(stage_dir)
    out = [
        check("acceptance.md exists", bool(doc)),
        check(
            "every acceptance criterion has a row with its status",
            bool(numbers) and not uncovered,
            "criteria: " + ", ".join(uncovered),
        ),
        check("result.json has one evidence entry per criterion", len(res.get("evidence", [])) >= len(numbers)),
    ]
    branch = branch_of(root, res)
    out.append(check("result.json names the branch of the tests", branch is not None))
    if branch:
        product = [f for f in changed_files(root, branch) if not TEST_PATH.search(f)]
        out.append(check("the branch changes test files only", not product, ", ".join(product[:5])))
        if suite:
            out.append(tests_check(root, branch))
    return out
