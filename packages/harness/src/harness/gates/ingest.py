"""harness/gates/ingest.py — the librarian stage gate: the wiki on its branch lints clean and raw material is untouched."""

from __future__ import annotations

from pathlib import Path

from .. import wiki
from ._common import branch_of, changed_files, check, on_branch, result, text


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    res = result(stage_dir)
    out = [check("changes.md exists", bool(text(stage_dir, "output/changes.md")))]
    branch = branch_of(root, res)
    out.append(check("result.json names the branch of the wiki change", branch is not None))
    if branch:
        files = changed_files(root, branch)
        raw = [f for f in files if f.startswith("context/")]
        outside = [f for f in files if not f.startswith("wiki/")]
        lint, err = on_branch(root, branch, wiki.lint)
        out += [
            check("context/ is not in the diff", not raw, ", ".join(raw[:5])),
            check("the branch changes wiki/ only", not outside, ", ".join(outside[:5])),
            check(
                "harness wiki-lint is clean on the branch",
                bool(lint) and lint["ok"],
                err or "; ".join((lint or {}).get("problems", [])[:3]),
            ),
        ]
    return out
