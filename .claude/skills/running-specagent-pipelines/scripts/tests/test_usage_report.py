"""Tests of usage_report.py on synthetic transcripts: one call per message id (B1), no call for a '<synthetic>' line
(B2), a resumed session's copied calls counted once (B4), the parsing importable without running the report, and
--prefix, --since and --by-day as before; the list prices of 2026-10-29 with their date and page on the first line,
each family priced by its own four prices, the total row last, and the names other scripts import (manager-build
Task 10); the cache reads, cache writes and output in dollars beside their tokens (spec 005, requirement 7a).

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
    """The report's rows for `name`, split into columns: agent, [day], sess, calls, avg ctx, cache rd, rd $, cache wr,
    wr $, output, out $, $ equiv."""
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
    # in 6, output 3,000, cache read 299,980, cache write 14: (6*4 + 3000*20 + 299980*0.2 + 14*8) / 1e6 = 0.12, of it
    # read 0.06, write 0.00 and output 0.06 (the dollars beside their tokens; a call counted per line would triple them)
    assert rows(r.stdout, "t/builder") == [
        ["t/builder", "1", "2", "150,000", "299,980", "0.06", "14", "0.00", "3,000", "0.06", "0.12"]
    ]


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
    # in 6, output 500, cache read 49,980, cache write 14: (24 + 10000 + 9996 + 112) / 1e6 = 0.02, of it read 0.01,
    # write 0.00 and output 0.01
    assert rows(r.stdout, "t/builder") == [
        ["t/builder", "2026-10-23", "1", "2", "25,000", "49,980", "0.01", "14", "0.00", "500", "0.01", "0.02"]
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
    names.append("dollars")  # score_run.py (spec 005, requirement 7a) splits a call's price with it
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
        "dollars": "(message)",
    }


def test_the_cache_reads_cache_writes_and_output_are_printed_as_dollars_beside_their_tokens(home):
    """Spec 005, requirement 7a: the cache is measured in money. A row shows the dollars of the cache reads, the cache
    writes and the output right of their token counts, at the prices of the call's family, one usage per message id
    (each call here is three lines). Per 1M tokens, with read 7,000,000, write 200,000 and output 300,000: Opus
    1.40 + 1.60 + 6.00 = 9.00; Sonnet 0.70 + 0.80 + 3.00 = 4.50; Fable 1.75 + 4.00 + 15.00 = 20.75. Counted per line,
    every figure would be three times as big."""
    big = tokens(0, 300_000, 7_000_000, 200_000)
    for name, sid, model in [
        ("t/opus", SID, "claude-opus-5-5"),
        ("t/sonnet", SID2, "claude-sonnet-5-5"),
        ("t/fable", SID3, "claude-fable-5-1"),
    ]:
        home.session(name, sid, [(10_000, 100, [THINK, TEXT, read("/run/a.md")])])
        priced(home, sid, model, big)
    r = home.run("usage_report.py")
    assert r.returncode == 0, r.stdout + r.stderr
    got = {name: rows(r.stdout, name)[0] for name in ("t/opus", "t/sonnet", "t/fable")}
    assert {name: x[1:3] for name, x in got.items()} == {name: ["1", "1"] for name in got}  # one session, one call
    # from the cache rd column on: cache rd, rd $, cache wr, wr $, output, out $, $ equiv
    assert {name: x[4:] for name, x in got.items()} == {
        "t/opus": ["7,000,000", "1.40", "200,000", "1.60", "300,000", "6.00", "9.00"],
        "t/sonnet": ["7,000,000", "0.70", "200,000", "0.80", "300,000", "3.00", "4.50"],
        "t/fable": ["7,000,000", "1.75", "200,000", "4.00", "300,000", "15.00", "20.75"],
    }
    assert rows(r.stdout, "total") == [["total", "34.25"]]  # the total row keeps its shape: only the total


def test_the_header_names_the_dollar_columns_beside_the_token_columns(home):
    r = home.run("usage_report.py")
    assert r.returncode == 0, r.stdout + r.stderr
    header = " ".join(r.stdout.splitlines()[1].split())
    assert header == "agent day sess calls avg ctx cache rd rd $ cache wr wr $ output out $ $ equiv"


def test_dollars_splits_a_call_s_price_by_kind_in_the_order_of_the_price_table(home):
    """usage_report.dollars(message) -> (input, output, cache read, cache write) dollars of one call at its family's
    prices (the order of PRICE); a missing usage field counts 0 and a message without a model is Opus."""
    code = (
        "import json, sys; sys.path.insert(0, sys.argv[1]); import usage_report as u; "
        "print(json.dumps(u.dollars(json.loads(sys.argv[2]))))"
    )
    message = {"model": "claude-opus-5-5", "usage": tokens(1_000_000, 300_000, 7_000_000, 200_000)}
    r = child(home, code, json.dumps(message))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == pytest.approx([4.0, 6.0, 1.4, 1.6])
    r = child(home, code, json.dumps({"usage": {"output_tokens": 1_000_000, "cache_read_input_tokens": None}}))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == pytest.approx([0.0, 20.0, 0.0, 0.0])
