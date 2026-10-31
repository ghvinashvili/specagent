"""harness/trust.py — the record that the human trusts the checkout, which `claude --bg` needs.

Claude Code keeps it as `hasTrustDialogAccepted` in the checkout's entry under `projects` of ~/.claude.json, and looks
for it from the folder up to the repository's root and no higher: a checkout moved into a trusted container folder was
refused, and a session in bypass mode never showed the dialog that records it (seen 2026-10-03). The launcher records
it before it starts or resumes a role session: the human asked for the run in this checkout, and its sessions run the
checkout's code already (docs/decisions/0013-no-command-to-type-and-at-most-one-password.md)."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path


def claude_json() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home()) / ".claude.json"


def trusted(root: Path, config: Path | None = None) -> bool:
    """Whether the checkout's trust is recorded; True before Claude Code's first start, which asks by itself."""
    config = config or claude_json()
    if not config.is_file():
        return True
    projects = json.loads(config.read_text(encoding="utf-8")).get("projects", {})
    return bool(projects.get(str(root.resolve()), {}).get("hasTrustDialogAccepted"))


def record(root: Path, config: Path | None = None, tries: int = 3) -> bool:
    """Record the trust as the dialog would: the flag alone in the checkout's entry, nothing else of the entry or the
    file changed. Claude Code writes the file too, so a write is given up when the file changed while it was prepared,
    and tried again. True when the record was written; a machine where Claude Code never ran is left alone."""
    config = config or claude_json()
    key = str(root.resolve())
    for _ in range(tries):
        if not config.is_file():
            return False
        before = config.stat()
        doc = json.loads(config.read_text(encoding="utf-8"))
        entry = doc.setdefault("projects", {}).setdefault(key, {})
        if entry.get("hasTrustDialogAccepted"):
            return False
        entry["hasTrustDialogAccepted"] = True
        tmp = _temporary(config, json.dumps(doc, indent=2, ensure_ascii=False))
        os.chmod(tmp, before.st_mode & 0o777)
        now = config.stat()
        if (now.st_mtime_ns, now.st_size) != (before.st_mtime_ns, before.st_size):
            tmp.unlink()  # Claude Code wrote meanwhile: read again rather than undo its change
            time.sleep(0.2)
            continue
        os.replace(tmp, config)  # whole or not at all: Claude Code reads this file at every start
        return True
    return False


def _temporary(config: Path, text: str) -> Path:
    """A file of its own beside the config (the shards of a stage launch one after another, but never share one)."""
    fd, name = tempfile.mkstemp(dir=config.parent, prefix=config.name + ".", suffix=".harness-tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        out.write(text)
    return Path(name)


def ensure(root: Path) -> str | None:
    """Before `claude --bg`: record the trust when it is missing. Returns a note for the launcher's answer, or None."""
    try:
        if trusted(root):
            return None
        return f"trust recorded for {root.resolve()}" if record(root) else None
    except (OSError, ValueError) as exc:  # `claude --bg` then names the refusal itself
        return f"trust not recorded: {exc}"
