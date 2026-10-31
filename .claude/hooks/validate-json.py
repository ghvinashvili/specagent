#!/usr/bin/env python3
"""PreToolUse(Write) + PostToolUse(Edit) hook: validate a run's JSON files against schemas/.
A Write is denied before it happens (its content is in tool_input). An Edit can only be checked after it happened
(PostToolUse runs after the tool executed), so the violation is reported back and the model must rewrite the file.
Only a run's JSON files are held to the check: every other `.json` a session writes (a tsconfig.json with a comment)
passes as it is. The schemas are the main checkout's (CLAUDE_PROJECT_DIR, mapped to the main checkout when it is a
checkout). A hook that cannot decide refuses the call (exit 2)."""

import json
import os
import re
import sys
from pathlib import Path

RUN = r"/[0-9]{8}-[0-9]{6}-[a-z0-9-]+"  # a run directory anywhere under the runs root (outside the repository)
SCHEMA_FOR = [
    (RUN + r"/manifest\.json$", "run-manifest"),
    (RUN + r"/state\.json$", "run-state"),
    (RUN + r"/escalations/[0-9]{3}\.json$", "escalation"),
    (
        RUN + r"/stages/[^/]+(/[0-9]{2})?/escalation\.json$",
        "escalation",
    ),  # a blind session's question, filed by harness poll
    (RUN + r"/stages/[^/]+(/[0-9]{2})?/result\.json$", "stage-result"),
    (RUN + r"/stages/[^/]+(/[0-9]{2})?/gate\.json$", "gate-verdict"),
    (RUN + r"/stages/[^/]+(/[0-9]{2})?/tasks\.json$", "tasks"),
]


def main_checkout(path: Path) -> Path:
    """The main checkout of a checkout under `.claude/worktrees/`, as stop-gate.py maps it; else the path itself."""
    return path.parents[2] if path.parent.name == "worktrees" and path.parents[1].name == ".claude" else path


def _jsonschema():
    """python3's own jsonschema, or the workspace's when the workspace was made from the same Python (ops/bootstrap.py
    makes it so): a fresh machine has the workspace, not always python3-jsonschema. None when neither has it."""
    try:
        import jsonschema
    except ImportError:
        v = sys.version_info
        main = main_checkout(Path(os.environ.get("CLAUDE_PROJECT_DIR") or "."))
        sys.path.append(str(main / ".venv" / "lib" / f"python{v[0]}.{v[1]}" / "site-packages"))
        try:
            import jsonschema
        except ImportError:
            return None
    return jsonschema


def schema_of(file_path: str) -> str | None:
    """The schema of a run's JSON file, or None for any other file."""
    return next((n for pattern, n in SCHEMA_FOR if re.search(pattern, file_path)), None)


def problems(file_path: str, text: str) -> str | None:
    name = schema_of(file_path)
    if name is None:
        return None  # not a run's file: no check of its own
    try:
        document = json.loads(text)
    except Exception as exc:  # noqa: BLE001
        return f"{file_path} is not valid JSON: {exc}"
    jsonschema = _jsonschema()
    if jsonschema is None:
        return None  # parse-only where jsonschema is not installed
    root = main_checkout(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve())
    schema = json.loads((root / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft7Validator(schema).iter_errors(document), key=lambda e: list(e.path))
    if not errors:
        return None
    detail = "; ".join(f"{'/'.join(map(str, e.path)) or '$'}: {e.message}" for e in errors[:5])
    return f"{file_path} fails schemas/{name}.schema.json: {detail}"


def main() -> int:
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path", "")
    if not file_path.endswith(".json") or schema_of(file_path) is None:
        return 0
    if data.get("hook_event_name") == "PreToolUse" and data.get("tool_name") == "Write":
        reason = problems(file_path, tool_input.get("content", ""))
        if reason:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": reason,
                        }
                    }
                )
            )
        return 0
    if data.get("hook_event_name") == "PostToolUse" and data.get("tool_name") == "Edit":
        reason = problems(file_path, Path(file_path).read_text(encoding="utf-8"))
        if reason:
            print(
                json.dumps(
                    {
                        "decision": "block",
                        "reason": reason + " — the edit is already on disk: rewrite the whole file with Write.",
                    }
                )
            )
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a hook that cannot check a run's file refuses the call (exit 2)
        print(f"validate-json: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
