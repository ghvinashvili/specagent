"""The commands a Bash call runs, as the guard hooks read them (guard-bash.py, guard-checkout.py).

A command is split into simple commands at the shell's separators (`;`, `&&`, `||`, `|`, `&`, a newline, a
parenthesis, so the inside of `$( )` is a command of its own), quotes are taken off as the shell takes them off, and a
line continuation joins its lines. The wrappers that run their arguments as a command are taken off: a leading
assignment, `env`, `sudo`, `doas`, `exec`, `command` (not `command -v`, a lookup), `builtin`, `nice`, `nohup`,
`timeout`, `stdbuf`, `time`, `noglob`, `xargs` and `eval`, and the script of `bash -c` and its kin is read as commands
of its own. Claude Code takes off only some of them before it matches a permission rule (permissions.md:237-245 in
context/fix-20261004/claude-code-facts.md), so the guards do it themselves. A command the shell could not read either
(an open quote) gives None.

`#` is part of a word here: bash starts a comment only at the start of a word, and a reader that took the rest of the
line after a `#` inside a word for a comment would not see the commands after it (`echo a#b; git add -A`). The words of
a real comment are read as words, which can only make a guard refuse more
(packages/harness/tests/test_plain_spellings.py). This reader gives the guards the plain spellings of a command; what
the shell builds at run time (a variable the command sets, a brace, a function, a pipe into `sh`) it does not see, and
the sandbox and the write gate hold those (docs/decisions/0025; test_boundary_settings.py, test_closed_paths.py).
"""

from __future__ import annotations

import re
import shlex

ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SEPARATOR = set("();|&\n")
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "mksh", "ash"}
# The options of a wrapper that take a value in the next word (a value given with `=` or attached needs none).
VALUED = {
    "env": {"-u", "--unset", "-C", "--chdir"},
    "sudo": {"-u", "--user", "-g", "--group", "-C", "--close-from", "-D", "--chdir", "-h", "--host", "-p", "--prompt",
             "-r", "--role", "-t", "--type", "-T", "--command-timeout", "-U", "--other-user"},
    "doas": {"-u", "-C"},
    "exec": {"-a"},
    "nice": {"-n", "--adjustment"},
    "timeout": {"-k", "--kill-after", "-s", "--signal"},
    "stdbuf": {"-i", "--input", "-o", "--output", "-e", "--error"},
    "time": {"-f", "--format", "-o", "--output"},
    "xargs": {"-a", "--arg-file", "-d", "--delimiter", "-E", "-e", "--eof", "-I", "-i", "--replace", "-L", "-l",
              "--max-lines", "-n", "--max-args", "-P", "--max-procs", "-s", "--max-chars", "--process-slot-var"},
    "command": set(),
    "builtin": set(),
    "noglob": set(),
    "nohup": set(),
}  # fmt: skip
DEPTH = 8  # nested `bash -c` and `eval` read before the command counts as one nobody can read


def tokens(command: str) -> list[str] | None:
    """The words and operators of a command, quotes taken off; None for a command the shell cannot read."""
    lex = shlex.shlex(command.replace("\\\n", ""), posix=True, punctuation_chars="();<>|&\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""  # `#` is a word character: bash comments only at the start of a word
    try:
        return list(lex)
    except ValueError:
        return None


def simple_commands(command: str, depth: int = 0) -> list[list[str]] | None:
    """Every simple command the text runs, its wrappers taken off, in order; None when it cannot be read."""
    found = tokens(command)
    if found is None or depth > DEPTH:
        return None
    parts: list[list[str]] = [[]]
    for tok in found:
        if tok and set(tok) <= SEPARATOR:
            parts.append([])
        else:
            parts[-1].append(tok)
    out: list[list[str]] = []
    for argv in parts:
        inner = unwrap(argv, depth)
        if inner is None:
            return None
        out += inner
    return out


def _script(words: list[str]) -> str | None:
    """The script of `bash -c <script>` and its kin, or None when the shell runs a file or its input."""
    i, wants = 1, False
    while i < len(words):
        w = words[i]
        if w in ("-o", "+o", "-O", "+O") and i + 1 < len(words):
            i += 2
            continue
        if w.startswith("-") and not w.startswith("--") and len(w) > 1:
            wants = wants or "c" in w[1:]
            i += 1
            continue
        if w.startswith("--"):
            i += 1
            continue
        return w if wants else None
    return None


def unwrap(argv: list[str], depth: int = 0) -> list[list[str]] | None:
    """The command a wrapper runs, as one or more simple commands; [] for a lookup that runs nothing."""
    words = list(argv)
    while words:
        name = words[0].rsplit("/", 1)[-1]
        if ASSIGNMENT.match(words[0]):
            words.pop(0)
        elif name == "eval":
            return simple_commands(" ".join(words[1:]), depth + 1)
        elif name in SHELLS and _script(words) is not None:
            return simple_commands(_script(words) or "", depth + 1)
        elif name == "command" and len(words) > 1 and words[1] in ("-v", "-V"):
            return []
        elif name in VALUED:
            words = _options(name, words[1:])
        else:
            break
    return [words] if words else []


def _options(name: str, words: list[str]) -> list[str]:
    """The words after a wrapper's options (and after env's assignments, timeout's duration)."""
    while words and (words[0].startswith("-") or (name == "env" and ASSIGNMENT.match(words[0]))):
        opt = words.pop(0)
        if opt == "--":
            break
        if name == "env" and opt in ("-S", "--split-string") and words:
            words = (shlex.split(words.pop(0)) if tokens(words[0]) is not None else []) + words
        elif name == "env" and opt.startswith("--split-string="):
            words = shlex.split(opt.split("=", 1)[1]) + words
        elif opt in VALUED[name] and words:
            words.pop(0)
    if name == "timeout" and words:
        words.pop(0)  # the duration
    return words
