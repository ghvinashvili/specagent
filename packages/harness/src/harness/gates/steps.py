"""harness/gates/steps.py — every numbered step of a type's Working method carries one rule,
`<!-- check: ... -->` at its end, and the gate checks the rule against the session's transcript and the files of the
stage (specs/001-chat-depth/spec.md, part 2). A rule names the trace a step leaves; it never asks a model.

The language is small and closed:
  read: <glob>                 a Read of a matching file succeeded, or the file was in the prompt (pack.md, prompt.md)
  ran: <program> [args]        a Bash call ran it: first program of a segment after the wrappers, not refused
       ... failed | passed     the runner's own summary line says so (pytest), else a one-program call's exit code
       ... before: edit: <glob> the run came before the first Edit or Write of a matching file; `code` is every file
                               of the repository that TEST_PATH does not match
  wrote: <glob>                a matching, non-empty file exists under the stage directory
  output: <check>              the gate's check of that name passed in this gate run (`*` stands for a field the
                               gate fills in, as in `* has the five sections`)
  when: <condition>            the rest applies only when: code_changed | input: <glob> | stage: <id>[,<id>]
  trust: <reason>              the step leaves no trace a script can check; the reason is shown
Clauses are separated by `;` and must all hold. `trust:` stands alone.
"""

from __future__ import annotations

import ast
import fnmatch
import re
import shlex
from pathlib import Path

import yaml

from .. import access
from . import _common
from ._common import TEST_PATH, check

COMMENT = re.compile(r"<!--\s*check:(.*?)-->", re.DOTALL)
STEP = re.compile(r"^(\d+)\.\s")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
PLACEHOLDERS = ("test", "lint", "types")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# pytest's own summary line: `3 failed, 61 passed, 10 errors in 1.43s`, `no tests ran in 0.00s`, framed by `=` with -v
PYTEST_SUMMARY = re.compile(
    r"^=*\s*(?P<body>(?:\d+ [a-z]+(?:, )?)+|no tests ran) in [\d.]+s(?: \(\d+:\d\d:\d\d\))?\s*=*$"
)
UV_VALUE_OPTIONS = {
    "--package",
    "--directory",
    "--project",
    "--with",
    "--with-editable",
    "--with-requirements",
    "--python",
    "-p",
    "--group",
    "--extra",
    "--env-file",
    "--index",
    "--default-index",
    "--from",
}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
PYTHON = re.compile(r"^python(\d(\.\d+)?)?$")


# ---------------------------------------------------------------- the type file: steps and their rules


def method_steps(text: str) -> list[dict]:
    """The numbered steps of the `Working method` section: {"n", "line" (1-based), "last" (the step's last line),
    "rules": [the text of every `<!-- check: ... -->` in the step]}. A step is its numbered line and the indented or
    continued lines below it, up to a blank line, the next numbered line or the next heading."""
    out: list[dict] = []
    inside, level, open_ = False, 0, False
    for i, line in enumerate(text.splitlines(), 1):
        h = HEADING.match(line)
        if h:
            if inside and len(h.group(1)) <= level:
                break
            inside = inside or h.group(2).strip().lower() == "working method"
            level = level or (len(h.group(1)) if inside else 0)
            open_ = False
            continue
        m = STEP.match(line) if inside else None
        if m:
            out.append({"n": int(m.group(1)), "line": i, "last": i, "text": line})
            open_ = True
        elif open_ and line.strip() and line[0].isspace():
            out[-1]["last"], out[-1]["text"] = i, out[-1]["text"] + "\n" + line
        else:
            open_ = False
    for step in out:
        step["rules"] = [r.strip() for r in COMMENT.findall(step["text"])]
    return out


def agent_steps(root: Path, role_type: str) -> list[dict]:
    """The steps of `.claude/agents/<type>.md`, or [] when the type has no agent file."""
    path = root / ".claude" / "agents" / f"{role_type}.md"
    return method_steps(path.read_text(encoding="utf-8")) if path.is_file() else []


def insert_rules(text: str, rules: dict[int, str]) -> str:
    """The text with `<!-- check: <rule> -->` at the end of the last line of every step numbered in `rules`. A step
    that already carries a rule gets none added; a number the method does not have raises ValueError."""
    steps = {s["n"]: s for s in method_steps(text)}
    unknown = sorted(set(rules) - set(steps))
    if unknown:
        raise ValueError(f"the Working method has no step {', '.join(map(str, unknown))}")
    lines = text.splitlines(keepends=True)
    for n, rule in rules.items():
        step = steps[n]
        if step["rules"]:
            continue
        i = step["last"] - 1
        end = "\n" if lines[i].endswith("\n") else ""
        lines[i] = lines[i].rstrip("\n").rstrip() + f" <!-- check: {rule} -->" + end
    return "".join(lines)


# ---------------------------------------------------------------- the rule language


def parse(rule: str) -> dict:
    """{"when": (kind, value) | None, "trust": reason | None, "clauses": [...]}; ValueError names what is wrong."""
    body = rule.strip()
    if body.startswith("trust:"):
        reason = body[len("trust:") :].strip()
        if not reason:
            raise ValueError("trust: needs a reason")
        return {"when": None, "trust": reason, "clauses": []}
    parts = [p.strip() for p in body.split(";")]
    if not body or any(not p for p in parts):
        raise ValueError("an empty clause")
    out: dict = {"when": None, "trust": None, "clauses": []}
    for part in parts:
        kind, _, value = part.partition(":")
        kind, value = kind.strip(), value.strip()
        if kind == "when":
            if out["when"] or out["clauses"]:
                raise ValueError("when: comes first, once")
            out["when"] = _condition(value)
        elif kind == "trust":
            raise ValueError("trust: stands alone")
        elif kind in ("read", "wrote") and value and " " not in value:
            out["clauses"].append({"kind": kind, "glob": value})
        elif kind == "output" and value:
            out["clauses"].append({"kind": "output", "check": value})
        elif kind == "ran" and value:
            out["clauses"].append(_parse_ran(value))
        else:
            raise ValueError(f"not a rule of the language: {part!r}")
    if not out["clauses"]:
        raise ValueError("when: needs a rule after it")
    return out


def _condition(value: str) -> tuple[str, str]:
    kind, _, arg = value.partition(":")
    kind, arg = kind.strip(), arg.strip()
    if kind == "code_changed" and not arg:
        return ("code_changed", "")
    if kind in ("input", "stage") and arg and " " not in arg.replace(", ", ","):
        return (kind, arg.replace(" ", ""))
    raise ValueError(f"not a condition: {value!r}")


def _parse_ran(value: str) -> dict:
    before = None
    if " before: " in f" {value} ":
        value, _, rest = value.partition("before:")
        kind, _, glob = rest.strip().partition(":")
        if kind.strip() != "edit" or not glob.strip() or " " in glob.strip():
            raise ValueError(f"before: takes edit: <glob>, not {rest.strip()!r}")
        before = glob.strip()
    words = value.split()
    outcome = words.pop() if words and words[-1] in ("failed", "passed") else None
    if not words:
        raise ValueError("ran: needs a program")
    if words[0].startswith("{") and words[0].strip("{}") not in PLACEHOLDERS:
        raise ValueError(f"unknown placeholder {words[0]}")
    return {"kind": "ran", "words": words, "outcome": outcome, "before": before}


# ---------------------------------------------------------------- commands: segments, wrappers, runners


# A Bash call cut into what a here-document needs to be found: quoted text, an escaped character, the here-string and
# here-document operators, a line end, and runs of anything else.
SHELL_TOKEN = re.compile(r"""'[^']*'|"(?:\\.|[^"\\])*"|\\.|<<<|<<-?|\n|[^'"\\<\n]+|.""", re.DOTALL)
HEREDOC_WORD = re.compile(r"""[ \t]*((?:'[^']*'|"[^"]*"|\\.|[^\s|&;()<>'"\\])+)""")  # the delimiter after `<<`


def without_bodies(command: str) -> str:
    """A Bash call without the bodies of its here-documents: the line that opens one stays, and so does every line
    after its terminator (the delimiter alone on a line; after `<<-` with its tabs taken off). A here-string (`<<<`)
    has no body, and `<<` inside quotes opens nothing; bodies opened on one line follow each other in order."""
    out: list[str] = []
    pending: list[tuple[str, bool]] = []  # the delimiter of every here-document the current line opens, `<<-` or not
    pos = 0
    while pos < len(command):
        m = SHELL_TOKEN.match(command, pos)
        token, pos = m.group(0), m.end()
        word = HEREDOC_WORD.match(command, pos) if token in ("<<", "<<-") else None
        if word:
            pending.append(("".join(shlex.split(word.group(1))), token == "<<-"))
            token, pos = command[m.start() : word.end()], word.end()
        out.append(token)
        if token == "\n":
            for delimiter, tabs in pending:
                while pos < len(command):
                    end = command.find("\n", pos)
                    end = len(command) if end < 0 else end  # no terminator: the body runs to the end of the call
                    line, pos = command[pos:end], end + 1
                    if (line.lstrip("\t") if tabs else line) == delimiter:
                        break
            pending = []
    return "".join(out)


def segments(command: str) -> list[list[str]]:
    """The words of every simple command of a Bash call, split at `&&`, `||`, `;`, `|`, `&` and line ends outside
    quotes. A here-document's body is not a command, the lines after its terminator are (without_bodies)."""
    command = without_bodies(command)
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars="();<>|&\n")
        lex.whitespace = " \t\r"
        tokens = list(lex)
    except ValueError:  # an unbalanced quote: split on the operators alone
        tokens = re.sub(r"(&&|\|\||[;|&\n])", r" \1 ", command).split()
    # shlex joins operator characters that stand together: `;\n`, `&&\n` and the `\n\n` of a blank line are an
    # operator and line ends, each of which ends a command
    tokens = [p for t in tokens for p in (re.split(r"(\n)", t) if "\n" in t and not t.strip("();<>|&\n") else [t]) if p]
    out, cur = [], []
    for tok in tokens:
        if tok in ("&&", "||", ";", "|", "&", "\n", ";;", "|&"):
            out, cur = (out + [cur] if cur else out), []
        elif tok not in ("(", ")"):
            cur.append(tok)
    return out + [cur] if cur else out


def unwrap(words: list[str]) -> list[str]:
    """The words of a simple command from its runner on: `NAME=value`, `env NAME=value`, `uv run [options]`,
    `uvx [options]`, `npx [options]`, `python -m` and `python3 -m` are taken off the front (correction 3)."""
    w = list(words)
    while w:
        head = Path(w[0]).name
        if ASSIGNMENT.match(w[0]):
            w = w[1:]
        elif head == "env":
            w = w[1:]
            while w and ASSIGNMENT.match(w[0]):
                w = w[1:]
        elif head == "uv" and len(w) > 1 and w[1] == "run":
            w = _options(w[2:])
        elif head in ("uvx", "npx"):
            w = _options(w[1:])
        elif PYTHON.match(head) and len(w) > 1 and w[1] == "-m":
            w = w[2:]
        else:
            break
    return w


def _options(w: list[str]) -> list[str]:
    while w and w[0].startswith("-"):
        w = w[2:] if w[0] in UV_VALUE_OPTIONS else w[1:]
    return w


def runners(command: str) -> list[list[str]]:
    """Every program a Bash call runs, as its words from the runner on; `cd <dir>` segments are left out."""
    out = []
    for seg in segments(command):
        w = unwrap(seg)
        if w and Path(w[0]).name not in ("cd", "pushd"):
            out.append(w)
    return out


def runner_of(command: list[str] | None) -> list[str] | None:
    """The runner of a project command (`uv run pytest -q` -> `pytest`): the first program after the wrappers."""
    if not command:
        return None
    w = unwrap(command)
    return w[:1] or None


def _starts(words: list[str], pattern: list[str]) -> bool:
    """The words begin with the pattern: the program by its file name (`python` stands for every python3.x), the
    words after it by fnmatch (`ran: python *probes/*.py`)."""
    if len(words) < len(pattern):
        return False
    head = Path(words[0]).name
    if not (head == pattern[0] or (pattern[0] == "python" and PYTHON.match(head))):
        return False
    return all(fnmatch.fnmatchcase(w, p) for w, p in zip(words[1 : len(pattern)], pattern[1:], strict=True))


def pytest_outcome(output: str) -> str | None:
    """`failed`, `passed` or None from pytest's own summary lines in a call's output, colour codes removed: failed
    when a line counts a failure or an error, passed when one counts passes and none counts either."""
    seen = None
    for line in ANSI.sub("", output).splitlines():
        m = PYTEST_SUMMARY.match(line.strip())
        if not m:
            continue
        counts = {w: int(n) for n, w in re.findall(r"(\d+) ([a-z]+)", m.group("body"))}
        if counts.get("failed", 0) or counts.get("error", 0) or counts.get("errors", 0):
            return "failed"
        if counts.get("passed", 0):
            seen = "passed"
    return seen


# ---------------------------------------------------------------- evaluating one rule


def _matches(path: str, glob: str) -> bool:
    return fnmatch.fnmatchcase(path, glob) or fnmatch.fnmatchcase(path, "*/" + glob)


def repo_path(path: str, roots: list[str]) -> str | None:
    """The path of a file inside the repository: what follows `.claude/worktrees/<name>/`, a repository root the
    session worked in, or nothing for an absolute path outside them; a relative name (of the material) as it is."""
    if "/.claude/worktrees/" in path:
        return path.split("/.claude/worktrees/", 1)[1].split("/", 1)[-1]
    if not path.startswith("/"):
        return path
    under = sorted((r.rstrip("/") for r in roots if path.startswith(r.rstrip("/") + "/")), key=len)
    return path[len(under[0]) + 1 :] if under else None


def _code(path: str, ctx: dict) -> bool:
    """`code`: a file of the repository, not of the run, that TEST_PATH does not match."""
    if f"/{ctx['run_id']}/" in path or path.startswith(("input/", "output/")) or path == "prompt.md":
        return False
    rel = repo_path(path, ctx["roots"])
    return rel is not None and not TEST_PATH.search(rel)


def _edited(path: str, glob: str, ctx: dict) -> bool:
    return _code(path, ctx) if glob == "code" else _matches(path, glob)


def _pattern(words: list[str], ctx: dict) -> list[str] | None:
    """The words a `ran:` rule looks for; a placeholder is the runner of the project command, None when the project
    names no such command."""
    if words[0].startswith("{"):
        runner = runner_of(ctx["commands"].get(words[0].strip("{}")))
        return runner + words[1:] if runner else None
    return words


def _runs(pattern: list[str], events: list[dict]) -> list[dict]:
    return [
        e
        for e in events
        if e["tool"] == "Bash" and not e["denied"] and any(_starts(w, pattern) for w in runners(e["command"]))
    ]


def _outcome(call: dict, pattern: list[str]) -> str | None:
    if Path(pattern[0]).name == "pytest":
        return pytest_outcome(call["output"])
    if len(runners(call["command"])) != 1 or call["exit_code"] is None:  # no summary line: one program, its code
        return None
    return "passed" if call["exit_code"] == 0 else "failed"


def _first_edit(glob: str, ctx: dict) -> int | None:
    """The position of the first successful Edit or Write of a file the glob takes in."""
    edits = [e for e in ctx["events"] if e["tool"] in ("Edit", "Write") and e["ok"]]
    return next((e["seq"] for e in edits if _edited(e["file"], glob, ctx)), None)


def _check_ran(clause: dict, ctx: dict) -> tuple[str, str]:
    pattern = _pattern(clause["words"], ctx)
    if pattern is None:
        return "n/a", f"the project names no {clause['words'][0]} command"
    if ctx["events"] is None:
        return "n/a", "no transcript"
    calls = _runs(pattern, ctx["events"])
    if clause["outcome"]:
        calls = [c for c in calls if _outcome(c, pattern) == clause["outcome"]]
    first = _first_edit(clause["before"], ctx) if clause["before"] else None
    if first is not None:
        calls = [c for c in calls if c["seq"] < first]
    if calls:
        return "pass", f"#{calls[-1]['seq']} `{calls[-1]['command'][:80]}`"
    what = f"no `{' '.join(pattern)}` run" + (f" that {clause['outcome']}" if clause["outcome"] else "")
    return "fail", what + (f" before the first edit of {clause['before']} (#{first})" if first is not None else "")


def _check_read(clause: dict, ctx: dict) -> tuple[str, str]:
    glob = clause["glob"]
    given = next((f for f in ctx["prompt_files"] if _edited(f, glob, ctx)), None)
    if given:
        return "pass", f"`{given}` was in the prompt"
    if ctx["events"] is None:
        return "n/a", "no transcript"
    reads = [e for e in ctx["events"] if e["tool"] == "Read" and e["ok"]]
    opened = next((e for e in reads if _edited(e["file"], glob, ctx)), None)
    if opened:
        return "pass", f"#{opened['seq']} read `{opened['file']}`"
    return "fail", f"no Read of {glob}, and it was not in the prompt"


def _check_wrote(clause: dict, ctx: dict) -> tuple[str, str]:
    sd: Path = ctx["stage_dir"]
    found = [
        p.relative_to(sd).as_posix()
        for p in sorted(sd.rglob("*"))
        if p.is_file() and p.stat().st_size > 0 and fnmatch.fnmatchcase(p.relative_to(sd).as_posix(), clause["glob"])
    ]
    return ("pass", f"`{found[0]}`") if found else ("fail", f"no file {clause['glob']} in the stage directory")


def name_matches(name: str, wanted: str) -> bool:
    """A check name against a name of a rule, where `*` in either stands for any text (a field the gate fills in)."""

    def rx(s: str) -> str:
        return re.escape(s).replace(r"\*", ".*")

    return bool(re.fullmatch(rx(wanted), name) or re.fullmatch(rx(name), wanted))


def _check_output(clause: dict, ctx: dict) -> tuple[str, str]:
    found = {n: ok for n, ok in ctx["gate"].items() if name_matches(n, clause["check"])}
    if not found:
        return "n/a", f"the gate of stage {ctx['stage_id']} has no check {clause['check']!r}"
    failed = [n for n, ok in found.items() if not ok]
    return ("fail", f"the check {failed[0]!r} failed") if failed else ("pass", "the gate's check passed")


CHECKERS = {"ran": _check_ran, "read": _check_read, "wrote": _check_wrote, "output": _check_output}


def _holds(when: tuple[str, str], ctx: dict) -> bool:
    kind, arg = when
    if kind == "code_changed":
        return bool(ctx["code_changed"])
    if kind == "stage":
        return ctx["stage_id"] in arg.split(",")
    inp: Path = ctx["stage_dir"] / "input"
    files = [p.relative_to(inp).as_posix() for p in inp.rglob("*")] if inp.is_dir() else []
    return any(_matches(f, arg) for f in files)


def evaluate(rule: str, ctx: dict) -> tuple[str, str]:
    """(`pass` | `fail` | `n/a` | `trust`, detail) of one step's rule. `n/a`: its condition does not hold, or what it
    names does not exist here (a gate without that check, a project without that command, no transcript)."""
    try:
        parsed = parse(rule)
    except ValueError as exc:
        return "fail", f"the rule is not in the language: {exc}"
    if parsed["trust"]:
        return "trust", parsed["trust"]
    if parsed["when"] and not _holds(parsed["when"], ctx):
        return "n/a", f"when: {':'.join(x for x in parsed['when'] if x)} does not hold"
    passed, detail = [], ""
    for clause in parsed["clauses"]:
        result, detail = CHECKERS[clause["kind"]](clause, ctx)
        if result == "fail":
            return "fail", detail
        if result == "pass":
            passed.append(detail)
    return ("pass", "; ".join(passed)) if passed else ("n/a", detail)


def context(repo: Path, run_dir: Path, stage_dir: Path, events: list[dict] | None, gate: dict[str, bool]) -> dict:
    """What a rule is evaluated against for one unit: its transcript events (None without a transcript), the files
    of its prompt, the repository roots its paths are relative to, the project's commands, whether code changed,
    and the checks of its gate (name: passed)."""
    parts = stage_dir.relative_to(run_dir / "stages").parts
    roots = {str(repo.resolve())}
    for e in events or []:
        for p in (e.get("file") or "", e.get("cwd") or ""):
            if "/.claude/worktrees/" in p:
                roots.add(p.split("/.claude/worktrees/")[0])
            elif p and p == e.get("cwd"):
                roots.add(p)
    inp = stage_dir / "input"
    patch = inp.is_dir() and any(inp.rglob("changes.patch"))
    branch = _common.unit_branch(repo, run_dir, stage_dir)
    base = _common.base_commit(repo, run_dir)
    commits = branch and base and _common.git(repo, "rev-list", "--count", f"{base}..{branch}").stdout.strip()
    return {
        "events": events,
        "stage_dir": stage_dir,
        "stage_id": parts[0],
        "run_id": run_dir.name,
        "prompt_files": _common.prompt_files(stage_dir),
        "roots": sorted(roots),
        "commands": {k: _common.project_command(run_dir, k) for k in PLACEHOLDERS},
        "code_changed": bool(patch or (commits and commits != "0")),
        "gate": gate,
    }


def step_checks(steps: list[dict], ctx: dict) -> list[dict]:
    """One check per step that carries a rule, named `step <n>: <rule>`; `n/a` and `trust` pass with their reason."""
    out = []
    for step in steps:
        if not step["rules"]:
            continue  # a step without a rule is `harness validate`'s finding, not the session's
        result, detail = evaluate(step["rules"][0], ctx)
        out.append(check(f"step {step['n']}: {step['rules'][0]}", result != "fail", f"{result}: {detail}"))
    return out


# ---------------------------------------------------------------- `harness validate`


def _literal(node: ast.AST | None) -> str | None:
    """A check name as the source writes it: a string, or an f-string with `*` for every field."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(str(v.value) if isinstance(v, ast.Constant) else "*" for v in node.values)
    return None


def gate_names(gate: str) -> set[str]:
    """The names of the checks a gate module may return, read from its source and from the gate modules it imports
    (one level of `from .x import`, transitively), the shared checks of `__init__.py` and `_common.py` included."""
    here = Path(__file__).parent
    todo, seen, names = [gate, "__init__", "_common"], set(), set()
    while todo:
        mod = todo.pop()
        if mod in seen or not (here / f"{mod}.py").is_file():
            continue
        seen.add(mod)
        tree = ast.parse((here / f"{mod}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                todo.append(node.module)
            elif isinstance(node, ast.Call) and getattr(node.func, "id", None) == "check" and node.args:
                names.add(_literal(node.args[0]))
            elif isinstance(node, ast.Dict):
                names |= {_literal(v) for k, v in zip(node.keys, node.values, strict=True) if _literal(k) == "name"}
    return {n for n in names if n}


def stages_of_types(root: Path) -> dict[str, set[str]]:
    """Role type -> the stage ids (= gate modules) that serve it, over the default table and every pipeline."""
    roles = root / "docs" / "roles"
    out: dict[str, set[str]] = {}
    for table in [roles / "stages.yaml", *sorted((roles / "pipelines").glob("*.yaml"))]:
        for row in (yaml.safe_load(table.read_text(encoding="utf-8")) or {}).get("stages", []):
            out.setdefault(row.get("role_type"), set()).add(row.get("id"))
    return out


def _rule_problems(name: str, n: int, rule: str, stages: set[str], names: set[str]) -> list[str]:
    try:
        parsed = parse(rule)
    except ValueError as exc:
        return [f"{name}: step {n}: {exc}"]
    out = []
    if parsed["when"] and parsed["when"][0] == "stage":
        out += [
            f"{name}: step {n}: no table gives stage {s} to {name}"
            for s in parsed["when"][1].split(",")
            if s not in stages
        ]
    for c in parsed["clauses"]:
        if c["kind"] == "output" and not any(name_matches(have, c["check"]) for have in names):
            out.append(f"{name}: step {n}: output: names a check no gate of {name} has: {c['check']!r}")
    return out


def problems(root: Path) -> list[str]:
    """For `harness validate`: in every agent file but the manager's, a rule outside the language, a step with more
    than one rule, an `output:` naming a check no gate of the type has, a `when: stage:` naming a stage the type does
    not serve; and, once need-to-know.yaml gives the type a `steps` mode, a step without a rule."""
    policy = access.load_policy(root)
    serving = stages_of_types(root)
    out: list[str] = []
    for path in sorted((root / ".claude" / "agents").glob("*.md")):
        name = path.stem
        if name == "manager":
            continue
        names = {n for g in serving.get(name, set()) for n in gate_names(g)}
        required = access.steps_mode(policy, name) is not None
        for step in method_steps(path.read_text(encoding="utf-8")):
            if not step["rules"]:
                out += [f"{name}: step {step['n']} has no rule `<!-- check: ... -->`"] if required else []
            elif len(step["rules"]) > 1:
                out.append(f"{name}: step {step['n']} has {len(step['rules'])} rules; one comment holds them all")
            else:
                out += _rule_problems(name, step["n"], step["rules"][0], serving.get(name, set()), names)
    return out
