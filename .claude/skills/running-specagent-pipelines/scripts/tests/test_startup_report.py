"""Tests of startup_report.py on synthetic transcripts: a session's start-up cost is the context of its first write
call (an Edit, a Write, or a Bash command with `git commit`, `>>` or `tee -a`); per agent the sessions, those that
never wrote, the median and the maximum; the sessions over the threshold with the files they read before the write.

  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
"""

import pytest
from transcript_home import SCRIPTS, SYNTHETIC, TEXT, THINK, Home, bash, edit, read, tool, write


def sid(n: int) -> str:
    return f"{n:08d}-0000-4000-8000-000000000000"


@pytest.fixture
def home(tmp_path) -> Home:
    return Home(tmp_path)


def report(home: Home, *args: str) -> str:
    r = home.run("startup_report.py", *args)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def row(out: str, name: str) -> list[str]:
    """The columns after the agent's name: sessions, no write, resumed, median, max, over the threshold."""
    [line] = [x for x in out.splitlines() if x.split()[:1] == [name]]
    return line.split()[1:]


def over(out: str) -> list[str]:
    """The lines of the sessions over the threshold."""
    return [x for x in out.splitlines() if x.startswith("- ")]


@pytest.mark.parametrize(
    "block, counts",
    [
        (edit("/run/x.py"), True),
        (write("/run/x.py"), True),
        (bash('git commit -m "Task 5"'), True),
        (bash("git -C /skill -c user.name=agentsys/builder -c user.email=a@b commit -F msg.txt"), True),
        (bash('echo "Task 5: done" >> build-log.md'), True),
        (bash("printf x | tee -a build-log.md"), True),
        (bash("git -C /skill log --oneline -1"), False),
        (bash("sed -n 1,40p build-log.md > /dev/null"), False),
        (read("/run/x.py"), False),
        (tool("Grep", pattern="Task 5"), False),
    ],
)
def test_what_counts_as_a_write(home, block, counts):
    home.session(
        "t/builder",
        sid(1),
        [(10_000, 10, [read("/run/a.md")]), (20_000, 10, [TEXT, block]), (30_000, 10, [edit("/run/z.py")])],
    )
    cost = "20,000" if counts else "30,000"
    assert row(report(home), "t/builder") == ["1", "0", "0", cost, cost, "0"]


def test_the_cost_is_the_first_write_calls_context_and_the_reads_are_those_before_it(home):
    """The write's call is split over lines with tool results between them (the live shape); a Read or a Bash in that
    same call ran beside the write, not before it, and a file read twice is listed once. The Bash commands before the
    write are counted: the live sessions read mostly with them (demo/critic 02806580: 77 Bash, no Read)."""
    home.session(
        "t/builder",
        sid(1),
        [
            (25_000, 10, [THINK, read("/run/a.md"), read("/run/b.md")]),
            (35_000, 10, [read("/run/a.md"), read("/run/c.md"), bash("sed -n 1,20p /run/e.md")]),
            (45_000, 10, [THINK, TEXT, read("/run/d.md"), bash("ls /run"), edit("/run/x.py")]),
            (55_000, 10, [write("/run/y.py")]),
        ],
    )
    out = report(home, "--threshold", "40000")
    assert row(out, "t/builder") == ["1", "0", "0", "45,000", "45,000", "1"]
    assert over(out) == [
        (
            f"- t/builder {sid(1)}: 45,000 at call 3 (2026-10-23 10:00 UTC); 1 Bash before it; "
            "reads before it (3): /run/a.md, /run/b.md, /run/c.md"
        )
    ]


def test_at_most_12_paths_are_listed(home):
    paths = [f"/run/f{i:02d}.md" for i in range(15)]
    home.session("t/builder", sid(1), [*[(70_000, 10, [read(p)]) for p in paths], (80_000, 10, [edit("/run/x.py")])])
    [line] = over(report(home))
    assert line.endswith("; reads before it (15): " + ", ".join(paths[:12]) + " (+3 more)")


def test_per_agent_count_median_maximum_no_write_and_the_threshold(home):
    for n, cost in ((1, 10_000), (2, 70_000), (3, 90_000)):
        home.session("t/builder", sid(n), [(5_000, 10, [read("/run/a.md")]), (cost, 10, [edit("/run/x.py")])])
    home.session("t/builder", sid(4), [(5_000, 10, [read("/run/a.md")]), (6_000, 10, [TEXT])])  # never wrote
    home.session("t/critic", sid(5), [(30_000, 10, [bash("cat >> critique.md <<'EOF'\n#### C1\nEOF")])])
    out = report(home)
    assert row(out, "t/builder") == ["3", "1", "0", "70,000", "90,000", "2"]
    assert row(out, "t/critic") == ["1", "0", "0", "30,000", "30,000", "0"]
    assert row(out, "total") == ["4", "1", "0", "50,000", "90,000", "2"]
    assert [x.split()[2] for x in over(out)] == [f"{sid(3)}:", f"{sid(2)}:"]  # the largest first
    out = report(home, "--threshold", "80000")
    assert row(out, "t/builder")[-1] == "1" and len(over(out)) == 1


def test_a_session_that_never_wrote_is_over_the_threshold_when_its_context_passed_it(home):
    """B6: most live sessions that never wrote reached the cap before their first write (demo/critic: 24 of 30 past
    200,000), so their resumes wrote; they are the costliest start-ups. Each one counts in the threshold column and
    is listed with its largest call; the median and the maximum stay those of the measured writes."""
    home.session("t/critic", sid(1), [(20_000, 10, [edit("/run/x.py")])])
    home.session(
        "t/critic",
        sid(2),
        [
            (50_000, 10, [read("/run/a.md"), bash("ls /run")]),
            (210_000, 10, [bash("sed -n 1,9p /run/b.md"), read("/run/a.md")]),
            (205_000, 10, [TEXT]),
        ],
    )
    home.session("t/critic", sid(3), [(30_000, 10, [read("/run/a.md")])])  # never wrote, stayed under it
    home.session("t/critic", sid(4), [(100_000, 10, [write("/run/critique.md")])])
    out = report(home)
    assert row(out, "t/critic") == ["2", "2", "0", "60,000", "100,000", "2"]
    assert row(out, "total") == ["2", "2", "0", "60,000", "100,000", "2"]
    assert over(out) == [
        (
            f"- t/critic {sid(2)}: no write in 3 calls, 210,000 at call 2 (2026-10-23 10:00 UTC); 2 Bash; reads (1): "
            "/run/a.md"
        ),
        f"- t/critic {sid(4)}: 100,000 at call 1 (2026-10-23 10:00 UTC); 0 Bash before it; reads before it (0)",
    ]
    assert row(report(home, "--threshold", "220000"), "t/critic")[-1] == "0"


def test_since_prefix_and_a_session_without_a_call(home):
    home.session("t/builder", sid(1), [(10_000, 10, [edit("/x")])], start="2026-10-21T23:59:50")
    home.session("t/builder", sid(2), [(20_000, 10, [edit("/x")])], start="2026-10-22T00:00:00")
    home.session("t/builder", sid(3), [])  # never made a call: no start-up to measure
    home.session("u/builder", sid(4), [(40_000, 10, [edit("/x")])])
    out = report(home, "--prefix", "t/", "--since", "2026-10-22")
    assert row(out, "t/builder") == ["1", "0", "0", "20,000", "20,000", "0"]
    assert "u/builder" not in out
    assert home.claude_calls() == ["agents --json --all"]  # nothing else is run
    assert "no session matched" in report(home, "--prefix", "v/")


def test_a_resumed_session_is_counted_as_resumed_not_measured(home):
    """B4: a resumed session's transcript begins with the calls of the session it resumes, dated before its own start,
    so its first write is no start-up. --since reads a session's own start: the resume of a session from before it
    is still counted."""
    home.session("t/builder", sid(1), [(10_000, 10, [read("/run/a.md")]), (20_000, 10, [edit("/run/x.py")])])
    home.session("t/builder", sid(2), [(80_000, 10, [edit("/run/y.py")])], start="2026-10-23T10:30:00", resumes=sid(1))
    out = report(home)
    assert row(out, "t/builder") == ["1", "0", "1", "20,000", "20,000", "0"]
    assert over(out) == []
    home.session("t/critic", sid(3), [(10_000, 10, [edit("/x")])], start="2026-10-21T12:00:00")
    home.session("t/critic", sid(4), [(50_000, 10, [edit("/y")])], start="2026-10-22T09:00:00", resumes=sid(3))
    assert row(report(home, "--since", "2026-10-22"), "t/critic") == ["0", "0", "1", "-", "-", "0"]


def test_the_parsing_is_usage_reports(home):
    """The lines come from usage_report.lines(), so B1 and B2 hold here too: a '<synthetic>' line is no call, the
    lines of one call count once; and the parsing is imported, not copied."""
    home.session(
        "t/builder",
        sid(1),
        [SYNTHETIC, (10_000, 10, [THINK, read("/run/a.md"), TEXT]), (20_000, 10, [edit("/run/x.py")])],
    )
    [line] = over(report(home, "--threshold", "0"))
    assert line.startswith(f"- t/builder {sid(1)}: 20,000 at call 2 ")
    source = (SCRIPTS / "startup_report.py").read_text(encoding="utf-8")
    assert "import usage_report" in source and "json.loads" not in source and "glob" not in source
