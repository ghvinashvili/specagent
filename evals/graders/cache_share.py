#!/usr/bin/env python3
"""Deterministic grader: exit 0 when the sessions of a trial shared their system prompt in the prompt cache.

Reads the trial's `cache.json` (written by the eval runner, one entry per session). Two things must hold:
the knowledge pack is part of every session's system prompt, and every session after the first found that system
prompt in the cache on its first request. The second check uses a floor of one token per five characters of the
system prompt: the tools add to what is read, so a real hit lies well above it, and a miss reads nothing.
"""

import json
import sys
from pathlib import Path


def main() -> int:
    sessions = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    problems = []
    for n, s in enumerate(sessions, 1):
        if not s.get("pack_chars"):
            problems.append(f"session {n}: no knowledge pack")
        elif (s.get("system_prompt_chars") or 0) < s["agent_chars"] + s["pack_chars"] - 4:
            problems.append(
                f"session {n}: the pack is not in the system prompt ({s.get('system_prompt_chars')} characters)"
            )
        if n > 1 and (s.get("first_request_cache_read") or 0) < 0.2 * (s.get("system_prompt_chars") or 0):
            problems.append(
                f"session {n}: first request read {s.get('first_request_cache_read')} tokens from the cache; "
                f"the system prompt has {s.get('system_prompt_chars')} characters"
            )
    if len(sessions) < 2:
        problems.append("the case needs at least two sessions")
    print("; ".join(problems) or f"shared: {[s.get('first_request_cache_read') for s in sessions]}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
