#!/usr/bin/env python3
"""code-intel: install the plugin's language servers into its data directory, on their own.

The SessionStart hook runs this file. When the servers of the pinned versions are in place it returns at once;
otherwise it starts the installation in the background and returns, so that no session waits for it. A server that is
not there yet fails to start, and Claude Code starts it again the next time a file of its language is edited.

    python3 ensure.py               the hook: check, and install in the background when something is missing
    python3 ensure.py --wait        install in the foreground: a new project, a first setup on a machine
    python3 ensure.py --check       print what is installed as JSON; exit 1 when something is missing
    python3 ensure.py --probe       start every server of .lsp.json and ask it to initialize; exit 1 when one does not answer
    python3 ensure.py --print-data  print the data directory: the lsp wrapper asks it when Claude Code gives none

Everything is fetched by its pinned version (toolchain/) and checked: uv from PyPI against its published hash, only
when the machine has none; node and clangd as Python wheels, through uv; the servers from npm with the lock file.
Nothing outside the data directory changes except the download caches of uv and npm. Native Windows is not served:
the servers run in WSL2, where this file sees Linux.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import select
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # the plugin
# Every executable the installation must leave behind, and where: the Python environment or npm's bin directory.
EXECUTABLES = {
    "node": "venv",
    "clangd": "venv",
    "pyright-langserver": "npm",
    "typescript-language-server": "npm",
    "intelephense": "npm",
    "vscode-html-language-server": "npm",
    "vscode-css-language-server": "npm",
}
# The pinned versions. They are not at the plugin root: Claude Code would run npm on a package.json there when it
# installs the plugin, with the machine's node, which a machine may not have.
PINNED = ("toolchain/versions.json", "toolchain/package.json", "toolchain/package-lock.json")


def plugin_data_id() -> str:
    """Claude Code's name for the plugin's data directory: code-intel-<marketplace>. In the repository the
    marketplace is named in plugins/.claude-plugin/marketplace.json beside the plugin; in Claude Code's cache by the
    folder above the plugin's (cache/<marketplace>/code-intel/<version>)."""
    market = ROOT.parent / ".claude-plugin" / "marketplace.json"
    name = json.loads(market.read_text(encoding="utf-8"))["name"] if market.is_file() else ROOT.parent.parent.name
    return f"code-intel-{name}"


def data_dir(given: str | None = None) -> Path:
    """The plugin's data directory: Claude Code passes it to the hook; a script started by hand computes it."""
    if given:
        return Path(given)
    if os.environ.get("CLAUDE_PLUGIN_DATA"):
        return Path(os.environ["CLAUDE_PLUGIN_DATA"])
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    return config / "plugins" / "data" / plugin_data_id()


def native_windows() -> bool:
    return os.name == "nt"


def platform_tag() -> str:
    """What the installed binaries depend on: the system, the processor, and the Python the environment was made from."""
    return f"{sys.platform}-{platform.machine().lower()}-py{sys.version_info[0]}.{sys.version_info[1]}"


def wanted() -> str:
    h = hashlib.sha256()
    for name in PINNED:
        h.update((ROOT / name).read_bytes())
    h.update(platform_tag().encode())
    return h.hexdigest()


def locations(data: Path) -> dict[str, Path]:
    return {
        exe: data / "venv" / "bin" / exe if where == "venv" else data / "node_modules" / ".bin" / exe
        for exe, where in EXECUTABLES.items()
    }


def missing(data: Path) -> list[str]:
    return [exe for exe, path in locations(data).items() if not path.exists()]


def installed(data: Path) -> bool:
    stamp = data / "stamp"
    return stamp.is_file() and stamp.read_text(encoding="utf-8").strip() == wanted() and not missing(data)


def wheel_matches(filename: str) -> bool:
    """A uv wheel built for this machine."""
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        arch = "arm64" if machine in ("arm64", "aarch64") else "x86_64"
        return "macosx" in filename and arch in filename
    if sys.platform.startswith("linux"):
        arch = "aarch64" if machine in ("arm64", "aarch64") else machine.replace("amd64", "x86_64")
        libc = "manylinux" if platform.libc_ver()[0] == "glibc" else "musllinux"
        return libc in filename and arch in filename
    return False


def fetch_uv(data: Path, version: str) -> Path:
    """uv on PATH, or the copy in the data directory, or the pinned wheel from PyPI checked against its hash."""
    found = shutil.which("uv")
    if found:
        return Path(found)
    target = data / "bin" / "uv"
    if target.exists():
        return target
    with urllib.request.urlopen(f"https://pypi.org/pypi/uv/{version}/json", timeout=60) as resp:
        meta = json.load(resp)
    wheels = [f for f in meta["urls"] if f["filename"].endswith(".whl") and wheel_matches(f["filename"])]
    if not wheels:
        raise RuntimeError(f"uv {version} has no wheel for {platform_tag()}")
    with urllib.request.urlopen(wheels[0]["url"], timeout=600) as resp:
        blob = resp.read()
    if hashlib.sha256(blob).hexdigest() != wheels[0]["digests"]["sha256"]:
        raise RuntimeError(f"uv {version}: the download does not match the hash PyPI publishes")
    with zipfile.ZipFile(io.BytesIO(blob)) as wheel:
        member = next(n for n in wheel.namelist() if n.endswith("/scripts/uv"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(wheel.read(member))
    target.chmod(0o755)
    return target


def run(cmd: list[str], log, env: dict | None = None) -> None:
    log.write(f"$ {' '.join(cmd)}\n")
    log.flush()
    done = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, check=False)
    if done.returncode:
        raise RuntimeError(f"`{' '.join(cmd[:3])} ...` ended with exit code {done.returncode}")


def install(data: Path, log) -> None:
    spec = json.loads((ROOT / "toolchain" / "versions.json").read_text(encoding="utf-8"))
    data.mkdir(parents=True, exist_ok=True)
    uv = fetch_uv(data, spec["uv"])
    venv = data / "venv"
    if venv.exists():  # made by another Python, or half made: built again
        shutil.rmtree(venv)
    run([str(uv), "venv", "--quiet", "--python", sys.executable, str(venv)], log)
    pins = [f"{name}=={version}" for name, version in spec["python"].items()]
    run([str(uv), "pip", "install", "--quiet", "--python", str(venv / "bin" / "python"), *pins], log)
    for name in ("package.json", "package-lock.json"):
        shutil.copyfile(ROOT / "toolchain" / name, data / name)
    env = dict(os.environ, PATH=f"{venv / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}")
    npm = [str(venv / "bin" / "npm"), "ci", "--prefix", str(data), "--no-audit", "--no-fund", "--loglevel=error"]
    run(npm, log, env)
    gone = missing(data)
    if gone:
        raise RuntimeError(f"installed, but these are missing: {', '.join(gone)}")
    (data / "stamp").write_text(wanted() + "\n", encoding="utf-8")


def _message(stream, deadline: float) -> dict | None:
    """One JSON-RPC message from a server's stdout, or None when it does not come before the deadline."""
    fd, buf = stream.fileno(), b""
    while b"\r\n\r\n" not in buf:
        if not select.select([fd], [], [], max(0.0, deadline - time.monotonic()))[0]:
            return None
        chunk = os.read(fd, 1)
        if not chunk:
            return None
        buf += chunk
    head, _, rest = buf.partition(b"\r\n\r\n")
    length = int(
        next(v for k, v in (h.split(b":", 1) for h in head.split(b"\r\n")) if k.strip().lower() == b"content-length")
    )
    body = rest
    while len(body) < length:
        if not select.select([fd], [], [], max(0.0, deadline - time.monotonic()))[0]:
            return None
        chunk = os.read(fd, length - len(body))
        if not chunk:
            return None
        body += chunk
    return json.loads(body)


def probe(data: Path, name: str, server: dict, timeout: float = 30.0) -> str | None:
    """Start one server of .lsp.json the way Claude Code does and ask it to initialize. None when it answers."""
    command = server["command"].replace("${CLAUDE_PLUGIN_ROOT}", str(ROOT))
    env = dict(os.environ, CLAUDE_PLUGIN_DATA=str(data), CLAUDE_PLUGIN_ROOT=str(ROOT))
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"processId": os.getpid(), "rootUri": ROOT.as_uri(), "capabilities": {}},
    }
    body = json.dumps(request).encode()
    proc = subprocess.Popen(
        [command, *server.get("args", [])],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        proc.stdin.write(b"Content-Length: %d\r\n\r\n%s" % (len(body), body))
        proc.stdin.flush()
        deadline = time.monotonic() + timeout
        while True:
            msg = _message(proc.stdout, deadline)
            if msg is None:
                err = proc.stderr.read1(2000).decode(errors="replace").strip() if proc.poll() is not None else ""
                return f"{name}: no answer to initialize within {timeout:.0f} s" + (f" ({err})" if err else "")
            if msg.get("id") == 1:
                return None if "capabilities" in (msg.get("result") or {}) else f"{name}: {msg.get('error')}"
    finally:
        proc.kill()
        proc.wait()


def probe_all(data: Path) -> dict[str, str | None]:
    servers = json.loads((ROOT / ".lsp.json").read_text(encoding="utf-8"))
    return {name: probe(data, name, server) for name, server in servers.items()}


def take_lock(data: Path, wait: bool):
    """One installation at a time: role sessions start together."""
    import fcntl

    data.mkdir(parents=True, exist_ok=True)
    handle = open(data / "install.lock", "w", encoding="utf-8")  # noqa: SIM115 - held until the process ends
    try:
        fcntl.flock(handle, fcntl.LOCK_EX if wait else fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def main(argv: list[str]) -> int:
    args = argv[1:]
    given = args[args.index("--data") + 1] if "--data" in args else None
    data = data_dir(given)
    if "--print-data" in args:
        print(data)
        return 0
    if "--probe" in args:
        failed = {name: why for name, why in probe_all(data).items() if why}
        print(json.dumps({"data": str(data), "failed": failed}))
        return 1 if failed else 0
    if "--check" in args:
        report = {"data": str(data), "installed": installed(data), "missing": missing(data), "platform": platform_tag()}
        print(json.dumps(report))
        return 0 if report["installed"] else 1
    if native_windows():
        note = "code-intel: on Windows the language servers run in WSL2; open the project in a WSL2 distribution"
        print(note if "--wait" in args else json.dumps({"systemMessage": note}))
        return 1 if "--wait" in args else 0
    wait = "--wait" in args
    if wait or "--install" in args:
        lock = take_lock(data, wait)
        if lock is None:  # another installation is running
            return 0
        with open(data / "install.log", "a", encoding="utf-8") as log:
            log.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {platform_tag()}\n")
            try:
                if not installed(data):
                    install(data, log)
            except Exception as exc:  # noqa: BLE001 - every failure is reported the same way
                log.write(f"failed: {exc}\n")
                if wait:
                    print(f"code-intel: {exc} (log: {data / 'install.log'})", file=sys.stderr)
                return 1
        if wait:
            print(f"code-intel: language servers in place in {data}")
        return 0
    if installed(data):
        return 0
    data.mkdir(parents=True, exist_ok=True)
    with open(data / "install.log", "a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--install", "--data", str(data)],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    note = (
        "code-intel: the language servers are being installed in the background; the first time takes a few "
        f"minutes. Log: {data / 'install.log'}"
    )
    print(json.dumps({"systemMessage": note}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
