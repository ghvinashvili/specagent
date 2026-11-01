#!/usr/bin/env python3
"""Set up a checkout of this repository on this machine, so that work starts without a manual step.

    python3 ops/bootstrap.py           what the SessionStart hook runs: set up in the background, return at once
    python3 ops/bootstrap.py --wait    the same in the foreground: ops/new-project.py, or a first setup by hand

In this order, each step skipped when it is done already:
1. uv: when the machine has none, the pinned wheel from PyPI, checked against its published hash, into ~/.local/bin.
2. The workspace (`uv sync`), on the machine's python3 when it is new enough, so that the hooks, which run on python3,
   can use its jsonschema.
3. `just`, when it is missing: PyPI's rust-just, pinned, with `uv tool install`, into ~/.local/bin; optional.
4. The git hooks: `core.hooksPath` set to the versioned .githooks/, which refresh the code graph after each commit,
   merge and checkout, unless the checkout names a hooks folder of its own or is not the top of a git repository yet;
   optional.
5. The project plugins of docs/roles/extensions.yaml, installed for this project; then the machine's launch file
   `<config dir>/specagent-launch.json` of the pipeline skill's watcher, whose `plugin_dirs` names the installed directory
   of every plugin of ROLE_PLUGINS, so that every role session loads it (a role under --setting-sources local loads no
   project plugin by itself); optional.
6. The language servers of plugins/code-intel (its own installer, plugins/code-intel/scripts/ensure.py).
7. The sandbox of role sessions, when `.claude/settings.json` enables it: on Linux and WSL2
   `ops/machine-setup.py --auto`, as the SessionStart hook runs it; on macOS the built-in seatbelt (`sandbox-exec`) is
   checked.
8. The first code graph (`bash ops/graph.sh`), when graphify is installed and `wiki/graph/` is not built yet.
9. graphify's skill for Claude Code, when graphify is installed and ~/.claude/skills/graphify/SKILL.md is missing:
   `graphify install --platform claude`, which also appends its four-line block to ~/.claude/CLAUDE.md; optional.
10. The pipeline skill at user level: ~/.claude/skills/running-specagent-pipelines becomes a symbolic link to this
    checkout's .claude/skills/running-specagent-pipelines when it is missing; an existing link or copy is kept, and a
    copy or a dangling link is named in the log with the command that replaces it; optional.
11. `harness doctor`: what is still missing is printed with its fix. Where only the administrator can set the sandbox
    up, the session offers it with one password; the trust record that `claude --bg` needs is written by the launcher
    (harness/trust.py).
Native Windows is not served: the repository runs in WSL2.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_BIN = Path.home() / ".local" / "bin"
LOG = ROOT / ".claude" / "bootstrap.log"
JUST = "rust-just==1.58.0"  # `just` from PyPI (just.systems: `uv tool install rust-just`), pinned like uv
USER_SKILLS = Path.home() / ".claude" / "skills"  # Claude Code's user-level skills; graphify's install writes there too
PIPELINE_SKILL = "running-specagent-pipelines"  # this checkout's .claude/skills/ folder, linked at user level
PLATFORM = sys.platform  # "linux" on Linux and WSL2, "darwin" on macOS; native Windows stops in main()


def _ensure_module():
    sys.dont_write_bytecode = True  # no __pycache__ in the plugin: Claude Code copies the directory when it installs it
    spec = importlib.util.spec_from_file_location(
        "code_intel_ensure", ROOT / "plugins" / "code-intel" / "scripts" / "ensure.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def uv_path() -> Path | None:
    found = shutil.which("uv")
    if found:
        return Path(found)
    local = LOCAL_BIN / "uv"
    return local if local.exists() else None


def needed() -> list[str]:
    """What a session start would set up: cheap checks only."""
    todo = []
    if uv_path() is None:
        todo.append("uv")
    if not (ROOT / ".venv").is_dir():
        todo.append("workspace")
    return todo


def step(name: str, cmd: list[str], log, env: dict | None = None) -> bool:
    log.write(f"$ {' '.join(cmd)}\n")
    log.flush()
    done = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env, check=False)
    if done.returncode:
        log.write(f"{name}: exit code {done.returncode}\n")
    return done.returncode == 0


def project_plugins() -> list[str]:
    """The plugins this repository enables (`harness validate` keeps them equal to docs/roles/extensions.yaml)."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return sorted(key for key, on in settings.get("enabledPlugins", {}).items() if on)


def installed_plugins() -> set[str]:
    out = subprocess.run(["claude", "plugin", "list", "--json"], capture_output=True, text=True, check=False)
    if out.returncode:
        return set()
    here = str(ROOT)
    return {p["id"] for p in json.loads(out.stdout) if p.get("scope") != "project" or p.get("projectPath") == here}


def install_plugins(log) -> list[str]:
    """The project's plugins that are not installed for this checkout. The internal marketplace is known to Claude Code
    by its name for the whole machine, so it is pointed at this checkout first; Claude Code then rewrites
    .claude/settings.json in its own key order, which is put back when nothing else in it changed."""
    missing = [key for key in project_plugins() if key not in installed_plugins()]
    if not missing:
        return []
    settings = ROOT / ".claude" / "settings.json"
    before = settings.read_text(encoding="utf-8")
    market = json.loads((ROOT / "plugins" / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))["name"]
    known = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "plugins" / "known_marketplaces.json"
    source = json.loads(known.read_text(encoding="utf-8")).get(market, {}).get("source", {}) if known.is_file() else {}
    if source.get("path") != str(ROOT / "plugins"):
        step(market, ["claude", "plugin", "marketplace", "add", str(ROOT / "plugins")], log)
    step(market, ["claude", "plugin", "marketplace", "update", market], log)
    failed = [key for key in missing if not step(key, ["claude", "plugin", "install", key, "--scope", "project"], log)]
    if json.loads(settings.read_text(encoding="utf-8")) == json.loads(before):
        settings.write_text(before, encoding="utf-8")
    return failed


LAUNCH_FILE = "specagent-launch.json"  # the pipeline skill's watcher reads it: plugin directories for every role
ROLE_PLUGINS = ("token-optimizer",)  # project plugins every role session loads (the watcher adds --plugin-dir)


def config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def plugin_name(directory: Path) -> str | None:
    try:
        return json.loads((directory / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("name")
    except (OSError, ValueError, AttributeError):
        return None


def installed_dir(name: str) -> Path | None:
    """The newest installed version of a project plugin in Claude Code's cache of the internal marketplace."""
    try:
        market = json.loads((ROOT / "plugins" / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))[
            "name"
        ]
    except (OSError, ValueError, KeyError):
        return None
    base = config_dir() / "plugins" / "cache" / market / name
    versions = [p for p in base.iterdir() if plugin_name(p) == name] if base.is_dir() else []
    versions.sort(key=lambda p: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p.name)])
    return versions[-1] if versions else None


def machine_launch_file(log) -> bool:
    """The watcher's launch file: `plugin_dirs` holds the installed directory of every plugin of ROLE_PLUGINS. Another
    version's directory of the same plugin is replaced, every other entry and key is kept; a plugin that is not
    installed is named in the log. Optional: nothing here fails the setup."""
    path = config_dir() / LAUNCH_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError) as exc:
        log.write(f"launch file: {path} unreadable ({exc}); left alone\n")
        return False
    data = data if isinstance(data, dict) else {}
    dirs = [d for d in data.get("plugin_dirs", []) if isinstance(d, str)]
    found = {name: installed_dir(name) for name in ROLE_PLUGINS}
    for name, directory in found.items():
        if directory is None:
            log.write(f"launch file: {name} is not installed; not added\n")
    wanted = [d for d in dirs if plugin_name(Path(d)) not in ROLE_PLUGINS] + [str(d) for d in found.values() if d]
    if wanted == dirs:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**data, "plugin_dirs": wanted}, indent=2) + "\n", encoding="utf-8")
    log.write(f"launch file: {path} plugin_dirs {wanted}\n")
    return True


def just_path() -> Path | None:
    """`just` on PATH, or in ~/.local/bin, where `uv tool install` puts it."""
    found = shutil.which("just")
    if found:
        return Path(found)
    local = LOCAL_BIN / "just"
    return local if local.exists() else None


def install_just(uv: Path, log) -> None:
    """Install `just` with uv when it is missing. Optional: a failure is in the log, and doctor names the fix."""
    if just_path() is None:
        step("just", [str(uv), "tool", "install", JUST], log)


def hooks_path() -> str | None:
    """The checkout's `core.hooksPath` (`git config --local`), or None when it is unset."""
    done = subprocess.run(
        ["git", "-C", str(ROOT), "config", "--local", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.stdout.strip() or None


def git_top() -> Path | None:
    """The top of the git repository that holds ROOT (`git rev-parse --show-toplevel`), or None outside one."""
    done = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False
    )
    return Path(done.stdout.strip()).resolve() if done.returncode == 0 else None


def git_hooks(log) -> None:
    """Point git at the versioned .githooks/ once per checkout; a hooks folder the checkout names itself is kept, and
    a folder that is not the top of a git repository yet gets nothing."""
    if git_top() != ROOT:
        log.write(f"hooks: {ROOT} is not the top of a git repository yet; nothing set\n")
        return
    current = hooks_path()
    if current is None:
        step("hooks", ["git", "-C", str(ROOT), "config", "--local", "core.hooksPath", ".githooks"], log)
    elif current != ".githooks":
        log.write(f"hooks: core.hooksPath is {current}, kept; the graph is then refreshed by just graph only\n")


def sandbox(log) -> bool:
    """The sandbox of role sessions, when .claude/settings.json enables it: ops/machine-setup.py --auto on Linux and
    WSL2, the built-in seatbelt on macOS."""
    settings = ROOT / ".claude" / "settings.json"
    if not (settings.is_file() and json.loads(settings.read_text(encoding="utf-8")).get("sandbox", {}).get("enabled")):
        log.write("sandbox: .claude/settings.json does not enable it; nothing to set up\n")
        return True
    if PLATFORM == "linux":
        return step("sandbox", [sys.executable, str(ROOT / "ops" / "machine-setup.py"), "--auto"], log)
    if PLATFORM == "darwin" and shutil.which("sandbox-exec") is None:
        log.write("sandbox: sandbox-exec is not on PATH, so the built-in sandbox of macOS is missing\n")
        return False
    return True


def build_graph(log) -> bool:
    """The first code graph of this checkout (ops/graph.sh); True when built, already there, or graphify is missing."""
    if shutil.which("graphify") is None:
        log.write(
            "graph: graphify is not installed; bash ops/graph.sh builds the graph once it is "
            "(uv tool install graphifyy==0.9.64)\n"
        )
        return True
    if (ROOT / "wiki" / "graph" / "index.md").exists():
        return True
    return step("graph", ["bash", str(ROOT / "ops" / "graph.sh")], log)


def install_graphify_skill(log) -> None:
    """graphify's skill for Claude Code, at user level, when graphify is installed and the skill is not. Optional."""
    graphify = shutil.which("graphify")
    if graphify and not (USER_SKILLS / "graphify" / "SKILL.md").is_file():
        step("graphify-skill", [graphify, "install", "--platform", "claude"], log)


def link_user_skill(log) -> None:
    """The pipeline skill at user level as a link to this checkout's; an existing link or copy is kept. Optional."""
    source = ROOT / ".claude" / "skills" / PIPELINE_SKILL
    link = USER_SKILLS / PIPELINE_SKILL
    if not source.is_dir() or (link.is_symlink() and link.exists()):
        return
    if link.is_symlink():
        log.write(
            f"skill: {link} -> {os.readlink(link)} is dangling, kept; ln -sfn {source} {link} makes it the link\n"
        )
        return
    if link.exists():
        log.write(f"skill: {link} is a copy, kept; mv {link} {link}.old && ln -s {source} {link} makes it the link\n")
        return
    try:
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(source, target_is_directory=True)
        log.write(f"skill: {link} -> {source}\n")
    except OSError as exc:
        log.write(f"skill: {link} not linked: {exc}\n")


def setup(log) -> list[str]:
    """Every step; returns what failed."""
    failed = []
    log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} bootstrap {ROOT}\n")
    ensure = _ensure_module()
    uv = uv_path()
    if uv is None:
        try:
            uv = ensure.fetch_uv(
                Path.home() / ".local",
                json.loads(
                    (ROOT / "plugins" / "code-intel" / "toolchain" / "versions.json").read_text(encoding="utf-8")
                )["uv"],
            )
        except Exception as exc:  # noqa: BLE001
            log.write(f"uv: {exc}\n")
            return ["uv"]
    python = shutil.which("python3")
    sync = [str(uv), "sync", "--quiet"]
    if not (ROOT / ".venv").is_dir() and python and sys.version_info >= (3, 12):
        sync += ["--python", python]
    if not step("workspace", sync, log):
        failed.append("workspace")
    install_just(uv, log)
    git_hooks(log)
    if shutil.which("claude"):
        failed += install_plugins(log)
        machine_launch_file(log)
    else:
        failed.append("claude")
    data = ensure.data_dir()
    if not step(
        "code-intel",
        [sys.executable, str(ROOT / "plugins" / "code-intel" / "scripts" / "ensure.py"), "--wait", "--data", str(data)],
        log,
    ):
        failed.append("code-intel")
    if not sandbox(log):
        failed.append("sandbox")
    if not build_graph(log):
        failed.append("graph")
    install_graphify_skill(log)
    link_user_skill(log)
    return failed


def report(failed: list[str]) -> int:
    uv = uv_path()
    doctor = (
        subprocess.run(
            [str(uv), "run", "--quiet", "harness", "doctor"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        if uv
        else None
    )
    lines = [f"set up: {ROOT}"] if not failed else [f"not set up: {', '.join(failed)} (log: {LOG})"]
    if doctor and doctor.stdout.strip().startswith("{"):
        checks = json.loads(doctor.stdout)["checks"]
        lines += [f"- {c['name']}: {c.get('fix', '')}" for c in checks if not c["ok"] and c.get("required")]
    if uv and not shutil.which("uv"):
        lines.append(f"uv is in {uv.parent}; a new terminal finds it once that directory is on PATH")
    print("\n".join(lines))
    return 1 if failed else 0


def native_windows() -> bool:
    return os.name == "nt"


def main(argv: list[str]) -> int:
    if native_windows():
        print("this repository runs in WSL2 on Windows: open it in a WSL2 distribution")
        return 1
    LOG.parent.mkdir(parents=True, exist_ok=True)
    if "--wait" in argv:
        import fcntl

        with open(ROOT / ".claude" / "bootstrap.lock", "w", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)  # sessions that start together set up one after the other
            with open(LOG, "a", encoding="utf-8") as log:
                failed = setup(log)
            return report(failed)
    with open(LOG, "a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--wait"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
