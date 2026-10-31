"""A finished run's leftovers, removed only after its record is checked as saved (spec 5.9.4): the run's worktrees and
branches, its `scratch/`, the job folders of its sessions and the `--also` paths. Lists every deletion with what
it loses by default; `--apply` removes them on the owner's yes for the listed digest (`--yes <digest>`) until three runs
were applied with one, then by the standing rule; the owner reads `collected.md` in the run folder afterwards.

Usage: python3 -I collect_run.py RUN_DIR --repo DIR --plan PATH --kept PATH [--kept PATH ...] [--main BRANCH]
       [--final SHA ...] [--worktree DIR ...] [--branch NAME ...] [--also PATH ...] [--agents FILE] [--jobs DIR]
       [--history FILE] [--apply] [--yes DIGEST]
The save check refuses the whole list when a record's line 1 is not `STATUS: done` or check_formats.py fails, a lesson
of the run has no `(skill: <sha>|none)` mark or its commit is not in the main branch, a kept item is missing or lies
inside a deletion, an `--also` path lies in the run folder outside `scratch/`, a build log's done commit or a `--final`
is not in the main branch, a Deferred item of the plan is not in the tracker, or a deletion would lose work that is not
saved. Exit 0 listed or removed; 1 a removal failed or a kept item is missing afterwards; 2 a usage error, before
anything is listed; 3 refused.
"""

import argparse
import dataclasses
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys

PROG = "collect_run.py"
HERE = pathlib.Path(__file__).resolve().parent  # the folder of check_formats.py
FINISHED = {"done", "failed", "stopped"}
TRACKER = "docs/exec-plans/tech-debt-tracker.md"
FINAL = re.compile(r"STATUS: done(?:\s|$)")
DONE = re.compile(r"^(?:- )?Task (\d+): done — ([0-9a-f]{7,40})\b", re.MULTILINE)  # check_formats.py:43
MERGED = re.compile(r"Merged: \S+ at [0-9a-f]{7,40}\b")
MARK = re.compile(r"\(skill: (none|[0-9a-f]{7,40})\)")
TD = re.compile(r"\bTD-\d{3}\b")
TD_ROW = re.compile(r"^\| (TD-\d{3}) \|")
JOB_ID = re.compile(r"[0-9a-f]{8}")  # fullmatch on a row's id
DEFERRED = re.compile(r"#{2,3} Deferred")
LESSONS = re.compile(r"## Lessons from this run")
HEADING = re.compile(r"#{1,3} ")
ITEM = re.compile(r"(?:- |\d+\. )")
FENCE = re.compile(r"\s*(`{3,})(.*)")  # a fence line: its backticks, then the info string
KINDS = ("worktree", "branch", "job", "path")  # the order of the total: and done: counts
PLURAL = {"worktree": "worktrees", "branch": "branches", "job": "job folders", "path": "paths"}


class Usage(Exception):
    """A reason to exit 2 before anything is listed."""


@dataclasses.dataclass
class Deletion:
    """One thing the run owns that the collector removes."""

    kind: str  # "worktree", "branch", "path", "job"
    target: str  # the path as printed, or the branch name
    ident: str  # its digest line
    line: str  # its `would ...` line
    sha: str = ""  # a branch's 40-hex sha, for its `deleted branch` line


def git(repo: str | pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    """`git -C <repo> <args>` with text output; the caller reads the exit code."""
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)


def ancestor(repo: str, sha: str, main: str) -> int:
    """The exit code of `git merge-base --is-ancestor <sha> <main>`: 0 yes, 1 no, any other an error."""
    return git(repo, "merge-base", "--is-ancestor", sha, main).returncode


def real(path: str | pathlib.Path) -> str:
    """The path with every symlink resolved."""
    return os.path.realpath(path)


def worktrees(repo: str) -> list[dict]:
    """The worktrees of `repo` in git's order, the main one first: path, HEAD and branch (None when detached)."""
    found: list[dict] = []
    for line in git(repo, "worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            found.append({"path": line.removeprefix("worktree "), "head": "", "branch": None})
        elif found and line.startswith("HEAD "):
            found[-1]["head"] = line.removeprefix("HEAD ")
        elif found and line.startswith("branch refs/heads/"):
            found[-1]["branch"] = line.removeprefix("branch refs/heads/")
    return found


def items(text: str, heading: re.Pattern[str]) -> list[str]:
    """The items under the headings `heading` matches, outside fenced code: each one's lines, its marker cut off."""
    found: list[list[str]] = []
    inside, fence, current = False, "", None
    for line in text.splitlines():
        m = FENCE.match(line)
        if fence:
            if m and len(m.group(1)) >= len(fence) and not m.group(2).strip():
                fence = ""
            continue
        if m:
            fence, current = m.group(1), None
        elif HEADING.match(line):
            inside, current = bool(heading.match(line)), None
        elif inside and (marker := ITEM.match(line)):
            current = [line[marker.end() :]]
            found.append(current)
        elif current is not None and line.strip() and line[0].isspace():
            current.append(line.strip())
        else:
            current = None
    return ["\n".join(lines) for lines in found]


def key(item: str) -> str:
    """A Deferred item's key: its first line up to the first ": ", or the whole first line."""
    first = item.splitlines()[0] if item else ""
    return first.split(": ", 1)[0].strip()


def norm(text: str) -> str:
    """The text without backticks, its whitespace collapsed, in lower case."""
    return " ".join(text.replace("`", "").split()).lower()


def count(path: pathlib.Path) -> tuple[int, int]:
    """The regular files at or under `path` and their bytes, read with os.lstat, so no symlink is followed."""
    st = os.lstat(path)
    if not stat.S_ISDIR(st.st_mode):
        return (1, st.st_size) if stat.S_ISREG(st.st_mode) else (0, 0)
    files, total = 0, 0
    for root, _, names in os.walk(path):
        for name in names:
            st = os.lstat(os.path.join(root, name))
            if stat.S_ISREG(st.st_mode):
                files, total = files + 1, total + st.st_size
    return files, total


def size(path: pathlib.Path) -> str:
    """`<n> files, <MB> MB`, the size as clean_jobs_tmp.py prints it."""
    files, total = count(path)
    return f"{files} files, {total / 1_000_000:.1f} MB"


def tally(kinds: list[str]) -> str:
    """`<w> worktrees, <b> branches, <j> job folders, <p> paths`: the kinds counted in KINDS order."""
    return ", ".join(f"{kinds.count(k)} {PLURAL[k]}" for k in KINDS)


def holds(path: str | pathlib.Path, protected: list[pathlib.Path]) -> bool:
    """Whether `path`, by real path, is a protected path or lies above one."""
    mine = pathlib.Path(real(path))
    return any(p.is_relative_to(mine) for p in protected)


def listing() -> list[dict]:
    """The rows of `claude agents --json --all`; Usage when it fails or prints no JSON list."""
    try:
        out = subprocess.run(
            ["claude", "agents", "--json", "--all"], capture_output=True, text=True, timeout=300, check=False
        )
        data = json.loads(out.stdout) if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        data = None
    if not isinstance(data, list):
        raise Usage("claude agents --json --all failed or printed no JSON list")
    return [row for row in data if isinstance(row, dict)]


def agent_cwds(args: argparse.Namespace, agents: dict) -> dict[str, str]:
    """Each agent's real cwd; a relative cwd is taken from the run folder."""
    return {
        name: real(os.path.join(args.run_dir, spec["cwd"]))
        for name, spec in agents.items()
        if isinstance(spec, dict) and isinstance(spec.get("cwd"), str)
    }


def picked_worktrees(
    args: argparse.Namespace, agents: dict, trees: list[dict], protected: list[pathlib.Path]
) -> tuple[list[tuple[str, dict]], list[str]]:
    """The run worktrees (an agent's cwd or a --worktree) in real-path order, and the --worktree refusals."""
    linked = {real(t["path"]): t for t in trees[1:]}  # the first block is the main worktree: never a deletion
    picked = {cwd: linked[cwd] for cwd in agent_cwds(args, agents).values() if cwd in linked}
    refused = []
    for given in args.worktree:
        if holds(given, protected):
            refused.append(f"refused: {given} holds the run folder or the main worktree")
        elif real(given) not in linked:
            refused.append(f"refused: {given} is not a worktree of {args.repo}")
        else:
            picked[real(given)] = linked[real(given)]
    return [(tree["path"], tree) for _, tree in sorted(picked.items())], refused


def void(st: os.stat_result) -> bool:
    """A folder or a 0-byte regular file: what an empty untracked path is made of."""
    return stat.S_ISDIR(st.st_mode) or (stat.S_ISREG(st.st_mode) and st.st_size == 0)


def fail(error: OSError) -> None:
    """os.walk's onerror: a folder that cannot be read stops the walk."""
    raise error


def holds_nothing(path: pathlib.Path) -> bool:
    """An empty untracked path (C505): a 0-byte regular file, or a folder of folders and 0-byte regular files only."""
    try:
        st = os.lstat(path)
        if not void(st):
            return False
        if not stat.S_ISDIR(st.st_mode):
            return True  # a 0-byte regular file: os.walk would call onerror on it
        for root, dirs, files in os.walk(path, onerror=fail):
            if not all(void(os.lstat(os.path.join(root, name))) for name in dirs + files):
                return False
    except OSError:
        return False
    return True


def clear_empty(tree: str) -> None:
    """Removes a worktree's empty untracked paths, found again, which `git worktree remove` would refuse (C505)."""
    for line in git(tree, "status", "--porcelain", "--ignored").stdout.splitlines():
        path = pathlib.Path(tree, line[3:])
        if line.startswith("?? ") and holds_nothing(path):
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()


def worktree_deletion(args: argparse.Namespace, p: str, t: dict) -> tuple[Deletion, list[str]]:
    """One run worktree's deletion with what it loses, and the refusals of its unsaved work."""
    status = [line for line in git(p, "status", "--porcelain", "--ignored").stdout.splitlines() if line]
    ignored = [line[3:] for line in status if line.startswith("!! ")]
    empty = sum(1 for line in status if line.startswith("?? ") and holds_nothing(pathlib.Path(p, line[3:])))
    dirty = len(status) - len(ignored) - empty
    ahead = 0
    if t["branch"] is None:
        ahead = int(git(args.repo, "rev-list", "--count", f"{args.main}..{t['head']}").stdout.strip() or 0)
    parts = [
        f"{dirty} uncommitted paths" if dirty else "",
        f"{empty} empty untracked paths" if empty else "",
        f"{ahead} commits not in {args.main}" if ahead else "",
        "ignored " + ", ".join(ignored) if ignored else "",
    ]
    where = f"branch {t['branch']}" if t["branch"] else "detached"
    loses = "; ".join(part for part in parts if part) or "nothing"
    line = f"would remove worktree {p} ({where}, HEAD {t['head'][:7]}): loses {loses}"
    refused = [f"refused: worktree {p} has {dirty} uncommitted paths"] if dirty else []
    if t["branch"] is None and ancestor(args.repo, t["head"], args.main) != 0:
        refused.append(f"refused: worktree {p} HEAD {t['head'][:7]} is not in {args.main}")
    return Deletion("worktree", p, f"worktree {real(p)} {t['head']}", line), refused


def worktree_deletions(
    args: argparse.Namespace, agents: dict, trees: list[dict], protected: list[pathlib.Path]
) -> tuple[list[Deletion], list[str], list[dict]]:
    """The run worktrees' deletions, the refusals of their targets and unsaved work, and their trees."""
    picked, refused = picked_worktrees(args, agents, trees, protected)
    found: list[Deletion] = []
    run_trees: list[dict] = []
    for path, tree in picked:
        if holds(path, protected):
            refused.append(f"refused: {path} holds the run folder or the main worktree")
            continue
        deletion, why = worktree_deletion(args, path, tree)
        found.append(deletion)
        refused += why
        run_trees.append(tree)
    return found, refused, run_trees


def branch_names(args: argparse.Namespace, run_trees: list[dict], trees: list[dict]) -> tuple[list[str], list[str]]:
    """The branches to delete (the run worktrees', then each --branch) and the --branch refusals."""
    names = [t["branch"] for t in run_trees if t["branch"]]
    run_paths = {real(t["path"]) for t in run_trees}
    refused = []
    for name in args.branch:
        holder = next((t["path"] for t in trees if t["branch"] == name and real(t["path"]) not in run_paths), None)
        if name == args.main:
            refused.append(f"refused: branch {name} is the main branch")
        elif git(args.repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}").returncode != 0:
            refused.append(f"refused: no branch {name}")
        elif holder:
            refused.append(f"refused: branch {name} is checked out in {holder}")
        elif name not in names:
            names.append(name)
    return names, refused


def branch_deletions(
    args: argparse.Namespace, run_trees: list[dict], trees: list[dict]
) -> tuple[list[Deletion], list[str]]:
    """The branches' deletions with the commits each would lose, and their refusals."""
    names, refused = branch_names(args, run_trees, trees)
    found: list[Deletion] = []
    for name in names:
        if name == args.main:
            refused.append(f"refused: branch {name} is the main branch")
            continue
        sha = git(args.repo, "rev-parse", f"refs/heads/{name}").stdout.strip()
        ahead = int(git(args.repo, "rev-list", "--count", f"{args.main}..refs/heads/{name}").stdout.strip() or 0)
        loses = f"loses {ahead} commits not in {args.main}" if ahead else f"loses nothing (in {args.main})"
        found.append(
            Deletion("branch", name, f"branch {name} {sha}", f"would delete branch {name} at {sha[:7]}: {loses}", sha)
        )
        if ahead:
            refused.append(f"refused: branch {name} at {sha[:7]} has {ahead} commits not in {args.main}")
    return found, refused


def scratch_deletion(args: argparse.Namespace) -> tuple[list[Deletion], list[str]]:
    """RUN_DIR/scratch when it exists, or its `skipped` line when it is a symlink."""
    path = pathlib.Path(args.run_dir) / "scratch"
    if path.is_symlink():
        return [], [f"skipped {path}: a symlink"]
    if not path.exists():
        return [], []
    return [Deletion("path", str(path), f"path {real(path)}", f"would remove {path}: loses {size(path)}")], []


def run_rows(args: argparse.Namespace, agents: dict, rows: list[dict]) -> list[dict]:
    """The listing's rows of the run's sessions (an 8-hex id, an agent's name and that agent's cwd), in id order."""
    cwds = agent_cwds(args, agents)
    mine = [
        row
        for row in rows
        if isinstance(row.get("id"), str)
        and JOB_ID.fullmatch(row["id"])
        and isinstance(row.get("name"), str)
        and isinstance(row.get("cwd"), str)
        and cwds.get(row["name"]) == real(row["cwd"])
    ]
    return sorted(mine, key=lambda row: row["id"])


def job_deletions(
    args: argparse.Namespace, agents: dict, rows: list[dict]
) -> tuple[list[Deletion], list[str], list[str]]:
    """The job folders of the run's finished sessions, the refusals for those still running, and the skipped lines."""
    found: list[Deletion] = []
    refused, notes = [], []
    for row in run_rows(args, agents, rows):
        if "pid" in row or row.get("state") not in FINISHED:
            refused.append(f"refused: session {row['name']} ({row['id']}) is still running")
            continue
        folder = args.jobs / row["id"]
        if folder.is_symlink():
            notes.append(f"skipped {folder}: a symlink")
        elif folder.exists():
            line = f"would remove job {folder} ({row['name']}, {row['state']}): loses {size(folder)}"
            found.append(Deletion("job", str(folder), f"job {row['id']}", line))
    return found, refused, notes


def also_deletions(args: argparse.Namespace, protected: list[pathlib.Path]) -> tuple[list[Deletion], list[str]]:
    """Each --also path's deletion, or its refusal when it is missing, holds a protected path, or lies in the run
    folder outside its scratch/ (a record file the run keeps)."""
    found: list[Deletion] = []
    refused = []
    run = protected[0]
    for given in args.also:
        mine = pathlib.Path(real(given))
        if not os.path.lexists(given):
            refused.append(f"refused: {given} is missing")
        elif holds(given, protected):
            refused.append(f"refused: {given} holds the run folder or the main worktree")
        elif mine.is_relative_to(run) and not mine.is_relative_to(run / "scratch"):
            refused.append(f"refused: {given} lies in the run folder outside scratch/")
        else:
            line = f"would remove {given}: loses {size(pathlib.Path(given))}"
            found.append(Deletion("path", given, f"path {real(given)}", line))
    return found, refused


def deletions(
    args: argparse.Namespace, agents: dict, rows: list[dict], trees: list[dict]
) -> tuple[list[Deletion], list[str], list[str]]:
    """Every deletion of the run in order, the refusals of the targets and the unsaved work, and the skipped lines."""
    protected = [pathlib.Path(real(args.run_dir)), pathlib.Path(real(trees[0]["path"]))]
    wts, refused, run_trees = worktree_deletions(args, agents, trees, protected)
    branches, why = branch_deletions(args, run_trees, trees)
    scratch, notes = scratch_deletion(args)
    jobs, running, skipped = job_deletions(args, agents, rows)
    also, missing = also_deletions(args, protected)
    return wts + branches + scratch + jobs + also, refused + why + running + missing, notes + skipped


def first_line(path: pathlib.Path) -> str:
    """The file's first line without its line end; empty when it cannot be read."""
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            return f.readline().rstrip("\r\n")
    except OSError:
        return ""


def records(run: pathlib.Path) -> list[pathlib.Path]:
    """The record files: each *.md directly in the run folder whose line 1 starts with `STATUS: `, in name order."""
    return [p for p in sorted(run.glob("*.md")) if p.is_file() and first_line(p).startswith("STATUS: ")]


def check_records(args: argparse.Namespace) -> list[str]:
    """Each record's line 1 is final, and check_formats.py passes on the run folder."""
    refused = []
    for path in records(pathlib.Path(args.run_dir)):
        line = first_line(path)
        if not FINAL.match(line):
            refused.append(f'refused: {path.name} line 1 is "{line}", not "STATUS: done"')
    out = subprocess.run(
        [sys.executable, "-I", str(HERE / "check_formats.py"), args.run_dir, "--repo", args.repo],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        text = (out.stdout if out.stdout.strip() else out.stderr).strip()
        refused.append(f"refused: check_formats.py exit {out.returncode}: {text.splitlines()[0] if text else ''}")
    return refused


def check_lessons(args: argparse.Namespace) -> list[str]:
    """Each lesson of the run, a merge record aside, carries a skill mark whose commit is in the main branch."""
    path = pathlib.Path(args.run_dir) / "lessons.md"
    if not path.is_file():
        return [f"refused: {path} is missing"]
    text = path.read_text(encoding="utf-8", errors="replace")
    if not any(LESSONS.match(line) for line in text.splitlines()):
        return ['refused: lessons.md has no "## Lessons from this run" section']
    refused = []
    for item in items(text, LESSONS):
        words = " ".join(item.split())
        mark = MARK.search(words)
        if MERGED.search(words):
            continue
        if not mark:
            refused.append(f"refused: lesson without a (skill: <sha>|none) mark: {words[:60]}")
        elif mark.group(1) != "none" and ancestor(args.repo, mark.group(1), args.main) != 0:
            refused.append(f"refused: lesson mark {mark.group(1)} is not in {args.main}")
    return refused


def check_kept(args: argparse.Namespace, found: list[Deletion]) -> list[str]:
    """Each --kept exists and lies, by real path, inside no worktree, path or job deletion."""
    spots = [d.target for d in found if d.kind != "branch"]
    refused = []
    for given in args.kept:
        if not os.path.exists(given):
            refused.append(f"refused: kept {given} is missing")
            continue
        inside = next((spot for spot in spots if pathlib.Path(real(given)).is_relative_to(real(spot))), None)
        if inside:
            refused.append(f"refused: kept {given} lies inside {inside}")
    return refused


def done_lines(run: pathlib.Path) -> list[tuple[str, str]]:
    """The build logs' done lines as (sha, "<log name> Task <N>"): build-log.md, build-log-kb.md, then the rest."""
    first = [run / "build-log.md", run / "build-log-kb.md"]
    logs = [p for p in first if p.is_file()] + [p for p in sorted(run.glob("build-log*.md")) if p not in first]
    found = []
    for path in logs:
        text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
        found += [(m.group(2), f"{path.name} Task {m.group(1)}") for m in DONE.finditer(text)]
    return found


def check_commits(args: argparse.Namespace) -> list[str]:
    """Every done commit of the build logs and each --final is an ancestor of the main branch."""
    named = done_lines(pathlib.Path(args.run_dir)) + [(sha, "--final") for sha in args.final]
    if not named:
        return ['refused: no final commit named (no "Task N: done — <sha>" line in a build log, no --final)']
    refused = []
    for sha, source in named:
        code = ancestor(args.repo, sha, args.main)
        if code == 1:
            refused.append(f"refused: {sha[:7]} ({source}) is not an ancestor of {args.main}")
        elif code != 0:
            refused.append(f"refused: {sha} ({source}) is not a commit of {args.repo}")
    return refused


def check_deferred(args: argparse.Namespace) -> list[str]:
    """K1: each Deferred item of the plan's files on the main branch names a tracker row or is quoted by one."""
    plan = args.plan.rstrip("/")
    names = git(args.repo, "ls-tree", "--name-only", args.main, f"{plan}/").stdout.splitlines()
    files = sorted(name for name in names if name.endswith(".md"))
    refused = [] if files else [f"refused: no {plan}/*.md on {args.main}"]
    tracker = git(args.repo, "show", f"{args.main}:{TRACKER}")
    if tracker.returncode != 0:
        return [*refused, f"refused: no {TRACKER} on {args.main}"]
    rows = [norm(line) for line in tracker.stdout.splitlines() if TD_ROW.match(line)]
    ids = {m.group(1) for m in map(TD_ROW.match, tracker.stdout.splitlines()) if m}
    for name in files:
        for item in items(git(args.repo, "show", f"{args.main}:{name}").stdout, DEFERRED):
            if ids & set(TD.findall(item)) or any(norm(key(item)) in row for row in rows):
                continue
            refused.append(f'refused: Deferred item "{key(item)}" ({name.rsplit("/", 1)[-1]}) is not in the tracker')
    return refused


def check(args: argparse.Namespace, found: list[Deletion]) -> list[str]:
    """The save check, in order: records, lessons, kept items, commits, Deferred items."""
    return (
        check_records(args) + check_lessons(args) + check_kept(args, found) + check_commits(args) + check_deferred(args)
    )


def digest(found: list[Deletion]) -> str:
    """12 hex digits of the sha256 of the sorted digest lines; sizes are not in it, so a late scratch file keeps it."""
    return hashlib.sha256("\n".join(sorted(d.ident for d in found)).encode()).hexdigest()[:12]


def yeses(history: pathlib.Path) -> int:
    """The runs applied with the owner's yes: the distinct "run" strings of the history lines whose "yes" is true.

    A missing or unreadable history counts 0; a line that is not a JSON object, or whose "run" is not a string,
    counts nothing."""
    try:
        lines = history.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        return 0
    runs = set()
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("yes") is True and isinstance(entry.get("run"), str):
            runs.add(entry["run"])
    return len(runs)


def check_yes(args: argparse.Namespace, history: pathlib.Path, now: str) -> list[str]:
    """With --apply: the owner's yes was given for this digest, or three runs were applied with a yes."""
    if args.yes is not None and args.yes != now:
        return [f"refused: the list changed since the owner's yes (digest {now}, yes given for {args.yes})"]
    if args.yes is None and (k := yeses(history)) < 3:
        return [
            f"refused: --apply needs --yes <digest> until the owner has said yes for three runs ({k} of 3 in {history})"
        ]
    return []


def remove(args: argparse.Namespace, d: Deletion) -> str:
    """Removes one deletion: its `removed` or `deleted` line, or `failed <kind> <target>: <reason>`."""
    try:
        if d.kind == "worktree":
            clear_empty(d.target)
        if d.kind in ("worktree", "branch"):
            out = git(args.repo, *(("worktree", "remove") if d.kind == "worktree" else ("branch", "-D")), d.target)
            if out.returncode != 0:
                errors = out.stderr.strip().splitlines()
                return f"failed {d.kind} {d.target}: {errors[0] if errors else f'exit {out.returncode}'}"
        elif os.path.isdir(d.target) and not os.path.islink(d.target):
            shutil.rmtree(d.target)
        else:
            pathlib.Path(d.target).unlink()
    except OSError as e:
        return f"failed {d.kind} {d.target}: {e}"
    if d.kind == "branch":
        return f"deleted branch {d.target} at {d.sha[:7]}"
    return f"removed worktree {d.target}" if d.kind == "worktree" else f"removed {'job ' * (d.kind == 'job')}{d.target}"


def apply(args: argparse.Namespace, found: list[Deletion]) -> tuple[list[str], int]:
    """Removes every deletion in order, going on after a failure, then checks each kept item again."""
    lines = [remove(args, d) for d in found]
    removed = [d.kind for d, line in zip(found, lines, strict=True) if not line.startswith("failed ")]
    lines += [f"failed kept {given}: missing" for given in args.kept if not os.path.exists(given)]
    failed = sum(line.startswith("failed ") for line in lines)
    lines.append(f"done: {tally(removed)} removed; {failed} failed")
    return lines, failed


def record(args: argparse.Namespace, history: pathlib.Path, now: str, printed: list[str], acted: list[str]) -> None:
    """Appends the apply's block to RUN_DIR/collected.md and its JSON line to the history."""
    stamp = datetime.datetime.now(datetime.UTC)
    how = "the owner's yes" if args.yes is not None else "the standing rule"
    block = [f"# Collected {stamp:%Y-%m-%d %H:%M} UTC", f"digest {now}; {how}", *printed, *acted]
    with (pathlib.Path(args.run_dir) / "collected.md").open("a", encoding="utf-8") as f:
        f.write("\n".join(block) + "\n")
    entry = {"run": real(args.run_dir), "at": f"{stamp:%Y-%m-%dT%H:%M:%SZ}", "digest": now, "yes": args.yes is not None}
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def load(args: argparse.Namespace) -> dict:
    """The agents of the run's agents file; Usage for a missing run folder, agents file or main branch."""
    if not os.path.isdir(args.run_dir):
        raise Usage(f"no run folder {args.run_dir}")
    path = pathlib.Path(args.agents) if args.agents else pathlib.Path(args.run_dir) / "_control" / "_agents.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Usage(f"cannot read the agents file {path}: {e}") from None
    agents = data.get("agents") if isinstance(data, dict) else None
    if not isinstance(agents, dict):
        raise Usage(f"cannot read the agents file {path}: no agents object")
    if git(args.repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{args.main}").returncode != 0:
        raise Usage(f"no branch {args.main} in {args.repo}")
    return agents


def collect(args: argparse.Namespace) -> int:
    """Lists the run's deletions, runs the save check, and removes them with --apply when nothing is refused."""
    agents = load(args)
    rows = listing()
    found, refused, notes = deletions(args, agents, rows, worktrees(args.repo))
    refused = list(dict.fromkeys(check(args, found) + refused))
    run = pathlib.Path(args.run_dir)
    printed = [d.line for d in found] + notes + [f"keep {p}" for p in [*records(run), run / "lessons.md", *args.kept]]
    print("\n".join(printed))
    now = digest(found)
    history = pathlib.Path(args.history) if args.history else pathlib.Path(real(run)).parent / "collect-history.jsonl"
    if args.apply and not refused:
        refused = check_yes(args, history, now)
    if refused:
        print("\n".join([*refused, f"nothing removed: {len(refused)} refusals"]))
        return 3
    if not args.apply:
        print(f"total: {tally([d.kind for d in found])}; digest {now}; nothing removed without --apply")
        return 0
    acted, failed = apply(args, found)
    print("\n".join(acted))
    record(args, history, now, printed, acted)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """Parses the command line and runs the collector; a usage error exits 2."""
    ap = argparse.ArgumentParser(prog=PROG, description="Remove a finished run's leftovers once its record is saved.")
    ap.add_argument("run_dir", help="the run folder; kept, except its scratch/")
    ap.add_argument("--repo", required=True, help="the main worktree of the run's repository (never removed)")
    ap.add_argument("--plan", required=True, help="the plan folder, relative to the repository, read on --main")
    ap.add_argument("--kept", action="append", required=True, help="a file or folder that must exist before and after")
    ap.add_argument("--main", default="main", help="the branch everything must be merged into (default: main)")
    ap.add_argument("--final", action="append", default=[], help="a commit that must be an ancestor of --main")
    ap.add_argument("--worktree", action="append", default=[], help="a run worktree no agent's cwd names")
    ap.add_argument("--branch", action="append", default=[], help="a run branch with no worktree")
    ap.add_argument("--also", action="append", default=[], help="an eval result copy or preview copy to remove")
    ap.add_argument("--agents", help="the run's agents file (default: RUN_DIR/_control/_agents.json)")
    ap.add_argument("--jobs", type=pathlib.Path, default=pathlib.Path.home() / ".claude" / "jobs")
    ap.add_argument(
        "--history", help="the runs applied so far, one JSON line each (default: RUN_DIR/../collect-history.jsonl)"
    )
    ap.add_argument("--apply", action="store_true", help="remove; without it nothing is removed")
    ap.add_argument("--yes", help="the owner's yes for the dry run's digest; only with --apply")
    args = ap.parse_args(argv)
    if args.yes is not None and not args.apply:
        ap.error("--yes needs --apply")
    try:
        return collect(args)
    except Usage as e:
        print(f"{PROG}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
