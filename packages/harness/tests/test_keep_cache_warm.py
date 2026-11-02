"""The keep-cache-warm hook of a role's settings (owner, 2026-11-01): a foreground call past 210 s is refused, and a
turn end of a session whose record is not final continues it with a keep-alive, up to the break-even."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "keep-cache-warm.py"


def hook(args, data, env=None):
    return subprocess.run(
        [sys.executable, "-I", str(HOOK), *args],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=env,
    )


def bash(command, **fields):
    return {"tool_name": "Bash", "tool_input": {"command": command, **fields}}


@pytest.mark.parametrize(
    "data",
    [
        bash("uv run pytest -q", timeout=600000),
        bash("timeout -k 10 3500 sh scratch/waiter.sh"),
        bash("sleep 600 && cat verify.md"),
        bash("timeout 10m uv run pytest -q"),
        bash("for i in $(seq 1 16); do python3 -I _wait_for_log.py verify.md; done"),
        # V3 of the verifier: an option's value, a quote or a backtick before the word, a waiter in the loop's condition
        bash("timeout -s KILL 900 uv run pytest -q"),
        bash("timeout --signal KILL 900 uv run pytest -q"),
        bash("timeout -k 10 -s TERM 900 uv run pytest -q"),
        bash("timeout -v -k 5 900 uv run pytest -q"),  # an option with no value before one with a value
        bash("bash -c 'sleep 600'"),
        bash('sh -c "timeout 900 uv run pytest"'),
        bash("echo `sleep 600`"),
        bash("cat verify.md;sleep 600"),  # each character that may stand before the word, with no space between
        bash("cat verify.md&&sleep 600"),
        bash("cat verify.md|sleep 600"),
        bash("(sleep 600)"),
        bash("cat verify.md && sleep 600"),
        bash("until python3 -I _wait_for_log.py verify.md 3; do sleep 1; done"),
        bash("while true\ndo\n  python3 -I _wait_for_log.py verify.md 3\ndone"),
        # V3, second round: a quoted string that is shell (a `-c` body, an `eval` argument) is read as shell, and a
        # waiter in quotes is still the waiter
        bash("bash -c 'for i in 1 2 3; do python3 -I _wait_for_log.py verify.md 3; done'"),
        bash('sh -c "until python3 -I _wait_for_log.py verify.md 3; do :; done"'),
        bash('eval "sleep 600"'),
        bash("env X=1 /bin/bash -lc 'timeout 900 uv run pytest'"),
        bash('for i in 1 2 3; do python3 -I "$W/scripts/wait_for_log.py" verify.md 3; done'),
        bash('echo "starting a long wait"; sleep 600'),
        bash("bash --norc -x -c 'sleep 600'"),  # options before the -c
        # a `-c` body at the start of a command that is longer than the 80 characters looked back over is still shell
        bash("bash -c 'sleep 600'; echo " + "x" * 80),
        # an escaped quote outside a string opens no string, so the loop after it is not hidden by the quote after it
        bash("echo it\\'s; for i in 1 2; do python3 -I _wait_for_log.py verify.md 3; done; echo 'x'"),
        # V23 of the verifier: a `$(…)` or backtick pair inside double quotes is shell, so the quotes hide nothing in it
        bash('out="$(timeout 900 uv run pytest -q 2>&1)"; echo "$out" | tail -n 3'),
        bash('echo "result: $(timeout -k 10 900 uv run pytest -q | tail -n 1)"'),
        bash('x="$(sleep 600)"'),
        bash('echo "`sleep 600`"'),
        bash('out="$(for i in 1 2 3; do python3 -I wait_for_log.py build-log.md 3; done)"'),
        bash('echo "$(while true; do python3 -I wait_for_ready.py --once 3; done)"'),
        bash("x=$(timeout 900 uv run pytest -q)"),  # the same without quotes
        # the pair ends at its own closing bracket, past a nested pair, an escaped bracket and a bracket in a string
        bash('x="$(echo $(date -u) && sleep 600)"'),
        bash('x="$(echo \\) && sleep 600)"'),
        bash('x="$(echo "a)" && sleep 600)"'),
        bash("x=\"$(echo 'a)' && sleep 600)\""),
        bash('echo "$(echo "$(sleep 600)")"'),
        bash('x="$( (echo a) && sleep 600)"'),  # plain brackets inside the pair are counted
        bash('x="$("$W/run.sh" && sleep 600)"'),  # a pair that starts with a quoted word
        bash("echo \"`'a)' && sleep 600`\""),
        bash("echo \"$(bash -c 'sleep 600')\""),  # a `-c` body inside a pair is shell as anywhere
        bash('echo `echo "$(sleep 600)"`'),  # a pair in quotes in a backtick pair
        # a heredoc inside a pair ends at its delimiter line: what follows it in the pair is shell; `<<<` opens no
        # heredoc; after `<<-` the delimiter's line may start with tabs; outside a pair the body is shell, since a
        # script fed to `bash <<EOF` runs
        bash("x=\"$(cat <<'EOF'\nnotes\nEOF\nsleep 600\n)\""),
        bash("x=\"$(cat <<'A' <<'B'\nfirst\nA\nsecond\nB\nsleep 600\n)\""),
        bash("x=\"$(cat <<-'EOF'\n\tnotes\n\tEOF\nsleep 600\n)\""),
        bash('x="$(cat <<< "EOF"\nsleep 600\nEOF\n)"'),
        bash("bash <<'EOF'\nsleep 600\nEOF"),
        # a quote or a pair that never closes is ordinary text, so the wait after it is still seen
        bash('echo "a string that never closes; sleep 600'),
        bash('echo "$(date; sleep 600'),
    ],
)
def test_a_foreground_call_that_may_hold_the_turn_past_210_s_is_refused(data):
    r = hook(["pretool"], data)
    assert r.returncode == 2 and "210 s" in r.stderr and "run_in_background" in r.stderr


@pytest.mark.parametrize(
    "data",
    [
        bash("uv run pytest -q", timeout=200000),
        bash("timeout 200 uv run pytest -q"),
        bash("sleep 30"),
        bash("python3 -I _wait_for_log.py verify.md"),
        bash("for f in a b; do cat $f; done"),
        bash("timeout -k 10 3500 sh scratch/waiter.sh", run_in_background=True),
        {"tool_name": "Read", "tool_input": {"file_path": "x"}},
        # V3 of the verifier: the word "for" in prose is no loop; a short timeout or sleep behind an option or a quote
        bash("echo waiting for it; python3 -I _wait_for_log.py build-log.md 3"),
        bash("until grep -q done verify.md; do sleep 30; done"),
        bash("timeout -s KILL 200 uv run pytest -q"),
        bash("bash -c 'sleep 30'"),
        # V3, second round: the text of a quoted string is data (a commit message, an echo), not shell
        bash(
            'git commit -q -m "docs: Task 11 - the CHANGELOG names, for each step, of 2026-11-02 '
            '(wait_for_ready.py --index/--lane)" -m "Role-Session: x"'
        ),
        bash('git commit -q -m "docs: wait for it, do not poll wait_for_ready.py"'),
        bash("git commit -q -m 'docs: while the builder works, do not run wait_for_log.py in a loop'"),
        bash("git commit -q -m \"$(cat <<'EOF'\ndocs: wait for it, do not poll wait_for_ready.py\nEOF\n)\""),
        bash('echo "for each lane, do wait_for_ready.py"; git status'),
        bash('echo "say \\"wait for it, do wait_for_log.py\\" twice"'),
        bash('git commit -q -m "fix: the hook refuses sleep 600 and timeout 900"'),
        bash("bash -c 'git commit -m \"wait for it, do wait_for_log.py\"'"),
        # a quoted string deep in a `-c` body is data at its own place in the command, not at its place in the body
        bash("bash -c 'echo \"sleep 600\"'"),
        bash('sh -c \'echo "timeout 900"; echo "sleep 600"\''),
        bash('git commit -q -m "docs: wait for it, \\\ndo not poll wait_for_ready.py"'),  # a line continuation inside
        # the waiter stands before the loop, after a long quoted string: the places in the text still line up
        bash(
            'echo "a message long enough to shift every offset after it"; '
            "python3 -I _wait_for_log.py verify.md 3; for f in a b; do cat $f; done"
        ),
        # V23: the text around a `$(…)` pair in double quotes stays data, and so does a quoted string or a heredoc body
        # inside the pair
        bash(
            "git commit -q -m \"$(cat <<'EOF'\nfix: for each finding, do not poll; wait_for_ready.py reads the index\nEOF\n)\""
        ),
        bash("git commit -q -m \"$(cat <<'EOF'\ndocs: a message that names sleep 600 and timeout 900\nEOF\n)\""),
        bash('echo "done at $(date -u +%H:%M)"'),
        bash('echo "sleep 600 then $(date -u) then timeout 900"'),
        bash('echo "cost \\$(sleep 600) and \\`sleep 600\\`"'),  # escaped: no pair
        bash("echo '$(sleep 600) `sleep 600`'"),  # single quotes: no pair
        bash('echo "$(echo "a)" "sleep 600")"'),
        bash("echo \"$(echo 'a)' 'sleep 600')\""),
        bash('echo "$(git log -1 --format="for each, do wait_for_ready.py")"'),
        bash("x=$(git log -1 --format='for each, do wait_for_ready.py')"),  # a pair outside quotes
        # the forms of a heredoc: its delimiter bare, in double quotes, with a dash and a tab; a body that holds
        # brackets, quotes, a backtick and a sleep; a line that only starts like the delimiter; two heredocs on a line
        bash('git commit -q -m "$(cat <<EOF\nfix: for each, do wait_for_ready.py\nEOF\n)"'),
        bash('git commit -q -m "$(cat <<"EOF"\nfix: sleep 600\nEOF\n)"'),
        bash("git commit -q -m \"$(cat <<-'EOF'\n\tfix: sleep 600\n\tEOF\n)\""),
        bash('git commit -q -m "$(cat <<\'EOF\'\nfix: (partial, it\'s "x" `tick`\nsleep 600\nEOF\n)"'),
        bash("git commit -q -m \"$(cat <<'EOF'\nEOFS\nthe line ends with EOF\nsleep 600\nEOF\n)\""),
        bash("git commit -q -m \"$(cat <<'EOF'\n\tEOF\nsleep 600\nEOF\n)\""),  # tabs end only a `<<-` heredoc
        bash("git commit -q -m \"$(cat << 'EOF'\nfix: sleep 600\nEOF\n)\""),  # a space after the operator
        bash("x=\"$(cat <<'A' <<'B'\nfirst\nA\nsleep 600\nB\n)\""),
        bash("x=$(cat <<'EOF'\nfor each, do wait_for_ready.py\nEOF\n)"),  # a heredoc in a pair outside quotes
        bash("x=`cat <<'EOF'\nfor each, do wait_for_ready.py\nEOF\n`"),  # and in a backtick pair
        # a quote or a pair that never closes is ordinary text: the strings after it are still data
        bash('echo it\'s fine; git commit -q -m "docs: for each step, do wait_for_ready.py"'),
        bash('echo "price: $(" "for each, do wait_for_ready.py"'),
    ],
)
def test_a_short_call_a_background_call_or_another_tool_passes(data):
    r = hook(["pretool"], data)
    assert (r.returncode, r.stderr) == (0, "")


def test_a_turn_end_of_a_record_not_final_continues_the_session_with_a_keep_alive(tmp_path):
    record = tmp_path / "verify.md"
    record.write_text("STATUS: verifying Task 3\n", encoding="utf-8")
    env = {"TMPDIR": str(tmp_path), "PATH": "/usr/bin:/bin"}
    r = hook(["stop", str(record), "STATUS: done", "--wait", "0"], {"session_id": "s1"}, env)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["decision"] == "block" and out["reason"].startswith("Keep-alive for the prompt cache")


@pytest.mark.parametrize("line", ["STATUS: done", "STATUS: done after Task 4"])
def test_a_final_record_lets_the_turn_end(tmp_path, line):
    record = tmp_path / "verify.md"
    record.write_text(f"{line}\n", encoding="utf-8")
    env = {"TMPDIR": str(tmp_path), "PATH": "/usr/bin:/bin"}
    r = hook(["stop", str(record), "STATUS: done", "--wait", "0"], {"session_id": "s1"}, env)
    assert (r.returncode, r.stdout) == (0, "")


@pytest.mark.parametrize("content", [None, b"", b"\xff\xfeSTATUS: waiting\n"], ids=["missing", "empty", "undecodable"])
def test_a_missing_empty_or_undecodable_record_lets_the_turn_end(tmp_path, content):
    """V4 of the verifier: the missing-record branch had no case, so a session whose record does not exist yet would be
    held by keep-alives for up to 60 minutes at every turn end; an empty or undecodable record takes the same exit."""
    record = tmp_path / "verify.md"
    if content is not None:
        record.write_bytes(content)
    env = {"TMPDIR": str(tmp_path), "PATH": "/usr/bin:/bin"}
    r = hook(["stop", str(record), "STATUS: done", "--wait", "0"], {"session_id": "s1"}, env)
    assert (r.returncode, r.stdout) == (0, "")


def test_the_keep_alive_stops_at_the_break_even_counted_from_the_first_turn_end(tmp_path):
    record = tmp_path / "verify.md"
    record.write_text("STATUS: waiting\n", encoding="utf-8")
    env = {"TMPDIR": str(tmp_path), "PATH": "/usr/bin:/bin"}
    args = ["stop", str(record), "STATUS: done", "--wait", "0", "--max-minutes", "60"]
    assert json.loads(hook(args, {"session_id": "s2"}, env).stdout)["decision"] == "block"
    state = tmp_path / "specagent-keep-warm-s2.json"
    state.write_text(json.dumps({"start": 0}), encoding="utf-8")  # the stretch began long ago
    r = hook(args, {"session_id": "s2", "stop_hook_active": True}, env)
    assert (r.returncode, r.stdout) == (0, "") and not state.exists()
    fresh = hook(args, {"session_id": "s2", "stop_hook_active": False}, env)  # a new stretch starts again
    assert json.loads(fresh.stdout)["decision"] == "block"
