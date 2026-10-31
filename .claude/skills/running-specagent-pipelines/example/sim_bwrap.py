"""Build a bwrap in the order Claude Code was seen to use (2026-10-29, read from a live role's /proc/<pid>/cmdline) and run a
probe inside it, so a settings file is checked before a rollout: --ro-bind / /, writable binds (cwd, add-dirs, allowWrite,
/tmp/claude-1000), a tmpfs over each denyRead folder and a read-only bind of /dev/null over each other denyRead path (as
Claude Code 2.1.314 does, references/sandbox-and-blindness.md "A file in denyRead"), read-only binds over every Edit(...)
deny and denyWrite path; a leading `~/` is the home directory in each of them, as Claude Code expands it.
Usage: sim_bwrap.py <run>/_control/_agents.json <agent name> '<bash probe>'"""

import json
import os
import pathlib
import re
import subprocess
import sys

agents_json, name, probe = sys.argv[1], sys.argv[2], sys.argv[3]
run_dir = os.path.dirname(os.path.dirname(os.path.abspath(agents_json)))
cfg = json.loads(pathlib.Path(agents_json).read_text(encoding="utf-8"))
a = cfg["agents"][name]
s = json.loads(
    pathlib.Path(a["settings"] if a["settings"].startswith("/") else f"{run_dir}/{a['settings']}").read_text(
        encoding="utf-8"
    )
)
fs = s["sandbox"]["filesystem"]
home = os.path.expanduser
norm = lambda r: "/" + re.sub(r"/\*\*$", "", home(r[5:-1])).lstrip("/")
argv = ["bwrap", "--new-session", "--die-with-parent", "--unshare-pid", "--unshare-user", "--ro-bind", "/", "/"]
for d in [a["cwd"], *a["add_dirs"], *map(home, fs.get("allowWrite", [])), "/tmp/claude-1000"]:
    argv += ["--bind-try", d, d]
for d in map(home, fs.get("denyRead", [])):
    if os.path.isdir(d):
        argv += ["--tmpfs", d]
    elif os.path.exists(d):
        argv += ["--ro-bind", "/dev/null", d]
edit_deny = [norm(r) for r in s["permissions"]["deny"] if r.startswith("Edit(")]
for d in edit_deny + [home(d) for d in fs.get("denyWrite", [])]:
    argv += ["--ro-bind-try", d, d]
argv += ["--dev", "/dev", "--proc", "/proc", "--chdir", a["cwd"], "--", "bash", "-c", probe]
r = subprocess.run(argv, capture_output=True, text=True, check=False)
print(r.stdout + r.stderr, end="")
