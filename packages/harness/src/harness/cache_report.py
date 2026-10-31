#!/usr/bin/env python3
"""Prompt-cache report for Claude Code session transcripts (.jsonl).

Reads only the `usage` block of each API response (never message content) and prints, per session:
requests, tokens read from cache / written to cache / uncached, the hit ratio, what the input cost and
what it would have cost without caching, and every request that missed the cache with its likely cause.

Usage:  cache_report.py [--misses N] [--json] SESSION.jsonl [SESSION.jsonl ...]

Prices are USD per million tokens from https://platform.claude.com/docs/en/build-with-claude/prompt-caching
(table read 2026-10-01). A model that is not in the table is reported in tokens only.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# model-id prefix -> (base input, 5m write, 1h write, cache read, output)
PRICES = {
    "claude-fable-5-1": (10.0, 12.5, 20.0, 0.25, 50.0),
    "claude-opus-5-5": (4.0, 5.0, 8.0, 0.20, 20.0),
    "claude-opus-5": (5.0, 6.25, 10.0, 0.50, 25.0),
    "claude-opus-4-8": (5.0, 6.25, 10.0, 0.50, 25.0),
    "claude-opus-4-7": (5.0, 6.25, 10.0, 0.50, 25.0),
    "claude-sonnet-5": (2.0, 2.5, 4.0, 0.20, 10.0),
    "claude-sonnet-5-5": (2.0, 2.5, 4.0, 0.20, 10.0),
    "claude-haiku-4-5": (1.0, 1.25, 2.0, 0.10, 5.0),
}
TTL_SECONDS = {"5m": 300, "1h": 3600}
MISS_SHARE = 0.5  # a request is a miss when less than half of its prompt came from the cache
MIN_PROMPT = 2000  # ignore tiny helper requests


def price(model: str):
    for prefix, p in PRICES.items():
        if model.startswith(prefix):
            return p
    return None


def requests(path: Path):
    """One record per API response (transcripts repeat the usage block once per content block)."""
    # Output tokens grow while a response streams, and the transcript stores one record per content block:
    # keep the first record of a response for the input side and the largest output count seen for it.
    out_max: dict = {}
    for line in path.open(errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        m = d.get("message") or {}
        u = m.get("usage")
        if d.get("type") == "assistant" and u and m.get("id"):
            out_max[m["id"]] = max(out_max.get(m["id"], 0), u.get("output_tokens", 0))
    seen = set()
    for line in path.open(errors="replace"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        m = d.get("message") or {}
        u = m.get("usage")
        if d.get("type") != "assistant" or not u or m.get("id") in seen or m.get("model") == "<synthetic>":
            continue
        seen.add(m.get("id"))
        u = dict(u, output_tokens=out_max.get(m.get("id"), u.get("output_tokens", 0)))
        cc = u.get("cache_creation") or {}
        w1h = cc.get("ephemeral_1h_input_tokens", 0)
        w5m = cc.get("ephemeral_5m_input_tokens", 0)
        if not cc:
            w5m = u.get("cache_creation_input_tokens", 0)
        try:
            ts = datetime.fromisoformat(d["timestamp"])
        except (KeyError, ValueError):
            ts = None
        yield {
            "ts": ts,
            "model": m.get("model", "?"),
            "uncached": u.get("input_tokens", 0),
            "read": u.get("cache_read_input_tokens", 0),
            "w5m": w5m,
            "w1h": w1h,
            "out": u.get("output_tokens", 0),
        }


def analyse(path: Path, max_misses: int) -> dict:
    rs = list(requests(path))
    tot = {k: 0 for k in ("uncached", "read", "w5m", "w1h", "out")}
    cost = no_cache = 0.0
    unpriced = 0
    misses, prev = [], None
    for i, r in enumerate(rs):
        for k in tot:
            tot[k] += r[k]
        prompt = r["uncached"] + r["read"] + r["w5m"] + r["w1h"]
        p = price(r["model"])
        if p:
            cost += (r["uncached"] * p[0] + r["w5m"] * p[1] + r["w1h"] * p[2] + r["read"] * p[3]) / 1e6
            no_cache += prompt * p[0] / 1e6
        else:
            unpriced += prompt
        gap = (r["ts"] - prev["ts"]).total_seconds() if prev and r["ts"] and prev["ts"] else None
        if i > 0 and prompt >= MIN_PROMPT and r["read"] < MISS_SHARE * prompt:
            ttl = "1h" if (prev["w1h"] or r["w1h"]) else "5m"
            if prev["model"] != r["model"]:
                cause = f"model changed {prev['model']} -> {r['model']}"
            elif gap is not None and gap > TTL_SECONDS[ttl]:
                cause = f"idle {gap / 60:.0f} min, longer than the {ttl} lifetime"
            elif prompt < 0.6 * (prev["uncached"] + prev["read"] + prev["w5m"] + prev["w1h"]):
                cause = "prompt shrank: compaction or a new conversation"
            else:
                cause = "prefix changed (tools, system prompt, project context or edited history)"
            misses.append(
                {
                    "n": i + 1,
                    "at": r["ts"].isoformat(timespec="minutes") if r["ts"] else "?",
                    "prompt": prompt,
                    "model": r["model"],
                    "read": r["read"],
                    "gap_min": round(gap / 60, 1) if gap is not None else None,
                    "cause": cause,
                }
            )
        prev = r
    prompt_total = tot["uncached"] + tot["read"] + tot["w5m"] + tot["w1h"]
    first = rs[0] if rs else None
    return {
        "session": path.name,
        "requests": len(rs),
        "models": sorted({r["model"] for r in rs}),
        "prompt_tokens": prompt_total,
        "read": tot["read"],
        "written_5m": tot["w5m"],
        "written_1h": tot["w1h"],
        "uncached": tot["uncached"],
        "output": tot["out"],
        "hit_ratio": round(tot["read"] / prompt_total, 4) if prompt_total else None,
        "first_request_write": (first["w5m"] + first["w1h"]) if first else 0,
        "first_request_read": first["read"] if first else 0,
        "input_cost_usd": round(cost, 2),
        "input_cost_without_cache_usd": round(no_cache, 2),
        "unpriced_prompt_tokens": unpriced,
        "miss_count": len(misses),
        "misses": misses[:max_misses],
    }


def of_run(root: Path, run_id: str, max_misses: int = 8) -> dict:
    """The report for every session of a run, found by the session ids in its state.json. The first-request numbers
    show what a session shared with the sessions before it: `first_request_read` is the prefix it found in the cache."""
    from . import launch, state

    st = json.loads((state.runs_root(root) / run_id / "state.json").read_text(encoding="utf-8"))
    sessions, missing = [], []
    for stage_id, ss in st["stages"].items():
        units = sorted(ss["shards"].items()) if ss.get("shards") else [("", ss)]
        for shard, u in units:
            for sid in u.get("session_ids", []):
                log = launch.transcript_of(sid)
                if log is None:
                    missing.append(sid)
                    continue
                sessions.append({"stage": stage_id + (f"/{shard}" if shard else ""), **analyse(log, max_misses)})
    # A role session runs on a model of the policy's list, whatever the user's own default is.
    from . import access

    allowed = access.load_policy(root)["defaults"].get("models") or []
    outside = [
        {"stage": s["stage"], "session": s["session"], "models": bad}
        for s in sessions
        if (bad := [m for m in s["models"] if allowed and not any(name in m for name in allowed)])
    ]
    return {
        "ok": not outside,
        "run_id": run_id,
        "sessions": sessions,
        "no_transcript": missing,
        "outside_model_policy": outside,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--misses", type=int, default=8, help="how many misses to list per session")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    out = [analyse(f, a.misses) for f in a.files]
    if a.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    for s in out:
        print(f"\n{s['session']}  models={','.join(s['models'])}")
        print(
            f"  requests {s['requests']}, prompt tokens {s['prompt_tokens']:,}: read {s['read']:,}, "
            f"written 5m {s['written_5m']:,} / 1h {s['written_1h']:,}, uncached {s['uncached']:,}; output {s['output']:,}"
        )
        hr = f"{s['hit_ratio'] * 100:.1f}%" if s["hit_ratio"] is not None else "n/a"
        print(
            f"  hit ratio {hr}; first request read {s['first_request_read']:,} and wrote {s['first_request_write']:,} tokens"
        )
        note = (
            f" ({s['unpriced_prompt_tokens']:,} prompt tokens on models without a price are not counted)"
            if s["unpriced_prompt_tokens"]
            else ""
        )
        print(
            f"  input cost ${s['input_cost_usd']:.2f}; without caching ${s['input_cost_without_cache_usd']:.2f}{note}"
        )
        print(f"  misses after the first request: {s['miss_count']}")
        for m in s["misses"]:
            print(
                f"    #{m['n']} {m['at']} prompt {m['prompt']:,} read {m['read']:,} gap {m['gap_min']} min — {m['cause']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
