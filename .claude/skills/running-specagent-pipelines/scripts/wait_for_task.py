#!/usr/bin/env python3
"""Critic's waiter: exits 0 when there is work.
Polls every 30 s and returns within 3.5 min (exit 3 and the line to run it again), so the caller's next call
comes within the prompt cache's 5 minutes (owner, 2026-11-01); a wait known to be longer than about an hour ends the
session instead, and the watcher relaunches it on work.

python3 wait_for_task.py --plan PLAN.md --response critique-response.md N
    exit when a task after N is complete, or the response file says 'STATUS: plan complete'
    (a task counts as complete once the next '### Task <n>' heading exists)
python3 wait_for_task.py --critique critique.md --response critique-response.md --answers
    exit when every '#### C<n>' / '#### A<n>' id in the critique has a '<id>:' line in the response file
python3 wait_for_task.py --log plan-log.md --critique critique.md --response critique-response.md
    the lanes' form: exit when a 'Task <n>: written' line of the log names a task that is neither at most the N of
    the critique's line 1 ('STATUS: reviewed|caught up through Task N'; 'STATUS: done' covers every task) nor listed
    on its line 2 ('Reviewed: <list>'), or when the response's line 1 is 'STATUS: plan complete' or 'STATUS: done',
    every '#### C<n>' / '#### A<n>' id has its answer line and the critique's line 1 is not 'STATUS: done' (the
    critic's summary is due)
--once, in any form: one check, no polling; prints its line and exits 0 when there is work now, 3 when not.
"""

import argparse
import pathlib
import re
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--plan")
ap.add_argument("--log")
ap.add_argument("--critique")
ap.add_argument("--response", required=True)
ap.add_argument("--answers", action="store_true")
ap.add_argument("--once", action="store_true")
ap.add_argument("last", nargs="?", type=int, default=0)
args = ap.parse_args()


def text(path):
    p = pathlib.Path(path) if path else None
    return p.read_text(encoding="utf-8", errors="ignore") if p and p.exists() else ""


def unanswered(critique, response):
    asked = set(re.findall(r"^#### ([CA]\d+)\b", critique, re.MULTILINE))
    return asked, sorted(asked - set(re.findall(r"^([CA]\d+):", response, re.MULTILINE)))


def lanes(response):
    critique = text(args.critique)
    lines = critique.splitlines() or [""]
    done = lines[0].startswith("STATUS: done")
    m = re.match(r"STATUS: (?:caught up|reviewed) through Task (\d+)", lines[0])
    through = 10**6 if done else (int(m.group(1)) if m else 0)
    second = lines[1] if len(lines) > 1 else ""
    listed = {int(n) for n in re.findall(r"\d+", second)} if second.startswith("Reviewed:") else set()
    for n in map(int, re.findall(r"^Task (\d+): written\b", text(args.log), re.MULTILINE)):
        if n > through and n not in listed:
            return f"Task {n} written, not reviewed", True, []
    asked, missing = unanswered(critique, response)
    if response.startswith(("STATUS: plan complete", "STATUS: done")) and not missing and not done:
        return f"plan complete, all {len(asked)} answered: the summary is due", True, []
    return f'nothing to review: critic says "{lines[0] or "no critique yet"}"', False, missing


def check():
    """(its line, whether there is work, the unanswered ids)."""
    response = text(args.response)
    if args.log:
        return lanes(response)
    if args.answers:
        asked, missing = unanswered(text(args.critique), response)
        return (
            (f"all {len(asked)} answered" if not missing else f"unanswered: {', '.join(missing)}"),
            not missing,
            missing,
        )
    tasks = [int(n) for n in re.findall(r"^### Task (\d+)", text(args.plan), re.MULTILINE)]
    complete = "STATUS: plan complete" in response
    done = (max(tasks) if complete else max(tasks) - 1) if tasks else 0
    return f"complete through Task {done}; plan complete: {complete}", done > args.last or complete, []


deadline = time.monotonic() + 210
while True:
    line, work, missing = check()
    if work or args.once:
        print(line)
        sys.exit(0 if work else 3)
    if time.monotonic() + 30 > deadline:
        break
    time.sleep(30)
print(
    line
    + (f"; unanswered: {', '.join(missing)}" if missing else "")
    + ". Run the same command again now: a call within 5 min keeps the prompt cache warm"
)
sys.exit(3)
