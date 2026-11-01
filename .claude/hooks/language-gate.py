#!/usr/bin/env python3
"""Stop hook of the manager chat: a reply to the user is written in the user's language (owner, 2026-11-01).

The rule (vault `manager-replies-in-the-users-language`): the manager chat answers in the language of the user's own
messages, whatever language its tools, logs and agents use; agents stay English. The hook compares the script of the
reply's letters (outside code blocks, inline code and links) with the script of the user's last message of their own
(not a tool result, a command, a notification or another session's message). A transliterated language is answered in
its own script: set `LANGUAGE_GATE_SCRIPT` (e.g. `Georgian`) in the environment of the chat, which then wins over the
detected script; without it a user message in Latin letters sends nothing back, since it may be a transliteration. A reply of under 60 letters, a user message with no letters and a second stop in a row
(`stop_hook_active`) pass, so the gate asks once and never loops.
"""

import json
import os
import re
import sys
from pathlib import Path

SCRIPTS = {
    "Latin": r"A-Za-z\u00c0-\u024f",
    "Georgian": r"\u10a0-\u10ff\u1c90-\u1cbf",
    "Cyrillic": r"\u0400-\u04ff",
    "Greek": r"\u0370-\u03ff",
    "Armenian": r"\u0530-\u058f",
    "Hebrew": r"\u0590-\u05ff",
    "Arabic": r"\u0600-\u06ff",
    "Devanagari": r"\u0900-\u097f",
    "CJK": r"\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af",
}
NOT_OWN = ("<", "[Request interrupted")  # tags of commands, notifications, reminders and peers' messages


def letters(text: str) -> dict[str, int]:
    """The letters of each script in `text`, code blocks, inline code and links left out."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"https?://\S+|\S+\.(?:com|org|md|py|json|html|txt|yaml)\b", " ", text)
    return {name: len(re.findall(f"[{chars}]", text)) for name, chars in SCRIPTS.items()}


def texts(content: object) -> str:
    """The text of a message's content: a string, or its text blocks joined."""
    if isinstance(content, str):
        return content
    blocks = content if isinstance(content, list) else []
    return "\n".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")


def last_turn(path: str) -> tuple[str, str]:
    """The user's last message of their own and the assistant's reply text after it."""
    user, reply = "", ""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return user, reply
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("isSidechain"):
            continue
        text = texts(d.get("message", {}).get("content"))
        if d.get("type") == "user" and not d.get("isMeta") and text.strip():
            if not text.lstrip().startswith(NOT_OWN):
                user, reply = text, ""
        elif d.get("type") == "assistant":
            reply += text + "\n"
    return user, reply


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if not isinstance(data, dict) or data.get("stop_hook_active"):
        return 0
    user, reply = last_turn(str(data.get("transcript_path", "")))
    wanted = os.environ.get("LANGUAGE_GATE_SCRIPT", "").strip()
    if wanted not in SCRIPTS:
        counts = letters(user)
        if not any(counts.values()):
            return 0
        wanted = max(counts, key=counts.get)
        if wanted == "Latin":
            return 0  # a Latin message may be a transliteration, answered in its own script: only the setting decides
    found = letters(reply)
    total = sum(found.values())
    if total < 60 or found[wanted] * 2 >= total:
        return 0
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    f"Language rule: the user writes in {wanted} script and your reply is mostly in another "
                    f"({found[wanted]} of {total} letters in {wanted}). Rewrite the whole reply in the user's "
                    "language and script; only code, commands, file names and proper names stay as they are. "
                    "Call no tools."
                ),
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
