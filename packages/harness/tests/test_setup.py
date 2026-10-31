"""A checkout sets itself up: plugins/code-intel/scripts/ensure.py, ops/bootstrap.py, the SessionStart hook and the
checks of `harness doctor` (docs/decisions/0009-a-checkout-sets-itself-up.md). Nothing here downloads anything."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from harness import doctor

REPO = Path(__file__).resolve().parents[3]
PLUGIN = REPO / "plugins" / "code-intel"


def load(path: Path, name: str):
    sys.dont_write_bytecode = True  # Claude Code copies the plugin directory as it is
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def ensure():
    return load(PLUGIN / "scripts" / "ensure.py", "code_intel_ensure")


@pytest.fixture()
def bootstrap():
    return load(REPO / "ops" / "bootstrap.py", "ops_bootstrap")


def test_every_language_server_starts_through_the_launcher_and_is_one_the_installer_leaves_behind(ensure):
    servers = json.loads((PLUGIN / ".lsp.json").read_text(encoding="utf-8"))
    assert set(servers) == {"pyright", "typescript", "intelephense", "clangd", "html", "css"}
    for server in servers.values():
        assert server["command"] == "${CLAUDE_PLUGIN_ROOT}/scripts/lsp"
        assert server["args"][0] in ensure.EXECUTABLES
    assert (PLUGIN / "scripts" / "lsp").stat().st_mode & 0o111
    # pinned versions live below the plugin root: Claude Code runs npm on a package.json at the root when it installs
    assert not (PLUGIN / "package.json").exists() and (PLUGIN / "toolchain" / "package-lock.json").is_file()


def test_a_changed_pin_asks_for_a_new_installation(ensure, tmp_path: Path, monkeypatch):
    copy = tmp_path / "code-intel"
    shutil.copytree(PLUGIN, copy, ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.setattr(ensure, "ROOT", copy)
    data = tmp_path / "data"
    for exe, path in ensure.locations(data).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(exe)
    (data / "stamp").write_text(ensure.wanted() + "\n")
    assert ensure.installed(data)
    versions = copy / "toolchain" / "versions.json"
    spec = json.loads(versions.read_text())
    spec["python"]["clangd"] = "0.0.1"
    versions.write_text(json.dumps(spec))
    assert not ensure.installed(data)


def test_the_uv_wheel_is_the_one_built_for_this_machine(ensure, monkeypatch):
    names = [
        "uv-1-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
        "uv-1-py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl",
        "uv-1-py3-none-musllinux_1_1_x86_64.whl",
        "uv-1-py3-none-macosx_10_12_x86_64.whl",
        "uv-1-py3-none-macosx_11_0_arm64.whl",
        "uv-1-py3-none-win_amd64.whl",
    ]

    def pick(system: str, machine: str, libc: str = "glibc") -> list[str]:
        monkeypatch.setattr(ensure.sys, "platform", system)
        monkeypatch.setattr(ensure.platform, "machine", lambda: machine)
        monkeypatch.setattr(ensure.platform, "libc_ver", lambda: (libc, "2.39"))
        return [n for n in names if ensure.wheel_matches(n)]

    assert pick("linux", "x86_64") == [names[0]]
    assert pick("linux", "aarch64") == [names[1]]
    assert pick("linux", "x86_64", libc="") == [names[2]]
    assert pick("darwin", "x86_64") == [names[3]]
    assert pick("darwin", "arm64") == [names[4]]
    assert pick("win32", "AMD64") == []


def test_the_hook_returns_at_once_and_installs_in_the_background_only_what_is_missing(
    ensure, tmp_path: Path, monkeypatch, capsys
):
    started = []
    monkeypatch.setattr(ensure.subprocess, "Popen", lambda cmd, **kw: started.append(cmd))
    data = tmp_path / "data"
    assert ensure.main(["ensure.py", "--data", str(data)]) == 0
    note = json.loads(capsys.readouterr().out)["systemMessage"]
    assert "background" in note and str(data / "install.log") in note
    assert started and started[0][-3:] == ["--install", "--data", str(data)]
    monkeypatch.setattr(ensure, "installed", lambda d: True)
    started.clear()
    assert ensure.main(["ensure.py", "--data", str(data)]) == 0
    assert capsys.readouterr().out == "" and not started


def test_check_names_what_is_missing(ensure, tmp_path: Path, capsys):
    assert ensure.main(["ensure.py", "--check", "--data", str(tmp_path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["installed"] is False and set(report["missing"]) == set(ensure.EXECUTABLES)


def test_native_windows_is_sent_to_wsl2(ensure, bootstrap, tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(ensure, "native_windows", lambda: True)
    assert ensure.main(["ensure.py", "--data", str(tmp_path)]) == 0
    assert "WSL2" in json.loads(capsys.readouterr().out)["systemMessage"]
    monkeypatch.setattr(bootstrap, "native_windows", lambda: True)
    assert bootstrap.main(["bootstrap.py", "--wait"]) == 1
    assert "WSL2" in capsys.readouterr().out
    monkeypatch.setattr(doctor, "_native_windows", lambda: True)
    item = next(c for c in doctor.check(REPO)["checks"] if c["name"] == "the repository runs in WSL2")
    assert item["ok"] is False and item["required"] is True


def test_the_setup_installs_the_plugins_this_repository_enables_and_keeps_the_settings_file_as_it_was(
    bootstrap, tmp_path: Path, monkeypatch
):
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    (root / "plugins" / ".claude-plugin").mkdir(parents=True)
    (root / "plugins" / ".claude-plugin" / "marketplace.json").write_text(json.dumps({"name": "internal"}))
    text = '{\n  "enabledPlugins": {"b@internal": true, "a@internal": true, "off@internal": false},\n  "env": {}\n}\n'
    settings = root / ".claude" / "settings.json"
    settings.write_text(text)
    monkeypatch.setattr(bootstrap, "ROOT", root)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "config"))
    assert bootstrap.project_plugins() == ["a@internal", "b@internal"]
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        if cmd[:3] == ["claude", "plugin", "list"]:
            listed = [{"id": "a@internal", "scope": "project", "projectPath": str(root)}]
            return subprocess.CompletedProcess(cmd, 0, json.dumps(listed), "")
        if cmd[:3] == ["claude", "plugin", "install"]:  # Claude Code writes the file back in its own key order
            settings.write_text(json.dumps(json.loads(text), indent=4, sort_keys=True))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(bootstrap.subprocess, "run", fake_run)
    with open(tmp_path / "log", "w") as log:
        assert bootstrap.install_plugins(log) == []
    assert ["claude", "plugin", "marketplace", "add", str(root / "plugins")] in calls
    assert ["claude", "plugin", "install", "b@internal", "--scope", "project"] in calls
    assert not any(c[:3] == ["claude", "plugin", "install"] and "a@internal" in c for c in calls)
    assert settings.read_text() == text


def run_session_start(root: Path, home: Path, env_file: Path, extra: dict | None = None) -> dict | None:
    res = subprocess.run(
        [sys.executable, str(REPO / ".claude" / "hooks" / "session-start.py")],
        input=json.dumps({"source": "startup"}),
        capture_output=True,
        text=True,
        check=True,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(home),
            "CLAUDE_PROJECT_DIR": str(root),
            "CLAUDE_ENV_FILE": str(env_file),
            **(extra or {}),
        },
    )
    return json.loads(res.stdout) if res.stdout.strip() else None


def test_a_fresh_checkout_starts_its_setup_and_a_set_up_one_does_not(tmp_path: Path):
    root, home, env_file = tmp_path / "repo", tmp_path / "home", tmp_path / "env"
    (root / "ops").mkdir(parents=True)
    marker = tmp_path / "started"
    # the hook imports the script for its trust record, so the stub acts only when it is run
    (root / "ops" / "bootstrap.py").write_text(
        f"if __name__ == '__main__':\n    open({str(marker)!r}, 'w').write('yes')\n"
    )
    home.mkdir()
    note = run_session_start(root, home, env_file)
    assert "Setting up this checkout" in note["systemMessage"]
    for _ in range(50):  # the setup runs detached
        if marker.exists():
            break
        subprocess.run(["sleep", "0.1"], check=True)
    assert marker.read_text() == "yes"
    marker.unlink()
    (root / ".venv").mkdir()
    (home / ".local" / "bin").mkdir(parents=True)
    (home / ".local" / "bin" / "uv").write_text("")
    assert run_session_start(root, home, env_file) is None
    assert not marker.exists()
    # uv in ~/.local/bin, which this shell's PATH lacks, reaches the session's commands
    assert env_file.read_text() == f'export PATH="{home / ".local" / "bin"}:$PATH"\n'


def test_the_sandbox_is_set_up_as_this_user_and_only_what_needs_root_is_asked(tmp_path: Path):
    """The hook writes nothing to ~/.claude.json; where this user can set the sandbox up it starts that in the
    background and says so; where only the administrator can, the session is told what to offer the human."""
    root, home, env_file = tmp_path / "repo", tmp_path / "home", tmp_path / "env"
    (root / "ops").mkdir(parents=True)
    (root / ".venv").mkdir()
    (home / ".local" / "bin").mkdir(parents=True)
    (home / ".local" / "bin" / "uv").write_text("")
    machine = root / "ops" / "machine-setup.py"
    fake = (
        "from pathlib import Path\n"
        f"RECORDS = Path({str(tmp_path / 'records')!r})\n"
        f"USER_BIN = Path({str(home / '.local' / 'bin')!r})\n"
        "WHY_NOT = None\n"
        "SOCAT, NESTED = None, False\n"
        "def facts(root):\n"
        "    return {'linux': True, 'sandbox_enabled': True, 'socat': SOCAT, 'nested_ok': NESTED}\n"
        "def user_plan(f):\n"
        "    work = not (f['socat'] and f['nested_ok'])\n"
        "    return {'bwrap': 'copy' if work and not WHY_NOT else None, 'socat': None, 'why_not': WHY_NOT}\n"
        "def refresh_due(f):\n"
        "    return False\n"
        "def plan(f):\n"
        "    return {'changes': ['installs socat'], 'steps': ['x'], 'undo': [], 'notes': []}\n"
    )
    machine.write_text(fake)
    out = run_session_start(root, home, env_file)
    assert "without a password" in out["systemMessage"] and "hookSpecificOutput" not in out
    assert (tmp_path / "records" / "user-space.log").exists()  # the background run writes its log there
    machine.write_text(fake.replace("WHY_NOT = None", "WHY_NOT = 'restriction'"))
    context = run_session_start(root, home, env_file)["hookSpecificOutput"]["additionalContext"]
    assert "python3 ops/machine-setup.py" in context and "installs socat" in context and "no role session" in context
    machine.write_text(fake.replace("SOCAT, NESTED = None, False", "SOCAT, NESTED = 's', True"))
    assert run_session_start(root, home, env_file) is None  # a sandbox that works: nothing to do or ask
    assert not (home / ".claude.json").exists()


def test_the_launcher_is_told_what_keeps_the_sandbox_from_starting(tmp_path: Path, monkeypatch):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps({"sandbox": {"enabled": True}}))
    monkeypatch.setattr(doctor.sys, "platform", "linux")
    monkeypatch.setattr(doctor.shutil, "which", lambda name, path=None: None if name == "socat" else f"/usr/bin/{name}")
    assert doctor.sandbox_problem(tmp_path) == "socat not on PATH"
    monkeypatch.setattr(doctor.shutil, "which", lambda name, path=None: f"/usr/bin/{name}")
    monkeypatch.setattr(doctor, "nested_userns", lambda b: subprocess.CompletedProcess([], 1, "", "uid_map: denied"))
    assert doctor.sandbox_problem(tmp_path).endswith("uid_map: denied")
    monkeypatch.setattr(doctor, "nested_userns", lambda b: subprocess.CompletedProcess([], 0, "", ""))
    assert doctor.sandbox_problem(tmp_path) is None
    # the PATH of the background service lacks what this process finds: the remedy is a restart of the service
    monkeypatch.setattr(doctor.shutil, "which", lambda name, path=None: None if path == "/svc" else f"/usr/bin/{name}")
    service = doctor.sandbox_problem(tmp_path, "/svc")
    assert service.startswith("bubblewrap and socat not on PATH") and "claude daemon stop --any" in service
    monkeypatch.setattr(doctor.sys, "platform", "darwin")  # macOS has its own sandbox
    monkeypatch.setattr(doctor.shutil, "which", lambda name, path=None: None)
    assert doctor.sandbox_problem(tmp_path) is None


def test_doctor_reports_language_servers_that_are_missing_or_do_not_answer(tmp_path: Path, monkeypatch):
    script = tmp_path / "plugins" / "code-intel" / "scripts" / "ensure.py"
    assert doctor.code_intel(tmp_path)["detail"] == "plugins/code-intel is missing"
    script.parent.mkdir(parents=True)
    script.write_text("")
    answers = {"--check": (1, json.dumps({"missing": ["clangd", "node"]})), "--probe": (0, json.dumps({"failed": {}}))}

    def fake(cmd, timeout=20):
        code, out = answers[cmd[-1]]
        return subprocess.CompletedProcess(cmd, code, out, "")

    monkeypatch.setattr(doctor, "_run", fake)
    item = doctor.code_intel(tmp_path)
    assert item["ok"] is False and item["detail"] == "missing: clangd, node" and item["required"] is False
    answers["--check"] = (0, "{}")
    assert doctor.code_intel(tmp_path)["ok"] is True
    answers["--probe"] = (1, json.dumps({"failed": {"clangd": "clangd: no answer to initialize within 30 s"}}))
    item = doctor.code_intel(tmp_path)
    assert item["ok"] is False and "clangd: no answer" in item["detail"]


def test_code_intel_finds_its_data_directory_by_the_marketplace_it_comes_from(ensure, monkeypatch, tmp_path: Path):
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    assert ensure.data_dir() == tmp_path / "plugins" / "data" / "code-intel-example-repo-plugins"
    cached = tmp_path / "cache" / "acme-plugins" / "code-intel" / "0.1.0"  # Claude Code's plugin cache
    cached.mkdir(parents=True)
    monkeypatch.setattr(ensure, "ROOT", cached)
    assert ensure.plugin_data_id() == "code-intel-acme-plugins"


def test_a_set_up_checkout_turns_its_git_hooks_on_and_keeps_another_hooks_path(tmp_path: Path):
    root, home, env_file = tmp_path / "repo", tmp_path / "home", tmp_path / "env"
    (root / "ops").mkdir(parents=True)
    shutil.copy2(REPO / "ops" / "bootstrap.py", root / "ops" / "bootstrap.py")
    (root / ".githooks").mkdir()
    (root / ".githooks" / "post-commit").write_text("#!/usr/bin/env bash\n")
    (root / ".venv").mkdir()
    (home / ".local" / "bin").mkdir(parents=True)
    (home / ".local" / "bin" / "uv").write_text("")
    quiet = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
    local = ["git", "-C", str(root), "config", "--local"]  # --local: not the -c value of a command line
    assert run_session_start(root, home, env_file, quiet) is None  # not a repository yet: nothing to set
    assert not (root / ".git").exists()
    subprocess.run(
        ["git", "init", "-q", str(root)], check=True, capture_output=True, env={**quiet, "PATH": "/usr/bin:/bin"}
    )
    assert run_session_start(root, home, env_file, quiet) is None
    assert (
        subprocess.run([*local, "core.hooksPath"], capture_output=True, text=True, check=False).stdout == ".githooks\n"
    )
    subprocess.run([*local, "core.hooksPath", ".husky/_"], check=True)
    assert run_session_start(root, home, env_file, quiet) is None
    assert (
        subprocess.run([*local, "core.hooksPath"], capture_output=True, text=True, check=False).stdout == ".husky/_\n"
    )


def test_the_setup_message_names_every_step_of_the_bootstrap(tmp_path: Path):
    root, home, env_file = tmp_path / "repo", tmp_path / "home", tmp_path / "env"
    (root / "ops").mkdir(parents=True)
    (root / "ops" / "bootstrap.py").write_text("")
    home.mkdir()
    message = run_session_start(root, home, env_file)["systemMessage"]
    steps = ("uv", "the workspace", "`just`", "the git hooks", "the plugins", "the language servers", "the sandbox",
             "the first code graph", "graphify's skill", "the user-level pipeline skill")  # fmt: skip
    assert [step for step in steps if step not in message] == [], message
    assert "appends a block to ~/.claude/CLAUDE.md" in message, message
