#!/usr/bin/env python3
"""Start-up cost per SpecAgent session, from the transcripts: the context size of a session's first write call (the first
call with an Edit, a Write, or a Bash command with `git commit`, `>>` or `tee -a`). What a session reads before its
first write is what it pays to start, and every later call re-reads it. Run from the main session; no model involved.

  python3 startup_report.py [--prefix demo/] [--since 2026-10-22] [--threshold 60000]

Per agent: the fresh sessions measured, those that never wrote, the resumed ones, the median and the maximum start-up
cost, and how many are over the threshold; then each session over it, with the number of Bash commands it ran before
its first write and the files it read before it (its Read paths, deduplicated, at most 12). A session that never
wrote is over the threshold when its largest call passed it, and is listed with that call: most of the live ones
reached the cap before a write, so their resumes wrote, and they are the costliest start-ups. A resumed session is
counted, not measured: Claude Code writes it under a new id, its transcript beginning with a copy of the session it
resumes, so its first call is dated before its own start. The sessions, their transcripts and their calls come from
usage_report.py (imported): `claude agents --json --all`, one call per message id, no '<synthetic>' line. --since
keeps the sessions that started on or after that day (UTC); a session that made no call is left out.
"""

import argparse
import collections
import os
import re
import statistics
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import usage_report as ur

LISTED = 12  # Read paths shown per session
# `git commit` also with git's options before the subcommand, as the pipelines commit: `git -C <dir> -c … commit`
GIT_COMMIT = re.compile(r"\bgit(?:\s+(?:-[cC]\s+\S+|--[\w-]+(?:=\S+)?))*\s+commit\b")


def is_write(block):
    """An Edit, a Write, or a Bash command that commits or appends."""
    name, command = block.get("name"), (block.get("input") or {}).get("command") or ""
    return (
        name in ("Edit", "Write")
        or name == "Bash"
        and (">>" in command or "tee -a" in command or "git commit" in command or bool(GIT_COMMIT.search(command)))
    )


def unique(paths):
    return list(dict.fromkeys(p for p in paths if p))


def startup(paths, start="", since=""):
    """A session's start-up, from its transcripts and its start (startedAt, in the transcripts' form): {'cost', 'call',
    'at', 'bash', 'reads'}: the context of its first write call, that call's number and time, and the number of Bash
    commands and the Read paths of the calls before it; when it never wrote, cost None, its largest call ('peak',
    'call', 'at'), its number of calls ('calls') and all its Bash commands and Read paths. {'resumed': True} when its
    first call is dated before its start. None when it made no call or started before `since` (a day)."""
    first, numbers, reads, bash, peak = None, {}, [], [], (0, None, "")
    for path in paths:
        for key, d in ur.lines(path):
            if first is None:
                first = d.get("timestamp", "")
                if since and (start or first)[:10] < since:
                    return None
                if start and first < start:
                    return {"resumed": True}
            numbers.setdefault(key, len(numbers) + 1)
            if ur.context(d["message"]["usage"]) > peak[0]:
                peak = (ur.context(d["message"]["usage"]), key, d.get("timestamp", ""))
            content = d["message"].get("content")
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                if is_write(block):  # a Read or Bash of this same call ran beside it, not before it
                    return {
                        "cost": ur.context(d["message"]["usage"]),
                        "call": numbers[key],
                        "at": d.get("timestamp", ""),
                        "bash": sum(k != key for k in bash),
                        "reads": unique(p for k, p in reads if k != key),
                    }
                if block.get("name") == "Read":
                    reads.append((key, (block.get("input") or {}).get("file_path")))
                elif block.get("name") == "Bash":
                    bash.append(key)
    if first is None:
        return None
    return {
        "cost": None,
        "peak": peak[0],
        "call": numbers.get(peak[1], 0),
        "at": peak[2],
        "calls": len(numbers),
        "bash": len(bash),
        "reads": unique(p for _, p in reads),
    }


def report(rows, since="", threshold=60000):
    """Per agent name its costs and the numbers of its sessions that never wrote and that were resumed; the sessions
    over the threshold (one that never wrote by its largest call), the largest first, as (name, session id,
    start-up)."""
    per = collections.defaultdict(lambda: {"costs": [], "none": 0, "none_over": 0, "resumed": 0})
    over = []
    for r in rows:
        sid, name = r["sessionId"], r.get("name") or ""
        s = startup(sorted(ur.transcripts(sid)), ur.started(r), since)
        if s is None:
            continue
        if s.get("resumed"):
            per[name]["resumed"] += 1
        elif s["cost"] is None:
            per[name]["none"] += 1
            if s["peak"] > threshold:
                per[name]["none_over"] += 1
                over.append((name, sid, s))
        else:
            per[name]["costs"].append(s["cost"])
            if s["cost"] > threshold:
                over.append((name, sid, s))
    over.sort(key=lambda x: -(x[2]["cost"] or x[2]["peak"]))
    return per, over


def row(name, v, threshold):
    costs = v["costs"]
    median = f"{statistics.median(costs):,.0f}" if costs else "-"
    top = f"{max(costs):,}" if costs else "-"
    return (
        f"{name[:28]:28} {len(costs):8} {v['none']:8} {v['resumed']:8} {median:>9} {top:>9} "
        f"{sum(c > threshold for c in costs) + v['none_over']:12}"
    )


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Start-up cost per SpecAgent session: the context of each session's first write call."
    )
    ap.add_argument("--prefix", default="")
    ap.add_argument("--since", default="")
    ap.add_argument("--threshold", type=int, default=60000)
    args = ap.parse_args(argv)

    per, over = report(ur.agent_rows(args.prefix), args.since, args.threshold)
    print(
        "start-up cost: the context (input + cache write + cache read tokens) of a fresh session's first write call "
        "(Edit, Write, or Bash with git commit, >> or tee -a); a resumed session is counted, not measured; one that "
        "never wrote is counted, and over the threshold when its largest call passed it"
    )
    if not per:
        print(f"no session matched (prefix {args.prefix!r}, since {args.since!r})")
        return
    print(
        f"{'agent':28} {'sessions':>8} {'no write':>8} {'resumed':>8} {'median':>9} {'max':>9} "
        f"{'over ' + format(args.threshold, ','):>12}"
    )
    for name in sorted(per):
        print(row(name, per[name], args.threshold))
    print(
        row(
            "total",
            {
                "costs": [c for v in per.values() for c in v["costs"]],
                "none": sum(v["none"] for v in per.values()),
                "none_over": sum(v["none_over"] for v in per.values()),
                "resumed": sum(v["resumed"] for v in per.values()),
            },
            args.threshold,
        )
    )
    print(
        f"\nsessions over {args.threshold:,} at their first write (or, never writing, at their largest call), with "
        f"the Bash commands they ran and the files they read before it (Read, deduplicated, at most {LISTED}):"
    )
    for name, sid, s in over:
        reads = s["reads"]
        listed = ", ".join(reads[:LISTED]) + (f" (+{len(reads) - LISTED} more)" if len(reads) > LISTED else "")
        when = f"({s['at'][:16].replace('T', ' ')} UTC)"
        head = (
            f"no write in {s['calls']} calls, {s['peak']:,} at call {s['call']} {when}; {s['bash']} Bash; reads"
            if s["cost"] is None
            else f"{s['cost']:,} at call {s['call']} {when}; {s['bash']} Bash before it; reads before it"
        )
        print(f"- {name} {sid}: {head} ({len(reads)})" + (f": {listed}" if reads else ""))
    if not over:
        print("none")


if __name__ == "__main__":
    main()
