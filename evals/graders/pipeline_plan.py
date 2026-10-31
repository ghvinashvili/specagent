#!/usr/bin/env python3
"""Deterministic grader of the pipeline evals: thirteen checks, one per known error class of a plan, a run or a commit.

Case mode, `pipeline_plan.py <workspace>`: reads `<workspace>/expect.json` (`check`, `inputs`, `found`, and `base` or
`max_bytes` where the check takes one), runs the check on the inputs, which resolve against the workspace and are
named as written (a folder's files as `<input>/<path below it>`), and prints its findings sorted, one per line. It
exits 0 when they equal the sorted `found`, else 1, with the `missing:` lines (expected, not found) and then the
`unexpected:` lines on stderr. Measure mode, `pipeline_plan.py --check <name> --root <dir> <input>...`, prints one
check's findings on any files, inputs named as given, and exits 1 when there is one. Standard library only, but the
pages rule and the job timeouts, which ask the write gate (`harness.gates.write`) and `harness.evals.suite_minutes`
under the harness's own Python. See evals/README.md.
"""

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from collections.abc import Callable
from fnmatch import fnmatchcase
from pathlib import Path

OPEN = re.compile(r"(`{3,})([^`]*)")  # CommonMark: three or more backticks open a fence; its info string has none
SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)  # a code span: backticks, the text, the same run
CITATION = re.compile(r"([^\s:`]*[/.][^\s:`]*):(\d+)(?:-(\d+))?")  # <path>:<n> or <path>:<n>-<m>, no space
COMMANDS = {"bash", "sh", "shell", "console"}
STOP = re.compile(r"- \[[ xX]\]|#{1,6}(\s|$)")  # a checkbox line or a heading ends the search for an Expected: line
DEPENDENCY = re.compile(r'^\+\s*"[A-Za-z0-9][A-Za-z0-9._-]*(\[[^\]]*\])?\s*([<>=!~;].*)?",?\s*$')
PYPROJECT = re.compile(r"diff --git a/(\S+/)?pyproject\.toml ")  # any pyproject.toml; the one uv.lock is at the root
MANIFEST_LINE = re.compile(r"([0-9a-f]{64}) [ *](.+)")  # as sha256sum writes it
TIMEOUT = re.compile(  # GNU timeout, its options, a duration (no unit is seconds), and `harness eval` later on the line
    r"\btimeout(?:\s+(?:(?:-k|--kill-after|-s|--signal)(?:=|\s+)\S+|--preserve-status|--foreground|-v|--verbose))*"
    r"\s+((\d+(?:\.\d+)?)([smhd]?))\s.*?\bharness\s+eval\b(.*)"
)
SECONDS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}
SUITE_FLAG = re.compile(r"--suite(?:=|\s+)(\S+)")
CASE_FLAG = re.compile(r"--case(?:=|\s+)(\S+)")
NO_SESSIONS = re.compile(r"--(?:baseline|no-sessions)(?!\S)")  # a run that starts no session needs no time
DENY = re.compile(r"(?:Edit|Write)\((.*)\)")
WAITER = re.compile(r"[\w./-]*wait[\w-]*\.(py|sh)")  # a script whose file name holds `wait`
PLACEHOLDER = re.compile(r"<[^<>]*>")  # a brief's <run-dir>, <log> or <lines>, for the agent to fill
SLEEP = re.compile(r"(?:^|[;&|(]|\bdo\b|\bthen\b|\belse\b)\s*sleep\s+\d", re.MULTILINE)  # at a command position
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
Function = ast.FunctionDef | ast.AsyncFunctionDef
# pytest 9.1.1's builtin fixtures (`pytest --fixtures -v`), and `request`, which that listing leaves out
BUILTIN_FIXTURES = frozenset(
    {
        "cache",
        "capfd",
        "capfdbinary",
        "caplog",
        "capsys",
        "capsysbinary",
        "capteesys",
        "doctest_namespace",
        "monkeypatch",
        "pytestconfig",
        "record_property",
        "record_testsuite_property",
        "record_xml_attribute",
        "recwarn",
        "request",
        "subtests",
        "tmp_path",
        "tmp_path_factory",
        "tmpdir",
        "tmpdir_factory",
    }
)
INDEXES = {"index.md", "log.md", "README.md", "llms.txt"}
GENERATED = ("graphify-out/", "wiki/graph/", ".venv/", "evals/results/")
OBSIDIAN_KEPT = {  # a vault's settings; the rest of .obsidian/ is the app's
    "wiki/.obsidian/": {"app.json", "core-plugins.json", "graph.json"},  # the vault at wiki/, before the adoption
    ".obsidian/": {"app.json", "appearance.json", "core-plugins.json", "graph.json", "snippets/vault-colors.css"},
}  # the checkout root as the claude-obsidian vault: the plugin's files and core-plugins.json


def name(path: Path) -> str:
    return path.as_posix()


def lines_of(path: Path) -> list[str]:
    """The file's lines as `sed -n` numbers them: split at newlines only (str.splitlines also splits at U+2028)."""
    text = path.read_text(encoding="utf-8")
    return text.removesuffix("\n").split("\n") if text else []


def fences(lines: list[str]) -> list[tuple[int, int, str]]:
    """The fenced blocks as (opening index, closing index or len(lines), first word of the info string)."""
    out, i = [], 0
    while i < len(lines):
        opening = OPEN.fullmatch(lines[i].strip())
        if not opening:
            i += 1
            continue
        closing = re.compile(f"`{{{len(opening.group(1))},}}")  # only backticks, at least as many
        end = next((j for j in range(i + 1, len(lines)) if closing.fullmatch(lines[j].strip())), len(lines))
        out.append((i, end, (opening.group(2).split() or [""])[0]))
        i = end + 1
    return out


def outside_fences(lines: list[str]) -> list[tuple[int, str]]:
    """(line number, text) of the lines that are neither in a fenced block nor one of its fences."""
    inside = {j for start, end, _ in fences(lines) for j in range(start, end + 1)}
    return [(i + 1, line) for i, line in enumerate(lines) if i not in inside]


def paragraphs(lines: list[str]) -> list[str]:
    """Each paragraph (a run of non-blank lines outside the fences), joined by newlines: a code span may cross them."""
    runs, last = [], -1
    for n, line in outside_fences(lines):
        if not line.strip():
            continue
        if n != last + 1:
            runs.append([])
        runs[-1].append(line)
        last = n
    return ["\n".join(run) for run in runs]


def cited_lines(inputs: list[Path], opts: dict) -> list[str]:
    """Error class 1: a `<path>:<n>` code span outside fences that names a missing file or a line past its end."""
    base, out = Path(opts.get("base", ".")), []
    for path in inputs:
        for n, line in outside_fences(lines_of(path)):
            for span in (m.group(2) for m in SPAN.finditer(line)):
                cited = CITATION.fullmatch(span)
                if not cited:
                    continue
                target = base / cited.group(1)
                if not target.is_file():
                    out.append(f"{name(path)}:{n}: cites {span} which does not exist at the base")
                    continue
                count = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
                if int(cited.group(3) or cited.group(2)) > count:  # a range by its end
                    out.append(f"{name(path)}:{n}: cites {span} past the file's {count} lines")
    return out


def expected_lines(inputs: list[Path], opts: dict) -> list[str]:
    """Error class 2: a command block with no `Expected:` line before the next fence, checkbox line or heading."""
    out = []
    for path in inputs:
        lines = lines_of(path)
        for start, end, info in fences(lines):
            if info in COMMANDS and not has_expected(lines[end + 1 :]):
                out.append(f"{name(path)}:{start + 1}: a command block without an Expected: line")
    return out


def has_expected(after: list[str]) -> bool:
    for line in after:
        text = line.strip()
        if OPEN.fullmatch(text) or STOP.match(text):
            return False
        if text.removeprefix("- ").startswith("Expected:"):
            return True
    return False


def tests_can_fail(inputs: list[Path], opts: dict) -> list[str]:
    """Error class 3: a test that asserts nothing, asserts a constant or takes a fixture that nothing defines."""
    trees = [(path, offset, tree) for path in inputs for offset, tree in python_trees(path)]
    known = BUILTIN_FIXTURES | {f for _, _, tree in trees for f in fixture_names(tree)}
    out = []
    for path, offset, tree in trees:
        for fn, method in collected_tests(tree):
            out += [f"{name(path)}:{offset + n}: {fn.name} {what}" for n, what in weak_points(fn, method, known)]
    return out


def python_trees(path: Path) -> list[tuple[int, ast.Module]]:
    """A `.py` input whole (offset 0), or a document's ```python blocks offset by their fence line; code that does
    not parse is left out."""
    lines = lines_of(path)
    if path.suffix == ".py":
        parts = [(0, lines)]
    else:
        parts = [(start + 1, lines[start + 1 : end]) for start, end, info in fences(lines) if info == "python"]
    out = []
    for offset, body in parts:
        try:
            out.append((offset, ast.parse("\n".join(body))))
        except (SyntaxError, ValueError):
            continue
    return out


def dotted(node: ast.AST) -> str:
    """`a.b.c` for a name or a chain of attributes, else ""."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = dotted(node.value)
        return f"{head}.{node.attr}" if head else ""
    return ""


def fixture_names(tree: ast.AST) -> set[str]:
    """The names the `@pytest.fixture` (or `@fixture`) functions give, a decorator's `name=` first."""
    out = set()
    for fn in (n for n in ast.walk(tree) if isinstance(n, FUNCTIONS)):
        for deco in fn.decorator_list:
            call = deco if isinstance(deco, ast.Call) else None
            if dotted(call.func if call else deco) not in ("pytest.fixture", "fixture"):
                continue
            given = next((k.value for k in (call.keywords if call else []) if k.arg == "name"), None)
            if isinstance(given, ast.Constant) and isinstance(given.value, str):
                out.add(given.value)
            else:
                out.add(fn.name)
    return out


def collected_tests(tree: ast.Module) -> list[tuple[Function, bool]]:
    """Each `def test_*` of the module and of its classes, with whether it is a method (its first parameter is self)."""
    out = []
    for node in tree.body:
        if isinstance(node, FUNCTIONS) and node.name.startswith("test_"):
            out.append((node, False))
        elif isinstance(node, ast.ClassDef):
            out += [(f, True) for f in node.body if isinstance(f, FUNCTIONS) and f.name.startswith("test_")]
    return out


def weak_points(fn: Function, method: bool, known: frozenset[str]) -> list[tuple[int, str]]:
    """(AST line, problem) for one test: it asserts nothing, an assert of a constant, a parameter no fixture fills."""
    nodes = [n for stmt in fn.body for n in ast.walk(stmt)]
    out = []
    if not any(isinstance(n, (ast.Assert, ast.Raise)) or dotted(n) in ("pytest.raises", "pytest.fail") for n in nodes):
        out.append((fn.lineno, "asserts nothing"))
    constant = [n for n in nodes if isinstance(n, ast.Assert) and isinstance(n.test, ast.Constant)]
    out += [(n.lineno, "asserts a constant") for n in constant]
    given = known | parametrized(fn)
    out += [(fn.lineno, f"uses the missing fixture {p}") for p in fixture_params(fn, method) if p not in given]
    return out


def parametrized(fn: Function) -> set[str]:
    """The argument names of the function's `@pytest.mark.parametrize` decorators."""
    out = set()
    for deco in fn.decorator_list:
        if not (isinstance(deco, ast.Call) and dotted(deco.func).endswith("mark.parametrize")):
            continue
        names = deco.args[0] if deco.args else next((k.value for k in deco.keywords if k.arg == "argnames"), None)
        if isinstance(names, ast.Constant) and isinstance(names.value, str):
            out |= {n.strip() for n in names.value.split(",") if n.strip()}
        elif isinstance(names, (ast.Tuple, ast.List)):
            out |= {e.value for e in names.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    return out


def fixture_params(fn: Function, method: bool) -> list[str]:
    """The parameters pytest fills with fixtures: those without a default, a method's self left out."""
    positional = [*fn.args.posonlyargs, *fn.args.args]
    required = positional[: len(positional) - len(fn.args.defaults)]
    keyword = [a for a, default in zip(fn.args.kwonlyargs, fn.args.kw_defaults, strict=True) if default is None]
    skip = {positional[0].arg} if method and positional else set()
    return [a.arg for a in [*required, *keyword] if a.arg not in skip]


def disjoint_files(inputs: list[Path], opts: dict) -> list[str]:
    """Error class 4: two tasks of different builders whose files cells list the same path, or a glob that matches."""
    out = []
    for path in inputs:
        rows = sorted(task_rows(lines_of(path)), key=lambda row: row[1])
        for i, (line, task, builder, files) in enumerate(rows):
            for _, other, other_builder, other_files in rows[i + 1 :]:
                if other_builder == builder:
                    continue
                for a, b in ((a, b) for a in files for b in other_files):
                    if a == b or fnmatchcase(a, b) or fnmatchcase(b, a):
                        listed = b if "*" in a else a
                        both = f"Task {task} (builder {builder}) and Task {other} (builder {other_builder})"
                        out.append(f"{name(path)}:{line}: {both} both list {listed}")
    return out


def task_rows(lines: list[str]) -> list[tuple[int, int, str, list[str]]]:
    """(line, task, builder, files) per row of the table under `## Task order`, its columns found by the header."""
    start = next((i for i, line in enumerate(lines) if re.fullmatch(r"##\s+Task order\s*", line.strip())), None)
    if start is None:
        return []
    rows, header = [], []
    for i in range(start + 1, len(lines)):
        text = lines[i].strip()
        if not text.startswith("|"):
            if header or text.startswith("#"):
                break
            continue
        cells = [c.strip() for c in text.strip("|").split("|")]
        if not header:
            header = [c.lower() for c in cells]
            continue
        if not {"builder", "files"} <= set(header) or len(cells) < len(header) or not cells[0].isdigit():
            continue  # the delimiter row, or a row that names no task
        spans = re.findall(r"`([^`]+)`", cells[header.index("files")])
        files = list(dict.fromkeys(f for span in spans for f in braces(span)))
        rows.append((i + 1, int(cells[0]), cells[header.index("builder")], files))
    return rows


def braces(entry: str) -> list[str]:
    """Brace expansion as the shell does it: `src/{a,b}.py` is src/a.py and src/b.py."""
    group = re.search(r"\{([^{}]*)\}", entry)
    if not group:
        return [entry]
    return [x for alt in group.group(1).split(",") for x in braces(entry[: group.start()] + alt + entry[group.end() :])]


def lock_with_deps(inputs: list[Path], opts: dict) -> list[str]:
    """Error class 5: a diff whose section of any pyproject.toml adds a dependency while uv.lock is not in the diff."""
    out = []
    for path in inputs:
        lines = lines_of(path)
        if any(line.startswith("diff --git a/uv.lock ") for line in lines):
            continue
        section = ""
        for n, line in enumerate(lines, 1):
            if line.startswith("diff --git "):
                section = line
            added = not line.startswith("+++") and DEPENDENCY.match(line)
            if added and PYPROJECT.match(section):
                out.append(f"{name(path)}:{n}: pyproject.toml adds a dependency and uv.lock does not change")
    return out


def control_files(inputs: list[Path], opts: dict) -> list[str]:
    """Error class 6: a control file whose hash is not the run's manifest's; a task file whose heading names another
    task, or that no `Task <n>: started by` line of the plan log claims (written ahead). Inputs: the run, the plan."""
    run, plan = inputs
    out = []
    manifest = run / "_manifest.sha256"
    for line in lines_of(manifest) if manifest.is_file() else []:
        entry = MANIFEST_LINE.fullmatch(line.strip())
        if not entry:
            continue
        target = run / entry.group(2)
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != entry.group(1):
            out.append(f"{name(target)}: a control file changed after the run started")
    log = lines_of(run / "plan-log.md") if (run / "plan-log.md").is_file() else []
    for task in sorted(plan.glob("task-*.md")):
        number = re.fullmatch(r"task-(\d+)\.md", task.name)
        if not number:
            continue
        n, first = int(number.group(1)), (lines_of(task) or [""])[0]
        if not first.startswith(f"# Task {n} — "):
            named = re.match(r"# Task (\d+)", first)
            out.append(f"{name(task)}:1: the heading names Task {int(named.group(1)) if named else '?'}")
        if not any(line.startswith(f"Task {n}: started by") for line in log):
            out.append(f'{name(task)}:1: written ahead (no "Task {n}: started by" in plan-log.md)')
    return out


def summaries_and_sizes(inputs: list[Path], opts: dict) -> list[str]:
    """Error class 8: in the input folders, an index over the size limit, and a page without its `.summary.md` summary or
    over the limit (a summary is no page)."""
    limit, out = int(opts.get("max_bytes", 12000)), []
    for folder in inputs:
        for path in sorted(p for p in folder.rglob("*") if p.is_file()):
            size = path.stat().st_size
            if path.name in INDEXES:
                if size > limit:
                    out.append(f"{name(path)}: an index of {size} bytes, over {limit}")
            elif path.suffix == ".md" and not path.name.endswith(".summary.md"):
                if not path.with_name(path.stem + ".summary.md").is_file():
                    out.append(f"{name(path)}: no .summary.md summary")
                if size > limit:
                    out.append(f"{name(path)}: {size} bytes, over {limit}")
    return out


def generated_files(inputs: list[Path], opts: dict) -> list[str]:
    """Error class 9: a generated artifact in a saved `git ls-files` list (the vault's Obsidian settings files are kept)."""
    out = []
    for path in inputs:
        for n, tracked in enumerate((line.strip() for line in lines_of(path)), 1):
            obsidian = any(tracked.startswith(d) and tracked[len(d) :] not in kept for d, kept in OBSIDIAN_KEPT.items())
            if tracked.startswith(GENERATED) or "__pycache__" in tracked.split("/")[:-1] or obsidian:
                out.append(f"{name(path)}:{n}: {tracked} is generated and must not be committed")
    return out


def pages_rule(inputs: list[Path], opts: dict) -> list[str]:
    """Spec 5: a commit with code shows its pages (the write gate's own rule, ADR-0027) and a test."""
    from harness.gates.write import is_code, pages_problem  # a python grader runs under the harness's Python

    out = []
    for path in inputs:
        for commit in json.loads(path.read_text(encoding="utf-8"))["commits"]:
            changed, tasks = commit["changed"], commit["tasks"]
            detail = pages_problem(changed, tasks, tasks)  # commits.json is the planner's word: both lists are it
            if detail:
                out.append(f"{name(path)}: {commit['id']}: {detail}")
            if any(is_code(p) for p in changed) and not any(is_test(p) for p in changed):
                out.append(f"{name(path)}: {commit['id']}: no test")
    return out


def is_test(path: str) -> bool:
    """A test file: a name `test_*` or `*_test.*`, or a `tests/` folder on the way."""
    parts = path.split("/")
    return parts[-1].startswith("test_") or fnmatchcase(parts[-1], "*_test.*") or "tests" in parts[:-1]


def job_timeouts(inputs: list[Path], opts: dict) -> list[str]:
    """Lesson class of 2026-10-29: a job's `timeout` under the longest run of the `harness eval` selection it wraps."""
    from harness.evals import suite_minutes  # a python grader runs under the harness's Python

    out = []
    for path in inputs:
        for n, line in enumerate(lines_of(path), 1):
            m = TIMEOUT.search(line)
            suite = m and SUITE_FLAG.search(m.group(4))
            if not m or not suite or float(m.group(2)) == 0 or NO_SESSIONS.search(m.group(4)):
                continue  # no timed run of a selection, no limit (GNU timeout reads 0 so), or no session to wait for
            case = CASE_FLAG.search(m.group(4))
            need = suite_minutes(opts["base"], suite.group(1), case and case.group(1))
            if float(m.group(2)) * SECONDS[m.group(3)] < need * 60:
                which = f"evals/{suite.group(1)}" + (f" --case {case.group(1)}" if case else "")
                out.append(f"{name(path)}:{n}: timeout {m.group(1)} is under {need} min, the longest {which} can run")
    return out


def ancestor_deny(inputs: list[Path], opts: dict) -> list[str]:
    """Lesson class of 2026-10-29: a write deny on a path the sandbox lets the agent write, or on an ancestor of it."""
    out = []
    for path in inputs:
        settings = json.loads(path.read_text(encoding="utf-8"))
        filesystem = settings.get("sandbox", {}).get("filesystem", {})
        entries = (DENY.fullmatch(entry) for entry in settings.get("permissions", {}).get("deny", []))
        denies = [
            (m.group(0), m.group(1)[1:] if m.group(1).startswith(("//", "/<")) else m.group(1)) for m in entries if m
        ] + [(f"denyWrite {entry}", entry) for entry in filesystem.get("denyWrite", [])]
        for written in filesystem.get("allowWrite", []):
            cuts = [written] + [written[:i] for i, c in enumerate(written) if c == "/"]  # the path and its ancestors
            for shown, pattern in denies:
                if any(fnmatchcase(cut, pattern.removesuffix("/**")) for cut in cuts):
                    out.append(f"{name(path)}: {shown} covers the written path {written}")
    return out


def handoff_notes(inputs: list[Path], opts: dict) -> list[str]:
    """Lesson class of 2026-10-29: a hand-over note that points at files instead of carrying its facts."""
    from pipeline_note import problems  # Python puts the script's folder on sys.path

    out = []
    for path in inputs:
        facts = json.loads(path.with_suffix(".facts.json").read_text(encoding="utf-8"))
        out += [f"{name(path)}: {line}" for line in problems(path.read_text(encoding="utf-8"), facts)]
    return out


def waiters(inputs: list[Path], opts: dict) -> list[str]:
    """Spec 10.19: no `sleep` in a command, and every waiter run as a brief gives it (a <placeholder> is one word)."""
    forms = [
        re.compile(PLACEHOLDER.sub(r"\\S+", re.escape(" ".join(span.group(2).split()))))
        for path in inputs
        if path.suffix == ".md"
        for paragraph in paragraphs(lines_of(path))
        for span in SPAN.finditer(paragraph)
        if WAITER.search(span.group(2))
    ]
    out = []
    for path in (p for p in inputs if p.suffix == ".jsonl"):
        for n, command in bash_commands(path):
            flat = " ".join(command.split())
            if SLEEP.search(command):
                out.append(f"{name(path)}:{n}: sleep: {flat}")
            if WAITER.search(command) and not any(form.search(flat) for form in forms):
                out.append(f"{name(path)}:{n}: waiter not as the brief gives it: {flat}")
    return out


def bash_commands(path: Path) -> list[tuple[int, str]]:
    """A transcript's Bash commands on their line numbers: `input.command` of each `tool_use` item named `Bash`."""
    out = []
    for n, line in enumerate(lines_of(path), 1):
        record = json.loads(line) if line.strip() else None
        message = record.get("message") if isinstance(record, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        for item in content if isinstance(content, list) else []:
            if isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") == "Bash":
                out.append((n, (item.get("input") or {}).get("command", "")))
    return out


CHECKS: dict[str, Callable[[list[Path], dict], list[str]]] = {
    "cited-lines": cited_lines,
    "expected-lines": expected_lines,
    "tests-can-fail": tests_can_fail,
    "disjoint-files": disjoint_files,
    "lock-with-deps": lock_with_deps,
    "control-files": control_files,
    "summaries-and-sizes": summaries_and_sizes,
    "generated-files": generated_files,
    "pages-rule": pages_rule,
    "job-timeouts": job_timeouts,
    "ancestor-deny": ancestor_deny,
    "handoff-notes": handoff_notes,
    "waiters": waiters,
}


def run_check(check: str, inputs: list[str], opts: dict) -> list[str]:
    """The check's findings, sorted and printed one per line."""
    found = sorted(set(CHECKS[check]([Path(i) for i in inputs], opts)))
    if found:
        print("\n".join(found))
    return found


def case(workspace: Path) -> int:
    """One case: the check's findings on the workspace's inputs against `found` of its expect.json."""
    expect = json.loads((workspace / "expect.json").read_text(encoding="utf-8"))
    os.chdir(workspace)  # the inputs and the base resolve against the workspace and are named as written
    opts = {"base": Path(expect.get("base", ".")), "max_bytes": expect.get("max_bytes", 12000)}
    found, want = run_check(expect["check"], expect["inputs"], opts), sorted(expect["found"])
    missing, unexpected = [f for f in want if f not in found], [f for f in found if f not in want]
    for line in [f"missing: {f}" for f in missing] + [f"unexpected: {f}" for f in unexpected]:
        print(line, file=sys.stderr)
    return 0 if found == want else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="The pipeline evals' code checks; see the module's docstring.")
    parser.add_argument("--check", choices=sorted(CHECKS), help="measure mode: run this check on the inputs")
    parser.add_argument("--root", default=".", help="measure mode: the base that cited lines resolve against")
    parser.add_argument("paths", nargs="+", metavar="PATH", help="a case's workspace, or with --check the inputs")
    args = parser.parse_args()
    if args.check:
        return 1 if run_check(args.check, args.paths, {"base": Path(args.root)}) else 0
    return case(Path(args.paths[0]))


if __name__ == "__main__":
    sys.exit(main())
