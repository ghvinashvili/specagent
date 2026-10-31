#!/usr/bin/env python3
"""Token use per SpecAgent session, from the transcripts: how big the context is per call, how many calls, an
API-equivalent cost, and the dollars of the cache reads, the cache writes and the output beside their token counts
(the cache is measured in money: spec 005). Run from the main session; no model involved.

  python3 usage_report.py [--prefix demo/] [--since 2026-10-15] [--by-day]

Reads `claude agents --json --all` for the names and session ids, then ~/.claude/projects/*/<sessionId>.jsonl.
A call is one message id: Claude Code writes a call as one line per content block, each with the call's id and usage,
writes '<synthetic>' lines of its own, which are no call, and writes a resumed session under a new id whose transcript
begins with a copy of the session it resumes: each call is counted once, under the session that started first.
startup_report.py imports the parsing below.
Cost constants below are the API list prices per million tokens of PRICES_AS_OF from PRICES_URL (the 1-hour cache
write; Haiku 5.5 at its price for prompts up to 100,000 tokens); the report prints that date and page first: check
them before quoting a figure.
The subscription's limit is not dollars, but it weighs tokens the same way, so the ranking holds.
"""

import argparse
import collections
import datetime
import glob
import json
import os
import subprocess

PRICES_AS_OF = "2026-10-29"
PRICES_URL = "https://platform.claude.com/docs/en/about-claude/pricing"
PRICE = {  # $ per 1M tokens: input, output, cache read, cache write (1h)
    "opus": (4.0, 20.0, 0.20, 8.0),
    "sonnet": (2.0, 10.0, 0.10, 4.0),
    "haiku": (0.10, 0.50, 0.01, 0.20),
    "fable": (10.0, 50.0, 0.25, 20.0),
}


def family(model):
    m = (model or "").lower()
    return next((f for f in PRICE if f in m), "opus")


def agent_rows(prefix=""):
    """The rows of `claude agents --json --all` with a session id and a name that starts with prefix, the earliest
    start first."""
    rows = json.loads(
        subprocess.run(["claude", "agents", "--json", "--all"], capture_output=True, text=True, check=True).stdout
        or "[]"
    )
    return sorted(
        (r for r in rows if (r.get("name") or "").startswith(prefix) and r.get("sessionId")),
        key=lambda r: r.get("startedAt") or 0,
    )


def agent_sessions(prefix=""):
    """sessionId -> name for every session `claude agents --json --all` lists under a name that starts with prefix."""
    return {r["sessionId"]: r.get("name") or "" for r in agent_rows(prefix)}


def started(row):
    """A row's startedAt (epoch ms) in the transcripts' form, '2026-10-26T07:15:08.123Z'; '' when it has none."""
    ms = row.get("startedAt")
    if not isinstance(ms, (int, float)):
        return ""
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def transcripts(sid):
    return glob.glob(os.path.expanduser(f"~/.claude/projects/*/{sid}.jsonl"))


def lines(path):
    """(key, line) for each line of a transcript that carries a usage, in file order; key is the call's message id.
    The lines of one call share its id and usage, and a tool's result can come between two of them: count a call
    once per key. '<synthetic>' lines ("No response requested.", a usage-limit notice, an API error) are left out."""
    with open(path, encoding="utf-8", errors="ignore") as f:
        for n, line in enumerate(f):
            if '"usage"' not in line:
                continue
            try:
                d = json.loads(line)
                m = d["message"]
                if not isinstance(m["usage"], dict) or m.get("model") == "<synthetic>":
                    continue
            except (ValueError, KeyError, TypeError):
                continue
            yield m.get("id") or d.get("requestId") or (path, n), d


def calls(path, seen=None):
    """The first line of each call of a transcript, in file order, except the calls in `seen` (a set of call keys to
    share across transcripts: a resumed session's transcript begins with the calls of the session it resumes)."""
    seen = set() if seen is None else seen
    for key, d in lines(path):
        if key not in seen:
            seen.add(key)
            yield d


def context(u):
    """A call's context: its input, cache write and cache read tokens."""
    return sum(u.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))


def dollars(message):
    """One call's price by kind at its model family's prices: (input, output, cache read, cache write) dollars, in the
    order of PRICE. `message` is the call's `message` (its model and usage); `calls()` gives a call once, so a sum of
    these is the report's cost."""
    usage = message.get("usage") or {}
    kinds = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    return tuple((usage.get(k) or 0) * price / 1e6 for k, price in zip(kinds, PRICE[family(message.get("model"))]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="")
    ap.add_argument("--since", default="")
    ap.add_argument("--by-day", action="store_true")
    args = ap.parse_args(argv)

    stats = collections.defaultdict(
        lambda: {
            "calls": 0,
            "in": 0,
            "cw": 0,
            "cr": 0,
            "out": 0,
            "cost": 0.0,
            "cw_usd": 0.0,
            "cr_usd": 0.0,
            "out_usd": 0.0,
            "sessions": set(),
            "ctx_sum": 0,
        }
    )
    seen = set()
    for sid, name in agent_sessions(args.prefix).items():
        for path in transcripts(sid):
            for d in calls(path, seen):
                u = d["message"]["usage"]
                ts = d.get("timestamp", "")
                if args.since and ts[:10] < args.since:
                    continue
                key = (name, ts[:10]) if args.by_day else (name, "")
                s = stats[key]
                i, cw, cr, o = (
                    u.get(k) or 0
                    for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
                )
                paid_in, paid_out, paid_cr, paid_cw = dollars(d["message"])
                s["calls"] += 1
                s["in"] += i
                s["cw"] += cw
                s["cr"] += cr
                s["out"] += o
                s["ctx_sum"] += context(u)
                s["cost"] += paid_in + paid_out + paid_cr + paid_cw
                s["cr_usd"] += paid_cr
                s["cw_usd"] += paid_cw
                s["out_usd"] += paid_out
                s["sessions"].add(sid)

    print(f"prices of {PRICES_AS_OF} from {PRICES_URL}")
    print(
        f"{'agent':28} {'day':10} {'sess':>4} {'calls':>6} {'avg ctx':>8} {'cache rd':>9} {'rd $':>8} {'cache wr':>9} "
        f"{'wr $':>8} {'output':>8} {'out $':>8} {'$ equiv':>8}"
    )
    total = 0.0
    for (name, day), s in sorted(stats.items(), key=lambda kv: -kv[1]["cost"]):
        avg = s["ctx_sum"] // max(s["calls"], 1)
        total += s["cost"]
        print(
            f"{name[:28]:28} {day:10} {len(s['sessions']):4} {s['calls']:6} {avg:8,} {s['cr']:9,} {s['cr_usd']:8.2f} "
            f"{s['cw']:9,} {s['cw_usd']:8.2f} {s['out']:8,} {s['out_usd']:8.2f} {s['cost']:8.2f}"
        )
    # the total row holds only the total: surface.py quotes its last field
    print(f"{'total':28} {'':10} {'':4} {'':6} {'':8} {'':9} {'':8} {'':9} {'':8} {'':8} {'':8} {total:8.2f}")


if __name__ == "__main__":
    main()
