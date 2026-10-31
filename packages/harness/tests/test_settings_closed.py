"""The paths the project's settings close, where the plan's tests (test_closed_paths.py) do not reach: a settings rule
whose path leaves the repository through `..`, or names the repository's root itself, closes no path in it, as the plan
says of `_repo_pattern` (None outside the root and for the root itself); and the assignment's listed material is refused
a file the settings close, as the material chosen by script is (docs/decisions/0025)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from harness import access, launch

POLICY = {
    "schema_version": 1,
    "defaults": {
        "dirs": ["stage"], "blind": False, "brief_drop": [], "cache_ttl": "5m", "plugins": [], "mcp_servers": [],
        "pack_files": [], "repo_deny": ["docs/handoff/**"], "blind_deny": [], "never_copy": [],
    },
    "types": {"planner": {"may_receive": ["brief"], "outputs_of": []}},
}  # fmt: skip


def test_a_settings_rule_that_climbs_out_of_the_repository_or_names_its_root_closes_nothing(tmp_path: Path):
    """`../runs/_inbox` is the entry the plan has the manager add to `sandbox.filesystem.denyRead`: it names the inbox
    beside the checkout, not a path of the repository, and a `..` written into a Read rule or an absolute rule leaves
    the root as well. A `..` that stays inside the repository still closes the path it reaches."""
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    deny_read = ["../runs/_inbox", "./a/../../outside/**", ".", "./", "/", "./b/../c"]
    deny = ["Read(../secrets.txt)", f"Read(/{root.resolve().as_posix()}/../x/**)"]
    settings = {"permissions": {"deny": deny}, "sandbox": {"filesystem": {"denyRead": deny_read}}}
    (root / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")
    assert access.settings_closed(root) == ["*/c", "*/c/*", "c", "c/*"]


def test_an_assignment_that_lists_a_file_the_project_settings_close_is_refused(tmp_path: Path):
    """launch.material_problem, which `harness assign` asks before it stores an assignment, takes the type's closed
    paths with the project settings' (access.unreadable): a listed file under `secrets/` is closed to the stage's type,
    a listed file the settings leave open is no problem."""
    root = tmp_path / "repo"
    settings = json.dumps({"sandbox": {"filesystem": {"denyRead": ["./secrets"]}}})
    files = {"docs/roles/need-to-know.yaml": yaml.safe_dump(POLICY), ".claude/settings.json": settings,
             "secrets/notes.md": "the vault\n", "src/app.py": "a = 1\n"}  # fmt: skip
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    manifest = {"stages": [{"id": "plan", "role_type": "planner"}]}
    closed = launch.material_problem(root, manifest, "plan", "## Material\n- `secrets/notes.md` — the notes\n")
    assert closed == "material `secrets/notes.md`: `secrets/notes.md` is closed to the type of this stage"
    assert launch.material_problem(root, manifest, "plan", "## Material\n- `src/app.py` — the app\n") is None
