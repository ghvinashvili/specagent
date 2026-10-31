# Task 7 — The manager-lessons and learning-record forms, the measurement order, the manager's self-measurement and its page

planner: d
builder: d
depends_on: 1 (`Merged: a->d` after 1)
files: `templates/vault/forms/manager-lessons.md` (new), `templates/vault/forms/learning-record.md` (new), `templates/vault/README.md` and `templates/vault/rules.md` (the forms named), `scripts/manager/measure_manager.py` (new), `scripts/tests/test_measure_manager.py` (new), `scripts/manager/README.md` (`## measure_manager.py` with a `Usage:` line, which Task 1's `test_catalogue.py` requires), `references/measuring.md` (`### After every run, in this order`), `docs/roles/manager-chat.md` (new), four pages in `wiki/decisions/` with their `.summary.md` (1a, 2a, 3a, 5), `wiki/index.md`, `wiki/log.md`, `docs/llms.txt`
acceptance: 10.1, 10.2, 10.13 (by `measure_manager.py`); 10.3, 10.4 (their rules shipped, checked over the owner's vault at the run's end: departure 4)
milestone: M2

Paths: `scripts/` and `references/` are under `.claude/skills/running-specagent-pipelines/` (the index's shorthand).
Commands use `W=/home/tite/Desktop/agentic-flow-template/manager-build-d` (builder D's worktree),
`SK="${W:?}/.claude/skills/running-specagent-pipelines"` and `PY="${W:?}/.venv/bin/python"`. The tree this task is
built on: `feat/manager-build-d` after Task 5 (builder D takes its rows in index order: f70e84c, the `Merged: a->d`
merge that brings Task 1 and the `Merged: b->d` merge that brings Task 2, in either order, then Task 5's commit;
index rows 5 and 7 at 6c3a1cc). Every figure below was measured on f70e84c (the plan worktree's tree
outside `docs/exec-plans` equals it) with this task's files added in a scratch copy. Standard library only.

## Goal
The manager measures itself the way it measures the roles, and the same management mistake does not happen twice
(spec 5.6, 5.8, 7.2-7.7; the owner's requirements 5 and 9). `scripts/manager/measure_manager.py` reads the manager's
own transcript, its hand-off folder and its lessons page: the first call against 30,000 tokens (10.1, question 5),
every call against the 200,000 cap with a hand-off written before each compaction (10.2), the lessons page read in one
of the first five calls, and the page's form, size and recurrences (10.13), plus the findings per `Checklist:` item
(the count that promotes a shared cause, 7.6). The template ships the two forms of the owner's vault (D6):
`forms/manager-lessons.md` and `forms/learning-record.md`. `references/measuring.md` gets the order after every run
(5.6), and `docs/roles/manager-chat.md` describes the manager the owner talks to: the pipeline skill's main session
(1a), without the sandbox and with four guards (2a, 8.3.8), its duties by phase with the tool of each, its own
measures, its recovery order, its lessons page in the vault with a section per project (3a), and its profile chosen by
measurement (5). Four decision pages record 1a, 2a, 3a and 5.

## Spec carried
- 5.8, 8.2.7, 8.3.7, 10.1 and question 5: `measure_manager.py first-call` (one or more transcripts; three starts in a
  row; both profiles once, the one under 30,000 kept).
- 5.8 and 10.2: `measure_manager.py calls` (every call under the cap; `--handoff-dir`: a `*-handoff.md` written before
  each compaction, after the one before).
- 7.3, 7.7, 8.2.11 and 10.13: `reads` (the page in a tool call of the first five calls) and `lessons` (the item form,
  under 8,000 bytes, `--since` for the measurement page's items added, fired again and recurrences).
- 7.6, 8.2.10, 8.3.18 (the learning-record part) and TD-003 (as text): `forms/learning-record.md` with the five fields
  and the promotion rule; `checklist` counts the findings per cited item.
- 7.7, 8.3.13 (the forms) and question 3 (3a): `forms/manager-lessons.md` (the item form, the classes, the fold, a
  section per project), copied once to `<vault>/decisions/global/manager-lessons.md`.
- 5.6, 7.2 item 2 and 8.2.9 (measurements before pages): `references/measuring.md`, `### After every run, in this order`.
- 5.5, 8.2.6, 8.3.8 and question 2 (2a): `docs/roles/manager-chat.md`, `## No sandbox, four guards`.
- 8.3.1 and question 1 (1a): `docs/roles/manager-chat.md` names `docs/roles/MANAGER.md` as the harness's design.
- 5.7 (with Task 5): the page's duty list: routine questions decided with the assumption stated, the four kinds of
  question asked once, every status line with a digit and a record path.
- 5.8 (with Task 2): `## Recovery`: the registry `_control/registry.json` before any record (10.5).
- 5.9.2, 5.9.3, 7.2 items 1, 3-5, 7.4 and 10.3: `## After a run`: owner statements first, pages after; one log line
  per unit; the learning loop; Task 6's collector steps (K2).
- 7.5, 8.2.15 and question 12: the page states that no graph rule exists before the measurement page; the measurement
  is the main session's (Deferred).

## Departures from the spec (with the reasons)
1. 10.1 names "the parsing of `startup_report.py`". `measure_manager.py` uses `usage_report.py`'s parsing instead (a
   call is one message id; its context is input plus cache write plus cache read), because `startup_report.py` reads
   only the sessions `claude agents` lists and measures the context at the first write (8.3.7), not the first call.
2. 10.2 asks for a hand-off "with an mtime before each compaction". A hand-off counts for a compaction only when its
   name ends in `-handoff.md` (`.claude/hooks/handoff.py:4` writes `docs/handoff/<date>-<time>-handoff.md`) and its
   mtime is after the compaction before (for the first: after the transcript's first timestamp) and at or before the
   compaction; otherwise one old note would pass every later compaction.
3. 10.13's "the page's path appears in the first five calls" is read as: a `tool_use` input of one of the first five
   calls contains the path (a Read, a Grep, a `sed -n`); the path in a prompt or a note is not a read.
4. 10.3 and 10.4 check the owner's vault at the run's end with the spec's commands (`git log --format=%ct --
   context/owner-statements/<date>.md`; `ops/check_pages.py`). The vault and its pages are the owner's and the main
   session's (D6), so this task ships their rules (`docs/roles/manager-chat.md`, `references/measuring.md`, the forms)
   and no script.
5. The spec writes the item's arrow as `→` (U+2192); the form writes `->` like the run records (`Merged: a->b`), and
   `lessons` accepts both.

## Contracts
Honoured (cited by heading, never by line):
- Task 1 (builder a), `example/common.md` `## Proof rule (binding)`: every critic and verifier finding cites
  `Checklist: <file>:<line>` (a pinned copy's line, a `lessons.md` "Known error classes" line or a spec line);
  `checklist` counts the lines that start with `Checklist:` and hold exactly one `<file>:<line>` token, grouped by that
  value. Task 1's Step 2d creates `scripts/manager/README.md` (a `# scripts/manager` title and one paragraph), and its
  `test_catalogue.py` requires a `## measure_manager.py` section with a line matching
  `^Usage: .*scripts/manager/measure_manager.py\b`. Lane d gets Task 1 by
  `Merged: a->d` before Task 5 (index row 7, `depends_on: 1`; lessons.md 22:27 UTC), so the file is there and Step 4
  appends to it; Task 1 also moves the two tests that read `references/` (the headings and the named paths) from
  `test_docs.py` to its `test_skill_md.py` (Steps 1 and 5 run both files).
- Task 2 (builder b), Contracts K1 and K4: a fresh manager reads `_control/registry.json` before any record (10.5);
  orders go through `python3 -I <skill>/scripts/watch_agents.py --order <agent> <text> <config>`, which prints
  `order <msg_id> <agent>` and the prompt the manager sends with `SendMessage`; the role answers `ACK <msg_id>` at a
  line start, and a missing ACK is resent by stop and resume.
- Task 3 (builder b), Contracts: `duty_list.py extract <plan-dir> --out <run-dir>/_control/duties.md` after the index
  and before the launch; `monitor_records.py watch <run-dir>` as a background command, re-armed after every exit.
- Task 5 (builder d, built before this task): `references/measuring.md` holds `### The owner's surface` and
  `scripts/manager/README.md` holds `## surface.py`; this task appends after them and edits neither. Its contract for
  this task (task-05.md `## Contracts`, planner-b; C18): `docs/roles/manager-chat.md` says the manager's status answer
  to the owner is two or three short lines, "now: …, next: …" (spec 5.7, `:695`), whose figures (a role's unit,
  context and cost, the run's cost) are copied as printed from the stdout of
  `python3 -I <skill>/scripts/manager/surface.py <run> --phrases <owner phrase file>`, never computed (10.6), each
  line with a figure and the record path `<run>/_control/surface.txt` (10.18); the whole stdout only when the owner
  asks for the costs or the full state; and that after the launch the manager starts
  `python3 -I <skill>/scripts/manager/surface.py <run> --phrases <file> --out <run>/_control/surface.txt --every 120`
  as a background command and re-arms it after every exit, as it does the monitor (Step 6).
- Task 6 (builder c), Contracts K2: before the collector, the manager marks each item of `## Lessons from this run`
  with `(skill: <sha>)` or `(skill: none)`, `Merged:` records stay unmarked; then
  `python3 -I <skill>/scripts/collect_run.py <run> --repo <checkout> --plan <plan folder> --kept <page> ...`, the list
  shown to the owner, on the owner's yes the same command with `--apply --yes <digest>`; after three such runs
  `--apply` alone, and the owner reads `<run>/collected.md`.
Given (sent to `manager/plan-fixer` with this task's commit):
- Task 10 (builder b): `usage_report.py` keeps `lines(path)` (yields `(key, line)` per assistant line with a usage)
  and `context(u)` (input + cache write + cache read) beside the `PRICE`, `family` and `calls` that Task 2's K6
  keeps: `measure_manager.py` imports all three of `calls`, `lines` and `context`.
- Task 11: the `## For Task 11` section below.

## Interfaces
`scripts/manager/measure_manager.py`, no shebang line (a builder cannot set a mode under `.claude/skills/`, and
ruff's EXE001 fails `uv run ruff check .` on a shebang in a file that is not executable: lessons.md 22:23 UTC),
standard library only, run as `python3 -I scripts/manager/measure_manager.py <subcommand> ...`; the tests call only
this command line. It imports `usage_report` from its parent folder (`sys.path.insert(0, <the scripts folder>)`, as
`startup_report.py` does at f70e84c) and uses only `ur.calls(path)` (the first line of each message id with a usage),
`ur.lines(path)` (`(key, line)` per assistant line with a usage) and `ur.context(usage)`. Every function stays under
50 lines (the planner's scratch version: 22 at most).

| Subcommand | Output lines (stdout, in this order) | Exit |
|---|---|---|
| `first-call TRANSCRIPT... [--limit 30000]` | per transcript, in the given order: `<path>: first call <n> tokens, limit <limit>: pass` (n < limit) or `...: fail`; a transcript without a call: `<path>: no call: fail` | 0 when every transcript passes, else 1 |
| `calls TRANSCRIPT [--cap 200000] [--handoff-dir DIR]` | `<path>: <k> calls, max <n> tokens at call <i> (<timestamp>), cap <cap>: pass\|fail` (the first call with the largest context; fail when a call's context is over the cap), then `over cap: call <i> <n> tokens (<timestamp>)` per such call in order; with `--handoff-dir`, per `compact_boundary` line in order: `compaction <timestamp> (<preTokens> tokens before): hand-off <name> at <YYYY-MM-DDTHH:MM:SSZ>: pass` (the newest `*-handoff.md` directly in DIR with bound < mtime <= the compaction) or `compaction <timestamp> (<preTokens> tokens before): no hand-off since <bound>: fail`; no call: `<path>: no call: fail` | 0 when nothing fails, else 1 |
| `reads TRANSCRIPT TEXT [--calls 5]` | `<path>: <TEXT> in call <k> of the first <calls>: pass` for the first call (numbered by message id in file order) among the first `--calls` with a `tool_use` block whose JSON input contains TEXT; else `<path>: <TEXT> not in the first <calls> calls: fail` | 0 or 1 |
| `lessons PAGE [--max-bytes 8000] [--since YYYY-MM-DD]` | `<page>: bytes <b>, items <n>, problems <p>: pass\|fail`; then the problems, per item in order: `line <l>: item <num>: no "<trigger> -> <rule>"`, `line <l>: item <num>: no "cost measured" with a number`, `line <l>: item <num>: no "<date>, <record>" with a file`, `line <l>: item <num>: number used before at line <l0>`, and last `page: bytes <b>, not under <max>`; with `--since D`: `added since D: <numbers or none>`, `fired again since D: <num> (<k>), ...` (or `none`; k is the item's own count of later dates >= D), `recurrences since D: <count>` (the sum of the k) | 1 when a problem, else 0 |
| `checklist RECORD...` | `<count> <file>:<line>` per cited value, highest count first, ties by value; then `<record>:<n>: malformed Checklist line: <the line stripped>` per other `Checklist:` line in file order; then `total: Checklist lines <t>, items <i>, malformed <m>` | 1 when a malformed line, else 0 |

Common rules:
- A missing TRANSCRIPT, PAGE, RECORD or `--handoff-dir` prints `measure_manager: <path>: no such file` on stderr,
  nothing on stdout, exit 2; argparse's usage errors (a `--since` that is not `YYYY-MM-DD` among them) exit 2.
- A compaction is the line `{"type": "system", "subtype": "compact_boundary", "timestamp": "<ISO>",
  "compactMetadata": {"trigger": ..., "preTokens": <n>}}` (claude 2.1.312); the bound of the first compaction is the
  transcript's first `timestamp`, of every later one the compaction before.
- An item of the lessons page is a line `<n>. <text>` at the line start; an indented non-blank line right after it
  continues it. The arrow is ` -> ` or ` → ` with a space on each side; the cost is `; cost measured ` and text with a
  digit before the next `;`; each firing is `; <YYYY-MM-DD>, <record>`, at least one, every record holding a file name
  (`\w\.[A-Za-z]\w*`). Numbers may have gaps (an item keeps its number below the fold) and are never reused. Added since
  D: the item's earliest date >= D; fired again: a later date of the item >= D, printed as `<num> (<k>)` with k the
  item's own count of later dates >= D (one item can fire twice in a run, and 10.13 wants the count by item);
  recurrences: the sum of the k. The size is counted in bytes.
- A `Checklist:` line is counted when its rest, stripped, is one `\S+:\d+` token; any other `Checklist:` line is
  malformed. Only lines that start with `Checklist:` are read.

## Steps

- [ ] **Step 1 — the baseline.** On builder D's tree after Task 5:
  ```bash
  W=/home/tite/Desktop/agentic-flow-template/manager-build-d; SK="${W:?}/.claude/skills/running-specagent-pipelines"; PY="${W:?}/.venv/bin/python"
  git -C "${W:?}" log --oneline -3
  test -e "${SK:?}/scripts/manager/README.md" && echo has-readme || echo no-readme
  ls "${W:?}/templates/vault"
  (ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 600 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests" 2>&1 | tail -1)
  (ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_skill_md.py" "${SK:?}/scripts/tests/test_docs.py" 2>&1 | tail -1)
  ```
  Expected: Task 5's commit on top, the `Merged: a->d` and `Merged: b->d` merges below it; `has-readme` (Task 1
  creates the file, Task 5 adds `## surface.py`; `no-readme` means the `Merged: a->d` merge is missing: stop and tell
  the main session); `INDEX.md README.md concepts context decisions log.md ops rules.md` (no `forms`); `<N0> passed`
  for the skill suite and `<D0> passed` for the two files that read `references/`: write both down. The skill suite
  collected 146 tests at f70e84c; Task 1's, Task 2's and Task 5's tests come on top (the two files: `12 passed` at
  Task 1's commit, task-01.md 5f). The repository suite (`uv run pytest -q`) is the verifier's at M2 (C503's rule).

- [ ] **Step 2 — the script: tests, red, code, green.** Write `scripts/tests/test_measure_manager.py`:
````python
"""measure_manager.py (manager-build Task 7): the manager's first call against 30,000 tokens, every call against the
200,000 cap with a hand-off written before each compaction, the manager-lessons page read in the first five calls, the
page's form, size and recurrences, and the count of findings per `Checklist:` item. Transcripts in the live shape of
transcript_home.py (one line per content block, tool results between, '<synthetic>' lines); no session is started."""

import datetime
import json
import os
import re
import subprocess
import sys

from transcript_home import SCRIPTS, SYNTHETIC, TEXT, Home, bash, read

sys.dont_write_bytecode = True
MANAGER = SCRIPTS / "manager"
CHECKOUT = SCRIPTS.parents[3]
TOOL = MANAGER / "measure_manager.py"
ARROW = chr(0x2192)  # the spec writes the item's arrow as U+2192; the form writes "->"; both are accepted
FRONT = "---\ntitle: Manager lessons\ntype: decision\nscope: global\n---\n# Manager lessons\n\n"  # 7 lines


def run(*args, env=None):
    return subprocess.run(
        [sys.executable, "-I", str(TOOL), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=env,
    )


def transcript(tmp_path, n, calls, start="2026-10-29T10:00:00"):
    """A manager transcript: its first line (the user's) at start + 1 s, then one second per line."""
    sid = f"{n:08x}-0000-4000-8000-000000000000"
    home = Home(tmp_path / f"t{n}")
    home.session("manager", sid, calls, start=start)
    return home.projects / f"{sid}.jsonl"


def compact(path, at, pre=167_000):
    """A compaction as Claude Code 2.1.312 writes it: a system line with subtype compact_boundary."""
    entry = {
        "type": "system",
        "subtype": "compact_boundary",
        "content": "Conversation compacted",
        "isMeta": False,
        "timestamp": at,
        "level": "info",
        "compactMetadata": {"trigger": "auto", "preTokens": pre},
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def handoff(folder, name, at):
    path = folder / name
    path.write_text("# Hand-off\n", encoding="utf-8")
    t = datetime.datetime.fromisoformat(at).timestamp()
    os.utime(path, (t, t))


def page(tmp_path, body, name="manager-lessons.md"):
    path = tmp_path / name
    path.write_text(FRONT + body, encoding="utf-8")
    return path


def test_first_call_is_the_first_real_call_and_must_be_under_the_limit(tmp_path):
    # A synthetic line first (zero usage) is no call; the first real call is 29,999 and a later one 120,000: the first
    # call passes, though the largest does not; exactly 30,000 fails ("under 30,000", 10.1). One line per transcript,
    # in the order given.
    under = transcript(tmp_path, 1, [SYNTHETIC, (29_999, 40, [TEXT, read("/v/INDEX.md")]), (120_000, 40, [TEXT])])
    at = transcript(tmp_path, 2, [(30_000, 40, [TEXT])])
    r = run("first-call", under, at)
    assert r.returncode == 1
    assert r.stdout.splitlines() == [
        f"{under}: first call 29999 tokens, limit 30000: pass",
        f"{at}: first call 30000 tokens, limit 30000: fail",
    ]


def test_three_starts_under_the_limit_pass_and_the_limit_is_an_option(tmp_path):
    starts = [transcript(tmp_path, n, [(c, 40, [TEXT])]) for n, c in ((3, 21_000), (4, 25_500), (5, 29_000))]
    r = run("first-call", *starts)
    assert (r.returncode, r.stdout.count(": pass\n")) == (0, 3)
    r = run("first-call", *starts, "--limit", "25500")
    assert r.returncode == 1
    assert [line.rsplit(": ", 1)[1] for line in r.stdout.splitlines()] == ["pass", "fail", "fail"]


def test_a_transcript_without_a_call_fails_and_a_missing_one_is_an_error(tmp_path):
    empty = transcript(tmp_path, 6, [SYNTHETIC])
    r = run("first-call", empty)
    assert (r.returncode, r.stdout) == (1, f"{empty}: no call: fail\n")
    gone = tmp_path / "gone.jsonl"
    r = run("first-call", gone)
    assert (r.returncode, r.stdout, r.stderr) == (2, "", f"measure_manager: {gone}: no such file\n")


def test_calls_reports_the_largest_and_every_call_over_the_cap(tmp_path):
    # Lines: user 10:00:01; call 1 at :02; call 2 at :03 (text), :04 (tool), :05 (its result); a synthetic line at
    # :06, which is no call; call 3 at :07; call 4 at :08. 200,000 is the cap itself and passes ("exceeds", 10.2).
    calls = [(12_000, 40, [TEXT]), (200_000, 40, [TEXT, read("/v/a.md")]), SYNTHETIC]
    calls += [(200_001, 40, [TEXT]), (150_000, 40, [TEXT])]
    path = transcript(tmp_path, 7, calls)
    r = run("calls", path)
    assert r.returncode == 1
    assert r.stdout.splitlines() == [
        f"{path}: 4 calls, max 200001 tokens at call 3 (2026-10-29T10:00:07.000Z), cap 200000: fail",
        "over cap: call 3 200001 tokens (2026-10-29T10:00:07.000Z)",
    ]


def test_calls_pass_under_the_cap_and_the_cap_is_an_option(tmp_path):
    path = transcript(tmp_path, 8, [(90_000, 40, [TEXT]), (140_000, 40, [TEXT]), (140_000, 40, [TEXT])])
    first_max = "max 140000 tokens at call 2 (2026-10-29T10:00:03.000Z)"
    r = run("calls", path)
    assert (r.returncode, r.stdout) == (0, f"{path}: 3 calls, {first_max}, cap 200000: pass\n")
    r = run("calls", path, "--cap", "100000")
    assert r.returncode == 1
    assert r.stdout.splitlines() == [
        f"{path}: 3 calls, {first_max}, cap 100000: fail",
        "over cap: call 2 140000 tokens (2026-10-29T10:00:03.000Z)",
        "over cap: call 3 140000 tokens (2026-10-29T10:00:04.000Z)",
    ]


def test_each_compaction_needs_a_hand_off_written_since_the_one_before(tmp_path):
    # Compactions at 11:00 and 12:00; hand-offs at 10:59 and 11:59 cover one each. Without the 11:59 file the second
    # compaction has none: the 10:59 file is older than the first compaction, so it was written for that one. The
    # first run is in UTC+4 all year (Etc/GMT-4): a hand-off's time is its mtime in UTC, whatever the zone.
    path = transcript(tmp_path, 9, [(50_000, 40, [TEXT]), (160_000, 40, [TEXT])])
    compact(path, "2026-10-29T11:00:00.000Z", pre=170_000)
    compact(path, "2026-10-29T12:00:00.000Z", pre=171_000)
    folder = tmp_path / "handoff"
    folder.mkdir()
    handoff(folder, "2026-10-29-1059-handoff.md", "2026-10-29T10:59:00+00:00")
    handoff(folder, "2026-10-29-1159-handoff.md", "2026-10-29T11:59:00+00:00")
    one = "compaction 2026-10-29T11:00:00.000Z (170000 tokens before): hand-off 2026-10-29-1059-handoff.md"
    two = "compaction 2026-10-29T12:00:00.000Z (171000 tokens before): hand-off 2026-10-29-1159-handoff.md"
    r = run("calls", path, "--handoff-dir", folder, env={**os.environ, "TZ": "Etc/GMT-4"})
    assert r.returncode == 0
    assert r.stdout.splitlines()[1:] == [f"{one} at 2026-10-29T10:59:00Z: pass", f"{two} at 2026-10-29T11:59:00Z: pass"]
    (folder / "2026-10-29-1159-handoff.md").unlink()
    r = run("calls", path, "--handoff-dir", folder)
    assert r.returncode == 1
    assert r.stdout.splitlines()[1:] == [
        f"{one} at 2026-10-29T10:59:00Z: pass",
        "compaction 2026-10-29T12:00:00.000Z (171000 tokens before): no hand-off since 2026-10-29T11:00:00.000Z: fail",
    ]
    assert run("calls", path).stdout.count("\n") == 1  # without --handoff-dir no compaction is checked


def test_a_hand_off_after_the_compaction_before_the_session_or_by_another_name_does_not_count(tmp_path):
    # The session's first line is at 10:00:01: a hand-off of 09:30 belongs to an earlier session, one of 11:01 came
    # after the compaction, and notes.md is no hand-off file (`*-handoff.md`, .claude/hooks/handoff.py:4).
    path = transcript(tmp_path, 10, [(50_000, 40, [TEXT])])
    compact(path, "2026-10-29T11:00:00.000Z")
    folder = tmp_path / "handoff"
    folder.mkdir()
    handoff(folder, "2026-10-29-0930-handoff.md", "2026-10-29T09:30:00+00:00")
    handoff(folder, "2026-10-29-1101-handoff.md", "2026-10-29T11:01:00+00:00")
    handoff(folder, "notes.md", "2026-10-29T10:30:00+00:00")
    r = run("calls", path, "--handoff-dir", folder)
    assert r.returncode == 1
    assert r.stdout.splitlines()[1:] == [
        "compaction 2026-10-29T11:00:00.000Z (167000 tokens before): no hand-off since 2026-10-29T10:00:01.000Z: fail",
    ]


def test_reads_finds_the_page_in_a_tool_call_of_the_first_five_calls(tmp_path):
    # Calls 1-4 have two lines each (text, then a tool call and its result); the page is read on call 5's second line.
    target = "/vault/decisions/global/manager-lessons.md"
    calls = [(20_000 + i, 40, [TEXT, bash(f"head -1 rec{i}.md")]) for i in range(4)]
    calls.append((25_000, 40, [TEXT, read(target)]))
    path = transcript(tmp_path, 11, calls)
    r = run("reads", path, target)
    assert (r.returncode, r.stdout) == (0, f"{path}: {target} in call 5 of the first 5: pass\n")
    r = run("reads", path, target, "--calls", "4")
    assert (r.returncode, r.stdout) == (1, f"{path}: {target} not in the first 4 calls: fail\n")


def test_reads_counts_calls_not_lines_and_only_tool_calls(tmp_path):
    # Call 1 names the page in its text (no read); a synthetic line is no call; the page is read in call 6.
    name = "manager-lessons.md"
    calls = [(20_000, 40, [{"type": "text", "text": f"{name} comes later."}, bash("head -1 a.md")]), SYNTHETIC]
    calls += [(21_000 + i, 40, [TEXT]) for i in range(4)] + [(26_000, 40, [read(f"/v/decisions/global/{name}")])]
    path = transcript(tmp_path, 12, calls)
    r = run("reads", path, name)
    assert (r.returncode, r.stdout) == (1, f"{path}: {name} not in the first 5 calls: fail\n")
    r = run("reads", path, name, "--calls", "6")
    assert (r.returncode, r.stdout) == (0, f"{path}: {name} in call 6 of the first 6: pass\n")


GOOD = (
    "## All projects\n"
    "1. A plan's merge duty read when a role waits -> the duty list read when the plan is written; cost measured 64 min\n"
    "   of builder B idle; 2026-10-29, runs/a/lessons.md:147\n"
    f"2. A settings change rolled out unsimulated {ARROW} simulate it first; cost measured 38 min, 7 sessions; "
    "2026-10-29, runs/a/lessons.md:164; 2026-11-02, runs/b/lessons.md:20\n"
    "\n"
    "## demo-project\n"
    "4. A guessed timeout -> the cases' own numbers; cost measured 90 min of suite; 2026-11-03, runs/b/verify.md:88\n"
)


def test_a_page_in_the_form_passes_with_wrapped_items_either_arrow_and_gaps_in_the_numbers(tmp_path):
    path = page(tmp_path, GOOD)
    size = len((FRONT + GOOD).encode())
    r = run("lessons", path, "--since", "2027-01-01")
    assert r.returncode == 0
    assert r.stdout.splitlines() == [
        f"{path}: bytes {size}, items 3, problems 0: pass",
        "added since 2027-01-01: none",
        "fired again since 2027-01-01: none",
        "recurrences since 2027-01-01: 0",
    ]


def test_an_item_without_arrow_measured_cost_record_file_or_own_number_is_a_problem(tmp_path):
    body = (
        "1. No arrow here; cost measured 5 min; 2026-10-29, a/lessons.md:1\n"
        "2. Trigger -> rule; cost measured a while; 2026-10-29, a/lessons.md:2\n"
        "3. Trigger -> rule; cost measured 9 min; 2026-10-29, the run's notes\n"
        "4. Trigger -> rule; cost measured 9 min; 2026-10-29, a/verify.md:4; 2026-10-30, the second run\n"
        "2. Trigger -> another rule; cost measured 3 min; 2026-10-30, a/lessons.md:9\n"
    )
    path = page(tmp_path, body)
    r = run("lessons", path)
    assert r.returncode == 1
    assert r.stdout.splitlines() == [
        f"{path}: bytes {len((FRONT + body).encode())}, items 5, problems 5: fail",
        'line 8: item 1: no "<trigger> -> <rule>"',
        'line 9: item 2: no "cost measured" with a number',
        'line 10: item 3: no "<date>, <record>" with a file',
        'line 11: item 4: no "<date>, <record>" with a file',
        "line 12: item 2: number used before at line 9",
    ]


def test_the_page_must_be_under_8000_bytes_counted_in_bytes(tmp_path):
    # The arrow is one character and three bytes: a page of exactly 8,000 bytes has 7,998 characters and fails.
    item = f"1. Trigger {ARROW} rule; cost measured 5 min; 2026-10-29, a/lessons.md:1\n"
    pad = 8_000 - len((FRONT + item).encode()) - 1
    exact = page(tmp_path, item + "x" * pad + "\n", "exact.md")
    assert (len(exact.read_bytes()), len(exact.read_text(encoding="utf-8"))) == (8_000, 7_998)
    r = run("lessons", exact)
    assert r.returncode == 1
    assert r.stdout.splitlines() == [
        f"{exact}: bytes 8000, items 1, problems 1: fail",
        "page: bytes 8000, not under 8000",
    ]
    under = page(tmp_path, item + "x" * (pad - 1) + "\n", "under.md")
    assert run("lessons", under).stdout == f"{under}: bytes 7999, items 1, problems 0: pass\n"
    assert run("lessons", under, "--max-bytes", "7999").returncode == 1


def test_since_lists_the_items_added_and_the_items_that_fired_again(tmp_path):
    body = (
        "1. T1 -> R1; cost measured 1 min; 2026-10-20, a/l.md:1\n"
        "2. T2 -> R2; cost measured 2 min; 2026-10-20, a/l.md:2; 2026-10-22, a/l.md:8; 2026-11-01, b/l.md:5\n"
        "3. T3 -> R3; cost measured 3 min; 2026-11-01, b/l.md:6\n"
        "4. T4 -> R4; cost measured 4 min; 2026-11-01, b/l.md:7; 2026-11-02, b/l.md:9; 2026-11-03, b/l.md:11\n"
        "5. T5 -> R5; cost measured 5 min; 2026-10-21, a/l.md:3; 2026-10-25, a/l.md:4\n"
    )
    r = run("lessons", page(tmp_path, body), "--since", "2026-11-01")
    assert r.returncode == 0
    assert r.stdout.splitlines()[1:] == [
        "added since 2026-11-01: 3, 4",
        "fired again since 2026-11-01: 2 (1), 4 (2)",
        "recurrences since 2026-11-01: 3",
    ]


def test_checklist_counts_findings_per_cited_item_highest_first(tmp_path):
    critique = tmp_path / "critique.md"
    critique.write_text(
        "#### C1\nThe plan cites a missing path.\nChecklist: lessons.md:51\n\n"
        "#### C2\nThe same class again.\nChecklist: lessons.md:51   \n\n"
        "#### C3\nAn ECC item.\nChecklist: .claude/ecc/agents/code-reviewer.md:40\n"
        "A note that quotes Checklist: lessons.md:51 in the middle of a line cites nothing.\n",
        encoding="utf-8",
    )
    verify = tmp_path / "verify.md"
    verify.write_text(
        "#### V1\nChecklist: lessons.md:5\n#### V2\nChecklist: .claude/ecc/agents/code-reviewer.md:40\n",
        encoding="utf-8",
    )
    r = run("checklist", critique, verify)
    assert r.returncode == 0
    assert r.stdout.splitlines() == [
        "2 .claude/ecc/agents/code-reviewer.md:40",
        "2 lessons.md:51",
        "1 lessons.md:5",
        "total: Checklist lines 5, items 3, malformed 0",
    ]


def test_checklist_reports_a_malformed_line_with_its_place(tmp_path):
    record = tmp_path / "verify.md"
    record.write_text("#### V1\nChecklist: lessons.md line 51\n#### V2\nChecklist: spec.md:1091\n", encoding="utf-8")
    r = run("checklist", record)
    assert r.returncode == 1
    assert r.stdout.splitlines() == [
        "1 spec.md:1091",
        f"{record}:2: malformed Checklist line: Checklist: lessons.md line 51",
        "total: Checklist lines 2, items 1, malformed 1",
    ]


def test_the_readme_and_the_forms_carry_the_tool_s_contract():
    readme = (MANAGER / "README.md").read_text(encoding="utf-8")
    assert "## measure_manager.py" in readme.splitlines()
    section = readme.split("\n## measure_manager.py\n", 1)[1].split("\n## ", 1)[0]
    for sub in ("first-call", "calls", "reads", "lessons", "checklist"):
        assert re.search(rf"(?m)^Usage: python3 -I scripts/manager/measure_manager\.py {sub} ", section), sub
    vault = CHECKOUT / "templates" / "vault"
    lessons = (vault / "forms" / "manager-lessons.md").read_text(encoding="utf-8")
    assert "`<n>. <trigger> -> <rule>; cost measured <cost>; <YYYY-MM-DD>, <record>`" in lessons
    record = (vault / "forms" / "learning-record.md").read_text(encoding="utf-8")
    fields = ("trigger", "action", "evidence", "confidence", "scope")
    assert [f for f in fields if not re.search(rf"(?m)^- {f}: ", record)] == []
    for name in ("README.md", "rules.md"):
        text = (vault / name).read_text(encoding="utf-8")
        assert "forms/manager-lessons.md" in text and "forms/learning-record.md" in text, name
    r = run("lessons", vault / "forms" / "manager-lessons.md")
    assert r.returncode == 0 and r.stdout.endswith(", items 0, problems 0: pass\n")
````
  Run: `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_measure_manager.py" 2>&1 | tail -1)`
  Expected: `16 failed` (no `measure_manager.py` yet). The last test reads the README section and the forms that Steps
  3 and 4 write, so until then it is filtered; the filter measured red first:
  `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_measure_manager.py" -k 'not test_the_readme_and_the_forms_carry_the_tool_s_contract' 2>&1 | tail -1)`
  Expected: `15 failed, 1 deselected`. Write `scripts/manager/measure_manager.py` against the Interfaces
  (no shebang line: the tests run it as `python3 -I <path>`). Run the filtered command again. Expected:
  `15 passed, 1 deselected`. The wrong versions the planner
  ran red once against these tests (each failed at least one test): the largest call taken as the first; the limit
  and the cap compared on the wrong side of equality; the last of equal maxima reported; a hand-off taken without the
  bound before the compaction, or without the bound after it; any `*.md` taken as a hand-off; the bound never moved
  to the compaction before; calls counted per line, not per message id; only a call's first line searched; text
  blocks searched as well as tool calls; lines counted as calls; wrapped item lines not joined; a cost without a digit
  accepted; a record without a file name accepted; one record with a file enough when another lacks one; a reused
  number not reported; gaps in the numbers reported; `→` not accepted; the size counted in characters; a page of
  exactly 8,000 bytes passing; every item counted as added; `added` with `>` instead of `>=`; a firing before
  `--since` counted as fired again; `fired again` with `>`; an item's count taken over every repeat whatever its date
  (item 2's repeat of 2026-10-22 catches it); an item fired again printed without its count (`2, 4`); each item
  fired again counted once; an item's earliest date counted as a firing; the total taken as the number of items fired
  again; `none` not printed for an empty list; a hand-off's mtime turned into local time, or the compaction and its
  bound read as naive local times (on a machine set to UTC only the `TZ=Etc/GMT-4` run catches these two);
  findings grouped by file instead of `file:line`; `Checklist:` matched in mid-line; the value not stripped; the
  counts sorted by value; exit 0 with a malformed line; a transcript without a call passing; exit 1 for a missing
  file (40 wrong versions, 40 red, run with `TZ=UTC`).

- [ ] **Step 3 — the forms and the vault's README and rules** (`templates/vault/`). Write
  `templates/vault/forms/manager-lessons.md`:
````markdown
---
title: Manager lessons
type: decision
scope: global
status: verified
updated: YYYY-MM-DD
audience: [main]
sources: [context/owner-statements/YYYY-MM-DD.md]
decided: YYYY-MM-DD
by: owner
why: the same management mistake never twice; every main session reads this page in its first calls
decision_status: decided
would_change_if: three runs in a row end with no item fired again and no item added
---
# Manager lessons

The main session's own mistakes, each turned into a rule, read by every main session in its first calls. Copy this
form once to `decisions/global/manager-lessons.md`, list it in `INDEX.md`, set the dates and `sources`, and keep one
section per project under the global one. One item per mistake, appended the moment the mistake is found:

`<n>. <trigger> -> <rule>; cost measured <cost>; <YYYY-MM-DD>, <record>`

- `<n>` is the item's number, never reused; `<trigger>` is what happened; `<rule>` is what the manager does instead.
- `<cost>` is the measured cost with its number and unit: minutes waited, sessions without a commit, tokens, dollars.
- `<record>` is the file and line that show the mistake, such as `<run>/lessons.md:147`.
- The same mistake again: append `; <YYYY-MM-DD>, <record>` to its item; it keeps its number.
- An item that fired in no run for three runs moves under `## Below the fold` with its number.
- The page stays under 8,000 bytes, about 2,000 tokens. After each edit, and for the run's measurement page (the items
  added, the items fired again with their counts, the recurrences):
  `python3 -I <skill>/scripts/manager/measure_manager.py lessons <this page> --since <the run's first day>`.
- Classes of mistakes to name in a trigger: a duty read late, a rollout not simulated, an estimated time, a guessed
  timeout, polling by hand, an order lost on a watcher exit, the owner asked what a rule answers, a leftover not
  collected.

## All projects

## <project>

## Below the fold
````
  Write `templates/vault/forms/learning-record.md`:
````markdown
# Learning record (form)

One lesson as a record, in the shape of ECC's instinct model without its hooks. Roles write only the run's
`lessons.md` and their own record; the manager writes records into pages, and only what was checked is remembered.

- trigger: <what was seen, in one sentence>
- action: <the rule that answers it, in one sentence>
- evidence: <path>:<line> of the record that shows it (a finding, a log line, a measurement)
- confidence: <0.3 to 0.9> (0.3 for one sighting, raised as it recurs or is measured)
- scope: run | project | global (the run's `lessons.md`, the project's `wiki/decisions/`, the vault's `decisions/global/`)

Promotion, by hand: a record whose trigger recurs in two runs or two projects, or a cause shared by two findings,
becomes a rule, a decision page (`wiki/decisions/` for a project, `decisions/global/` for all) and one line in the
skill or the brief template. Two findings share a cause when they cite the same checklist item;
`python3 -I <skill>/scripts/manager/measure_manager.py checklist <run>/critique.md <run>/verify.md` lists the items
by the number of findings citing them, highest first. Before a run's "Read first" is compacted, `audit_read_first.py`
shows what would be lost; a finding with a read-only command becomes an eval case by `replay_cases.py`.
````
  In `templates/vault/README.md`, inside its text block of the tree, add these two lines right after the `ops/` line:
  ```text
  forms/manager-lessons.md the main session's lessons page; copied once to decisions/global/ (rules.md)
  forms/learning-record.md the shape of one learning record and the rule that promotes it (rules.md)
  ```
  In `templates/vault/rules.md`, add this paragraph and one blank line right before the `Never here:` line:
  ```text
  Forms: `forms/manager-lessons.md` is the main session's lessons page, copied once to
  `decisions/global/manager-lessons.md` and read by every main session in its first calls: one item per management
  mistake with its measured cost and its record, the page under 8,000 bytes (the template's pipeline skill checks it
  with `scripts/manager/measure_manager.py lessons`). `forms/learning-record.md` is the shape of one learning record
  (trigger, action, evidence, confidence, scope) and the rule that promotes a record to a decision page.
  ```
  `ops/new-vault.py` copies the whole form (`shutil.copytree`), and `ops/check_pages.py` checks only `decisions/`,
  `concepts/`, `entities/` and `sources/`, so a fresh vault still has 0 pages to check. Run:
  `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 300 "${PY:?}" -m pytest -q -p no:cacheprovider "${W:?}/ops/tests/test_new_vault.py" 2>&1 | tail -1)`
  Expected: `9 passed` (as at f70e84c; `test_the_form_holds_nothing_of_the_owners_vault` scans the forms too: no name
  of the owner's vault, no letter of a refused block).

- [ ] **Step 4 — the README section** (`scripts/manager/README.md`, Task 1's file). Append at the end of the file,
  after one blank line and after Task 5's `## surface.py` section:
````markdown
## measure_manager.py

The manager's own measures (spec 5.6, 5.8, 7.7), from the transcript path the manager gives
(`~/.claude/projects/<project>/<session id>.jsonl`; a call and its context as `usage_report.py` counts them):
its first call against 30,000 tokens (10.1: three starts in a row; question 5: the first transcripts of both profiles,
the one under 30,000 is kept), every call against the 200,000 cap and a `*-handoff.md` file written before each
compaction, since the compaction before or the session's start (10.2), the manager-lessons page read in a tool call of
the first five calls, the page's form, size and recurrences (10.13), and the findings per `Checklist:` item, the
count that promotes a shared cause to a rule (spec 7.6). Read-only, no model, standard library only.

```text
Usage: python3 -I scripts/manager/measure_manager.py first-call TRANSCRIPT... [--limit 30000]
Usage: python3 -I scripts/manager/measure_manager.py calls TRANSCRIPT [--cap 200000] [--handoff-dir DIR]
Usage: python3 -I scripts/manager/measure_manager.py reads TRANSCRIPT TEXT [--calls 5]
Usage: python3 -I scripts/manager/measure_manager.py lessons PAGE [--max-bytes 8000] [--since YYYY-MM-DD]
Usage: python3 -I scripts/manager/measure_manager.py checklist RECORD...
```

Exit 0 when every check passes, 1 when one fails, 2 on a usage error or a missing file. `lessons` with `--since <the
run's first day>` prints the items added, the items fired again with their counts and the recurrences for the run's
measurement page;
`checklist <run>/critique.md <run>/verify.md` prints `<count> <file>:<line>` per cited item, highest first.
````
  Run the last test by name:
  `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_measure_manager.py" -k test_the_readme_and_the_forms_carry_the_tool_s_contract 2>&1 | tail -1)`
  Expected: `1 passed, 15 deselected`. Then the whole file without `-k`. Expected: `16 passed`. Wrong versions run red
  once against the last test (each `1 failed, 15 deselected`): the `checklist` usage line missing; the section named
  `## measure_manager`; the form's item line written with `→`; the record form's `- scope: ` line missing; `rules.md`
  without `forms/learning-record.md`; the vault README without `forms/manager-lessons.md`; the form holding an item
  without arrow, cost and record.

- [ ] **Step 5 — the measurement order** (`references/measuring.md`). Append at the end of the file, after one blank
  line and after Task 5's `### The owner's surface`; the file keeps its one `# ` title, and every `scripts/`,
  `example/` or `references/` path named in it must exist in the skill (`test_skill_md.py` since Task 1,
  `test_skill_md_and_its_references_name_only_files_the_skill_has_and_the_current_rules`), so the section names no
  script of another lane:
````markdown
### After every run, in this order
The main session measures the run and itself before any page or summary cites a number (spec 5.6). The scripts are
the ones above, run in this order:
1. `scripts/check_formats.py <run-dir>`: no number of the run is trusted while it lists an error.
2. `scripts/findings_report.py <run-dir>`: the findings per kind and the escape table.
3. `scripts/usage_report.py --prefix <run>/ --since <date>`: calls and cost per role, once the date of its price
   table is checked against the provider's prices of the day.
4. `scripts/startup_report.py --prefix <run>/ --since <date> --threshold 60000`: the first-write context per session.
5. The manager itself, from its own transcript (`~/.claude/projects/<project>/<session id>.jsonl`), with
   `scripts/manager/measure_manager.py`: `first-call <transcript>...` (under 30,000 tokens, on three starts in a row),
   `calls <transcript> --handoff-dir <checkout>/docs/handoff` (no call over 200,000 tokens, and a hand-off written
   before each compaction), `reads <transcript> decisions/global/manager-lessons.md` (the lessons page read in one of
   the first five calls) and `lessons <vault>/decisions/global/manager-lessons.md --since <the run's first day>` (the
   items added, the items fired again with their counts, the recurrences).
6. `scripts/manager/measure_manager.py checklist <run>/critique.md <run>/verify.md`: the findings per `Checklist:`
   item, highest first; an item that two findings cite is a shared cause, promoted by hand to a rule (spec 7.6).
7. Every number, with the command that produced it, goes into `<vault>/context/measurements/<date>-<run>.md`, committed
   before the owner's summary or any page cites it; `ops/check_pages.py` runs in the vault after every commit and
   prints 0 problems.
````
  Run: `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_skill_md.py" "${SK:?}/scripts/tests/test_docs.py" 2>&1 | tail -1)`
  Expected: `<D0> passed`, Step 1's figure (Task 1 moved the headings test and the named-paths test from
  `test_docs.py` to `test_skill_md.py`, task-01.md 1b; on f70e84c, before that move, `test_docs.py` gave `9 passed`
  with this section appended). A `## ` heading in the section, or a path such as `scripts/collect_run.py` that lane d
  does not have, turns it red.

- [ ] **Step 6 — the manager's page** (`docs/roles/manager-chat.md`, new; no frontmatter, a `# ` title, like
  `docs/roles/MANAGER.md`). Title: `# The manager in chat: the pipeline skill's main session`. Paths in code spans,
  not links (several tools named are other lanes' until the merge). Under 200 lines. Its parts, each with these facts:
  - Opening paragraph (8.3.1, question 1: 1a): the owner's manager is the main session that runs the pipeline skill
    (`.claude/skills/running-specagent-pipelines/`); it is the one chat the owner talks to, and it launches the roles
    as background sessions with the owner's yes. `docs/roles/MANAGER.md` is the harness's manager
    (`claude --agent manager`), a separate design for harness runs.
  - `## No sandbox, four guards` (5.5, 8.2.6, 8.3.8, question 2: 2a): every role runs sandboxed and blind; the manager
    runs without the sandbox because it does what the sandbox refuses the roles: merges in any worktree, `.claude/`
    and `.git` administration, data moved between disks, sessions launched and stopped, transcripts read for
    measurements, the vault pushed. The four guards: the permission rules (never read `~/.config` credentials, never
    push the template); the auto-mode classifier (irreversible deletions are refused and left to the owner); the
    owner's launch rule (agents and the judge only with the owner's yes, in one message with the count, purpose,
    settings files and estimated cost); and it never runs project code or tests itself. The template's project session
    keeps the sandbox on: `.claude/settings.json` (lines 47-64 at f70e84c) sets the sandbox enabled,
    `allowUnsandboxedCommands` false and excludes `claude *`, `uv run harness launch|resume|poll|eval|watch|doctor*|
    abort|integrate *` and `python3 ops/machine-setup.py [--user|--undo]`; the manager's chat is another session.
    A role's refusal (`SANDBOX:`, "Read-only file system", "sandbox violation") is answered by supplying the path,
    host or material into the run folder, never by weakening a sandbox; a step that cannot wait is held, not faked.
  - `## Duties by phase` (5.1-5.9), one line per duty with its tool: before a run, the size rule (a pipeline only
    when one context cannot hold the work, otherwise one session and a verifier), the duty list
    (`scripts/duty_list.py extract <plan-dir> --out <run-dir>/_control/duties.md`), the pre-flight
    (`scripts/manager/preflight.py`; the usage reading of the desktop app's `get_usage` written to
    `_control/usage.json` before each launch, D3), the `_launch.md` table, every time from `date -u`; during a run, the
    monitor (`scripts/monitor_records.py watch <run-dir>`, a background command re-armed with the same command after
    every exit), the surface (`scripts/manager/surface.py <run> --phrases <file> --out <run>/_control/surface.txt
    --every 120`, started after the launch as a background command and re-armed after every exit, as the monitor is),
    orders by `scripts/watch_agents.py --order <agent> <text> <config>` and the `ACK <msg_id>` line, the
    `Merged:` duties with a hex sha; the owner's questions (5.7: routine questions decided with the assumption stated;
    only agent launches, destructive or irreversible actions, merges into `main` and spending asked, once, in one
    message with the sizes and the options; every status line with a digit and a record path; the status answer is
    two or three short lines, "now: …, next: …", whose figures are copied as printed from the stdout of
    `python3 -I <skill>/scripts/manager/surface.py <run> --phrases <owner phrase file>`, never computed, each with the
    record path `<run>/_control/surface.txt`, the whole stdout only when the owner asks for the costs, 10.6);
    measurement (`references/measuring.md`, `### After every run, in this order`).
  - `## Measuring itself` (5.8, 8.2.7, 10.1, 10.2, 10.13, question 5: 5): it starts under 30,000 tokens; both profiles,
    the terminal `claude` profile and `just manager` (`justfile`), are measured once at their first call with
    `measure_manager.py first-call <one transcript of each>` and the one under 30,000 is kept; then `first-call` on
    three starts in a row; at the run's end `calls <transcript> --handoff-dir <checkout>/docs/handoff` and
    `reads <transcript> decisions/global/manager-lessons.md`; the transcript is
    `~/.claude/projects/<project>/<session id>.jsonl`; the numbers go on the run's measurement page
    (`<vault>/context/measurements/<date>-<run>.md`). It hands over at 200k like every role: a hand-off under
    `docs/handoff/` written before the compaction, at the hook's first notice (`.claude/hooks/handoff.py`), then a
    fresh session, never an endless chat.
  - `## Recovery` (5.8, 7.3, need 1): after a reboot `claude respawn --all`; after a compaction or a fresh start, in
    this order: the newest hand-off note, the manager-lessons page, `_control/registry.json` (before any record),
    `head -1` of every record file, the tail of `_watch.log`, `claude agents --json`; then the watcher restarted on
    `_agents.json`; no transcript read back.
  - `## The lessons page` (7.7, 8.2.11, question 3: 3a): `<vault>/decisions/global/manager-lessons.md`, pushed, one
    section per project under `## All projects`, copied once from `templates/vault/forms/manager-lessons.md`; read in
    the first calls of every main session; an item appended the moment a mistake is found, with its measured cost and
    record; the same mistake again appends a date and record to its item; three runs without a firing move it below
    the fold; under 8,000 bytes, checked with `measure_manager.py lessons`; the first four items of spec 7.7 (a duty
    read late, a rollout not simulated, an estimated time, a guessed timeout) are written by the main session with
    their records.
  - `## After a run` (5.9.2, 5.9.3, 7.2, 7.4, 7.6, 10.3, 10.4): an owner decision goes as one line into
    `<vault>/context/owner-statements/<date>.md` in the same turn (the owner's words, the `date -u` time, the meaning
    in one sentence), committed before any page cites it; then the page, global in `decisions/global/`, project in
    `wiki/decisions/`, with `decided`, `by`, `why`, `would_change_if` and one `INDEX.md` line; the measurement page
    before any summary cites a number, `ops/check_pages.py` after every vault write with 0 problems; one `log.md` line
    per unit of work; the learning loop: a lesson becomes a record in the form of `forms/learning-record.md`, and a
    trigger that recurs in two runs or two projects, or a cause two findings share
    (`measure_manager.py checklist <run>/critique.md <run>/verify.md`), becomes a decision page and one line in the
    skill or the brief template, by hand; `audit_read_first.py` before "Read first" is compacted, `replay_cases.py`
    for a finding with a read-only command; roles write only `lessons.md` and their record, the manager the pages.
    Then the collector (Task 6, K2): each item of `## Lessons from this run` marked `(skill: <sha>)` or
    `(skill: none)`, `Merged:` records unmarked; `python3 -I <skill>/scripts/collect_run.py <run> --repo <checkout>
    --plan <plan folder> --kept <page> ...` as a dry run; the list to the owner; on the owner's yes the same command
    with `--apply --yes <digest>`; after three such runs `--apply` alone; the owner reads `<run>/collected.md`.
    The graph over the vault (7.5, question 12): no graph rule before a measurement page of the export's size and a
    query's tokens; that measurement is the main session's.
  In `docs/llms.txt`, append at the end of `## Roles` (after the `Instruction changelog` line at f70e84c):
  ```text
  - [Manager in chat](roles/manager-chat.md): the pipeline skill's main session as the manager: no sandbox and four guards, duties by phase, its own measures, recovery, the lessons page
  ```
  Check (every fact the later tasks and the verifier rely on is on the page):
  ```bash
  F="${W:?}/docs/roles/manager-chat.md"; for s in 'docs/roles/MANAGER.md' '## No sandbox, four guards' '## Duties by phase' '## Measuring itself' '## Recovery' '## The lessons page' '## After a run' '.claude/settings.json' 'allowUnsandboxedCommands' 'just manager' 'measure_manager.py first-call' '--handoff-dir' 'decisions/global/manager-lessons.md' '_control/registry.json' 'watch_agents.py --order' 'ACK <msg_id>' 'surface.py <run> --phrases' '_control/surface.txt' '--every 120' 'two or three short lines' 'claude respawn --all' 'context/owner-statements/' 'context/measurements/' '(skill: <sha>)' '--apply --yes <digest>' 'forms/learning-record.md'; do grep -qF -- "$s" "$F" || echo "missing: $s"; done; echo "checked $(wc -l < "$F") lines"
  ```
  Expected: one line `checked <n> lines` with n under 200 and no `missing:` line. `harness docs-check` is the
  verifier's full suite at M2 (`_common.md:74-76`, Global Constraint 6; C503's rule): it wants every page under
  `docs/` listed in `docs/llms.txt`, so without the line above it would name `roles/manager-chat.md`.

- [ ] **Step 7 — the decision pages** (`wiki/decisions/`). Four pages, each with the frontmatter of
  `wiki/decisions/diagrams-are-mermaid-text.md` (`title`, `type: decision`, `status: draft`, `updated: <the commit's
  date, date -u +%F>`, `audience: [all]`, `decided: 2026-10-29`, `by: owner`, `why`, `would_change_if`,
  `decision_status: decided`, `scope: global`; no `: ` inside a value), a `# ` title equal to `title`, and a body of
  one or two paragraphs: what was decided (owner, 2026-10-29, 17:03 UTC, the question's answer), why, and what the
  template ships for it. Each has a `.summary.md` beside it whose first line is the one given below.
  | Page | `title` | `why` | `would_change_if` | `.summary.md` first line |
  |---|---|---|---|---|
  | `the-manager-is-the-pipeline-skill-main-session.md` (1a) | The manager is the pipeline skill's main session | the owner talks to one chat; the skill's main session already launches, watches, merges and measures the roles, and no page described it beside the harness's manager | the harness's manager runs SpecAgent pipelines with the same duties, or the owner chooses one design for both | `Decision (owner, 2026-10-29): the manager is the main session that runs the pipeline skill; docs/roles/manager-chat.md describes it, docs/roles/MANAGER.md stays the harness's.` |
  | `the-manager-runs-without-the-sandbox.md` (2a) | The manager runs without the sandbox, with four guards | the manager does what the sandbox refuses the roles (merges in any worktree, .claude and .git administration, sessions launched and stopped, transcripts read, the vault pushed); every role stays sandboxed and blind | a sandbox can grant those operations to one session without opening them to the roles, or a guard fails once | `Decision (owner, 2026-10-29): the manager runs without the sandbox; its guards are the permission rules, the auto-mode classifier, the owner's launch rule and never running project code.` |
  | `manager-lessons-live-in-the-vault.md` (3a) | Manager lessons live in the vault, a section per project | the same management mistake never twice in any project; one page that every main session reads in its first calls | the page passes 8,000 bytes with live items, or three runs end with no item fired again and none added | `Decision (owner, 2026-10-29): the manager-lessons page is the vault's decisions/global/manager-lessons.md, pushed, with a section per project; the template ships its form and its check.` |
  | `the-manager-profile-is-measured-at-its-first-call.md` (5) | The manager's profile is measured at its first call | the manager must start under 30,000 tokens; 51,915 were measured with the desktop app's 36 plugins, so the profile is chosen by measurement | neither profile starts under 30,000 tokens, or a change of plugins moves the first call by more than 5,000 tokens | `Decision (owner, 2026-10-29): both manager profiles, the terminal claude profile and just manager, are measured once at the first call; the one under 30,000 tokens is kept.` |
  Append at the end of `wiki/index.md`'s `## Decisions` (after the last line there, Task 5's included):
  ```text
  - [The manager is the pipeline skill's main session](decisions/the-manager-is-the-pipeline-skill-main-session.md): the owner's manager is the chat that runs the pipeline skill; docs/roles/manager-chat.md describes it, MANAGER.md stays the harness's
  - [The manager runs without the sandbox, with four guards](decisions/the-manager-runs-without-the-sandbox.md): permission rules, the auto-mode classifier, the owner's launch rule, never project code; every role stays sandboxed
  - [Manager lessons live in the vault](decisions/manager-lessons-live-in-the-vault.md): the vault's decisions/global/manager-lessons.md with a section per project; the template ships the form and the check
  - [The manager's profile is measured at its first call](decisions/the-manager-profile-is-measured-at-its-first-call.md): the terminal claude profile and just manager measured once; the one under 30,000 tokens kept
  ```
  Append at the end of `wiki/log.md`:
  ```text
  ## <the commit's date> pages written with Task 7 of the manager-build run
  - commit: Task 7 of the manager-build run
  - created: decisions/the-manager-is-the-pipeline-skill-main-session.md
  - created: decisions/the-manager-runs-without-the-sandbox.md
  - created: decisions/manager-lessons-live-in-the-vault.md
  - created: decisions/the-manager-profile-is-measured-at-its-first-call.md
  - updated: index.md
  ```
  Check:
  ```bash
  for p in the-manager-is-the-pipeline-skill-main-session the-manager-runs-without-the-sandbox manager-lessons-live-in-the-vault the-manager-profile-is-measured-at-its-first-call; do head -1 "${W:?}/wiki/decisions/$p.summary.md" | grep -q '^Decision (owner, 2026-10-29): ' || echo "summary: $p"; grep -qF "(decisions/$p.md)" "${W:?}/wiki/index.md" || echo "index: $p"; done; echo pages-checked
  ```
  Expected: `pages-checked` alone. `harness wiki-lint` is the verifier's full suite at M2 (C503's rule): `wiki.py`
  flags a page that `wiki/index.md` does not list, which the check above rules out (at f70e84c its one note is
  `graph/index.md is not built`).

- [ ] **Step 8 — the full checks.**
  ```bash
  (ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 600 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests" 2>&1 | tail -1)
  (cd "${W:?}" && uv run ruff check . && uv run ruff format --check .; echo "exit $?") 2>&1 | tail -3
  ```
  Expected: `<N0 + 16> passed` (146 + 16 = 162 measured at f70e84c in a scratch copy), no `failed` or `error`;
  `All checks passed!`, `<n> files already formatted` and `exit 0`. The repository suite (`uv run pytest -q`, which
  collects these 16 tests by `pyproject.toml:25`), `harness validate`, `docs-check` (with `plan-lint` inside it,
  `catalog.py:350`), `wiki-lint` and `map --check` are the verifier's full suites at M2 (`_common.md:74-76`, Global
  Constraint 6; C503's rule); `bash ops/graph.sh` is `just graph` (`justfile:40-41`), no command of this task.
  The ruff run is the checkout's (0.16.10 with `pyproject.toml`): both Python files of this task passed
  `uv run ruff check --stdin-filename <repo path>` and `ruff format --check --stdin-filename <repo path>` there.

- [ ] **Step 9 — commit and log.**
  ```bash
  git -C "${W:?}" add templates/vault/forms/manager-lessons.md templates/vault/forms/learning-record.md templates/vault/README.md templates/vault/rules.md .claude/skills/running-specagent-pipelines/scripts/manager/measure_manager.py .claude/skills/running-specagent-pipelines/scripts/manager/README.md .claude/skills/running-specagent-pipelines/scripts/tests/test_measure_manager.py .claude/skills/running-specagent-pipelines/references/measuring.md docs/roles/manager-chat.md docs/llms.txt wiki/index.md wiki/log.md wiki/decisions/the-manager-is-the-pipeline-skill-main-session.md wiki/decisions/the-manager-is-the-pipeline-skill-main-session.summary.md wiki/decisions/the-manager-runs-without-the-sandbox.md wiki/decisions/the-manager-runs-without-the-sandbox.summary.md wiki/decisions/manager-lessons-live-in-the-vault.md wiki/decisions/manager-lessons-live-in-the-vault.summary.md wiki/decisions/the-manager-profile-is-measured-at-its-first-call.md wiki/decisions/the-manager-profile-is-measured-at-its-first-call.summary.md
  git -C "${W:?}" diff --cached --name-status "${BASE:?}"
  ```
  Expected: only the added files (`A` or `M`), nothing else.
  `BASE` is the commit Task 7 began on, where the build log's review range starts: `HEAD` now when no
  hand-over committed WIP, else the parent of the first WIP commit (lessons 23:45, B2 of build-log-c).
  Commit with the message
  `feat(manager): Task 7 — the manager-lessons and learning-record forms, the measurement order, the manager's self-measurement and its page`
  and a body naming spec 5.5-5.9, 7.2-7.7, 8.2.6-11, 8.3.1, 8.3.7, 8.3.8, 8.3.13, 8.3.18, questions 1, 2, 3, 5 and the
  acceptance checks 10.1, 10.2, 10.13; then log `Task 7: done — <sha>` in `build-log-d.md`.

## For Task 11
- `docs/roles/VERSION` and `docs/roles/CHANGELOG.md`: this task changes instruction files that `harness audit` counts
  (`templates/` and `.claude/skills/`, but not `docs/roles/manager-chat.md`): `templates/vault/forms/manager-lessons.md`,
  `templates/vault/forms/learning-record.md`, `templates/vault/README.md`, `templates/vault/rules.md`,
  `scripts/manager/measure_manager.py`, `scripts/manager/README.md`, `scripts/tests/test_measure_manager.py` and
  `references/measuring.md`; the release's one VERSION bump names them in its CHANGELOG line.
- `SKILL.md`: one sentence naming `scripts/manager/measure_manager.py` (the manager's own measures, after every run)
  where SKILL.md points to `references/measuring.md`; a link line only, SKILL.md at most 12,000 bytes.
- `docs/template/MIGRATIONS.md` 1.5.0: a vault made before 1.5.0 has no `forms/` (`ops/new-vault.py` copies the form
  only into an empty folder): the sync brief copies `templates/vault/forms/` into the vault, then
  `forms/manager-lessons.md` once to `decisions/global/manager-lessons.md` with its dates and `sources` set and one
  `INDEX.md` line, and runs `ops/check_pages.py` (0 problems).
- `CHANGELOG.md` 1.5.0: the two vault forms, `measure_manager.py`, `references/measuring.md`'s order after every run,
  `docs/roles/manager-chat.md` and the four decision pages of questions 1, 2, 3 and 5.
- The tracker (Task 6's K1): each Deferred item below gets a row whose Plan cell quotes its key, e.g.
  `manager-build Deferred: the vault pages of 8.3.13`; the TD-003 item already names its row.

## Deferred
- the vault pages of 8.3.13: the pages propose-ideas-proactively and truth-only-never-flatter, the manager's start-up
  measurement page and the manager-lessons page itself are the owner's vault pages, written by the main session (D6);
  the template ships the forms and the script that measures.
- TD-003 the learning loop by script: records written from findings by observation hooks (ECC's instinct model with
  its hooks) stay out; the form and the promotion rule ship as text and the loop stays by hand until three runs
  measure the form (spec 7.6; the index's Deferred line for TD-003).
- 7.5 the graph over the vault: measured first by the main session (question 12; 8.2.15); no graph rule and no script
  before its measurement page.
- a script for 10.3 and 10.4: they check the owner's vault at the run's end with the spec's commands (departure 4).
- the 30,000 limit enforced at start-up: `first-call` measures after the start and exits 1 over the limit; no hook can
  stop a start, because the first call's size is known only once it is made.

## Verified
- `usage_report.py` at f70e84c: `lines(path)` :67, `calls(path, seen=None)` :85, `context(u)` :95; transcripts at
  `~/.claude/projects/*/<sessionId>.jsonl` (:64).
- Flags at f70e84c (`grep -o 'add_argument("[^"]*"'`): `startup_report.py` `--prefix`, `--since`, `--threshold`;
  `usage_report.py` `--prefix`, `--since`, `--by-day`; `findings_report.py` and `check_formats.py` take `run_dir`.
- claude 2.1.312 writes a compaction as `{"type":"system","subtype":"compact_boundary",...,"timestamp":ISO,
  "compactMetadata":{"trigger","preTokens"}}` (`grep -ao` in `~/.local/share/claude/versions/2.1.312`).
- `.claude/hooks/handoff.py:4`: hand-offs are `docs/handoff/<date>-<time>-handoff.md`.
- `claude respawn` is in `claude --help`; `SKILL.md:108`: "After a reboot: `claude respawn --all`".
- `justfile:15`: the `manager:` recipe.
- `test_docs.py` at f70e84c: the README tests read `SCRIPTS.glob("*.py")` (not `scripts/manager/`); the reference
  test allows one `# ` title per file and requires every `\b(?:scripts|example|references)/[\w./-]*\w` it finds to
  exist in the skill (by test name in Step 5).
- `templates/vault/ops/check_pages.py:33` scans `decisions`, `concepts`, `entities`, `sources`; `ops/new-vault.py:46`
  copies the form with `shutil.copytree`; `build_indexes.py` and `split_large.py` read `context/` and the page folders.
- `catalog.py:277-284` (docs-check: a page under `docs/` listed in `docs/llms.txt`), `INDEX_MAX_BYTES = 12_000` (:59);
  `docs/llms.txt` is 6,279 bytes at f70e84c; `wiki.py:100` (a page not in `index.md`), `wiki.py:18-19` (200 lines,
  12,000 bytes).
- Measured (scratch copies at f70e84c, the plan worktree's `.venv`): the skill suite 146 passed, 162 with this task's
  files; `test_docs.py` 9 passed with the section; `ops/tests/test_new_vault.py` 9 passed on the plan worktree and its
  8 form tests passed with the forms added; Step 2's `16 failed`, `15 failed, 1 deselected`,
  `15 passed, 1 deselected`; Step 4's `1 passed, 15 deselected`, `16 passed`; 34 wrong versions of the script and 7 of
  the documents red (40 of the script since C15, A5 and A6: below).
- ruff 0.16.10 (`justfile:10` runs `uv run ruff check .`): `ruff check` and `ruff format --check` with
  `--stdin-filename .claude/skills/running-specagent-pipelines/scripts/...` from the checkout pass on both files.
- `datetime.fromisoformat` reads a trailing `Z` since Python 3.11 (docs.python.org/3.12/library/datetime.html).
- C15, A5, A6 (plan fixer, `scratch/plan-fixer/t7`: the planner's scratch tool with the per-item count): the edited
  test file passes `ruff check` and `ruff format --check` (0.16.10, `--stdin-filename`); `16 passed` in the machine's
  zone and with `TZ=UTC`; today's format fails only `test_since_lists_the_items_added_and_the_items_that_fired_again`;
  40 wrong versions red with `TZ=UTC` (the planner's 34, its every-repeat one moved to the per-item count, and 6
  new); with the old test file and `TZ=UTC` the two hand-off versions fail no hand-off test, and on the critic's A5
  fixture, without item 2's repeat of 2026-10-22, the count over every repeat passes.
- `TZ=Etc/GMT-4 date -d 2026-01-15T10:59:00Z` and `-d 2026-10-29T10:59:00Z` both print `14:59 +0400` (UTC+4 all
  year).
- `pyproject.toml:25` at f70e84c: `testpaths` holds `.claude/skills/running-specagent-pipelines/scripts/tests` (C16).
- C503's rule (lessons.md 22:27 UTC): `_common.md:74-76` names `uv run pytest -q`, the ruff pair, `harness validate`,
  `docs-check`, `wiki-lint` and `map --check` as the verifier's full suites, and Global Constraint 6 gives the builder
  its task's tests, commands and the ruff pair; `catalog.py:350` runs `plan-lint` inside docs-check;
  `justfile:40-41`: `graph:` is `bash ops/graph.sh`.
- No shebang (EXE001): lessons.md 22:23 UTC; the tests run the script as `[sys.executable, "-I", str(TOOL), ...]`
  and none reads a mode or a shebang (grep of the test file).
- Task 1 (task-01.md): `test_catalogue.py` checks the README in one test that loops over `scripts/manager/*.py`
  (:596-601), so this task adds no case there; the headings test and the named-paths test move from `test_docs.py` to
  `test_skill_md.py` (:206, :246-248, :301); the two files give `12 passed` at Task 1's commit (5f, :1104-1109).
- Task 5 at 3c9758e (task-05.md:71-78, `## Contracts`; C18): the status answer and the background `--out ...
  --every 120` command, word for word as in Contracts above; `spec.md:695` (5.7: status in two or three lines).
