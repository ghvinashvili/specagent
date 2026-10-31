#!/usr/bin/env python3
"""Set this machine up for the sandbox of role sessions: as this user where that is enough, else with one password.

    python3 ops/machine-setup.py           set up what is missing: as this user where it can, else with one password
    python3 ops/machine-setup.py --user    only what this user can do, also after a decline or a failure
    python3 ops/machine-setup.py --auto    the same as the SessionStart hook runs it: a decline or a recent failure holds
    python3 ops/machine-setup.py --undo    take the user-space copies out and remember the decline
    python3 ops/machine-setup.py --plan    print what either way would change, as JSON, and change nothing

A role session's shell commands run inside Claude Code's sandbox. On Linux and WSL2 the sandbox needs bubblewrap and
socat, and a user namespace inside bubblewrap (Claude Code's seccomp helper makes one for every command). An AppArmor
profile that a distribution puts on bubblewrap can refuse that inner namespace: Zorin OS ships one
(`bwrap-userns-restrict-patched`), Ubuntu offers one (`bwrap-userns-restrict`), and when the sysctl
`kernel.apparmor_restrict_unprivileged_userns` is 1, Ubuntu refuses bubblewrap the namespace altogether. Without the
sandbox Claude Code runs the commands unsandboxed, and nothing says so in the session; a role session's settings hold
`sandbox.failIfUnavailable`, so it does not start at all then.

As this user, without a password: where the kernel lets every program make a user namespace (Ubuntu's restriction is
off, as on Zorin OS, or there is no AppArmor, as in WSL2), a copy of bubblewrap in ~/.local/bin, which comes before
/usr/bin on PATH, is not the file a distribution's profile attaches to and makes the namespace: what any program there
may do already. socat, when it is missing, is unpacked from its Debian package (`apt-get download`, `dpkg-deb -x`) into
the same folder; nothing is installed for the system, and the distribution's profile and the Flatpak applications it
guards stay as they are. Each copy is checked before it moves in. The copies follow the system: a changed
/usr/bin/bwrap is copied again, and once a day a package apt has another version of is unpacked again. A failure is
remembered for a day, and meanwhile the session offers the administrator's way. `--undo` takes the copies out and
remembers the decline; `--user` lifts it.

Where that cannot help (Ubuntu's restriction on, no apt, ~/.local/bin not first on PATH), only the administrator can
install a package or change an AppArmor profile. This script gathers every such change into one shell script and runs
it with one password: in a desktop session `pkexec` opens the system's password window, in a
terminal `sudo` asks there. The script reaches the root shell as an argument (`sh -c`), never as a file this user could
change in between. The changes:
- install `socat`, and `bubblewrap` when it is missing, with the machine's package manager;
- disable every AppArmor profile that attaches to `/usr/bin/bwrap` (a symlink in `/etc/apparmor.d/disable/`, then
  unloaded), and put in its place the profile of Claude Code's documentation (code.claude.com/docs/en/sandboxing, Set up
  Linux and WSL2): bubblewrap may make user namespaces, the commands it runs are not confined by it.
The script that undoes the changes is written beside the record of what was done (`--plan` names the folder).
macOS uses its own sandbox and needs nothing here; native Windows runs the repository in WSL2.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPARMOR = Path("/etc/apparmor.d")
SYSCTL = Path("/proc/sys/kernel/apparmor_restrict_unprivileged_userns")
BWRAP = "/usr/bin/bwrap"
OURS = "bwrap"  # the file name the documentation gives the profile
DOCS_PROFILE = """abi <abi/4.0>,
include <tunables/global>

profile bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
  include if exists <local/bwrap>
}
"""
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")  # a profile file name that goes into the root script
ATTACHES = re.compile(r"^\s*profile\s+\S+\s+/usr/bin/bwrap\b", re.MULTILINE)
INSTALL = {
    "apt-get": "DEBIAN_FRONTEND=noninteractive apt-get install -y {}",
    "dnf": "dnf install -y {}",
    "zypper": "zypper --non-interactive install {}",
    "pacman": "pacman -S --noconfirm --needed {}",
}
RECORDS = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "harness" / "machine-setup"
USER_BIN = Path.home() / ".local" / "bin"
USER_RECORD = RECORDS / "user-space.json"  # what the user-space way put into USER_BIN, from where, last checked when
DAY = 24 * 3600
UNDO = "python3 ops/machine-setup.py --undo"


def nested_userns(bwrap: str) -> subprocess.CompletedProcess:
    """A user namespace inside the sandbox: what Claude Code's seccomp helper needs for every sandboxed command (the
    same probe as `harness doctor`)."""
    cmd = [bwrap, "--unshare-user", "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev"]
    return subprocess.run(
        [*cmd, "unshare", "--user", "--map-root-user", "true"], capture_output=True, text=True, timeout=20, check=False
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def system_bwrap() -> str | None:
    """The system's bubblewrap: the first on PATH outside ~/.local/bin."""
    dirs = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d and Path(d).expanduser() != USER_BIN]
    return shutil.which("bwrap", path=os.pathsep.join(dirs))


def user_bin_first(path: str | None = None) -> bool:
    """Whether ~/.local/bin comes before /usr/bin on PATH: Claude Code finds bwrap and socat on its PATH."""
    dirs = [Path(d).expanduser() for d in (os.environ.get("PATH", "") if path is None else path).split(os.pathsep) if d]
    if USER_BIN not in dirs:
        return False
    return Path("/usr/bin") not in dirs or dirs.index(USER_BIN) < dirs.index(Path("/usr/bin"))


def user_record() -> dict:
    try:
        return json.loads(USER_RECORD.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def sandbox_enabled(root: Path = ROOT) -> bool:
    settings = root / ".claude" / "settings.json"
    if not settings.is_file():
        return False
    return bool(json.loads(settings.read_text(encoding="utf-8")).get("sandbox", {}).get("enabled"))


def bwrap_profiles(apparmor: Path = APPARMOR) -> list[dict]:
    """The AppArmor profile files that attach to /usr/bin/bwrap, with whether each is disabled already."""
    found = []
    if not apparmor.is_dir():
        return found
    disabled = apparmor / "disable"
    for path in sorted(p for p in apparmor.iterdir() if p.is_file()):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if ATTACHES.search(text):
            found.append(
                {
                    "name": path.name,
                    "ours": path.name == OURS and text == DOCS_PROFILE,
                    "disabled": (disabled / path.name).exists(),
                }
            )
    return found


def facts(root: Path = ROOT) -> dict:
    """What decides the plan, read without changing anything."""
    linux = sys.platform.startswith("linux")
    bwrap = shutil.which("bwrap")
    probe = nested_userns(bwrap) if linux and bwrap else None
    restrict = None
    if SYSCTL.is_file():
        try:
            restrict = int(SYSCTL.read_text().strip())
        except ValueError:
            restrict = None
    system = system_bwrap() if linux else None
    return {
        "linux": linux,
        "sandbox_enabled": sandbox_enabled(root),
        "socat": shutil.which("socat"),
        "bwrap": bwrap,
        "system_bwrap_sha": sha256(Path(system)) if system else None,
        "user_bin_first": user_bin_first(),
        "user": user_record(),
        "dpkg_deb": shutil.which("dpkg-deb") is not None,
        "nested_ok": probe is not None and probe.returncode == 0,
        "nested_error": (probe.stderr or probe.stdout).strip()[-300:] if probe is not None else "",
        "restrict_userns": restrict,
        "apparmor": APPARMOR.is_dir() and shutil.which("apparmor_parser") is not None,
        "profiles": bwrap_profiles(),
        "installer": next((name for name in INSTALL if shutil.which(name)), None),
    }


def user_plan(f: dict, now: float | None = None) -> dict:
    """What can be done as this user, without a password: {"bwrap": "copy" | "download" | None, "socat": "download" |
    None, "why_not": why the user-space way cannot help here, or None}. A failure is remembered for a day, or until
    the system's bubblewrap changes, and a decline until `--user`: meanwhile the administrator's way is offered."""
    out: dict = {"bwrap": None, "socat": None, "why_not": None}
    if not f["linux"] or not f["sandbox_enabled"]:
        return out
    ours = str(USER_BIN / "bwrap")
    if f["bwrap"] is None:
        out["bwrap"] = "download"
    elif not f["nested_ok"] and f["bwrap"] != ours:
        out["bwrap"] = "copy"
    if not f["socat"]:
        out["socat"] = "download"
    broken_copy = not f["nested_ok"] and f["bwrap"] == ours
    if not out["bwrap"] and not out["socat"] and not broken_copy:
        return out
    record, now = f["user"], time.time() if now is None else now
    failed = record.get("failed") or {}
    why = None
    if record.get("declined"):
        why = "the human declined it (--undo); `python3 ops/machine-setup.py --user` sets it up again"
    elif failed and failed.get("system_bwrap_sha") == f["system_bwrap_sha"] and now - failed.get("at", 0) < DAY:
        why = f"it failed here less than a day ago: {failed.get('why', '')}"
    elif out["bwrap"] and f["restrict_userns"] == 1:  # unpacking socat needs no namespace
        why = "Ubuntu's restriction lets only a program with an AppArmor profile make a user namespace"
    elif broken_copy:
        why = f"the copy of bubblewrap in {USER_BIN} cannot make the namespace either: {f['nested_error']}"
    elif not f["user_bin_first"]:
        why = f"{USER_BIN} does not come before /usr/bin on PATH, so a copy there would not be found first"
    elif (out["bwrap"] == "download" or out["socat"]) and not (f["installer"] == "apt-get" and f["dpkg_deb"]):
        why = "a package is unpacked as this user only from apt (apt-get download, dpkg-deb)"
    return {"bwrap": None, "socat": None, "why_not": why} if why else out


def stale(f: dict, candidates: dict) -> dict:
    """The copies in ~/.local/bin that no longer follow the system: a copied /usr/bin/bwrap that changed since (an
    update), and a package that apt now has another version of (`candidates`: package -> version)."""
    record, out = f["user"], {}
    copied = record.get("bwrap") or {}
    if copied.get("from") and f["system_bwrap_sha"] and f["system_bwrap_sha"] != copied.get("sha256"):
        out["bwrap"] = "copy"
    for name, package in (("bwrap", "bubblewrap"), ("socat", "socat")):
        entry = record.get(name) or {}
        if entry.get("package") == package and candidates.get(package) not in (None, entry.get("version")):
            out[name] = "download"
    return out


def refresh_due(f: dict, now: float | None = None) -> bool:
    """Whether the hook should start a refresh: copies are there, and the system's bubblewrap changed or a day passed
    since the last check."""
    record = f["user"]
    if not (record.get("bwrap") or record.get("socat")) or record.get("declined"):
        return False
    now = time.time() if now is None else now
    return bool(stale(f, {})) or now - record.get("checked_at", 0) > DAY


def apt_candidate(package: str) -> str | None:
    """The version apt would install now."""
    out = subprocess.run(["apt-cache", "policy", package], capture_output=True, text=True, timeout=60, check=False)
    found = re.search(r"Candidate:\s*(\S+)", out.stdout)
    return found.group(1) if found and found.group(1) != "(none)" else None


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, timeout=300)


def unpack(package: str, member: str, staging: Path) -> tuple[Path, str]:
    """One file of a Debian package, as this user: `apt-get download` fetches the package apt would install and
    `dpkg-deb -x` unpacks it into `staging`; nothing is installed."""
    _run(["apt-get", "download", package], cwd=staging)
    deb = next(staging.glob(f"{package}_*.deb"))
    version = _run(["dpkg-deb", "-f", str(deb), "Version"]).stdout.strip()
    _run(["dpkg-deb", "-x", str(deb), str(staging / package)])
    return staging / package / member, version


def followed(path: Path, root: Path) -> Path:
    """The file a member of an unpacked package names. A member may be a link (socat 1.8 of Ubuntu ships
    `usr/bin/socat` as a link to `socat1`): it is followed inside the package, never out to the machine's own files, and
    the file it names is what is checked and moves in; the link alone would name nothing in ~/.local/bin."""
    base = root.resolve()
    for _ in range(8):
        if not path.is_symlink():
            if not path.resolve().is_relative_to(base):
                raise OSError(f"{path.name} lies outside the unpacked package")
            return path
        target = Path(os.readlink(path))
        path = base / target.relative_to("/") if target.is_absolute() else path.parent / target
    raise OSError(f"{path.name}: a chain of links")


def _put_copies(f: dict, todo: dict, staging: Path, record: dict, done: dict) -> str | None:
    """Stage, check and move in each copy; why it stopped, or None."""
    namespace = f["nested_ok"]
    if todo.get("bwrap"):
        if todo["bwrap"] == "copy":
            source = system_bwrap()
            if source is None:
                return "the system's bubblewrap is not on PATH any more"
            staged = staging / "bwrap"
            shutil.copyfile(source, staged)
            os.chmod(staged, 0o755)
            entry = {"from": source}
        else:
            staged, version = unpack("bubblewrap", "usr/bin/bwrap", staging)
            staged = followed(staged, staging / "bubblewrap")
            entry = {"package": "bubblewrap", "version": version}
        probe = nested_userns(str(staged))
        if probe.returncode != 0:
            return (
                "the copy of bubblewrap cannot make the namespace either: "
                + (probe.stderr or probe.stdout).strip()[-300:]
            )
        entry["sha256"] = sha256(staged)  # the file that moves in: what a refresh compares and --undo recognises
        os.replace(staged, USER_BIN / "bwrap")
        record["bwrap"] = done["bwrap"] = entry
        namespace = True
    if todo.get("socat"):
        if not namespace:
            return "socat waits until a namespace inside bubblewrap works"
        staged, version = unpack("socat", "usr/bin/socat", staging)
        staged = followed(staged, staging / "socat")
        started = subprocess.run([str(staged), "-V"], capture_output=True, text=True, timeout=20, check=False)
        if started.returncode != 0:
            return "socat from its package does not start here: " + (started.stderr or started.stdout).strip()[-300:]
        entry = {"package": "socat", "version": version, "sha256": sha256(staged)}
        os.replace(staged, USER_BIN / "socat")
        record["socat"] = done["socat"] = entry
    return None


def apply_user(f: dict, todo: dict, checked: bool = False) -> dict:
    """Put the copies into ~/.local/bin. Each is checked where it was unpacked, before it moves in: a bubblewrap that
    cannot make the namespace, or a socat that does not start, never reaches PATH. socat moves in only once the
    namespace works: with socat and without it, every command of a role session would fail. A failure is recorded,
    so that the next session start offers the administrator's way instead of trying again at once."""
    USER_BIN.mkdir(parents=True, exist_ok=True)
    RECORDS.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".harness-staging-", dir=USER_BIN))  # one file system: os.replace is atomic
    record, done = dict(f["user"]), {}
    try:
        why = _put_copies(f, todo, staging, record, done)
    except (OSError, subprocess.SubprocessError, StopIteration) as exc:
        why = f"{type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    if why:
        record["failed"] = {"why": why, "at": time.time(), "system_bwrap_sha": f["system_bwrap_sha"]}
    else:
        record.pop("failed", None)
        if checked or "checked_at" not in record:
            record["checked_at"] = time.time()
    USER_RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return {"ok": why is None, **({"why": why} if why else {}), "done": done, "undo": UNDO}


@contextlib.contextmanager
def _locked():
    """One user-space run at a time: two sessions that start together, or an undo while the hook's run unpacks."""
    import fcntl

    RECORDS.mkdir(parents=True, exist_ok=True)
    with open(RECORDS / "user-space.lock", "w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def undo_user() -> dict:
    """Take the copies out of ~/.local/bin, each only when it is still the file this script put there, and remember
    that the human declined the user-space way, so that no session start puts them back."""
    removed, left = [], []
    try:
        with _locked():
            record = user_record()
            for name in ("bwrap", "socat"):
                path, entry = USER_BIN / name, record.get(name) or {}
                if path.is_file() and entry.get("sha256") and sha256(path) == entry["sha256"]:
                    path.unlink()
                    removed.append(str(path))
                elif path.exists():
                    left.append(str(path))  # not the file this script put there
            USER_RECORD.write_text(json.dumps({"declined": {"at": time.time()}}, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:  # a sandboxed command may not write there: the command runs outside it by its exact name
        return {"ok": False, "why": f"{type(exc).__name__}: {exc}", "removed": removed}
    return {"ok": True, "removed": removed, "left_alone": left, "again": "python3 ops/machine-setup.py --user"}


def main_user(explicit: bool = True) -> dict:
    """The user-space way, under a lock: two sessions that start together do it once. An explicit run (`--user`)
    lifts a decline and a remembered failure; the hook's run (`--auto`) respects both."""
    with _locked():
        f = facts()
        if explicit and (f["user"].get("declined") or f["user"].get("failed")):
            kept = {k: v for k, v in f["user"].items() if k not in ("declined", "failed")}
            USER_RECORD.write_text(json.dumps(kept, indent=2) + "\n", encoding="utf-8")
            f = facts()
        way = user_plan(f)
        if way["why_not"]:
            return {"ok": False, "why_not": way["why_not"]}
        checked = bool(f["user"]) and time.time() - f["user"].get("checked_at", 0) > DAY
        packages = {(f["user"].get(n) or {}).get("package") for n in ("bwrap", "socat")} - {None}
        candidates = {p: apt_candidate(p) for p in sorted(packages)} if checked else {}
        todo = {**stale(f, candidates), **{k: v for k, v in way.items() if k != "why_not" and v}}
        result = apply_user(f, todo, checked) if todo or checked else {"ok": True, "done": {}}
        after = facts()
        return {**result, "sandbox_works": bool(after["socat"] and after["nested_ok"])}


def plan(f: dict) -> dict:
    """The root steps that make the sandbox work, in words and as commands, the steps that undo them, and what cannot
    be done here."""
    steps: list[str] = []
    undo: list[str] = []
    changes: list[str] = []
    notes: list[str] = []
    if not f["linux"]:
        notes.append("nothing to do: the sandbox needs no setup outside Linux and WSL2")
        return {"changes": changes, "steps": steps, "undo": undo, "notes": notes}
    if not f["sandbox_enabled"]:
        notes.append("nothing to do: this repository does not enable the sandbox")
        return {"changes": changes, "steps": steps, "undo": undo, "notes": notes}
    apparmor_fix = False
    if f["bwrap"] and not f["nested_ok"]:
        theirs = [p for p in f["profiles"] if not p["ours"] and not p["disabled"]]
        unsafe = [p["name"] for p in theirs if not SAFE_NAME.match(p["name"])]
        theirs = [p for p in theirs if SAFE_NAME.match(p["name"])]
        have_ours = any(p["ours"] for p in f["profiles"])
        if unsafe:
            notes.append(f"profiles left alone, their names are not plain file names: {unsafe}")
        if not f["apparmor"] or not (theirs or (f["restrict_userns"] == 1 and not have_ours)):
            notes.append(f"a namespace inside bubblewrap is refused for a reason not known here: {f['nested_error']}")
        else:
            apparmor_fix = True
            if theirs:
                steps.append("mkdir -p /etc/apparmor.d/disable")
                changes.append(
                    "disables the AppArmor profile "
                    + ", ".join(p["name"] for p in theirs)
                    + " on bubblewrap, which refuses the sandbox the namespace it makes inside bubblewrap"
                )
            for p in theirs:
                steps += [
                    f"ln -sf /etc/apparmor.d/{p['name']} /etc/apparmor.d/disable/{p['name']}",
                    f"apparmor_parser -R /etc/apparmor.d/{p['name']} || true",
                ]
                undo += [
                    f"rm -f /etc/apparmor.d/disable/{p['name']}",
                    f"apparmor_parser -r /etc/apparmor.d/{p['name']}",
                ]
            if any(p["name"] == OURS for p in theirs):
                notes.append(f"/etc/apparmor.d/{OURS} holds another profile: it is disabled and not overwritten")
            elif not have_ours:
                steps += [
                    f"cat > /etc/apparmor.d/{OURS} <<'PROFILE'\n{DOCS_PROFILE}PROFILE",
                    f"apparmor_parser -r /etc/apparmor.d/{OURS}",
                ]
                undo = [f"apparmor_parser -R /etc/apparmor.d/{OURS} || true", f"rm -f /etc/apparmor.d/{OURS}", *undo]
                changes.append(
                    "puts in the profile of Claude Code's documentation: bubblewrap may make user namespaces, and the "
                    "commands it runs are not confined by it"
                )
            if f["restrict_userns"] == 1:
                changes.append(
                    "what is given up: Ubuntu lets no program make a user namespace, to make attacks on the kernel "
                    "harder; afterwards any program on this machine can make one through bubblewrap"
                )
            else:
                changes.append(
                    "what is given up: this machine lets every program make user namespaces already, so no program "
                    "gains a power; Flatpak applications, which run in bubblewrap too, lose the extra layer the "
                    "distribution's profile put around them"
                )
    # socat comes last and only where the namespace works or is fixed by the steps above: with socat and without the
    # namespace, the sandbox starts and every Bash call of a role session fails, which is worse than no sandbox
    packages = [] if f["bwrap"] else ["bubblewrap"]
    if not f["socat"]:
        if f["bwrap"] and (f["nested_ok"] or apparmor_fix):
            packages.append("socat")
        elif not f["bwrap"]:
            notes.append("socat follows in a second run, once bubblewrap is here and its namespace is checked")
        else:
            notes.append(
                "socat is not installed while a namespace inside bubblewrap is refused: the sandbox would "
                "then start and every Bash call of a role session would fail"
            )
    if packages and f["installer"]:
        install = INSTALL[f["installer"]].format(" ".join(packages))
        if f["installer"] == "apt-get":  # a machine whose package lists are old finds the package after an update
            install = f"{install} || (apt-get update && {install})"
        steps.append(install)
        changes.append(f"installs {' and '.join(packages)}")
    elif packages:
        notes.append(f"install {', '.join(packages)} with this machine's package manager: none known was found")
    return {"changes": changes, "steps": steps, "undo": undo, "notes": notes}


def script(steps: list[str]) -> str:
    return "#!/bin/sh\nset -eu\n" + "".join(f"{line}\n" for line in steps)


def runner(env: dict | None = None, tty: bool | None = None) -> list[str] | None:
    """How the root script gets the password: the system's window in a desktop session, sudo in a terminal."""
    env = os.environ if env is None else env
    tty = sys.stdin.isatty() if tty is None else tty
    if (env.get("DISPLAY") or env.get("WAYLAND_DISPLAY")) and shutil.which("pkexec"):
        return ["pkexec", "/bin/sh"]
    if tty and shutil.which("sudo"):
        return ["sudo", "/bin/sh"]
    return None


KNOWN = ("--plan", "--undo", "--user", "--auto")


def main(argv: list[str]) -> int:
    usage = "\n\n".join(__doc__.split("\n\n")[:2])
    if {"-h", "--help"} & set(argv[1:]):
        print(usage)
        return 0
    unknown = [a for a in argv[1:] if a not in KNOWN]
    if unknown:  # a word it does not know once set the machine up, as the plain command does
        print(f"unknown argument: {' '.join(unknown)}\n\n{usage}", file=sys.stderr)
        return 2
    if os.name == "nt":
        print("this repository runs in WSL2 on Windows: open it in a WSL2 distribution")
        return 1
    before = facts()
    way = user_plan(before)
    todo = plan(before)
    if "--plan" in argv:
        print(json.dumps({"facts": before, "user_space": way, **todo, "records": str(RECORDS)}, indent=2))
        return 0
    if "--undo" in argv:
        result = undo_user()
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    if "--user" in argv or "--auto" in argv or ((way["bwrap"] or way["socat"]) and not way["why_not"]):
        result = main_user(explicit="--auto" not in argv)  # never falls back to the password by itself
        print(json.dumps(result, indent=2))
        return 0 if result.get("sandbox_works") else 1
    if not todo["steps"]:
        print("\n".join(todo["notes"]) or "the sandbox has what it needs")
        return 0 if before["nested_ok"] and before["socat"] else 1
    record = RECORDS / dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%SZ")
    record.mkdir(parents=True, exist_ok=True)
    (record / "apply.sh").write_text(script(todo["steps"]), encoding="utf-8")
    (record / "undo.sh").write_text(script(todo["undo"]), encoding="utf-8")
    how = runner()
    if how is None:
        print(
            f"one step needs the administrator and no password window or terminal is here: read {record / 'apply.sh'}, "
            "then run its commands as root"
        )
        return 1
    print("one password, once. This " + "; ".join(todo["changes"]) + f". Undo: {record / 'undo.sh'}", flush=True)
    # The script goes to the root shell as an argument, never as a file: a file of this user could be changed by any
    # of this user's processes between its writing and the moment root reads it.
    done = subprocess.run([*how, "-c", script(todo["steps"])], capture_output=True, text=True, check=False)
    after = facts()
    result = {
        "applied": done.returncode == 0,
        "exit_code": done.returncode,
        "output": (done.stdout + done.stderr).strip()[-2000:],
        "socat": after["socat"],
        "nested_ok": after["nested_ok"],
        "nested_error": after["nested_error"],
        "undo": str(record / "undo.sh"),
    }
    if after["socat"] and not after["nested_ok"]:  # the sandbox now starts and refuses every command
        result["warning"] = (
            f"every Bash call of a role session now fails: read {record / 'undo.sh'} (a file of this user), then "
            "run its commands as root"
        )
    (record / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if after["nested_ok"] and after["socat"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
