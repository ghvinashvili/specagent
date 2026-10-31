"""harness/gates/advise.py — the advisor stage gate, per shard: a short answer that does not name its own perspective."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ._common import check, stage_file, text


def checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    answer = text(stage_dir, "output/answer.md")
    words = len(re.findall(r"\S+", answer))
    path = stage_file(stage_dir, "tasks.json")  # None for a link out of the stage directory
    tasks = json.loads(path.read_text(encoding="utf-8"))["tasks"] if path else []
    named = [t["category"] for t in tasks if t["category"].strip() and t["category"].lower() in answer.lower()]
    return [
        check("answer.md exists", bool(answer)),
        check("answer.md has 150 to 300 words", 150 <= words <= 300, str(words)),
        check("the answer does not name its perspective", not named, ", ".join(named)),
        check("the task of the shard passes", bool(tasks) and all(t["passes"] for t in tasks)),
    ]
