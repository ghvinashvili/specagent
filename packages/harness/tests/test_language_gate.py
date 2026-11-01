"""The manager chat's language gate (owner, 2026-11-01): a reply is written in the user's language and script."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "language-gate.py"
WORD = "\u10d4\u10e1 \u10de\u10d0\u10e1\u10e3\u10ee\u10d8 "  # a Georgian phrase, escaped: the template holds no Georgian letter
GEORGIAN = WORD * 12
HELLO = "\u10d2\u10d0\u10db\u10d0\u10e0\u10ef\u10dd\u10d1\u10d0"
ENGLISH = "This reply is written in English, so the language rule sends it back when the user writes in Georgian."


def transcript(tmp_path, *turns):
    lines = [json.dumps({"type": kind, "message": {"content": text}}) for kind, text in turns]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def gate(path, env=None, active=False):
    data = {"transcript_path": str(path), "stop_hook_active": active}
    return subprocess.run(
        [sys.executable, "-I", str(HOOK)],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env={"PATH": "/usr/bin:/bin", **(env or {})},
    )


@pytest.mark.parametrize(("user", "reply", "blocked"), [
    (HELLO, ENGLISH, True),
    (HELLO, GEORGIAN, False),
    ("How are things going?", ENGLISH, False),
    ("How are things going?", GEORGIAN, True),
])  # fmt: skip
def test_a_reply_in_another_script_than_the_user_s_is_sent_back_once(tmp_path, user, reply, blocked):
    r = gate(transcript(tmp_path, ("user", user), ("assistant", [{"type": "text", "text": reply}])))
    assert r.returncode == 0 and bool(r.stdout) == blocked
    if blocked:
        assert json.loads(r.stdout)["decision"] == "block"


def test_a_peer_s_message_or_a_notification_is_not_the_user_s_language(tmp_path):
    path = transcript(
        tmp_path,
        ("user", HELLO),
        ("user", "<cross-session-message from=x>Please carry the page.</cross-session-message>"),
        ("assistant", [{"type": "text", "text": ENGLISH}]),
    )
    assert json.loads(gate(path).stdout)["decision"] == "block"


def test_a_transliterated_language_is_answered_in_the_script_the_chat_names(tmp_path):
    path = transcript(tmp_path, ("user", "kargi, gaaswore"), ("assistant", [{"type": "text", "text": ENGLISH}]))
    assert gate(path).stdout == ""
    assert json.loads(gate(path, {"LANGUAGE_GATE_SCRIPT": "Georgian"}).stdout)["decision"] == "block"


def test_code_a_short_reply_and_a_second_stop_pass(tmp_path):
    code = "```\n" + ENGLISH * 3 + "\n```\n" + GEORGIAN
    for reply, active in (("OK, done.", False), (code, False), (ENGLISH, True)):
        path = transcript(tmp_path, ("user", HELLO), ("assistant", [{"type": "text", "text": reply}]))
        assert gate(path, active=active).stdout == ""
