#!/usr/bin/env python3
"""PreToolUse(Bash) hook: deny a command that a rule of .claude/hooks/guard-bash.json names.

A rule is a `pattern`, matched against the command as written and against every simple command shellwords.py reads in
it, or a `check`, a function of this file over those simple commands (separators, quotes, line continuations, and the
wrappers `env`, `sudo`, `exec`, `bash -c` and the rest taken off). A rule with `"when": "role"` holds in a role session
only. The rules refuse the plain spellings: what a command builds at run time (a variable, a brace, a function, a pipe
into `sh`) is held by the sandbox of a role session and by the write gate, which judges a commit on what it changes
(docs/decisions/0025; test_boundary_settings.py, test_closed_paths.py). The rules and the settings come from the main
checkout (CLAUDE_PROJECT_DIR, mapped to the main checkout when it is a checkout); where the shell stands is the input's
`cwd`. A hook that cannot decide refuses the call with exit 2: exit 1 would let it through (docs/decisions/0020).
"""

import fnmatch
import glob
import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shellwords

# A run's JSON files and its escalations, wherever a word names them (a path, a redirection, inline code).
RUN_JSON = re.compile(
    r"(?:^|[^\w.-])(?:result|tasks|gate|escalation|manifest|state|checks)\.json\b|escalations/[0-9]{3}\.json"
    r"|(?:^|/)escalations/?$"
)
READERS = {"cat", "head", "tail", "less", "more", "jq", "grep", "egrep", "fgrep", "rg", "wc", "ls", "stat", "file",
           "diff", "cmp", "sha256sum", "md5sum", "readlink", "realpath", "test", "[", "git"}  # fmt: skip
REDIRECTS = {">", ">>", ">|", "&>", "&>>", ">&", "<>"}
INBOX = re.compile(r"(?:^|[^\w.-])_inbox(?:/|$|[^\w.-])")
RECURSIVE = {"find", "rg", "fd", "fdfind", "ag", "tree", "du", "tar", "zip", "rsync"}
RECURSE_FLAG = {"grep": "rR", "egrep": "rR", "fgrep": "rR", "ls": "R", "cp": "rRa", "scp": "r"}
GIT_VALUED = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env", "--super-prefix"}
WHOLE_TREE = {".", "./", "*", ":", ":/", ":/.", ":/*", ":(top)", ":(top).", ":(top)*"}


def main_checkout(path: Path) -> Path:
    """The main checkout of a checkout under `.claude/worktrees/`, as stop-gate.py maps it; else the path itself."""
    return path.parents[2] if path.parent.name == "worktrees" and path.parents[1].name == ".claude" else path


def runs_root(root: Path) -> Path:
    """harness.state.runs_root without the harness package: ../runs when that folder carries .harness-runs,
    otherwise ../<repo>-runs (packages/harness/tests/test_layout.py holds the two to one rule)."""
    shared = root.parent / "runs"
    return shared if (shared / ".harness-runs").is_file() else root.parent / f"{root.name}-runs"


def deny(reason: str) -> None:
    out = {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}
    print(json.dumps({"hookSpecificOutput": out}))


def _path(word: str, cwd: Path) -> Path:
    p = Path(os.path.expandvars(os.path.expanduser(word)))
    return Path(os.path.abspath(p if p.is_absolute() else cwd / p))


def _globbed(word: str, cwd: Path) -> list[str]:
    if not any(c in word for c in "*?["):
        return []
    return glob.glob(str(_path(word, cwd)))[:200]


def inbox(commands, cwd: Path, root: Path, raw: str) -> bool:
    """A command that reads under <runs root>/_inbox/, by any program, a glob, or a search rooted above it."""
    if os.environ.get("HARNESS_ROLE") == "quarantine-reader":
        return False
    if commands is None:
        return bool(INBOX.search(raw))
    run_dir = os.environ.get("HARNESS_RUN_DIR")
    box = (Path(run_dir).parent if run_dir else runs_root(root)) / "_inbox"
    for argv in commands:
        if any(INBOX.search(w) or any(INBOX.search(m) for m in _globbed(w, cwd)) for w in argv):
            return True
        name = argv[0].rsplit("/", 1)[-1] if argv else ""
        flags = "".join(w[1:] for w in argv[1:] if w.startswith("-") and not w.startswith("--"))
        recursive = name in RECURSIVE or (name in RECURSE_FLAG and (set(flags) & set(RECURSE_FLAG[name])
                                                                    or "--recursive" in argv))  # fmt: skip
        if recursive and any(box.is_relative_to(_path(w, cwd)) for w in argv[1:] if not w.startswith("-")):
            return True
    return False


def run_files(commands, cwd: Path, root: Path, raw: str) -> bool:
    """A shell command that names a run's JSON file or its escalations, other than a reader that only reads it."""
    for argv in commands or []:
        name = argv[0].rsplit("/", 1)[-1] if argv else ""
        for i, word in enumerate(argv):
            if RUN_JSON.search(word) and (name not in READERS or (i > 0 and argv[i - 1] in REDIRECTS)):
                return True
    return False


def _sweeps(
    args: list[str], letters: str, long: tuple, short_valued: str, long_valued: set, attached: str = ""
) -> bool:
    """Whether `git add` or `git commit` arguments take the whole tree: an option of `letters` (in any cluster), a
    long one or its abbreviation, or a pathspec that is the top or the current directory. `short_valued` options take
    a value (the rest of their cluster, else the next word); `attached` ones only the rest of their cluster."""
    i, plain = 0, False
    while i < len(args):
        arg = args[i]
        i += 1
        if plain or not arg.startswith("-") or arg == "-":
            if arg in WHOLE_TREE or os.path.normpath(arg) == "." or (arg.startswith(":(") and "top" in arg):
                return True
            continue
        if arg == "--":
            plain = True
            continue
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            if name == "--pathspec-from-file" or any(full.startswith(name) and len(name) >= 4 for full in long):
                return True
            if name in long_valued and "=" not in arg:
                i += 1
            continue
        for j, ch in enumerate(arg[1:]):
            if ch in letters:
                return True
            if ch in short_valued or ch in attached:
                if ch in short_valued and j == len(arg) - 2:
                    i += 1  # the value is the next word
                break  # the rest of the cluster is the value
    return False


def git_sweep(commands, cwd: Path, root: Path, raw: str) -> bool:
    """`git add -A`, `git add .`, `git commit -a` and the other plain spellings that stage or commit the whole tree."""
    for argv in commands or []:
        if not argv or argv[0].rsplit("/", 1)[-1] != "git":
            continue
        i = 1
        while i < len(argv) and argv[i].startswith("-"):
            i += 2 if argv[i] in GIT_VALUED else 1
        sub, args = (argv[i], argv[i + 1 :]) if i < len(argv) else ("", [])
        if sub in ("add", "stage") and _sweeps(args, "Au", ("--all", "--update", "--no-ignore-removal"), "", set()):
            return True
        commit_valued = {"--message", "--file", "--reuse-message", "--reedit-message", "--template", "--author",
                         "--date", "--cleanup", "--fixup", "--squash", "--trailer"}  # fmt: skip
        if sub == "commit" and _sweeps(args, "a", ("--all",), "mFCct", commit_valued, attached="uS"):
            return True
    return False


def unsandboxed(commands, cwd: Path, root: Path, raw: str) -> bool:
    """A command of `sandbox.excludedCommands` (it runs outside the sandbox), also behind a wrapper or in `bash -c`."""
    patterns: list[str] = []
    for name in ("settings.json", "settings.local.json"):
        path = root / ".claude" / name
        if path.is_file():
            patterns += json.loads(path.read_text(encoding="utf-8")).get("sandbox", {}).get("excludedCommands", [])
    return any(fnmatch.fnmatchcase(" ".join(argv), p) for argv in commands or [] for p in patterns)


def unreadable(commands, cwd: Path, root: Path, raw: str) -> bool:
    return commands is None


CHECKS = {f.__name__: f for f in (inbox, run_files, git_sweep, unsandboxed, unreadable)}


def main() -> int:
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    root = main_checkout(Path(os.environ["CLAUDE_PROJECT_DIR"]).resolve())
    rules = json.loads((root / ".claude" / "hooks" / "guard-bash.json").read_text(encoding="utf-8"))
    in_role = bool(os.environ.get("HARNESS_RUN_DIR"))
    cwd = Path(data.get("cwd") or os.getcwd())
    commands = shellwords.simple_commands(command)
    texts = [command, *(shlex.join(argv) for argv in commands or [])]
    for rule in rules["deny"]:
        if rule.get("when") == "role" and not in_role:  # a rule for role sessions only
            continue
        if "pattern" in rule:
            hit = any(re.search(rule["pattern"], text) for text in texts)
        else:
            hit = CHECKS[rule["check"]](commands, cwd, root, command)
        if hit:
            deny(rule["reason"])
            return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - a guard that cannot decide refuses the call (exit 2 blocks it)
        print(f"guard-bash: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
