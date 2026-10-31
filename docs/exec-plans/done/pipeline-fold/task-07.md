# Task 7 — The judge's conditions on the manager: J4-J11 of the manager-build run

builder: b
depends_on: 4, 5
milestone: M2

## Goal
The manager-build judge (run `manager-build-2026-10-29`, `judge.md`, verdict "release with conditions") left three
majors on the branch, J5, J6 and J10, and five minors, J4, J7, J8, J9 and J11, plus J1's wording. Each becomes one
test and one fix here, so the next launch (Task 6's measurement run) starts with every condition met. J3 is the
vault's and is done (`decisions/global/models-per-role.md`, 2026-10-30); J2 is a wording of the spec outside the
repository and stays in the judge's record.

**Files:**
- Modify: `.claude/skills/running-specagent-pipelines/example/{builder-a,builder-b,critic,judge,plan-fixer,planner,verifier}-settings.json`
- Modify: `.claude/skills/running-specagent-pipelines/example/sim_bwrap.py`, `example/README.md`, `example/common.md`, `scripts/tests/test_skill_example.py`
- Modify: `.claude/skills/running-specagent-pipelines/scripts/manager/preflight.py`, `scripts/tests/test_preflight.py`, `references/preflight-and-capacity.md`
- Modify: `.claude/skills/running-specagent-pipelines/scripts/watch_agents.py`, `scripts/tests/test_watch_agents.py`, `scripts/docs/watch_agents.md`
- Modify: `.claude/skills/running-specagent-pipelines/SKILL.md`, `scripts/tests/test_skill_md.py`
- Modify: `.claude/skills/running-specagent-pipelines/scripts/collect_run.py`, `scripts/tests/test_collect_run.py`, `scripts/docs/collect_run.md`
- Modify: `.claude/skills/running-specagent-pipelines/scripts/check_formats.py`, `scripts/tests/test_check_formats.py`, `scripts/docs/check_formats.md`
- Modify: `.claude/skills/running-specagent-pipelines/scripts/manager/surface.py`, `scripts/tests/test_surface.py`, `scripts/manager/README.md`, `scripts/README.md`
- Modify: `.claude/skills/running-specagent-pipelines/references/sandbox-and-blindness.md`, `references/measuring.md`
- Modify: `.claude/skills/running-specagent-pipelines/example/lessons.md` (one line under "Known error classes")
- Modify: `.claude/skills/running-specagent-pipelines/example/critic-assignment.md`, `example/verifier-assignment.md`, `references/choosing-roles-and-skills.md` (R11, B5)
- Modify: `docs/exec-plans/done/manager-build/task-11.md` (line 806, the TD-016 quote)

**Interfaces:**
- Consumes: `preflight.py`'s `NINE` deny list (`:32-42`) and `check_blind(st, role)` (`:197-208`: its `need` holds
  the `denyRead` paths; every missing item goes into one problem, `missing a, b`), `State` (`:72-84`), `parser()`; `Watcher.match(name, rows)` (watch_agents.py, rule 3 "the newest of its name");
  `collect_run.check_kept` and `also_deletions`; `check_formats.merged_error(marker, sha, config, repo)`;
  `surface.load_registry(run_dir)`; the watcher config's `registry` field (`scripts/README.md`, "registry" row).
- Produces: the seven settings with `Read(~/.claude/.credentials.json)` in `permissions.deny` and
  `~/.claude/.credentials.json` in `sandbox.filesystem.denyRead`; `example/sim_bwrap.py` masking a file as the runtime does;
  `preflight.py` requiring both; `Watcher.match` rule 3 adopting only a row whose real `cwd` is the agent's and, before the first
  launch, one started after the first `Yes:` line of `_launch.md` minus 5 s (`Watcher.yes_floor`);
  `preflight.py` refusing a single-slash `Edit(/x)` or `Write(/x)` rule; `surface.py --config P` and
  `surface.registry_path(run_dir, config)`, the config's `registry` path passed to `load_registry` and `run_start`;
  `check_formats.merged_error` checking the marker in `--repo` when no named checkout is a directory; `collect_run.also_deletions` refusing a path inside the run folder other than `scratch/`.

## Rules
- One finding, one test, one fix, in the order J6, J5, J10, J4, J7, J9, J8, J11, J1, then R11 and B5 (Step 8a); every test is written and run
  red before its fix. Quote the judge's place (`judge.md` of the manager-build run, `#### J<n>`) in the test's docstring.
- Step 1 pins the sandbox form of J6 in the installed runtime's code (checked 2026-10-30 on 2.1.314: a file in
  `denyRead` gets a read-only bind of `/dev/null`, a folder a tmpfs), so the examples get both the `Read()` deny and
  the `denyRead` entry, and the sim, which put a tmpfs on every `denyRead` path (`bwrap: Can't mkdir <file>: Not a
  directory`, pre-flight of 2026-10-30 05:5x), masks a file the runtime's way.
- Nothing is launched: the proof for the live half of J6 and J10 is the next run's pre-flight and
  `measure_manager.py reads`, named in the lesson line.

- [ ] **Step 0: The base holds Tasks 4 and 5 and lane a's fixes (C37)**

Task 4 (lane a) edits `scripts/watch_agents.py`, `scripts/check_formats.py`, their tests, `scripts/README.md`,
`scripts/docs/watch_agents.md` and `SKILL.md` before this task, and lane a's fixes 0d2445f (V9, V10, R10), 6c63d19
(R8, R9) and 13f0d1d (V11, which holds both) change them again; lane b receives lane a's commits only through the main
session's merge (`lessons.md`, "Read first" item 3), not with the done line.

Run: `grep -n '^Task [45]: done' /home/tite/Desktop/agent-system-run/pipeline-fold-2026-10-30/build-log.md /home/tite/Desktop/agent-system-run/pipeline-fold-2026-10-30/build-log-b.md`,
then `for s in 3c80656 3f5ff76 13f0d1d; do git -C /home/tite/Desktop/agentic-flow-template/pipeline-fold-b merge-base --is-ancestor $s HEAD; echo "$s $?"; done`
Expected: `Task 4: done — 3c80656` and `Task 5: done — 3f5ff76`, then `0` after each of the three shas (true at lane
b's 59d3953). On a `1`, wait in the background with `python3
/home/tite/Desktop/agent-system-run/pipeline-fold-2026-10-30/wait_for_log.py
/home/tite/Desktop/agent-system-run/pipeline-fold-2026-10-30/lessons.md <its line count>` until the main session's
`Merged: a->b` or `Merged: a+b` line is there, then run the check again. Merge nothing yourself.

- [ ] **Step 1: Pin the runtime's rule for a file in `denyRead` (C34)**

The installed runtime is one native binary with no `.js` beside it, so the check reads the binary.
Run: `B=$(readlink -f "$(command -v claude)"); echo "$B"; LC_ALL=C grep -a -o 'file mask already covers: [ -~]\{0,110\}' "$B" | sort -u`
and `LC_ALL=C grep -a -c -F 'Merged with paths from Read(...) deny permission rules' "$B"`
Expected (checked 2026-10-30): `/home/tite/.local/share/claude/versions/2.1.314`; two lines, the first
`` file mask already covers: ${Xe} -> ${xn}`);continue}xt.add(xn),w.push("--ro-bind","/dev/null",xn),Kn.push({source:"/dev/null",landing:xn ``
(the read-deny loop binds `/dev/null` over a path that is not a folder; a folder gets a tmpfs), the second
`file mask already covers: J`; then `2` (the settings schema: `denyRead` paths are "Merged with paths from Read(...)
deny permission rules"). Under a new heading `## A file in denyRead` of `references/sandbox-and-blindness.md`, quote
the first line with the binary's version and the sentence it proves: "Claude Code 2.1.314 masks a file in `denyRead`
with a read-only bind of `/dev/null` and a folder with a tmpfs; an update can change it, and the next pre-flight's
`blind` check is the live proof." Another version without such a line: stop and send the plan fixer the output.
(`grep` here is ugrep: a leading `[ -~]\{0,200\}` stops with "exceeds complexity limits"; the trailing class works.)

- [ ] **Step 2: J6, the tests (A18)**

In `scripts/tests/test_preflight.py` (lines at lane b's 59d3953) the fixtures take the new rule first, or every
pre-flight test fails `blind` once the fix lands: `NINE` (`:22-32`) becomes `TEN`, with
`"Read(~/.claude/.credentials.json)",` after `"Bash(pgrep:*)",` (`:31`); `Run.settings`' `for r in NINE]` (`:196`)
becomes `for r in TEN]`; its `denyRead` (`:205`) gains `"~/.claude/.credentials.json"` after
`f"{self.checkout}/docs/handoff"`. Then append (`filled` and `blind` serve Step 7's J8 test too):

```python
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
```

In `scripts/tests/test_skill_example.py` (lines at 59d3953): `import os` and `import subprocess` join the imports
(`:10-12`); the `BLIND` tuple's last line (`:147`) becomes
`         "Bash(pgrep:*)", "Read(~/.claude/.credentials.json)")  # fmt: skip`; `SANDBOXED` (`:148`) gains
`"~/.claude/.credentials.json"` as its fourth path (the tests at `:151` and `:157` then pin the examples' new entries).
Append (nested bwrap cannot make namespaces here, so a fake `bwrap` prints its argv; a `cat` through a `/dev/null`
mask reads as success, so no test judges the mask by a read):

```python
def test_sim_bwrap_masks_a_file_in_deny_read_with_dev_null_and_a_folder_with_a_tmpfs(tmp_path):
    """J6 (judge.md of manager-build-2026-10-29, #### J6) and Step 1: Claude Code 2.1.314 binds /dev/null over a file
    in denyRead and mounts a tmpfs over a folder; the sim put a tmpfs on both, which bwrap refuses for a file."""
    secret, folder, cwd, control = tmp_path / "secret.json", tmp_path / "hidden", tmp_path / "wt", tmp_path / "_control"
    for d in (folder, cwd, control, tmp_path / "bin"):
        d.mkdir()
    secret.write_text("{}\n", encoding="utf-8")
    settings = {"permissions": {"deny": []}, "sandbox": {"filesystem": {"denyRead": [str(secret), str(folder)]}}}
    (control / "s.json").write_text(json.dumps(settings), encoding="utf-8")
    agents = {"agents": {"t/a": {"cwd": str(cwd), "add_dirs": [], "settings": "_control/s.json"}}}
    (control / "_agents.json").write_text(json.dumps(agents), encoding="utf-8")
    fake = tmp_path / "bin" / "bwrap"  # a nested bwrap cannot make namespaces here: the fake prints the argv it gets
    fake.write_text(f"#!{sys.executable}\nimport sys\nprint(' '.join(sys.argv[1:]))\n", encoding="utf-8")
    fake.chmod(0o755)
    env = {**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"}
    argv = [sys.executable, "-I", str(EXAMPLE / "sim_bwrap.py"), str(control / "_agents.json"), "t/a", "true"]
    out = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=30, check=False).stdout
    assert f"--ro-bind /dev/null {secret} " in out and f"--tmpfs {folder} " in out
    assert f"--tmpfs {secret} " not in out
```

- [ ] **Step 3: J6, run red, then fix**

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_preflight.py -k credentials; python3 -m pytest -q tests/test_skill_example.py -k "blind_to or runs_sandboxed or sim_bwrap")`
Expected: `2 failed`, then `3 failed` (the examples and the pre-flight lack the rule; the sim puts a tmpfs on the file).
Fix: in the seven `example/*-settings.json`, `Read(~/.claude/.credentials.json)` joins `permissions.deny` and
`~/.claude/.credentials.json` joins `sandbox.filesystem.denyRead`. `scripts/manager/preflight.py`: `NINE` (`:32-42`)
becomes `TEN` with the same rule (every use renamed); `check_blind`'s `need` (`:206`) gains
`"~/.claude/.credentials.json"`; its pass text (`:208`) reads "the ten deny rules are set" (Step 7's J8 test pins it).
`example/sim_bwrap.py:29-31`: a folder gets `--tmpfs`, any other existing path `--ro-bind /dev/null <path>`; its
docstring (`:3`, "tmpfs over denyRead") says both. Texts: `references/preflight-and-capacity.md:14-15` (`blind`: "the
nine rules" -> ten, the credentials file named, "the same three paths" -> four); `references/sandbox-and-blindness.md:10`
(the `denyRead` list names `~/.claude/.credentials.json`) and `:14-15` ("then tmpfs over each `denyRead` path" -> a
tmpfs over each folder and `/dev/null` over each file, as `## A file in denyRead` shows); `example/README.md:63-65`
(the deny list and `filesystem.denyRead` name the credentials file); `example/common.md:23-24` ("Credentials never:
nothing under `~/.config/`, and never `~/.claude/.credentials.json`.").
Run the same command. Expected: `2 passed`, then `3 passed`.

- [ ] **Step 4: J5, the tests (A19)**

In `scripts/tests/test_watch_agents.py` (lines at 59d3953) the helpers change first, or the cwd rule fails 59 of the
112 watcher tests (`row()` plants `"cwd": "/x"`, and the agents run in the checkout): `row()` (`:73-93`) gains
`cwd: str | None = None,` after `age: int = 3600,` (`:80`), drops `"cwd": "/x",` (`:89`), and its optional-field
update (`:92`) becomes `(("status", status), ("pid", pid), ("waitingFor", waiting), ("cwd", cwd)) if v})`;
`Pipeline.rounds()` gives each row without a cwd the checkout's, after `data = [...]` (`:183`):

```python
        for answer in data:  # a row without a cwd runs in the checkout, the agents' cwd (J5)
            for r in answer.get("rows", []):
                r.setdefault("cwd", str(self.checkout))
```

Then append (`before-yes`: a row of the agent's cwd started before the first `Yes:` line; `after-yes`: one started
after it, with entries made in the run folder later, A19's case):

```python
ELSEWHERE = row(sid=SID2, state="stopped", status=None, pid=None, age=60, cwd="/elsewhere")  # an earlier run's


@pytest.mark.parametrize(
    "rows, adopted",
    [
        ([ELSEWHERE, row(age=3600)], SID),  # the newer namesake, stopped, ran in another folder
        ([ELSEWHERE], None),  # no row in the agent's cwd: no session, and nothing revived
    ],
    ids=["older-here", "elsewhere-only"],
)
def test_rule_3_adopts_only_a_namesake_in_the_agent_s_cwd(p, rows, adopted):
    """J5 (judge.md of manager-build-2026-10-29, #### J5): with launched_at None, rule 3 adopted the newest row of the
    agent's name from any folder, so an earlier run's session of the same name was adopted, then revived."""
    p.rounds(rows)
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert registry(p)["roles"]["t/builder"]["session_id"] == adopted
    assert p.calls() == []  # by name alone, the stopped SID2 was adopted and revived


@pytest.mark.parametrize("age, adopted", [(3600, None), (600, SID)], ids=["before-yes", "after-yes"])
def test_rule_3_before_a_launch_adopts_a_row_started_after_the_first_yes_line(p, age, adopted):
    """J5, C35: before the watcher's first launch, rule 3's floor is the first `Yes:` line of `_launch.md` minus 5 s,
    which the run writes once before any launch; entries made in the run folder after the agent started move nothing."""
    yes = time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(time.time() - 1800))
    p.write("_launch.md", f"Yes: {yes} — t/builder\nYes: 2099-01-01T00:00Z — a later line\n")
    p.rounds([row(age=age)])
    (p.run / "scratch" / "planner").mkdir(parents=True)
    p.write("handoff-critic.md", "HANDOFF critic after Task 1 — 2026-10-30 09:00\n")
    r = p.watch(rounds=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert registry(p)["roles"]["t/builder"]["session_id"] == adopted
```

- [ ] **Step 5: J5, run red, then fix**

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_watch_agents.py -k rule_3)`
Expected: `3 failed, 1 passed` (`after-yes` passes before the fix: it guards that the floor keeps a later row).
Fix in `Watcher.match` (`watch_agents.py:671-692`): a row is a candidate only when
`os.path.realpath(r.get("cwd") or "")` equals `os.path.realpath(self.agents[name]["cwd"])` (as `collect_run.py:326-337`
compares cwds); the floor (`:680`) is `self.yes_floor()` while `launched_at` is `None`, else `launched_at - 5` as now.
New `Watcher.yes_floor()`: the earliest `Yes: <YYYY-MM-DDTHH:MMZ> — ` line of `<run_dir>/_launch.md` (the pattern of
`preflight.py:53`, `YES`) as UTC epoch seconds minus 5; `None` without the file or such a line (the cwd test alone).
Why that line (C35): the pre-flight holds every launch until each role is named in a `Yes:` line
(`example/launch.md:4-7`), so it precedes every launch and is written once, while the run folder's `st_ctime` moves
with every entry made in it and `Launched:` is written after the first role starts. `copies()` stays as is: it counts
live namesakes in any cwd and ends the watch, on purpose (a duplicate in a wrong folder must stop it). Texts: the
module docstring (`:16-19`), `match`'s docstring (`:672-673`) and `scripts/docs/watch_agents.md:50-52` (the match)
say that rule 3 takes only a row in the agent's cwd and, before the first launch, one started after the first `Yes:`
line. (`references/watching.md` holds no "start the watcher after every agent" rule: nothing to remove there.)
Run the same command. Expected: `4 passed`.

- [ ] **Step 6: J10, the test and the line (C43)**

Append to `scripts/tests/test_skill_md.py`:

```python
def test_skill_md_sends_the_main_session_to_its_page_and_the_lessons_page():
    """J10 (judge.md of manager-build-2026-10-29, #### J10): nothing a fresh main session loads pointed it to its own
    page or to the lessons page."""
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "The main session is the manager: it first reads `docs/roles/manager-chat.md` and" in text
    assert "`<vault>/decisions/global/manager-lessons.md`." in text
```

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_skill_md.py -k lessons_page)`
Expected: `1 failed`.
Then two edits in SKILL.md, 11,925 B at 59d3953 (a line alone would take it to 12,053 B, over the 12,000 B of
`test_skill_md.py:41`). First, after `previous stage ends. Nothing waits for the owner.` (`:11`), two new lines:

```text
The main session is the manager: it first reads `docs/roles/manager-chat.md` and
`<vault>/decisions/global/manager-lessons.md`.
```

Second, the "Measuring the pipeline" row (`:118-120`), old -> new:

```text
- [Measuring the pipeline](references/measuring.md): the read-only reports (records, gates, cost, budget, lessons,
  replay), what they measured, and the jobs' disk; after every run, `scripts/manager/measure_manager.py` measures the
  manager itself.
```

```text
- [Measuring the pipeline](references/measuring.md): the read-only reports (records, gates, cost, budget, lessons,
  replay); `scripts/manager/measure_manager.py` for the manager.
```

The row's title (`test_skill_md.py:30`) and the path (`:112`) stay; no skill test holds the words cut.
Run the same command, then `wc -c < .claude/skills/running-specagent-pipelines/SKILL.md`.
Expected: `1 passed`; `11982`.

- [ ] **Step 7: J4, J7, J9, J8 — one test each, red then green (C36, A20)**

Each finding in this order: its test, its red run, its fix, its green run. Every `Run:` below is
`(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q <file> -k <selection>)`.

J4. Append to `scripts/tests/test_collect_run.py`:

```python
def test_also_refuses_a_path_inside_the_run_folder_other_than_scratch(tmp_path):
    """J4 (judge.md of manager-build-2026-10-29, #### J4): `--also` could name a kept record file, and nothing
    refused it."""
    r = Run(tmp_path)
    log, lessons, notes = r.run / "build-log-a.md", r.run / "lessons.md", r.run / "scratch" / "planner" / "notes.md"
    out = r.collect("--also", str(log), "--also", str(lessons), "--also", str(notes))
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: {log} lies in the run folder outside scratch/",
        f"refused: {lessons} lies in the run folder outside scratch/",
    ]
```

Run: `tests/test_collect_run.py -k also_refuses`. Expected: `1 failed`.
Fix in `collect_run.also_deletions`: after its `holds()` branch, a given path whose real path lies in the run folder
(`protected[0]`) and not under its `scratch/` is refused with `refused: <given> lies in the run folder outside
scratch/` (exit 3, as the other refusals); `scripts/docs/collect_run.md` adds it to the save check's refusals
(`:14-17`, after "a `--kept` item is missing or lies inside a deletion"): "an `--also` path lies in the run folder
outside `scratch/`". Run the same command. Expected: `1 passed`.

J7. Append to `scripts/tests/test_check_formats.py` (two `make_repo()` calls in one second give one sha, so the sha
the repository lacks is `"f" * 40`):

```python
def test_a_merged_marker_is_checked_in_the_repo_when_the_lane_worktrees_are_gone(run, tmp_path):
    """J7 (judge.md of manager-build-2026-10-29, #### J7): after an apply removed the lane worktrees, the collector's
    save check refused its own re-run, since an `x->y` or `+` marker was checked only in the removed checkouts."""
    repo, gone = tmp_path / "repo", tmp_path / "removed-a"
    sha, _ = make_repo(repo)
    other = "f" * 40  # a sha the repository lacks
    (run / "_control").mkdir()
    agents = {
        "manager/builder-a": {"cwd": str(gone), "status": "build-log-a.md"},
        "manager/builder-b": {"cwd": f"{gone}-b", "status": "build-log-b.md"},
    }
    (run / "_control" / "_agents.json").write_text(json.dumps({"agents": agents}))
    write(
        run,
        "lessons.md",
        f"""
        # Lessons
        - 20:14 UTC (main session): Merged: b->a at {sha} — b merged into a
        - 20:15 UTC (main session): Merged: a+b at {sha} — both lanes
        - 20:16 UTC (main session): Merged: b->a at {other} — a commit the repo lacks
        """,
    )
    code, out = check(run, "--repo", str(repo))
    assert (code, out["errors"]) == (1, [f"lessons.md:4: Merged: b->a at {other} is not a commit of {repo}"])
    code, out = check(run)  # without --repo the checkouts stay the only place, as before
    assert (code, out["errors"]) == (
        1,
        [
            f"lessons.md:2: Merged: b->a at {sha} is not an ancestor of HEAD in {gone}",
            f"lessons.md:3: Merged: a+b at {sha} is not an ancestor of HEAD in {gone} or {gone}-b",
            f"lessons.md:4: Merged: b->a at {other} is not an ancestor of HEAD in {gone}",
        ],
    )
```

Run: `tests/test_check_formats.py -k lane_worktrees`. Expected: `1 failed`.
Fix in `check_formats.merged_error`: before `if places:`, `if places and repo and not any(pathlib.Path(p).is_dir() for
p in places): places = []`, so with `--repo` and every named checkout gone the marker is checked in the repository
(`is not a commit of <repo>`); without `--repo` the old error stays. `scripts/docs/check_formats.md:13` ("whose sha
the merged-into checkout lacks") adds "or, when every lane worktree is gone, the `--repo` repository lacks". Run the
same command. Expected: `1 passed`.

J9 (C36). In `scripts/tests/test_surface.py`, three cases join `REFUSALS` (`:502`) after its `"registry"` case (`:509`):

```python
    "registry outside the run": (
        lambda run: write_json(run / "_control" / "_agents.json", {"registry": "../x.json"}),
        [],
        "registry ../x.json leaves run_dir",
    ),
    "config": (broken("_agents.json"), [], "{run}/_control/_agents.json does not parse: " + JSON_ERROR),
    "named config missing": (None, ["--config", "{run}/_control/none.json"], "no config at {run}/_control/none.json"),
```

Then append:

```python
@pytest.mark.parametrize(
    "config, argv, registry",
    [
        ("_agents.json", [], "_control/reg2.json"),
        ("_agents-judge.json", ["--config", "{run}/_control/_agents-judge.json"], "_control/reg2.json"),
        ("_agents.json", [], None),
    ],
    ids=["default-config", "named-config", "no-registry-key"],
)
def test_surface_reads_the_registry_at_the_path_its_config_names(home, tmp_path, capsys, config, argv, registry):
    """J9 (judge.md of manager-build-2026-10-29, #### J9): surface.py read the registry only at
    `_control/registry.json`, while the watcher's documented `registry` field can put it anywhere in the run folder."""
    run = full_run(tmp_path)
    old = run / "_control" / "registry.json"
    new = run / registry if registry else old
    old.rename(new)
    write_json(
        run / "_control" / config, {"run_dir": str(run), "agents": {}, **({"registry": registry} if registry else {})}
    )
    assert surface.main([str(run), "--now", NOW, *(a.replace("{run}", str(run)) for a in argv)]) == 0
    cost = total(*RUN_DAY)
    expected = full_lines(run, cost, round(float(cost) / 40 * 100))
    assert capsys.readouterr().out.splitlines() == [line.replace(str(old), str(new)) for line in expected]
```

Run: `tests/test_surface.py -k "config or outside"` (the six new cases). Expected: `5 failed, 1 passed`
(`no-registry-key` passes before the fix: it guards the default).
Fix in `scripts/manager/surface.py`: the parser (`:331-342`) gains `--config P` (default
`<run_dir>/_control/_agents.json`, as `preflight.py check --config`); a new `registry_path(run_dir, config)` returns the
config's `registry` under `run_dir`, or `_control/registry.json` when the default config is missing or has no
`registry`; a named config that is missing -> SurfaceError `no config at <path>`, one that does not parse -> `<path>
does not parse: <error>`, a `registry` that leaves `run_dir` -> `registry <value> leaves run_dir` (the watcher's rule,
`watch_agents.py:574-576`); each exits 2 with one `surface: ` line on stderr (`main`, `:376-404`). `surface_text`
(`:346-356`) reads the path once and passes it to `load_registry` (`:154-164`, fixed path `:156`) and `run_start`
(`:192-199`, path rebuilt at `:197`; through `run_line`, `:210-228`); `render` (`:300-316`) takes it as an optional last
parameter, so the tests' positional `render(run, phrases, now, cost)` calls (`test_surface.py:393`, `:401`, `:414`,
`:425-426`) stay. Texts: the docstrings `:4` and `:302`; `scripts/manager/README.md:69` ("one per role of
`_control/registry.json`" -> "one per role of the registry its config names") and its usage line `:76` (`[--config
FILE]`); `scripts/README.md:74` (the `registry` row: `surface.py` reads the registry there too). Run the same command.
Expected: `6 passed`.

J8. Append to `scripts/tests/test_preflight.py`, after Step 2's helpers (A18: each example, filled as the manager
fills it, passes `blind`; `Edit(//x)`, `Edit(x)` and `Edit(~/x)` stay allowed):

```python
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
```

Run: `tests/test_preflight.py -k single_slash`. Expected: `7 failed`.
Fix in `preflight.check_blind` (`:197-208`, every role, sandboxed or not: J8 says "any single-slash `Edit` or `Write`
rule", judge.md:214-215, so not behind `check_ancestor`'s skip of `--unsandboxed` roles, `:212-213`): the deny rules
matching `(?:Edit|Write)\(/(?!/)` add the problem `single-slash <rules>: write //<path> for the root, <path> for the
cwd`, the rules joined by `, `. `ANCESTOR`'s cwd-anchored case (`Edit(/data/**)`) is judged by `check_ancestor` alone
and stays green. Under a new heading `## Rules with one slash` of `references/sandbox-and-blindness.md`, one sentence:
the pre-flight and the eval grader read `Edit(/x)` two ways (J8), so until the runtime's reading is pinned the
pre-flight refuses any single-slash `Edit` or `Write` rule: write `//<path>` for the root, `<path>` for the cwd. Run
the same command. Expected: `7 passed`.

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_collect_run.py tests/test_check_formats.py tests/test_surface.py tests/test_preflight.py)`
Expected: `135 passed` (20 + 25 + 37 + 53: the base's 19 + 24 + 31 + 44 plus 1, 1, 6 and 9, Step 2's two among them).

- [ ] **Step 8: J11 and J1, the texts (C41)**

J11: `docs/exec-plans/done/manager-build/task-11.md:806` becomes the TD-016 row of 0d49b8a's
`docs/exec-plans/tech-debt-tracker.md`, word for word (today they differ in one span: line 806 still names the owner's
other project where the row says "the sync of the owner's other project").
Run: `diff <(sed -n 806p docs/exec-plans/done/manager-build/task-11.md) <(git show 0d49b8a:docs/exec-plans/tech-debt-tracker.md | grep '^| TD-016 ')`
Expected: before the edit `1c1` with the two lines (exit 1); after it, no output (exit 0).
J1: `references/measuring.md` gains item 8 after item 7 (`:60-62`), in J1's words (judge.md of the manager-build run,
`#### J1`, `:43-45`): "8. A page that cites an owner statement was written after it: compare the statement's first
commit (`git log --format=%ct -- context/owner-statements/<date>.md`, its last line) with the commit that adds the
citation (`git log -S 'owner-statements/<date>.md' --format=%ct -- <page>`, its last line), not with the page's first
commit."
Run: `grep -c "git log -S 'owner-statements" .claude/skills/running-specagent-pipelines/references/measuring.md`
Expected: `1`.
`example/lessons.md`, at the end of "Known error classes" (the list above `## Lessons from this run`, `:49`): "- A role
settings file that leaves `~/.claude/.credentials.json` readable (J6 of the manager-build judge; the pre-flight's
`blind` check refuses it)."
Run: `grep -c 'credentials.json' .claude/skills/running-specagent-pipelines/example/lessons.md`
Expected: `1`.

- [ ] **Step 8a: R11 and B5 — the code checklists follow the diff to the verifier; the role table**

Spec Decided 3 (`docs/design-docs/pipeline-fold.md:91-99`): the critic never opens a checkout's code and the verifier
reads every diff, so the checklists that read code move to the verifier (R11 of the critic, B5 of builder-b). In
`scripts/tests/test_skill_example.py`, `DOMAIN`'s critic row (`:202`) and verifier row (`:205`) become:

```python
    "critic": (["code-reviewer.md", "silent-failure-hunter.md"], []),
    "verifier": (["pr-test-analyzer.md", "security-reviewer.md", "silent-failure-hunter.md"], []),
```

and the domain test's comment (`:228-230`) names "a verifier without security-reviewer" among the cases that fail.
Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_skill_example.py -k domain_section)`
Expected: `1 failed`.
Fix: `example/critic-assignment.md:54`, old -> new:

```text
Spec: .claude/ecc/agents/code-reviewer.md:17-36, .claude/ecc/agents/security-reviewer.md:41-52, .claude/ecc/agents/silent-failure-hunter.md:19-43 — the review order and the checklists of a coverage round (spec 4.7, the critic row for a feature or a bug)
Spec: .claude/ecc/agents/code-reviewer.md:27-35, .claude/ecc/agents/silent-failure-hunter.md:19-43 — the confidence filter and the silent-failure checklist of a coverage round (spec 4.7, the critic row for a feature or a bug)
```

`example/verifier-assignment.md:57`, old -> new:

```text
Spec: .claude/ecc/agents/pr-test-analyzer.md:19-46, .claude/ecc/agents/silent-failure-hunter.md:19-48 — the test-coverage and silent-failure checks of every verified commit (spec 4.7, the verifier row)
Spec: .claude/ecc/agents/pr-test-analyzer.md:21-37, .claude/ecc/agents/security-reviewer.md:41-51, .claude/ecc/agents/silent-failure-hunter.md:19-47 — the test-coverage, security and silent-failure checks of every verified commit's diff (spec 4.7, the verifier row)
```

The critic's line drops `code-reviewer.md:17-26` (run `git diff`, read the full file) and the OWASP list; the
verifier's takes 17 + 11 + 29 = 57 lines, within `DOMAIN_MAX_LINES = 59` (`scripts/manager/catalogue.py:26`, checked by
the domain test through `catalogue.check_briefs`). `references/choosing-roles-and-skills.md`: the "a feature (code)"
row (`:41`) reads "critic: code-reviewer, silent-failure-hunter; builder: tdd-guide; verifier: pr-test-analyzer,
security-reviewer, silent-failure-hunter"; the "a bug" row (`:42`) ends "the verifier reruns the repro and reads the
diff" instead of "the verifier reruns the repro; a critic reads the diff" (B5; the "a security review" row, `:45`,
names no diff and stays).
Run the same command. Expected: `1 passed`.

- [ ] **Step 9: The task's checks, once, and the commit (C40)**

Run: `(cd .claude/skills/running-specagent-pipelines/scripts && python3 -m pytest -q tests/test_preflight.py tests/test_watch_agents.py tests/test_skill_md.py tests/test_collect_run.py tests/test_check_formats.py tests/test_surface.py tests/test_skill_example.py)`
Expected: `274 passed` (53 + 116 + 8 + 20 + 25 + 37 + 15: at lane b's 59d3953 the seven files hold 44 + 112 + 7 + 19 +
24 + 31 + 14 = 251 tests, all passing; this task adds 9, 4, 1, 1, 1, 6 and 1).
Run: `uv run ruff check .`; `uv run ruff format --check .`; `wc -c < .claude/skills/running-specagent-pipelines/SKILL.md`
Expected: clean; `11982`.
Checks once each (`_common.md`, "Checks once each"): the full suites (`uv run pytest -q`, the skill's whole `tests`,
`just validate`, `uv run harness docs-check`, `uv run harness wiki-lint`) and `uv run harness validate` are the
verifier's at M2, not this task's; for this task this replaces the index's Global Constraints line on them
(`00-index.md:28-30`).

```bash
git add .claude/skills/running-specagent-pipelines docs/exec-plans/done/manager-build/task-11.md
git commit -m "feat(skill): Task 7 — the manager-build judge's conditions: J6 credentials deny, J5 match by cwd, J10 SKILL.md pointer, J4 J7 J8 J9 J11 J1; R11 B5 checklists to the verifier"
```

## Deferred
- J2 (the spec's "within 120 s" against need 1's "one watcher interval"): the spec lives in the run folder
  `manager-spec-2026-10-29/spec.md`, outside the repository; the judge's record keeps it.
- The live proofs: the next run's pre-flight on the seven settings (J6) and `measure_manager.py reads` on its first
  manager transcript (J10), Task 6.

## Verified (2026-10-30, at lane b's 59d3953 unless named)
- Base: `merge-base --is-ancestor` of 3c80656, 3f5ff76, 13f0d1d against 59d3953 -> 0 each; build-log.md:22, build-log-b.md:11.
- Runtime: `readlink -f "$(command -v claude)"` -> `/home/tite/.local/share/claude/versions/2.1.314` (ELF, no `.js`);
  Step 1's two commands print the two lines and `2`.
- `test_preflight.py:22-32` `NINE`, `:196` `for r in NINE]`, `:205` `denyRead`; `preflight.py:32-42` `NINE`, `:53` `YES`,
  `:72-84` `State`, `:197-208` `check_blind` (`:202` the sandboxed part, `:206` `need`, `:208` the pass text),
  `:212-213` `check_ancestor`'s skip of `--unsandboxed` roles.
- `test_skill_example.py:10` imports, `:147` `BLIND`'s last line, `:148` `SANDBOXED`, `:151`, `:157`, `:202`, `:205`
  `DOMAIN`, `:228-230` the comment; `example/sim_bwrap.py:3`, `:29-31`; a nested bwrap cannot create a namespace here.
- `watch_agents.py:16-19`, `:574-576`, `:671-692` (`:680` the floor), `:1347` `launch_table`; `test_watch_agents.py:73-93`
  `row()`, `:181-183` `rounds()`; `scripts/docs/watch_agents.md:50-52`; `example/launch.md:4-7` (a `Yes:` line before
  every launch); `references/watching.md`: no "start the watcher after" rule (grep).
- SKILL.md 11,925 B, `:11`, `:118-120`; 11,982 B after Step 6 (`scratch/plan-fixer/t7/c43.py`); `test_skill_md.py:30`,
  `:41`, `:112`; no skill test holds the words cut (`git grep -F` over `scripts/tests/`).
- `surface.py:4`, `:154-164`, `:192-199`, `:210-228`, `:300-316`, `:331-342`, `:346-356`, `:376-404`;
  `test_surface.py:502`, `:509`, `:536`; `scripts/manager/README.md:69`, `:76`; `scripts/README.md:74`.
- `scripts/docs/collect_run.md:14-17`; `scripts/docs/check_formats.md:13`; `references/preflight-and-capacity.md:14-15`;
  `references/sandbox-and-blindness.md:10`, `:14-15`; `example/README.md:63-65`; `example/common.md:23-24`.
- J11: the diff of Step 8 exits 1 today (one span); J1: judge.md:43-45 (manager-build run); `references/measuring.md`
  items end at 7 (`:60-62`); `example/lessons.md:49`; no version string in SKILL.md or `example/lessons.md`.
- R11, B5: `example/critic-assignment.md:54`, `example/verifier-assignment.md:57`; `code-reviewer.md:27` "## Confidence-
  Based Filtering" to `:35`, `pr-test-analyzer.md:21-37`, `security-reviewer.md:41-51` (OWASP Top 10),
  `silent-failure-hunter.md:19-47`; `catalogue.py:26` `DOMAIN_MAX_LINES = 59`; `choosing-roles-and-skills.md:41-42`, `:45`.
- Counts (`--collect-only`): 44, 112, 7, 19, 24, 31, 14 at 59d3953 (all pass); 53, 116, 8, 20, 25, 37, 15 = 274 with
  every test of this task (copy of a5e7785, whose seven files equal 59d3953's counts). Each red Expected was run on
  that copy; every green one under a reference fix (`scratch/plan-fixer/t7/green`), J9's checked red only.
