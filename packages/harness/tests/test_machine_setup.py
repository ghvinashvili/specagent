"""The machine sets itself up for the sandbox (ops/machine-setup.py): as this user where that is enough, else with one
password, so that nobody types a command after a clone."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ZORIN = {"name": "bwrap-userns-restrict-patched", "ours": False, "disabled": False}
APT = "DEBIAN_FRONTEND=noninteractive apt-get install -y {0} || (apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y {0})"


def load(path: Path, name: str):
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def ms(tmp_path: Path, monkeypatch):
    """The script, with its folders in the test's own directory: no test may put a file into this user's home."""
    module = load(REPO / "ops" / "machine-setup.py", "ops_machine_setup")
    monkeypatch.setattr(module, "USER_BIN", tmp_path / "home-bin")
    monkeypatch.setattr(module, "RECORDS", tmp_path / "records")
    monkeypatch.setattr(module, "USER_RECORD", tmp_path / "records" / "user-space.json")
    monkeypatch.setattr(module, "unpack", lambda *a: pytest.fail("a package was fetched"))
    return module


def facts(**changed) -> dict:
    """A Linux machine whose sandbox works; each test changes what it is about."""
    base = {
        "linux": True,
        "sandbox_enabled": True,
        "socat": "/usr/bin/socat",
        "bwrap": "/usr/bin/bwrap",
        "nested_ok": True,
        "nested_error": "",
        "restrict_userns": 0,
        "apparmor": True,
        "profiles": [],
        "installer": "apt-get",
        "system_bwrap_sha": "s1",
        "user_bin_first": True,
        "user": {},
        "dpkg_deb": True,
    }
    return {**base, **changed}


def test_a_machine_whose_sandbox_works_needs_nothing(ms):
    assert ms.plan(facts()) == {"changes": [], "steps": [], "undo": [], "notes": []}


def test_the_zorin_profile_gives_way_to_the_documented_one_and_socat_comes_last(ms):
    out = ms.plan(facts(socat=None, nested_ok=False, nested_error="write failed /proc/self/uid_map", profiles=[ZORIN]))
    steps = out["steps"]
    assert steps[:4] == [
        "mkdir -p /etc/apparmor.d/disable",
        "ln -sf /etc/apparmor.d/bwrap-userns-restrict-patched /etc/apparmor.d/disable/bwrap-userns-restrict-patched",
        "apparmor_parser -R /etc/apparmor.d/bwrap-userns-restrict-patched || true",
        f"cat > /etc/apparmor.d/bwrap <<'PROFILE'\n{ms.DOCS_PROFILE}PROFILE",
    ]
    assert steps[4:] == ["apparmor_parser -r /etc/apparmor.d/bwrap", APT.format("socat")]
    assert out["undo"] == [
        "apparmor_parser -R /etc/apparmor.d/bwrap || true",
        "rm -f /etc/apparmor.d/bwrap",
        "rm -f /etc/apparmor.d/disable/bwrap-userns-restrict-patched",
        "apparmor_parser -r /etc/apparmor.d/bwrap-userns-restrict-patched",
    ]
    assert len(out["changes"]) == 4 and out["notes"] == []
    assert "Flatpak" in out["changes"][2]  # what the human gives up on a machine without the restriction


def test_ubuntu_with_the_restriction_on_gets_the_documented_profile(ms):
    out = ms.plan(facts(nested_ok=False, restrict_userns=1))
    assert out["steps"] == [
        f"cat > /etc/apparmor.d/bwrap <<'PROFILE'\n{ms.DOCS_PROFILE}PROFILE",
        "apparmor_parser -r /etc/apparmor.d/bwrap",
    ]
    assert any("any program on this machine can make one" in c for c in out["changes"])


def test_socat_waits_while_the_namespace_is_refused_for_a_reason_not_known(ms):
    """With socat and without the namespace the sandbox starts and every command of a role session fails."""
    out = ms.plan(facts(socat=None, nested_ok=False, nested_error="boom"))
    assert out["steps"] == []
    assert any("reason not known here: boom" in n for n in out["notes"])
    assert any("every Bash call" in n for n in out["notes"])


def test_bubblewrap_comes_first_and_socat_in_a_second_run(ms):
    out = ms.plan(facts(bwrap=None, socat=None, nested_ok=False))
    assert out["steps"] == [APT.format("bubblewrap")]
    assert any("second run" in n for n in out["notes"])


def test_nothing_is_done_outside_linux_or_where_the_repository_has_no_sandbox(ms):
    assert ms.plan(facts(linux=False, socat=None))["steps"] == []
    assert ms.plan(facts(sandbox_enabled=False, socat=None))["steps"] == []


def test_another_profile_in_the_documented_file_is_disabled_and_not_overwritten(ms):
    out = ms.plan(facts(nested_ok=False, profiles=[{"name": "bwrap", "ours": False, "disabled": False}]))
    assert "ln -sf /etc/apparmor.d/bwrap /etc/apparmor.d/disable/bwrap" in out["steps"]
    assert not any(s.startswith("cat > ") for s in out["steps"])
    assert any("not overwritten" in n for n in out["notes"])


def test_a_profile_name_that_is_not_a_plain_file_name_never_reaches_the_root_script(ms):
    out = ms.plan(
        facts(nested_ok=False, restrict_userns=1, profiles=[{"name": "x;rm -rf /", "ours": False, "disabled": False}])
    )
    assert not any("x;rm" in s for s in out["steps"])
    assert any("not plain file names" in n for n in out["notes"])


def test_a_machine_without_a_known_package_manager_is_told_and_nothing_is_guessed(ms):
    out = ms.plan(facts(socat=None, installer=None))
    assert out["steps"] == [] and any("package manager" in n for n in out["notes"])


def test_the_profiles_found_are_those_that_attach_to_bubblewrap(ms, tmp_path: Path):
    (tmp_path / "disable").mkdir()
    (tmp_path / "bwrap-userns-restrict-patched").write_text(
        "abi <abi/4.0>,\nprofile bwrap /usr/bin/bwrap flags=(attach_disconnected,mediate_deleted) {\n}\n"
    )
    (tmp_path / "bwrap").write_text(ms.DOCS_PROFILE)
    (tmp_path / "firefox").write_text("profile firefox /usr/lib/firefox/firefox {\n}\n")
    (tmp_path / "old").write_text("profile bwrap /usr/bin/bwrap {\n}\n")
    (tmp_path / "disable" / "old").symlink_to(tmp_path / "old")
    found = {p["name"]: p for p in ms.bwrap_profiles(tmp_path)}
    assert set(found) == {"bwrap", "bwrap-userns-restrict-patched", "old"}
    assert found["bwrap"]["ours"] and not found["bwrap-userns-restrict-patched"]["ours"]
    assert found["old"]["disabled"] and not found["bwrap-userns-restrict-patched"]["disabled"]


def test_the_root_script_stops_at_its_first_failure(ms):
    assert ms.script(["a", "b"]) == "#!/bin/sh\nset -eu\na\nb\n"


def test_the_password_is_asked_in_the_systems_window_on_a_desktop_and_by_sudo_in_a_terminal(ms, monkeypatch):
    monkeypatch.setattr(ms.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert ms.runner({"DISPLAY": ":0"}, tty=False) == ["pkexec", "/bin/sh"]
    assert ms.runner({"WAYLAND_DISPLAY": "wayland-0"}, tty=True) == ["pkexec", "/bin/sh"]
    assert ms.runner({}, tty=True) == ["sudo", "/bin/sh"]
    assert ms.runner({}, tty=False) is None


def test_the_root_shell_gets_the_script_as_an_argument_and_never_as_a_file(ms, tmp_path: Path, monkeypatch):
    """A file of this user could be changed by any of this user's processes before root reads it."""
    broken = facts(socat=None, nested_ok=False, profiles=[ZORIN], user_bin_first=False)  # only root can help here
    monkeypatch.setattr(ms, "facts", lambda root=None: broken)
    monkeypatch.setattr(ms, "runner", lambda env=None, tty=None: ["pkexec", "/bin/sh"])
    monkeypatch.setattr(ms, "RECORDS", tmp_path / "records")
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return ms.subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(ms.subprocess, "run", fake_run)
    assert ms.main(["machine-setup.py"]) == 1  # the fake machine is still broken afterwards
    assert calls == [["pkexec", "/bin/sh", "-c", ms.script(ms.plan(broken)["steps"])]]
    record = next((tmp_path / "records").iterdir())
    assert sorted(p.name for p in record.iterdir()) == ["apply.sh", "result.json", "undo.sh"]


def test_the_commands_a_session_runs_for_the_human_run_outside_the_sandbox_by_their_exact_names():
    """Where the sandbox starts but refuses the namespace no command runs in it, and root is out of its reach; `--user`
    and `--undo` write in ~/.local, outside the checkout. The patterns are exact: no other file or argument under ops/
    runs outside by its name, and role sessions are denied all of them (harness/access.py)."""
    excluded = json.loads((REPO / ".claude" / "settings.json").read_text())["sandbox"]["excludedCommands"]
    mine = {
        "python3 ops/machine-setup.py",
        "python3 ops/machine-setup.py --user",
        "python3 ops/machine-setup.py --undo",
    }
    assert {p for p in excluded if p.startswith("python3")} == mine


def zorin(**changed) -> dict:
    """This machine on 2026-10-03: Zorin's profile on /usr/bin/bwrap, the restriction off, no socat."""
    this = {"socat": None, "nested_ok": False, "nested_error": "write failed /proc/self/uid_map", "profiles": [ZORIN]}
    return facts(**{**this, **changed})


def test_where_every_program_may_make_a_namespace_the_sandbox_needs_no_password(ms):
    assert ms.user_plan(zorin()) == {"bwrap": "copy", "socat": "download", "why_not": None}
    assert ms.user_plan(facts(socat=None)) == {"bwrap": None, "socat": "download", "why_not": None}  # WSL2
    assert ms.user_plan(facts(bwrap=None, socat=None)) == {"bwrap": "download", "socat": "download", "why_not": None}
    assert ms.user_plan(facts()) == {"bwrap": None, "socat": None, "why_not": None}


def test_the_user_space_way_says_why_it_cannot_help(ms):
    assert "restriction" in ms.user_plan(zorin(restrict_userns=1))["why_not"]
    assert "PATH" in ms.user_plan(zorin(user_bin_first=False))["why_not"]
    assert "apt" in ms.user_plan(zorin(installer="dnf"))["why_not"]
    ours = str(ms.USER_BIN / "bwrap")
    assert "cannot make the namespace either" in ms.user_plan(facts(bwrap=ours, nested_ok=False))["why_not"]
    # without a download nothing needs apt: a copy of the system's bubblewrap is enough
    assert ms.user_plan(zorin(socat="/usr/bin/socat", installer=None))["bwrap"] == "copy"


def test_user_bin_must_come_before_usr_bin(ms):
    home_bin = str(ms.USER_BIN)
    assert ms.user_bin_first(f"{home_bin}:/usr/local/bin:/usr/bin")
    assert not ms.user_bin_first(f"/usr/bin:{home_bin}")
    assert not ms.user_bin_first("/usr/local/bin:/usr/bin")


@pytest.fixture()
def home(ms, tmp_path: Path, monkeypatch):
    system = tmp_path / "usr-bin-bwrap"
    system.write_text("the system's bubblewrap")
    monkeypatch.setattr(ms, "system_bwrap", lambda: str(system))
    return tmp_path


def probe(code: int):
    return lambda bwrap: ms_completed(code)


def ms_completed(code: int):
    import subprocess

    return subprocess.CompletedProcess([], code, "", "" if code == 0 else "uid_map: denied")


def test_the_copies_move_in_only_once_checked_and_socat_only_after_the_namespace(ms, home, monkeypatch):
    def unpack(package, member, staging):
        out = staging / package / member
        out.parent.mkdir(parents=True)
        out.write_text("#!/bin/sh\nexit 0\n")
        out.chmod(0o755)
        return out, "1.7.4.4-2"

    monkeypatch.setattr(ms, "unpack", unpack)
    monkeypatch.setattr(ms, "nested_userns", probe(1))
    refused = ms.apply_user(zorin(), {"bwrap": "copy", "socat": "download"})
    assert (
        not refused["ok"] and not (home / "home-bin" / "bwrap").exists() and not (home / "home-bin" / "socat").exists()
    )
    monkeypatch.setattr(ms, "nested_userns", probe(0))
    done = ms.apply_user(zorin(), {"bwrap": "copy", "socat": "download"})
    assert done["ok"] and (home / "home-bin" / "bwrap").read_text() == "the system's bubblewrap"
    assert (home / "home-bin" / "socat").exists() and not list((home / "home-bin").glob(".harness-staging-*"))
    record = json.loads((home / "records" / "user-space.json").read_text())
    assert record["bwrap"]["from"].endswith("usr-bin-bwrap")
    assert {k: record["socat"][k] for k in ("package", "version")} == {"package": "socat", "version": "1.7.4.4-2"}


def test_a_program_its_package_ships_as_a_link_moves_in_as_the_file_it_names(ms, home, monkeypatch):
    """socat 1.8 of Ubuntu ships `usr/bin/socat` as a link to `socat1`, which stays in the staging folder: the link
    alone moved in and named nothing, so the sandbox still had no socat (seen on this machine on 2026-10-03)."""

    def unpack(package, member, staging):
        out = staging / package / member
        out.parent.mkdir(parents=True)
        (out.parent / "socat1").write_text("#!/bin/sh\nexit 0\n")
        (out.parent / "socat1").chmod(0o755)
        out.symlink_to("socat1")
        return out, "1.8.0.0-4ubuntu0.1"

    monkeypatch.setattr(ms, "unpack", unpack)
    monkeypatch.setattr(ms, "nested_userns", probe(0))
    done = ms.apply_user(zorin(), {"bwrap": "copy", "socat": "download"})
    socat = home / "home-bin" / "socat"
    assert done["ok"] and socat.is_file() and not socat.is_symlink() and os.access(socat, os.X_OK)
    assert socat.read_text() == "#!/bin/sh\nexit 0\n"


def test_a_link_in_a_package_is_followed_inside_it_and_never_out(ms, tmp_path: Path):
    root = tmp_path / "pkg"
    (root / "usr" / "bin").mkdir(parents=True)
    (root / "usr" / "bin" / "socat1").write_text("socat")
    (root / "usr" / "bin" / "absolute").symlink_to("/usr/bin/socat1")  # read inside the package, not the machine's
    found = ms.followed(root / "usr" / "bin" / "absolute", root)
    assert found.resolve() == (root / "usr" / "bin" / "socat1").resolve()
    (root / "usr" / "bin" / "out").symlink_to("../../../outside")
    with pytest.raises(OSError, match="outside the unpacked package"):
        ms.followed(root / "usr" / "bin" / "out", root)


def test_an_argument_it_does_not_know_changes_nothing(ms, monkeypatch, capsys):
    """`--help`, or a word typed wrong, once set the machine up: every argument but the four was the plain command."""
    monkeypatch.setattr(ms, "facts", lambda root=None: pytest.fail("the machine was examined"))
    monkeypatch.setattr(ms, "main_user", lambda explicit=True: pytest.fail("the user-space way was taken"))
    monkeypatch.setattr(ms, "runner", lambda env=None, tty=None: pytest.fail("the password was asked"))
    assert ms.main(["machine-setup.py", "--help"]) == 0
    assert "--plan" in capsys.readouterr().out
    assert ms.main(["machine-setup.py", "--usr"]) == 2
    assert "--usr" in capsys.readouterr().err


def test_the_copies_follow_the_system(ms):
    copied = {"bwrap": {"from": "/usr/bin/bwrap", "sha256": "s1"}, "socat": {"package": "socat", "version": "1"}}
    assert ms.stale(facts(user=copied), {}) == {}
    assert ms.stale(facts(user=copied, system_bwrap_sha="s2"), {}) == {"bwrap": "copy"}  # an update of bubblewrap
    assert ms.stale(facts(user=copied), {"socat": "2"}) == {"socat": "download"}
    assert ms.refresh_due(facts(user={**copied, "checked_at": 100.0}), now=100.0 + ms.DAY + 1)
    assert not ms.refresh_due(facts(user={**copied, "checked_at": 100.0}), now=200.0)
    assert not ms.refresh_due(facts(), now=10**10)  # nothing was put there: nothing to follow


def test_by_default_the_user_space_way_is_taken_and_the_password_is_not_asked(ms, home, monkeypatch):
    monkeypatch.setattr(ms, "facts", lambda root=None: zorin())
    monkeypatch.setattr(ms, "main_user", lambda explicit=True: {"ok": True, "done": {}, "sandbox_works": True})
    monkeypatch.setattr(ms, "runner", lambda env=None, tty=None: pytest.fail("the password was asked"))
    assert ms.main(["machine-setup.py"]) == 0


def test_a_failure_hands_over_to_the_password_for_a_day_and_a_decline_until_asked_again(ms):
    failed = {"failed": {"why": "socat from its package does not start here", "at": 1000.0, "system_bwrap_sha": "s1"}}
    assert "less than a day ago" in ms.user_plan(zorin(user=failed), now=1000.0 + 60)["why_not"]
    assert ms.user_plan(zorin(user=failed), now=1000.0 + ms.DAY + 1)["bwrap"] == "copy"  # a day later: again
    assert ms.user_plan(zorin(user=failed, system_bwrap_sha="s2"), now=1060.0)["bwrap"] == "copy"  # an update: again
    declined = {"declined": {"at": 1.0}}
    assert "--user" in ms.user_plan(zorin(user=declined))["why_not"]
    assert not ms.refresh_due(facts(user={**declined, "bwrap": {"from": "/usr/bin/bwrap", "sha256": "old"}}))


def test_socat_alone_needs_no_namespace_where_the_restriction_is_on(ms):
    out = ms.user_plan(facts(socat=None, restrict_userns=1))  # the administrator's profile made bubblewrap work
    assert out == {"bwrap": None, "socat": "download", "why_not": None}


def test_a_failed_attempt_is_recorded_and_moves_nothing_in(ms, home, monkeypatch):
    monkeypatch.setattr(ms, "nested_userns", probe(1))
    out = ms.apply_user(zorin(), {"bwrap": "copy", "socat": "download"}, checked=True)
    assert not out["ok"] and out["undo"] == ms.UNDO and out["done"] == {}
    record = json.loads((home / "records" / "user-space.json").read_text())
    assert "cannot make the namespace" in record["failed"]["why"] and "checked_at" not in record
    monkeypatch.setattr(ms, "system_bwrap", lambda: None)  # the system's bubblewrap went away meanwhile
    out = ms.apply_user(zorin(), {"bwrap": "copy"})
    assert not out["ok"] and "not on PATH any more" in out["why"]


def test_undo_takes_out_only_what_was_put_in_and_remembers_the_decline(ms, home, monkeypatch):
    monkeypatch.setattr(ms, "nested_userns", probe(0))
    assert ms.apply_user(zorin(socat="/usr/bin/socat"), {"bwrap": "copy"})["ok"]
    record = json.loads((home / "records" / "user-space.json").read_text())
    assert record["bwrap"]["sha256"] == ms.sha256(home / "home-bin" / "bwrap")  # the copy's own hash
    (home / "home-bin" / "socat").write_text("somebody else's socat")
    out = ms.undo_user()
    assert out["removed"] == [str(home / "home-bin" / "bwrap")] and out["left_alone"] == [
        str(home / "home-bin" / "socat")
    ]
    assert json.loads((home / "records" / "user-space.json").read_text()).keys() == {"declined"}


def test_an_undo_the_file_system_refuses_is_reported(ms, home, monkeypatch):
    monkeypatch.setattr(ms, "nested_userns", probe(0))
    assert ms.apply_user(zorin(socat="/usr/bin/socat"), {"bwrap": "copy"})["ok"]
    (home / "home-bin").chmod(0o500)  # as the sandbox keeps a command from writing outside its checkout
    try:
        out = ms.undo_user()
    finally:
        (home / "home-bin").chmod(0o700)
    assert not out["ok"] and "PermissionError" in out["why"] and (home / "home-bin" / "bwrap").exists()
