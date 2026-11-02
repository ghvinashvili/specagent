#!/usr/bin/env python3
"""A plan's task files checked before they are handed on (lessons of a project's run of 2026-11-02: C34, C39, C43, C49, C53,
C58, C60, C63; quoted tests that failed ruff).

  python3 -I task_lint.py <task-NN.md | plan-dir>... [--repo DIR]

Per task file (`task-NN.md`; a plan folder gives every one of them):
- a `Step 0` whose `Expected:` line holds a number: the tests collected at the task's base;
- every command (a fenced shell block, or a `Run:` line) has an `Expected:` line before the next command or step;
- every fenced `python` block of the task and of its `task-NN.code.md` passes `ruff check` and `ruff format --check`
  when the repository (`--repo`, else the plan's git checkout) has a ruff configuration, run from that repository so its
  rules apply. A block is checked as a fragment, since it is often the lines to add to a file: dedented, without the
  rules that need the whole file (F401, F811, F821, E402, I001); a block that does not parse alone, or holds only
  expressions that are no calls (one entry of a set), is counted as `unchecked fragment`. A block of another language
  is counted as unchecked, never passed.

Prints `<file>:<line>: <problem>` per problem, then `task_lint: <n> files, <m> problems[, unchecked <lang> <k>]`.
Exit 0 with no problem, 1 with one, 2 when a path is not there or ruff does not run (its error on stderr, nothing on
stdout: no edit of a task fixes a tool that cannot start). Read-only.
"""

import argparse
import ast
import pathlib
import re
import shutil
import subprocess
import sys
import textwrap

STEP = re.compile(r"^\s*-\s*\[[ xX]\]\s*\*\*Step (\d+)\b")
FENCE = re.compile(r"^\s*(```+|~~~+)\s*([\w+-]*)")
EXPECTED = re.compile(r"^\s*(?:[-*]\s*)?Expected:\s*(.*)")
RUN_LINE = re.compile(r"^\s*(?:[-*]\s*)?Run:\s*`")
SHELLS = {"bash", "sh", "shell", "console", "zsh"}
RUFF_CONFIGS = ("ruff.toml", ".ruff.toml")
# the rules that need the whole file: a task's block is often the lines to add to one
FRAGMENT_IGNORES = "F401,F811,F821,E402,I001"


def blocks(lines: list[str]) -> list[tuple[int, str, list[str]]]:
    """Each fenced block's first line number, language (lower case) and body lines. A fence closes on a line of the same
    character, at least as long as the opening, with nothing else on it (CommonMark), so a longer fence quotes a
    shorter one (V9 of the verifier)."""
    out, open_at, lang, mark, body = [], 0, "", "", []
    for n, line in enumerate(lines, 1):
        fence = FENCE.match(line)
        if not open_at and fence:
            open_at, mark, lang, body = n, fence.group(1), fence.group(2).lower(), []
        elif open_at and re.fullmatch(rf"\s*{re.escape(mark[0])}{{{len(mark)},}}\s*", line):
            out.append((open_at, lang, body))
            open_at = 0
        elif open_at:
            body.append(line)
    return out


def inside_any(n: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= n <= b for a, b in spans)


def command_problems(lines: list[str]) -> list[tuple[int, str]]:
    """Step 0 and its count; a command without its `Expected:` line before the next command or step."""
    fenced = blocks(lines)
    spans = [(start, start + len(body) + 1) for start, _, body in fenced]
    events: list[tuple[int, str]] = []  # (line, kind): step, command, expected
    for n, line in enumerate(lines, 1):
        if inside_any(n, spans):
            continue
        if STEP.match(line):
            events.append((n, "step"))
        elif RUN_LINE.match(line):
            events.append((n, "command"))
        elif EXPECTED.match(line):
            events.append((n, "expected"))
    events += [(start, "command") for start, lang, _ in fenced if lang in SHELLS]
    events.sort()
    problems, pending = [], None
    for n, kind in events:
        if kind == "expected":
            pending = None
        else:
            if pending:
                problems.append((pending, "a command without an `Expected:` line"))
            pending = n if kind == "command" else None
    if pending:
        problems.append((pending, "a command without an `Expected:` line"))
    return problems + step_zero(lines)


def step_zero(lines: list[str]) -> list[tuple[int, str]]:
    """The task's `Step 0` and the count its `Expected:` line names."""
    start = next((n for n, line in enumerate(lines, 1) if (m := STEP.match(line)) and m.group(1) == "0"), None)
    if start is None:
        return [(1, "no `Step 0` (the tests collected at the task's base, with an `Expected:` count)")]
    for line in lines[start:]:
        if STEP.match(line):
            break
        expected = EXPECTED.match(line)
        if expected and re.search(r"\d", expected.group(1)):
            return []
    return [(start, "`Step 0` has no `Expected:` line with a count")]


def ruff_config(repo: pathlib.Path | None) -> bool:
    if repo is None:
        return False
    if any((repo / name).is_file() for name in RUFF_CONFIGS):
        return True
    pyproject = repo / "pyproject.toml"
    return pyproject.is_file() and "[tool.ruff" in pyproject.read_text(encoding="utf-8", errors="replace")


def lines_of_a_larger_statement(source: str) -> bool:
    """The block does not parse alone, or holds no statement but expressions that are not calls: one entry of a set or a
    dict, which ruff would read as a useless expression and ask to wrap in parentheses."""
    try:
        body = ast.parse(source).body
    except SyntaxError:
        return True
    return bool(body) and all(isinstance(n, ast.Expr) and not isinstance(n.value, ast.Call) for n in body)


class RuffCannotRun(Exception):
    """ruff, or the `uv run` that starts it, did not run: no edit of a task's block would fix that (V11 of the verifier)."""


def ruff_command() -> list[str]:
    found = shutil.which("ruff")
    return [found] if found else ["uv", "run", "--quiet", "ruff"]


def ruff_problems(path: pathlib.Path, lines: list[str], repo: pathlib.Path) -> tuple[list[tuple[int, str]], int]:
    """Each python block that `ruff check` or `ruff format --check` refuses, run from the repository, and the number
    of blocks left unchecked. A block is checked as a fragment, since a task's block is often the lines to add to a file
    and uses that file's names and imports (V10 of the verifier): dedented, without the rules that need the whole file,
    and a block that is no statement of its own (it does not parse alone, or is an entry of a literal) is counted, never
    refused. Only exit 1 of ruff is the block's problem; a tool that cannot start, or ends otherwise, raises
    RuffCannotRun with its error."""
    ruff = ruff_command()
    problems, fragments = [], 0
    for start, lang, body in blocks(lines):
        if lang not in ("python", "py"):
            continue
        source, name = textwrap.dedent("\n".join(body)) + "\n", f"{path.stem}_block_{start}.py"
        if lines_of_a_larger_statement(source):
            fragments += 1
            continue
        for args, what in (
            (["check", "--quiet", "--ignore", FRAGMENT_IGNORES], "ruff check"),
            (["format", "--check", "--quiet"], "ruff format"),
        ):
            try:
                done = subprocess.run(
                    [*ruff, *args, "--stdin-filename", name, "-"],
                    input=source,
                    capture_output=True,
                    text=True,
                    cwd=repo,
                    check=False,
                )
            except OSError as error:
                raise RuffCannotRun(f"{what} could not start on {path}:{start}: {error}") from error
            if done.returncode not in (0, 1):  # 1 is a violation or "would reformat"; any other exit is the tool's own
                detail = " ".join((done.stderr or done.stdout).split())[:300] or "no output"
                raise RuffCannotRun(f"{what} exited {done.returncode} on {path}:{start}: {detail}")
            if done.returncode:
                first = (done.stdout or done.stderr).strip().splitlines()[:1]
                why = first[0] if first and what == "ruff check" else "it would reformat it"
                problems.append((start, f"{what} refuses the python block: {why}"))
    return problems, fragments


def checkout_of(path: pathlib.Path) -> pathlib.Path | None:
    done = subprocess.run(
        ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False
    )
    return pathlib.Path(done.stdout.strip()) if done.returncode == 0 and done.stdout.strip() else None


def task_files(paths: list[pathlib.Path]) -> list[pathlib.Path]:
    out = []
    for p in paths:
        out += sorted(p.glob("task-*.md")) if p.is_dir() else [p]
    return [p for p in out if not p.name.endswith(".code.md")]


def main() -> int:
    ap = argparse.ArgumentParser(prog="task_lint.py", description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", type=pathlib.Path, metavar="PATH")
    ap.add_argument("--repo", type=pathlib.Path, help="the repository whose ruff configuration applies")
    a = ap.parse_args()
    missing = [p for p in a.paths if not p.exists()]
    if missing:
        print(f"task_lint: {missing[0]}: no such file", file=sys.stderr)
        return 2
    files, problems, unchecked = task_files(a.paths), [], {}
    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        problems += [(path, n, why) for n, why in command_problems(lines)]
        repo = a.repo or checkout_of(path)
        for each in (path, path.with_name(path.name.replace(".md", ".code.md"))):
            if not each.is_file():
                continue
            text = each.read_text(encoding="utf-8").splitlines()
            for _, lang, _ in blocks(text):
                if lang and lang not in SHELLS | {"python", "py", "text", "md", "markdown", "json", "yaml", "toml"}:
                    unchecked[lang] = unchecked.get(lang, 0) + 1
            if ruff_config(repo):
                try:
                    found, fragments = ruff_problems(each, text, repo)
                except RuffCannotRun as error:
                    print(f"task_lint: {error}", file=sys.stderr)
                    return 2
                problems += [(each, n, why) for n, why in found]
                if fragments:
                    unchecked["fragment"] = unchecked.get("fragment", 0) + fragments
    for path, n, why in problems:
        print(f"{path}:{n}: {why}")
    extra = "".join(f", unchecked {lang} {k}" for lang, k in sorted(unchecked.items()))
    print(f"task_lint: {len(files)} files, {len(problems)} problems{extra}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
