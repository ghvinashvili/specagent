# Task 10 — `scripts/README.md` split (TD-008) and the prices of `usage_report.py`

planner: d
builder: b
depends_on: 1, 2, 3, 6, 8 (`Merged: a->b` after Task 1, `Merged: c->b` after Tasks 6 and 8)
files: `scripts/README.md` (an index, at most 12,000 bytes), `scripts/docs/<stem>.md` (new: one page per script, its README section moved), `scripts/usage_report.py` (the list prices of 2026-10-29 with their date and source, the `fable` family, the prices line), `scripts/tests/test_docs.py` (its README tests read the pages; the index test), `scripts/tests/test_usage_report.py` (extended: 5 tests at f70e84c, 5 new)
acceptance: 10.18 (the cost total agrees: the `total` row's form and value pinned by a test; Task 5's surface quotes it)
milestone: M2

Paths: `scripts/` and `references/` are under `.claude/skills/running-specagent-pipelines/` (the index's shorthand).
Commands use `W=/home/tite/Desktop/agentic-flow-template/manager-build-b` (builder B's worktree),
`SK="${W:?}/.claude/skills/running-specagent-pipelines"`, `PY="${W:?}/.venv/bin/python"`,
`R=/home/tite/Desktop/agent-system-run/manager-build-2026-10-29` (the run folder) and `X="${R:?}/scratch/builder-b/t10"`
(builder B's scratch for `split_check.py` and its output; never the shell's cwd: the sandbox plants `.claude/` and
`.mcp.json` placeholders in a folder a shell enters). The tree this task is built on: `feat/manager-build-b` after
Task 3 (builder B takes its rows in index order: 2, 3, 10) and after the two merges the main session logs in
`lessons.md`: `Merged: a->b at <sha>` (brings Task 1: `test_docs.py` without `KEPT`, `MOVED` and its two SKILL.md
tests) and `Merged: c->b at <sha>` (brings Tasks 6 and 8: the `collect_run.py` section). Step 1 checks the `done`
commit of each task this one depends on with `git -C "$W" merge-base --is-ancestor <sha> HEAD` (`lessons.md` Read
first 3). Every figure below was measured on f70e84c (the plan worktree's tree outside `docs/exec-plans` equals it),
on Task 1's commit cabb8a3, or read from the task files of Tasks 1, 2, 3 and 6 at 8d2d438; figures that only exist
after those tasks are printed by Step 1. The tests and `split_check.py` ran in the planner's scratch
(`scratch/planner-d/t10/`) on f70e84c's skill with Task 1's deletions from `test_docs.py` (`co/`, its scratch commit
c49bd75; 14 sections where this tree has 17). Standard library only.

## Goal
`scripts/README.md` is 19,156 bytes at f70e84c, a section per script, over the 12 KB rule (TD-008, spec 8.3.9), and
Tasks 2, 3 and 6 add to it. Each `### ` script section moves to its own page `scripts/docs/<stem>.md`, unchanged but
its heading levels and the rewordings of two pages (Interfaces); the README keeps its intro, one index line per
script, `## Config v2` and `## Tests`, and `test_docs.py` keeps the shape: one page per script with its usage line and
options, the README at most 12,000 bytes.

`usage_report.py`'s prices date from 2026-10-08 and its `sonnet` and `haiku` rows hold the prices of Sonnet 4.6 and
Haiku 4.5 (spec 8.3.14). The task sets the list prices of 2026-10-29 from the official pricing page, adds the `fable`
family, keeps the date and the page in two constants, prints them on the report's first line, and pins the `total`
row (the last line; its last field the run's cost, which the surface quotes: 10.18).

## Spec carried
- 8.3.9, the `scripts/README.md` half ("`scripts/README.md` 18,977 bytes ... against the 12 KB rule"; 19,156 at
  f70e84c; the `docs/architecture/harness.md` half is Task 9's).
- 8.3.14 ("`usage_report.py` prices date from 2026-10-08 (`<skill>/scripts/README.md:123`)").
- TD-008 (`docs/exec-plans/tech-debt-tracker.md:12`): the split; the row is closed by Task 11 with this task's commit
  (`## For Task 11`; `docs/` is builder A's, lessons 20:36).
- 10.18 ("the cost in the translated summary equals `usage_report.py`'s total for the run"): Task 5's surface quotes the
  last field of the last line that starts with `total` (task-05.md, its `usage_report.py` contract); this task keeps
  that line's form and pins its value with a test.

## Departures from the spec (with the reasons)
1. One flat price tuple per family: Claude Haiku 5.5's prices for prompts over 100,000 tokens ($0.50 input, $1 1-hour
   cache write, $0.05 cache read, $2.50 output) are not applied. Task 2's watcher prices each call by
   `PRICE[family(model)]` (its K6, written), so a tier in the report alone would make the registry's per-role costs
   disagree with the total; the roles of this template run Opus and Sonnet. Deferred with the fix.
2. Fast mode (Opus 5.5 at $8 / $40) and US-only inference (1.1x) are not applied: no transcript line of this run was
   measured with a speed or geography field. Deferred.
3. The 12 KB rule is applied as 12,000 bytes, the cap of SKILL.md's test and of `.claude/rules/wiki.md:12`.
4. `## Config v2` stays in the README (not a page): SKILL.md:87-88 sends the reader to "fields and defaults in
   `scripts/README.md`", and SKILL.md is builder A's file at 11,933 of 12,000 bytes; with the script sections out, the
   README is 6,160 bytes on the planner's scratch tree (14 index lines, the reworded intro and tests), plus three
   index lines and Task 2's config rows here.

## Contracts
Honoured (cited by heading, never by line):
- Task 1 (builder a), its contract for this task: `test_docs.py` loses `KEPT`, `MOVED` and the two SKILL.md tests to
  `test_skill_md.py` and keeps `REFERENCES`, read by `test_the_main_session_runs_no_hook_of_a_role_s_unmerged_commit`;
  7 tests remain. This task edits that version only (after `Merged: a->b`; built at cabb8a3, whose `test_docs.py`
  differs from Step 2's file only in what this task changes). Task 1's `scripts/manager/README.md` exists on this
  tree; the README index names the folder in one sentence.
- Task 2 (builder b), K6: `PRICE` (name -> a tuple of four $/1M prices: input, output, cache read, cache write),
  `family(model)` and `calls(path, seen=None)` keep their names, the tuple's order and the signatures; the prices may
  change (Task 2's test computes from `PRICE`). Task 2's Step 9 renames the watcher's heading to
  ``### `watch_agents.py` — the watcher, version 3`` and appends its Config v2 rows at the ends of their tables.
- Task 3 (builder b), its Step 5: ``### `monitor_records.py` `` and ``### `duty_list.py` `` under `## Watching`,
  after the `watch_agents.py` section; the `check_formats.py` section extended in place.
- Task 5 (builder d): `surface.py` runs `python3 -I usage_report.py --prefix P [--since YYYY-MM-DD]` and takes the
  run's cost from the last field of the last line that starts with `total` (C4 point 3): that line keeps its form
  (`total` first, the cost last with two decimals) and stays the last line.
- Task 6 (builder c): ``### `collect_run.py` `` at the end of the `## Cleaning up` group.
- Task 7 (builder d, written by this lane): `measure_manager.py` imports `calls`, `lines` and `context`;
  `startup_report.py` (f70e84c :27-28) imports `lines`, `context`, `transcripts`, `started` and `agent_rows`. Every
  name keeps its signature (test 10 of `test_usage_report.py`).
- Task 11 (builder a): edits `test_the_example_config_is_v2_and_check_accepts_it` after `Merged: a+b+c+d`; this task
  leaves that test's body unchanged and gives its tracker row and decisions under `## For Task 11`.
Given: none (this task adds no name another task must honour beyond those above).

## Interfaces
### `scripts/README.md` (after the task)
In order: the title `# Scripts` and the intro paragraph with two edits: "writes nothing unless its section says so."
becomes "writes nothing unless its page says so.", and after its last words, "`tests/` (see Tests).", it goes on:
"Each script's usage, options and files are on its page under `docs/`; this file indexes them and keeps the config
fields and the tests. The manager's own scripts are in `manager/`, with a README of their own." Then each group
heading (`## Watching`, `## Waiting`, `## Measuring`, `## Cleaning up`) with its text, each of its
``### `<file>` — <title>`` sections replaced by the line ``- [`<file>`](docs/<stem>.md): <title>`` in the same order
(one list per group, no blank line inside it, one blank line before and after it). `## Config v2` byte for byte;
`## Tests` byte for byte but one sentence: its words "checks this file, `example/agents.json`, `SKILL.md` and
`references/` against the scripts." become "checks this file, the pages under `docs/` and `example/agents.json`
against the scripts; `test_skill_md.py` checks `SKILL.md` and `references/`." (Task 1 moved the SKILL.md tests
there). No line starts with `### `. At most 12,000 bytes. Step 3's `split_check.py` builds this file from the README
at `HEAD` and holds the three edits in `REWORDED`; the builder copies its output and edits nothing by hand.

### `scripts/docs/<stem>.md` (new, one page per script)
`<stem>` is the script's file name without its suffix (`watch_agents.md`, `judge_after_verify.md`). The page is the
README section moved: the heading ``### `<file>` — <title>`` becomes the title ``# `<file>` — <title>``; a heading
line inside the section (`#### ` or deeper, outside a code fence) loses two `#`; every other line is the same byte for
byte but the rewordings below; trailing blank lines are dropped and the page ends with one newline. One page per
`scripts/*.py` and `scripts/*.sh`, no other `.md` file in `scripts/docs/`. Paths inside stay relative to the skill
folder (`scripts/<file>`, `example/agents.json`), as in the README.

The rewordings of two pages (`split_check.py`'s `REWORDED`): on `docs/watch_agents.md`, `(Config v2 below)` becomes
`(Config v2 in [the README](../README.md))`, the only moved line that points outside its section (Tasks 2, 3 and 6 add
none); on `docs/usage_report.md`, "(list prices of 2026-10-08;" becomes "(list prices of 2026-10-29;", and after the
paragraph that ends "counted them twice." come a blank line and the paragraph "Its first line names the date and the
page of its prices (`PRICES_AS_OF` and `PRICES_URL` in the script): the API list prices per million tokens with the
1-hour cache write, and Haiku 5.5 at its price for prompts up to 100,000 tokens."

The sections to move (headings at f70e84c, lines and bytes from the f70e84c README; three sections come from Tasks 3
and 6). The README's group headings stay at their places:

| README section (heading start) | from | group | page |
|---|---|---|---|
| ``### `watch_agents.py` `` (:11-55, 3,996 B; "version 3" after Task 2) | f70e84c, Task 2 | Watching | `docs/watch_agents.md` |
| ``### `monitor_records.py` `` | Task 3 | Watching | `docs/monitor_records.md` |
| ``### `duty_list.py` `` | Task 3 | Watching | `docs/duty_list.md` |
| ``### `migrate_agents_json.py` `` (:56-71, 1,162 B) | f70e84c | Watching | `docs/migrate_agents_json.md` |
| ``### `judge_after_verify.sh` `` (:72-86, 1,224 B) | f70e84c | Watching | `docs/judge_after_verify.md` |
| ``### `wait_for_task.py` `` (:91-99, 492 B) | f70e84c | Waiting | `docs/wait_for_task.md` |
| ``### `wait_for_ready.py` `` (:100-107, 412 B) | f70e84c | Waiting | `docs/wait_for_ready.md` |
| ``### `wait_for_log.py` `` (:108-113, 212 B) | f70e84c | Waiting | `docs/wait_for_log.md` |
| ``### `usage_report.py` `` (:118-127, 661 B) | f70e84c | Measuring | `docs/usage_report.md` |
| ``### `startup_report.py` `` (:128-137, 740 B) | f70e84c | Measuring | `docs/startup_report.md` |
| ``### `check_formats.py` `` (:138-150, 1,000 B; extended by Task 3) | f70e84c, Task 3 | Measuring | `docs/check_formats.md` |
| ``### `findings_report.py` `` (:151-159, 592 B) | f70e84c | Measuring | `docs/findings_report.md` |
| ``### `audit_read_first.py` `` (:160-169, 710 B) | f70e84c | Measuring | `docs/audit_read_first.md` |
| ``### `replay_cases.py` `` (:170-183, 1,112 B) | f70e84c | Measuring | `docs/replay_cases.md` |
| ``### `make_pack.py` `` (:184-196, 971 B) | f70e84c | Measuring | `docs/make_pack.md` |
| ``### `clean_jobs_tmp.py` `` (:199-211, 1,063 B) | f70e84c | Cleaning up | `docs/clean_jobs_tmp.md` |
| ``### `collect_run.py` `` | Task 6 | Cleaning up | `docs/collect_run.md` |

Kept at f70e84c: the title and intro (:1-8, 533 B), the group headings with their text (395 B), `## Config v2`
(:212-254, 3,254 B), `## Tests` (:255-263, 627 B); the moved sections are 14,347 of the 19,156 bytes. The README has
no Markdown link (`](`) at f70e84c, so no relative link breaks when a section moves one folder down; the watcher
page's one new link is relative to `docs/`.

### `scripts/usage_report.py`
Module constants (the prices from https://platform.claude.com/docs/en/about-claude/pricing, read 2026-10-29; the
1-hour cache write; Haiku 5.5 at its price for prompts up to 100,000 tokens):
```python
PRICES_AS_OF = "2026-10-29"
PRICES_URL = "https://platform.claude.com/docs/en/about-claude/pricing"
PRICE = {  # $ per 1M tokens: input, output, cache read, cache write (1h)
    "opus": (4.0, 20.0, 0.20, 8.0),
    "sonnet": (2.0, 10.0, 0.10, 4.0),
    "haiku": (0.10, 0.50, 0.01, 0.20),
    "fable": (10.0, 50.0, 0.25, 20.0),
}
```
Functions, each keeping exactly this `inspect.signature`: `family(model)`, `agent_rows(prefix='')`,
`agent_sessions(prefix='')`, `started(row)`, `transcripts(sid)`, `lines(path)`, `calls(path, seen=None)`,
`context(u)`, `main(argv=None)`. `family(model)` returns the first of `opus`, `sonnet`, `haiku`, `fable` that the
lower-cased name contains, else `opus` (an empty or missing name too). The docstring's two lines on the prices
(f70e84c :12-13, "as recorded on 2026-10-08 (Opus 5.5) and the usual ratios for Sonnet and Haiku") become: "Cost
constants below are the API list prices per million tokens of PRICES_AS_OF from PRICES_URL (the 1-hour cache write;
Haiku 5.5 at its price for prompts up to 100,000 tokens); the report prints that date and page first: check them
before quoting a figure."

Output (stdout), in this order; options unchanged (`--prefix`, `--since`, `--by-day`):
1. `prices of 2026-10-29 from https://platform.claude.com/docs/en/about-claude/pricing` (the two constants);
2. the header line as at f70e84c;
3. the rows as at f70e84c, the cost `(in*p[0] + out*p[1] + cr*p[2] + cw*p[3]) / 1e6` with `p = PRICE[family(model)]`;
4. last, the total row as at f70e84c: `total` first, the sum of the rows' unrounded costs last, formatted `8.2f`.
Importing the module prints nothing and runs no `claude` (test 4, kept).

### `scripts/tests/test_docs.py` (on Task 1's version)
Constants: `README`, `EXAMPLE`, `REFERENCES` stay; `DOCS = SCRIPTS / "docs"` is new. Helpers: `sections()`,
`watcher_names()`, `config_section()` (the README's `## Config v2`) and `options()` stay; `script_sections()` is
replaced by three: `scripts() -> list[str]` (the sorted names of `scripts/*.py` and `scripts/*.sh`;
`scripts/manager/` has a README of its own), `stem(name) -> str` (the name without its last suffix) and
`script_pages() -> dict[str, str]` (each `DOCS/*.md` whose first line matches ``^# `([\w.]+\.(?:py|sh))` — `` and
whose script's stem equals the page's file stem, by script name: a page titled for another script counts for
neither). The tests after this task (8; Task 1 left 7):

| Test | Replaces | Checks |
|---|---|---|
| `test_every_script_has_a_page_named_after_it_with_its_usage_line` | `test_the_readme_has_a_section_and_a_usage_line_for_every_script` | `script_pages()` names == `scripts()`; `DOCS/*.md` names == the stems + `.md`; each `.py` page has `^ *python3 -I scripts/<name>\b` |
| `test_every_option_a_script_parses_is_on_its_page` | `test_every_option_a_script_parses_is_in_its_section` | each `--x` of `options(p)` on p's page |
| `test_the_watcher_s_page_lists_its_exit_codes` | `test_the_watcher_s_section_lists_its_exit_codes` | `^\| <code> \|` for 0-4 on `docs/watch_agents.md` |
| `test_the_readme_documents_every_field_of_a_v2_config_and_the_short_defaults` | — (unchanged) | the README's `## Config v2` |
| `test_the_example_config_is_v2_and_check_accepts_it` | — (unchanged; Task 11 edits it) | |
| `test_the_judge_launcher_s_page_has_its_usage_line` | `test_the_readme_has_a_section_with_the_usage_line_of_the_judge_launcher` | the usage regex, `JUDGE_POLL`, `JUDGE_DELAY` on `docs/judge_after_verify.md` |
| `test_the_main_session_runs_no_hook_of_a_role_s_unmerged_commit` | — (unchanged) | |
| `test_the_readme_is_an_index_of_at_most_12000_bytes_with_one_line_per_page` | — (new) | bytes <= 12,000; no `^### `; the lines ``^- \[`(<name>)`\]\(docs/(<page>)\): \S`` give each of `scripts()` once, each with its stem's page, each page existing |

### `scripts/tests/test_usage_report.py` (5 tests kept: their costs are Opus's, whose prices do not change)
New: `import json`; the constants `SID4 = "ffffffff-0000-1111-2222-333333333333"` (a fourth session) and `PAGE` (the
pricing page's URL); the helpers `tokens(inp, out, cache_read, cache_write) -> dict` (a `usage` with the four counts),
`priced(home, sid, model, usage)` (rewrites every assistant line of the transcript `sid` but the `<synthetic>` ones
with the given `model` and `usage`; the Home writes Opus and a fixed split: input 3, cache write 7, cache read
context - 10) and `child(home, code, *args)` (runs `code` in `python -I -B -c` with `scripts/` as its `sys.argv[1]`,
under the Home's stub `claude`, `check=False`). The new tests (10 in all), each fixture's figures computed by hand in
its comments (Step 4 has them in full):

| Test | Fixture | The wrong versions it catches |
|---|---|---|
| `test_the_prices_are_the_list_prices_of_2026_10_29_with_their_source` | a child process imports the module: `PRICE`, `PRICES_AS_OF`, `PRICES_URL`; `family()` of `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1`, `CLAUDE-FABLE-5-1`, `""`, `None`, `other` | the 2026-10-08 prices; `fable` missing or priced as `opus`; Sonnet 5.5's cache read at the skill's cached $0.20; `family()` without `lower()` |
| `test_each_family_s_calls_are_priced_by_its_own_four_prices` | one call each: opus, sonnet, fable at input 1,000,000, output 300,000, cache read 7,000,000, cache write 200,000 (13.00, 6.50, 30.75 by hand); haiku at input 90,000, output 1,000,000, cache read 9,000, cache write 900 (a prompt of 99,900 tokens: 0.51) | cache read and write prices swapped in the formula; the 5-minute write price; a family priced as another; Haiku's long-prompt prices |
| `test_the_total_row_is_the_last_line_and_sums_the_unrounded_costs` | three Opus agents at $0.004 each: rows `0.00`, total `0.01` | the total summed from rounded rows; a line after the total; another format |
| `test_the_report_names_the_date_and_source_of_its_prices_on_its_first_line` | with and without a session | no prices line; an old date; another page; the line after the header or on stderr |
| `test_the_names_other_scripts_import_keep_their_signatures` | a child process prints `inspect.signature` of the nine functions | a renamed or dropped name, a changed parameter (the readers: the watcher, `startup_report.py`, `measure_manager.py`) |

## Steps
- [ ] **Step 1 — the baseline.** The dependencies in `HEAD`, the README's sections, the three test counts.
  ```bash
  R=/home/tite/Desktop/agent-system-run/manager-build-2026-10-29
  for t in a:1 b:2 b:3 c:6 c:8; do
    n=${t#*:}
    s=$(grep -oE "^Task $n: done — [0-9a-f]{7,}" "${R:?}/build-log-${t%%:*}.md" | tail -1 | awk '{print $NF}')
    git -C "${W:?}" merge-base --is-ancestor "$s" HEAD 2>/dev/null && echo "Task $n $s in HEAD" || echo "Task $n ${s:-none} MISSING"
  done
  grep -oE 'Merged: (a|c)->b at [0-9a-f]{7,}' "${R:?}/lessons.md"
  ```
  Expected: `Task 1 cabb8a3 in HEAD` (or the sha of a later `Task 1: done` line), then `Task <n> <sha> in HEAD` for
  Tasks 2, 3, 6 and 8, then `Merged: a->b at <sha>` and `Merged: c->b at <sha>` (a second `c->b` line when the main
  session merged after each of Tasks 6 and 8). A `MISSING` line stops the task: the main session merges (lessons
  21:29), never the builder; wait for its line.
  ```bash
  grep -n '^## \|^### ' "${SK:?}/scripts/README.md" | cut -c1-90
  grep -c '^### ' "${SK:?}/scripts/README.md"; ls "${SK:?}/scripts" | grep -cE '\.(py|sh)$'; wc -c < "${SK:?}/scripts/README.md"
  ```
  Expected: `## Watching` with the sections of `watch_agents.py` ("the watcher, version 3"), `monitor_records.py`,
  `duty_list.py`, `migrate_agents_json.py` and `judge_after_verify.sh`, then `## Waiting`, `## Measuring` and
  `## Cleaning up` with theirs in the order of the Interfaces table, then `## Config v2` and `## Tests`; then `17`,
  `17` and the README's bytes (over 12,000: 19,156 at f70e84c before Tasks 2, 3 and 6 added to it). Another order
  changes only the order of Step 3's `same` lines; two equal counts other than 17 change only Step 3's counts
  (`<n> pages`, `moved <n>`); two different counts stop the task (a script without a section or a section without a
  script): message `manager/plan-fixer-b` with the list.
  ```bash
  for f in test_docs.py test_usage_report.py; do (ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/$f" 2>&1 | tail -1); done
  (ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 600 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests" 2>&1 | tail -1)
  ```
  Expected: `7 passed in <t>s`, `5 passed in <t>s`, then `<N0> passed in <t>s` with no `failed`; write N0 in
  `build-log-b.md` (Step 6 expects N0 + 6; N0 was 144 on the planner's scratch tree, which lacks the new test files
  of Tasks 1, 2, 3 and 6).

- [ ] **Step 2 — `test_docs.py`: tests, red.** First the guard that the file is Task 1's built version:
  `git -C "${W:?}" diff --quiet cabb8a3 HEAD -- .claude/skills/running-specagent-pipelines/scripts/tests/test_docs.py && echo task-1-version`.
  Expected: `task-1-version`. Anything else means a commit after Task 1's changed the file: diff it against cabb8a3,
  carry that change into the Write below and tell `manager/plan-fixer-b`. Then write
  `${SK}/scripts/tests/test_docs.py` whole with the Write tool (the skill folder takes Write and Edit only,
  task-01.md:42): the file below differs from cabb8a3's only in the docstring (Task 1's sentence on
  `test_skill_md.py` kept), `DOCS`, the three helpers in place of `script_sections()`, the four renamed tests and the
  index test (the Interfaces table; diffed in the planner's scratch).
````python
"""Tests of the documentation (Task 7; manager-build Task 10): every script has its page under scripts/docs/ with its
usage line and every option it parses, the watcher's page its exit codes; scripts/README.md is an index of at most
12,000 bytes, one line per page, with every field of a v2 config and its default; example/agents.json is a v2 config
that `watch_agents.py --check` accepts, every role of it having a fresh text; the SKILL.md tests are in
test_skill_md.py (manager-build Task 1).

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
"""

import ast
import json
import re
import subprocess
import sys

from transcript_home import SCRIPTS, Home

SKILL = SCRIPTS.parent
README = SCRIPTS / "README.md"
DOCS = SCRIPTS / "docs"
EXAMPLE = SKILL / "example" / "agents.json"
REFERENCES = SKILL / "references"


def watcher_names() -> dict:
    """watch_agents.py's defaults, other fields, agent fields and fresh roles, read in a child process."""
    code = (
        "import json, sys; sys.dont_write_bytecode = True; sys.path.insert(0, sys.argv[1]); import watch_agents as w; "
        "print(json.dumps({'defaults': w.DEFAULTS, 'other': w.OTHER_FIELDS, 'agent': w.AGENT_FIELDS, "
        "'roles': list(w.FRESH)}))"
    )
    return json.loads(
        subprocess.run(
            [sys.executable, "-I", "-c", code, str(SCRIPTS)], capture_output=True, text=True, check=True
        ).stdout
    )


def sections(text: str, depth: int) -> dict[str, str]:
    """Each heading line of at most `depth` #s, to its text up to the next such heading."""
    parts = re.split(rf"(?m)^(?=#{{1,{depth}}} )", text)
    return {part.splitlines()[0]: part for part in parts if part.startswith("#")}


def scripts() -> list[str]:
    """The scripts' names: scripts/*.py and scripts/*.sh (scripts/manager/ has a README of its own)."""
    return sorted(p.name for pattern in ("*.py", "*.sh") for p in SCRIPTS.glob(pattern))


def stem(name: str) -> str:
    return name.rsplit(".", 1)[0]


def script_pages() -> dict[str, str]:
    """Each scripts/docs/<stem>.md whose first line is ``# `<stem>.py` — …`` (or .sh), by script name."""
    found = {}
    for page in sorted(DOCS.glob("*.md")):
        text = page.read_text(encoding="utf-8")
        m = re.match(r"# `([\w.]+\.(?:py|sh))` — ", text)
        if m and stem(m.group(1)) == page.stem:
            found[m.group(1)] = text
    return found


def config_section() -> str:
    return next(
        (
            text
            for head, text in sections(README.read_text(encoding="utf-8"), 2).items()
            if head.startswith("## Config v2")
        ),
        "",
    )


def options(script) -> list[str]:
    """The `--x` strings of the script's add_argument calls, read with ast (the waiters poll from import on)."""
    tree = ast.parse(script.read_text(encoding="utf-8"))
    return sorted(
        {
            str(a.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument"
            for a in node.args
            if isinstance(a, ast.Constant) and str(a.value).startswith("--")
        }
    )


def test_every_script_has_a_page_named_after_it_with_its_usage_line():
    pages = script_pages()
    assert sorted(pages) == scripts()
    assert sorted(p.name for p in DOCS.glob("*.md")) == sorted(f"{stem(n)}.md" for n in scripts())
    usage = [n for n in pages if n.endswith(".py") and not re.search(rf"(?m)^ *python3 -I scripts/{n}\b", pages[n])]
    assert usage == []


def test_every_option_a_script_parses_is_on_its_page():
    pages = script_pages()
    missing = {
        p.name: [o for o in options(p) if not re.search(rf"(?<![\w-]){o}(?![\w-])", pages.get(p.name, ""))]
        for p in sorted(SCRIPTS.glob("*.py"))
    }
    assert {name: opts for name, opts in missing.items() if opts} == {}


def test_the_watcher_s_page_lists_its_exit_codes():
    text = script_pages().get("watch_agents.py", "")
    assert [code for code in range(5) if not re.search(rf"(?m)^\| {code} \|", text)] == []


def test_the_readme_documents_every_field_of_a_v2_config_and_the_short_defaults():
    text, names = config_section(), watcher_names()
    fields = [*names["defaults"], *names["other"], *names["agent"]]
    assert [f for f in fields if f"`{f}`" not in text] == []
    short = {k: json.dumps(v) for k, v in names["defaults"].items() if len(json.dumps(v)) <= 60}
    assert [k for k, v in short.items() if not re.search(rf"(?m)^\| `{k}` \| `{re.escape(v)}` \|", text)] == []


def test_the_example_config_is_v2_and_check_accepts_it(tmp_path):
    config, names = json.loads(EXAMPLE.read_text(encoding="utf-8")), watcher_names()
    assert {"cap", "handoff_wait", "nudges", "permission_wait", "budget", "milestones"} <= set(config)
    roles = {name.split("/")[-1] for name in config["agents"]}
    assert roles <= set(names["roles"]) | set(config.get("fresh", {}))
    assert not config["milestones"] or {"builder", "verifier"} <= roles  # the switch acts on these two roles only
    run = tmp_path / "run"
    run.mkdir()
    for agent in config["agents"].values():
        (run / agent["settings"]).write_text("{}\n", encoding="utf-8")
        (run / agent["status"]).write_text("STATUS: building Task 1\n", encoding="utf-8")
    copy = run / "_agents.json"
    copy.write_text(json.dumps({**config, "run_dir": str(run)}), encoding="utf-8")
    home = Home(tmp_path)
    r = home.run("watch_agents.py", "--check", str(copy))
    assert r.returncode == 0, r.stdout + r.stderr
    assert home.claude_calls() == ["agents --json --all"]
    lines = r.stdout.splitlines()
    assert [f"{name}: no session" for name in config["agents"]] == [x for x in lines if ": no session" in x]
    assert lines[-1] == f"would sleep {config.get('interval', 120)} s and go on"


def test_the_judge_launcher_s_page_has_its_usage_line():
    text = script_pages().get("judge_after_verify.sh", "")
    usage = r"(?m)^ *(?:bash )?scripts/judge_after_verify\.sh <agents-judge\.json> <checkout> <record-file>\.\.\."
    assert re.search(usage, text) and "JUDGE_POLL" in text and "JUDGE_DELAY" in text


def test_the_main_session_runs_no_hook_of_a_role_s_unmerged_commit():
    text = (REFERENCES / "launch.md").read_text(encoding="utf-8")
    assert "`git -c core.hooksPath=/dev/null worktree add --detach <dir> <sha>`" in text
    assert "git worktree add" not in text
    rule = "Every git command the main session runs on a role's commit before that commit is merged into the trunk"
    assert rule in text and "`scripts/judge_after_verify.sh`" in text


def test_the_readme_is_an_index_of_at_most_12000_bytes_with_one_line_per_page():
    text = README.read_text(encoding="utf-8")
    assert len(text.encode()) <= 12_000
    assert re.findall(r"(?m)^### .*", text) == []
    lines = re.findall(r"(?m)^- \[`([\w.]+)`\]\(docs/([\w.-]+)\): \S", text)
    assert sorted(name for name, _ in lines) == scripts()
    assert [(n, page) for n, page in lines if page != f"{stem(n)}.md" or not (DOCS / page).is_file()] == []
````
  Run: `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_docs.py" 2>&1 | grep -oE '::test_\w+|[0-9]+ (passed|failed).*')`
  Expected (measured on the planner's unsplit scratch copy, pytest 9.1.1):
  ```
  ::test_every_script_has_a_page_named_after_it_with_its_usage_line
  ::test_every_option_a_script_parses_is_on_its_page
  ::test_the_watcher_s_page_lists_its_exit_codes
  ::test_the_judge_launcher_s_page_has_its_usage_line
  ::test_the_readme_is_an_index_of_at_most_12000_bytes_with_one_line_per_page
  5 failed, 3 passed in <t>s
  ```
  The three that pass read what stays: the README's `## Config v2`, `example/agents.json` and `references/`.

- [ ] **Step 3 — the split: the pages, the index, green.** `split_check.py` builds the expected README and pages from
  the README at `HEAD` (the table above; the README's three edits and the two pages' rewordings in `REWORDED`) and
  compares them with the checkout, or writes them to a folder with `--out`. Write it with the Write tool to
  `${X}/split_check.py` (builder B's scratch, outside the repository; no shebang, run as `python3 -I`):
````python
"""The move of manager-build Task 10 (TD-008), checked: from scripts/README.md at a base revision, the expected README
(an index) and one page per `### ` script section; compared with a checkout, or written to a folder with --out.

  python3 -I split_check.py <checkout> <base-rev> [--out <dir>]

A page is its section with the title one level up (`# `), the inner headings (four # or more, outside code fences)
two # fewer, the reworded lines of REWORDED applied, the trailing blank lines dropped. The README keeps the parts
before, between and after the sections; each group's sections become one line each, ``- [`<file>`](docs/<stem>.md):
<title>``, between one blank line before and one after. Prints `same|differ <name>` per section and for README.md,
then `moved <n>, differ <d>, README <b> bytes`; exit 1 when anything differs or a reworded line is not found once.
"""

import argparse
import pathlib
import re
import subprocess

SKILL = ".claude/skills/running-specagent-pipelines"
TITLE = re.compile(r"### `([\w.]+\.(?:py|sh))` — (.+)")
PRICES = (
    "Its first line names the date and the page of its prices (`PRICES_AS_OF` and `PRICES_URL` in the script): the API\n"
    "list prices per million tokens with the 1-hour cache write, and Haiku 5.5 at its price for prompts up to 100,000\n"
    "tokens.\n"
)
INTRO = (
    "`tests/` (see Tests). Each script's usage, options and files are on its page under `docs/`; this file\n"
    "indexes them and keeps the config fields and the tests. The manager's own scripts are in `manager/`, with a\n"
    "README of their own.\n"
)
TESTS = (
    "checks this file, the pages under `docs/` and `example/agents.json` against the scripts; `test_skill_md.py`\n"
    "checks `SKILL.md` and `references/`.\n"
)
REWORDED = {
    "README.md": [
        ("writes nothing unless its section says so.", "writes nothing unless its page says so."),
        ("`tests/` (see Tests).\n", INTRO),
        ("checks this file, `example/agents.json`, `SKILL.md` and `references/` against the scripts.\n", TESTS),
    ],
    "watch_agents.py": [("(Config v2 below)", "(Config v2 in [the README](../README.md))")],
    "usage_report.py": [
        ("(list prices of 2026-10-08;", "(list prices of 2026-10-29;"),
        ("counted them twice.\n", "counted them twice.\n\n" + PRICES),
    ],
}


def blocks(text: str) -> list[list[str]]:
    """The lines, cut before each heading of one to three # outside a code fence."""
    found, fence = [[]], False
    for line in text.splitlines():
        if not fence and re.match(r"#{1,3} ", line):
            found.append([])
        if line.startswith("```"):
            fence = not fence
        found[-1].append(line)
    return [b for b in found if b]


def joined(lines: list[str]) -> str:
    lines = list(lines)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n"


def reword(name: str, text: str, problems: list[str]) -> str:
    for old, new in REWORDED.get(name, []):
        if text.count(old) != 1:
            problems.append(f"unmatched {name}: {old!r}")
        text = text.replace(old, new)
    return text


def expected(readme: str, problems: list[str]) -> tuple[str, dict[str, tuple[str, str]]]:
    """The README index and {name: (page file, page text)}, in the README's order."""
    out, pages, pending = [], {}, []
    for block in blocks(readme):
        m = TITLE.fullmatch(block[0])
        if m:
            name, stem = m.group(1), m.group(1).rsplit(".", 1)[0]
            lines, fence = ["# " + block[0][4:]], False
            for line in block[1:]:
                if line.startswith("```"):
                    fence = not fence
                lines.append(line[2:] if not fence and re.match(r"#{4,} ", line) else line)
            pages[name] = (f"{stem}.md", reword(name, joined(lines), problems))
            pending.append(f"- [`{name}`](docs/{stem}.md): {m.group(2)}")
            continue
        if pending:
            out = [*joined(out).splitlines(), "", *pending, ""]
            pending = []
        out += block
    if pending:
        out = [*joined(out).splitlines(), "", *pending, ""]
    return reword("README.md", joined(out), problems), pages


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("checkout", type=pathlib.Path)
    ap.add_argument("base")
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()
    scripts = args.checkout / SKILL / "scripts"
    base = subprocess.run(
        ["git", "-C", str(args.checkout), "show", f"{args.base}:{SKILL}/scripts/README.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    problems: list[str] = []
    readme, pages = expected(base, problems)
    if args.out:
        (args.out / "docs").mkdir(parents=True, exist_ok=True)
        (args.out / "README.md").write_text(readme, encoding="utf-8")
        for page, text in pages.values():
            (args.out / "docs" / page).write_text(text, encoding="utf-8")
        print(f"wrote README.md and {len(pages)} pages to {args.out}, README {len(readme.encode())} bytes")
    differ = 0
    if not args.out:
        paths = {name: scripts / "docs" / page for name, (page, _) in pages.items()}
        paths["README.md"] = scripts / "README.md"
        texts = {name: text for name, (_, text) in pages.items()} | {"README.md": readme}
        for name, path in paths.items():
            same = path.is_file() and path.read_text(encoding="utf-8") == texts[name]
            differ += not same
            print("same" if same else "differ", name)
        print(f"moved {len(pages)}, differ {differ}, README {len((scripts / 'README.md').read_bytes())} bytes")
    for problem in problems:
        print(problem)
    return 1 if differ or problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
````
  Run:
  ```bash
  rm -rf "${X:?}/out"
  python3 -I "${X:?}/split_check.py" "${W:?}" HEAD --out "${X:?}/out"; echo "exit $?"
  ```
  Expected: `wrote README.md and 17 pages to <X>/out, README <b> bytes` with `<b>` at most 12000, then `exit 0`. A
  line `unmatched <name>: '<old>'` (exit 1) means a task before this one changed a line that `REWORDED` rewords: stop
  and send the line to `manager/plan-fixer-b`.
  Copy the output with the Write tool, each file Read whole and written unchanged, its last newline kept (no `cp`:
  the skill folder takes Write and Edit only, task-01.md:42; Read `${SK}/scripts/README.md` before its Write, which
  refuses to overwrite a file the session has not read): `${X}/out/README.md` to `${SK}/scripts/README.md` and each
  `${X}/out/docs/<stem>.md` to `${SK}/scripts/docs/<stem>.md` (17 pages). Edit nothing by hand: a fix goes into
  `REWORDED` and the `--out` run is repeated.
  Run:
  ```bash
  python3 -I "${X:?}/split_check.py" "${W:?}" HEAD; echo "exit $?"
  (ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_docs.py" 2>&1 | tail -1)
  git -C "${W:?}" status --short -- .claude/skills/running-specagent-pipelines
  ```
  Expected: `same <name>` for the 17 scripts in the README's order (the table's: `watch_agents.py`,
  `monitor_records.py`, `duty_list.py`, `migrate_agents_json.py`, `judge_after_verify.sh`, `wait_for_task.py`,
  `wait_for_ready.py`, `wait_for_log.py`, `usage_report.py`, `startup_report.py`, `check_formats.py`,
  `findings_report.py`, `audit_read_first.py`, `replay_cases.py`, `make_pack.py`, `clean_jobs_tmp.py`,
  `collect_run.py`), then `same README.md`, then `moved 17, differ 0, README <b> bytes` (the `<b>` of the `--out`
  run) and `exit 0`; then `8 passed in <t>s`; then
  ` M .claude/skills/running-specagent-pipelines/scripts/README.md`,
  ` M .claude/skills/running-specagent-pipelines/scripts/tests/test_docs.py` and
  `?? .claude/skills/running-specagent-pipelines/scripts/docs/`, nothing else.
  The wrong trees `test_docs.py` fails on (the planner's runs, each red; `scratch/planner-d/t10/docmut.py`): the
  README unsplit; a page missing; a page named with its suffix (`watch_agents.py.md`); an index line missing; a title
  left at `### `; the README over 12,000 bytes; an index line pointing at a suffixed page; a section kept in the
  README beside its page; an extra page; two pages' titles swapped; the judge page without its usage line; a page
  without one of its options; the watcher page without its exit codes; an index line twice; an index line without
  its backticks; a page without its usage line.

- [ ] **Step 4 — `test_usage_report.py`: tests, red.** First the guard that neither file changed since f70e84c (no
  task before this one edits them):
  `git -C "${W:?}" diff --quiet f70e84c HEAD -- .claude/skills/running-specagent-pipelines/scripts/usage_report.py .claude/skills/running-specagent-pipelines/scripts/tests/test_usage_report.py && echo unchanged`.
  Expected: `unchanged`. Anything else: diff them against f70e84c, carry a test change into the Write below and tell
  `manager/plan-fixer-b`. Then write `${SK}/scripts/tests/test_usage_report.py` whole with the Write tool: the five
  tests of f70e84c unchanged, `import json`, `SID4`, `PAGE`, the helpers `tokens()`, `priced()` and `child()`, and the
  five new tests of the Interfaces table.
````python
"""Tests of usage_report.py on synthetic transcripts: one call per message id (B1), no call for a '<synthetic>' line
(B2), a resumed session's copied calls counted once (B4), the parsing importable without running the report, and
--prefix, --since and --by-day as before; the list prices of 2026-10-29 with their date and page on the first line,
each family priced by its own four prices, the total row last, and the names other scripts import (manager-build
Task 10).

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
"""

import json
import subprocess
import sys

import pytest
from transcript_home import SCRIPTS, SYNTHETIC, TEXT, THINK, Home, edit, read

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "66666666-7777-8888-9999-000000000000"
SID3 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
SID4 = "ffffffff-0000-1111-2222-333333333333"
PAGE = "https://platform.claude.com/docs/en/about-claude/pricing"


@pytest.fixture
def home(tmp_path) -> Home:
    return Home(tmp_path)


def rows(out: str, name: str) -> list[list[str]]:
    """The report's rows for `name`, split into columns: agent, [day], sess, calls, avg ctx, cache rd, cache wr,
    output, $ equiv."""
    return [x.split() for x in out.splitlines() if x.split()[:1] == [name]]


def tokens(inp: int, out: int, cache_read: int, cache_write: int) -> dict:
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_write,
    }


def priced(home: Home, sid: str, model: str, usage: dict) -> None:
    """Every assistant line of the transcript `sid` but the '<synthetic>' ones gets `model` and `usage` (the Home
    writes claude-opus-5-5 and input 3, cache write 7, cache read context - 10)."""
    path = home.projects / f"{sid}.jsonl"
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d["type"] == "assistant" and d["message"]["model"] != "<synthetic>":
            d["message"] |= {"model": model, "usage": usage}
        out.append(json.dumps(d) + "\n")
    path.write_text("".join(out), encoding="utf-8")


def child(home: Home, code: str, *args: str) -> subprocess.CompletedProcess:
    """`code` in a child Python that imports from scripts/ (its sys.argv[1]), under the Home's stub `claude`."""
    return subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, str(SCRIPTS), *args],
        capture_output=True,
        text=True,
        timeout=30,
        env=home.env(),
        cwd=home.root,
        check=False,
    )


def test_a_call_written_as_several_lines_counts_once(home):
    """B1: a call is one line per content block, each with the call's id and usage, its tool results between them."""
    home.session(
        "t/builder",
        SID,
        [
            (100_000, 1_000, [THINK, TEXT, read("/run/a.md")]),
            (200_000, 2_000, [THINK, read("/run/b.md"), edit("/run/x.py")]),
        ],
    )
    r = home.run("usage_report.py")
    assert r.returncode == 0, r.stdout + r.stderr
    # in 6, output 3,000, cache read 299,980, cache write 14: (6*4 + 3000*20 + 299980*0.2 + 14*8) / 1e6 = 0.12
    assert rows(r.stdout, "t/builder") == [["t/builder", "1", "2", "150,000", "299,980", "14", "3,000", "0.12"]]


def test_a_synthetic_line_is_no_call(home):
    """B2: Claude Code writes '<synthetic>' assistant lines itself ("No response requested.", a usage-limit notice),
    with zero usage; counted, they add calls and lower the average context."""
    home.session("t/builder", SID, [SYNTHETIC, (100_000, 1_000, [TEXT]), SYNTHETIC])
    r = home.run("usage_report.py")
    assert r.returncode == 0, r.stdout + r.stderr
    assert [x[1:4] for x in rows(r.stdout, "t/builder")] == [["1", "1", "100,000"]]


def test_the_calls_a_resumed_session_copied_count_once(home):
    """B4: Claude Code writes a resumed session under a new id, its transcript beginning with a copy of the session it
    resumes (662 of 1,723 live sessions since 2026-10-22). The earlier start owns the copied calls, whatever order
    `claude agents` lists them in."""
    home.session("t/builder", SID, [(10_000, 100, [TEXT]), (20_000, 200, [read("/run/a.md")])])
    home.session("t/builder", SID2, [(30_000, 300, [edit("/run/x.py")])], start="2026-10-23T10:30:00", resumes=SID)
    home.rows.reverse()
    home.save_rows()
    r = home.run("usage_report.py")
    assert r.returncode == 0, r.stdout + r.stderr
    assert [x[1:4] for x in rows(r.stdout, "t/builder")] == [["2", "3", "20,000"]]


def test_importing_the_parsing_runs_no_report(home):
    """startup_report.py imports usage_report with its own flags: the import neither reads them nor runs `claude`."""
    code = f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); import usage_report; print('imported')"
    r = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, "--threshold", "60000"],
        capture_output=True,
        text=True,
        timeout=30,
        env=home.env(),
        cwd=home.root,
        check=False,
    )
    assert (r.returncode, r.stdout) == (0, "imported\n"), r.stderr
    assert home.claude_calls() == []


def test_prefix_since_and_by_day_as_before(home):
    """One line per call, as before B1: the same numbers before and after the fix."""
    home.session("t/builder", SID, [(10_000, 100, [TEXT])], start="2026-10-21T23:59:50")
    home.session("t/builder", SID2, [(20_000, 200, [TEXT]), (30_000, 300, [TEXT])], start="2026-10-23T08:00:00")
    home.session("u/critic", SID3, [(40_000, 400, [TEXT])])
    r = home.run("usage_report.py", "--prefix", "t/", "--since", "2026-10-22", "--by-day")
    assert r.returncode == 0, r.stdout + r.stderr
    # in 6, output 500, cache read 49,980, cache write 14: (24 + 10000 + 9996 + 112) / 1e6 = 0.02
    assert rows(r.stdout, "t/builder") == [
        ["t/builder", "2026-10-23", "1", "2", "25,000", "49,980", "14", "500", "0.02"]
    ]
    assert rows(r.stdout, "u/critic") == []
    assert home.claude_calls() == ["agents --json --all"]


def test_the_prices_are_the_list_prices_of_2026_10_29_with_their_source(home):
    """8.3.14: the rows of 2026-10-08 held Sonnet 4.6's and Haiku 4.5's prices. Per 1M tokens: input, output, cache
    read, 1-hour cache write; Haiku 5.5 at its price for prompts up to 100,000 tokens; an unknown model is Opus."""
    names = [
        "claude-opus-5-5",
        "claude-sonnet-5-5",
        "claude-haiku-5-5",
        "claude-fable-5-1",
        "CLAUDE-FABLE-5-1",
        "",
        None,
        "other",
    ]
    code = (
        "import json, sys; sys.path.insert(0, sys.argv[1]); import usage_report as u; "
        "print(json.dumps([u.PRICE, u.PRICES_AS_OF, u.PRICES_URL, [u.family(n) for n in json.loads(sys.argv[2])]]))"
    )
    r = child(home, code, json.dumps(names))
    assert r.returncode == 0, r.stderr
    price, as_of, url, families = json.loads(r.stdout)
    assert price == {
        "opus": [4.0, 20.0, 0.20, 8.0],
        "sonnet": [2.0, 10.0, 0.10, 4.0],
        "haiku": [0.10, 0.50, 0.01, 0.20],
        "fable": [10.0, 50.0, 0.25, 20.0],
    }
    assert (as_of, url) == ("2026-10-29", PAGE)
    assert families == ["opus", "sonnet", "haiku", "fable", "fable", "opus", "opus", "opus"]


def test_each_family_s_calls_are_priced_by_its_own_four_prices(home):
    """One call per family: Opus, Sonnet and Fable at input 1,000,000, output 300,000, cache read 7,000,000, cache
    write 200,000; Haiku at a prompt of 99,900 tokens (input, cache read and cache write), under its long-prompt
    prices' 100,000."""
    big = tokens(1_000_000, 300_000, 7_000_000, 200_000)
    for name, sid, model, usage in [
        ("t/opus", SID, "claude-opus-5-5", big),
        ("t/sonnet", SID2, "claude-sonnet-5-5", big),
        ("t/fable", SID3, "claude-fable-5-1", big),
        ("t/haiku", SID4, "claude-haiku-5-5", tokens(90_000, 1_000_000, 9_000, 900)),
    ]:
        home.session(name, sid, [(10_000, 100, [TEXT])])
        priced(home, sid, model, usage)
    r = home.run("usage_report.py")
    assert r.returncode == 0, r.stdout + r.stderr
    # opus 1*4 + 0.3*20 + 7*0.2 + 0.2*8 = 13.00; sonnet 1*2 + 0.3*10 + 7*0.1 + 0.2*4 = 6.50;
    # fable 1*10 + 0.3*50 + 7*0.25 + 0.2*20 = 30.75; haiku 0.09*0.1 + 1*0.5 + 0.009*0.01 + 0.0009*0.2 = 0.50927;
    # the total 50.75927. Swapped cache prices give opus 66.04, the 5-minute write 12.40, Sonnet's cache read at
    # $0.20 7.20, the old Sonnet 10.80, the old Haiku 5.09, Haiku's long-prompt prices 2.55, Fable as Opus 13.00.
    costs = {name: rows(r.stdout, name)[0][-1] for name in ("t/opus", "t/sonnet", "t/fable", "t/haiku")}
    assert costs == {"t/opus": "13.00", "t/sonnet": "6.50", "t/fable": "30.75", "t/haiku": "0.51"}
    assert rows(r.stdout, "total") == [["total", "50.76"]]


def test_the_total_row_is_the_last_line_and_sums_the_unrounded_costs(home):
    """surface.py (manager-build Task 5) quotes the last field of the last line that starts with `total` (10.18)."""
    for name, sid in [("t/builder", SID), ("t/critic", SID2), ("t/verifier", SID3)]:
        home.session(name, sid, [(10_000, 100, [TEXT])])
        priced(home, sid, "claude-opus-5-5", tokens(0, 200, 0, 0))
    r = home.run("usage_report.py")
    assert r.returncode == 0, r.stdout + r.stderr
    # each 200 * 20 / 1e6 = 0.004, printed 0.00; the total 0.012, printed 0.01 (from the rounded rows 0.00)
    assert [rows(r.stdout, n)[0][-1] for n in ("t/builder", "t/critic", "t/verifier")] == ["0.00", "0.00", "0.00"]
    last = r.stdout.splitlines()[-1]
    assert last.startswith("total ") and last.split() == ["total", "0.01"]


def test_the_report_names_the_date_and_source_of_its_prices_on_its_first_line(home):
    """8.3.14: a figure is quoted with the date and the page of its prices; the header is line 2, the total row
    last, with and without a session."""
    first = f"prices of 2026-10-29 from {PAGE}"
    r = home.run("usage_report.py")
    assert r.returncode == 0, r.stdout + r.stderr
    lines = r.stdout.splitlines()
    assert [lines[0], lines[1].split()[:2], lines[-1].split()] == [first, ["agent", "day"], ["total", "0.00"]]
    home.session("t/builder", SID, [(10_000, 100, [TEXT])])
    r = home.run("usage_report.py", "--prefix", "t/", "--by-day")
    assert r.returncode == 0, r.stdout + r.stderr
    lines = r.stdout.splitlines()
    assert [lines[0], lines[1].split()[0], lines[2].split()[0], len(lines)] == [first, "agent", "t/builder", 4]


def test_the_names_other_scripts_import_keep_their_signatures(home):
    """The watcher (PRICE, family, calls: manager-build Task 2's K6), startup_report.py (lines, context, transcripts,
    started, agent_rows) and measure_manager.py (calls, lines, context: Task 7) import these by name."""
    names = ["family", "agent_rows", "agent_sessions", "started", "transcripts", "lines", "calls", "context", "main"]
    code = (
        "import inspect, json, sys; sys.path.insert(0, sys.argv[1]); import usage_report as u; "
        "print(json.dumps({n: str(inspect.signature(getattr(u, n))) for n in sys.argv[2:]}))"
    )
    r = child(home, code, *names)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {
        "family": "(model)",
        "agent_rows": "(prefix='')",
        "agent_sessions": "(prefix='')",
        "started": "(row)",
        "transcripts": "(sid)",
        "lines": "(path)",
        "calls": "(path, seen=None)",
        "context": "(u)",
        "main": "(argv=None)",
    }
````
  Run: `(ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_usage_report.py" 2>&1 | grep -oE '::test_\w+|[0-9]+ (passed|failed).*')`
  Expected (measured on f70e84c's script with this file, pytest 9.1.1):
  ```
  ::test_the_prices_are_the_list_prices_of_2026_10_29_with_their_source
  ::test_each_family_s_calls_are_priced_by_its_own_four_prices
  ::test_the_report_names_the_date_and_source_of_its_prices_on_its_first_line
  3 failed, 7 passed in <t>s
  ```
  The total-row test and the signature test pass before Step 5 and after it: they guard what Task 5's surface and the
  importers (Task 2's watcher, `startup_report.py`, Task 7's `measure_manager.py`) read.

- [ ] **Step 5 — `usage_report.py`: green.** Edit `${SK}/scripts/usage_report.py` with the Edit tool (the file keeps
  its first line and its mode) to the Interfaces above: `PRICES_AS_OF` and `PRICES_URL` above `PRICE`, the four
  families' prices, `family()` over the four names, the docstring's two price lines replaced by the three of the
  Interfaces, and `prices of <PRICES_AS_OF> from <PRICES_URL>` printed before the header. The page's price sentence
  moved with the page in Step 3; this step changes the script only. `main()` is 45 lines at f70e84c (`ast`,
  `end_lineno - lineno + 1`) and the prices line adds one: no function of the file passes 50 lines (the second
  command; on f70e84c's file it prints `[]`, and `[('main', 45)]` with the bound at 44).
  Run:
  ```bash
  (ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 120 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests/test_usage_report.py" 2>&1 | tail -1)
  "${PY:?}" -I -c 'import ast, sys; t = ast.parse(open(sys.argv[1], encoding="utf-8").read()); print([(f.name, f.end_lineno - f.lineno + 1) for f in t.body if isinstance(f, ast.FunctionDef) and f.end_lineno - f.lineno + 1 > 50])' "${SK:?}/scripts/usage_report.py"
  ```
  Expected: `10 passed in <t>s`, then `[]`.
  The wrong versions `test_usage_report.py` fails on (the planner's runs, each red; `scratch/planner-d/t10/usemut.py`):
  the 2026-10-08 prices; `fable` missing; `fable` priced but not a family; `fable` priced as `opus`; Sonnet's cache
  read at $0.20; the cache read and write prices swapped in the formula; input and output swapped; the 5-minute write
  price; Haiku's long-prompt prices; the total summed from the rounded rows; a line after the total; the total with
  three decimals; the total with a dollar sign; no prices line; the old date; another page; the prices line after the
  header; the prices line on stderr; an unknown model priced as Haiku; `family()` without `lower()`; `calls()` with
  another default for `seen`; `family()`'s parameter renamed; `agent_sessions()` without its default; `context()`
  renamed.

- [ ] **Step 6 — the task's checks.** The skill suite (this task's two test files and every test that imports
  `usage_report.py` or reads the README), the split once more, the README's bytes, the ruff pair:
  ```bash
  (ulimit -v 8388608; PYTHONDONTWRITEBYTECODE=1 timeout -k 10 600 "${PY:?}" -m pytest -q -p no:cacheprovider "${SK:?}/scripts/tests" 2>&1 | tail -1)
  python3 -I "${X:?}/split_check.py" "${W:?}" HEAD | tail -1; wc -c < "${SK:?}/scripts/README.md"
  (cd "${W:?}" && uv run ruff check . && uv run ruff format --check .; echo "exit $?") 2>&1 | tail -3
  ```
  Expected: `<N0 + 6> passed in <t>s` (N0 from Step 1; 144 -> 150 on the planner's scratch tree);
  `moved 17, differ 0, README <b> bytes` and `<b>` again, at most 12000 (write it in `build-log-b.md` for Task 11's
  tracker row); `All checks passed!`, `<n> files already formatted`, `exit 0`. Not in this task (lessons 22:27,
  C503): the harness suite, `harness validate`, `docs-check`, `wiki-lint` and `map --check` are the verifier's at M2.

- [ ] **Step 7 — commit and log.**
  ```bash
  git -C "${W:?}" add .claude/skills/running-specagent-pipelines/scripts/README.md .claude/skills/running-specagent-pipelines/scripts/docs .claude/skills/running-specagent-pipelines/scripts/usage_report.py .claude/skills/running-specagent-pipelines/scripts/tests/test_docs.py .claude/skills/running-specagent-pipelines/scripts/tests/test_usage_report.py
  git -C "${W:?}" diff --cached --name-status "${BASE:?}"
  ```
  `BASE` is the commit Task 10 began on, where the build log's review range starts: `HEAD` now when no hand-over
  committed WIP, else the parent of the first WIP commit (lessons 23:45, B2 of build-log-c). Expected: `M` for the
  README, `usage_report.py` and the two test files and `A` for the 17 pages, nothing else (untracked sandbox
  placeholders such as `.mcp.json` are not listed). Commit with the message
  `feat(manager): Task 10 — scripts/README.md split into one page per script (TD-008) and the prices of usage_report.py`
  and a body naming spec 8.3.9 and 8.3.14, TD-008 and the acceptance check 10.18 (the `total` row's form pinned); then
  `git -C "${W:?}" diff --stat "${BASE:?}" HEAD | tail -1`. Expected: `21 files changed, ...`. Log
  `Task 10: done — <sha>` in `build-log-b.md`, with N0 and the README's bytes.

## For Task 11
(builder B cannot write `docs/` or `wiki/`, lessons 20:36; Task 11 writes these after `Merged: a+b+c+d`)
- Tracker: TD-008 closed by Task 10's commit: `scripts/README.md` <bytes at that commit> (Step 6's `<b>`, in
  `build-log-b.md`), an index; each script's section is its page under `scripts/docs/`; `test_docs.py` keeps both.
- Decision `skill-script-pages`, "The skill's script docs: one page per script, the README an index": each script's
  usage, options and files live in `scripts/docs/<stem>.md`; `scripts/README.md` holds the index line, the config
  fields and the tests, at most 12,000 bytes; a new script adds its page and its line. Evidence: TD-008, spec 8.3.9,
  the README's 19,156 bytes at f70e84c, `test_docs.py`'s index test. Task: 10.
- Decision `dated-api-prices`, "usage_report.py's prices carry their date and source": the list prices of
  2026-10-29 from the official page in `PRICE`, the date and page in `PRICES_AS_OF` and `PRICES_URL`, printed on the
  report's first line; one flat tuple per family (Haiku 5.5's long-prompt prices, fast mode and US-only inference are
  Deferred). Evidence: spec 8.3.14; the pricing page read 2026-10-29; the old `sonnet` and `haiku` rows held Sonnet
  4.6's and Haiku 4.5's prices. Task: 10.
- `wiki/index.md` and `wiki/log.md` one line each for the two pages; MIGRATIONS 1.5.0: `usage_report.py`'s first line
  is now `prices of <date> from <url>` (the header is line 2, the total row unchanged); the script sections of
  `scripts/README.md` moved to `scripts/docs/<stem>.md`.
- `references/measuring.md:2` (C506; builder A's Task 11, after the merges; Task 10 does not write `references/`):
  "(usage and options in `scripts/README.md`)" becomes "(usage and options on each script's page under
  `scripts/docs/`, indexed in `scripts/README.md`)": after Task 10 the README holds no usage line and no option.

## Deferred
- Haiku 5.5's long-prompt prices (over 100,000 prompt tokens, counting input, cache reads and cache writes; each
  request priced on its own): a `price(model, usage)` function that both the watcher and the report read, in one
  task with Task 2's K6 changed (departure 1).
- Fast mode (Opus 5.5 $8 / $40) and `inference_geo: "us"` (1.1x): after a transcript line with the field is recorded
  (departure 2).
- A warning when `PRICES_AS_OF` is older than a set number of days: it needs a clock the tests control; the date on
  the first line keeps the age visible meanwhile.

## Verified
- `usage_report.py` at f70e84c: docstring prices :12-13, `PRICE` :25-29 (`opus` (4.0, 20.0, 0.20, 8.0), `sonnet`
  (3.0, 15.0, 0.30, 6.0), `haiku` (1.0, 5.0, 0.10, 2.0)), `family` :32-34 (unknown -> `opus`), `agent_rows` :37,
  `agent_sessions` :50, `started` :55, `transcripts` :63, `lines` :67, `calls` :85, `context` :95, `main` :100
  (`--prefix`, `--since`, `--by-day` :102-104), the cost :131, the header :134-136, the total row :144
  (`git show f70e84c:<skill>/scripts/usage_report.py`).
- The pricing page https://platform.claude.com/docs/en/about-claude/pricing (read 2026-10-29), per MTok, input / 5m
  write / 1h write / cache read / output: Fable 5.1 $10 / $12.50 / $20 / $0.25 / $50; Opus 5.5 $4 / $5 / $8 / $0.20 /
  $20; Sonnet 5.5 $2 / $2.50 / $4 / $0.10 / $10; Haiku 5.5 up to 100,000 prompt tokens $0.10 / $0.125 / $0.20 /
  $0.01 / $0.50, over $0.50 / $0.625 / $1 / $0.05 / $2.50 ("A request's prompt length counts all of its input tokens,
  including cache reads and cache writes"); fast mode Opus 5.5 $8 / $40; `inference_geo: "us"` 1.1x. The claude-api
  skill's cached table (2026-10-06) gives Sonnet 5.5 cache reads $0.20; the live page's footnote 2 (0.05x the base
  input) gives $0.10, and the live page is used.
- The README at f70e84c: 19,156 bytes, 263 lines; the sections, lines and bytes of the table above (an `awk` over
  `git show f70e84c:<skill>/scripts/README.md`); `grep -n '](' ` finds no link.
- `test_docs.py` at f70e84c: `README` :19 read at :61, :69, :172; `script_sections` :59-62, `config_section` :65-73,
  the tests :90, :96, :105, :110, :118, :169, :180; Task 1's step 1b deletes :22-36 and :140-168 (task-01.md).
- Task 1 built: `Task 1: done — cabb8a3 (...)` (`build-log-a.md:3`, the form Step 1's loop reads); its file
  (`git show cabb8a3:<skill>/scripts/tests/test_docs.py`) differs from Step 2's file only in the docstring (its
  sentence on `test_skill_md.py` kept in Step 2's), `DOCS`, `script_sections()` -> `scripts()`, `stem()`,
  `script_pages()`, the four renamed tests and the index test (`diff` in `scratch/planner-d/t10/`).
- `test_usage_report.py` at f70e84c: 5 tests (:30, :46, :55, :68, :84), `rows()` :24-27, the Opus costs in the
  comments of :42 and :91; `transcript_home.py`: `Home.session` writes `"model": "claude-opus-5-5"` and the usage
  input 3, cache write 7, cache read context - 10, output as given.
- The red runs, by the steps' own commands: Step 2's on the planner's unsplit copy (`t10/mut/unsplit`): the five
  names and `5 failed, 3 passed`; Step 4's on f70e84c's skill with the new test file (`t10/red4`, its
  `usage_report.py` equal to f70e84c's by `cmp`): the three names and `3 failed, 7 passed` (pytest 9.1.1, the plan
  worktree's `.venv`).
- The green runs on the scratch checkout `t10/co` (scratch commit c49bd75: f70e84c's skill with Task 1's deletions):
  `split_check.py` 15 `same`, `moved 14, differ 0, README 6160 bytes`, exit 0, and exit 1 on three wrong moves and on
  an unmatched rewording; `test_docs.py` `8 passed`; `test_usage_report.py` `10 passed` on the planner's
  implementation (docstring :12-13 -> three lines, the constants above `PRICE`, `family()` over the four names, the
  prices line first); the skill suite 144 -> 150 passed.
- The wrong versions of Steps 3 and 5: 16 of 16 doc trees red in `test_docs.py` (`t10/docmut.py`) and 24 of 24
  `usage_report.py` versions red in `test_usage_report.py` (`t10/usemut.py`).
- ruff 0.16.10 (`justfile:10`): both test files pass `ruff check` and `ruff format --check` with `--stdin-filename`
  at their repository paths (lessons 21:34, 21:57). The skill folder takes Write and Edit only (task-01.md:42); this
  task adds no script to the repository, so no shebang question arises (lessons 22:23; `split_check.py` lives in
  builder B's scratch and has none).
- Readers of the names: `startup_report.py` :27-28 (`import usage_report as ur`), `ur.lines` :57, `ur.context`
  :65-73, `ur.transcripts` and `ur.started` :104, `ur.agent_rows` :141; Task 2's K6 and its test helper
  `usage_report()` (task-02.md, Contracts and the test helpers); Task 7's Contracts (`calls`, `lines`, `context`).
- SKILL.md :87-88 at f70e84c (:85-86 at cabb8a3: "fields and defaults in `scripts/README.md`") and
  `example/README.md:50` ("fields in `../scripts/README.md`"): both stay true, the README keeping the config fields.
  `references/measuring.md:2` ("usage and options in `scripts/README.md`", the same at f70e84c and cabb8a3) does not:
  no usage line or option stays in the README, so Task 11 rewords it (`## For Task 11`, C506).
- `.claude/rules/docs.md` applies to `docs/**/*.md` and `docs/llms.txt` only (its `paths:`); `docs/llms.txt` names no
  skill file; `.claude/rules/wiki.md:12`: 12,000 bytes per page.
- Tasks 2 and 6 leave `test_docs.py` unedited (task-02.md:42, task-06.md:934); Task 3 reads it only (task-03.md Step
  5); Task 8's files are outside the skill (index row 8), so the 17 sections are 14 + Task 3's 2 + Task 6's 1.
- git 2.43.0 (`git --version`) in a scratch repo (`scratch/plan-fixer-b/gitprobe`: a base commit, a WIP commit with an
  add and a delete, two more staged paths): `git diff --cached --name-status <base>` -> `A`, `A`, `M`, `D` and no
  untracked path, `git status --short` two lines and `??`; `git diff --stat <base> HEAD | tail -n 1` ->
  ` 4 files changed`, `git show --stat HEAD` ` 2 files changed` (Step 7, B2 of build-log-c).
