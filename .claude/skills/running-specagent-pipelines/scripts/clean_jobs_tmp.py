#!/usr/bin/env python3
"""The `tmp` folders of finished background jobs (~/.claude/jobs/<id>/tmp): an earlier run's jobs filled about 90 GB
with them. Lists them by default; `--apply` removes them, and only them (each job's state.json and timeline.jsonl stay).

Usage: python3 -I clean_jobs_tmp.py [--jobs DIR] [--hours N] [--apply]
A job is finished when its row of `claude agents --json --all` has an 8-hex-digit `id`, no `pid`, a `state` of done,
failed or stopped, and no row with a `pid` shares its `sessionId` (a resumed session lives on under a new id). A job
whose state.json (else its folder) changed less than `--hours` ago is left alone, and a `tmp` that is a symlink is
reported and never followed. Exit 0; 2 when the jobs folder is missing or the listing fails; 1 when a removal fails.
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

PROG = "clean_jobs_tmp.py"
FINISHED = {"done", "failed", "stopped"}
JOB_ID = re.compile(r"[0-9a-f]{8}")


def rows() -> list[dict] | None:
    """The rows of `claude agents --json --all`, or None when it fails or prints no JSON list."""
    try:
        out = subprocess.run(
            ["claude", "agents", "--json", "--all"], capture_output=True, text=True, timeout=300, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        data = json.loads(out.stdout)
    except ValueError:
        return None
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else None


def finished(listing: list[dict]) -> list[dict]:
    """The rows of finished jobs, in id order."""
    live = {row.get("sessionId") for row in listing if "pid" in row}
    jobs = [
        row
        for row in listing
        if isinstance(row.get("id"), str)
        and JOB_ID.fullmatch(row["id"])
        and "pid" not in row
        and row.get("state") in FINISHED
        and row.get("sessionId") not in live
    ]
    return sorted(jobs, key=lambda row: row["id"])


def size(folder: pathlib.Path) -> int:
    """The bytes of the files under `folder` (os.lstat sizes; symlinks are not followed)."""
    total = 0
    for parent, _dirs, files in os.walk(folder):
        for name in files:
            try:
                total += os.lstat(os.path.join(parent, name)).st_size
            except OSError:
                continue
    return total


def recent(folder: pathlib.Path, hours: float) -> bool:
    """Whether the job's state.json (else its folder) changed less than `hours` ago."""
    state = folder / "state.json"
    stamp = state if state.is_file() else folder
    return time.time() - stamp.stat().st_mtime < hours * 3600


def main(argv: list[str] | None = None) -> int:
    """List the tmp folders of finished jobs, or remove them with --apply, and print the total."""
    ap = argparse.ArgumentParser(prog=PROG, description="List or remove the tmp folders of finished background jobs.")
    ap.add_argument(
        "--jobs",
        type=pathlib.Path,
        default=pathlib.Path("~/.claude/jobs").expanduser(),
        help="the jobs folder (default ~/.claude/jobs)",
    )
    ap.add_argument("--hours", type=float, default=24.0, help="leave jobs that changed less than N hours ago (24)")
    ap.add_argument("--apply", action="store_true", help="remove the folders (without it nothing is removed)")
    args = ap.parse_args(argv)
    if not args.jobs.is_dir():
        print(f"{PROG}: no jobs folder {args.jobs}", file=sys.stderr)
        return 2
    listing = rows()
    if listing is None:
        print(f"{PROG}: claude agents --json --all failed or did not print a JSON list", file=sys.stderr)
        return 2
    count, total, failed = 0, 0, False
    for row in finished(listing):
        folder = args.jobs / row["id"]
        tmp = folder / "tmp"
        if not os.path.lexists(tmp) or recent(folder, args.hours):
            continue
        if folder.is_symlink() or tmp.is_symlink():
            print(f"skipped {folder if folder.is_symlink() else tmp}: a symlink")
            continue
        if not tmp.is_dir():
            continue
        found = size(tmp)
        what = f"{tmp} ({row['state']}, {row.get('name', '')}, {found / 1_000_000:.1f} MB)"
        if args.apply:
            try:
                shutil.rmtree(tmp)
            except OSError as e:
                print(f"{PROG}: cannot remove {tmp}: {e}", file=sys.stderr)
                failed = True
                continue
        print(f"removed {what}" if args.apply else f"would remove {what}")
        count, total = count + 1, total + found
    tail = " removed" if args.apply else "; nothing removed without --apply"
    print(f"total: {count} folders, {total / 1_000_000:.1f} MB{tail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
