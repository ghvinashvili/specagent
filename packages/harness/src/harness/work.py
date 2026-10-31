"""Code work travels from stage to stage as a commit.

A stage whose type changes the repository (a writer, a test-verifier, a librarian) leaves its work on a branch, one
per shard; the `output/` directory of such a stage holds at most a note about it. A later stage that names `<stage>:output/` as an input would receive nothing (seen live on 2026-10-02: the
verifier's `input/work/` was an empty directory, and the repository it started in was the base without the change).

Before a stage that depends on code work starts, the launcher builds the work commit: the base the branches started
from plus the change of every shard, as one commit with a neutral author and no trailers. The stage gets

- a checkout of that commit under `.claude/worktrees/<name>`, on a branch of its own, which its session enters with
  EnterWorktree (Claude Code resumes a worktree that already exists under the name it is given), and
- `changes.patch` under `input/<alias>/`: the change itself, without commit metadata.

A type that commits (a test-verifier, a later writer) builds on the work; a reviewing type runs its checks there.
Shards that change the same lines cannot be combined by a program: the launch is refused with the conflicting files,
and the manager takes the conflict to the human.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from . import access, state
from .gates import _common
from .gitcall import GIT

# The author of the work commit. A reviewer that runs `git log` in its checkout sees this and nothing else about
# who made the change; the fixed date makes the commit id depend on the content alone.
IDENTITY = {
    "GIT_AUTHOR_NAME": "work",
    "GIT_AUTHOR_EMAIL": "work@localhost",
    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
    "GIT_COMMITTER_NAME": "work",
    "GIT_COMMITTER_EMAIL": "work@localhost",
    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000",
}
MESSAGE = "work under review"


class WorkConflict(Exception):
    """Two shards changed the same place; `files` are the paths git could not combine."""

    def __init__(self, files: list[str], branches: list[str]):
        super().__init__(f"the branches {', '.join(branches)} cannot be combined: {', '.join(files) or 'see git'}")
        self.files, self.branches = files, branches


def _git(root: Path, *args: str, check: bool = True, neutral: bool = False) -> subprocess.CompletedProcess:
    env = {**os.environ, **IDENTITY} if neutral else None
    return subprocess.run([*GIT, *args], cwd=root, env=env, capture_output=True, text=True, check=check)


def sources(root: Path, policy: dict, stages: dict[str, dict], run_dir: Path, row: dict) -> list[dict]:
    """The branches behind the inputs of a stage: one entry per unit of an earlier stage whose type changes the
    repository (`changes_repository` in the policy: a writer, a test-verifier, a librarian) and whose result names
    its branch. Whatever file of that stage the row asks for, the work itself is on the branch."""
    found, seen = [], set()
    for item in row["inputs"]:
        dep, sep, _ = item.partition(":")
        if not sep or dep in seen or dep not in stages:
            continue
        seen.add(dep)
        if not access.type_row(policy, stages[dep]["role_type"])["changes_repository"]:
            continue
        base = run_dir / "stages" / dep
        shards = sorted(p for p in base.iterdir() if p.is_dir() and access.SHARD.match(p.name)) if base.is_dir() else []
        for unit in shards or [base]:
            result = unit / "result.json"
            if not result.is_file():
                continue
            branch = _common.branch_of(root, json.loads(result.read_text(encoding="utf-8")))
            if branch:
                found.append({"stage": dep, "shard": unit.name if unit != base else "", "branch": branch})
    return found


def combine(root: Path, branches: list[str]) -> tuple[str, str]:
    """(base, tree): the commit every branch started from, and the tree with the change of every branch applied."""
    heads = [_git(root, "rev-parse", f"{b}^{{commit}}").stdout.strip() for b in branches]
    base = _git(root, "merge-base", "--octopus", "HEAD", *heads).stdout.strip()
    acc = heads[0]
    for branch, head in zip(branches[1:], heads[1:], strict=True):
        merged = _git(root, "merge-tree", "--write-tree", "--name-only", acc, head, check=False)
        lines = merged.stdout.splitlines()
        if merged.returncode != 0:  # the tree id, the conflicting paths, an empty line, git's messages
            files = lines[1 : lines.index("")] if "" in lines else lines[1:]
            raise WorkConflict(sorted(set(files)), [branches[0], branch] if len(branches) == 2 else branches)
        acc = _git(root, "commit-tree", lines[0], "-p", acc, "-p", head, "-m", MESSAGE, neutral=True).stdout.strip()
    return base, _git(root, "rev-parse", f"{acc}^{{tree}}").stdout.strip()


TRIAL = "trial under review"


def trial_sources(root: Path, policy: dict, stages: dict[str, dict], run_dir: Path, row: dict) -> list[dict]:
    """The planner's trial a stage reviews before any work starts: for a row that changes nothing itself and returns
    to the stage that made the trial (`returns_to`, the critic of the stage `attack`), that stage's
    output/trial/trial.patch when its type builds a trial. Another reader of a plan (a council's, a writer) gets the
    plan without the trial's checkout; a writer takes the patch as a reference (planner.md)."""
    back = (row.get("returns_to") or {}).get("stage")
    if access.type_row(policy, row["role_type"])["changes_repository"] or back not in stages:
        return []
    named = {i.partition(":")[0] for i in row["inputs"] if ":" in i} | set(row.get("depends_on") or [])
    patch = run_dir / "stages" / back / "output" / "trial" / "trial.patch"
    if back in named and access.type_row(policy, stages[back]["role_type"])["trial_checkout"] and patch.is_file():
        return [{"stage": back, "trial": str(patch)}]
    return []


def trial_commit(root: Path, base: str, patch: Path) -> str:
    """The base with a planner's trial applied, as one commit with the neutral author: its id follows from the
    content, like the work commit's. A patch that does not apply raises AccessError with git's words."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, **IDENTITY, "GIT_INDEX_FILE": str(Path(tmp) / "index")}

        def run(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run([*GIT, *args], cwd=root, env=env, capture_output=True, text=True, check=False)

        run("read-tree", base)
        applied = run("apply", "--cached", str(patch))
        if applied.returncode != 0:
            raise access.AccessError(f"the trial patch does not apply to the base: {applied.stderr.strip()[-300:]}")
        return run("commit-tree", run("write-tree").stdout.strip(), "-p", base, "-m", TRIAL).stdout.strip()


def _follow(root: Path, path: Path, name: str, commit: str) -> None:
    """The work changed after this unit's checkout was made (its author was resumed and committed again). A
    checkout that only reviewed is moved to the new work commit, and what its session left changed there goes: no
    deliverable lives in it (that is under output/). One that holds commits of its own is left alone: replaying them
    is a decision, not a step of the launcher."""
    old = [c for c in _git(path, "log", "--format=%H %an", "-50").stdout.splitlines() if c.endswith(" work")]
    own = _git(path, "rev-list", "--count", f"{old[0].split()[0]}..HEAD").stdout.strip() if old else "1"
    if own != "0":
        raise access.AccessError(f"the checkout {name} holds its own commits on an earlier state of the work")
    moved = _git(path, "checkout", "-q", "-f", "-B", f"worktree-{name}", commit, check=False)
    if moved.returncode != 0:
        raise access.AccessError(f"the checkout {name} could not follow the work: {moved.stderr.strip()[-300:]}")


def prepare(
    root: Path,
    policy: dict,
    stages: dict[str, dict],
    run_dir: Path,
    row: dict,
    stage_dir: Path,
    name: str,
    checkout: bool = True,
):
    """Build the work commit and the checkout of a unit that depends on committed work; None when it depends on
    none. Running it again changes nothing while the work is the same: the commit id follows from the content. When
    the work has changed, a reviewing checkout follows it and the patch is written again (resume calls this too).
    A stage that reviews a plan gets the base with the planner's trial instead (trial_sources, trial_commit). With
    `checkout` False only the patch is written: a type that cannot enter a worktree and runs nothing (a judge) reads
    the change from it."""
    found = sources(root, policy, stages, run_dir, row)
    trials = [] if found else trial_sources(root, policy, stages, run_dir, row)
    if not found and not trials:
        return None
    if found:
        base, tree = combine(root, [f["branch"] for f in found])
        commit = _git(root, "commit-tree", tree, "-p", base, "-m", MESSAGE, neutral=True).stdout.strip()
    else:
        base = _common.base_commit(root, run_dir) or _git(root, "rev-parse", "HEAD").stdout.strip()
        commit = trial_commit(root, base, Path(trials[0]["trial"]))
        # the checkout's settings, hooks and agents would run in the reviewer's session, outside the sandbox
        shut = _common.closed_to(root, policy, run_dir, stages[trials[0]["stage"]]["role_type"])
        bad = [f for f in _common.changed_paths(root, base, commit) if shut(f)]
        if bad:
            raise access.AccessError(f"the trial changes paths closed to its author: {', '.join(bad[:6])}")
    found = found or trials
    path = root / ".claude" / "worktrees" / name
    if checkout and not path.exists():
        made = _git(root, "worktree", "add", "-q", "-B", f"worktree-{name}", str(path), commit, check=False)
        if made.returncode != 0:
            raise access.AccessError(f"the checkout of the work could not be created: {made.stderr.strip()[-300:]}")
    elif checkout and _git(path, "rev-parse", "HEAD").stdout.strip() != commit:
        _follow(root, path, name, commit)
    t = access.type_row(policy, row["role_type"])
    alias = t["alias"].get(stages[found[0]["stage"]]["role_type"], found[0]["stage"])
    patch = stage_dir / "input" / alias / "changes.patch"
    sha = access.put_copy(patch, _git(root, "diff", base, commit).stdout.encode("utf-8"))  # read-only, like every copy
    return {"worktree": name, "path": str(path), "base": base, "commit": commit, "patch": str(patch), "sha256": sha,
            "from": found}  # fmt: skip


def _unit_dirs(run_dir: Path, stage_id: str) -> list[Path]:
    base = run_dir / "stages" / stage_id
    shards = sorted(p for p in base.iterdir() if p.is_dir() and access.SHARD.match(p.name)) if base.is_dir() else []
    return shards or [base]


def _replay(root: Path, onto: str, commit: str) -> str:
    """The commit `commit` again, on top of `onto`, with its own author, date and message."""
    merged = _git(root, "merge-tree", "--write-tree", f"--merge-base={commit}^", onto, commit, check=False)
    if merged.returncode != 0:
        raise WorkConflict(merged.stdout.splitlines()[1:], [commit])
    name, mail, date, body = _git(root, "show", "-s", "--format=%an%x00%ae%x00%aI%x00%B", commit).stdout.split("\x00")
    env = {**os.environ, "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": mail, "GIT_AUTHOR_DATE": date}
    tree = merged.stdout.splitlines()[0]
    made = subprocess.run(
        [*GIT, "commit-tree", tree, "-p", onto, "-m", body.rstrip("\n")],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return made.stdout.strip()


def integrate(root: Path, policy: dict, stages: list[dict], run_dir: Path) -> dict:
    """One branch with everything a run committed, for the human to merge: `run/<run-id>`.

    The stages are taken in table order. A stage that started from the base (the first writer) contributes its
    branches as they are: one shard is taken as it is, several are merged, and their own commits stay. A stage that
    started from the work commit (a test-verifier after the writer) has its own commits replayed on top: the tree
    it started from is the tree of the real history, so nothing can conflict. Checkouts that only reviewed are not
    part of the result. A branch built before is never rewritten: the human may have added to it, and it is built
    again only after they deleted it (docs/decisions/0010)."""
    target = f"run/{run_dir.name}"
    built = _git(root, "rev-parse", "--verify", "-q", f"refs/heads/{target}", check=False).stdout.strip()
    if built:
        return {
            "ok": True,
            "status": "integrated_before",
            "branch": target,
            "head": built,
            "hint": f"the branch stays as it is; to build it again, delete it first: `git branch -D {target}`",
        }
    acc: str | None = None
    base: str | None = None
    used: list[dict] = []
    for row in stages:
        if not access.type_row(policy, row["role_type"])["changes_repository"]:
            continue
        for unit in _unit_dirs(run_dir, row["id"]):
            result = unit / "result.json"
            branch = (
                _common.branch_of(root, json.loads(result.read_text(encoding="utf-8"))) if result.is_file() else None
            )
            if not branch:
                continue
            head = _git(root, "rev-parse", f"{branch}^{{commit}}").stdout.strip()
            record = access.unit_record(run_dir, unit, "work")
            started = json.loads(record.read_text(encoding="utf-8"))["commit"] if record.is_file() else None
            if started and acc:  # built on the neutral work commit: replay its own commits onto the real history
                own = _git(root, "rev-list", "--reverse", f"{started}..{head}").stdout.split()
                for commit in own:
                    acc = _replay(root, acc, commit)
                used.append({"stage": row["id"], "branch": branch, "commits": len(own), "how": "replayed"})
            elif acc is None:
                base, acc = _git(root, "merge-base", "HEAD", head).stdout.strip(), head
                used.append({"stage": row["id"], "branch": branch, "how": "taken"})
            else:
                merged = _git(root, "merge-tree", "--write-tree", "--name-only", acc, head, check=False)
                lines = merged.stdout.splitlines()
                if merged.returncode != 0:
                    files = lines[1 : lines.index("")] if "" in lines else lines[1:]
                    raise WorkConflict(sorted(set(files)), [branch])
                acc = _git(root, "commit-tree", lines[0], "-p", acc, "-p", head, "-m", f"Merge {branch}").stdout.strip()
                used.append({"stage": row["id"], "branch": branch, "how": "merged"})
    if acc is None:
        return {"ok": False, "status": "nothing_committed", "why": "no stage of this run left work on a branch"}
    _git(root, "branch", "-f", target, acc)
    ahead = _git(root, "rev-list", "--count", f"{base}..{acc}").stdout.strip()
    return {
        "ok": True,
        "branch": target,
        "base": base,
        "head": acc,
        "commits": int(ahead),
        "from": used,
        "next": f"review `git diff {base[:9]} {target}`, then `git merge --no-ff {target}` on the branch it belongs to",
    }


def drop_checkout(root: Path, name: str) -> bool:
    """Remove a checkout and its branch: the trial of a planner, once the stage that builds on the plan starts.
    True when there was something to remove."""
    path, branch = root / ".claude" / "worktrees" / name, f"worktree-{name}"
    had = path.is_dir() or _git(root, "rev-parse", "--verify", "-q", branch, check=False).returncode == 0
    if path.is_dir():
        _git(root, "worktree", "remove", "-f", "-f", str(path), check=False)
    _git(root, "worktree", "prune", check=False)
    _git(root, "branch", "-D", branch, check=False)
    return had


SALVAGE = {  # who saved a checkout's uncommitted work: the harness, at the time it did
    "GIT_AUTHOR_NAME": "harness",
    "GIT_AUTHOR_EMAIL": "harness@localhost",
    "GIT_COMMITTER_NAME": "harness",
    "GIT_COMMITTER_EMAIL": "harness@localhost",
}


def remove_checkout(root: Path, path: Path, ref: str) -> str | None:
    """Remove a checkout of a run. Its uncommitted work (tracked and untracked files; ignored files are made again and
    not kept) is first saved as a commit on top of the checkout's HEAD and `ref` points at it; the commit is returned,
    None for a clean checkout (docs/decisions/0010). `git restore --source=<ref> -- .` brings the work back."""
    saved = None
    if path.is_dir() and _git(path, "status", "--porcelain", check=False).stdout.strip():
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, **SALVAGE, "GIT_INDEX_FILE": str(Path(tmp) / "index")}

            def git(*args: str) -> str:
                done = subprocess.run([*GIT, *args], cwd=path, env=env, capture_output=True, text=True, check=True)
                return done.stdout.strip()

            git("read-tree", "HEAD")
            git("add", "-A")
            message = f"salvage: the uncommitted work of {path.name}\n\nSaved by the harness before the checkout went."
            saved = git("commit-tree", git("write-tree"), "-p", "HEAD", "-m", message)
        _git(root, "update-ref", ref, saved)
    if path.is_dir():
        _git(root, "worktree", "remove", "-f", "-f", str(path), check=False)
    _git(root, "worktree", "prune", check=False)
    return saved


def clean_checkouts(root: Path, policy: dict, stages: list[dict], run_dir: Path) -> dict:
    """Remove the checkouts of a run, after saving what was not committed (remove_checkout). A review checkout goes
    with its branch; the branch of a unit that committed is kept (its commits are in `run/<run-id>`, the branch itself
    is the human's to delete)."""
    from . import launch  # the name of a unit's checkout is the launcher's rule

    removed, kept, salvaged, not_removed = [], [], [], []
    for row in stages:
        own = access.type_row(policy, row["role_type"])["changes_repository"]
        for unit in _unit_dirs(run_dir, row["id"]):
            shard = int(unit.name) if access.SHARD.match(unit.name) else None
            name = launch.worktree_name(run_dir.name, row["id"], shard)
            path = root / ".claude" / "worktrees" / name
            if path.is_dir():
                ref, rel = f"refs/harness/salvage/{run_dir.name}/{name}", str(path.relative_to(root))
                try:
                    if remove_checkout(root, path, ref):
                        salvaged.append(ref)
                except subprocess.CalledProcessError as e:  # the work could not be saved: the checkout stays
                    why = f"its uncommitted work could not be saved, so it stays: {(e.stderr or '').strip()[:300]}"
                    not_removed.append({"checkout": rel, "why": why})
                    continue
                if path.is_dir():
                    not_removed.append({"checkout": rel, "why": "`git worktree remove` could not remove it"})
                else:
                    removed.append(rel)
            branch = f"worktree-{name}"
            if _git(root, "rev-parse", "--verify", "-q", branch, check=False).returncode != 0:
                continue
            if own:
                kept.append(branch)
            else:
                _git(root, "branch", "-D", branch, check=False)
    _git(root, "worktree", "prune", check=False)
    return {"ok": True, "removed": removed, "kept_branches": kept, "salvaged": salvaged, "not_removed": not_removed}


WIKI_PAGE = re.compile(r"^wiki/(concepts|entities|sources|decisions)/[a-z0-9-]+\.md$")


def accepted(stages: list[dict], run_dir: Path) -> bool:
    """The run's checks accepted its work: some stage's result.json holds a verdict, and every verdict is accept."""
    decisions = []
    for row in stages:
        path = run_dir / "stages" / row["id"] / "result.json"
        if not path.is_file():
            continue
        try:
            res = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False  # an unreadable verdict is no accept
        verdict = res.get("verdict") if isinstance(res, dict) else None
        if isinstance(verdict, dict) and "decision" in verdict:
            decisions.append(verdict["decision"])
    return bool(decisions) and all(d == "accept" for d in decisions)


def mark_verified(root: Path, stages: list[dict], run_dir: Path, base: str, head: str) -> tuple[str, list[str]]:
    """The pages a wiki run changed become `verified` once the checks of its run accepted them: one more commit on top
    of the run's work, made here without a model. The librarian writes `draft`; only a `verified` page is delivered
    in a knowledge pack (pack.pages), so without this step nothing the wiki learns would ever reach a session."""
    if not accepted(stages, run_dir):
        return head, []
    changed = _git(root, "diff", "--name-only", base, head, "--", "wiki").stdout.splitlines()
    marked: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}

        def git(*args: str, data: str | None = None) -> str:
            done = subprocess.run(
                [*GIT, *args], cwd=root, env=env, input=data, capture_output=True, text=True, check=True
            )
            return done.stdout.strip()

        git("read-tree", head)
        for path in (p for p in changed if WIKI_PAGE.match(p)):
            text = _git(root, "show", f"{head}:{path}", check=False).stdout
            front, sep, body = text[4:].partition("\n---\n") if text.startswith("---\n") else ("", "", "")
            fixed = re.sub(r"^status: draft$", "status: verified", front, count=1, flags=re.MULTILINE)
            if not sep or fixed == front:
                continue
            blob = git("hash-object", "-w", "--stdin", data="---\n" + fixed + sep + body)
            git("update-index", "--cacheinfo", f"100644,{blob},{path}")
            marked.append(path)
        tree = git("write-tree")
    if not marked:
        return head, []
    message = (
        f"docs(wiki): {len(marked)} pages verified\n\n"
        f"The check stage of run {run_dir.name} confirmed the statements of these pages against their sources."
    )
    return _git(root, "commit-tree", tree, "-p", head, "-m", message).stdout.strip(), marked


def integrate_run(root: Path, run_id: str, clean: bool = False) -> dict:
    """`harness integrate`: refuse while a stage is unfinished or waits for a human, then build `run/<run-id>`."""
    run_dir = state.runs_root(root) / run_id
    manifest = state.load(root, run_dir / "manifest.json", "run-manifest")
    st = state.load(root, run_dir / "state.json", "run-state")
    open_stages = [
        sid for sid, s in st["stages"].items() if s["status"] != "done" or s.get("approval") in ("pending", "rejected")
    ]
    if open_stages:
        why = "every stage is done and approved before the run's work becomes one branch"
        return {"ok": False, "status": "not_finished", "stages": open_stages, "why": why}
    policy = access.load_policy(root)
    stages = manifest["stages"]  # the stages the run was made with, whatever the table says now
    try:
        out = integrate(root, policy, stages, run_dir)
    except WorkConflict as e:
        return {"ok": False, "status": "work_conflict", "files": e.files, "branches": e.branches, "why": str(e)}
    if out["ok"] and "base" in out:  # a branch built before is left as it is
        head, pages = mark_verified(root, stages, run_dir, out["base"], out["head"])
        if pages:
            _git(root, "branch", "-f", out["branch"], head)
            out.update(head=head, commits=out["commits"] + 1, verified_pages=pages)
    if clean and out.get("status") == "nothing_committed":  # a planning run: nothing to integrate, all to close
        out["ok"] = True
    if clean and out["ok"]:
        out["cleaned"] = clean_checkouts(root, policy, stages, run_dir)
        out["cleaned"]["sessions"] = remove_sessions(st)
    return out


def session_jobs(st: dict) -> list[str]:
    """Every background session a run started, by the job id `claude --bg` printed, in launch order."""
    jobs: list[str] = []
    for stage in st["stages"].values():
        for unit in [stage, *stage.get("shards", {}).values()]:
            jobs += [j for j in unit.get("job_ids", []) if j not in jobs]
    return jobs


def abort_run(root: Path, run_id: str, reason: str) -> dict:
    """`harness abort`: end a run that will not be integrated (docs/decisions/0010). Its sessions are stopped first,
    so nothing writes into a checkout while it goes; its checkouts go after their uncommitted work is saved; its
    sessions leave the session list (the transcripts stay); branches with commits and the run folder stay. The state
    records `aborted` with the reason and the status the run had. A run already aborted is reported as it is."""
    run_dir = state.runs_root(root) / run_id
    st = state.load(root, run_dir / "state.json", "run-state")
    if st["status"] == "aborted":
        return {"ok": True, "status": "aborted", "run_id": run_id, "already": True, "aborted": st["aborted"]}
    target = f"run/{run_id}"
    if _git(root, "rev-parse", "--verify", "-q", f"refs/heads/{target}", check=False).returncode == 0:
        hint = f"`harness integrate --run {run_id} --clean` cleans it; the branch stays"
        return {"ok": False, "status": "integrated", "branch": target, "hint": hint}
    stages = state.load(root, run_dir / "manifest.json", "run-manifest")["stages"]  # those the run was made with
    for job in session_jobs(st):
        try:
            subprocess.run(["claude", "stop", job], capture_output=True, text=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            break
    cleaned = clean_checkouts(root, access.load_policy(root), stages, run_dir)
    sessions = remove_sessions(st)
    with state.locked(run_dir / "state.json"):  # sessions and checkouts went without the lock: read again (ADR-0021)
        st = state.load(root, run_dir / "state.json", "run-state")
        if st["status"] != "aborted":  # an abort run at the same time keeps the record it wrote first
            st["aborted"] = {"at": state.now(), "reason": reason, "from": st["status"]}
            st["status"], st["updated_at"] = "aborted", state.now()
            state.save(root, run_dir / "state.json", st, "run-state")
    out = {"ok": True, "status": "aborted", "run_id": run_id, "from": st["aborted"]["from"], "sessions": sessions}
    out.update({k: v for k, v in cleaned.items() if k != "ok"})
    if cleaned["salvaged"]:
        out["restore"] = "`git worktree add <dir> <ref>`: the saved work as one commit on top of the checkout's last"
    return out


def remove_sessions(st: dict) -> list[str]:
    """Take a finished run's background sessions out of Claude Code's session list (`claude stop`, `claude rm`),
    so the agent view shows what is running and not everything that ever ran. The transcripts stay on disk
    (seen live: `claude rm` keeps `<session>.jsonl`), which is what `cache-report` and an audit read."""
    jobs = session_jobs(st)
    removed = []
    for job in jobs:
        try:
            subprocess.run(["claude", "stop", job], capture_output=True, text=True, timeout=30, check=False)
            done = subprocess.run(["claude", "rm", job], capture_output=True, text=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            break
        if done.returncode == 0:
            removed.append(job)
    return removed
