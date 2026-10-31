#!/usr/bin/env python3
"""SessionEnd hook: record the transcript path and the end reason of a role session (archive pointer)."""

import datetime as dt
import json
import os
import sys
from pathlib import Path


def main() -> int:
    data = json.load(sys.stdin)
    run_dir = os.environ.get("HARNESS_RUN_DIR")
    stage = os.environ.get("HARNESS_STAGE")
    if not run_dir or not stage:
        return 0
    log = (
        Path(run_dir) / "stages" / stage / os.environ.get("HARNESS_SHARD", "") / "logs" / "session-end.jsonl"
    )  # per shard
    log.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "session_id": data.get("session_id"),
        "reason": data.get("reason"),
        "transcript_path": data.get("transcript_path"),
    }
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
