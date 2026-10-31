"""The two code-hygiene hooks: format-on-edit.py runs ruff on the Python file Claude changed, test-alongside.py warns
when a new source file has no test that names it. Each test feeds a hook its JSON on stdin and reads what it prints."""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
RUFF = Path(sys.executable).parent / "ruff"  # the dev group's ruff beside the interpreter `uv run pytest` uses


def run_hook(name: str, payload: dict, path: str = "/usr/bin:/bin", env: dict | None = None) -> tuple[int, dict | None]:
    res = subprocess.run(
        [sys.executable, str(HOOKS / name)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": path, **(env or {})},
        check=False,
    )
    return res.returncode, (json.loads(res.stdout) if res.stdout.strip() else None)


def edited(root: Path, rel: str, tool: str = "Edit") -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": str(root / rel)},
        "cwd": str(root),
    }


def written(root: Path, rel: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(root / rel), "content": "x = 1\n"},
        "cwd": str(root),
    }


def project(root: Path, files: dict[str, str], ruff: bool = True) -> Path:
    files = {"pyproject.toml": '[tool.ruff]\nline-length = 120\nextend-exclude = ["vendor"]\n', **files}
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    if ruff:
        (root / ".venv" / "bin").mkdir(parents=True)
        (root / ".venv" / "bin" / "ruff").symlink_to(RUFF)
    return root


def test_format_on_edit_formats_the_python_file_claude_changed(tmp_path):
    root = project(tmp_path, {"pkg/mod.py": "x=1\n", "pkg/new.py": "y  =  [1,2]\n"})
    assert run_hook("format-on-edit.py", edited(root, "pkg/mod.py")) == (0, None)
    assert run_hook("format-on-edit.py", edited(root, "pkg/new.py", tool="Write")) == (0, None)
    assert (root / "pkg/mod.py").read_text() == "x = 1\n"
    assert (root / "pkg/new.py").read_text() == "y = [1, 2]\n"


def test_format_on_edit_leaves_other_files_excluded_paths_and_other_folders_alone(tmp_path):
    root = project(tmp_path / "p", {"notes.md": "x=1\n", "vendor/v.py": "x=1\n", "data.json": '{"a":1}\n'})
    outside = tmp_path / "elsewhere.py"
    outside.write_text("x=1\n")
    for rel in ("notes.md", "vendor/v.py", "data.json", "../elsewhere.py", "pkg/gone.py"):
        assert run_hook("format-on-edit.py", edited(root, rel)) == (0, None), rel
    assert [(root / rel).read_text() for rel in ("notes.md", "vendor/v.py")] == ["x=1\n", "x=1\n"]
    assert outside.read_text() == "x=1\n"


def test_format_on_edit_tells_claude_when_ruff_cannot_format_the_file(tmp_path):
    root = project(tmp_path, {"pkg/broken.py": "def f(:\n"})
    code, out = run_hook("format-on-edit.py", edited(root, "pkg/broken.py"))
    assert code == 0 and out, (code, out)
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    context = out["hookSpecificOutput"]["additionalContext"]
    head = "format-on-edit: ruff could not format pkg/broken.py: "  # then ruff's first stderr line
    assert context.startswith(head + "error: Failed to parse pkg/broken.py:1:7: "), context
    assert (root / "pkg/broken.py").read_text() == "def f(:\n"


def test_format_on_edit_takes_the_main_checkouts_ruff_else_stays_silent_and_never_runs_uv(tmp_path):
    root = project(tmp_path / "p", {"pkg/mod.py": "x=1\n"}, ruff=False)
    bin_dir, calls = tmp_path / "bin", tmp_path / "calls.txt"
    bin_dir.mkdir()
    for tool in ("uv", "ruff"):  # on the PATH, never called: `uv run` would create and sync .venv (T8-D8)
        fake = bin_dir / tool
        fake.write_text(f'#!/bin/sh\necho "{tool} $*" >> {calls}\n')
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    assert run_hook("format-on-edit.py", edited(root, "pkg/mod.py"), path=f"{bin_dir}:/usr/bin:/bin") == (0, None)
    assert (root / "pkg/mod.py").read_text() == "x=1\n"
    assert not calls.exists() and not (root / ".venv").exists()
    main = project(tmp_path / "main", {})
    tree = project(main / ".claude" / "worktrees" / "w", {"pkg/mod.py": "x=1\n"}, ruff=False)
    assert run_hook("format-on-edit.py", edited(tree, "pkg/mod.py")) == (0, None)
    assert (tree / "pkg/mod.py").read_text() == "x = 1\n"


def test_a_new_source_file_without_a_test_that_names_it_gets_a_warning(tmp_path):
    root = project(
        tmp_path,
        {
            "packages/demo/src/demo/__init__.py": "",
            "packages/demo/tests/test_other.py": "from demo import refresh, fresh_start\n",
            "ops/tests/test_tools.py": "TOOLS = ['tool-kit', 'retool']\n",
            "packages/game/tests/test_other.cpp": "// boardgame\n",
        },
        ruff=False,
    )
    for rel, tests in (
        ("packages/demo/src/demo/fresh.py", "packages/demo/tests"),
        ("ops/tool.py", "ops/tests"),
        ("packages/game/src/board.cpp", "packages/game/tests"),
    ):
        code, out = run_hook("test-alongside.py", written(root, rel))
        assert code == 0 and out, rel
        hso = out["hookSpecificOutput"]
        assert hso["hookEventName"] == "PreToolUse"
        assert "permissionDecision" not in hso  # a warning, never a decision
        assert f"no test under {tests} names {Path(rel).stem}" in hso["additionalContext"]


def test_a_new_source_file_named_by_a_test_passes_silently(tmp_path):
    root = project(
        tmp_path,
        {
            "packages/demo/tests/unit/test_x.py": "from demo import fresh\n",
            "packages/demo/tests/test_deep.py": "from demo.sub.deep import f\n",
            "ops/tests/test_tool.py": 'TOOL = OPS / "tool.py"\n',
            "ops/tests/test_split_large.py": "",
            "packages/web/tests/turn.test.ts": "",
            "packages/web/tests/e2e/menu.spec.tsx": "",
            "packages/game/tests/board_test.cc": "",
        },
        ruff=False,
    )
    for rel in (
        "packages/demo/src/demo/fresh.py",
        "packages/demo/src/demo/sub/deep.py",
        "ops/tool.py",
        "ops/split_large.py",
        "packages/web/src/turn.ts",
        "packages/web/src/menu.tsx",
        "packages/game/src/board.hpp",
    ):
        assert run_hook("test-alongside.py", written(root, rel)) == (0, None), rel


def test_other_writes_pass_test_alongside_silently(tmp_path):
    root = project(
        tmp_path / "p",
        {"packages/demo/src/demo/old.py": "x = 1\n", "ops/old.py": "x = 1\n", "packages/demo/tests/conftest.py": ""},
        ruff=False,
    )
    for rel in (
        "packages/demo/src/demo/old.py",
        "ops/old.py",
        "packages/demo/src/demo/__init__.py",
        "packages/demo/src/demo/types.pyi",
        "packages/demo/src/styles.css",
        "packages/demo/src/CMakeLists.txt",
        "packages/demo/tests/test_new.py",
        "ops/tests/helper.py",
        "ops/sub/tool.py",
        "ops/run.sh",
        "docs/new.md",
        "../outside.py",
    ):
        assert run_hook("test-alongside.py", written(root, rel)) == (0, None), rel


def test_the_project_directory_is_the_root_when_the_session_has_moved_into_a_subfolder(tmp_path):
    root = project(tmp_path, {"pkg/__init__.py": "", "ops/mod.py": "x=1\n", "ops/tests/test_other.py": ""})
    moved, env = {"cwd": str(root / "pkg")}, {"CLAUDE_PROJECT_DIR": str(root)}
    assert run_hook("format-on-edit.py", {**edited(root, "ops/mod.py"), **moved}, env=env) == (0, None)
    assert (root / "ops/mod.py").read_text() == "x = 1\n"
    code, out = run_hook("test-alongside.py", {**written(root, "ops/tool.py"), **moved}, env=env)
    assert code == 0 and out, (code, out)
    assert "no test under ops/tests names tool" in out["hookSpecificOutput"]["additionalContext"]


def test_the_two_hooks_are_registered_in_the_project_settings():
    hooks = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]
    want = {"PostToolUse": ("Edit|Write", "format-on-edit.py"), "PreToolUse": ("Write", "test-alongside.py")}
    for event, (matcher, name) in want.items():
        commands = [h for g in hooks[event] if g.get("matcher") == matcher for h in g["hooks"]]
        mine = [h for h in commands if h["command"] == f'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/{name}']
        assert len(mine) == 1 and mine[0]["type"] == "command" and 0 < mine[0]["timeout"] <= 30, event
        assert os.access(HOOKS / name, os.R_OK)
