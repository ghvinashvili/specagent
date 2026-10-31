"""The open finding ids of a run folder, one per line: the work_check of a role that answers findings.

  python3 -I open_ids.py <run-dir> [--kind C,A,B,V,R] [--cause plan] [--parity odd|even] [--no-shared] [--task N]

An id is open as check_formats.ids() reads the run folder: it has no answer line yet (a B only when it was sent to the
planner or the plan fixer). The kinds print in the order of --kind, each kind's ids in reading order. An id's task is
the `##` or `###` heading above its `#### <id>` line when that heading starts `Task <n>` (`## Task 2 (diff)`,
`## Task 2 — abc1234`); any other heading, or none (a build log's B line), makes the id shared; an id's first heading
wins. --parity keeps the ids of the tasks of that parity and every shared id; --no-shared drops the shared ids (the
second fixer's collection, judge J3 of the pipeline-fold run); --task keeps task n's ids only, no shared one; --cause plan drops a V or R whose heading names the cause (code). Exit 0 when it printed an id, 3 when
none, 2 on a usage error (a --kind entry that is not one or two capital letters: `C, A`, `c,a`) or a run folder that
does not exist, so a broken check never reads as "nothing waits". Read-only.
"""

import argparse
import pathlib
import re
import sys

sys.dont_write_bytecode = True  # `python3 -I` ignores PYTHONDONTWRITEBYTECODE; the skill folder stays clean
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_formats as cf

HEADING_FILES = ("critique.md", "verify.md", "judge.md", "verify-kb.md")  # the files whose headings ids() reads
PARITY = {"odd": 1, "even": 0}


def headings(run: pathlib.Path) -> dict[str, tuple[int | None, str]]:
    """Each `#### <id>` id's task (None when shared) and heading line, the sections read as wait_for_ready.py reads."""
    out: dict[str, tuple[int | None, str]] = {}
    for name in HEADING_FILES:
        task = None
        for line in cf.read(run / name).splitlines():
            if h := cf.HEADING.match(line):
                out.setdefault(h.group(1) + h.group(2), (task, line))
            elif s := re.match(r"#{2,3} (.+)", line):
                t = re.match(r"Task (\d+)", s.group(1).strip())
                task = int(t.group(1)) if t else None
    return out


def open_ids(
    run: pathlib.Path,
    kinds: list[str],
    parity: str | None = None,
    task: int | None = None,
    cause: str | None = None,
    shared: bool = True,
) -> list[str]:
    """The open ids of `kinds`, kind by kind in that order and each kind's in reading order, kept by the filters."""
    waiting, where = cf.ids(run)["open"], headings(run)
    out: list[str] = []
    for kind in kinds:
        for ident in waiting.get(kind, []):
            n, line = where.get(ident, (None, ""))
            if task is not None and n != task:
                continue
            if not shared and n is None:
                continue
            if parity and n is not None and n % 2 != PARITY[parity]:
                continue
            found = cf.CAUSE.search(line)
            if cause == "plan" and kind in ("V", "R") and found and found.group(1) == "code":
                continue
            out.append(ident)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Print the open finding ids of a run folder, one per line.")
    ap.add_argument("run_dir")
    ap.add_argument("--kind", default="C,A,B,V,R", help="comma-separated kinds, printed in this order")
    ap.add_argument("--cause", choices=["plan"], help="drop the V and R ids whose heading names (code)")
    ap.add_argument("--parity", choices=["odd", "even"], help="the ids of the tasks of this parity and every shared id")
    ap.add_argument("--task", type=int, help="task N's ids only, no shared one")
    ap.add_argument(
        "--no-shared",
        dest="shared",
        action="store_false",
        help="drop the shared ids (the index's, a non-task section's, a build log's B line): the second fixer's",
    )
    args = ap.parse_args(argv)
    kinds = args.kind.split(",")
    if bad := [kind for kind in kinds if not re.fullmatch(r"[A-Z]{1,2}", kind)]:  # check_formats.HEADING's kind
        ap.error(f"--kind: not a kind (one or two capital letters, no spaces): {bad[0]!r}")
    run = pathlib.Path(args.run_dir)
    if not run.is_dir():
        print(f"open_ids.py: no such folder: {run}", file=sys.stderr)
        return 2
    found = open_ids(run, kinds, args.parity, args.task, args.cause, args.shared)
    for ident in found:
        print(ident)
    return 0 if found else 3


if __name__ == "__main__":
    sys.exit(main())
