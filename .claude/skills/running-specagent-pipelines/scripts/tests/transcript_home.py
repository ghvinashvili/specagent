"""Shared by test_usage_report.py and test_startup_report.py: a HOME with synthetic transcripts in the live shape (one
line per content block, the blocks of a call sharing its message id and usage, a tool's result between two blocks of
its call; Claude Code's own '<synthetic>' lines) and a stub `claude` on PATH that answers `agents --json --all` with
the sessions written so far and logs every invocation.
"""

import datetime
import json
import os
import pathlib
import subprocess
import sys

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
STUB = """#!{python} -I
import os, pathlib, sys
state = pathlib.Path(os.environ["STUB_DIR"])
with open(state / "calls.log", "a") as f:
    f.write(" ".join(sys.argv[1:]) + "\\n")
if sys.argv[1:] == ["agents", "--json", "--all"]:
    print((state / "agents.json").read_text())
    sys.exit(0)
sys.exit(1)
"""
THINK = {"type": "thinking", "thinking": "Which file first?", "signature": "sig"}
TEXT = {"type": "text", "text": "Reading the note."}
SYNTHETIC = "synthetic"  # in a session's calls: a line Claude Code writes itself, with zero usage


def tool(name: str, **given) -> dict:
    return {"type": "tool_use", "id": f"toolu_{name}", "name": name, "input": given}


def read(path: str) -> dict:
    return tool("Read", file_path=path)


def bash(command: str) -> dict:
    return tool("Bash", command=command, description="a command")


def edit(path: str) -> dict:
    return tool("Edit", file_path=path, old_string="a", new_string="b")


def write(path: str) -> dict:
    return tool("Write", file_path=path, content="x\n")


class Home:
    """A HOME with transcripts under .claude/projects/-work/, the stub `claude` on PATH, and its session list."""

    def __init__(self, root: pathlib.Path):
        self.root = root
        self.projects = root / "home" / ".claude" / "projects" / "-work"
        self.stub = root / "stub"
        for d in (self.projects, self.stub, root / "bin"):
            d.mkdir(parents=True)
        claude = root / "bin" / "claude"
        claude.write_text(STUB.replace("{python}", sys.executable), encoding="utf-8")
        claude.chmod(0o755)
        self.rows = []
        self.save_rows()

    def save_rows(self):
        (self.stub / "agents.json").write_text(json.dumps(self.rows), encoding="utf-8")

    def session(self, name: str, sid: str, calls, start: str = "2026-10-23T10:00:00", resumes: str | None = None):
        """A transcript of `sid`, listed under `name` with `start` (UTC) as its startedAt. `calls`: (context, output
        tokens, content blocks) per call, or SYNTHETIC; each block is one line, and a tool_use line is followed by its
        result; one second per line from `start`. `resumes`: a session written before, whose lines this transcript
        begins with, as Claude Code writes a resumed session (under a new id, the history copied in)."""
        t = datetime.datetime.fromisoformat(start)

        def stamp() -> str:
            nonlocal t
            t += datetime.timedelta(seconds=1)
            return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        lines = []
        if resumes:
            for x in (self.projects / f"{resumes}.jsonl").read_text(encoding="utf-8").splitlines():
                lines.append({**json.loads(x), "sessionId": sid})
        lines.append(
            {
                "type": "user",
                "timestamp": stamp(),
                "sessionId": sid,
                "message": {"role": "user", "content": "You are a fresh session; read your note."},
            }
        )
        for i, call in enumerate(calls):
            if call == SYNTHETIC:
                lines.append(
                    {
                        "type": "assistant",
                        "timestamp": stamp(),
                        "sessionId": sid,
                        "message": {
                            "id": f"{sid[:8]}-synthetic-{i}",
                            "model": "<synthetic>",
                            "role": "assistant",
                            "content": [{"type": "text", "text": "No response requested."}],
                            "usage": {
                                "input_tokens": 0,
                                "output_tokens": 0,
                                "cache_creation_input_tokens": 0,
                                "cache_read_input_tokens": 0,
                            },
                        },
                    }
                )
                continue
            context, output, blocks = call
            usage = {
                "input_tokens": 3,
                "cache_creation_input_tokens": 7,
                "cache_read_input_tokens": context - 10,
                "output_tokens": output,
            }
            for block in blocks:
                lines.append(
                    {
                        "type": "assistant",
                        "timestamp": stamp(),
                        "sessionId": sid,
                        "requestId": f"req_{sid[:8]}_{i}",
                        "message": {
                            "id": f"msg_{sid[:8]}_{i}",
                            "model": "claude-opus-5-5",
                            "role": "assistant",
                            "content": [block],
                            "usage": usage,
                        },
                    }
                )
                if block["type"] == "tool_use":
                    lines.append(
                        {
                            "type": "user",
                            "timestamp": stamp(),
                            "sessionId": sid,
                            "message": {
                                "role": "user",
                                "content": [{"type": "tool_result", "tool_use_id": block["id"], "content": "ok"}],
                            },
                        }
                    )
        (self.projects / f"{sid}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")
        started = datetime.datetime.fromisoformat(start).replace(tzinfo=datetime.UTC)
        self.rows.append(
            {
                "name": name,
                "sessionId": sid,
                "state": "done",
                "kind": "background",
                "startedAt": int(started.timestamp() * 1000),
            }
        )
        self.save_rows()

    def env(self) -> dict:
        return {
            **os.environ,
            "PATH": f"{self.root / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.root / "home"),
            "STUB_DIR": str(self.stub),
        }

    def run(self, script: str, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-I", str(SCRIPTS / script), *args],
            capture_output=True,
            text=True,
            timeout=30,
            env=self.env(),
            cwd=self.root,
            check=False,
        )

    def claude_calls(self) -> list[str]:
        path = self.stub / "calls.log"
        return path.read_text().splitlines() if path.exists() else []
