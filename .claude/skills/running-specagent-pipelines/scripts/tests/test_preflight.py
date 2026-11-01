"""The manager's pre-flight (`scripts/manager/preflight.py`): the checks before a launch, the launch table and the yes,
capacity, timeouts from the eval cases, the polling check and the clock check. Every test but one (the example's launch
table, which goes to `check_launch` itself) runs the script as the manager does, on a run folder built in tmp_path, with
fake `sim_bwrap.py`, `check_formats.py` and `monitor_records.py` scripts; no test starts a session or a sandbox."""

import importlib.util
import json
import re
import shutil
import subprocess
import sys

import pytest
from transcript_home import SCRIPTS

PREFLIGHT = SCRIPTS / "manager" / "preflight.py"
SKILL = SCRIPTS.parent
NOW = "2026-10-29T20:00Z"
# Built from parts, so that no skill file spells a model name (Global Constraint 10).
OPUS, SONNET = "op" + "us", "son" + "net"

TEN = (
    "Read(~/.claude/projects/**)",
    "Read(/<run-dir>/_control/**)",
    "Read(/<checkout>/docs/handoff/**)",
    "Read(//proc/**)",
    "Bash(claude agents:*)",
    "Bash(claude logs:*)",
    "Bash(claude attach:*)",
    "Bash(ps:*)",
    "Bash(pgrep:*)",
    "Read(~/.claude/.credentials.json)",
)

FAKE_SIM = """
import os, subprocess, sys
config, agent, probe = sys.argv[1:4]
with open(os.environ["FAKE_SIM_LOG"], "a", encoding="utf-8") as log:
    log.write(agent + "\\n")
mode = os.environ.get("FAKE_SIM_MODE", "good")
if mode in ("good", "ro"):
    probe = probe.replace(os.environ["FAKE_SIM_CONTROL"], os.environ["FAKE_SIM_NOWHERE"])
if mode == "ro":
    probe = probe.replace("touch ", "true ")
out = subprocess.run(["/bin/bash", "-c", probe], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
print(out.stdout + out.stderr)
"""

FAKE_FORMATS = """
import os, sys
with open(os.environ["FAKE_FORMATS_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
code = int(os.environ.get("FAKE_FORMATS_EXIT", "0"))
print("checked 4 files")
if code:
    print("plan-log.md:1: line 1 is not a STATUS line")
sys.exit(code)
"""

FAKE_MONITOR = """
import os, sys
with open(os.environ["FAKE_MONITOR_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
mode = os.environ.get("FAKE_MONITOR_ARMED", "1")
if mode == "1":
    print("armed since 2026-10-29 19:50:00 UTC, last round 2026-10-29 19:59:30 UTC, interval 30 s")
    sys.exit(0)
if mode == "gone":
    print(f"{sys.argv[2]}: no such run folder", file=sys.stderr)
    sys.exit(2)
print("not armed: no watch recorded")
print("read 0 watch records", file=sys.stderr)
sys.exit(1)
"""

FAKE_CLAUDE = f"""#!{sys.executable}
import os, sys
if sys.argv[1:] != ["agents", "--json", "--all"]:
    sys.exit(64)
sys.stdout.write(open(os.environ["FAKE_AGENTS"], encoding="utf-8").read())
"""

MEASURED = (  # R5: the dollars and the start-up read come from the last run's measurement page
    "from ~/vault/context/measurements/2026-10-29-demo.md (the last run of the same shape): "
    "$2-$3 per session, start-up read 58k tokens per fresh session"
)
LAUNCH = f"""# Launch: demo run

Purpose: build the demo plan's two lanes
Size: one context cannot hold it: 11 tasks at 120k-180k tokens each, measured on the last run
Model rule: the model is the `model` key of each role's settings file under `_control/`
Estimate: 3 roles, one fresh session per unit, 12-16 sessions; {MEASURED}; $40-$60 per unit, $200 for the run
Budget: 300 calls and 4000000 output tokens per session
Usage: five-hour 40% (resets 2026-10-29T21:30Z), weekly 30% (resets 2026-11-04T13:00Z), read at 2026-10-29T19:55Z

| role | lane | work | settings | skills | ECC texts | cost estimate |
|---|---|---|---|---|---|---|
| planner | a | writes the plan | `_control/planner-settings.json` | running-specagent-pipelines | planner | $10 |
| builder-a | a | builds lane A | `_control/builder-a-settings.json` | running-specagent-pipelines | tdd-guide | $25 |
| judge | - | reads the record once | `_control/judge-settings.json` | - | - | $5 |
"""


class Run:
    """A ready run folder: two roles (a planner in a plain checkout, a builder in a worktree with its own .venv), a judge
    config, settings under `_control/`, a brief naming a waiter, `_launch.md`, `usage.json`, the three fakes and a fake
    `claude` that prints the rows of `agents.json`."""

    def __init__(self, tmp_path):
        self.root = tmp_path
        self.run, self.checkout = tmp_path / "run", tmp_path / "checkout"
        self.plan, self.wt, self.home = tmp_path / "plan", tmp_path / "wt-a", tmp_path / "home"
        self.control = self.run / "_control"
        self.config = self.control / "_agents.json"
        self.planner_settings = self.control / "planner-settings.json"
        self.builder_settings = self.control / "builder-a-settings.json"
        self.common = f"Wait with `python3 -I {self.run}/_wait_for_log.py {self.run}/plan-log.md 'Task 4: written'`.\n"
        self.sim, self.formats, self.monitor = (tmp_path / "fakes" / n for n in ("sim.py", "formats.py", "monitor.py"))
        self.sim_log, self.formats_log, self.monitor_log = (
            tmp_path / n for n in ("sim.log", "formats.log", "monitor.log")
        )
        self.env = {
            "HOME": str(self.home),
            "TMPDIR": str(tmp_path),  # R5: check_disk's tempfile.gettempdir() needs a writable folder
            "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin",
            "FAKE_SIM_LOG": str(self.sim_log),
            "FAKE_SIM_CONTROL": str(self.control),
            "FAKE_SIM_NOWHERE": str(tmp_path / "nowhere"),
            "FAKE_FORMATS_LOG": str(self.formats_log),
            "FAKE_MONITOR_LOG": str(self.monitor_log),
            "FAKE_AGENTS": str(tmp_path / "agents.json"),
        }
        self.make_folders()
        self.write_configs()
        self.write_run_files()

    def make_folders(self):
        """The checkout, the plan checkout, the builder's worktree with its `.git` file, `.venv` and pyproject, HOME."""
        for d in (
            self.control,
            self.checkout / ".git",
            self.checkout / "docs" / "handoff",
            self.plan / ".git",
            self.wt / ".venv",
            self.home / ".cache",
            self.root / "bin",
            self.root / "fakes",
        ):
            d.mkdir(parents=True)
        (self.wt / ".git").write_text("gitdir: ../checkout/.git/worktrees/wt-a\n", encoding="utf-8")
        (self.wt / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")

    def write_configs(self):
        """`_agents.json` (the planner and builder-a), `_agents-judge.json` and the three settings files."""
        self.write_json(
            self.config,
            {
                "common": [
                    "--strict-mcp-config",
                    "--effort",
                    "max",
                    "--permission-mode",
                    "auto",
                    "--setting-sources",
                    "local",
                    "--autocompact",
                    "235000",
                    "--exclude-dynamic-system-prompt-sections",
                    "--system-prompt-snapshot",
                    "on",
                ],
                "agents": {
                    "planner": {
                        "cwd": str(self.plan),
                        "add_dirs": [str(self.run)],
                        "settings": "_control/planner-settings.json",
                        "extra_prompt": {"file": "_pack-planner.md", "mark": "startup pack of demo/planner"},
                    },
                    "builder-a": {
                        "cwd": str(self.wt),
                        "add_dirs": [str(self.run)],
                        "settings": "_control/builder-a-settings.json",
                        "extra_prompt": {"file": "_pack-builder-a.md", "mark": "startup pack of demo/builder-a"},
                    },
                },
                "budget": {"calls": 300, "output_tokens": 4000000},
            },
        )
        self.write_json(
            self.control / "_agents-judge.json",
            {
                "agents": {
                    "judge": {
                        "cwd": str(self.run),
                        "add_dirs": [],
                        "settings": "_control/judge-settings.json",
                        "extra_prompt": {"file": "_pack-judge.md", "mark": "startup pack of demo/judge"},
                    }
                },
            },
        )
        self.write_json(self.planner_settings, self.settings([self.plan, self.run]))
        self.write_json(self.builder_settings, self.settings([self.wt, self.run, self.checkout / ".git"]))
        self.write_json(self.control / "judge-settings.json", self.settings([self.run]))

    def write_run_files(self):
        """The waiter, `_common.md` naming it, `_launch.md`, two usage readings and the three fakes."""
        (self.run / "_wait_for_log.py").write_text("# waiter\n", encoding="utf-8")
        for role in ("planner", "builder-a", "judge"):
            (self.run / f"_pack-{role}.md").write_text(
                f"# Your standing orders (startup pack of demo/{role})\n", encoding="utf-8"
            )
        (self.run / "_common.md").write_text(self.common, encoding="utf-8")
        (self.run / "_launch.md").write_text(LAUNCH, encoding="utf-8")
        self.usage(
            [
                ("2026-10-29T19:00Z", [("five-hour", 30, "2026-10-29T21:30Z"), ("weekly", 30, "2026-11-04T13:00Z")]),
                ("2026-10-29T19:55Z", [("five-hour", 40, "2026-10-29T21:30Z"), ("weekly", 30, "2026-11-04T13:00Z")]),
            ]
        )
        for path, text in ((self.sim, FAKE_SIM), (self.formats, FAKE_FORMATS), (self.monitor, FAKE_MONITOR)):
            path.write_text(text, encoding="utf-8")
        claude = self.root / "bin" / "claude"
        claude.write_text(FAKE_CLAUDE, encoding="utf-8")
        claude.chmod(0o755)
        self.sessions()

    def sessions(self, *rows):
        """The rows the fake `claude agents --json --all` prints (none by default)."""
        (self.root / "agents.json").write_text(json.dumps(list(rows)), encoding="utf-8")

    def settings(self, allow_write):
        return {
            "model": "the-lane-model",
            "permissions": {
                "allow": [],
                "deny": [r.replace("<run-dir>", str(self.run)).replace("<checkout>", str(self.checkout)) for r in TEN],
            },
            "sandbox": {
                "enabled": True,
                "autoAllowBashIfSandboxed": True,
                "allowUnsandboxedCommands": False,
                "failIfUnavailable": True,
                "filesystem": {
                    "allowWrite": [str(p) for p in allow_write],
                    "denyRead": [
                        "~/.claude/projects",
                        f"{self.control}",
                        f"{self.checkout}/docs/handoff",
                        "~/.claude/.credentials.json",
                    ],
                },
            },
            "env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "", "CLAUDE_CODE_PROMPT_CACHE_TTL": "5m"},
            "includeCoAuthoredBy": False,
            "hooks": {
                "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": f"{WARM} pretool"}]}],
                "Stop": [{"hooks": [{"type": "command", "command": f"{WARM} stop rec.md 'STATUS: done'"}]}],
            },
        }

    @staticmethod
    def write_json(path, data):
        path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")

    def edit(self, path, change):
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        self.write_json(path, data)

    def usage(self, readings):
        self.write_json(
            self.control / "usage.json",
            {
                "readings": [
                    {
                        "taken_at": taken,
                        "source": "get_usage",
                        "extra_usage": False,
                        "limits": [{"name": n, "used_pct": p, "resets_at": r} for n, p, r in limits],
                    }
                    for taken, limits in readings
                ]
            },
        )

    def args(self, *extra):
        """`--sim` and `--monitor` are left out when `extra` names `--no-sim`, `--no-monitor` or another `--monitor`."""
        sim = [] if "--no-sim" in extra else ["--sim", self.sim]
        monitor = [] if {"--no-monitor", "--monitor"} & set(map(str, extra)) else ["--monitor", self.monitor]
        return [
            "check",
            self.run,
            "--checkout",
            self.checkout,
            *sim,
            "--formats",
            self.formats,
            *monitor,
            "--now",
            NOW,
            *extra,
        ]


def preflight(*args, env):
    return subprocess.run(
        [sys.executable, "-I", str(PREFLIGHT), *map(str, args)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )


def results(proc):
    lines = [re.fullmatch(r"(PASS|FAIL|SKIP) ([a-z]+)(?: ([\w-]+))?: (.*)", line) for line in proc.stdout.splitlines()]
    return [m.groups() for m in lines if m]


def found(proc, check, agent=None):
    """The (status, detail) pairs of one check."""
    return [(s, d) for s, c, a, d in results(proc) if c == check and a == agent]


def test_a_ready_run_passes_twenty_checks_writes_the_result_file_and_leaves_no_probe_mark(tmp_path):
    r = Run(tmp_path)
    proc = preflight(*r.args(), env=r.env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    per_role = [
        (s, c, a)
        for a in ("planner", "builder-a")
        for s, c in (
            ("PASS", "blind"),
            ("PASS", "cache"),
            ("PASS", "ancestor"),
            ("PASS", "probe"),
            ("PASS", "worktree"),
        )
    ]
    run_wide = [
        ("PASS", c, None) for c in ("waiters", "briefs", "formats", "monitor", "disk", "usage", "live", "launch")
    ]
    assert [(s, c, a) for s, c, a, _ in results(proc)] == [
        ("PASS", "config", None),
        ("PASS", "model", None),
        *per_role,
        *run_wide,
    ]
    assert proc.stdout.splitlines()[-1] == f"preflight: 20 passed, 0 failed, 0 skipped — {r.control}/preflight.json"
    saved = json.loads((r.control / "preflight.json").read_text(encoding="utf-8"))
    assert saved["passed"] is True and saved["written_at"] == NOW and saved["roles"] == ["planner", "builder-a"]
    assert saved["run_dir"] == str(r.run) and len(saved["results"]) == 20
    assert {k: saved["results"][2][k] for k in ("check", "agent", "status")} == {
        "check": "blind",
        "agent": "planner",
        "status": "PASS",
    }
    assert sorted(str(p) for p in tmp_path.rglob(".preflight-*")) == []
    assert r.sim_log.read_text(encoding="utf-8").split() == ["planner", "builder-a"]
    assert r.formats_log.read_text(encoding="utf-8").split() == [str(r.run)]
    assert r.monitor_log.read_text(encoding="utf-8").split() == ["status", str(r.run)]


def test_a_model_in_the_config_a_brief_or_lessons_fails_and_a_model_key_in_a_settings_file_does_not(tmp_path):
    r = Run(tmp_path)
    r.edit(r.planner_settings, lambda s: s.update(model=OPUS))
    assert [s for s, _ in found(preflight(*r.args(), env=r.env), "model")] == ["PASS"]
    r.edit(r.config, lambda c: c["common"].extend(["--model", OPUS]))
    (r.run / "_common.md").write_text(r.common + f"Use {OPUS.capitalize()} for the plan.\n", encoding="utf-8")
    (r.run / "lessons.md").write_text(f"- the {SONNET.upper()} critic missed it\n", encoding="utf-8")
    proc = preflight(*r.args(), env=r.env)
    [(status, detail)] = found(proc, "model")
    assert proc.returncode == 1 and status == "FAIL"
    assert "_control/_agents.json:" in detail and "_common.md:2" in detail and "lessons.md:1" in detail
    assert "settings" not in detail


def test_a_config_or_a_settings_file_outside_control_fails_and_the_config_failure_stops_the_rest(tmp_path):
    r = Run(tmp_path)
    outside = r.run / "_agents.json"
    outside.write_text(r.config.read_text(encoding="utf-8"), encoding="utf-8")
    proc = preflight(*r.args("--config", outside), env=r.env)
    assert proc.returncode == 1 and [(s, c) for s, c, _, _ in results(proc)] == [("FAIL", "config")]
    assert proc.stdout.splitlines()[-1] == f"preflight: 0 passed, 1 failed, 0 skipped — {r.control}/preflight.json"
    assert json.loads((r.control / "preflight.json").read_text(encoding="utf-8"))["passed"] is False
    (r.run / "builder-a-settings.json").write_text(r.builder_settings.read_text(encoding="utf-8"), encoding="utf-8")
    r.edit(r.config, lambda c: c["agents"]["builder-a"].update(settings="builder-a-settings.json"))
    [(status, detail)] = found(preflight(*r.args(), env=r.env), "config")
    assert status == "FAIL" and "builder-a" in detail and "_control" in detail
    assert found(preflight(*r.args("--roles", "planner"), env=r.env), "config")[0][0] == "PASS"
    [(status, detail)] = found(preflight(*r.args("--roles", "planner,critic"), env=r.env), "config")
    assert status == "FAIL" and "critic" in detail


def test_blind_names_every_missing_deny_rule_flag_and_denyread_path(tmp_path):
    r = Run(tmp_path)

    def planner(s):
        deny = s["permissions"]["deny"]
        deny[deny.index(f"Read(/{r.control}/**)")] = f"Read({r.control}/**)"
        s["sandbox"]["allowUnsandboxedCommands"] = True
        s["includeCoAuthoredBy"] = True

    def builder(s):
        deny = s["permissions"]["deny"]
        deny.remove("Bash(pgrep:*)")
        deny[deny.index("Read(//proc/**)")] = "Read(/proc/**)"
        s["sandbox"]["filesystem"]["denyRead"].remove(f"{r.checkout}/docs/handoff")

    r.edit(r.planner_settings, planner)
    r.edit(r.builder_settings, builder)
    proc = preflight(*r.args(), env=r.env)
    [(s1, d1)], [(s2, d2)] = found(proc, "blind", "planner"), found(proc, "blind", "builder-a")
    assert (s1, s2) == ("FAIL", "FAIL")
    assert f"Read(/{r.control}/**)" in d1 and "allowUnsandboxedCommands" in d1 and "pgrep" not in d1
    assert "Bash(pgrep:*)" in d2 and "Read(//proc/**)" in d2 and f"{r.checkout}/docs/handoff" in d2
    assert "includeCoAuthoredBy" in d1 and "includeCoAuthoredBy" not in d2  # only the planner's is set wrong
    [(s3, d3)] = found(preflight(*r.args("--unsandboxed", "planner"), env=r.env), "blind", "planner")
    assert s3 == "FAIL" and f"Read(/{r.control}/**)" in d3 and "allowUnsandboxedCommands" not in d3
    assert "includeCoAuthoredBy" in d3


ANCESTOR = [
    # (allowWrite, deny rules, denyWrite, expected): {R} the tmp root, {wt} the builder's cwd, {home} $HOME
    (["{wt}/.git"], ["Edit(/{wt})"], [], "FAIL"),
    (["{wt}"], ["Write(/{wt}/**)"], [], "FAIL"),
    (["{R}/data-cache"], ["Edit(/{R}/data/**)"], [], "PASS"),
    (["{wt}"], ["Edit(/{wt}/.git/hooks/**)"], [], "PASS"),
    (["~/.cache"], ["Edit(~/.cache/**)"], [], "FAIL"),
    (["{wt}/data/out"], ["Edit(/data/**)"], [], "FAIL"),
    (["{wt}/sub"], [], ["{wt}"], "FAIL"),
]


@pytest.mark.parametrize(
    "allow, deny, deny_write, expected",
    ANCESTOR,
    ids=["parent", "equal", "sibling-prefix", "below", "home", "cwd-anchored", "denyWrite"],
)
def test_a_deny_rule_on_an_allowwrite_path_or_above_it_fails_and_one_below_it_passes(
    tmp_path, allow, deny, deny_write, expected
):
    r = Run(tmp_path)
    fill = {"R": tmp_path, "wt": r.wt, "home": r.home}

    def change(s):
        s["permissions"]["deny"] += [x.format(**fill) for x in deny]
        s["sandbox"]["filesystem"]["allowWrite"] = [x.format(**fill) for x in allow]
        s["sandbox"]["filesystem"]["denyWrite"] = [x.format(**fill) for x in deny_write]

    r.edit(r.builder_settings, change)
    [(status, detail)] = found(
        preflight(*r.args("--roles", "builder-a", "--no-sim"), env=r.env), "ancestor", "builder-a"
    )
    assert status == expected, detail


@pytest.mark.parametrize(
    "mode, expected, words",
    [
        ("good", "PASS", []),
        ("open", "FAIL", ["write into", "_control", "read of"]),
        ("ro", "FAIL", ["write refused in"]),
    ],
)
def test_the_probe_passes_only_when_worktree_writes_land_and_control_stays_shut(tmp_path, mode, expected, words):
    r = Run(tmp_path)
    proc = preflight(*r.args("--roles", "planner"), env={**r.env, "FAKE_SIM_MODE": mode})
    [(status, detail)] = found(proc, "probe", "planner")
    assert status == expected and all(w in detail for w in words), detail
    if mode == "ro":
        assert str(r.plan) in detail and "write into" not in detail
    assert sorted(str(p) for p in tmp_path.rglob(".preflight-*")) == []


def test_an_allowwrite_entry_under_home_is_probed_and_reported_at_its_expanded_path(tmp_path):
    r = Run(tmp_path)
    r.edit(r.builder_settings, lambda s: s["sandbox"]["filesystem"]["allowWrite"].append("~/.cache"))
    cache = str(r.home / ".cache")
    proc = preflight(*r.args("--roles", "builder-a"), env={**r.env, "FAKE_SIM_MODE": "ro"})
    [(status, detail)] = found(proc, "probe", "builder-a")
    assert status == "FAIL" and cache in detail and "~/.cache" not in detail, detail
    proc = preflight(*r.args("--roles", "builder-a"), env={**r.env, "FAKE_SIM_MODE": "good"})
    assert [s for s, _ in found(proc, "probe", "builder-a")] == ["PASS"], proc.stdout
    assert sorted(str(p) for p in tmp_path.rglob(".preflight-*")) == []


def test_without_bwrap_the_probe_fails_unless_it_is_skipped_on_purpose_and_unsandboxed_roles_skip_it(tmp_path):
    r = Run(tmp_path)
    env = {**r.env, "PATH": str(tmp_path / "bin")}
    args = [
        "check",
        r.run,
        "--checkout",
        r.checkout,
        "--formats",
        r.formats,
        "--monitor",
        r.monitor,
        "--now",
        NOW,
        "--roles",
        "planner",
    ]
    proc = preflight(*args, env=env)
    assert found(proc, "probe", "planner") == [("FAIL", "bwrap not on PATH")] and proc.returncode == 1
    proc = preflight(*args, "--no-sim", env=env)
    assert [s for s, _ in found(proc, "probe", "planner")] == ["SKIP"] and proc.returncode == 0
    assert proc.stdout.splitlines()[-1].startswith("preflight: 14 passed, 0 failed, 1 skipped — ")
    r.edit(r.planner_settings, lambda s: s["sandbox"].update(enabled=False))
    proc = preflight(*r.args("--roles", "planner", "--unsandboxed", "planner"), env=r.env)
    assert [s for s, _ in found(proc, "probe", "planner")] == ["SKIP"]
    assert [s for s, _ in found(proc, "ancestor", "planner")] == ["SKIP"]
    assert [s for s, _ in found(proc, "blind", "planner")] == ["PASS"] and not r.sim_log.exists()


def test_worktree_fails_without_the_cwd_its_git_or_the_venv_a_pyproject_needs(tmp_path):
    r = Run(tmp_path)
    shutil.rmtree(r.wt / ".venv")
    (r.plan / ".git").rmdir()
    proc = preflight(*r.args("--no-sim"), env=r.env)
    [(s1, d1)], [(s2, d2)] = found(proc, "worktree", "planner"), found(proc, "worktree", "builder-a")
    assert (s1, s2) == ("FAIL", "FAIL") and ".git" in d1 and ".venv" in d2
    (r.wt / "pyproject.toml").unlink()
    assert found(preflight(*r.args("--no-sim"), env=r.env), "worktree", "builder-a")[0][0] == "PASS"
    shutil.rmtree(r.plan)
    [(s3, d3)] = found(preflight(*r.args("--no-sim"), env=r.env), "worktree", "planner")
    assert s3 == "FAIL" and str(r.plan) in d3


def test_every_waiter_a_brief_names_is_a_file_in_the_run_folder_with_no_placeholder_left(tmp_path):
    r = Run(tmp_path)
    brief = r.run / "_planner-assignment.md"
    brief.write_text("Then `python3 -I _wait_for_ready.py plan-log.md`.\n", encoding="utf-8")
    [(status, detail)] = found(preflight(*r.args("--no-sim"), env=r.env), "waiters")
    assert status == "FAIL" and "_planner-assignment.md" in detail and "_wait_for_ready.py" in detail
    (r.run / "_wait_for_ready.py").write_text("# waiter\n", encoding="utf-8")
    assert found(preflight(*r.args("--no-sim"), env=r.env), "waiters")[0][0] == "PASS"
    (r.run / "_wait_for_task.py").write_text("# waiter\n", encoding="utf-8")
    brief.write_text("Then `python3 -I <run-dir>/_wait_for_task.py plan-log.md 4`.\n", encoding="utf-8")
    [(status, detail)] = found(preflight(*r.args("--no-sim"), env=r.env), "waiters")
    assert status == "FAIL" and "<run-dir>/_wait_for_task.py" in detail


def test_formats_and_monitor_report_the_exit_and_the_last_line_of_their_script(tmp_path):
    r = Run(tmp_path)
    env = {**r.env, "FAKE_FORMATS_EXIT": "1", "FAKE_MONITOR_ARMED": "0"}
    proc = preflight(*r.args("--no-sim"), env=env)
    assert found(proc, "formats") == [("FAIL", "exit 1: plan-log.md:1: line 1 is not a STATUS line")]
    assert found(proc, "monitor") == [("FAIL", "exit 1: not armed: no watch recorded")]
    assert r.formats_log.read_text(encoding="utf-8").split() == [str(r.run)]
    gone = preflight(*r.args("--no-sim"), env={**r.env, "FAKE_MONITOR_ARMED": "gone"})
    assert found(gone, "monitor") == [("FAIL", f"exit 2: {r.run}: no such run folder")]
    [(status, detail)] = found(
        preflight(*r.args("--no-sim", "--monitor", tmp_path / "absent.py"), env=r.env), "monitor"
    )
    assert status == "FAIL" and "absent.py" in detail
    assert [s for s, _ in found(preflight(*r.args("--no-sim", "--no-monitor"), env=env), "monitor")] == ["SKIP"]


def test_disk_fails_below_the_minimum_free_space(tmp_path):
    r = Run(tmp_path)
    assert found(preflight(*r.args("--no-sim", "--min-free-mb", "1"), env=r.env), "disk")[0][0] == "PASS"
    assert found(preflight(*r.args("--no-sim", "--min-free-mb", "1000000000"), env=r.env), "disk")[0][0] == "FAIL"


FIVE = "five-hour"
USAGE = [
    # (readings, extra args, expected, a word of the detail); now = 2026-10-29T20:00Z
    ([("2026-10-29T19:29Z", [(FIVE, 10, "2026-10-29T23:00Z")])], [], "FAIL", "31 min"),
    (
        [
            ("2026-10-29T19:00Z", [(FIVE, 40, "2026-10-29T21:30Z")]),
            ("2026-10-29T20:00Z", [(FIVE, 60, "2026-10-29T21:30Z")]),
        ],
        [],
        "PASS",
        "",
    ),
    (
        [
            ("2026-10-29T19:00Z", [(FIVE, 40, "2026-10-29T22:30Z")]),
            ("2026-10-29T20:00Z", [(FIVE, 60, "2026-10-29T22:30Z")]),
        ],
        [],
        "FAIL",
        "2026-10-29T22:00Z",
    ),
    (
        [
            ("2026-10-29T19:00Z", [(FIVE, 40, "2026-10-29T21:30Z")]),
            ("2026-10-29T20:00Z", [(FIVE, 60, "2026-10-29T21:30Z")]),
        ],
        ["--scale", "2"],
        "FAIL",
        "2026-10-29T21:00Z",
    ),
    ([("2026-10-29T20:00Z", [(FIVE, 80, "2026-10-29T23:00Z")])], [], "FAIL", "80"),
    ([("2026-10-29T20:00Z", [(FIVE, 79, "2026-10-29T23:00Z")])], [], "PASS", ""),
    (
        [
            ("2026-10-29T19:00Z", [("weekly", 40, "2026-11-04T13:00Z")]),
            ("2026-10-29T20:00Z", [("weekly", 41, "2026-11-04T13:00Z")]),
        ],
        [],
        "PASS",
        "",
    ),
    (
        [
            ("2026-10-29T19:00Z", [("weekly", 40, "2026-11-04T13:00Z")]),
            ("2026-10-29T20:00Z", [("weekly", 41, "2026-11-04T13:00Z")]),
        ],
        ["--hours", "72"],
        "FAIL",
        "2026-11-01T07:00Z",
    ),
    (
        [
            ("2026-10-29T19:00Z", [(FIVE, 10, "2026-10-29T19:30Z")]),
            ("2026-10-29T20:00Z", [(FIVE, 70, "2026-10-30T00:30Z")]),
        ],
        [],
        "PASS",
        "",
    ),
]


@pytest.mark.parametrize(
    "readings, extra, expected, word",
    USAGE,
    ids=[
        "stale",
        "rate-ends-after-reset",
        "rate-ends-before-reset",
        "scaled",
        "at-max",
        "below-max",
        "weekly-within-hours",
        "weekly-over-72h",
        "reset-between-readings",
    ],
)
def test_usage_fails_on_a_stale_reading_a_limit_at_the_maximum_or_a_rate_that_ends_before_the_reset(
    tmp_path, readings, extra, expected, word
):
    r = Run(tmp_path)
    r.usage(readings)
    [(status, detail)] = found(preflight(*r.args("--roles", "planner", "--no-sim", *extra), env=r.env), "usage")
    assert status == expected and word in detail, detail


def test_usage_fails_when_the_file_is_missing(tmp_path):
    r = Run(tmp_path)
    (r.control / "usage.json").unlink()
    [(status, detail)] = found(preflight(*r.args("--roles", "planner", "--no-sim"), env=r.env), "usage")
    assert status == "FAIL" and "usage.json" in detail


def launch_with(r, change):
    (r.run / "_launch.md").write_text(change(LAUNCH), encoding="utf-8")
    return found(preflight(*r.args("--roles", "planner", "--no-sim"), env=r.env), "launch")


def test_the_launch_table_needs_the_key_lines_the_six_cells_by_name_and_one_row_per_role_with_its_settings(tmp_path):
    r = Run(tmp_path)
    header = "| role | lane | work | settings | skills | ECC texts | cost estimate |"
    swapped = "| cost estimate | role | `settings` | lane | ECC texts | skills | work | notes |"  # cells by name, backticks stripped
    rows = LAUNCH.split(header + "\n|---|---|---|---|---|---|---|\n")[1]

    def reorder(text):
        cells = [[c.strip() for c in line.strip("|").split("|")] for line in rows.strip().splitlines()]
        moved = [f"| {c[6]} | {c[0]} | {c[3]} | {c[1]} | {c[5]} | {c[4]} | {c[2]} | - |" for c in cells]
        return text.split(header)[0] + swapped + "\n|---|---|---|---|---|---|---|---|\n" + "\n".join(moved) + "\n"

    assert [s for s, _ in launch_with(r, lambda t: t)] == ["PASS"]
    assert [s for s, _ in launch_with(r, reorder)] == ["PASS"]
    cases = [
        (lambda t: re.sub(r"(?m)^Size:.*\n", "", t), "Size:"),
        (
            lambda t: t.replace(
                "Size: one context cannot hold it: 11 tasks at 120k-180k tokens each, measured on the last run",
                "Size: one context cannot hold it",
            ),
            "Size:",
        ),
        (lambda t: re.sub(r"(?m)^Estimate:.*$", lambda m: m.group(0).replace("$", "USD "), t), "Estimate:"),
        (lambda t: t.replace("one fresh session per unit, ", ""), "Estimate:"),
        (lambda t: t.replace(" cost estimate |", " cost |"), "cost estimate"),
        (lambda t: re.sub(r"(?m)^\| builder-a .*\n", "", t), "builder-a"),
        (lambda t: t + "| critic | - | reviews | `_control/critic-settings.json` | - | - | $5 |\n", "critic"),
        (lambda t: t.replace("`_control/planner-settings.json`", "`planner-settings.json`"), "planner"),
    ]
    for change, word in cases:
        [(status, detail)] = launch_with(r, change)
        assert status == "FAIL" and word in detail, (word, detail)
    (r.control / "_agents-judge.json").unlink()
    [(status, detail)] = launch_with(r, lambda t: t)
    assert status == "FAIL" and "judge" in detail


def test_a_critic_with_no_planner_fails_the_launch_since_nobody_answers_its_findings(tmp_path):
    """2026-10-31: a project's manager chat launched a critic, two builders and a verifier on a plan a harness stage had
    written; the critic's findings had no planner to answer them, the builders waited and the manager wrote the answers
    itself, a role's work. Every role of a run is in the table from the start."""
    r = Run(tmp_path)
    config = json.loads(r.config.read_text(encoding="utf-8"))
    config["agents"]["critic"] = {**config["agents"]["planner"], "settings": "_control/critic-settings.json"}
    del config["agents"]["planner"]
    r.write_json(r.config, config)
    (r.control / "critic-settings.json").write_text(r.planner_settings.read_text(encoding="utf-8"), encoding="utf-8")
    planner_row = re.search(r"(?m)^\| planner .*\n", LAUNCH).group(0)
    critic_row = "| critic | a | attacks the plan | `_control/critic-settings.json` | - | - | $5 |\n"

    def launch(text):  # `launch_with` checks the planner, which this run does not have
        (r.run / "_launch.md").write_text(text, encoding="utf-8")
        return found(preflight(*r.args("--roles", "critic", "--no-sim"), env=r.env), "launch")

    [(status, detail)] = launch(LAUNCH.replace(planner_row, critic_row))
    assert status == "FAIL" and "a critic with no planner" in detail, detail
    config["agents"]["planner"] = {**config["agents"]["critic"], "settings": "_control/planner-settings.json"}
    r.write_json(r.config, config)
    [(status, detail)] = launch(LAUNCH.replace(planner_row, planner_row + critic_row))
    assert status == "PASS", detail


# V3 (10.16): the dollars per unit do not stand for the fresh sessions per unit.
def test_the_estimate_line_needs_the_fresh_sessions_per_unit_and_the_example_asks_for_them(tmp_path):
    r = Run(tmp_path)
    example = (SKILL / "example" / "launch.md").read_text(encoding="utf-8")
    filled = re.sub(r"<[^>]+>", "2", next(line for line in example.splitlines() if line.startswith("Estimate: ")))

    def estimate(line):
        return launch_with(r, lambda t: re.sub(r"(?m)^Estimate:.*$", lambda _: line, t))

    assert estimate(f"Estimate: 3 roles, 12-16 sessions; {MEASURED}; $3-$5 per unit, $50 for the run") == [
        ("FAIL", "Estimate: names no fresh sessions per unit")
    ]
    plural = f"Estimate: 3 roles, two sessions per unit, 12-16 sessions; {MEASURED}; $40-$60 per unit"
    assert [s for s, _ in estimate(plural)] == ["PASS"]
    assert [s for s, _ in estimate(filled)] == ["PASS"], filled


# R5 (spec 003): the price rests on a measurement page, its dollars per session and its start-up read, not on a guess.
def test_the_estimate_line_needs_a_measurement_page_a_cost_per_session_and_a_start_up_read(tmp_path):
    r = Run(tmp_path)
    whole = (
        f"Estimate: 3 roles, one fresh session per unit, 12-16 sessions; {MEASURED}; $40-$60 per unit, $200 for the run"
    )
    assert whole in LAUNCH

    def estimate(line):
        return launch_with(r, lambda t: re.sub(r"(?m)^Estimate:.*$", lambda _: line, t))

    assert [s for s, _ in estimate(whole)] == ["PASS"]
    cuts = (
        ("measurement page", "~/vault/context/measurements/2026-10-29-demo.md", "the last run"),
        ("cost per session", "$2-$3 per session", "$2-$3 each"),
        ("start-up read", "start-up read 58k tokens per fresh session", "58k tokens"),
    )
    for what, part, instead in cuts:
        assert part in whole, part
        assert estimate(whole.replace(part, instead)) == [("FAIL", f"Estimate: names no {what}")], what
    example = (SKILL / "example" / "launch.md").read_text(encoding="utf-8")
    asked = next(line for line in example.splitlines() if line.startswith("Estimate: "))
    assert [s for s, _ in estimate(re.sub(r"<[^>]+>", "2", asked))] == ["PASS"], asked
    page = (SKILL / "references" / "preflight-and-capacity.md").read_text(encoding="utf-8")
    assert all(what in page for what, _, _ in cuts)


def row(name, cwd, status="busy", pid: int | None = 4242):
    """A row of `claude agents --json --all`; a row with no pid is a finished job."""
    return {"id": "ab12cd34", "name": name, "cwd": str(cwd), "status": status, **({"pid": pid} if pid else {})}


# Manager-lessons 14 (2026-10-30): a second manager chat launched a run unseen. `live` lists every live session and
# fails on a busy one outside the run, in the checkout or one of its worktrees, that no `Live:` line names.
def test_live_fails_on_a_busy_outside_session_in_the_checkout_or_a_worktree_unless_a_live_line_names_it(tmp_path):
    r = Run(tmp_path)
    elsewhere, other = tmp_path / "elsewhere", tmp_path / "other-wt"
    # `git worktree add` leaves <checkout>/.git/worktrees/<name>/gitdir
    for name, wt in (("wt-a", r.wt), ("other", other)):
        (r.checkout / ".git" / "worktrees" / name).mkdir(parents=True)
        (r.checkout / ".git" / "worktrees" / name / "gitdir").write_text(f"{wt}/.git\n", encoding="utf-8")

    def live(*rows, launch=lambda t: t, raw=None):
        r.sessions(*rows)
        if raw is not None:
            (tmp_path / "agents.json").write_text(raw, encoding="utf-8")
        (r.run / "_launch.md").write_text(launch(LAUNCH), encoding="utf-8")
        [(status, detail)] = found(preflight(*r.args("--roles", "planner", "--no-sim"), env=r.env), "live")
        return status, detail

    status, detail = live()
    assert status == "PASS" and detail.startswith("0 live sessions"), detail
    mine = (row("planner", r.checkout), row("builder-a", r.wt))  # the run's own sessions are never the problem
    rows = (
        *mine,
        row("chat-away", elsewhere),
        row("chat-idle", r.checkout, "idle"),
        row("job-done", r.checkout, pid=None),
    )
    status, detail = live(*rows)
    assert status == "PASS" and detail.startswith("4 live sessions"), detail  # every name is listed, busy or idle
    assert "builder-a busy" in detail and "chat-idle idle" in detail and "job-done" not in detail, detail
    for where in (r.checkout, r.checkout / "docs", r.wt, other / "sub"):
        status, detail = live(*mine, row("manager-chat", where))
        assert status == "FAIL" and "named in no Live: line: manager-chat (" in detail, (where, detail)
    status, detail = live({"id": "ab12cd34", "name": "mystery", "status": "busy", "pid": 4242})
    assert status == "FAIL" and "mystery (no cwd)" in detail, detail

    named = "\nLive: manager-chat, chat-two — the manager's own chat and the owner's, read in the list\n"
    status, detail = live(row("manager-chat", r.checkout), row("chat-two", r.wt), launch=lambda t: t + named)
    assert status == "PASS" and "manager-chat busy" in detail, detail
    status, detail = live(row("manager-chat", r.checkout), row("third", r.checkout), launch=lambda t: t + named)
    assert status == "FAIL" and "named in no Live: line: third (" in detail and "manager-chat (" not in detail, detail

    agents = {"demo/critic": {"cwd": str(r.plan), "add_dirs": [], "settings": "_control/planner-settings.json"}}
    r.write_json(r.control / "_agents-demo.json", {"agents": agents})  # the run's prefix is the config's `demo/`
    assert live(row("demo/verifier", r.checkout))[0] == "PASS"
    assert live(row("other/verifier", r.checkout))[0] == "FAIL"

    for raw in ('{"agents": []}', "not json"):  # a listing that is not a JSON list fails, it is not an empty list
        status, detail = live(raw=raw)
        assert status == "FAIL" and "claude agents --json --all exit 0, no JSON list" in detail, detail
    r.env["FAKE_AGENTS"] = str(tmp_path / "nowhere.json")
    status, detail = live()
    assert status == "FAIL" and "claude agents --json --all exit 1, no JSON list" in detail, detail
    r.env["PATH"] = str(tmp_path / "no-bin")
    status, detail = live()
    assert status == "FAIL" and "claude agents --json --all did not run" in detail, detail
    page = (SKILL / "references" / "preflight-and-capacity.md").read_text(encoding="utf-8")
    assert "- `live`: " in page and "`Live:`" in page
    assert "`live`" in (SCRIPTS / "manager" / "README.md").read_text(encoding="utf-8")
    assert "`Live:" in (SKILL / "example" / "launch.md").read_text(encoding="utf-8")


# V5 (K2, index row 4): a role cell is an agent name as `_agents.json` writes it (`<project>/planner`). Since Task 11
# the example's settings values sit under `_control/` (K4), so the example's table and configs, `<project>` = demo,
# pass `check_launch` with no problem at all.
def test_the_example_launch_table_has_a_row_for_every_agent_of_the_example_configs(tmp_path):
    spec = importlib.util.spec_from_file_location("preflight", PREFLIGHT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run = tmp_path / "run"
    (run / "_control").mkdir(parents=True)
    for name in ("agents.json", "agents-judge.json"):
        text = (SKILL / "example" / name).read_text(encoding="utf-8").replace("<project>", "demo")
        (run / "_control" / f"_{name}").write_text(text, encoding="utf-8")
    launch = (SKILL / "example" / "launch.md").read_text(encoding="utf-8").replace("<project>", "demo")
    (run / "_launch.md").write_text(re.sub(r"<[^>]+>", "2", launch), encoding="utf-8")
    args = module.parser().parse_args(["check", str(run), "--checkout", str(tmp_path)])
    st = module.State(args, str(run), str(tmp_path), str(run / "_control"), module.parse_time(NOW))
    result = module.check_launch(st)
    assert result.status == "PASS", result.detail


def test_with_yes_every_checked_role_is_named_in_a_yes_line_stamped_no_later_than_now(tmp_path):
    r = Run(tmp_path)
    launch = r.run / "_launch.md"
    judge = ["--config", r.control / "_agents-judge.json", "--roles", "judge", "--no-sim", "--yes"]

    def yes(*args):
        return found(preflight(*r.args(*args), env=r.env), "launch")

    [(status, detail)] = yes("--no-sim", "--yes")
    assert status == "FAIL" and "planner" in detail and "builder-a" in detail
    launch.write_text(LAUNCH + "\nYes: 2026-10-29T19:58Z — planner-b, builder-a — another run\n", encoding="utf-8")
    [(status, detail)] = yes("--no-sim", "--yes")
    assert status == "FAIL" and "planner" in detail and "builder-a" not in detail
    launch.write_text(
        LAUNCH + "\nYes: 2026-10-29T19:58Z — planner, builder-a — the demo run as in the table\n", encoding="utf-8"
    )
    assert [s for s, _ in yes("--no-sim", "--yes")] == ["PASS"]
    assert [s for s, _ in yes("--no-sim")] == ["PASS"]
    [(status, detail)] = yes(*judge)
    assert status == "FAIL" and "judge" in detail
    launch.write_text(
        launch.read_text(encoding="utf-8") + "Yes: 2026-10-29T20:30Z — judge — the final review\n", encoding="utf-8"
    )
    [(status, detail)] = yes(*judge)
    assert status == "FAIL" and "2026-10-29T20:30Z" in detail and "judge" in detail
    launch.write_text(launch.read_text(encoding="utf-8").replace("T20:30Z", "T19:59Z"), encoding="utf-8")
    assert [s for s, _ in yes(*judge)] == ["PASS"]


# R4: stamps the pattern takes and the calendar refuses (day 32, hour 24, 2026 is no leap year, minute 60).
@pytest.mark.parametrize("stamp", ["2026-10-32T10:00Z", "2026-10-29T24:00Z", "2026-02-29T10:00Z", "2026-10-29T19:60Z"])
def test_with_yes_a_stamp_the_calendar_refuses_fails_the_launch_and_the_run_is_still_saved(tmp_path, stamp):
    r = Run(tmp_path)
    line = f"Yes: {stamp} — planner, builder-a — the demo run as in the table"
    (r.run / "_launch.md").write_text(LAUNCH + "\n" + line + "\n", encoding="utf-8")
    (r.control / "preflight.json").write_text('{"written_at": "2026-10-28T09:00Z", "passed": true}\n', encoding="utf-8")
    proc = preflight(*r.args("--yes"), env=r.env)
    assert "Traceback" not in proc.stderr, proc.stderr
    assert found(proc, "launch") == [
        ("FAIL", f"a Yes: line has an impossible time: {line}; no Yes: line names planner, builder-a")
    ]
    assert proc.stdout.splitlines()[-1] == f"preflight: 19 passed, 1 failed, 0 skipped — {r.control}/preflight.json"
    saved = json.loads((r.control / "preflight.json").read_text(encoding="utf-8"))
    assert proc.returncode == 1 and saved["written_at"] == NOW and saved["passed"] is False


def case(root, suite, name, text):
    (root / suite / name).mkdir(parents=True)
    (root / suite / name / "task.yaml").write_text(f"name: {name}\n{text}", encoding="utf-8")


def test_timeout_sums_trials_times_sessions_times_minutes_over_every_session_case(tmp_path):
    case(tmp_path, "s1", "a", "trials: 3\ntimeout_minutes: 15\n")
    case(tmp_path, "s1", "b", "trials: 1\nsessions: 2            # two runs of one stage\ntimeout_minutes: 10\n")
    case(tmp_path, "s1", "c", "session: false   # graded by code\ntimeout_minutes: 99\n")
    case(tmp_path, "s2", "d", "timeout_minutes: 20\n")
    proc = preflight("timeout", tmp_path / "s1", tmp_path / "s2", env={})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.splitlines() == [
        "s1/a: 3 x 1 x 15 min = 45 min",
        "s1/b: 1 x 2 x 10 min = 20 min",
        "s2/d: 1 x 1 x 20 min = 20 min",
        "total: 85 min over 3 session cases (1 code-only skipped)",
    ]
    assert (
        preflight("timeout", tmp_path / "s2" / "d", env={}).stdout.splitlines()[-1]
        == "total: 20 min over 1 session cases (0 code-only skipped)"
    )
    low = preflight("timeout", tmp_path / "s1", tmp_path / "s2", "--check", "84", env={})
    assert low.returncode == 1 and low.stdout.splitlines()[-1].startswith("FAIL timeout:")
    enough = preflight("timeout", tmp_path / "s1", tmp_path / "s2", "--check", "85", env={})
    assert enough.returncode == 0 and enough.stdout.splitlines()[-1].startswith("PASS timeout:")
    case(tmp_path, "s3", "e", "trials: 2\n")
    proc = preflight("timeout", tmp_path / "s3", env={})
    assert proc.returncode == 1 and "FAIL s3/e: a session case without timeout_minutes" in proc.stdout


def tool(timestamp, name, **inputs):
    content = [{"type": "tool_use", "id": "t", "name": name, "input": inputs}]
    return json.dumps(
        {"type": "assistant", "timestamp": timestamp, "message": {"role": "assistant", "content": content}}
    )


def test_polls_finds_a_sleep_inside_a_loop_body_and_nothing_else(tmp_path):
    commands = [
        "while ! grep -q done plan-log.md; do sleep 30; done",  # a `done` before the `do` is no loop end
        "for f in a b; do echo $f; done; sleep 1",
        "until test -s out.txt; do sleep 5; done",
        'python3 -c "import time\nwhile True:\n    time.sleep(5)"',
        "sleep 0.1 && echo ok",
        "while true; do for f in a; do echo $f; done; sleep 5; done",
        "for f in a b; do echo $f; done; sleep 1; while true; do date; done",
    ]
    lines = [json.dumps({"type": "user", "timestamp": "2026-10-29T19:00:00.000Z", "message": {"content": "go"}})]
    lines += [tool(f"2026-10-29T19:0{i}:00.000Z", "Bash", command=c) for i, c in enumerate(commands)]
    lines.append(tool("2026-10-29T19:09:00.000Z", "Write", file_path="x.sh", content="while true; do sleep 1; done"))
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")
    proc = preflight("polls", transcript, env={})
    assert proc.returncode == 1
    hits = [
        int(m.group(1)) for m in re.finditer(rf"(?m)^sleep loop: {re.escape(str(transcript))}:(\d+): ", proc.stdout)
    ]
    assert hits == [2, 4, 5, 7]
    assert proc.stdout.splitlines()[-1] == "polls: 7 Bash commands, 4 sleep loops"
    clean = tmp_path / "clean.jsonl"
    clean.write_text(lines[2] + "\n" + lines[5] + "\n", encoding="utf-8")
    proc = preflight("polls", clean, env={})
    assert proc.returncode == 0 and proc.stdout.splitlines() == ["polls: 2 Bash commands, 0 sleep loops"]


def test_clock_fails_a_time_not_in_date_u_form_and_a_stamp_far_from_its_writer(tmp_path):
    record = tmp_path / "rec.md"
    lines = [
        "- 20:12 UTC (main session): merged main into the plan",
        "- 18:00 UTC (plan fixer): fixed C1",
        "HANDOFF planner after Task 0 — 2026-10-29 20:14",
        "- 23:58 UTC: the last line of the day",
        "- 20:1x UTC: an estimated time",
        "- 07:00 UTC: a line no tool wrote",
        "see lessons.md:147 and test_docs.py:156-160",
    ]
    record.write_text("\n".join(lines) + "\n", encoding="utf-8")
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        "\n".join(
            [
                tool(
                    "2026-10-29T20:13:05.000Z",
                    "Edit",
                    file_path=str(record),
                    old_string="x",
                    new_string=lines[0] + "\n",
                ),
                tool("2026-10-29T20:13:30.000Z", "Bash", command=f"printf '%s\\n' '{lines[1]}' >> rec.md"),
                tool("2026-10-29T20:14:40.000Z", "Write", file_path="handoff.md", content=lines[2] + "\nState: none\n"),
                tool("2026-10-29T21:00:00.000Z", "Bash", command=f"grep -nF -- '{lines[0]}' rec.md"),
                tool("2026-10-30T00:03:00.000Z", "Edit", file_path=str(record), old_string="y", new_string=lines[3]),
                tool("2026-10-30T00:04:00.000Z", "Edit", file_path=str(record), old_string="z", new_string=lines[4]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc = preflight("clock", record, "--transcript", transcript, env={})
    assert proc.returncode == 1
    assert proc.stdout.splitlines() == [
        f"{record}:2: 18:00 UTC was written at 2026-10-29T20:13:30Z, 133 min apart",
        f"{record}:5: not in date -u form: 20:1x",
        "clock: 5 stamped lines, 4 matched a writer, 2 problems",
    ]
    # line 2's gap is 133.5 min: 133 whole minutes, not more than --slack 133, more than --slack 132
    proc = preflight("clock", record, "--transcript", transcript, "--slack", "133", env={})
    assert proc.stdout.splitlines()[-1] == "clock: 5 stamped lines, 4 matched a writer, 1 problems"
    proc = preflight("clock", record, "--transcript", transcript, "--slack", "132", env={})
    assert proc.stdout.splitlines()[-1] == "clock: 5 stamped lines, 4 matched a writer, 2 problems"


def section(text, heading):
    return re.search(rf"(?ms)^{re.escape(heading)}$(.*?)(?=^#{{1,2}} |\Z)", text).group(1)


def test_the_manager_readme_documents_the_usage_line_and_every_option_of_every_subcommand():
    text = section((SCRIPTS / "manager" / "README.md").read_text(encoding="utf-8"), "## preflight.py")
    assert re.search(
        r"(?m)^Usage: python3 -I scripts/manager/preflight\.py check <run-dir> --checkout <checkout>", text
    )
    for sub in ("check", "timeout", "polls", "clock"):
        out = subprocess.run(
            [sys.executable, "-I", str(PREFLIGHT), sub, "--help"], capture_output=True, text=True, check=True
        ).stdout
        options = set(re.findall(r"--[a-z][a-z-]+", out)) - {"--help"}
        assert sorted(o for o in options if o not in text) == [], sub
    assert "--scale" in text and "--yes" in text


def test_the_example_carries_the_launch_table_the_clock_rule_and_the_request_lines():
    launch = (SKILL / "example" / "launch.md").read_text(encoding="utf-8")
    for key in ("Purpose:", "Size:", "Model rule:", "Estimate:", "Budget:", "Usage:", "Yes:"):
        assert re.search(rf"(?m)^{re.escape(key)} ", launch), key
    assert "Launched:" in launch and not re.search(r"(?m)^Launched:", launch)  # C17: the prose only
    header = next(line for line in launch.splitlines() if line.startswith("| role |"))
    assert {"role", "lane", "settings", "skills", "ECC texts", "cost estimate"} <= {
        c.strip() for c in header.strip("|").split("|")
    }
    common = (SKILL / "example" / "common.md").read_text(encoding="utf-8")
    assert re.search(r"(?m)^Request-line bound: (\d+) minutes?\b", common).group(1) == "15"
    for s in (
        "`SANDBOX: <what was refused> — <why the step needs it>`",
        "COPY-REQUEST: <stage> -> <worktree>",
        "`CHECKOUT-REQUEST: <sha>`",
        "`FF-REQUEST: <branch> <sha> -> <branch> <sha>`",
        "`SUPPLIED:`",
        "`COPIED:`",
        "`CHECKED-OUT:`",
        "`FF-DONE:`",
        "`REFUSED: <KIND> — <why>`",
        "Order <msg_id>",
        "`ACK <msg_id>`",
        "`date -u +%Y-%m-%dT%H:%MZ`",
        "timeout -k 10",
    ):
        assert s in common, s


def test_the_reference_pages_carry_preflight_capacity_and_the_launch_settings():
    page = (SKILL / "references" / "preflight-and-capacity.md").read_text(encoding="utf-8")
    assert page.splitlines()[0] == "# Pre-flight and capacity"
    assert re.findall(r"(?m)^### (.*)$", page) == [
        "Pre-flight",
        "The launch table and the yes",
        "Capacity",
        "Timeouts",
        "The clock and polling",
        "Size",
    ]
    for s in (
        "scripts/manager/preflight.py check",
        "_control/usage.json",
        "--scale",
        "--hours",
        "--yes",
        "timeout -k 10",
        "one context cannot hold",
        "one session plus a verifier",
        "monitor_records.py status",
        "fresh sessions per unit",
        "named in its `role` cell as the config names it (`<project>/planner`)",  # V5 (K2)
    ):
        assert s in page, s
    ref = (SKILL / "references" / "launch.md").read_text(encoding="utf-8")
    assert "--model" not in ref and "<run-dir>/_control/<role>-settings.json" in ref
    assert "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE" in ref and "design-plugins.json" in ref


CREDENTIALS = "Read(~/.claude/.credentials.json)"
EXAMPLES = ("builder-a", "builder-b", "critic", "judge", "plan-fixer", "planner", "verifier")


def filled(role, tmp_path):
    """example/<role>-settings.json as the manager fills it: <run-dir> and <checkout> by the run's paths,
    <checkout-entry> and <checkout-file> by names under the checkout, every other placeholder by a path under tmp."""
    fill = {
        "run-dir": str(tmp_path / "run"),
        "checkout": str(tmp_path / "co"),
        "checkout-entry": "docs",
        "checkout-file": "README.md",
    }
    text = (SKILL / "example" / f"{role}-settings.json").read_text(encoding="utf-8")
    return json.loads(re.sub(r"<([a-z-]+)>", lambda m: fill.get(m[1], str(tmp_path / m[1])), text))


def blind(tmp_path, role, settings, *unsandboxed):
    """`check_blind` on one role's settings, with the run at <tmp>/run and the checkout at <tmp>/co."""
    spec = importlib.util.spec_from_file_location("preflight", PREFLIGHT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run, co = tmp_path / "run", tmp_path / "co"
    argv = ["check", str(run), "--checkout", str(co), *(x for r in unsandboxed for x in ("--unsandboxed", r))]
    st = module.State(
        module.parser().parse_args(argv), str(run), str(co), str(run / "_control"), module.parse_time(NOW)
    )
    st.settings[role] = settings
    result = module.check_blind(st, role)
    return result.status, result.detail


@pytest.mark.parametrize(
    "key, value, problem",
    [
        ("deny", CREDENTIALS, f"missing {CREDENTIALS}"),
        ("denyRead", "~/.claude/.credentials.json", "missing sandbox.filesystem.denyRead ~/.claude/.credentials.json"),
    ],
)
def test_blind_refuses_settings_that_leave_the_credentials_file_readable(tmp_path, key, value, problem):
    """J6 (judge.md of manager-build-2026-10-29, #### J6): the seven example settings let a session read
    ~/.claude/.credentials.json; the pre-flight needs the Read() deny and the denyRead entry."""
    settings = filled("critic", tmp_path)
    place = settings["permissions"] if key == "deny" else settings["sandbox"]["filesystem"]
    place[key] = [x for x in place[key] if x != value]
    assert blind(tmp_path, "critic", settings) == ("FAIL", problem)


SINGLE = "single-slash {}: write //<path> for the root, <path> for the cwd"


@pytest.mark.parametrize("role", EXAMPLES)
def test_each_filled_example_passes_blind_and_a_single_slash_edit_or_write_rule_fails_it(tmp_path, role):
    """J8 (judge.md of manager-build-2026-10-29, #### J8): the pre-flight and the eval grader read `Edit(/x)` in two
    ways; until the runtime says which, the pre-flight refuses any single-slash Edit or Write rule, for every role."""
    settings = filled(role, tmp_path)
    assert blind(tmp_path, role, settings) == ("PASS", "the ten deny rules are set")
    settings["permissions"]["deny"] += ["Edit(/x)", "Write(/y/**)", "Edit(//x)", "Edit(x)", "Edit(~/x)"]
    for unsandboxed in ((), (role,)):
        assert blind(tmp_path, role, settings, *unsandboxed) == ("FAIL", SINGLE.format("Edit(/x), Write(/y/**)"))


def test_blind_fails_a_role_whose_include_co_authored_by_is_absent_or_not_the_boolean_false(tmp_path):
    """The owner's order of 2026-10-30 (lessons.md:31): Claude Code's default commit trailer is `Co-Authored-By: <model>
    <noreply@anthropic.com>` and a role is blind to models. In 2.1.314 only the boolean `false` blanks it (an absent key,
    `true`, `null`, a string or a number leaves it), so each is a FAIL for every role, sandboxed or not."""
    settings = filled("critic", tmp_path)
    wrong = [{k: v for k, v in settings.items() if k != "includeCoAuthoredBy"}]
    wrong += [{**settings, "includeCoAuthoredBy": value} for value in (None, True, "false", 0)]
    for unsandboxed in ((), ("critic",)):
        assert blind(tmp_path, "critic", settings, *unsandboxed) == ("PASS", "the ten deny rules are set")
        failed = [blind(tmp_path, "critic", s, *unsandboxed) for s in wrong]
        assert failed == [("FAIL", "missing includeCoAuthoredBy false")] * len(wrong)


ATTRIBUTION = "attribution is set: it can bring the model's trailer back; remove the key"


def test_blind_fails_a_role_whose_settings_carry_an_attribution_key_with_the_trailer_key_at_false(tmp_path):
    """V1 (verify.md of pipeline-economy-2026-10-30, #### V1): in 2.1.314 a valid `attribution` object, one with a
    `commit` or a `pr`, wins over `includeCoAuthoredBy`, and `{"pr": ""}` leaves the commit text at the default
    `Co-Authored-By: <model> <noreply@anthropic.com>`. The pre-flight refuses the key for every role, whatever it
    holds."""
    settings = filled("critic", tmp_path)
    held = (
        {"pr": ""},
        {"commit": "Co-Authored-By: <model> <noreply@anthropic.com>"},
        {"commit": ""},
        {},
        None,
        False,
    )
    both = {k: v for k, v in settings.items() if k != "includeCoAuthoredBy"} | {"attribution": {"pr": ""}}
    for unsandboxed in ((), ("critic",)):
        failed = [blind(tmp_path, "critic", {**settings, "attribution": a}, *unsandboxed) for a in held]
        assert failed == [("FAIL", ATTRIBUTION)] * len(held)
        both_failed = blind(tmp_path, "critic", both, *unsandboxed)
        assert both_failed == ("FAIL", f"missing includeCoAuthoredBy false; {ATTRIBUTION}")


WARM = 'python3 "/c/.claude/hooks/keep-cache-warm.py"'


def test_the_cache_check_fails_a_lane_without_the_warm_cache_hooks(tmp_path):  # owner, 2026-11-01
    r = Run(tmp_path)
    r.edit(r.planner_settings, lambda s: s.pop("hooks"))
    r.edit(r.builder_settings, lambda s: s["hooks"].pop("Stop"))
    proc = preflight(*r.args(), env=r.env)
    [(status, planner)] = found(proc, "cache", "planner")
    assert status == "FAIL" and "no keep-cache-warm.py pretool hook on Bash" in planner and "stop hook" in planner
    [(status, builder)] = found(proc, "cache", "builder-a")
    assert status == "FAIL" and "pretool" not in builder and "no keep-cache-warm.py stop hook" in builder


def test_the_cache_check_fails_a_lane_without_compaction_its_own_pack_the_5m_ttl_or_its_model(tmp_path):
    """The cache and context rules of 2026-11-01 (owner): the pre-flight names each one a lane breaks."""
    r = Run(tmp_path)
    r.edit(r.config, lambda c: (c["common"].remove("--autocompact"), c["common"].remove("235000")))
    r.edit(r.config, lambda c: c["common"].remove("--exclude-dynamic-system-prompt-sections"))
    r.edit(r.config, lambda c: c["agents"]["planner"].pop("extra_prompt"))
    r.edit(r.planner_settings, lambda s: (s["env"].update(CLAUDE_CODE_PROMPT_CACHE_TTL="1h"), s.pop("model")))
    (r.run / "_pack-builder-a.md").unlink()
    r.edit(r.config, lambda c: c.update(cap=200_000, handoff_at=150_000))
    r.edit(r.config, lambda c: (c["common"].remove("--system-prompt-snapshot"), c["common"].remove("on")))
    proc = preflight(*r.args(), env=r.env)
    assert proc.returncode == 1
    [(status, planner)] = found(proc, "cache", "planner")
    assert status == "FAIL"
    for problem in (
        "common has no --autocompact",
        "common has no --exclude-dynamic-system-prompt-sections",
        "common has no --system-prompt-snapshot on",
        "handoff_at 150000 and cap 200000 must lie above the compaction point",
        "no extra_prompt of its own",
        "TTL is not 5m",
        "no model",
    ):
        assert problem in planner, planner
    [(status, builder)] = found(proc, "cache", "builder-a")
    assert status == "FAIL" and "its pack _pack-builder-a.md is not a file of the run folder" in builder


def test_the_cache_check_fails_a_pack_outside_the_run_folder_or_without_its_mark(tmp_path):
    r = Run(tmp_path)
    (r.root / "_pack-out.md").write_text("# Your standing orders (startup pack of demo/planner)\n", encoding="utf-8")
    r.edit(r.config, lambda c: c["agents"]["planner"]["extra_prompt"].update(file="../_pack-out.md"))
    (r.run / "_pack-builder-a.md").write_text("# another lane's head\n", encoding="utf-8")
    proc = preflight(*r.args(), env=r.env)
    [(_, planner)] = found(proc, "cache", "planner")
    [(_, builder)] = found(proc, "cache", "builder-a")
    assert "its pack ../_pack-out.md is not a file of the run folder" in planner
    assert "its pack _pack-builder-a.md does not hold its mark" in builder
