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
