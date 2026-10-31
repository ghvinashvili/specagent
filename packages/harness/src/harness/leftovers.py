"""What earlier runs left behind (docs/decisions/0010), found without a model and named with the command that removes
it. Nothing here removes anything: `harness doctor` shows the list, and `harness run` names the runs still open."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path

import jsonschema

from . import launch, state
from .gitcall import GIT

OPEN = ("created", "running", "waiting_human", "paused")
STALE = dt.timedelta(hours=24)  # an open run unchanged this long, with no unit working, is named


def _runs(root: Path) -> list[tuple[str, dict]]:
    runs = []
    for run_dir in sorted(state.runs_root(root, create=False).glob("*-*")):
        try:
            runs.append((run_dir.name, state.load(root, run_dir / "state.json", "run-state")))
        except (OSError, ValueError, jsonschema.ValidationError):  # no state, or one this version cannot read
            continue
    return runs


def _units(ss: dict) -> list[tuple[str | None, dict]]:
    return [(k, u) for k, u in sorted(ss["shards"].items())] if ss.get("shards") else [(None, ss)]


def _shards(run_dir: Path, stage_id: str, ss: dict) -> set[int | None]:
    """The units a stage has, as the state and the folders on disk know them (work.clean_checkouts goes by the
    folders): their checkouts are `launch.worktree_name(run, stage, shard)`."""
    base = run_dir / "stages" / stage_id
    on_disk = {int(p.name) for p in base.iterdir() if p.is_dir() and p.name.isdigit()} if base.is_dir() else set()
    known = {int(k) for k in ss.get("shards", {})} | on_disk
    return known or {None}


def _rows(u: dict, by_id: dict, by_session: dict) -> list[dict]:
    rows = [by_id[j] for j in u.get("job_ids", []) if j in by_id]
    return rows + [by_session[s] for s in u.get("session_ids", []) if s in by_session and by_session[s] not in rows]


def waits_for(st: dict) -> str:
    if any(e["status"] == "open" for e in st["escalations"]):
        return "an escalation"
    if any(ss["status"] == "done" and ss["approval"] == "pending" for ss in st["stages"].values()):
        return "an approval"
    return "nothing"


def open_runs(root: Path, but: str | None = None) -> list[dict]:
    """The runs not yet ended, for the manager to ask the human about each: go on, or `harness abort`."""
    return [
        {
            "run_id": run_id,
            "status": st["status"],
            "waits_for": waits_for(st),
            "changed_at": st.get("changed_at") or st["updated_at"],
        }
        for run_id, st in _runs(root)
        if st["status"] in OPEN and run_id != but
    ]


def _listing(root: Path) -> list[dict]:
    try:
        return launch.listing(root)
    except (OSError, ValueError, subprocess.CalledProcessError):  # no claude here: no sessions to judge
        return []


def find(root: Path, listing: list[dict] | None = None, now: dt.datetime | None = None) -> list[dict]:
    rows = _listing(root) if listing is None else listing
    now = now or dt.datetime.now(dt.UTC)
    by_id = {r["id"]: r for r in rows if r.get("id")}
    by_session = {r["sessionId"]: r for r in rows if r.get("sessionId")}
    found: list[dict] = []
    checkouts: set[str] = set()
    for run_id, st in _runs(root):
        names = {
            launch.worktree_name(run_id, sid, shard)
            for sid, ss in st["stages"].items()
            for shard in _shards(state.runs_root(root, create=False) / run_id, sid, ss)
        }
        if st["status"] != "aborted":  # an open run's checkouts, and a finished one's until it is closed
            checkouts |= names
        changed = dt.datetime.fromisoformat(st.get("changed_at") or st["updated_at"])
        if st["status"] == "done" and now - changed > STALE:
            listed = any(_rows(u, by_id, by_session) for ss in st["stages"].values() for _, u in _units(ss))
            if listed or any((root / ".claude" / "worktrees" / n).is_dir() for n in names):
                found.append(
                    {
                        "kind": "unclosed_run",
                        "what": f"{run_id}: done since {changed:%Y-%m-%d %H:%M}, its sessions or checkouts are still there",
                        "fix": f"`harness integrate --run {run_id} --clean` (a run that committed nothing is only "
                        f'closed), or `harness abort --run {run_id} --reason "<why>"`',
                    }
                )
        if st["status"] in OPEN:
            working = any(
                r.get("status") == "busy"
                for ss in st["stages"].values()
                for _, u in _units(ss)
                for r in _rows(u, by_id, by_session)
            )
            if not working and now - changed > STALE:
                found.append(
                    {
                        "kind": "stale_run",
                        "what": f"{run_id}: {st['status']} and unchanged since {changed:%Y-%m-%d %H:%M}, "
                        f"waiting for {waits_for(st)}",
                        "fix": f'ask the human: go on, or `harness abort --run {run_id} --reason "<their words>"`',
                    }
                )
        for sid, ss in st["stages"].items():
            finished = ss["status"] == "done" and ss["approval"] in ("not_required", "approved")
            if st["status"] != "aborted" and not finished:
                continue
            for _, u in _units(ss):
                for r in _rows(u, by_id, by_session):
                    if r.get("pid"):
                        found.append(
                            {
                                "kind": "live_session",
                                "what": f"session {r.get('id')} of {run_id}/{sid} is still a process",
                                "fix": f"claude stop {r.get('id')}",
                            }
                        )
    found += _checkouts(root, rows, checkouts)
    found += _plugin_records(root)
    shared = root.parent / "runs"
    if (shared / state.RUNS_MARKER).is_file():
        others = sorted(p.name for p in root.parent.iterdir() if p != root and state._checkout(p))
        if others:
            found.append(
                {
                    "kind": "shared_runs",
                    "what": f"{shared} is the runs root of {', '.join(others)} too",
                    "fix": "move the other checkouts out of this folder (a trial copy belongs in experiments/)",
                }
            )
    return found


def _checkouts(root: Path, rows: list[dict], open_checkouts: set[str]) -> list[dict]:
    found = []
    base = root / ".claude" / "worktrees"
    for r in rows:
        cwd = r.get("cwd") or ""
        if cwd.startswith(str(base) + os.sep) and not Path(cwd).exists():
            found.append(
                {
                    "kind": "lost_session",
                    "what": f"session {r.get('id')} works in {cwd}, which is gone",
                    "fix": f"claude rm {r.get('id')}",
                }
            )
    for path in sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []:
        if path.name not in open_checkouts:
            found.append(
                {
                    "kind": "checkout",
                    "what": f"{path.relative_to(root)} belongs to no run that is open or waiting to be closed",
                    "fix": "`harness abort` or `harness integrate --clean` for its run; otherwise, after a look, "
                    f"`git worktree remove {path.relative_to(root)}`",
                }
            )
    listed = subprocess.run(
        [*GIT, "worktree", "list", "--porcelain"], cwd=root, capture_output=True, text=True, check=False
    )
    for block in listed.stdout.split("\n\n") if listed.returncode == 0 else []:
        lines = block.splitlines()
        if any(line.startswith("prunable") for line in lines):
            found.append(
                {
                    "kind": "checkout_record",
                    "what": f"git still lists {lines[0].removeprefix('worktree ')}, which is gone",
                    "fix": "git worktree prune",
                }
            )
    return found


def _plugin_records(root: Path) -> list[dict]:
    """Registrations of this project's marketplaces, its own and the name every project shared before (1.1.0), at a
    path that is gone. Other projects' records are theirs."""
    names = {"harness-internal"}
    market = root / "plugins" / ".claude-plugin" / "marketplace.json"
    if market.is_file():
        names.add(json.loads(market.read_text(encoding="utf-8"))["name"])
    plugins = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "plugins"
    found = []
    known = plugins / "known_marketplaces.json"
    for name, entry in json.loads(known.read_text(encoding="utf-8")).items() if known.is_file() else []:
        path = (entry.get("source") or {}).get("path")
        if name in names and path and not Path(path).exists():
            found.append(
                {
                    "kind": "marketplace",
                    "what": f"{name} is registered at {path}, which is gone",
                    "fix": f"claude plugin marketplace remove {name} (when no checkout on this machine uses it)",
                }
            )
    installed = plugins / "installed_plugins.json"
    doc = json.loads(installed.read_text(encoding="utf-8")) if installed.is_file() else {}
    for key, entries in (doc.get("plugins", doc) if isinstance(doc, dict) else {}).items():
        if key.rpartition("@")[2] not in names or not isinstance(entries, list):
            continue
        for entry in entries:
            path = entry.get("projectPath") if isinstance(entry, dict) else None
            if path and not Path(path).exists():
                found.append(
                    {
                        "kind": "plugin",
                        "what": f"{key} is installed for {path}, which is gone",
                        "fix": f"`claude plugin uninstall {key} --scope project` run in {path}; the folder is gone, "
                        "so check first how Claude Code removes such a record",
                    }
                )
    return found
