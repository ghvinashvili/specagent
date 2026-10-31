"""templates/vault/ops/check_pages.py (spec 006, R6): a global page is a lesson or an order, and neutral. The check
refuses a global page without a kind; a lesson without an existing proof page under context/, whatever its date;
an order without a review date; a quoted text of the owner (a quote with a Georgian letter, or one whose
words are mostly not English); a Georgian letter in a global page; a global page or a candidate over 4,000 bytes
(the owner's order of 2026-10-31; the manager's lessons page keeps the limit of its form, under 8,000 bytes); and it
names a candidate past its review date. One test per refusal, and the page that passes. The vault's own
ops/check_pages.py is this file, copied.

  python3 -m pytest -q -p no:cacheprovider ops/tests/test_check_pages.py
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "templates" / "vault" / "ops" / "check_pages.py"
LETTER = chr(0x10D0)  # a Georgian letter, built from its code point: the template holds no such letter
LOW = chr(0x201E)  # the opening mark of the owner's low-high quotes, closed by either curly double mark
CLOSES = (chr(0x201C), chr(0x201D))
WORDS = "salt\nthe\ndish\nlate\nsear\nseason\nafter\nwater\nout\ndrew\nthis\nis\nright\n"  # a tiny English word list
PROOF = "context/measurements/2026-10-31-salt.md"
LESSON = f"""---
title: Salt late
type: decision
scope: global
status: verified
updated: 2026-10-31
audience: [all]
sources: [context/owner-statements/2026-10-31.md]
decided: 2026-10-31
by: owner
why: early salt drew the water out in both trials
decision_status: decided
would_change_if: a tasting that finds no difference
kind: lesson
proof: [{PROOF}]
---
# Salt late

Rule: salt the dish late. Why: early salt drew the water out. How to apply: season after the sear.
"""
QUOTED = LESSON.count("\n") + 2  # the line of a quote appended after the lesson and one blank line
ORDER = LESSON.replace("kind: lesson\n", "kind: order\nreview: 2027-10-31\n").replace(f"proof: [{PROOF}]\n", "")
CANDIDATE = LESSON.replace("kind: lesson\n", "kind: lesson\nreview: 2026-12-01\n").replace(f"proof: [{PROOF}]\n", "")
CONCEPT = """---
title: Salt
type: concept
scope: global
status: verified
updated: 2026-10-31
audience: [all]
sources: [context/owner-statements/2026-10-31.md]
---
# Salt

{body}
"""


def vault(tmp_path: Path, page: str = LESSON) -> Path:
    """A small vault: one global page, its source and its proof under context/, and the INDEX line that lists it."""
    root = tmp_path / "notes"
    for rel, text in {
        "INDEX.md": "# Index\n- [salt-late](decisions/global/salt-late.md): late\n",
        "decisions/global/salt-late.md": page,
        "context/owner-statements/2026-10-31.md": "# 2026-10-31\n",
        PROOF: "# Salt, measured twice\n",
    }.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def check(root: Path, *args: str, words: str | None = WORDS) -> subprocess.CompletedProcess:
    """Run the template's check on a vault. `words` is the English word list the check reads (None: no list at all)."""
    env = {**os.environ, "CHECK_PAGES_WORDS": str(root.parent / "words.txt")}
    if words is not None:
        (root.parent / "words.txt").write_text(words, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def page(root: Path, text: str, name: str = "decisions/global/salt-late.md") -> None:
    (root / name).write_text(text, encoding="utf-8")


def refused(result: subprocess.CompletedProcess, *parts: str) -> None:
    assert result.returncode == 1, result.stdout
    for part in parts:
        assert part in result.stdout, (part, result.stdout)


def sized(text: str, size: int) -> str:
    """The page with plain English lines appended until it is exactly `size` bytes (ASCII: a byte a character)."""
    line = "Salt the dish late, and season after the sear.\n"
    need = size - len(text.encode("utf-8"))
    assert need >= 0, (size, need)
    whole, rest = divmod(need, len(line))
    return text + line * whole + "s" * rest


def test_a_lesson_with_its_proof_passes(tmp_path: Path):
    result = check(vault(tmp_path))
    assert result.returncode == 0 and "1 pages checked, 0 problems" in result.stdout, result.stdout


def test_a_global_page_without_a_kind_is_refused(tmp_path: Path):
    root = vault(tmp_path, LESSON.replace("kind: lesson\n", ""))
    refused(check(root), "decisions/global/salt-late.md: a global page names its kind")
    page(root, LESSON.replace("kind: lesson\n", "kind: rule\n"))
    refused(check(root), "kind `rule` is neither `lesson` nor `order`")


def test_a_lesson_without_an_existing_proof_page_is_refused_whatever_its_date(tmp_path: Path):
    root = vault(tmp_path, LESSON.replace(f"proof: [{PROOF}]\n", ""))
    refused(check(root), "a global decision names its proof")
    page(root, LESSON.replace(PROOF, "context/measurements/missing.md"))
    refused(check(root), "proof `context/measurements/missing.md` is not an existing page under context/")
    page(root, LESSON.replace(PROOF, "decisions/global/salt-late.md"))
    refused(check(root), "is not an existing page under context/")
    page(root, LESSON.replace(PROOF, "context/../INDEX.md"))
    refused(check(root), "is not an existing page under context/")
    for day in ("2026-10-30", "2026-10-15", "2025-01-01"):
        old = LESSON.replace("decided: 2026-10-31", f"decided: {day}").replace(f"proof: [{PROOF}]\n", "")
        page(root, old)
        refused(check(root), "a global decision names its proof")  # no date lets a lesson off its proof
    page(root, LESSON.replace("decided: 2026-10-31", "decided: 2026-10-15"))
    assert check(root).returncode == 0  # an older lesson with its proof passes


def test_an_order_decided_after_the_rule_needs_no_proof(tmp_path: Path):
    result = check(vault(tmp_path, ORDER))
    assert result.returncode == 0, result.stdout


def test_an_order_without_a_review_date_is_refused(tmp_path: Path):
    root = vault(tmp_path, ORDER.replace("review: 2027-10-31\n", ""))
    refused(check(root), "decisions/global/salt-late.md: an order carries `review: YYYY-MM-DD`")
    page(root, ORDER.replace("review: 2027-10-31", "review: next year"))
    refused(check(root), "an order carries `review: YYYY-MM-DD`")


def test_a_quote_with_a_georgian_letter_is_refused(tmp_path: Path):
    root = vault(tmp_path, LESSON + f'\nThe owner said "{LETTER}{LETTER} {LETTER}" that day.\n')
    refused(check(root), f"decisions/global/salt-late.md:{QUOTED}: quoted text of the owner")


def test_a_quote_of_mostly_non_english_words_is_refused_by_the_word_list(tmp_path: Path):
    quote = '\nThe owner said "gaaketet es ukve rogor salt" that day.\n'
    root = vault(tmp_path, LESSON + quote)
    refused(check(root), f"decisions/global/salt-late.md:{QUOTED}: quoted text of the owner")
    page(root, LESSON + '\nA test says "salt the dish late" on both days.\n')
    assert check(root).returncode == 0  # an English quote is not what the check can tell from a rule's own words
    page(root, LESSON + '\nRun "claude --bg" and "uv run" in a session.\n')
    assert check(root).returncode == 0  # short quotes and command names are not texts of the owner
    page(root, LESSON + "\n> gaaketet es ukve rogor salt\n")
    refused(check(root), "quoted text of the owner")  # a block quote is a quote too
    for close in CLOSES:  # the owner's low-high marks, closed by either curly mark
        page(root, LESSON + f"\nThe owner said {LOW}gaaketet es ukve rogor salt{close} that day.\n")
        refused(check(root), f"decisions/global/salt-late.md:{QUOTED}: quoted text of the owner")
    page(root, LESSON + f"\nA test says {LOW}salt the dish late{CLOSES[0]} on both days.\n")
    assert check(root).returncode == 0  # an English quote in the same marks is not told from a rule's own words
    page(root, LESSON + '\n```text\n"gaaketet es ukve rogor salt"\n```\nA command: `"gaaketet es ukve rogor"`.\n')
    assert check(root).returncode == 0  # code is not prose


def test_without_a_word_list_a_quote_in_latin_script_georgian_words_is_refused(tmp_path: Path):
    quote = '\nThe owner said "ara minda gaaketet" that day.\n'
    root = vault(tmp_path, LESSON + quote)
    refused(check(root, words=None), f"decisions/global/salt-late.md:{QUOTED}: quoted text of the owner")
    page(root, LESSON + f"\nThe owner said {LOW}ara minda gaaketet{CLOSES[0]} that day.\n")
    refused(check(root, words=None), f"decisions/global/salt-late.md:{QUOTED}: quoted text of the owner")
    page(root, LESSON + '\nA test says "salt the dish late" on both days.\n')
    assert check(root, words=None).returncode == 0


def test_a_georgian_letter_in_a_global_page_is_refused_but_not_in_context_or_in_another_page(tmp_path: Path):
    root = vault(tmp_path, LESSON + f"\nA word: {LETTER}{LETTER}.\n")
    result = check(root)
    refused(result, "decisions/global/salt-late.md: a letter of a refused script (Georgian)")
    assert "quoted text" not in result.stdout
    page(root, LESSON)
    (root / "context" / "owner-statements" / "2026-10-31.md").write_text(f"# {LETTER}\n", encoding="utf-8")
    (root / "concepts").mkdir()
    page(root, CONCEPT.format(body=f"A word: {LETTER}."), "concepts/salt.md")
    (root / "INDEX.md").write_text(
        "# Index\n- [salt-late](decisions/global/salt-late.md): late\n- [salt](concepts/salt.md): salt\n",
        encoding="utf-8",
    )
    result = check(root)
    assert result.returncode == 0, result.stdout  # the owner's words live in context/; a concept is not a global rule


def test_a_candidate_past_its_review_date_is_named(tmp_path: Path):
    root = vault(tmp_path)
    (root / "context" / "candidates").mkdir()
    page(root, CANDIDATE, "context/candidates/salt-early.md")
    assert check(root, "--today", "2026-11-30").returncode == 0  # waiting for its proof, not yet due
    refused(
        check(root, "--today", "2026-12-02"),
        "context/candidates/salt-early.md: candidate past its review date 2026-12-01",
    )
    page(root, CANDIDATE.replace("review: 2026-12-01\n", ""), "context/candidates/salt-early.md")
    refused(check(root, "--today", "2026-11-30"), "context/candidates/salt-early.md: a candidate carries `review:")


def test_a_lesson_over_4000_bytes_is_refused_and_one_of_4000_passes(tmp_path: Path):
    """Owner's order, 2026-10-31: a global page is at most 4,000 bytes. The limit is "over", so 4,000 passes."""
    root = vault(tmp_path, sized(LESSON, 4_000))
    assert check(root).returncode == 0
    page(root, sized(LESSON, 4_001))
    refused(check(root), "decisions/global/salt-late.md: 4,001 bytes", "at most 4,000 bytes")


def test_an_order_over_4000_bytes_is_refused(tmp_path: Path):
    root = vault(tmp_path, sized(ORDER, 4_001))
    refused(check(root), "decisions/global/salt-late.md: 4,001 bytes", "at most 4,000 bytes")
    page(root, sized(ORDER, 4_000))
    assert check(root).returncode == 0


def test_a_candidate_over_4000_bytes_is_refused(tmp_path: Path):
    root = vault(tmp_path)
    (root / "context" / "candidates").mkdir()
    page(root, sized(CANDIDATE, 4_001), "context/candidates/salt-early.md")
    refused(
        check(root, "--today", "2026-11-30"),
        "context/candidates/salt-early.md: 4,001 bytes",
        "at most 4,000 bytes",
    )
    page(root, sized(CANDIDATE, 4_000), "context/candidates/salt-early.md")
    assert check(root, "--today", "2026-11-30").returncode == 0


def test_the_size_is_counted_in_bytes_not_characters(tmp_path: Path):
    text = LESSON + ("caf" + chr(0xE9) + " ") * 600 + "\n"  # 600 words of 5 characters and 6 bytes
    size = len(text.encode("utf-8"))
    assert len(text) < 4_000 < size
    refused(check(vault(tmp_path, text)), f"decisions/global/salt-late.md: {size:,} bytes")


def test_a_page_outside_decisions_global_is_not_held_to_4000_bytes(tmp_path: Path):
    root = vault(tmp_path)
    (root / "concepts").mkdir()
    page(root, sized(CONCEPT.format(body="Salt."), 5_000), "concepts/salt.md")
    (root / "INDEX.md").write_text(
        "# Index\n- [salt-late](decisions/global/salt-late.md): late\n- [salt](concepts/salt.md): salt\n",
        encoding="utf-8",
    )
    result = check(root)
    assert result.returncode == 0, result.stdout  # the order names a global page and a candidate, not a concept


LESSONS = "decisions/global/manager-lessons.md"
FORM = SCRIPT.parents[1] / "forms" / "manager-lessons.md"  # the form that states the lessons page's own limit


def with_lessons(root: Path, size: int) -> None:
    """The manager's lessons page, `size` bytes, beside the vault's global page, and the INDEX line that lists it."""
    page(root, sized(LESSON, size), LESSONS)
    index = (
        "# Index\n- [salt-late](decisions/global/salt-late.md): late\n"
        "- [manager-lessons](decisions/global/manager-lessons.md): lessons\n"
    )
    (root / "INDEX.md").write_text(index, encoding="utf-8")


def test_the_managers_lessons_page_keeps_the_limit_of_its_form_not_4000(tmp_path: Path):
    """Owner's order e850a096: the lessons page is held to the number its form states ("stays under 8,000 bytes"),
    the same way the pipeline skill's measurement counts it: 7,999 bytes pass, 8,000 do not."""
    stated = re.search(r"stays under ([\d,]+) bytes", FORM.read_text(encoding="utf-8"))
    assert stated, "forms/manager-lessons.md no longer states the page's limit as `stays under N bytes`"
    limit = int(stated.group(1).replace(",", ""))
    root = vault(tmp_path)
    with_lessons(root, limit - 1)
    result = check(root)
    assert result.returncode == 0 and "2 pages checked, 0 problems" in result.stdout, result.stdout
    with_lessons(root, limit)
    refused(check(root), f"{LESSONS}: {limit:,} bytes", f"stays under {limit:,} bytes")


def test_only_the_lessons_page_is_exempt_another_global_page_and_a_candidate_of_its_name_stay_at_4000(tmp_path: Path):
    root = vault(tmp_path)
    with_lessons(root, 5_000)  # over 4,000 and under its own limit: passes
    page(root, sized(LESSON, 4_001))  # decisions/global/salt-late.md
    (root / "context" / "candidates").mkdir()
    page(root, sized(CANDIDATE, 4_001), "context/candidates/manager-lessons.md")  # the name alone does not exempt
    result = check(root, "--today", "2026-11-30")
    refused(
        result,
        "decisions/global/salt-late.md: 4,001 bytes",
        "context/candidates/manager-lessons.md: 4,001 bytes",
        "2 pages checked, 2 problems",
    )
    assert f"{LESSONS}:" not in result.stdout, result.stdout
