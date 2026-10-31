"""The guard hooks of a role session's Bash and file tools (.claude/hooks/guard-checkout.py, guard-bash.py and the
command reader they share, shellwords.py): the plain spellings they refuse (wave 1 of the fixes of 2026-10-04; what a
command builds at run time is held by the sandbox and the write gate, docs/decisions/0025). And the guards the
pipeline's role settings wire (D10, owner 2026-10-30): guard-read.py refuses a whole read of a file over 20,000 bytes,
guard-records.py a Write or Edit that removes or rewrites a line of a run's record."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from harness import state

HOOKS = Path(__file__).resolve().parents[3] / ".claude" / "hooks"


def run_hook(name: str, payload: dict, env: dict) -> str:
    """What a PreToolUse hook decided: `deny`, `allow` (it printed nothing), or `exit <code>`."""
    res = subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin", **env},
    )
    if res.returncode:
        return f"exit {res.returncode}"
    return json.loads(res.stdout)["hookSpecificOutput"]["permissionDecision"] if res.stdout.strip() else "allow"


@pytest.fixture()
def box(tmp_path: Path) -> dict:
    """A shared checkout (`repo`), the session's checkout in it, another folder whose name holds the checkout's, and
    the session's stage directory in the runs root beside the repository; HOME is the folder that holds them all."""
    root = tmp_path / "repo"
    checkout = root / ".claude/worktrees/r1-plan"
    stage = tmp_path / "repo-runs/r1/stages/plan"
    for d in (root / "packages", checkout / "packages", root / ".claude/worktrees/r1-plan-old", stage / "input"):
        d.mkdir(parents=True, exist_ok=True)
    (root / "packages/x.py").write_text("BASE\n", encoding="utf-8")
    (checkout / "packages/x.py").write_text("WORK\n", encoding="utf-8")
    (root / ".claude/hooks").mkdir()
    shutil.copy(HOOKS / "guard-bash.json", root / ".claude/hooks/guard-bash.json")
    shutil.copy(HOOKS.parent / "settings.json", root / ".claude/settings.json")
    env = {"HARNESS_RUN_DIR": str(stage.parents[1]), "HARNESS_STAGE": "plan", "HARNESS_WORKTREE": "r1-plan",
           "CLAUDE_PROJECT_DIR": str(root), "HOME": str(tmp_path)}  # fmt: skip
    return {"root": root, "checkout": checkout, "stage": stage, "box": tmp_path, "env": env}


def places(b: dict, text: str) -> str:
    for key in ("root", "checkout", "stage", "box"):
        text = text.replace("{" + key.upper() + "}", str(b[key]))
    return text.replace("{OLD}", str(b["root"] / ".claude/worktrees/r1-plan-old"))


CHECKOUT_CASES = [
    ("A1", "Bash", {"command": "cat packages/x.py"}, "{ROOT}", "deny"),
    ("A2", "Read", {"file_path": "{ROOT}/packages/x.py"}, "{STAGE}", "deny"),
    ("A3", "Bash", {"command": "cat {ROOT}/packages/x.py"}, "{STAGE}", "deny"),
    ("A4", "Read", {"file_path": "{CHECKOUT}/packages/x.py"}, "{STAGE}", "allow"),
    ("A5", "Bash", {"command": "cd {CHECKOUT} && cat packages/x.py"}, "{ROOT}", "allow"),
    ("A6", "Bash", {"command": "ls"}, "{STAGE}", "allow"),
    ("B1", "Read", {"file_path": "{ROOT}/packages/x.py"}, "{CHECKOUT}", "deny"),  # 04/F1
    ("B2", "Bash", {"command": "cat {ROOT}/packages/x.py"}, "{CHECKOUT}", "deny"),
    ("B3", "Bash", {"command": "cd {ROOT} && cat packages/x.py"}, "{CHECKOUT}", "deny"),
    ("B4", "Bash", {"command": "cat ~/repo/packages/x.py"}, "{STAGE}", "deny"),  # 04/F2
    ("B5", "Bash", {"command": "cat ../../../../repo/packages/x.py"}, "{STAGE}", "deny"),
    ("B6", "Bash", {"command": "cd ~/repo && cat packages/x.py"}, "{STAGE}", "deny"),
    ("B7", "Bash", {"command": "cd {CHECKOUT} && cat {ROOT}/packages/x.py"}, "{ROOT}", "deny"),  # 04/F3
    ("B8", "Bash", {"command": "cd {CHECKOUT}/../../.. && cat packages/x.py"}, "{ROOT}", "deny"),
    ("B9", "Bash", {"command": "cat {ROOT}/packages/x.py"}, "{OLD}", "deny"),
    ("B10", "Grep", {"pattern": "BASE", "path": "{BOX}"}, "{STAGE}", "deny"),  # 04/F4
    ("B11", "Glob", {"pattern": "repo/packages/*.py", "path": "{BOX}"}, "{STAGE}", "deny"),
    ("C1", "Bash", {"command": "cat $HOME/repo/packages/x.py"}, "{STAGE}", "deny"),
    ("C2", "Bash", {"command": "cat {BOX}/rep*/packages/x.py"}, "{STAGE}", "deny"),
    ("C3", "Bash", {"command": "bash -c 'cat {ROOT}/packages/x.py'"}, "{CHECKOUT}", "deny"),
    ("C4", "Bash", {"command": "cat $(echo {ROOT})/packages/x.py"}, "{CHECKOUT}", "deny"),
    ("C5", "Glob", {"pattern": "{ROOT}/packages/*.py"}, "{CHECKOUT}", "deny"),
    ("C6", "Bash", {"command": "uv run pytest -q packages/harness"}, "{CHECKOUT}", "allow"),
    ("C7", "Edit", {"file_path": "{ROOT}/packages/x.py"}, "{CHECKOUT}", "deny"),
]


@pytest.mark.parametrize(
    ("case", "tool", "tool_input", "cwd", "expect"), CHECKOUT_CASES, ids=[c[0] for c in CHECKOUT_CASES]
)
def test_a_session_with_a_checkout_is_refused_the_plain_spellings_of_the_shared_checkout(
    box, case, tool, tool_input, cwd, expect
):
    """04/F1 to F4: refused also while the shell stands in the checkout (or a folder whose path holds its name), by
    `~`, `..`, a variable, a glob or `bash -c`, after the way back, and by a search rooted above the repository."""
    payload = {"tool_name": tool, "tool_input": {k: places(box, v) for k, v in tool_input.items()},
               "cwd": places(box, cwd), "hook_event_name": "PreToolUse"}  # fmt: skip
    assert run_hook("guard-checkout.py", payload, box["env"]) == expect


GIT_SWEEPS = [
    "git add -A", "git add .", "git commit -a -m probe", "git add --all", "git  add  -A", "git commit -am probe",
    "git -C . add -A", "git add -Av", "git add -v -A", "git add ./", "git add '.'", "git add -- .",
    "git add .&&git status --short", "git add :/", "git stage -A", "git add \\\n-A", "git commit -m probe -a",
    "git commit --message=probe --all", "git commit -m x .", "git add --al", "env git add -A", "sudo git add .",
    "exec git commit -a", "bash -c 'git add -A'", "command git add -A", "nice -n 5 git add .", "timeout 5 git add -A",
]  # fmt: skip


@pytest.mark.parametrize("command", GIT_SWEEPS)
def test_the_plain_spellings_of_a_whole_tree_add_or_commit_are_refused_in_a_role_session(box, command):
    """04/F5 and item 7g: the sandbox hides files the type may not read and git sees them as deleted."""
    assert run_hook("guard-bash.py", {"tool_name": "Bash", "tool_input": {"command": command}}, box["env"]) == "deny"


@pytest.mark.parametrize("command", ["git add a.txt", "git add packages/x.py tests/test_x.py", "git commit -m 'a.' ",
                                     "git commit -ma", "git status --short", "git diff HEAD -- ."])  # fmt: skip
def test_a_named_add_or_commit_passes(box, command):
    assert run_hook("guard-bash.py", {"tool_name": "Bash", "tool_input": {"command": command}}, box["env"]) == "allow"


@pytest.mark.parametrize(("command", "expect"), [
    ("echo '{}' > result.json", "deny"), ("tee tasks.json < draft.json", "deny"), ("cp draft.json result.json", "deny"),
    ("sed -i 's/partial/complete/' result.json", "deny"), ("python3 -c \"open('result.json', 'w').write('{}')\"", "deny"),
    ("printf '{' > {STAGE}/../../escalations/001.json", "deny"), ("mv x.json {BOX}/repo-runs/r1/escalations/", "deny"),
    ("cat result.json", "allow"), ("jq .status result.json", "allow"), ("ls {BOX}/repo-runs/r1/escalations", "allow"),
])  # fmt: skip
def test_a_role_session_writes_no_run_file_through_the_shell(box, command, expect):
    """04/F7: the run's JSON files, the escalations above all, are written with the Write tool, where the schema check
    runs; a reader may still read them."""
    payload = {"tool_name": "Bash", "tool_input": {"command": places(box, command)}, "cwd": str(box["checkout"])}
    assert run_hook("guard-bash.py", payload, box["env"]) == expect


@pytest.mark.parametrize("command", [
    "cat {INBOX}/note.txt", "nl {INBOX}/note.txt", "tac {INBOX}/note.txt", "base64 {INBOX}/note.txt",
    "python3 -c \"print(open('{INBOX}/note.txt').read())\"", "find {INBOX} -type f -exec cat {} +",
    "cat {RUNS}/_inb*/upload/note.txt", "grep -r UNTRUSTED {RUNS}", "find {RUNS} -name note.txt",
])  # fmt: skip
def test_no_session_but_the_quarantine_reader_reads_the_inbox_through_the_shell(box, command):
    """04/F6: the manager's session (no HARNESS_RUN_DIR) read an inbox file with any program but fourteen."""
    runs = box["box"] / "repo-runs"
    (runs / "_inbox/upload").mkdir(parents=True)
    (runs / "_inbox/upload/note.txt").write_text("UNTRUSTED\n", encoding="utf-8")
    text = command.replace("{INBOX}", str(runs / "_inbox/upload")).replace("{RUNS}", str(runs))
    manager = {"CLAUDE_PROJECT_DIR": str(box["root"]), "HOME": str(box["box"])}
    assert run_hook("guard-bash.py", {"tool_name": "Bash", "tool_input": {"command": text}}, manager) == "deny"
    assert run_hook("guard-bash.py", {"tool_name": "Bash", "tool_input": {"command": "ls"}}, manager) == "allow"


@pytest.mark.parametrize(("command", "expect"), [
    ("env uv run harness launch --run r1 --stage plan", "deny"), ("bash -c 'uv run harness poll --run r1'", "deny"),
    ("sudo python3 ops/machine-setup.py", "deny"), ("FOO=1 env uv run harness watch --run r1", "deny"),
    ("bash -c \"claude --bg hello\"", "deny"), ("echo 'an open quote", "deny"), ("uv run pytest -q", "allow"),
])  # fmt: skip
def test_a_role_session_runs_nothing_unsandboxed_behind_a_wrapper(box, command, expect):
    """Item 7g: before it matches a rule Claude Code takes off only some wrappers; env, sudo, exec and bash -c are
    taken off here. A command of `sandbox.excludedCommands` runs outside the sandbox."""
    assert run_hook("guard-bash.py", {"tool_name": "Bash", "tool_input": {"command": command}}, box["env"]) == expect


def test_the_rules_are_the_main_checkout_s_when_the_project_directory_is_a_checkout(box):
    """Item 7e: a session whose project directory is a checkout reads the rules of the main checkout, not the ones of
    the checkout it may be changing."""
    (box["checkout"] / ".claude/hooks").mkdir(parents=True)
    (box["checkout"] / ".claude/hooks/guard-bash.json").write_text('{"version": 2, "deny": []}', encoding="utf-8")
    env = {**box["env"], "CLAUDE_PROJECT_DIR": str(box["checkout"])}
    assert run_hook("guard-bash.py", {"tool_name": "Bash", "tool_input": {"command": "git add -A"}}, env) == "deny"


def module(name: str):
    """A hook script as a module, as test_layout.py loads the hooks that find run state on their own."""
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), HOOKS / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


@pytest.mark.parametrize("name", ["guard-bash", "guard-checkout"])
def test_a_guard_takes_the_main_checkout_for_a_project_directory_that_is_a_checkout(name: str, tmp_path: Path):
    """Item 7e: CLAUDE_PROJECT_DIR is where the session started (hooks.md:601-612 in the facts file); a guard maps a
    checkout under .claude/worktrees/ to the main checkout, whose rules a session cannot be changing."""
    repo = tmp_path / "template"
    assert module(name).main_checkout(repo / ".claude" / "worktrees" / "r1-write-01") == repo
    assert module(name).main_checkout(repo) == repo


def test_guard_bash_finds_the_inbox_where_the_harness_keeps_it(tmp_path: Path):
    """04/F6: the inbox guard of the shell looks for `<runs root>/_inbox/` by the harness's own rule."""
    repo = tmp_path / "container" / "template"
    repo.mkdir(parents=True)
    assert module("guard-bash").runs_root(repo) == state.runs_root(repo)
    (tmp_path / "container" / "runs").mkdir()
    (tmp_path / "container" / "runs" / state.RUNS_MARKER).write_text("")
    assert module("guard-bash").runs_root(repo) == state.runs_root(repo) == tmp_path / "container" / "runs"


@pytest.mark.parametrize("name", ["guard-checkout.py", "guard-bash.py", "guard-read.py", "guard-records.py"])
def test_a_guard_that_cannot_read_its_input_refuses_the_call(tmp_path: Path, name: str):
    """Item 7a: exit 1 lets the call through (hooks.md:840 in the facts file); a PreToolUse guard exits 2 on any
    exception, and says which hook refused."""
    env = {"HARNESS_RUN_DIR": str(tmp_path / "runs" / "r1"), "HARNESS_WORKTREE": "r1-plan",
           "CLAUDE_PROJECT_DIR": str(tmp_path / "repo")}  # fmt: skip
    res = subprocess.run(
        [sys.executable, str(HOOKS / name)], input="", capture_output=True, text=True, check=False,
        env={"PATH": "/usr/bin:/bin", **env},
    )  # fmt: skip
    assert res.returncode == 2 and res.stderr.startswith(f"{name.split('.')[0]}: ")  # the hook's, not a missing file's


EXAMPLE = HOOKS.parent / "skills" / "running-specagent-pipelines" / "example"
READ_GUARD = 'python3 "<checkout>/.claude/hooks/guard-read.py"'
RECORDS_GUARD = 'python3 "<checkout>/.claude/hooks/guard-records.py"'
LOG = "STATUS: building Task 2\nTask 1: done — abc1234\nV1: fixed — def5678\n"


def read_call(path: Path, cwd: Path | None = None, **tool_input) -> dict:
    """The PreToolUse input of a Read of `path` (a relative path is read from `cwd`)."""
    folder = cwd or (path.parent if path.is_absolute() else Path("/"))
    return {"tool_name": "Read", "tool_input": {"file_path": str(path), **tool_input}, "cwd": str(folder)}


@pytest.mark.parametrize(
    ("size", "tool_input", "expect"),
    [
        (25_000, {}, "deny"),
        (25_000, {"limit": 40}, "allow"),
        (25_000, {"offset": 300}, "allow"),
        (25_000, {"pages": "1-3"}, "allow"),  # a PDF's range
        (20_001, {}, "deny"),
        (20_000, {}, "allow"),  # over 20,000 bytes is refused, not 20,000
        (2_000, {}, "allow"),
    ],
)
def test_the_read_guard_refuses_a_whole_read_of_a_file_over_20_000_bytes(tmp_path, size, tool_input, expect):
    path = tmp_path / "notes.md"
    path.write_text("x" * size, encoding="utf-8")
    assert run_hook("guard-read.py", read_call(path, **tool_input), {}) == expect


def test_the_read_guard_says_how_to_read_by_range_and_reads_a_relative_path_from_the_cwd(tmp_path: Path):
    (tmp_path / "notes.md").write_text("x" * 25_000, encoding="utf-8")
    res = subprocess.run(
        [sys.executable, str(HOOKS / "guard-read.py")], input=json.dumps(read_call(Path("notes.md"), tmp_path)),
        capture_output=True, text=True, check=False, env={"PATH": "/usr/bin:/bin"},
    )  # fmt: skip
    out = json.loads(res.stdout)["hookSpecificOutput"]
    assert (res.returncode, out["hookEventName"], out["permissionDecision"]) == (0, "PreToolUse", "deny")
    assert out["permissionDecisionReason"] == "read by range: grep -n first, then offset and limit"


def test_the_read_guard_lets_through_a_missing_file_a_folder_and_an_image(tmp_path: Path):
    # Read reports a missing file itself; an image or a folder has no lines to cut by offset and limit
    (tmp_path / "shot.png").write_bytes(b"\x89PNG" + b"\0" * 30_000)
    for path in (tmp_path / "gone.md", tmp_path, tmp_path / "shot.png"):
        assert run_hook("guard-read.py", read_call(path), {}) == "allow", path.name


@pytest.mark.parametrize(("matcher", "command"), [("Read", READ_GUARD), ("Write|Edit", RECORDS_GUARD)])
def test_every_role_settings_file_runs_the_pipeline_guards_and_the_project_settings_do_not(matcher, command):
    files = sorted(EXAMPLE.glob("*-settings.json"))
    assert len(files) == 7
    for path in files:
        groups = json.loads(path.read_text(encoding="utf-8")).get("hooks", {}).get("PreToolUse", [])
        wired = [h for g in groups if g.get("matcher") == matcher for h in g.get("hooks", [])]
        assert {"type": "command", "command": command, "timeout": 10} in wired, path.name
    hook = command.rsplit("/", 1)[1].split(".")[0]
    assert hook not in (HOOKS.parent / "settings.json").read_text(encoding="utf-8")  # the owner's sessions


def record_call(path: Path, tool: str, **tool_input) -> dict:
    """The PreToolUse input of a Write or an Edit of `path`."""
    return {"tool_name": tool, "tool_input": {"file_path": str(path), **tool_input}, "cwd": str(path.parent)}


@pytest.mark.parametrize(
    ("tool", "tool_input", "expect"),
    [
        ("Write", {"content": LOG + "Task 2: done — 0123abc\n"}, "allow"),  # appended
        ("Write", {"content": LOG.replace("building Task 2", "done")}, "allow"),  # the STATUS line changed
        ("Write", {"content": LOG.replace("Task 1: done — abc1234\n", "")}, "deny"),  # a deleted line
        ("Write", {"content": "STATUS: done\n"}, "deny"),  # a shortened Write
        ("Write", {"content": LOG.replace("abc1234", "abc9999")}, "deny"),  # a rewritten line
        ("Edit", {"old_string": "building Task 2", "new_string": "done"}, "allow"),  # inside line 1
        ("Edit", {"old_string": "def5678\n", "new_string": "def5678\nV2: fixed — 0a1b2c3\n"}, "allow"),  # added
        ("Edit", {"old_string": "V1: fixed — def5678\n", "new_string": ""}, "deny"),  # a deleted line
        ("Edit", {"old_string": "Task", "new_string": "Item", "replace_all": True}, "deny"),  # line 1 and line 2
    ],
)
def test_the_records_guard_lets_a_record_grow_and_its_status_line_change(tmp_path, tool, tool_input, expect):
    path = tmp_path / "build-log-b.md"
    path.write_text(LOG, encoding="utf-8")
    assert run_hook("guard-records.py", record_call(path, tool, **tool_input), {}) == expect


@pytest.mark.parametrize(
    "name",
    ["build-log.md", "build-log-a.md", "fixer-log-odd.md", "verify.md", "critique.md", "critique-response.md",
     "plan-log.md", "lessons.md", "judge.md"],
)  # fmt: skip
def test_every_record_is_known_by_its_name(tmp_path: Path, name: str):
    path = tmp_path / name
    path.write_text(LOG, encoding="utf-8")
    assert run_hook("guard-records.py", record_call(path, "Write", content="STATUS: done\n"), {}) == "deny"


def test_the_records_guard_lets_a_new_record_and_a_file_that_is_no_record_be_written(tmp_path: Path):
    other = tmp_path / "notes.md"
    other.write_text(LOG, encoding="utf-8")
    for path in (tmp_path / "verify.md", other):
        assert run_hook("guard-records.py", record_call(path, "Write", content="STATUS: x\n"), {}) == "allow"


@pytest.mark.parametrize(("name", "second"), [("judge.md", "VERDICT: pending"), ("critique.md", "Reviewed: 4, 6")])
def test_the_verdict_and_the_lane_list_on_line_2_change_as_the_status_line_does(tmp_path, name, second):
    # B6: judge.md's line 2 is the verdict (judge-assignment.md:44, :70), critique.md's the lanes' list (critic :23-24)
    path = tmp_path / name
    path.write_text(f"STATUS: x\n{second}\n## Task 1\n", encoding="utf-8")
    field = second.split(":")[0]
    calls = [
        ("Write", {"content": f"STATUS: done\n{field}: release\n## Task 1\n## Task 2\n"}, "allow"),
        ("Edit", {"old_string": second, "new_string": f"{field}: 5"}, "allow"),
        ("Write", {"content": f"STATUS: done\n{field}: release\n## Task 3\n"}, "deny"),  # line 3 rewritten
    ]
    assert [run_hook("guard-records.py", record_call(path, t, **i), {}) for t, i, _ in calls] == [e for *_, e in calls]
    plain = tmp_path / "verify.md"  # no other record has a line 2 that may change
    plain.write_text(f"STATUS: x\n{second}\n## Task 1\n", encoding="utf-8")
    assert run_hook("guard-records.py", record_call(plain, "Edit", old_string=second, new_string="x"), {}) == "deny"
