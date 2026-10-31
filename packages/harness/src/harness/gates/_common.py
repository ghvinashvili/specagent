"""Helpers shared by the stage gates. A gate reads files and runs fixed commands; it never asks a model."""

from __future__ import annotations

import configparser
import fnmatch
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from .. import access
from ..gitcall import GIT
from . import _sandbox

LOCATOR = re.compile(r"`[^`\s]+:\d+(?:-\d+)?`")  # `path:line` or `path:line-line`
TEST_CMD = ["uv", "run", "pytest", "-q"]  # the repository's test command (`just test`)
TEST_TIMEOUT = 1800
# The project's commands by kind, the one source of `{test}`, `{lint}` and `{types}` in the step rules: AGENTS.md:10-11,
# justfile:7 and :10, .github/workflows/ci.yml:16-17. The repository names no type-check command.
PROJECT_COMMANDS: dict[str, list[str] | None] = {
    "test": TEST_CMD,
    "lint": ["uv", "run", "ruff", "check", "."],
    "types": None,
}
SPAN = re.compile(r"`([^`\s]+?):(\d+)(?:-(\d+))?`")  # a location as the role rules ask for it: in inline code
# a location wherever it stands, in inline code or not (spec part 6: every `path:line`): path characters, a line, an
# optional end; locators() keeps the ones that look like a path
PATH_LINE = re.compile(r"(?<![\w./~@+-])([\w./~@+-]+):(\d+)(?:-(\d+))?(?!\w)")
QUOTED = re.compile(r"\"[^\"\n]*\"|“[^”\n]*”|„[^“”\n]*[“”]")  # a quotation: its locations are the quoted text's own
TEXT_EXT = {
    "c", "cfg", "cpp", "css", "csv", "diff", "go", "h", "hpp", "html", "ini", "java", "js", "json", "jsonl", "jsx",
    "lock", "md", "patch", "php", "py", "rb", "rs", "sh", "sql", "toml", "ts", "tsx", "txt", "xml", "yaml", "yml",
}  # fmt: skip
# Added lines that look like a credential. gitleaks, when installed, runs as well; this list is the floor.
SECRETS = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|sk-[A-Za-z0-9_-]{20,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|(?i:(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"\s]{16,}['\"])"
)
# An open question a spec or a plan still carries: `[NEEDS CLARIFICATION: <question>]`. A sentence that only names
# the marker ("no `[NEEDS CLARIFICATION]` markers exist", seen live in a plan) is not one.
OPEN_MARKER = re.compile(r"\[NEEDS CLARIFICATION:\s*[^\]\s]")
TEST_PATH = re.compile(r"(^|/)(tests?|evals)/|(^|/)test_[^/]+$|_test\.[a-z]+$|(^|/)conftest\.py$")


def check(name: str, passed: bool, detail: str = "") -> dict:
    return {"name": name, "passed": bool(passed), **({"detail": detail[:300]} if detail else {})}


def stage_file(stage_dir: Path, rel: str | Path) -> Path | None:
    """The file of a stage at `rel`, or None when there is none, or when it is a link or leads out of the stage
    directory: a gate runs outside the sandbox, and what it reads may come back to the session in a check's detail
    (docs/decisions/0020). As an `outputs` path that leaves the stage directory names nothing (state.output_file)."""
    p = stage_dir / rel
    try:
        if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(stage_dir.resolve()):
            return None
    except OSError:
        return None
    return p


def text(stage_dir: Path, rel: str) -> str:
    p = stage_file(stage_dir, rel)
    return p.read_text(encoding="utf-8") if p else ""


def result(stage_dir: Path) -> dict:
    p = stage_file(stage_dir, "result.json")
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p else {}
    except (OSError, json.JSONDecodeError):
        return {}


def is_file(path: Path) -> bool:
    """Whether a path a stage's text names is a file the gate can see. False also where the system refuses to look:
    a component longer than a file name may be (OSError 36), a folder the gate may not enter (PermissionError)."""
    try:
        return path.is_file()
    except OSError:
        return False


def file_lines(path: Path) -> list[str] | None:
    """The lines of the file a path a stage's text names, or None when the gate can see or read no file there."""
    if not is_file(path):
        return None
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None


def inside(base: Path, rel: str) -> str | None:
    """The path of `base / rel` from `base` once every `..` and link on it is resolved, or None when it leaves `base`
    (an absolute path, `..`, a link out) or the system refuses to look."""
    try:
        return (base / rel).resolve().relative_to(base.resolve()).as_posix()
    except (OSError, ValueError):
        return None


def is_closed(rel: str, closed: list[str] | tuple = ()) -> bool:
    """Whether a repository path is one of `closed` (closed_paths), also inside a checkout under `.claude/worktrees/`,
    where the session's Read deny rules name it too."""
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel, f".claude/worktrees/*/{p}") for p in closed)


def closed_paths(root: Path, run_dir: Path, stage_dir: Path) -> list[str]:
    """The repository paths the stage's type may not read (access.unreadable: its row and the project's settings), from
    the run's manifest and the policy; the project settings' paths alone when either cannot be read. What the read gate
    and the locator check never open: they run outside the sandbox, and what they find reaches the session in a check's
    detail (docs/decisions/0020, 0025)."""
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        sid = stage_dir.relative_to(run_dir / "stages").parts[0]
        role_type = next(s["role_type"] for s in manifest["stages"] if s["id"] == sid)
        row = access.type_row(access.load_policy(root), role_type)
    except (OSError, ValueError, KeyError, StopIteration, access.AccessError):
        return access.settings_closed(root)
    return access.unreadable(row, root)


NUMBERING = r"(?:(?:\d+(?:\.\d+)*[.)]?|[A-Z](?:\.\d+)+[.)]?|[A-Z][.)])\s+)?"  # `4.`, `4.1`, `A.2`, `B)`


def sections(md: str) -> dict[str, str]:
    """Heading text (lower case, without numbering) -> body, for every heading of any level."""
    out, name, buf = {}, None, []
    for line in md.splitlines():
        m = re.match(rf"^#{{1,6}}\s+{NUMBERING}(.+?)\s*$", line)
        if m:
            if name is not None:
                out[name] = "\n".join(buf)
            name, buf = m.group(1).strip().lower(), []
        elif name is not None:
            buf.append(line)
    if name is not None:
        out[name] = "\n".join(buf)
    return out


def has_sections(md: str, names: list[str]) -> list[str]:
    """The names that are missing. A heading matches when it starts with the name, so "Risks" matches "Risks and tests"."""
    found = sections(md)
    return [n for n in names if not any(h.startswith(n.lower()) for h in found)]


SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")  # the line under the header row of a table


def _header(lines: list[str], i: int) -> bool:
    """Whether stripped line i is the header row of a table: a row the separator follows."""
    return lines[i].startswith("|") and i + 1 < len(lines) and bool(SEPARATOR.match(lines[i + 1]))


def _body_row(lines: list[str], i: int) -> bool:
    """Whether stripped line i is a row of a table's body: neither its header row nor its separator."""
    return lines[i].startswith("|") and not SEPARATOR.match(lines[i]) and not _header(lines, i)


def statements(md: str) -> list[str]:
    """List items and table rows: the lines that state something. Headings, blank lines, the separator of a table and
    its header row are left out; a row no separator follows is no header and states something."""
    lines = [line.strip() for line in md.splitlines()]
    return [s for i, s in enumerate(lines) if re.match(r"^([-*]|\d+[.)])\s+\S", s) or _body_row(lines, i)]


def _cells(row: str) -> list[str]:
    """The stripped cells of a table row."""
    return [c.strip() for c in row.strip("|").split("|")]


def table_rows(md: str) -> list[list[str]]:
    """Cells of every table row, without the header row and the separator of each table."""
    lines = [line.strip() for line in md.splitlines()]
    return [_cells(s) for i, s in enumerate(lines) if _body_row(lines, i)]


FINDING_HEADS = {"no": "no", "#": "no", "location": "location", "source": "source", "severity": "severity"}


def _finding(heads: list[str], cells: list[str]) -> dict[str, str]:
    """One row of a critic's table by the word each column is headed with; "" for a column the table lacks."""
    cell: dict[str, str] = {}
    for head, value in zip(heads, cells, strict=False):
        cell.setdefault(head, value)  # the first column of a name wins
    return {"no": cell.get("no", "") if "no" in heads else cells[0], "location": cell.get("location", ""),
            "source": cell.get("source", ""), "severity": cell.get("severity", "").strip("`* ").lower()}  # fmt: skip


def critique_rows(md: str) -> list[tuple[dict[str, str], str]] | None:
    """critique_table with the line of every finding, for a message that quotes the rows whole (harness/rounds.py)."""
    lines = [line.strip() for line in md.splitlines()]
    found: list[tuple[dict[str, str], str]] | None = None
    for i in [i for i in range(len(lines)) if _header(lines, i)]:
        heads = [FINDING_HEADS.get(c.strip("`*_ ").lower().split(" ")[0].rstrip(".:"), "") for c in _cells(lines[i])]
        if "severity" not in heads:
            continue
        found = [] if found is None else found
        for row in lines[i + 2 :]:
            if not row.startswith("|") or SEPARATOR.match(row):
                break
            found.append((_finding(heads, _cells(row)), row))
    return found


def critique_table(md: str) -> list[dict[str, str]] | None:
    """The findings of a critic's table, read by its header row as the critique gate and the judge read them: for
    every row its `no`, `location`, `source` and `severity` (lower case, without markup), each from the column whose
    header begins with that word (`No.` or `#`, `Location in the work ...`), "" where the table has no such column;
    without a `No.` column the number is the first cell. The rows of every table that has a Severity column; None when
    no table has one."""
    rows = critique_rows(md)
    return None if rows is None else [finding for finding, _ in rows]


def input_names(run_dir: Path, stage_dir: Path) -> list[str]:
    """What the stage was given from earlier stages, as the session saw it under input/ (written by harness/access.py)."""
    index = access.unit_record(run_dir, stage_dir, "inputs")
    if not index.is_file():
        return []
    own = ("brief.md", access.ASSIGNMENT)  # what the stage was told, not what it was given to work on
    return [e["as"] for e in json.loads(index.read_text(encoding="utf-8")) if e["as"] not in own]


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([*GIT, "-C", str(root), *args], capture_output=True, text=True, check=False)


def branch_of(root: Path, res: dict) -> str | None:
    """The one local branch the result names in its summary. A stage that commits says where."""
    names = [b for b in git(root, "branch", "--format=%(refname:short)").stdout.split() if b]
    named = [b for b in names if b in res.get("summary", "")]
    return max(named, key=len) if named else None


def changed_paths(root: Path, base: str, head: str, only: str = "") -> list[str]:
    """Every path `head` adds, changes or deletes against `base`, as git stores it (`only`: git's --diff-filter, `A`
    for the added ones). Without `-z` git quotes a name with an unusual character
    (`".claude/skills/\\303\\251/SKILL.md"`), and a check of the name would miss the folder; without `--no-renames` a
    file moved out of a closed path is named by its new path only. A name that is no UTF-8 is read as the file system
    reads it (os.fsdecode), never refused by a decoder."""
    argv = [*GIT, "-C", str(root), "diff", "-z", "--name-only", "--no-renames", *([f"--diff-filter={only}"] if only else []),
            f"{base}..{head}"]  # fmt: skip
    out = subprocess.run(argv, capture_output=True, check=False).stdout
    return [os.fsdecode(f) for f in out.split(b"\0") if f]


def changed_files(root: Path, branch: str) -> list[str]:
    """Every path the branch adds, changes or deletes since it left HEAD (changed_paths)."""
    return changed_paths(root, git(root, "merge-base", "HEAD", branch).stdout.strip(), branch)


def do_not_touch(run_dir: Path) -> list[str]:
    """The paths of the brief's `Do not touch:` line, without quotes and trailing slashes."""
    brief = run_dir / "brief.md"
    if not brief.is_file():
        return []
    m = re.search(r"^\s*-\s*Do not touch:\s*(.+)$", brief.read_text(encoding="utf-8"), re.MULTILINE)
    if not m:
        return []
    items = re.findall(r"`([^`]+)`", m.group(1)) or [p.strip() for p in m.group(1).split(",")]
    return [p.strip().rstrip("/") for p in items if p.strip() and not p.strip().startswith("<")]


def hooks_open(run_dir: Path) -> bool:
    """The brief's `Hooks: open` line: this run changes the hook scripts under `.claude/hooks/` (ADR-0015)."""
    brief = run_dir / "brief.md"
    return brief.is_file() and bool(
        re.search(r"^\s*-\s*Hooks:\s*open\s*$", brief.read_text(encoding="utf-8"), re.MULTILINE)
    )


def closed_to(root: Path, policy: dict, run_dir: Path, role_type: str | None):
    """Whether a repository path is closed to the commits of a type, judged on what a commit changes, whatever command
    made it (docs/decisions/0025): a path it may not read, by its row or by the project's settings (access.unreadable:
    the sandbox shows a closed folder empty and a closed file as a device, and git reports what it cannot see as
    deleted or changed; a whole-tree `git add` or `git commit` would carry those changes, seen live), the flow's own
    configuration (a `.claude` folder or file at any depth and every `.mcp.json`: a session that enters a checkout
    reads its settings, skills, agents and commands from there, and finds skills in folders below it), or a path the
    brief's `Do not touch:` line closes. Only the hook scripts may change, when the brief says `- Hooks: open`
    (ADR-0015): every session runs the main checkout's hooks (`$CLAUDE_PROJECT_DIR`), so a changed script runs nowhere
    before the run is integrated. A type the policy does not know gets the strictest list. Used for a writer's branch
    (scope_check), a planner's trial (work.prepare) and a critic's attack tests (attack.taken_paths). Names are
    compared in lower case: a file system that ignores case reads `.CLAUDE/settings.json` as the settings."""
    d = policy["defaults"]
    known = role_type in policy["types"]
    row = access.type_row(policy, role_type) if known else {"repo_deny": [*d["repo_deny"], *d["blind_deny"]]}
    hidden = access.unreadable(row, root)
    hooks, closed = hooks_open(run_dir), do_not_touch(run_dir)

    def shut(f: str) -> bool:
        low = f.lower()
        parts = low.split("/")
        if parts[-1] == ".mcp.json" or any(fnmatch.fnmatchcase(low, pat.lower()) for pat in hidden):
            return True
        if ".claude" in parts and not (hooks and low.startswith(".claude/hooks/")):
            return True
        return any(low == p.lower() or low.startswith(p.lower() + "/") for p in closed)

    return shut


def scope_check(root: Path, run_dir: Path, res: dict, branch: str) -> dict:
    """The branch changes nothing its author could not read and nothing the flow or the brief closes (closed_to): the
    effect of a commit is judged, whatever command made it (docs/decisions/0025)."""
    shut = closed_to(root, access.load_policy(root), run_dir, res.get("role_type"))
    bad = [f for f in changed_files(root, branch) if shut(f)]
    return check("the branch stays out of hidden and closed paths", not bad, ", ".join(bad[:6]))


def secrets_check(root: Path, branch: str) -> dict:
    base = git(root, "merge-base", "HEAD", branch).stdout.strip()
    diff = git(root, "diff", f"{base}..{branch}").stdout
    hits = [
        line[:80]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++") and SECRETS.search(line)
    ]
    if hits:
        return check("no credential in the branch diff", False, "; ".join(hits[:3]))
    if shutil.which("gitleaks"):
        run = subprocess.run(
            ["gitleaks", "git", "--no-banner", "--log-opts", f"{base}..{branch}", str(root)],
            capture_output=True,
            text=True,
            check=False,
        )
        return check("no credential in the branch diff", run.returncode == 0, run.stdout[-300:])
    return check("no credential in the branch diff", True, "built-in patterns only; gitleaks is not installed")


def on_branch(root: Path, branch: str, fn):
    """Run fn(path) on a temporary detached worktree of the branch and remove it afterwards."""
    tmp = Path(tempfile.mkdtemp(prefix="harness-gate-"))
    try:
        added = git(root, "worktree", "add", "--detach", str(tmp / "tree"), branch)
        if added.returncode != 0:
            return None, added.stderr[-300:]
        return fn(tmp / "tree"), ""
    finally:
        git(root, "worktree", "remove", "--force", str(tmp / "tree"))
        shutil.rmtree(tmp, ignore_errors=True)


def tests_check(root: Path, branch: str) -> dict:
    """The suite on a checkout of the branch (suite_checks), without protected tests."""
    return suite_checks(root, branch, {})[0]


GIVEN_RAN = "the plan's and the critic's tests run and pass as given"
GIVEN_XML = ".harness-given.xml"  # the JUnit report of the protected run, in its checkout


def suite_checks(root: Path, branch: str, given: dict[str, bytes]) -> list[dict]:
    """The suite on a checkout of the branch, inside a sandbox and without this process's environment
    (gates/_sandbox.py): the branch's tests and conftest.py are code its writer committed. Where no sandbox starts the
    suite is not run, and the check fails with the reason. `given` are the protected tests (protected_tests): they go
    over the checkout, so the writer's copies of them do not count; and they run once more by name (given_check)."""
    name = f"`{' '.join(TEST_CMD)}` passes on the branch"

    def run(tree: Path):
        placed = overlay(tree, given)
        return placed or _sandbox_run(root, tree, TEST_CMD)

    out, err = on_branch(root, branch, run)
    first = _ended(out, err)
    done = [check(name, first[0], first[1])]
    return [*done, given_check(root, branch, given)] if given else done


def given_check(root: Path, branch: str, given: dict[str, bytes]) -> dict:
    """The protected test modules by name (test_modules: a given conftest.py, helper or data file goes over the
    checkout and has no test case of its own), in a checkout of their own whose conftest.py files are the base's, with
    the base's pytest configuration named by -c (a configuration file the branch adds below the root is not looked
    for) and the plugins of the base's dependency set named by -p, no other loaded (base_plugins): a conftest.py, an
    ini file or a plugin of the branch could skip, drop or report as passed a given test that fails. The JUnit report
    says, case by case, what ran (given_missing); the paths follow `--`. Code under test runs in pytest's own process
    and stays out of reach (ADR-0024)."""
    base = git(root, "merge-base", "HEAD", branch).stdout.strip()
    config = pytest_config(root, base)
    modules = test_modules(root, base, sorted(given))
    if not modules:
        return check(GIVEN_RAN, True, "no test module among the given files")
    plugins = [arg for module in base_plugins(root, base) for arg in ("-p", module)]

    def run(tree: Path):
        placed = overlay(tree, {**base_config(root, base, branch), **config}) or overlay(tree, given)
        if placed:
            return placed
        argv = ["env", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", *TEST_CMD, "-c", next(iter(config)), "--rootdir=.",
                "-p", "no:cacheprovider", *plugins, f"--junitxml={GIVEN_XML}", "--", *modules]  # fmt: skip
        ended = _sandbox_run(root, tree, argv)
        report = stage_file(tree, GIVEN_XML)
        size_ok = report is not None and report.stat().st_size < 50_000_000
        return ended, report.read_text(encoding="utf-8", errors="replace") if size_ok else ""

    out, err = on_branch(root, branch, run)
    if not isinstance(out, tuple):
        return check(GIVEN_RAN, False, _ended(out, err)[1])
    missing = given_missing(out[1], modules)
    passed, tail = _ended(out[0], err)
    return check(GIVEN_RAN, passed and not missing, ", ".join(missing[:5]) or tail)


INI_SECTIONS = {"pytest.ini": "pytest", ".pytest.ini": "pytest", "pyproject.toml": "tool.pytest.ini_options",
                "tox.ini": "pytest", "setup.cfg": "tool:pytest"}  # in the order pytest looks for them  # fmt: skip
OWN_INI = ".harness-pytest.ini"


def base_options(root: Path, base: str | None) -> list[tuple[str, object]] | None:
    """The pytest options of the first configuration file pytest would take at the base's root, None without one."""
    for name, section in INI_SECTIONS.items() if base else ():
        data = blob(root, base, name)
        options = _options(name, section, data.decode("utf-8", "replace")) if data is not None else None
        if options is not None:
            return options
    return None


def pytest_config(root: Path, base: str) -> dict[str, bytes]:
    """The base's pytest configuration at the root as one ini file of our own, {OWN_INI: content}: the options of the
    first file pytest would take there (a pyproject.toml's written in ini form), or an empty section when the base has
    none. The protected run names it with -c; the branch's own files stay as they are, its environment too."""
    options = base_options(root, base)
    if options is None:
        return {OWN_INI: b"[pytest]\n"}
    lines = [f"{k} =" + "".join(f"\n    {x}" for x in (v if isinstance(v, list) else [v])) for k, v in options]
    return {OWN_INI: ("[pytest]\n" + "\n".join(lines) + "\n").encode("utf-8")}


PYTHON_FILES = ("test_*.py", "*_test.py")  # pytest's own `python_files`


def test_modules(root: Path, base: str | None, files: list[str]) -> list[str]:
    """The files that are test modules: named as pytest names them by default or as the base's `python_files` does (a
    file named on pytest's command line is collected whatever `python_files` says, so a given `test_*.py` always
    runs); a conftest.py, a helper or a data file has no test case of its own. A pattern with a `/` is matched against
    the whole path, as pytest does."""
    named = dict(base_options(root, base) or []).get("python_files")
    globs = [*PYTHON_FILES, *(" ".join(named if isinstance(named, list) else [str(named)]).split() if named else [])]
    return [f for f in files if any(fnmatch.fnmatch(f if "/" in g else PurePosixPath(f).name, g) for g in globs)]


def base_plugins(root: Path, base: str) -> list[str]:
    """The pytest plugins of the base's dependency set, by module: an entry point of the group pytest11 where the
    harness runs, of a distribution the base's uv.lock holds. The protected run names them with -p and loads no other
    (a plugin the work installs could report a failing given test as passed)."""
    try:
        packages = tomllib.loads((blob(root, base, "uv.lock") or b"").decode("utf-8")).get("package", [])
        locked = {_dist(p.get("name", "")) for p in packages}
    except (tomllib.TOMLDecodeError, UnicodeDecodeError, AttributeError):
        locked = set()
    found = importlib.metadata.entry_points(group="pytest11")
    return sorted({e.value.split(":")[0].strip() for e in found if e.dist and _dist(e.dist.name) in locked})


def _dist(name: str) -> str:
    """A distribution's name as packaging compares it (PEP 503)."""
    return re.sub(r"[-_.]+", "-", str(name)).lower()


def _options(name: str, section: str, text: str) -> list[tuple[str, object]] | None:
    """The pytest options of one configuration file, None when it has no pytest section or cannot be read."""
    try:
        if name == "pyproject.toml":
            found = tomllib.loads(text).get("tool", {}).get("pytest", {}).get("ini_options")
            return (
                None if found is None else [(k, str(v).lower() if isinstance(v, bool) else v) for k, v in found.items()]
            )
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(text)
    except (tomllib.TOMLDecodeError, configparser.Error):
        return None
    return (
        [(k, v.strip().splitlines() or [""]) for k, v in parser[section].items()]
        if parser.has_section(section)
        else None
    )


def base_config(root: Path, base: str, branch: str) -> dict[str, bytes | None]:
    """Every conftest.py of either commit as the base has it (None: the branch added it, so it goes). Names are
    compared in lower case: a file system that ignores case reads `tests/Conftest.py` as a conftest.py."""
    names = set()
    for rev in (base, branch):
        argv = [*GIT, "-C", str(root), "ls-tree", "-r", "-z", "--name-only", rev]
        listed = subprocess.run(argv, capture_output=True, check=False)
        names |= {os.fsdecode(n) for n in listed.stdout.split(b"\0") if n}
    wanted = [n for n in names if PurePosixPath(n).name.lower() == "conftest.py"]
    return {n: blob(root, base, n) for n in sorted(wanted)}


def _sandbox_run(root: Path, tree: Path, argv: list[str]):
    """A command in the sandbox, or the exception that kept it from ending."""
    try:
        return _sandbox.run(root, tree, argv, TEST_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return exc


def _ended(out, err: str) -> tuple[bool, str]:
    """(passed, detail) of a command run on a checkout: a string is why it was not run."""
    if isinstance(out, str):
        return False, f"not run: {out}"
    if out is None or isinstance(out, Exception):
        return False, err or str(out)
    return out.returncode == 0, (out.stdout + out.stderr)[-300:]


def given_missing(report: str, files: list[str]) -> list[str]:
    """The protected test files that did not run and pass, read from the JUnit report test case by test case: a file
    counts when it has a test case and none of its cases failed, erred or was skipped (an xfail is a skip there). A
    case is a file's when its class name is the file's module path (`tests/test_a.py` -> `tests.test_a`)."""
    try:
        cases = list(ElementTree.fromstring(report).iter("testcase"))
    except ElementTree.ParseError:
        return list(files)
    seen: dict[str, list[bool]] = {}
    for case in cases:
        cls = case.get("classname", "")
        good = not any(child.tag in ("failure", "error", "skipped") for child in case)
        for f in files:
            mod = f.removesuffix(".py").replace("/", ".")
            if cls == mod or cls.startswith(mod + "."):
                seen.setdefault(f, []).append(good)
    return [f for f in files if not seen.get(f) or not all(seen[f])]


def overlay(tree: Path, files: dict[str, bytes | None]) -> str:
    """Write files over a checkout as given (None removes one); "" when done, else why one could not be placed. A
    path under a link, or out of the checkout, is never written: the gate runs outside the sandbox, and a link the
    writer committed would take the write out of the tree. A file the branch holds where a folder of the path should
    be is named as the reason: an exception here would stop the poll of every run."""
    top = tree.resolve()
    for rel, data in sorted(files.items()):
        parts = PurePosixPath(rel).parts
        linked = [parts[:i] for i in range(1, len(parts)) if tree.joinpath(*parts[:i]).is_symlink()]
        if linked:
            return f"{rel}: {'/'.join(linked[0])} is a link on the branch"
        target = tree.joinpath(*parts)
        try:
            if target.is_symlink() or (data is None and target.is_file()):
                target.unlink()
            if data is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.parent.resolve().is_relative_to(top) or target.is_dir():
                return f"{rel} leads out of the checkout or is a folder on the branch"
            target.write_bytes(data)
        except OSError as exc:  # a file of the branch where a folder of the path should be: a reason, never a crash
            return f"{rel}: {exc.strerror or exc}"
    return ""


def blob(root: Path, rev: str, path: str) -> bytes | None:
    """A file of a commit as git stores it; None when the commit has none at that path."""
    res = subprocess.run([*GIT, "-C", str(root), "show", f"{rev}:{path}"], capture_output=True, check=False)
    return res.stdout if res.returncode == 0 else None


def given_path(rel: str) -> bool:
    """A protected test's path: relative, inside the repository, no part read as an option, a test by TEST_PATH."""
    p = PurePosixPath(rel)
    plain = not p.is_absolute() and ".." not in p.parts and not any(part.startswith("-") for part in p.parts)
    return bool(rel) and plain and bool(TEST_PATH.search(rel))


def _trial_tests(root: Path, run_dir: Path, patch: bytes) -> tuple[dict[str, bytes], str]:
    """The test files a planner's trial adds, as the trial has them: trial.patch applied to the run's base."""
    base = base_commit(root, run_dir)
    if not base:
        return {}, "the run names no base commit to apply the trial to"
    from .. import work  # work imports this module

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "trial.patch").write_bytes(patch)
        try:
            commit = work.trial_commit(root, base, Path(tmp) / "trial.patch")
        except access.AccessError as exc:
            return {}, str(exc)
    return {
        rel: blob(root, commit, rel) or b"" for rel in changed_paths(root, base, commit, "A") if given_path(rel)
    }, ""


def protected_tests(root: Path, run_dir: Path, stage_dir: Path) -> tuple[dict[str, bytes], str]:
    """The tests a writer keeps as they were given, by repository path, and what kept one from being read: the test
    files a planner's trial adds (a trial's change to an existing test is a reference, planner.md) and every attack
    test of a critic (`output/tests/<repository path>`). Read from the launcher's index of the stage's inputs, so a
    file the writer put under input/ counts for nothing, and as the launcher copied it (as_copied), so neither does a
    copy the writer changed; a path out of the repository is not taken."""
    index = access.unit_record(run_dir, stage_dir, "inputs")
    types = {s["id"]: s["role_type"] for s in _manifest(run_dir).get("stages", [])}
    out: dict[str, bytes] = {}
    problem = ""
    for e in json.loads(index.read_text(encoding="utf-8")) if index.is_file() else []:
        parts = stage_parts(run_dir, e.get("source", ""))
        if not parts:
            continue
        sid, rest = parts[0], parts[1:]
        rel = "/".join(rest[2:])
        attack = types.get(sid) == "critic" and rest[:2] == ("output", "tests") and given_path(rel)
        if not attack and rest != ("output", "trial", "trial.patch"):
            continue
        data = as_copied(stage_dir, e)
        if data is None:
            problem = problem or f"input/{e['as']} is not as the launcher copied it"
        elif attack:
            out[rel] = data
        else:
            found, why = _trial_tests(root, run_dir, data)
            out.update(found)
            problem = problem or why
    return out, problem


def stage_parts(run_dir: Path, source: str) -> tuple[str, ...]:
    """The parts of an input's source under the run's own stages/ (its stage first), () for a source elsewhere: a
    folder of that name further down is part of the path in the stage, as a test under `tests/stages/`."""
    for home, path in (
        (run_dir / "stages", Path(source)),
        (Path(os.path.realpath(run_dir / "stages")), Path(os.path.realpath(source))),
    ):
        try:
            return path.relative_to(home).parts if source else ()
        except ValueError:
            continue
    return ()


def _manifest(run_dir: Path) -> dict:
    try:
        return json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def unproven(res: dict, stage: str, numbers: list[str]) -> list[str]:
    """The numbers among `numbers` whose finding has no evidence entry in result.json that ran a command (its exit
    code kept) and names the finding as `<stage>#<n>` in its claim: each proof stands beside its finding."""
    ran = [str(e.get("claim", "")) for e in res.get("evidence", []) if e.get("command") and "exit_code" in e]
    return [n for n in numbers if not any(re.search(rf"(?<![\w-]){re.escape(stage)}#{re.escape(n)}\b", c) for c in ran)]


MATERIAL_FILE = re.compile(r"(?m)^### (\S+?)(?::\d+-\d+)?$")  # a file of the material, as pack.material heads it


def material_files(stage_dir: Path) -> list[str]:
    """The files of a stage's material, from the pack written at launch: what its session had in its prompt and so
    read without opening anything. A file given in pieces is named once; the knowledge pack is not material. A pack.md
    that is a link is not read (stage_file): the names would be another file's."""
    pack = stage_file(stage_dir, "pack.md")
    _, _, material = (pack.read_text(encoding="utf-8") if pack else "").partition("\n# Material\n")
    named = MATERIAL_FILE.findall(material)
    for line in material.splitlines():  # the files that are not text, which the session opened itself
        if line.startswith("Not text, so not in this section"):
            named += re.findall(r"`([^`]+)`", line)
    return list(dict.fromkeys(named))


def unaccounted_material(stage_dir: Path) -> list[str]:
    """Files of the material that no output of the stage accounts for. A file is accounted for when it heads a
    section of a document under `output/`, or stands in its Coverage: a section headed `Coverage` or the file
    `output/coverage.md`, with what was taken from it and where it went, or why it holds nothing for the task.
    Having the material in the prompt is not using it: measured on one stage, a session that had every file there
    wrote half the facts of a subagent that opened them (ADR-0008)."""
    files = material_files(stage_dir)
    out = stage_dir / "output"
    heads: list[str] = []
    covered: list[str] = []
    for p in sorted(out.rglob("*.md")) if files and out.is_dir() else []:
        if stage_file(stage_dir, p.relative_to(stage_dir)) is None:
            continue
        body = p.read_text(encoding="utf-8", errors="replace")
        found = sections(body)
        heads += list(found)
        covered += [b for h, b in found.items() if h.startswith("coverage")] + (
            [body] if p.name == "coverage.md" else []
        )
    return [f for f in files if not any(f.lower() in h for h in heads) and not any(f in b for b in covered)]


# ---------------------------------------------------------------- the checks of specs/001-chat-depth, part 3


def project_command(run_dir: Path, kind: str) -> list[str] | None:
    """The project's command of a kind (`test`, `lint`, `types`), or None when the project names none. One source for
    the step rules; a run of parts (plan A) will name its own commands under `run_dir`."""
    if kind not in PROJECT_COMMANDS:
        raise ValueError(f"no command kind {kind!r}; the kinds are {', '.join(PROJECT_COMMANDS)}")
    return PROJECT_COMMANDS[kind]


def prompt_files(stage_dir: Path) -> list[str]:
    """What the session had in its prompt without opening it: the first message (prompt.md, with the brief and the
    assignment) and every file its pack.md heads, the knowledge pack and the material alike."""
    pack = stage_file(stage_dir, "pack.md")  # a link is not read: its headings would be another file's
    named = MATERIAL_FILE.findall(pack.read_text(encoding="utf-8")) if pack else []
    return list(dict.fromkeys(["prompt.md", "input/brief.md", f"input/{access.ASSIGNMENT}", *named]))


def locators(text: str) -> list[tuple[str, int, int]]:
    """(path, first, last) of every `path:line` and `path:start-end` outside a quotation, in inline code or in plain
    text (a JSON string carries no backticks), when it looks like a path: a `/` in it or a text file's extension. A URL
    (a word with `://`), `pypi.org:443` or a time is not one."""
    out = []
    for line in text.splitlines():
        plain = QUOTED.sub(" ", line)
        for m in PATH_LINE.finditer(plain):
            before = plain[: m.start()]
            path, head = m.group(1), before.rsplit(None, 1)[-1] if before[-1:].strip() else ""
            if "://" in head + m.group(0) or (
                "/" not in path and Path(path).suffix.lower().lstrip(".") not in TEXT_EXT
            ):
                continue
            out.append((path, int(m.group(2)), int(m.group(3) or m.group(2))))
    return out


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def stage_texts(stage_dir: Path) -> list[tuple[str, str]]:
    """(name, text) of what a stage delivers in words: every .md and .txt under output/, report.md beside result.json,
    and every string of result.json."""
    out = stage_dir / "output"
    files = [p for p in sorted(out.rglob("*")) if p.suffix in (".md", ".txt") and p.is_file()] if out.is_dir() else []
    files += [stage_dir / "report.md"] if (stage_dir / "report.md").is_file() else []
    files = [p for p in files if stage_file(stage_dir, p.relative_to(stage_dir))]  # no link out of the stage
    texts = [(p.relative_to(stage_dir).as_posix(), p.read_text(encoding="utf-8", errors="replace")) for p in files]
    return texts + [("result.json", s) for s in _strings(result(stage_dir))]


def base_commit(repo: Path, run_dir: Path) -> str | None:
    """The commit a run started from: `base_commit` of its manifest, or for a run made before the manifest had one,
    the last commit of the checkout's history before the run was created."""
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if manifest.get("base_commit"):
        return manifest["base_commit"]
    found = git(repo, "rev-list", "-1", f"--before={manifest.get('created_at', '')}", "HEAD").stdout.strip()
    return found or None


def unit_branch(repo: Path, run_dir: Path, stage_dir: Path) -> str | None:
    """The branch of the unit's own checkout, `worktree-<run>-<stage>[-NN]`, when it exists in the repository."""
    from .. import launch  # launch imports this module

    parts = stage_dir.relative_to(run_dir / "stages").parts
    name = launch.worktree_name(run_dir.name, parts[0], int(parts[1]) if len(parts) > 1 else None)
    ok = git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/worktree-{name}").returncode == 0
    return f"worktree-{name}" if ok else None


class RepoFiles:
    """The repository files a location may name, as a stage saw them: in its checkout while that exists, else at its
    branch, else at the run's base commit (not at HEAD, which moves during a run). An exact path wins; otherwise
    every file the path is the tail of (`src/a.py`, written from a package directory) or that is the tail of the path
    (an absolute path) is a candidate. A path the stage's type may not read (closed_paths) is no file of it, and a
    path that leaves the checkout or the repository is not looked up on disk."""

    def __init__(self, repo: Path, run_dir: Path, stage_dir: Path) -> None:
        from .. import launch

        parts = stage_dir.relative_to(run_dir / "stages").parts
        name = launch.worktree_name(run_dir.name, parts[0], int(parts[1]) if len(parts) > 1 else None)
        self.repo, self.checkout = repo, repo / ".claude" / "worktrees" / name
        self.rev = unit_branch(repo, run_dir, stage_dir) or base_commit(repo, run_dir)
        self.closed = closed_paths(repo, run_dir, stage_dir)
        listed = git(repo, "ls-tree", "-r", "--name-only", self.rev).stdout.splitlines() if self.rev else []
        self.files = {f for f in listed if not is_closed(f, self.closed)}
        self.cache: dict[str, list[list[str]]] = {}

    def candidates(self, path: str) -> list[list[str]]:
        """The lines of every file the path may name; empty when it names none."""
        if path not in self.cache:
            self.cache[path] = self._candidates(path)
        return self.cache[path]

    def lines(self, path: str) -> list[str] | None:
        """The lines of the file the path names, its first candidate; None when it names none."""
        found = self.candidates(path)
        return found[0] if found else None

    def _candidates(self, path: str) -> list[list[str]]:
        rel = path.split("/.claude/worktrees/", 1)[1].split("/", 1)[-1] if "/.claude/worktrees/" in path else path
        if is_closed(rel, self.closed):
            return []
        for base in (self.checkout, *([] if self.rev else [self.repo])):
            at = None if rel.startswith("/") else inside(base, rel)
            lines = file_lines(base / rel) if at is not None and not is_closed(at, self.closed) else None
            if lines is not None:
                return [lines]
        exact = [rel] if rel in self.files else []
        tails = exact or sorted(f for f in self.files if f.endswith("/" + rel) or rel.endswith("/" + f))
        shown = [git(self.repo, "show", f"{self.rev}:{f}") for f in tails]
        return [s.stdout.splitlines() for s in shown if s.returncode == 0]


def _local(run_dir: Path, stage_dir: Path, path: str) -> list[str] | None:
    """The lines of the stage's own file that a location names: a path from the stage directory, its input/ or output/,
    or an absolute path into this stage's directory, also one written before the run directory moved (the run id in
    the path finds it). None for every other path, for a link and for a path that leaves its base: the gate runs
    outside the sandbox and opens nothing outside the stage, so another stage's file, the run's own files and a file
    outside the run read as no file (docs/decisions/0020, 0025)."""
    if path.startswith("/"):
        tail = path.split(f"/{run_dir.name}/", 1)[1] if f"/{run_dir.name}/" in path else ""
        own = stage_dir.relative_to(run_dir).as_posix() + "/"
        pairs = [(stage_dir, tail[len(own) :])] if tail.startswith(own) else []
    else:
        pairs = [(b, path) for b in (stage_dir, stage_dir / "input", stage_dir / "output")]
    for base, rel in pairs:
        p = stage_file(base, rel)
        lines = file_lines(p) if p else None
        if lines is not None:
            return lines
    return None


def locator_problems(repo: Path, run_dir: Path, stage_dir: Path) -> list[str]:
    """The `path:line` of the stage's texts that name no existing file or no existing line. A path is looked up in the
    run (_local), then in the repository (RepoFiles); a path the gate cannot look up names no file."""
    files = RepoFiles(repo, run_dir, stage_dir)
    bad: list[str] = []
    for name, text in stage_texts(stage_dir):
        for path, first, last in locators(text):
            found = _local(run_dir, stage_dir, path)
            texts = [found] if found is not None else files.candidates(path)
            where = f"`{path}:{first}{'-' + str(last) if last != first else ''}` in {name}"
            if not texts:
                bad.append(f"{where}: no such file")
            elif not any(1 <= first <= last <= len(lines) for lines in texts):
                bad.append(f"{where}: the file has {max(len(lines) for lines in texts)} lines")
    return bad


def locator_check(repo: Path, run_dir: Path, stage_dir: Path) -> dict:
    """Part 3 of specs/001-chat-depth, every type: a location names a file that exists and a line it has."""
    bad = locator_problems(repo, run_dir, stage_dir)
    return check("every `path:line` names an existing file and line", not bad, "; ".join(bad[:3]))


ENTRY = re.compile(r"(?m)^(?=(?:#{1,6}\s*)?\d+[.)]\s)")  # a numbered entry of a verifier's report.md starts a line
ENTRY_NUMBER = re.compile(r"(?:#{1,6}\s*)?(\d+)[.)]\s")
ENTRY_RESULT = re.compile(r"(?i)\b(confirmed|refuted|could not check)\b")
STATED_RESULT = re.compile(r"(?i)\bresult\b\W*(confirmed|refuted|could not check)")


def report_entries(report: str) -> list[tuple[int, str | None, str]]:
    """(number, result, text) of every numbered entry of a verifier's report.md, in order: the result is the word
    after `Result`, else the last result word of the entry, None without one. The one reading of the report: its gate
    (gates/verify.py), the judge's (gates/judge.py) and the loop (harness/rounds.py) take it from here."""
    out: list[tuple[int, str | None, str]] = []
    for block in ENTRY.split(report):
        m = ENTRY_NUMBER.match(block)
        if m:
            stated, words = STATED_RESULT.search(block), ENTRY_RESULT.findall(block)
            found = stated.group(1) if stated else (words[-1] if words else None)
            out.append((int(m.group(1)), found.lower() if found else None, block.strip()))
    return out


def _norm(command: str) -> str:
    return " ".join(command.split())


def _copied(stage_dir: Path) -> dict[str, dict] | None:
    """The inputs the launcher copied for a unit, by their name under input/, from `<run>/_access/<unit>.inputs.json`
    (access.materialize_inputs), which no role session can read or write; None for a directory that is no unit of a
    run, or a unit without that index."""
    stages = next((p for p in stage_dir.parents if p.name == "stages"), None)
    if stages is None:
        return None
    index = access.unit_record(stages.parent, stage_dir, "inputs")
    try:
        return {e["as"]: e for e in json.loads(index.read_text(encoding="utf-8"))}
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None


def as_copied(stage_dir: Path, entry: dict) -> bytes | None:
    """An input of a unit as the launcher copied it (access.materialize_inputs), by its entry in the unit's index: the
    bytes of its copy under input/ while they have the sha256 the index records, else those of its source; None when
    neither has it. A gate runs outside the sandbox: a copy the session changed is not believed, and a link or
    anything but a plain file is never read."""
    for p in (stage_file(stage_dir / "input", str(entry.get("as", ""))), Path(str(entry.get("source", "")))):
        try:
            if p is None or p.is_symlink() or not p.is_file():
                continue
            data = p.read_bytes()
        except OSError:
            continue
        if hashlib.sha256(data).hexdigest() == entry.get("sha256"):
            return data
    return None


def harness_runs(stage_dir: Path) -> list[dict]:
    """The commands the harness ran on the work outside any session, as the stage received them: every row of an
    input `checks.json` (gates/write.py record_checks). A verifier cites such a row for what its sandbox cannot run.
    A copy counts only as the launcher made it (as_copied); a file under input/ the unit's index does not name is no
    input. Without an index (a stage directory the launcher did not build) the copy is read as it is; a link never
    is."""
    inp = stage_dir / "input"
    copied = _copied(stage_dir)
    rows: list[dict] = []
    for path in sorted(inp.rglob("checks.json")) if inp.is_dir() else []:
        entry = (copied or {}).get(path.relative_to(inp).as_posix())
        if copied is not None and entry is None:
            continue  # not an input the launcher copied
        plain = stage_file(inp, path.relative_to(inp)) if entry is None else None
        data = as_copied(stage_dir, entry) if entry is not None else plain.read_bytes() if plain else None
        try:
            rows += json.loads(data.decode("utf-8")).get("checks", []) if data is not None else []
        except (ValueError, AttributeError):
            continue
    return [r for r in rows if isinstance(r, dict) and r.get("command")]


def evidence_check(stage_dir: Path, events: list[dict]) -> dict:
    """Part 3, every type: an evidence entry that names a command was run in the session, a Bash call whose text holds
    it (whitespace normalised), and ended with the entry's exit code when it gives one. A refused call did not run.
    A command the harness ran outside the session and the stage received in a `checks.json` counts as well, with the
    exit code that file records (the verifier's method cites it for what its sandbox cannot run to the end)."""
    calls = [e for e in events if e["tool"] == "Bash" and not e["denied"]]
    outside = harness_runs(stage_dir)
    bad: list[str] = []
    for entry in result(stage_dir).get("evidence", []):
        if not entry.get("command"):
            continue
        cmd = _norm(entry["command"])
        ran = [c for c in calls if cmd in _norm(c["command"])]
        cited = [r for r in outside if cmd in _norm(r["command"])]
        codes = sorted({c["exit_code"] for c in ran} | {r.get("exit_code") for r in cited}, key=str)
        if not ran and not cited:
            bad.append(f"`{cmd[:60]}`: not run in the session")
        elif "exit_code" in entry and entry["exit_code"] not in codes:
            shown = ", ".join("unknown" if c is None else str(c) for c in codes)
            bad.append(f"`{cmd[:60]}`: ended with {shown}, the entry says {entry['exit_code']}")
    return check("every evidence command was run as the entry says", not bad, "; ".join(bad[:3]))
