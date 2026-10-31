#!/usr/bin/env python3
"""Replay cases from a run folder's findings: a finding's command at the commit before its fix, and at the fix.

  python3 replay_cases.py <run-dir> --repo <checkout> --out <dir> [--try]

For each `#### V<n>` section of verify.md and `#### J<n>` section of judge.md that records a shell command, its
output and a commit, it writes `<out>/<id>/task.yaml` (the fields of the checkout's `evals/*/task.yaml`) and
`<out>/<id>/grader.sh`: `sh grader.sh before` takes the paths the command reads from the checkout at the sha before
the fix (`git archive`), runs the command there and passes (exit 0) when the recorded output appears; `sh grader.sh
fix` passes when it does not appear at the fix sha; a second argument names another sha (`HEAD`: still fixed?).
`<out>/index.md` lists the cases, and every other section with its reasons. A reused heading (`#### V29, round 2`)
is a case of its own, `<out>/V29-2/`.

Command: the code span that begins the section's `Command` bullet (`- Command:`, `- Command (in the checkout):`, a
label with a code span: ``- Command (at <sha>, `python -I`):``), or the fence under it; without such a bullet, the
same after a `Command:` that opens a sentence of a paragraph (``… (data.txt). Command: `grep …` ``). Output: the code
span that begins its `Output` bullet or the fence under it, else the span after `→` on the Command bullet (the
judge's form), else the span after an `Output:` that opens a sentence later in the command's bullet or paragraph (an
`Output:` paragraph of its own is not read for a prose command); it matches as a whole word (`0` is not in `10`), and a `…` in it (the
record's cut) matches any text on its line. Fix: `fixed at|in <sha>` or `closed at|in <sha>` in the section, or in
the `##`/`###` heading it stands in when that heading names it, and the build log's `<id>: fixed — <sha>`
(`rebuilt`, a list item too): the fixture is the oldest fix's parent, the fix grader runs at the newest fix. With no
fix that is a commit of the checkout: the commit the defect was seen at (`— <sha>` in the heading, `at <sha>` on the
Command or Output bullet, the last sha of the `Task N: done — …` line of the task section it stands in), and no fix
grader.

Replayed are read-only tools (grep, sed, awk, cat, head, …; `env`, `timeout`, `unshare` and `sh -c` are looked
through) on paths inside the checkout. Every other section is listed with its reasons: no command, no shell command,
cut short, a placeholder in the command, needs a model, needs the network, not a read-only tool, writes a file, reads
outside the checkout, no recorded output, no sha, not a commit of the checkout, not in the checkout at the sha. It
reads git only (`rev-parse`, `rev-list`, `cat-file`) and runs no command of a finding: `--try` runs each grader once
and records the result in index.md; a case replays when every grader passes (a fix grader's pass after a failing
before grader shows nothing). It writes under `<out>` only and refuses a non-empty `<out>` that holds no
index.md of its own; its earlier case folders there are replaced.
"""

import argparse
import json
import os
import pathlib
import posixpath
import re
import shlex
import shutil
import subprocess
import sys
from collections import Counter
from functools import cache

sys.dont_write_bytecode = True  # `python3 -I` ignores PYTHONDONTWRITEBYTECODE; the skill folder stays clean
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check_formats as cf
import findings_report as fr

SOURCES = (("verify.md", "V"), ("judge.md", "J"))
MARK = "# written by replay_cases.py"
INDEX_MARK = "(written by replay_cases.py)"
SHA = r"`?([0-9a-f]{7,40})\b`?"
FIXED = re.compile(r"\b(?:fixed|closed) (?:at|in) (?:plan )?" + SHA)
LOG_FIX = re.compile(r"^(?:- )?([VJ]\d+): (?:fixed|rebuilt)(?: —| in| at) " + SHA, re.MULTILINE)
HEADING_SHA = re.compile(r"— " + SHA)
AT_SHA = re.compile(r"\bat " + SHA)
DONE_LINE = re.compile(r"^(?:- )?Task (\d+): done — (.*)$", re.MULTILINE)
HEX = re.compile(r"\b[0-9a-f]{7,40}\b")
LABEL = re.compile(r"^\s*[-*]\s+\**(Command|Output)s?\b((?:[^:`\n]|`[^`\n]*`)*?)\**:\**[ \t]*(.*)$")
PROSE = re.compile(r"(?:^\s*|(?<=[.!?)\"”'`])\s+)\**(Command|Output)s?\**:\**[ \t]*")
BULLET = re.compile(r"^\s*[-*]\s")
FENCE = re.compile(r"^\s*(```|~~~)")
SPAN = re.compile(r"(`+)(.+?)\1")
ARROW = re.compile(r"[^`→]*→\s*(`+)(.+?)\1")

NO_COMMAND, NO_SHELL, CUT = "no command", "no shell command", "cut short (…)"
PLACEHOLDER, MODEL, NETWORK = "a placeholder in the command", "needs a model", "needs the network"
NOT_READ_ONLY, WRITES, OUTSIDE = "not a read-only tool", "writes a file", "reads outside the checkout"
NO_OUTPUT, NO_SHA, NOT_A_COMMIT = "no recorded output", "no sha", "not a commit of the checkout"
NOT_THERE = "not in the checkout at the sha"

READ_ONLY = frozenset(
    [
        "grep",
        "egrep",
        "fgrep",
        "sed",
        "awk",
        "gawk",
        "mawk",
        "cat",
        "head",
        "tail",
        "wc",
        "sort",
        "uniq",
        "cut",
        "tr",
        "nl",
        "diff",
        "cmp",
        "ls",
        "find",
        "jq",
        "file",
        "stat",
        "od",
        "xxd",
        "sha256sum",
        "md5sum",
        "basename",
        "dirname",
        "echo",
        "printf",
        "test",
        "[",
        "true",
        "false",
        "ulimit",
    ]
)
NO_OPERANDS = frozenset(["echo", "printf", "test", "[", "true", "false", "ulimit", "basename", "dirname"])
PATTERN_FIRST = frozenset(["grep", "egrep", "fgrep", "sed", "awk", "gawk", "mawk", "jq"])
CWD_WITHOUT_OPERANDS = frozenset(["ls", "find"])  # and `grep -r`: they read the folder they run in
WRAPPERS = {
    "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string"},
    "timeout": {"-s", "--signal", "-k", "--kill-after"},
    "nice": {"-n", "--adjustment"},
    "unshare": set(),
}
SHELLS = frozenset(["sh", "bash", "dash"])
NETWORK_TOOLS = frozenset(
    [
        "curl",
        "wget",
        "ssh",
        "scp",
        "sftp",
        "ftp",
        "rsync",
        "nc",
        "ncat",
        "netcat",
        "telnet",
        "ping",
        "dig",
        "nslookup",
        "host",
        "http",
        "https",
        "npm",
        "npx",
        "pnpm",
        "yarn",
    ]
)
NETWORK_SUBCOMMANDS = {
    "git": {"fetch", "pull", "clone", "push", "ls-remote", "submodule"},
    "pip": {"install", "download"},
    "pip3": {"install", "download"},
    "uv": {"sync", "lock", "add", "pip", "tool", "venv"},
    "docker": {"pull", "run", "build"},
}
MODELS = frozenset(["claude", "anthropic", "openai", "ollama", "llm"])
WRITE_FLAG = {
    "sed": re.compile(r"^(-[A-Za-z]*i|--in-place)"),
    "sort": re.compile(r"^(-o|--output)"),
    "find": re.compile(r"^-(exec|execdir|ok|okdir|delete|fprint0?|fprintf|fls)$"),
}
PATTERN_FLAG = re.compile(r"^(-[A-Za-z]*[ef]$|--regexp|--file|--expression)")
OPERATORS = frozenset(["|", "||", "&&", ";", "&", "(", ")", ";;", "|&"])
REDIRECTS = frozenset([">", ">>", "<", ">&", "<&", ">|", "&>", "&>>", "<>", "<<", "<<<"])
ASSIGN = re.compile(r"^[A-Za-z_]\w*=")
PLACEHOLDER_WORD = re.compile(r"<[A-Za-z][\w-]*(?: [\w'-]+)*>")  # `<work>`, `<a copy of the checkout>`
PY_CALL = re.compile(r"^[A-Za-z_][\w.]*\(")
PY_NAME = re.compile(r"^(?![\w.]*\.(?:py|sh|pl|rb|js)$)[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$")
GLOB = re.compile(r"[*?[]")
LOOKS_LIKE_PATH = re.compile(r"/|\.\w{1,8}$")

MATCH = r"""import re, sys
needle = sys.argv[1].strip()
text = open(sys.argv[2], encoding="utf-8", errors="replace").read()
rows = [row.rstrip() for row in needle.split("\n")]
body = r"[ \t]*\n".join(r"[^\n]*?".join(re.escape(p) for p in row.split("…")) for row in rows)
head = r"(?<!\w)" if re.match(r"\w", needle) else ""
tail = r"(?!\w)" if re.search(r"\w$", needle) else ""
sys.exit(0 if re.search(head + body + tail, text) else 1)"""

GRADER = """#!/bin/sh
@MARK@ from @SOURCE@: run it again rather than edit this file.
# @TITLE@
#   sh grader.sh before [<sha>]  passes (exit 0) when the recorded output appears at the sha before the fix
#   sh grader.sh fix [<sha>]     passes when it does not appear at the fix sha (at <sha>: HEAD, still fixed?)
# Exit 1: it fails; exit 2: no fix sha, or the fixture or the command could not be set up.
set -u
REPO=${REPLAY_REPO:-@REPO@}
BEFORE=@BEFORE@
FIX=@FIX@
COMMAND=@COMMAND@
NEEDLE=@NEEDLE@
case "${1:-}" in
  before) SHA=${2:-$BEFORE} WANT=appears ;;
  fix) SHA=${2:-$FIX} WANT=absent ;;
  *) echo "usage: sh grader.sh before|fix [<sha>]" >&2; exit 2 ;;
esac
[ -n "$SHA" ] || { echo "no fix sha: this case has its before grader only" >&2; exit 2; }
WORK=$(mktemp -d) || exit 2
trap 'rm -rf "$WORK"' EXIT
mkdir "$WORK/checkout" "$WORK/home" || exit 2
set -- @PATHS@
if [ "$#" -gt 0 ]; then
  git -C "$REPO" archive -o "$WORK/fixture.tar" "$SHA" -- "$@" && tar -xf "$WORK/fixture.tar" -C "$WORK/checkout" ||
    { echo "cannot take $* at $SHA from $REPO" >&2; exit 2; }
fi
cd "$WORK/checkout" || exit 2
env -i PATH="$PATH" HOME="$WORK/home" LANG=C.UTF-8 LC_ALL=C.UTF-8 TMPDIR="$WORK" \\
  timeout 60 sh -c "$COMMAND" </dev/null >"$WORK/output" 2>&1
[ "$?" -ne 124 ] || { echo "the command ran past 60 s at $SHA" >&2; exit 2; }
python3 -I -c '@MATCH@' "$NEEDLE" "$WORK/output"
case "$WANT $?" in
  "appears 0") echo "pass: the recorded output appears at $SHA"; exit 0 ;;
  "absent 1") echo "pass: the recorded output does not appear at $SHA"; exit 0 ;;
  "appears 1") echo "fail: the recorded output does not appear at $SHA" >&2 ;;
  "absent 0") echo "fail: the recorded output still appears at $SHA" >&2 ;;
  *) echo "the match failed at $SHA" >&2; exit 2 ;;
esac
tail -c 600 "$WORK/output" >&2
exit 1
"""

HOW = (
    "A case is `<id>/task.yaml`, in the fields of the checkout's `evals/` cases, and `<id>/grader.sh`: `sh "
    "<id>/grader.sh before` passes (exit 0) when the finding's recorded output appears in the checkout at the sha "
    "before the fix, `sh <id>/grader.sh fix` when it does not at the fix sha; a second argument names another sha "
    "(`HEAD`: still fixed?). Each grader takes only the paths its command reads (`git archive <sha> -- <paths>`) "
    "and runs the command with an empty HOME, no input and a 60 s limit. The checkout's `evals.py` runs "
    "file_exists, json_schema, regex, python and llm graders: these shell graders run by hand until it has one."
)


def git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=False)


@cache
def commit(repo: str, sha: str) -> str | None:
    """The full sha of a commit of the checkout (`<sha>^` its parent), or None."""
    p = git(repo, "rev-parse", "--verify", "--quiet", sha + "^{commit}")
    return p.stdout.strip() if p.returncode == 0 else None


@cache
def depth(repo: str, sha: str) -> int:
    """The number of commits a commit stands on: an ancestor's is smaller."""
    return int(git(repo, "rev-list", "--count", sha).stdout.strip() or 0)


@cache
def holds(repo: str, sha: str, path: str) -> bool:
    return path == "." or git(repo, "cat-file", "-e", f"{sha}:{path}").returncode == 0


def findings(text: str, kind: str) -> list[dict]:
    """Each `#### <kind><n>` section in reading order: id, line, heading, lines, its task, the headings over it."""
    lines = text.split("\n")
    heads = [i for i, line in enumerate(lines) if fr.HEADING_LINE.match(line)] + [len(lines)]
    out: list[dict] = []
    outer = inner = "none"
    over = ["", ""]
    for k, i in enumerate(heads[:-1]):
        line = lines[i]
        level, task = len(fr.HEADING_LINE.match(line).group(1)), fr.TASK_HEADING.match(line)
        if level == 2:
            outer = inner = task.group(1) if task else "none"
            over = [line, ""]
        elif level == 3:
            inner = task.group(1) if task else outer
            over[1] = line
        elif (h := cf.HEADING.match(line)) and h.group(1) == kind:
            out.append(
                {
                    "id": h.group(1) + h.group(2),
                    "line": i + 1,
                    "heading": line,
                    "lines": lines[i + 1 : heads[k + 1]],
                    "task": inner,
                    "over": list(over),
                }
            )
    return out


def bullet(lines: list[str], i: int) -> tuple[str, list[str]]:
    """The bullet at lines[i]: its text before any fence (lines joined by a space) and the fences under it."""
    indent = len(lines[i]) - len(lines[i].lstrip())
    text, fences, fence = [lines[i].strip()], [], None
    for j in range(i + 1, len(lines)):
        line = lines[j]
        if fence is not None:
            if FENCE.match(line):
                fences.append(dedent(fence))
                fence = None
            else:
                fence.append(line)
        elif FENCE.match(line):
            fence = []
        elif not line.strip():
            if not (j + 1 < len(lines) and FENCE.match(lines[j + 1])):
                break
        elif fr.HEADING_LINE.match(line) or (BULLET.match(line) and len(line) - len(line.lstrip()) <= indent):
            break
        elif not fences:
            text.append(line.strip())
    return " ".join(text), fences


def dedent(lines: list[str]) -> str:
    cut = min((len(line) - len(line.lstrip()) for line in lines if line.strip()), default=0)
    return "\n".join(line[cut:].rstrip() for line in lines).strip("\n")


def field(lines: list[str], label: str) -> tuple[str, str, list[str]] | None:
    """The first `label` bullet of a section: what stands between the label and its colon, the text after, fences."""
    for i, line in enumerate(lines):
        m = LABEL.match(line)
        if m and m.group(1) == label:
            text, fences = bullet(lines, i)
            m = LABEL.match(text)
            return m.group(2), m.group(3), fences
    return None


def prose(lines: list[str]) -> tuple[str, str, list[str]] | None:
    """A `Command:` that opens a sentence of a paragraph: no label, the paragraph's text after it, its fences."""
    fence = False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            fence = not fence
        elif not fence and any(m.group(1) == "Command" for m in PROSE.finditer(line)):
            text, fences = bullet(lines, i)
            m = next(m for m in PROSE.finditer(text) if m.group(1) == "Command")
            return "", text[m.end() :], fences
    return None


def command_of(lines: list[str]) -> tuple[str, str, str] | None:
    """The command ("" when the bullet begins with no code span or fence), the bullet's text after it, its label."""
    f = field(lines, "Command") or prose(lines)
    if f is None:
        return None
    label, rest, fences = f
    if m := SPAN.match(rest):
        return m.group(2).strip(), rest[m.end() :], label
    if fences and (not rest.strip() or rest.rstrip().endswith(":")):
        return fences[0], "", label
    return "", rest, label


def output_of(lines: list[str], after: str) -> tuple[str | None, str]:
    """The recorded output and the Output bullet's label, or (None, "")."""
    f = field(lines, "Output")
    if f:
        label, rest, fences = f
        if (m := SPAN.match(rest)) and m.group(2).strip():
            return m.group(2).strip(), label
        if fences and fences[0].strip() and (not rest.strip() or rest.rstrip().endswith(":")):
            return fences[0], label
    if (m := ARROW.match(after)) and m.group(2).strip():
        return m.group(2).strip(), ""
    m = next((m for m in PROSE.finditer(after) if m.group(1) == "Output"), None)
    if m and (s := SPAN.match(after, m.end())) and s.group(2).strip():
        return s.group(2).strip(), ""
    return None, ""


def simple_commands(command: str) -> list[list[str]]:
    """The command's simple commands, each a list of words (ValueError: shlex cannot split it)."""
    out: list[list[str]] = []
    for line in command.replace("\\\n", " ").split("\n"):
        lex = shlex.shlex(line, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        words: list[str] = []
        for word in lex:
            if word in OPERATORS:
                out += [words] if words else []
                words = []
            else:
                words.append(word)
        out += [words] if words else []
    return out


def redirections(words: list[str]) -> tuple[list[str], list[str], list[str]]:
    """The words without their redirections, the files read (`<`) and written (`>`, `>>`; /dev/null is none)."""
    argv, reads, writes = [], [], []
    i = 0
    while i < len(words):
        word = words[i]
        if word in REDIRECTS:
            target = words[i + 1] if i + 1 < len(words) else ""
            if word in ("<<", "<<<"):
                raise ValueError("a here-document")
            if word in (">&", "<&") and (target.isdigit() or target == "-"):
                pass
            elif word == "<":
                reads.append(target)
            elif target != "/dev/null":
                writes.append(target)
            i += 2
        elif word.isdigit() and i + 1 < len(words) and words[i + 1] in REDIRECTS:
            i += 1
        else:
            argv.append(word)
            i += 1
    return argv, reads, writes


def look_through(argv: list[str]) -> tuple[str | None, list[str]]:
    """The program a simple command runs and its arguments, past `VAR=value`, env, timeout, nice and unshare."""
    i = 0
    while i < len(argv):
        name = argv[i].rsplit("/", 1)[-1]
        if ASSIGN.match(argv[i]):
            i += 1
        elif name in WRAPPERS:
            i += 1
            while i < len(argv) and (argv[i].startswith("-") or (name == "env" and ASSIGN.match(argv[i]))):
                i += 2 if argv[i] in WRAPPERS[name] else 1
            i += 1 if name == "timeout" else 0  # the duration
        else:
            return argv[i], argv[i + 1 :]
    return None, []


def operands(name: str, args: list[str]) -> list[str]:
    """The paths a read-only tool reads: its words that are no option (and no pattern or script)."""
    if name in NO_OPERANDS:
        return []
    if name == "find":
        out = []
        for a in args:
            if a.startswith(("-", "(", "!")):
                break
            out.append(a)
    else:
        out = [a for a in args if not a.startswith("-")]
        if name in PATTERN_FIRST and not any(PATTERN_FLAG.match(a) for a in args):
            out = out[1:]
    recursive = name in ("grep", "egrep", "fgrep") and any(re.match(r"^-[A-Za-z]*[rR]|--recursive", a) for a in args)
    if not out and (name in CWD_WITHOUT_OPERANDS or recursive):
        return ["."]
    return [a for a in out if a != "/dev/null"]


def analyse(command: str) -> tuple[str, list[str]]:
    """Why the command cannot be replayed ("" when it can) and the paths it reads, relative to the checkout."""
    if "…" in command:
        return CUT, []
    if m := PLACEHOLDER_WORD.search(command):
        return f"{PLACEHOLDER}: {m.group(0)}", []
    if PY_CALL.match(command) or PY_NAME.match(command):
        return f"{NO_SHELL}: a Python name", []
    try:
        todo = simple_commands(command)
    except ValueError as exc:
        return f"{NO_SHELL}: {exc}", []
    paths: list[str] = []
    while todo:
        try:
            argv, reads, writes = redirections(todo.pop(0))
        except ValueError as exc:
            return f"{NO_SHELL}: {exc}", []
        if writes:
            return f"{WRITES}: > {writes[0]}", []
        prog, args = look_through(argv)
        if prog is None:
            continue
        name = prog.rsplit("/", 1)[-1]
        if name in MODELS:
            return f"{MODEL}: {prog}", []
        if name in NETWORK_TOOLS or set(args) & NETWORK_SUBCOMMANDS.get(name, set()):
            return f"{NETWORK}: {prog}", []
        if name in SHELLS and "-c" in args[:-1]:
            try:
                todo[:0] = simple_commands(args[args.index("-c") + 1])
            except ValueError as exc:
                return f"{NO_SHELL}: {exc}", []
            continue
        if name not in READ_ONLY:
            return f"{NOT_READ_ONLY}: {prog}", []
        if flag := next((a for a in args if name in WRITE_FLAG and WRITE_FLAG[name].match(a)), None):
            return f"{WRITES}: {name} {flag}", []
        if name in ("awk", "gawk", "mawk") and any("system(" in a for a in args):
            return f"{NOT_READ_ONLY}: {name} system()", []
        paths += operands(name, args) + reads
    for p in paths:
        if p.startswith(("/", "~")) or posixpath.normpath(p).startswith(".."):
            return f"{OUTSIDE}: {p}", []
    out: list[str] = []
    for p in paths:
        if g := GLOB.search(p):
            p = p[: g.start()].rpartition("/")[0] or "."
        p = posixpath.normpath(p)
        out += [] if p in out else [p]
    return "", out


def shas(section: dict, after: str, labels: tuple[str, str], log_fixes: dict, done: dict) -> tuple[list, list]:
    """The fix shas the finding names, and the shas the defect was seen at, in the order they are tried."""
    body = "\n".join(section["lines"])
    named = [m.group(1) for m in FIXED.finditer(section["heading"] + "\n" + body)]
    for head in section["over"]:
        if re.search(rf"\b{section['id']}\b", head):
            named += [m.group(1) for m in FIXED.finditer(head)]
    named += log_fixes.get(section["id"], [])
    seen = [m.group(1) for m in HEADING_SHA.finditer(section["heading"])][:1]
    seen += [
        m.group(1) for m in (AT_SHA.search(labels[0]), re.match(r"\s*at " + SHA, after), AT_SHA.search(labels[1])) if m
    ]
    seen += done.get(section["task"], [])[::-1]
    return named, seen


def replay(section: dict, repo: str, log_fixes: dict, done: dict) -> dict:
    """A case (command, output, before, fix, paths) or the reasons the section has none."""
    found = command_of(section["lines"])
    if found is None:
        return {"reasons": [NO_COMMAND]}
    command, after, command_label = found
    if not command:
        return {"reasons": [f"{NO_SHELL}: the Command line begins with no code span"]}
    reason, paths = analyse(command)
    if reason:
        return {"reasons": [reason], "command": command}
    needle, output_label = output_of(section["lines"], after)
    named, seen = shas(section, after, (command_label, output_label), log_fixes, done)
    reasons = [] if needle else [NO_OUTPUT]
    fixes = sorted({c for s in named if (c := commit(repo, s))}, key=lambda c: (depth(repo, c), c))
    before = commit(repo, fixes[0] + "^") if fixes else None
    origin = f"parent of the fix {fixes[0][:7]}" if before else ""
    if not before:
        before = next((c for s in seen if (c := commit(repo, s))), None)
        origin = "the commit the defect was seen at"
    if not before:
        missing = list(dict.fromkeys(named + seen))
        reasons.append(f"{NOT_A_COMMIT}: {', '.join(missing)}" if missing else NO_SHA)
        return {"reasons": reasons, "command": command}
    for p in paths:
        if not holds(repo, before, p) and LOOKS_LIKE_PATH.search(p):
            reasons.append(f"{NOT_THERE}: {p} ({before[:7]})")
    if reasons:
        return {"reasons": reasons, "command": command}
    paths = ["."] if "." in paths else [p for p in paths if holds(repo, before, p)]
    not_commits = [s for s in dict.fromkeys(named) if not commit(repo, s)]
    return {
        "command": command,
        "needle": needle,
        "before": before,
        "origin": origin,
        "fix": fixes[-1] if fixes else "",
        "paths": paths,
        "not_commits": not_commits,
    }


def task_yaml(case: dict, repo: str) -> str:
    q = lambda v: json.dumps(v, ensure_ascii=False)
    lines = [
        f"{MARK} from {case['source']}: run it again rather than edit this file",
        "schema_version: 1",
        f"name: {q(case['name'])}",
        'suite: "replay"',
        'role_type: "none"  # no session: the graders replay a finding\'s command on the checkout',
        "trials: 1",
        "timeout_minutes: 5",
        "max_budget_usd: 0",
        f"finding: {q(case['id'])}",
        f"source: {q(case['source'])}",
        f"title: {q(case['title'])}",
        "fixture:",
        f"  repo: {q(repo)}",
        f"  sha: {q(case['before'])}  # {case['origin']}",
        f"  paths: {q(case['paths'])}  # what the command reads: git archive <sha> -- <paths>",
        f"command: {q(case['command'])}",
        f"recorded_output: {q(case['needle'])}",
        "graders:",
    ]
    graders = [("before", case["before"], "the recorded output appears")]
    graders += [("fix", case["fix"], "the recorded output does not appear")] if case["fix"] else []
    for mode, sha, when in graders:
        lines += [
            '  - type: "shell"  # evals.py runs file_exists, json_schema, regex, python and llm graders',
            '    script: "grader.sh"',
            f"    args: [{q(mode)}]",
            f"    sha: {q(sha)}",
            f"    passes_when: {q(when)}",
        ]
    return "\n".join(lines + ['pass_rule: "deterministic_all"', ""])


def grader(case: dict, repo: str) -> str:
    values = {
        "@MARK@": MARK,
        "@SOURCE@": case["source"],
        "@TITLE@": case["title"],
        "@REPO@": shlex.quote(repo),
        "@BEFORE@": shlex.quote(case["before"]),
        "@FIX@": shlex.quote(case["fix"]),
        "@COMMAND@": shlex.quote(case["command"]),
        "@NEEDLE@": shlex.quote(case["needle"]),
        "@PATHS@": " ".join(shlex.quote(p) for p in case["paths"]),
        "@MATCH@": MATCH,
    }
    return re.sub("|".join(values), lambda m: values[m.group(0)], GRADER)


def prepare(out: pathlib.Path) -> str:
    """Make `out` ready for writing, its earlier case folders removed; why it is refused, or ""."""
    if out.exists() and not out.is_dir():
        return f"not a folder: {out}"
    if out.is_dir() and any(out.iterdir()):
        index = out / "index.md"
        if not (index.is_file() and INDEX_MARK in cf.read(index).split("\n", 1)[0]):
            return f"{out} is not empty and holds no index.md written by replay_cases.py: nothing written"
        for d in out.iterdir():
            if d.is_dir() and (d / "task.yaml").is_file() and cf.read(d / "task.yaml").startswith(MARK):
                shutil.rmtree(d)
    out.mkdir(parents=True, exist_ok=True)
    return ""


def try_case(case_dir: pathlib.Path, modes: list[str], tmp: pathlib.Path) -> dict:
    """Run each grader of a case once: passes, fails or error."""
    out = {}
    for mode in modes:
        try:
            rc = subprocess.run(
                ["sh", str(case_dir / "grader.sh"), mode],
                capture_output=True,
                text=True,
                timeout=180,
                env={**os.environ, "TMPDIR": str(tmp)},
                check=False,
            ).returncode
        except subprocess.TimeoutExpired:
            rc = -1
        out[mode] = {0: "passes", 1: "fails"}.get(rc, "error")
    return out


def replays(case: dict) -> bool:
    return all(r == "passes" for r in case["tried"].values())


def cell(text: str, limit: int = 0) -> str:
    text = " ".join(text.split())
    text = text[: limit - 1] + "…" if limit and len(text) > limit else text
    return text.replace("|", "\\|")


def index(head: str, cases: list[dict], skipped: list[dict], tried: bool) -> str:
    lines = [head, "", HOW, "", "## Replayable", ""]
    lines += [
        "| id | source | before | fix | command |" + (" tried |" if tried else ""),
        "|---|---|---|---|---|" + ("---|" if tried else ""),
    ]
    for c in cases:
        fix = f"`{c['fix'][:7]}`" if c["fix"] else "no fix sha"
        fix += f" ({', '.join(c['not_commits'])}: {NOT_A_COMMIT})" if c["not_commits"] else ""
        result = ", ".join(f"{mode} {r}" for mode, r in c.get("tried", {}).items())
        result += (": replays" if replays(c) else ": does not replay") if tried else ""
        lines.append(
            f"| {c['dir']} | {c['where']} | `{c['before'][:7]}` ({c['origin']}) | {fix} | "
            f"`` {cell(c['command'], 100)} `` |" + (f" {result} |" if tried else "")
        )
    lines += ["", "## Not replayable", "", "| id | source | reasons |", "|---|---|---|"]
    lines += [f"| {s['dir']} | {s['where']} | {cell('; '.join(s['reasons']))} |" for s in skipped]
    counts = Counter(k for s in skipped for k in dict.fromkeys(r.split(": ", 1)[0] for r in s["reasons"]))
    lines += ["", "## Reasons", "", "| reason | sections |", "|---|---:|"]
    lines += [f"| {r} | {n} |" for r, n in counts.most_common()]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay cases from a run folder's V and J findings.")
    ap.add_argument("run_dir")
    ap.add_argument("--repo", required=True, help="the checkout the findings' commits belong to")
    ap.add_argument("--out", required=True, help="the folder the cases and index.md are written to")
    ap.add_argument("--try", dest="try_", action="store_true", help="run each grader once, record the results")
    a = ap.parse_args()
    run, out, repo = (
        pathlib.Path(a.run_dir).resolve(),
        pathlib.Path(a.out).resolve(),
        str(pathlib.Path(a.repo).resolve()),
    )
    if not run.is_dir():
        print(f"replay_cases.py: not a folder: {run}", file=sys.stderr)
        return 2
    if git(repo, "rev-parse", "--git-dir").returncode != 0:
        print(f"replay_cases.py: not a git checkout: {repo}", file=sys.stderr)
        return 2
    if refused := prepare(out):
        print(f"replay_cases.py: {refused}", file=sys.stderr)
        return 2
    log = cf.read(run / "build-log.md")
    log_fixes: dict[str, list[str]] = {}
    for m in LOG_FIX.finditer(log):
        log_fixes.setdefault(m.group(1), []).append(m.group(2))
    done = {m.group(1): HEX.findall(m.group(2).split(" — ")[0]) for m in DONE_LINE.finditer(log)}
    cases, skipped, sections, dirs = [], [], {}, Counter()
    for name, kind in SOURCES:
        found = findings(cf.read(run / name), kind)
        sections[name] = len(found)
        for s in found:
            dirs[s["id"]] += 1
            r = replay(s, repo, log_fixes, done)
            r.update(
                id=s["id"],
                dir=s["id"] + (f"-{dirs[s['id']]}" if dirs[s["id"]] > 1 else ""),
                where=f"{name}:{s['line']}",
                source=f"{run / name}:{s['line']}",
                title=s["heading"][5:].strip(),
            )
            r["name"] = f"replay-{run.name}-{r['dir']}"
            (skipped if r.get("reasons") else cases).append(r)
    for c in cases:
        (out / c["dir"]).mkdir()
        (out / c["dir"] / "task.yaml").write_text(task_yaml(c, repo), encoding="utf-8")
        (out / c["dir"] / "grader.sh").write_text(grader(c, repo), encoding="utf-8")
        (out / c["dir"] / "grader.sh").chmod(0o755)
    if a.try_:
        tmp = out / ".tmp"
        tmp.mkdir(exist_ok=True)
        for c in cases:
            c["tried"] = try_case(out / c["dir"], ["before", "fix"] if c["fix"] else ["before"], tmp)
        shutil.rmtree(tmp, ignore_errors=True)
    with_fix = sum(1 for c in cases if c["fix"])
    summary = (
        f"{sum(sections.values())} sections ({', '.join(f'{n} {k}' for n, k in sections.items())}): "
        f"{len(cases)} cases ({with_fix} with a fix grader), {len(skipped)} not replayable"
    )
    head = (
        f"# Replay cases of {run.name} {INDEX_MARK}\n\n`python3 replay_cases.py {run} --repo {repo} --out {out}"
        f"{' --try' if a.try_ else ''}`: {summary}. "
        + ("Each grader ran once (`--try`)." if a.try_ else "No command of a finding ran.")
    )
    (out / "index.md").write_text(index(head, cases, skipped, a.try_), encoding="utf-8")
    print(f"replay cases: {summary}\nindex: {out / 'index.md'}")
    if a.try_:
        before = sum(1 for c in cases if c["tried"]["before"] == "passes")
        fix = sum(1 for c in cases if c["tried"].get("fix") == "passes")
        print(
            f"tried: before passes {before} of {len(cases)}, fix passes {fix} of {with_fix}; "
            f"{sum(map(replays, cases))} of {len(cases)} cases replay (every grader passes)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
