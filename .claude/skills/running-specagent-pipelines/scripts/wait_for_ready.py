#!/usr/bin/env python3
"""Builder's waiter: exit 0 when Task N is ready to build. Polls once a minute for up to 8 hours.

  python3 wait_for_ready.py --critique critique.md --response critique-response.md N
Ready: the critique's first line is 'STATUS: caught up through Task M' or 'STATUS: reviewed through Task M' with M >= N
(or 'STATUS: done'), and every '#### C<n>' / '#### A<n>' id filed under the shared sections or under Tasks 1..N has a
'<id>:' answer line in the response file. Sections are '##' or '###' headings; 'Task <n>' headings mark a task, any
other heading counts as shared.
  --once: one check, no polling; prints its line and exits 0 when Task N is ready now, 3 when not.
"""

import argparse
import pathlib
import re
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--critique", required=True)
ap.add_argument("--response", required=True)
ap.add_argument("task", type=int)
ap.add_argument("--once", action="store_true")
args = ap.parse_args()


def text(path):
    p = pathlib.Path(path)
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


def state(n):
    critique, response = text(args.critique), text(args.response)
    first = critique.splitlines()[0] if critique else ""
    m = re.match(r"STATUS: (?:caught up|reviewed) through Task (\d+)", first)
    reviewed = 10**6 if first.startswith("STATUS: done") else (int(m.group(1)) if m else 0)
    if reviewed < n or not response:
        return f'not ready: critic says "{first or "no critique yet"}"', False
    section, needed = 0, set()
    for line in critique.splitlines():
        if not line.startswith("####"):
            h = re.match(r"#{2,3} (.+)", line)
            if h:
                t = re.match(r"Task (\d+)", h.group(1).strip())
                section = int(t.group(1)) if t else 0
        i = re.match(r"#### ([CA]\d+)\b", line)
        if i and section <= n:
            needed.add(i.group(1))
    missing = sorted(needed - set(re.findall(r"^([CA]\d+):", response, re.MULTILINE)), key=lambda s: (s[0], int(s[1:])))
    return (f"Task {n} ready" if not missing else f"not ready: unanswered {', '.join(missing[:15])}"), not missing


for _ in range(480):
    message, ready = state(args.task)
    if ready or args.once:
        print(message)
        sys.exit(0 if ready else 3)
    time.sleep(60)
print("timeout after 8 hours; " + message)
sys.exit(1)
