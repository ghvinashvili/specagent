"""ops/sync-vault-globals.py (spec 006, R5): the template carries the global pages of a vault. The script copies into the
template's vault form (decisions/global/, the measurement pages they cite, and their INDEX lines) every page of the
vault's decisions/global/ that is `template: yes`, not withdrawn, and an order or a lesson with an existing proof page.
It edits two frontmatter lines, `sources:` and `proof:`, so that they name only what travels (a public URL, a neutral
measurement page of context/measurements/), and never the prose. It refuses a page that holds a Georgian letter, a model
name or an owner marker, or that the form's own check_pages.py refuses (a link to a page that does not travel, a size).
One test per refusal, and the page that passes.

  python3 -m pytest -q -p no:cacheprovider ops/tests/test_sync_vault_globals.py
"""

from __future__ import annotations

import functools
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FORM = REPO / "templates" / "vault"
SCRIPT = REPO / "ops" / "sync-vault-globals.py"
PREFLIGHT = REPO / ".claude" / "skills" / "running-specagent-pipelines" / "scripts" / "manager" / "preflight.py"
NEW_VAULT_TESTS = Path(__file__).with_name("test_new_vault.py")
LETTER = chr(0x10D0)  # a Georgian letter, built from its code point: the template and its tests hold no such letter
STATEMENT = "context/owner-statements/2026-10-31.md"
PROOF = "context/measurements/2026-10-31-salt.md"
MEMORY = "context/memory/kitchen/salt-late.md"
URL = "https://example.org/salt"
BODY = "Rule: salt the dish late. Why: early salt drew the water out. How to apply: season after the sear.\n"
WORDS = "salt\nthe\ndish\nlate\nsear\nseason\nafter\nwater\nout\ndrew\nthis\nis\nright\n"  # a tiny English word list
INDEX = """# Index

One line per page.

## Decisions (global)

## Concepts

## Entities

## Sources
"""


def load(name: str, path: Path):
    """A script of the repo as a module, by its path (the names with a hyphen cannot be imported)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FAMILIES = load("preflight_families", PREFLIGHT).MODELS


@functools.cache
def sync_module():
    """The script as a module: loaded where a test reads its constants, so that a missing script fails that test alone."""
    return load("sync_vault_globals", SCRIPT)


def render(
    title: str = "Salt late",
    kind: str = "order",
    template: str | None = "yes",
    status: str = "decided",
    sources: tuple[str, ...] = (STATEMENT,),
    proof: tuple[str, ...] | None = None,
    body: str = BODY,
) -> str:
    """One global page that passes the form's check: an order carries `review:`, a lesson its `proof:`."""
    fields = [
        ("title", title),
        ("type", "decision"),
        ("scope", "global"),
        ("kind", kind),
        ("template", template),
        ("status", "verified"),
        ("updated", "2026-10-31"),
        ("audience", "[all]"),
        ("sources", f"[{', '.join(sources)}]"),
        ("proof", None if proof is None else f"[{', '.join(proof)}]"),
        ("decided", "2026-10-31"),
        ("by", "owner"),
        ("review", "2027-10-31" if kind == "order" else None),
        ("why", "early salt drew the water out in both trials"),
        ("decision_status", status),
        ("would_change_if", "a tasting that finds no difference"),
    ]
    head = "".join(f"{key}: {value}\n" for key, value in fields if value is not None)
    return f"---\n{head}---\n# {title}\n\n{body}"


def make_vault(tmp_path: Path, pages: dict[str, str], extra: dict[str, str] | None = None) -> Path:
    """A small vault: the pages, an INDEX that lists them, the statement they cite and one neutral measurement page."""
    root = tmp_path / "vault"
    files = {
        "INDEX.md": "# Index\n" + "".join(f"- [{name}](decisions/global/{name}.md): a page\n" for name in pages),
        STATEMENT: "# 2026-10-31\n",
        PROOF: "# Salt, measured twice\n\nLate salt kept the water in.\n",
        **{f"decisions/global/{name}.md": text for name, text in pages.items()},
        **(extra or {}),
    }
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def copy_form(tmp_path: Path) -> Path:
    """A copy of the template's vault form with no global page and the INDEX of the empty form: the script owns both."""
    form = tmp_path / "form"
    shutil.copytree(FORM, form, ignore=shutil.ignore_patterns("__pycache__"))
    for folder in ("decisions/global", "context/measurements"):
        for old in (form / folder).glob("*.md"):
            old.unlink()
    (form / "INDEX.md").write_text(INDEX, encoding="utf-8")
    return form


def env_of(tmp_path: Path) -> dict[str, str]:
    (tmp_path / "words.txt").write_text(WORDS, encoding="utf-8")
    return {**os.environ, "CHECK_PAGES_WORDS": str(tmp_path / "words.txt")}


def sync(vault: Path, form: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), "--vault", str(vault), "--template", str(form), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env_of(vault.parent),
        timeout=120,
        check=False,
    )


def check(root: Path) -> subprocess.CompletedProcess:
    """The form's own check on a vault or on the form."""
    return subprocess.run(
        [sys.executable, "-B", str(FORM / "ops" / "check_pages.py"), str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env_of(root.parent),
        timeout=120,
        check=False,
    )


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def last(done: subprocess.CompletedProcess) -> str:
    return done.stdout.splitlines()[-1]


def refused_alone(tmp_path: Path, text: str, name: str = "salt-late", extra: dict[str, str] | None = None):
    """Sync one page that must be refused: its reason, the form without it, an INDEX that lists nothing."""
    vault, form = make_vault(tmp_path, {name: text}, extra), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 1, done.stdout + done.stderr
    assert last(done) == "0 carried, 1 refused, 0 skipped", done.stdout
    assert not (form / "decisions" / "global" / f"{name}.md").exists()
    assert (form / "INDEX.md").read_text(encoding="utf-8") == INDEX
    assert not list((form / "context" / "measurements").glob("*.md"))
    return next(line for line in done.stdout.splitlines() if line.startswith(f"refused {name}: "))


def test_the_fixture_vault_passes_the_forms_own_check(tmp_path: Path):
    vault = make_vault(tmp_path, {"salt-late": render(sources=(STATEMENT, URL)), "pepper": render(title="Pepper")})
    done = check(vault)
    assert done.returncode == 0 and "2 pages checked, 0 problems" in done.stdout, done.stdout


def test_a_carried_order_equals_the_vaults_page_except_its_sources_and_proof_lines(tmp_path: Path):
    text = render(sources=(STATEMENT, MEMORY, URL), proof=(MEMORY,))
    vault, form = make_vault(tmp_path, {"salt-late": text}, {MEMORY: "# a note\n"}), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "carried salt-late" in done.stdout.splitlines() and last(done) == "1 carried, 0 refused, 0 skipped"
    want = text.replace(f"sources: [{STATEMENT}, {MEMORY}, {URL}]", f"sources: [{URL}]")
    want = want.replace(f"proof: [{MEMORY}]\n", "")
    assert (form / "decisions" / "global" / "salt-late.md").read_bytes() == want.encode("utf-8")
    assert want.count("\n") == text.count("\n") - 1  # the sources line stays, the proof line goes: only those two lines
    index = (form / "INDEX.md").read_text(encoding="utf-8")
    assert index == INDEX.replace(
        "## Decisions (global)\n\n",
        "## Decisions (global)\n\n- [salt-late](decisions/global/salt-late.md): Salt late\n\n",
    )


def test_a_sources_line_with_nothing_that_travels_becomes_an_empty_list(tmp_path: Path):
    vault, form = make_vault(tmp_path, {"salt-late": render()}), copy_form(tmp_path)
    assert sync(vault, form).returncode == 0
    copy = (form / "decisions" / "global" / "salt-late.md").read_text(encoding="utf-8")
    assert "\nsources: []\n" in copy and STATEMENT not in copy


def test_a_page_with_no_template_line_or_template_no_or_withdrawn_is_skipped_and_counted(tmp_path: Path):
    pages = {
        "personal": render(template="no"),
        "unmarked": render(template=None),
        "retired": render(status="withdrawn"),
        "kept": render(),
    }
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 0, done.stdout + done.stderr
    assert last(done) == "1 carried, 0 refused, 3 skipped"
    for name in ("personal", "unmarked", "retired"):
        assert f"skipped {name}: " in done.stdout
    assert sorted(p.name for p in (form / "decisions" / "global").glob("*.md")) == ["kept.md"]


def test_a_template_yes_page_that_is_no_order_and_no_lesson_with_a_proof_is_skipped(tmp_path: Path):
    pages = {"no-kind": render(kind="note"), "no-proof": render(kind="lesson", proof=("context/memory/gone.md",))}
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 0 and last(done) == "0 carried, 0 refused, 2 skipped", done.stdout


def test_a_lesson_with_a_neutral_measurement_proof_carries_the_proof_page(tmp_path: Path):
    text = render(kind="lesson", sources=(STATEMENT, PROOF, MEMORY), proof=(PROOF, MEMORY))
    vault, form = make_vault(tmp_path, {"salt-late": text}, {MEMORY: "# a note\n"}), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 0, done.stdout + done.stderr
    copy = (form / "decisions" / "global" / "salt-late.md").read_text(encoding="utf-8")
    assert f"\nsources: [{PROOF}]\n" in copy and f"\nproof: [{PROOF}]\n" in copy and MEMORY not in copy
    assert (form / PROOF).read_bytes() == (vault / PROOF).read_bytes()
    assert not (form / MEMORY).exists()
    assert check(form).returncode == 0


def test_a_lesson_whose_only_proof_is_a_memory_note_is_refused(tmp_path: Path):
    text = render(kind="lesson", sources=(STATEMENT, MEMORY), proof=(MEMORY,))
    reason = refused_alone(tmp_path, text, extra={MEMORY: "# a note\n"})
    assert "proof" in reason and "context/measurements/" in reason, reason


NEUTRAL_BAD = [
    pytest.param(f"# Salt {LETTER}\n", id="a-georgian-letter"),
    pytest.param(f"# Salt, per the {FAMILIES[1]} run\n", id="a-model-name"),
    pytest.param("# Salt, measured on the trading desk\n", id="an-owner-project-word"),
    pytest.param("# Salt, mail someone@example.org\n", id="an-e-mail"),
    pytest.param("# Salt, kept in /home/someone/notes\n", id="a-path-under-home"),
    pytest.param("# Salt\n\napi_key = " + "x" * 12 + "\n", id="a-secret-pattern"),
]


@pytest.mark.parametrize("measurement", NEUTRAL_BAD)
def test_a_proof_page_that_holds_what_the_template_refuses_does_not_travel_and_its_lesson_is_refused(
    tmp_path: Path, measurement: str
):
    text = render(kind="lesson", sources=(STATEMENT, PROOF), proof=(PROOF,))
    reason = refused_alone(tmp_path, text, extra={PROOF: measurement})
    assert "proof" in reason, reason


PAGE_BAD = [
    pytest.param(f"Salt {LETTER} late.", "Georgian", id="a-georgian-letter"),
    pytest.param(f"Salt late, as the {FAMILIES[0]} one says.", "model name", id="model-family-1"),
    pytest.param(f"Salt late, as the {FAMILIES[1].upper()} one says.", "model name", id="model-family-2-in-capitals"),
    pytest.param(f"Salt late, as the {FAMILIES[2]} one says.", "model name", id="model-family-3"),
    pytest.param(f"Salt late, as the {FAMILIES[3]} one says.", "model name", id="model-family-4"),
    pytest.param("Salt late, as seen on the trading desk.", "owner marker", id="an-owner-project-word"),
    pytest.param("Salt late; write to someone@example.org.", "owner marker", id="an-e-mail"),
    pytest.param("Salt late; the notes are in /home/someone/notes.", "owner marker", id="a-path-under-home"),
    pytest.param("Salt late; the account is ghvinashvili.", "owner marker", id="the-owners-account"),
    pytest.param("Salt late; api_key = " + "x" * 12, "secret pattern", id="a-secret-pattern"),
]


@pytest.mark.parametrize(("sentence", "why"), PAGE_BAD)
def test_a_page_that_holds_what_the_template_refuses_is_refused_and_not_written(
    tmp_path: Path, sentence: str, why: str
):
    reason = refused_alone(tmp_path, render(body=BODY + sentence + "\n"))
    assert why in reason, reason
    assert LETTER not in reason  # the report never repeats the letter it refuses


def test_the_slug_of_a_page_is_scanned_too(tmp_path: Path):
    reason = refused_alone(tmp_path, render(), name="brooks-salt")
    assert "slug" in reason and "owner marker" in reason, reason


def test_an_owner_marker_or_a_model_name_in_the_sources_line_alone_does_not_refuse_a_page(tmp_path: Path):
    notes = ("context/memory/gexhex/salt-late.md", f"context/memory/{FAMILIES[2]}-notes.md")
    extra = {note: "# a note\n" for note in notes}
    vault, form = make_vault(tmp_path, {"salt-late": render(sources=(STATEMENT, *notes))}, extra), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 0 and last(done) == "1 carried, 0 refused, 0 skipped", done.stdout
    copy = (form / "decisions" / "global" / "salt-late.md").read_text(encoding="utf-8")
    assert "\nsources: []\n" in copy and "gexhex" not in copy and FAMILIES[2] not in copy


def test_the_launch_flag_model_is_a_flag_and_not_a_model_name(tmp_path: Path):
    vault, form = (
        make_vault(tmp_path, {"flags": render(body=BODY + "Launch with `claude -p --model <model>`.\n")}),
        copy_form(tmp_path),
    )
    done = sync(vault, form)
    assert done.returncode == 0 and last(done) == "1 carried, 0 refused, 0 skipped", done.stdout


def test_a_link_to_a_page_that_does_not_travel_is_refused_with_the_checks_text_and_no_link_is_rewritten(tmp_path: Path):
    pages = {"salt-late": render(body=BODY + "See [[pepper-early]].\n"), "pepper-early": render(template="no")}
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 1 and last(done) == "0 carried, 1 refused, 1 skipped", done.stdout
    assert "refused salt-late: link [[pepper-early]] does not resolve" in done.stdout
    assert not (form / "decisions" / "global" / "salt-late.md").exists()


def test_the_same_link_is_carried_once_its_target_travels_too(tmp_path: Path):
    pages = {"salt-late": render(body=BODY + "See [[pepper-early]].\n"), "pepper-early": render(title="Pepper")}
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 0 and last(done) == "2 carried, 0 refused, 0 skipped", done.stdout
    assert "[[pepper-early]]" in (form / "decisions" / "global" / "salt-late.md").read_text(encoding="utf-8")


def test_a_refused_page_takes_the_pages_that_link_it_and_the_proof_pages_only_it_cited(tmp_path: Path):
    pages = {
        "salt-late": render(kind="lesson", sources=(PROOF,), proof=(PROOF,), body=BODY + "See [[pepper]].\n"),
        "pepper": render(title="Pepper", body=BODY + f"Salt {LETTER}.\n"),
    }
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 1 and last(done) == "0 carried, 2 refused, 0 skipped", done.stdout
    assert "refused pepper: " in done.stdout
    assert "refused salt-late: link [[pepper]] does not resolve" in done.stdout
    assert not list((form / "context" / "measurements").glob("*.md"))  # its proof page stays behind with it
    assert (form / "INDEX.md").read_text(encoding="utf-8") == INDEX


def test_a_page_over_4000_bytes_is_refused_with_the_checks_text(tmp_path: Path):
    reason = refused_alone(tmp_path, render(body=BODY + "Salt the dish late, and season after the sear.\n" * 100))
    assert "at most 4,000 bytes" in reason, reason


def test_pages_are_carried_in_name_order_with_one_index_line_each_and_the_form_passes_its_own_check(tmp_path: Path):
    pages = {"b-pepper": render(title="Pepper"), "a-salt": render(title="Salt"), "c-lime": render(title="Lime")}
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 0 and last(done) == "3 carried, 0 refused, 0 skipped", done.stdout
    index = (form / "INDEX.md").read_text(encoding="utf-8").splitlines()
    start = index.index("## Decisions (global)") + 2
    assert index[start : start + 3] == [
        "- [a-salt](decisions/global/a-salt.md): Salt",
        "- [b-pepper](decisions/global/b-pepper.md): Pepper",
        "- [c-lime](decisions/global/c-lime.md): Lime",
    ]
    assert index[start + 3 : start + 5] == ["", "## Concepts"]
    done = check(form)
    assert done.returncode == 0 and "3 pages checked, 0 problems" in done.stdout, done.stdout


def test_an_index_hook_drops_the_yaml_quotes_of_a_quoted_title(tmp_path: Path):
    """V10: two pages of the vault carry `title: "…: …"` (a colon needs the quotes in YAML); the hook is the title."""
    pages = {
        "salt-late": render(title='"Salt: late"'),
        "pepper": render(title="'Pepper'"),
        "lime": render(title="Lime"),
    }
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 0 and last(done) == "3 carried, 0 refused, 0 skipped", done.stdout
    index = (form / "INDEX.md").read_text(encoding="utf-8")
    assert "- [salt-late](decisions/global/salt-late.md): Salt: late\n" in index
    assert "- [pepper](decisions/global/pepper.md): Pepper\n" in index
    assert '): "' not in index and "): '" not in index


def test_an_empty_selection_leaves_the_forms_index_byte_for_byte(tmp_path: Path):
    vault, form = make_vault(tmp_path, {"personal": render(template="no")}), copy_form(tmp_path)
    before = snapshot(form)
    done = sync(vault, form)
    assert done.returncode == 0 and last(done) == "0 carried, 0 refused, 1 skipped", done.stdout
    assert snapshot(form) == before


def test_a_rerun_removes_a_stale_copy_and_a_second_run_changes_no_byte(tmp_path: Path):
    text = render(kind="lesson", sources=(STATEMENT, PROOF), proof=(PROOF,))
    vault, form = make_vault(tmp_path, {"salt-late": text}), copy_form(tmp_path)
    (form / "decisions" / "global" / "stale.md").write_text("# stale\n", encoding="utf-8")
    (form / "context" / "measurements" / "stale.md").write_text("# stale\n", encoding="utf-8")
    assert sync(vault, form).returncode == 0
    assert not (form / "decisions" / "global" / "stale.md").exists()
    assert not (form / "context" / "measurements" / "stale.md").exists()
    assert (form / "decisions" / "global" / ".gitkeep").exists() and (
        form / "context" / "measurements" / ".gitkeep"
    ).exists()
    once = snapshot(form)
    assert PROOF in once and "decisions/global/salt-late.md" in once
    assert sync(vault, form).returncode == 0
    assert snapshot(form) == once


def test_a_page_that_leaves_the_vault_leaves_the_form_on_the_next_run(tmp_path: Path):
    vault, form = make_vault(tmp_path, {"salt-late": render(), "pepper": render(title="Pepper")}), copy_form(tmp_path)
    assert sync(vault, form).returncode == 0
    (vault / "decisions" / "global" / "pepper.md").write_text(render(title="Pepper", status="withdrawn"), "utf-8")
    done = sync(vault, form)
    assert done.returncode == 0 and last(done) == "1 carried, 0 refused, 1 skipped", done.stdout
    assert sorted(p.name for p in (form / "decisions" / "global").glob("*.md")) == ["salt-late.md"]
    assert "pepper" not in (form / "INDEX.md").read_text(encoding="utf-8")


def test_a_vault_without_decisions_global_the_form_itself_or_no_form_is_a_usage_error_and_nothing_is_written(
    tmp_path: Path,
):
    vault, form = make_vault(tmp_path, {"salt-late": render()}), copy_form(tmp_path)
    nothing = tmp_path / "nothing"
    nothing.mkdir()
    before = snapshot(form)
    for done, words in (
        (sync(nothing, form), "no decisions/global/ folder"),
        (sync(form, form), "the template's vault form itself"),
        (sync(vault, nothing), "has no ops/check_pages.py"),
        (
            subprocess.run(
                [sys.executable, "-B", str(SCRIPT)], capture_output=True, text=True, timeout=60, check=False
            ),
            "--vault",
        ),
    ):
        assert done.returncode == 2 and words in done.stderr, done.stderr
    assert snapshot(form) == before


def test_a_form_that_fails_its_own_check_for_a_page_that_is_not_a_global_page_is_not_written_to(tmp_path: Path):
    vault, form = make_vault(tmp_path, {"salt-late": render()}), copy_form(tmp_path)
    (form / "concepts" / "broken.md").write_text("no frontmatter here\n", encoding="utf-8")
    before = snapshot(form)
    done = sync(vault, form)
    assert done.returncode == 2, done.stdout + done.stderr
    assert "concepts/broken.md" in done.stdout + done.stderr
    assert snapshot(form) == before


def test_the_model_families_are_the_pipeline_preflights_and_none_is_spelled_here():
    assert sync_module().MODELS == FAMILIES and len(FAMILIES) == 4
    source = SCRIPT.read_text(encoding="utf-8") + Path(__file__).read_text(encoding="utf-8")
    assert not re.search(r"(?i)" + "|".join(FAMILIES), source)


def test_the_owner_words_cover_every_word_the_new_vault_tests_refuse():
    words = load("new_vault_words", NEW_VAULT_TESTS).OWNER.pattern.removeprefix("(?i)").split("|")
    samples = [word.replace("\\b", "").replace("\\", "") for word in words]
    assert len(samples) >= 10 and "tite" in samples and "README.ka" in samples
    assert [s for s in samples if not sync_module().OWNER.search(s) or not sync_module().OWNER.search(s.upper())] == []


def test_a_related_entry_whose_page_does_not_travel_goes_with_its_gloss_and_the_others_stay(tmp_path: Path):
    related = "\nRelated: [[pepper]] (what to grind), [[personal]] (a private page), [[lime]].\n"
    pages = {
        "salt-late": render(body=BODY + related),
        "pepper": render(title="Pepper"),
        "lime": render(title="Lime"),
        "personal": render(title="Personal", template="no"),
    }
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 0 and last(done) == "3 carried, 0 refused, 1 skipped", done.stdout
    assert "carried salt-late (dropped from Related: personal)" in done.stdout.splitlines()
    copy = (form / "decisions" / "global" / "salt-late.md").read_text(encoding="utf-8")
    assert copy.endswith("\nRelated: [[pepper]] (what to grind), [[lime]].\n")
    assert "personal" not in copy and "private page" not in copy
    assert check(form).returncode == 0


def test_a_related_paragraph_left_with_no_entry_goes_with_its_blank_line(tmp_path: Path):
    text = render(body=BODY + "\nRelated: [[personal]], [[nowhere]].\n")
    vault = make_vault(tmp_path, {"salt-late": text, "personal": render(title="Personal", template="no")})
    form = copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 0 and last(done) == "1 carried, 0 refused, 1 skipped", done.stdout
    assert "carried salt-late (dropped from Related: personal, nowhere)" in done.stdout.splitlines()
    want = render().replace(f"sources: [{STATEMENT}]", "sources: []")
    assert (form / "decisions" / "global" / "salt-late.md").read_text(encoding="utf-8") == want


def test_a_related_paragraph_whose_entries_all_travel_is_copied_byte_for_byte(tmp_path: Path):
    text = render(body=BODY + "\nRelated: [[pepper]] (a gloss that\nwraps), [[lime]].\n")
    pages = {"salt-late": text, "pepper": render(title="Pepper"), "lime": render(title="Lime")}
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    assert sync(vault, form).returncode == 0
    want = text.replace(f"sources: [{STATEMENT}]", "sources: []")
    assert (form / "decisions" / "global" / "salt-late.md").read_text(encoding="utf-8") == want


def test_a_related_paragraph_that_holds_more_than_entries_is_prose_and_its_links_must_resolve(tmp_path: Path):
    text = render(body=BODY + "\nRelated: see [[personal]] for the other cases.\n")
    pages = {"salt-late": text, "personal": render(title="Personal", template="no")}
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 1 and last(done) == "0 carried, 1 refused, 1 skipped", done.stdout
    assert "refused salt-late: link [[personal]] does not resolve" in done.stdout


def test_an_entry_for_a_page_that_is_refused_goes_too(tmp_path: Path):
    pages = {
        "salt-late": render(body=BODY + "\nRelated: [[pepper]].\n"),
        "pepper": render(title="Pepper", body=BODY + f"Salt {LETTER}.\n"),
    }
    vault, form = make_vault(tmp_path, pages), copy_form(tmp_path)
    done = sync(vault, form)
    assert done.returncode == 1 and last(done) == "1 carried, 1 refused, 0 skipped", done.stdout
    assert "carried salt-late (dropped from Related: pepper)" in done.stdout.splitlines()
    assert "refused pepper: " in done.stdout
    assert check(form).returncode == 0
