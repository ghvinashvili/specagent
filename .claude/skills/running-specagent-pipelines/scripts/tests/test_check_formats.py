"""Tests of check_formats.py on synthetic run folders.

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider scripts/tests
"""

import ast
import datetime
import json
import os
import pathlib
import subprocess
import sys
import textwrap
import time

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "check_formats.py"
GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


@pytest.fixture
def run(tmp_path):
    path = tmp_path / "run"
    path.mkdir()
    return path


def write(run: pathlib.Path, name: str, text: str) -> None:
    (run / name).write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


def check(run: pathlib.Path, *extra: str) -> tuple[int, dict]:
    p = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(run), "--json", *extra],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert p.stderr == ""
    return p.returncode, json.loads(p.stdout)


def make_repo(path: pathlib.Path) -> tuple[str, str]:
    """A tiny repository with one commit; returns the commit's sha and its tree's sha."""
    subprocess.run(["git", "init", "-q", str(path)], check=True, env=GIT_ENV)
    (path / "a.txt").write_text("a\n")
    git = ["git", "-C", str(path), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(git + ["add", "a.txt"], check=True, env=GIT_ENV)
    subprocess.run(git + ["commit", "-q", "-m", "one"], check=True, env=GIT_ENV)
    sha = subprocess.run(
        git + ["rev-parse", "HEAD", "HEAD^{tree}"], check=True, env=GIT_ENV, capture_output=True, text=True
    ).stdout.split()
    return sha[0], sha[1]


def test_missing_status_line(run):
    write(run, "critique.md", "# Critique\n#### C1 — a finding\n")
    write(run, "verify.md", "STATUS: verified through Task 1\n")
    write(run, "judge.md", "\n")
    code, out = check(run)
    assert code == 1
    assert out["errors"] == ["critique.md: line 1 is not `STATUS: …`", "judge.md: line 1 is not `STATUS: …`"]


def test_heading_used_twice_counts_round_2_as_the_same_id(run):
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1
        ### Task 1
        #### V29 — the rule drops letters (minor, code)
        body
        #### V29, round 2 — the rule stops at its own list (minor, code)
        body
        #### V30 — another finding (minor, plan)
        """,
    )
    code, out = check(run)
    assert code == 1
    assert out["errors"] == ["verify.md:5: #### V29 twice"]
    assert out["open"] == {"V": ["V29", "V30"]}


def test_answer_line_for_an_undefined_id(run):
    write(run, "critique.md", "STATUS: reviewed through Task 1\n#### C1 — x\n#### A1 — y\n")
    write(run, "critique-response.md", "STATUS: writing Task 2\nC1: applied — x\nA1: applied\nC7: applied — a typo\n")
    write(run, "build-log.md", "STATUS: waiting for Task 2\nV3: fixed — 1234567\n")
    code, out = check(run)
    assert code == 1
    assert out["errors"] == [
        "critique-response.md: `C7:` answers an id no file defines",
        "build-log.md: `V3:` answers an id no file defines",
    ]
    assert out["open"] == {}


def test_builder_own_b_line_against_sent_to_planner(run):
    write(
        run,
        "build-log.md",
        """
        STATUS: building Task 2
        B1: fixed in the code — Task 1 Step 3's path was wrong
        B2: sent to planner — Task 1 Step 4 names a hook that does not exist
        - B3: sent to planner — Task 2 Step 1 (an earlier run writes its lines as list items)
        - B4: fixed — 1234567 — its own finding, fixed by itself
        """,
    )
    write(run, "build-log-kb.md", "STATUS: waiting for Task 3\nBK1: sent to planner — Task 2 Step 7\n")
    write(run, "critique-response.md", "STATUS: writing Task 2\n")
    code, out = check(run)
    assert code == 0, out["errors"]
    assert out["open"] == {"B": ["B2", "B3"], "BK": ["BK1"]}
    write(run, "critique-response.md", "STATUS: writing Task 2\nB2: applied — the hook\nB3: applied\nBK1: applied\n")
    code, out = check(run)
    assert code == 0, out["errors"]
    assert out["open"] == {}


def test_a_sent_to_planner_quote_inside_a_line_opens_nothing(run):
    write(
        run,
        "build-log.md",
        """
        STATUS: building Task 3
        Task 1's test text `- B3: sent to planner` (an earlier run's form) is quoted inside a line.
        B3: fixed in 1234567 — its own finding, fixed by itself
        - B4: sent to planner — Task 3 Step 2 (a list item still sends)
        """,
    )
    write(run, "critique-response.md", "STATUS: writing Task 3\n")
    code, out = check(run)
    assert code == 0, out["errors"]
    assert out["open"] == {"B": ["B4"]}


def test_verifier_section_without_a_cause(run):
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1
        ## Task 1
        #### V1 — no cause at all
        Severity: minor.
        #### V2 — the cause in the heading (minor, plan)
        #### V3 — the cause on its own line
        Severity: major. Cause: (code): the loop stops early.
        #### V4 — only prose in parentheses
        Severity: minor (the code at foo.py:12 and the plan's step 3).
        #### V5 — the waiter's form without the colon
        Cause (spec): the spec says so.
        #### V6 — a nested form (minor, (plan))
        #### V2, round 2 — a reused id whose second section has no cause
        Severity: minor.
        #### VK1 — the KB side's verifier, no cause
        #### V7 — the cause, then the fix (major, code; fixed in d222541)
        #### V8 — the cause first (code, minor)
        """,
    )
    code, out = check(run)
    assert code == 1
    assert out["errors"] == [
        "verify.md:13: #### V2 twice",
        "verify.md:3: #### V1 has no (code), (plan), (spec) or (brief) cause",
        "verify.md:8: #### V4 has no (code), (plan), (spec) or (brief) cause",
        "verify.md:13: #### V2 has no (code), (plan), (spec) or (brief) cause",
        "verify.md:15: #### VK1 has no (code), (plan), (spec) or (brief) cause",
    ]


def test_a_verifier_section_may_name_brief_as_its_cause(run):
    """R8 (specs/003-pipeline-economy): a verifier without a planner tags `(brief)`. It counts in the forms the other
    causes do, a parenthesis of prose that holds the word does not, and a section with no cause still fails."""
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1
        ## Task 1
        #### V1 — the cause in the heading (brief)
        #### V2 — with a severity (minor, brief)
        #### V3 — the cause on its own line
        Severity: major. Cause: (brief): the assignment contradicts the spec.
        #### V4 — the cause, then the fix (major, brief; fixed in d222541)
        #### V5 — the waiter's form without the colon
        Cause (brief): the brief says so.
        #### V6 — only prose in parentheses
        Severity: minor (the brief at assignment.md:12 and the spec's step 3).
        #### V7 — no cause at all
        Severity: minor.
        """,
    )
    code, out = check(run)
    assert code == 1
    assert out["errors"] == [
        "verify.md:10: #### V6 has no (code), (plan), (spec) or (brief) cause",
        "verify.md:12: #### V7 has no (code), (plan), (spec) or (brief) cause",
    ]


def test_done_line_whose_sha_is_not_a_commit(run, tmp_path):
    repo = tmp_path / "repo"
    sha, tree = make_repo(repo)
    write(
        run,
        "build-log.md",
        f"""
        STATUS: waiting for Task 5
        Task 1: done — {sha[:7]} — the first task
        - Task 2: done — {sha} — an earlier run writes it as a list item
        Task 3: done — deadbee — no such object
        Task 4: done — {tree} — a tree, not a commit
        Task 5: steps 1-6 committed, NOT done — {sha[:7]}
        """,
    )
    code, out = check(run, "--repo", str(repo))
    assert code == 1
    assert out["errors"] == [
        f"build-log.md: Task 3: done — deadbee is not a commit of {repo}",
        f"build-log.md: Task 4: done — {tree} is not a commit of {repo}",
    ]
    assert out["done"] == [f"1:{sha[:7]}", f"2:{sha[:7]}", "3:deadbee", f"4:{tree[:7]}"]
    # Without --repo the builder's cwd comes from _agents.json (another role's cwd is not used).
    (run / "_agents.json").write_text(
        json.dumps({"agents": {"x/critic": {"cwd": "/nonexistent"}, "x/builder": {"cwd": str(repo)}}})
    )
    code, again = check(run)
    assert (code, again["errors"]) == (1, out["errors"])


def test_bad_handoff_line_one(run):
    notes = {
        "builder": "HANDOFF builder after Task 3 — 2026-10-26 06:04",
        "verifier": "HANDOFF verifier after Task 22 Step 17 part 3 G3 — 2026-10-24 06:34",
        "critic": "# Hand-over of the critic",
        "planner": "HANDOFF planner after Task 3",
        "judge": "HANDOFF judge after Task N — 2026-10-26 06:04",
        "plan-fixer": "HANDOFF planner after Task 3 — 2026-10-26 06:04",
        "builder-kb": "HANDOFF builder-kb after Task 4 — 2026-10-26 25:04",
        "sources": "",
    }
    for role, line in notes.items():
        write(run, f"handoff-{role}.md", line + "\nState: …\n" if line else "")
    code, out = check(run)
    assert code == 1
    assert sorted(e.split(":")[0] for e in out["errors"]) == [
        "handoff-builder-kb.md",
        "handoff-critic.md",
        "handoff-judge.md",
        "handoff-plan-fixer.md",
        "handoff-planner.md",
        "handoff-sources.md",
    ]


def test_list_item_answers_in_the_build_log(run):
    write(run, "verify.md", "STATUS: verified through Task 1\n#### V12 — x (minor, code)\n#### V13 — y (minor, code)\n")
    write(run, "lessons.md", "# Lessons\n## Read first\n1. O1: the owner's finding after the build.\n")
    write(
        run,
        "build-log.md",
        """
        STATUS: waiting for Task 2
        - V12: fixed — 565de4d (an earlier run writes its answers as list items)
        V13: fixed — 565de4d
        - O1: fixed — 565de4d
        """,
    )
    code, out = check(run)
    assert code == 0, out["errors"]
    assert out["open"] == {}


def test_list_item_answer_in_the_response_file_is_an_error(run):
    write(run, "critique.md", "STATUS: reviewed through Task 1\n#### C1 — x\n#### A1 — y\n")
    write(run, "critique-response.md", "STATUS: writing Task 2\n- C1: applied\nA1: applied\n")
    code, out = check(run)
    assert code == 1
    assert out["errors"] == ["critique-response.md:2: `- C1:` is a list item; the waiters read `C1:` at line start"]
    assert out["open"] == {"C": ["C1"]}


def test_json_and_text_output(run):
    write(run, "critique.md", "STATUS: reviewed through Task 1\n#### C1 — x\n")
    code, out = check(run)
    assert code == 0
    assert set(out) == {"open", "done", "errors"}
    assert out == {"open": {"C": ["C1"]}, "done": [], "errors": []}
    p = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(run)], capture_output=True, text=True, timeout=30, check=False
    )
    assert (p.returncode, p.stdout) == (0, "open: {'C': 1} | done tasks: 0 | errors: 0\n")
    write(run, "verify.md", "verified\n")
    p = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(run)], capture_output=True, text=True, timeout=30, check=False
    )
    assert p.returncode == 1
    assert p.stdout.splitlines() == [
        "ERROR verify.md: line 1 is not `STATUS: …`",
        "open: {'C': 1} | done tasks: 0 | errors: 1",
    ]
    code, out = check(run)
    assert (code, out["errors"]) == (1, ["verify.md: line 1 is not `STATUS: …`"])


def empty_commit(repo: pathlib.Path, message: str) -> str:
    """A commit with no change on top of make_repo's; its message makes its sha differ from another repository's."""
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", message], check=True, env=GIT_ENV)
    return subprocess.run(
        git + ["rev-parse", "HEAD"], check=True, env=GIT_ENV, capture_output=True, text=True
    ).stdout.strip()


def test_sent_to_plan_fixer_opens_a_b_id_as_sent_to_planner_does(run):
    write(
        run,
        "build-log.md",
        """
        STATUS: building Task 4
        B1: sent to plan-fixer — Task 4 Step 2 names a flag the tool does not have
        - B2: sent to plan-fixer — Task 4 Step 5 (a list item still sends)
        Task 3's quoted text `B3: sent to plan-fixer` opens nothing.
        B3: fixed in 1234567 — its own finding, fixed by itself
        """,
    )
    write(run, "critique-response.md", "STATUS: writing Task 5\n")
    code, out = check(run)
    assert code == 0, out["errors"]
    assert out["open"] == {"B": ["B1", "B2"]}
    write(run, "critique-response.md", "STATUS: writing Task 5\nB1: applied — the flag\nB2: applied\n")
    code, out = check(run)
    assert (code, out["errors"], out["open"]) == (0, [], {})


def test_every_build_log_defines_b_ids_answers_findings_and_needs_a_status_line(run):
    write(
        run,
        "build-log-a.md",
        """
        STATUS: building Task 3
        B1: sent to plan-fixer — Task 3 Step 4's command has no Expected line
        """,
    )
    write(
        run,
        "build-log-b.md",
        """
        STATUS: waiting for Task 4
        B2: fixed in 89abcde — its own finding, fixed by itself
        - V3: fixed — 89abcde
        """,
    )
    write(run, "verify.md", "STATUS: verifying Task 2\n\n#### V3 — minor (code)\nA path.\n")
    write(run, "critique-response.md", "STATUS: writing Task 5\nB1: applied — the Expected line\n")
    code, out = check(run)
    assert (code, out["errors"], out["open"]) == (0, [], {})
    write(run, "build-log-b.md", "Task 4: started\n")
    code, out = check(run)
    assert (code, out["errors"]) == (1, ["build-log-b.md: line 1 is not `STATUS: …`"])


def test_a_done_line_is_checked_in_the_checkout_of_the_builder_whose_log_holds_it(run, tmp_path):
    repo_a, repo_b = tmp_path / "a", tmp_path / "b"
    make_repo(repo_a)
    make_repo(repo_b)
    sha_a, sha_b = empty_commit(repo_a, "task 1 of builder a"), empty_commit(repo_b, "task 2 of builder b")
    write(run, "build-log-a.md", f"STATUS: waiting for Task 3\nTask 1: done — {sha_a[:7]}\n")
    write(run, "build-log-b.md", f"STATUS: waiting for Task 4\nTask 2: done — {sha_b[:7]}\n")
    agents = {
        "x/builder-a": {"cwd": str(repo_a), "status": "build-log-a.md"},
        "x/builder-b": {"cwd": str(repo_b), "status": "build-log-b.md"},
    }
    (run / "_agents.json").write_text(json.dumps({"agents": agents}), encoding="utf-8")
    code, out = check(run)
    assert (code, out["errors"], out["done"]) == (0, [], [f"1:{sha_a[:7]}", f"2:{sha_b[:7]}"])
    agents["x/builder-a"]["cwd"] = str(repo_b)
    (run / "_agents.json").write_text(json.dumps({"agents": agents}), encoding="utf-8")
    code, out = check(run)
    assert (code, out["errors"]) == (1, [f"build-log-a.md: Task 1: done — {sha_a[:7]} is not a commit of {repo_b}"])


def iso(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def aged(run: pathlib.Path, name: str, text: str, minutes: float) -> None:
    """A record written `minutes` ago by its mtime."""
    write(run, name, text)
    t = time.time() - minutes * 60
    os.utime(run / name, (t, t))


def test_an_open_request_past_the_bound_that_common_md_names_fails(run):
    aged(run, "plan-log.md", "STATUS: writing Task 3\nSANDBOX: allow writes to /x\n", 12)
    code, out = check(run)
    assert (code, out["errors"], out["open"]) == (0, [], {"SANDBOX": ["plan-log.md:2"]})
    write(run, "_common.md", "# Common\nRequest-line bound: 10 minutes (the monitor wakes the manager)\n")
    code, out = check(run)
    assert (code, out["open"]) == (1, {"SANDBOX": ["plan-log.md:2"]})
    assert out["errors"] == ["plan-log.md:2: SANDBOX open 12 min, past the bound of 10 min"]


def test_an_answer_closes_the_oldest_open_request_of_its_kind_above_it(run):
    write(
        run,
        "fixer-log.md",
        """
        STATUS: fixing
        COPIED: before any request
        COPY-REQUEST: templates/vault/a.md from the main checkout
        COPY-REQUEST: templates/vault/b.md from the main checkout
        FF-REQUEST: feat/x 1234567 -> main 89abcde
        COPIED: templates/vault/a.md — 2026-10-29 20:10 UTC
        SUPPLIED: nothing was asked
        REFUSED: FF-REQUEST — the branch moved
        - REFUSED: later, maybe
        ACK 1a2b3c4d
        """,
    )
    code, out = check(run)
    assert (code, out["open"]) == (1, {"COPY-REQUEST": ["fixer-log.md:4"]})
    assert out["errors"] == [
        "fixer-log.md:2: COPIED: answers no open COPY-REQUEST line above it",
        "fixer-log.md:7: SUPPLIED: answers no open SANDBOX line above it",
        "fixer-log.md:9: REFUSED: names no request kind",
    ]


def test_the_monitor_s_first_sight_wins_over_the_file_s_mtime(run):
    aged(run, "judge.md", "STATUS: judging\nCHECKOUT-REQUEST: 1234567\n", 30)
    state = run / "_control" / "monitor.json"
    state.parent.mkdir()
    state.write_text(json.dumps({"requests": [{"id": "judge.md:CHECKOUT-REQUEST:1", "seen": iso(time.time() - 120)}]}))
    code, out = check(run)
    assert (code, out["errors"], out["open"]) == (0, [], {"CHECKOUT-REQUEST": ["judge.md:2"]})
    state.write_text(json.dumps({"requests": [{"id": "judge.md:CHECKOUT-REQUEST:1", "seen": iso(time.time() - 1200)}]}))
    code, out = check(run)
    assert (code, out["errors"]) == (1, ["judge.md:2: CHECKOUT-REQUEST open 20 min, past the bound of 15 min"])
    other = run / "other.json"
    other.write_text(json.dumps({"requests": []}))
    code, out = check(run, "--state", str(other))
    assert (code, out["errors"]) == (1, ["judge.md:2: CHECKOUT-REQUEST open 30 min, past the bound of 15 min"])


def test_merged_lines_need_a_hex_sha_that_the_merged_into_checkout_holds(run, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    sha_a, _ = make_repo(a)
    make_repo(b)
    only_b = empty_commit(b, "b only")
    (run / "_control").mkdir()
    (run / "_control" / "_agents.json").write_text(
        json.dumps(
            {
                "agents": {
                    "manager/builder-a": {"cwd": str(a), "status": "build-log-a.md"},
                    "manager/builder-b": {"cwd": str(b), "status": "build-log-b.md"},
                }
            }
        )
    )
    write(
        run,
        "lessons.md",
        f"""
        # Lessons
        - 20:14 UTC (main session): Merged: b->a at {sha_a} — b merged into a
        - 20:15 UTC (main session): Merged: b→a at {only_b[:7]} — the recorded arrow, not in a
        - a waiter matches `Merged: a+b at [0-9a-f]{{7,}}`, never a bare count of `Merged: a+b`
        - 20:16 UTC (main session): Merged: b->a at {only_b} — not in a
        - 20:17 UTC (main session): Merged: a+b before the last task
        - 20:18 UTC (main session): Merged: main->plan at {"f" * 40}
        """,
    )
    code, out = check(run)
    assert code == 1
    assert out["errors"] == [
        f"lessons.md:3: Merged: b→a at {only_b[:7]} is not an ancestor of HEAD in {a}",
        f"lessons.md:5: Merged: b->a at {only_b} is not an ancestor of HEAD in {a}",
        "lessons.md:6: a Merged: line without a hex sha",
        f"lessons.md:7: Merged: main->plan at {'f' * 40} is not a commit of {a} or {b}",
    ]


def test_a_four_lane_marker_holds_when_any_named_builder_s_head_has_the_sha(run, tmp_path):
    repos = {lane: tmp_path / lane for lane in "abcd"}
    for repo in repos.values():
        make_repo(repo)
    only_c = empty_commit(repos["c"], "c only")
    agents = {f"manager/builder-{k}": {"cwd": str(v), "status": f"build-log-{k}.md"} for k, v in repos.items()}
    (run / "_control").mkdir()
    (run / "_control" / "_agents.json").write_text(json.dumps({"agents": agents}))
    write(
        run,
        "lessons.md",
        f"""
        # Lessons
        - 21:40 UTC (main session): Merged: a+b+c+d at {only_c} — the four lanes, in c's checkout only
        - 21:41 UTC (main session): Merged: a+b+c+d at {"e" * 40} — in none of the four
        """,
    )
    code, out = check(run)
    assert code == 1
    places = " or ".join(str(repos[k]) for k in "abcd")
    assert out["errors"] == [f"lessons.md:3: Merged: a+b+c+d at {'e' * 40} is not an ancestor of HEAD in {places}"]


def test_a_waiter_that_counts_the_merged_marker_with_grep_c_fails(run):
    write(
        run,
        "_wait.sh",
        "until grep -c 'Merged: a+b' lessons.md; do sleep 60; done\ngrep -cE 'Merged: a\\+b at [0-9a-f]{7,}' l.md\n",
    )
    write(
        run,
        "_builder-a-assignment.md",
        """
        Wait with `grep -qE 'Merged: a\\+b at [0-9a-f]{7,}' lessons.md`, never with a bare `grep -c`.
        A waiter never runs `grep -c 'x'` on the `Merged: a+b` marker.
        Old form: `n=$(grep -c "Merged: a+b" lessons.md)`
        ```
        grep --count 'Merged: b->a' lessons.md
        ```
        """,
    )
    code, out = check(run)
    tail = "a waiter counts the Merged marker with grep -c; match the hex sha instead"
    assert (code, out["errors"]) == (
        1,
        [f"_builder-a-assignment.md:3: {tail}", f"_builder-a-assignment.md:5: {tail}", f"_wait.sh:1: {tail}"],
    )


def test_a_ticked_duty_needs_its_utc_time(run):
    (run / "_control").mkdir()
    (run / "_control" / "duties.md").write_text(
        "# Duty list\n- [x] 2026-10-29 20:01 UTC (lessons.md:2, 960ca4e) D1 Merged: b->a — x\n"
        "- [x] 19:54 UTC (by hand) D2 Merged: main->plan\n- [x] (by hand) D3 judge approval\n- [ ] D4 COPY-REQUEST point\n",
        encoding="utf-8",
    )
    code, out = check(run)
    assert (code, out["errors"]) == (1, ["_control/duties.md:4: D3 is ticked without a UTC time"])


def test_the_config_under_control_gives_each_build_log_its_checkout(run, tmp_path):
    sha, _ = make_repo(tmp_path / "a")
    (run / "_control").mkdir()
    (run / "_control" / "_agents.json").write_text(
        json.dumps({"agents": {"manager/builder-a": {"cwd": str(tmp_path / "a"), "status": "build-log-a.md"}}})
    )
    write(run, "build-log-a.md", f"STATUS: building Task 2\nTask 1: done — {sha}\nTask 2: done — {'e' * 40}\n")
    code, out = check(run)
    assert out["done"] == [f"1:{sha[:7]}", "2:eeeeeee"]
    assert (code, out["errors"]) == (
        1,
        [f"build-log-a.md: Task 2: done — {'e' * 40} is not a commit of {tmp_path / 'a'}"],
    )


def test_every_function_is_under_50_lines_but_ids():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    sizes = {f.name: f.end_lineno - f.lineno + 1 for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
    assert sizes["ids"] <= 67
    assert {name: n for name, n in sizes.items() if name != "ids" and n >= 50} == {}


def test_an_id_answered_twice_in_the_response_file_is_an_error(run):
    write(run, "critique.md", "STATUS: x\n## Task 1\n#### C1 — t\n")
    write(run, "critique-response.md", "STATUS: x\nC1: applied — a\nC1: applied — b\n")
    code, out = check(run)
    assert code == 1 and "critique-response.md:3: C1 answered twice" in out["errors"]


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


def test_the_module_docstring_states_the_repo_rule_of_a_lane_marker():
    """R13: the usage text at the top states J7's rule as merged_error's docstring and docs/check_formats.md do."""
    doc = " ".join(ast.get_docstring(ast.parse(SCRIPT.read_text(encoding="utf-8"))).split())
    assert "with `--repo`, a lane marker whose named checkouts are all gone needs a commit of `--repo`" in doc


def test_a_finding_s_lesson_must_name_a_line_of_an_existing_file(run):  # owner, 2026-11-02
    write(run, "lessons.md", "STATUS: open\n# Lessons\n- A test list is no task.\n")
    write(
        run,
        "verify.md",
        """
        STATUS: verified through Task 1
        ## Task 1
        #### V1 — (code) the rule broken again
        Lesson: lessons.md:3
        #### V2 — (code) a line past the file
        Lesson: lessons.md:30
        #### V3 — (code) a file that does not exist
        Lesson: nowhere.md:1
        """,
    )
    code, out = check(run)
    lessons = [e for e in out["errors"] if "names Lesson" in e]
    assert code == 1 and len(lessons) == 2, out["errors"]
    assert any("V2 names Lesson lessons.md:30" in e for e in lessons)
    assert any("V3 names Lesson nowhere.md:1" in e for e in lessons)
