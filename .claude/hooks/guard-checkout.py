#!/usr/bin/env python3
"""PreToolUse(Bash, Read, Grep, Glob, Edit, Write): a role session that has a checkout of its own
touches the repository only from inside it. HARNESS_WORKTREE names the checkout: a writer's own branch, a planner's
trial, or the work a reviewing stage receives. The session starts in the shared checkout, which does not hold the work:
a test run or a file read there says something about the base, and a reviewer would report it as a finding about the
work. The plain spellings of a command or a path of the shared checkout are refused wherever the shell stands, its own
checkout included; its stage directory and the other directories outside the repository stay open, so it can read its
first message and its inputs. A search rooted above the repository reaches into it and is refused too, and so is a
Glob whose pattern climbs into the shared checkout or above it (packages/harness/tests/test_plain_spellings.py).

A shell that has left the checkout can come back. Seen live: a planner ran `cd` into its stage directory, every later
command was refused with "call EnterWorktree", and EnterWorktree answered "already in a worktree session"; the
session could do nothing but escalate. So a path inside the checkout is open whatever the working directory is, and
`cd <checkout>` is always the way back; what follows it in the same command is judged from there.

A command is read for its plain spellings (shellwords.py): every word that names a path by `~`, `..`, a variable of the
hook's own environment, a glob or an absolute path is resolved from the directory the command runs in, and a `cd`
moves that directory. A command that builds a path with `$( )` or backquotes is refused. What else the shell builds at
run time (a variable the command sets, a brace, a `cd` option, `CDPATH`) is not read here: once the session has entered
its checkout, its sandbox hides the shared checkout from every shell command (docs/decisions/0025;
test_boundary_settings.py). The repository is the main checkout of CLAUDE_PROJECT_DIR; where the shell stands is the
input's `cwd`, compared as a path. A hook that cannot decide refuses the call (exit 2).
"""

import glob
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shellwords

DYNAMIC = ("$(", "`", "<(", ">(")


def main_checkout(path: Path) -> Path:
    """The main checkout of a checkout under `.claude/worktrees/`, as stop-gate.py maps it; else the path itself."""
    return path.parents[2] if path.parent.name == "worktrees" and path.parents[1].name == ".claude" else path


def resolve(word: str, cwd: Path) -> Path:
    """A word as a path from `cwd`: `~` and variables expanded (`$PWD` is where the command runs)."""
    word = word.replace("${PWD}", str(cwd)).replace("$PWD", str(cwd))
    p = Path(os.path.expandvars(os.path.expanduser(word)))
    return Path(os.path.abspath(p if p.is_absolute() else cwd / p)).resolve()


def candidates(word: str, cwd: Path) -> list[Path]:
    """The paths a word may name: the word itself, the value of `--opt=value` or `NAME=value`, what a glob matches."""
    values = [word, *([word.split("=", 1)[1]] if "=" in word else [])]
    out = []
    for v in values:
        if "/" in v or v.startswith("~") or v in (".", ".."):
            out.append(resolve(v, cwd))
            if any(c in v for c in "*?["):
                out += [Path(m).resolve() for m in glob.glob(str(resolve(v, cwd)))[:200]]
    return out


class Repo:
    def __init__(self, root: Path, checkout: Path) -> None:
        self.root, self.checkout = root, checkout

    def shared(self, path: Path) -> bool:
        """Inside the repository and not inside the session's own checkout."""
        inside = path == self.root or self.root in path.parents
        return inside and not (path == self.checkout or self.checkout in path.parents)

    def above(self, path: Path) -> bool:
        """A folder that holds the repository: a search rooted there reaches into it."""
        return path in self.root.parents

    def command(self, command: str, here: Path) -> bool:
        """Whether a Bash command reads, runs in or names the shared checkout."""
        if any(d in command for d in DYNAMIC):
            return True
        commands, words = shellwords.simple_commands(command), shellwords.tokens(command)
        if commands is None or words is None:
            return True
        cwd = here
        for argv in commands:
            if argv and argv[0] in ("cd", "pushd"):
                rest = [w for w in argv[1:] if w != "--"]
                cwd = resolve(rest[0], cwd) if rest else Path.home().resolve()
                if self.shared(cwd) or self.above(cwd):
                    return True
                continue
            if self.shared(cwd):
                return True  # a command that runs in the shared checkout
            if any(self.shared(p) for w in argv for p in candidates(w, cwd)):
                return True
        # what the simple commands do not show: a wrapper's own options (`env -C <dir>`), a redirection's target
        fixed = [w for w in words if w.split("=", 1)[-1].startswith(("/", "~", "$"))]
        return any(self.shared(p) for w in fixed for p in candidates(w, here))


def main() -> int:
    data = json.load(sys.stdin)
    name = os.environ.get("HARNESS_WORKTREE")
    if not name or not os.environ.get("HARNESS_RUN_DIR"):
        return 0
    root = main_checkout(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve())
    repo = Repo(root, root / ".claude" / "worktrees" / name)
    here = Path(data["cwd"]).resolve() if data.get("cwd") else root
    tool, tool_input = data.get("tool_name"), data.get("tool_input") or {}
    if tool != "Bash":
        raw = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path")
        targets = [resolve(raw, here) if raw else here]
        if tool == "Glob":  # a pattern searches the folder it names before its first wildcard, wherever it climbs
            prefix = re.split(r"[*?\[{]", str(tool_input.get("pattern") or ""), maxsplit=1)[0]
            targets.append(resolve(prefix.rsplit("/", 1)[0] or "/" if "/" in prefix else ".", targets[0]))
        search = tool in ("Grep", "Glob")
        if not any(repo.shared(t) or (search and repo.above(t)) for t in targets):
            return 0  # outside the repository (the stage directory, the escalations), or inside the checkout
    inside = here == repo.checkout or repo.checkout in here.parents
    entered = repo.checkout.is_dir() or inside
    if tool == "Bash" and entered and not repo.command(str(tool_input.get("command") or ""), here):
        return 0
    if inside:
        reason = (
            f"This reaches the shared checkout, which does not hold your work: read and run only inside your own "
            f"checkout, {repo.checkout}, by paths inside it."
        )
    elif entered:
        reason = (
            f"You are outside your checkout. Run `cd {repo.checkout}` first; it may stand in front of the command. The "
            "shared checkout does not hold your work; the repository is read and commands are run only inside your own."
        )
    else:
        reason = (
            f"Call the EnterWorktree tool with the name {name} first. You are in the shared checkout, which does not "
            "hold your work; the repository is read and commands are run only inside your own checkout."
        )
    out = {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}
    print(json.dumps({"hookSpecificOutput": out}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a guard that cannot decide refuses the call (exit 2 blocks it)
        print(f"guard-checkout: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
