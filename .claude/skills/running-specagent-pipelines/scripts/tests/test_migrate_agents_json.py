"""Tests of migrate_agents_json.py on synthetic run folders: a live watcher copy (parsed with ast, never imported) and
its config become `_agents-v2.json`, and the behaviour that differs from watch_agents.py's defaults is printed.

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
"""

import json
import pathlib
import subprocess
import sys
import textwrap

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = SCRIPTS / "migrate_agents_json.py"

# An earlier run's form: LANG appended by a dict comprehension and +=, the order an f-string on RUN.
DICT_STYLE = """
import json, pathlib, sys, time
pathlib.Path({marker!r}).write_text("imported")
CAP = 200_000
HANDOFF_WAIT = 20 * 60
config = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
RUN = pathlib.Path(config['run_dir'])
NUDGE = ('Nudge text. '
         'Second part.')
HANDOFF_ORDER = ('Order: write the note as '
                 f'{{RUN}}/_handoff-rule.md says.')
FRESH = {{
    'builder': ('Fresh builder: read {{run}}/_builder-assignment.md.'),
    'critic': 'Fresh critic.',
}}
LANG = ' English only.'
FRESH = {{role: text + LANG for role, text in FRESH.items()}}
NUDGE += LANG
HANDOFF_ORDER += LANG
UNBLOCK = ('Unblock text.')
revived, blocked_since = {{}}, {{}}
for _ in range(int(sys.argv[2]) if len(sys.argv) > 2 else 240):
    first = blocked_since.setdefault('x', time.time())
    if time.time() - first < 900:
        pass
    revived['x'] = revived.get('x', 0) + 1
    if revived['x'] > 4:
        pass
    time.sleep(90)
"""

# Another run's form: LATE.format, no LANG, no permission-prompt wait, startup packs and an extra prompt in the config.
FORMAT_STYLE = """
import json, pathlib, sys, time
CAP = 200_000
HANDOFF_WAIT = 20 * 60
config = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
RUN = pathlib.Path(config['run_dir'])
NUDGE = (%(nudge)r)
HANDOFF_ORDER = ('Orders: see '
                 f'{RUN}/_handoff-rule.md.')
LATE = ('The note carries the state: open {files} only when needed. ')
FRESH = {
    'builder': ('Fresh builder. '
                + LATE.format(files='build-log.md, verify.md') +
                'Build the unit the note names.'),
}
USE_PACK = config.get('pack', False)
if USE_PACK:
    FRESH['builder'] = 'pack text'
EXTRA_PROMPT = config.get('extra_prompt')
for _ in range(240):
    for name, row in {}.items():
        if row.get('state') in ('blocked', 'failed'):
            pass
        if revived[name] > 6:
            pass
    time.sleep(120)
"""


def agents(*roles: str) -> dict:
    return {
        f"t/{r}": {
            "cwd": "/c",
            "add_dirs": ["/a"],
            "settings": f"_{r}-settings.json",
            "status": "build-log.md",
            "final": "STATUS: done",
        }
        for r in roles
    }


def migrate(run: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(run), *args], capture_output=True, text=True, timeout=30, check=False
    )


def defaults() -> dict:
    code = (
        "import json, sys; sys.dont_write_bytecode = True; sys.path.insert(0, sys.argv[1]); import watch_agents; "
        "print(json.dumps(watch_agents.DEFAULTS))"
    )
    return json.loads(
        subprocess.run(
            [sys.executable, "-I", "-c", code, str(SCRIPTS)], capture_output=True, text=True, check=True
        ).stdout
    )


@pytest.fixture
def run(tmp_path) -> pathlib.Path:
    path = tmp_path / "run"
    path.mkdir()
    return path


def test_a_dict_comprehension_form_is_read_without_importing_it(run, tmp_path):
    marker = tmp_path / "imported"
    (run / "_watch_agents.py").write_text(DICT_STYLE.format(marker=str(marker)), encoding="utf-8")
    (run / "_agents.json").write_text(
        json.dumps(
            {
                "run_dir": str(run),
                "common": ["--model", "opus"],
                "blocked_files": ["build-log.md"],
                "agents": agents("builder", "critic"),
            }
        ),
        encoding="utf-8",
    )
    before = sorted(p.name for p in run.iterdir())
    r = migrate(run)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not marker.exists()
    assert sorted(p.name for p in run.iterdir()) == sorted(before + ["_agents-v2.json"])
    v2 = json.loads((run / "_agents-v2.json").read_text())
    assert v2["run_dir"] == str(run) and v2["common"] == ["--model", "opus"]
    assert v2["blocked_files"] == ["build-log.md"] and v2["agents"] == agents("builder", "critic")
    assert v2["lang"] == " English only."
    assert v2["nudge"] == "Nudge text. Second part."
    assert v2["handoff_order"] == "Order: write the note as {run}/_handoff-rule.md says."
    assert v2["unblock"] == "Unblock text."
    assert v2["fresh"] == {"builder": "Fresh builder: read {run}/_builder-assignment.md.", "critic": "Fresh critic."}
    assert (v2["permission_wait"], v2["nudges"], v2["interval"]) == (900, 4, 90)
    assert "cap" not in v2 and "handoff_wait" not in v2  # the defaults' values
    assert "config: _agents.json" in r.stdout
    assert "permission_wait: 600 -> 900" in r.stdout and "nudges: 6 -> 4" in r.stdout
    assert "fresh.builder" in r.stdout and "lang" in r.stdout


def test_a_format_form_prefers_the_active_config_and_reports_what_v2_does_differently(run):
    d = defaults()
    (run / "_watch_agents.py").write_text(FORMAT_STYLE % {"nudge": d["nudge"]}, encoding="utf-8")
    config = {
        "run_dir": str(run),
        "common": [],
        "blocked_files": [],
        "pack": False,
        "extra_prompt": {"file": "_caveman.md", "mark": "Caveman voice is on"},
    }
    (run / "_agents.json").write_text(json.dumps({**config, "agents": agents("builder", "critic")}))
    (run / "_agents-active.json").write_text(json.dumps({**config, "agents": agents("builder", "plan-fixer")}))
    r = migrate(run)
    assert r.returncode == 0, r.stdout + r.stderr
    v2 = json.loads((run / "_agents-v2.json").read_text())
    assert v2["agents"] == agents("builder", "plan-fixer")
    assert v2["pack"] is False and v2["extra_prompt"] == config["extra_prompt"]
    assert v2["permission_wait"] is None  # no permission-prompt wait: a block exits at once
    assert v2["lang"] == "" and "nudge" not in v2
    assert v2["fresh"] == {
        "builder": "Fresh builder. The note carries the state: open build-log.md, verify.md only "
        "when needed. Build the unit the note names."
    }
    assert v2["handoff_order"] == "Orders: see {run}/_handoff-rule.md."
    assert "config: _agents-active.json" in r.stdout
    assert "fresh.plan-fixer: no text in this copy" in r.stdout
    assert "is blocked" in r.stdout and "failed" in r.stdout  # the wording of the exit events
    assert "pack" in r.stdout


def test_the_written_config_is_one_the_watcher_accepts(run):
    (run / "_watch_agents.py").write_text(FORMAT_STYLE % {"nudge": "x"}, encoding="utf-8")
    (run / "_agents.json").write_text(json.dumps({"run_dir": str(run), "agents": agents("builder")}))
    for name in ("_builder-settings.json", "build-log.md"):
        (run / name).write_text("{}\n")
    assert migrate(run).returncode == 0
    code = (
        "import sys; sys.dont_write_bytecode = True; sys.path.insert(0, sys.argv[1]); import watch_agents; "
        "w = watch_agents.Watcher(sys.argv[2]); print(w.permission_wait, repr(w.lang), w.nudge)"
    )
    r = subprocess.run(
        [sys.executable, "-I", "-c", code, str(SCRIPTS), str(run / "_agents-v2.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (r.returncode, r.stdout) == (0, "None '' x\n"), r.stderr


def test_out_writes_the_config_elsewhere_and_leaves_the_run_folder_alone(run, tmp_path):
    (run / "_watch_agents.py").write_text(FORMAT_STYLE % {"nudge": "x"}, encoding="utf-8")
    (run / "_agents.json").write_text(json.dumps({"run_dir": str(run), "agents": agents("builder")}))
    before = sorted(p.name for p in run.iterdir())
    out = tmp_path / "elsewhere" / "demo-agents-v2.json"
    r = migrate(run, "--out", str(out))
    assert r.returncode == 0, r.stdout + r.stderr
    assert sorted(p.name for p in run.iterdir()) == before
    assert json.loads(out.read_text())["run_dir"] == str(run) and f"wrote: {out}" in r.stdout


def test_missing_inputs_exit_2(run):
    r = migrate(run)
    assert r.returncode == 2 and "no _agents-active.json or _agents.json" in r.stdout
    (run / "_agents.json").write_text(json.dumps({"run_dir": str(run), "agents": {}}))
    r = migrate(run)
    assert r.returncode == 2 and "no _watch_agents.py" in r.stdout
    assert not (run / "_agents-v2.json").exists()


def test_a_value_the_parser_cannot_read_is_reported_not_guessed(run):
    source = textwrap.dedent("""
        import os
        CAP = int(os.environ.get('CAP', '200000'))
        NUDGE = 'n'
        FRESH = {'builder': 'b'}
    """)
    (run / "_watch_agents.py").write_text(source)
    (run / "_agents.json").write_text(json.dumps({"run_dir": str(run), "agents": agents("builder")}))
    r = migrate(run)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CAP: not a literal" in r.stdout
    assert "cap" not in json.loads((run / "_agents-v2.json").read_text())
