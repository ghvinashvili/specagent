"""ops/obsidian-ingest.py (wiki/decisions/the-checkout-is-a-claude-obsidian-vault.md): the claims of a page are the
bullets of its rule section or its sentences; the hot cache and the log keep their limits and their orders; a page
ingested into a vault leaves its source, its claims, its capture and its entries, and its own text unchanged. The tests
that run the plugin use a synthetic vault, one of them a copy of the checkout's own files (never its history), and skip
when the plugin is not installed."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RULE, PROSE = "wiki/decisions/the-rule-page.md", "wiki/decisions/the-prose-page.md"
SUMMARIES = (RULE.replace(".md", ".summary.md"), PROSE.replace(".md", ".summary.md"))
SOURCES, CLAIMS = "wiki/meta/ledgers/source-ledger.json", "wiki/meta/ledgers/claim-ledger.json"
INTRO = "Append-only; plugin operation entries newest first at the top; hand-written entries below them, newest last."
OLD_ENTRY = "## 2026-10-29 pages written with the work\n- commit: a task of an earlier run\n- created: a page\n"
STAMP = "2026-10-30T18:21:16Z"

# The vault as `ops/adopt-obsidian.py --apply` leaves it: nothing ingested yet.
HOT = """---
type: meta
title: Hot Cache
status: developing
created: 2026-10-30
updated: 2026-10-30
tags:
  - meta
  - hot-cache
---

# Recent Context

Navigation: [[index|Wiki index]] · [[overview|Vault overview]] · [[log|Operation history]]

## Last Updated

Vault initialized. No knowledge operations have completed yet.

## Key Recent Facts

- No facts recorded.

## Recent Changes

- Created the vault foundation.

## Active Threads

- Add a source to `inbox/`, then ingest it.
"""
OVERVIEW = """---
type: overview
title: Vault Overview
status: developing
created: 2026-10-30
updated: 2026-10-30
tags:
  - overview
---

# Vault Overview

This local-first vault compounds source-backed knowledge over time.

Use [[index|Wiki index]] to find knowledge, [[hot|Recent context]] to resume
work, and [[log|Operation history]] to review completed operations.
"""
INDEX = """---
type: meta
title: Wiki index
status: evergreen
created: 2026-10-30
updated: 2026-10-30
tags:
  - meta
  - index
---

# Wiki index

- [The rule page](decisions/the-rule-page.md): a page whose rule section holds its claims
- [The prose page](decisions/the-prose-page.md): a page of prose
"""
LOG = f"""---
type: meta
title: Wiki log
status: evergreen
created: 2026-10-30
updated: 2026-10-30
tags:
  - meta
  - log
---

# Wiki log

{INTRO}

{OLD_ENTRY}"""

RULE_BODY = """Context that is no claim of its own.

## The rule

- The first rule is one line.
- The second rule wraps
  over two lines.

## Record and source

The run that wrote it is named in its build log.
"""
RULE_CLAIMS = ["The first rule is one line.", "The second rule wraps over two lines."]
PROSE_BODY = """The vault is plain text, e.g. Markdown files. It has no database.

## What `ingest` reads

The driver reads the page as it was committed. Nothing else is read.

## Record and source

The run recorded it in its build log.
"""
PROSE_CLAIMS = [
    "The vault is plain text, e.g. Markdown files.",
    "It has no database.",
    "The driver reads the page as it was committed.",
    "Nothing else is read.",
]
CODE_HEADING = "What" + " " * 10 + "reads"  # `What `ingest` reads`, its code span blanked as the plugin reads a heading

# Line numbers matter in these two: the claims cite them.
RULE_TEXT = """---
title: T
---

# T

Context that is no claim.

## The rule

- The first rule is one line.
- The second rule wraps
  over two lines.

```text
- inside a fence
```

1. A numbered rule.

## Record and source

- A bullet of the record.
"""
PROSE_TEXT = """---
title: T
---

# T

The vault is plain text, e.g. Markdown files. It has no
database.

- A bullet outside any rule section.

```text
Fenced text is never a claim. Not even this one.
```

## Record and source

The run recorded it. See the log.
"""


def load():
    spec = importlib.util.spec_from_file_location("obsidian_ingest", ROOT / "ops" / "obsidian-ingest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


needs_plugin = pytest.mark.skipif(
    load().ADOPT.cli(ROOT) is None,
    reason="claude-obsidian plugin not installed: python3 ops/adopt-obsidian.py cli prints nothing",
)


def page(title: str, body: str) -> str:
    return f"""---
title: {title}
type: decision
status: draft
updated: 2026-10-30
created: 2026-10-29
audience: [all]
decided: 2026-10-29
by: owner
why: a page of the test vault
would_change_if: the test finds another reading
decision_status: decided
scope: global
tags:
  - decision
---

# {title}

{body}"""


def git(vault: Path, *args: str) -> None:
    flags = ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false"]
    flags += ["-c", "core.hooksPath=/dev/null", "-c", "core.autocrlf=false"]
    subprocess.run(["git", *flags, "-C", str(vault), *args], check=True, capture_output=True)


def make_vault(tmp_path: Path) -> Path:
    """The adopted vault with two decision pages and their summaries, committed: the pages are at HEAD."""
    vault = tmp_path / "vault"
    ledger = {"generated_at": STAMP}
    files = {
        "wiki/hot.md": HOT,
        "wiki/overview.md": OVERVIEW,
        "wiki/index.md": INDEX,
        "wiki/log.md": LOG,
        RULE: page("The rule page", RULE_BODY),
        PROSE: page("The prose page", PROSE_BODY),
        SUMMARIES[0]: "A page whose rule section holds its claims.\n",
        SUMMARIES[1]: "A page of prose.\n",
        SOURCES: json.dumps({**ledger, "schema": "claude-obsidian.source-ledger.v1", "sources": {}}, indent=2) + "\n",
        CLAIMS: json.dumps({**ledger, "schema": "claude-obsidian.claim-ledger.v1", "claims": {}}, indent=2) + "\n",
        ".raw/.manifest.json": json.dumps(
            {
                "address_map": {},
                "description": "Ingest delta tracker. Source payloads are create-only.",
                "sources": {},
                "version": 1,
            },
            indent=2,
        )
        + "\n",
        "inbox/.gitkeep": "",
    }
    for rel, text in files.items():
        (vault / rel).parent.mkdir(parents=True, exist_ok=True)
        (vault / rel).write_text(text, encoding="utf-8")
    for rel in (".claude-obsidian.json", ".vault-meta/lint-allowlist.json"):
        (vault / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, vault / rel)
    git(vault, "init", "-q")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "seed")
    return vault


def tree(vault: Path) -> dict[str, bytes]:
    return {
        p.relative_to(vault).as_posix(): p.read_bytes()
        for p in vault.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }


def ledgers(vault: Path) -> tuple[dict, dict]:
    return (
        json.loads((vault / SOURCES).read_text(encoding="utf-8"))["sources"],
        json.loads((vault / CLAIMS).read_text(encoding="utf-8"))["claims"],
    )


@pytest.fixture(scope="module")
def ingested(tmp_path_factory):
    """A vault whose two pages went through the driver, with the files that must come out unchanged as they were."""
    m = load()
    vault = make_vault(tmp_path_factory.mktemp("ingest"))
    unchanged = {rel: (vault / rel).read_bytes() for rel in (RULE, PROSE, *SUMMARIES, "wiki/index.md")}
    for rel in (RULE, PROSE):
        assert m.main(["--root", str(vault), "--rev", "HEAD", rel]) == 0
    return vault, unchanged


def test_the_claims_of_a_page_are_the_bullets_of_its_rule_section():
    m = load()
    got = [(c["text"], c["anchor"], c["first"], c["last"], m.locator(c)) for c in m.claims_of(RULE_TEXT)]
    assert got == [
        ("The first rule is one line.", "The rule", 11, 11, "L11"),
        ("The second rule wraps over two lines.", "The rule", 12, 13, "L12-L13"),
        ("A numbered rule.", "The rule", 19, 19, "L19"),
    ]


def test_the_claims_of_a_page_without_a_rule_section_are_its_sentences_outside_the_record():
    m = load()
    got = [(c["text"], c["anchor"], m.locator(c)) for c in m.claims_of(PROSE_TEXT)]
    assert got == [
        ("The vault is plain text, e.g. Markdown files.", "T", "L7"),
        ("It has no database.", "T", "L7-L8"),
        ("A bullet outside any rule section.", "T", "L10"),
    ]


def test_a_sentence_spans_the_lines_it_runs_over():
    m = load()
    assert m.sentences([(3, "First one"), (4, "ends here. Second one.")]) == [
        ("First one ends here.", 3, 4),
        ("Second one.", 4, 4),
    ]


def test_a_code_span_is_blanked_as_the_plugin_reads_a_heading():
    m = load()
    assert m.mask_code("## The `a` rule") == "## The     rule"
    assert m.mask_code("a ``b`c`` d") == "a         d"
    assert m.mask_code("an `unclosed span") == "an " + " " * 14
    claims = m.claims_of(page("T", PROSE_BODY))
    assert {c["anchor"] for c in claims if "driver" in c["text"]} == {CODE_HEADING}


def test_the_hot_cache_folds_its_oldest_facts_and_keeps_six_changes():
    m = load()
    hot = HOT
    for n in range(40):
        fact, change = f"- fact {n} " + "word " * 30, f"- change {n}"
        hot = m.update_hot(hot, fact, change, f"stamp {n}", ["- a thread"], "2026-10-31")
    assert m.words(hot) <= m.HOT_WORDS
    assert "- fact 39 " in hot
    assert "- fact 0 " not in hot
    assert [n for n in range(40) if f"- change {n}\n" in hot] == list(range(34, 40))
    assert "No facts recorded" not in hot
    assert "updated: 2026-10-31" in hot
    assert "stamp 39" in hot
    with pytest.raises(SystemExit, match="480 words"):
        m.update_hot(HOT, "- " + "word " * 500, "- change", "stamp", ["- a thread"], "2026-10-31")


def test_the_log_entry_goes_above_the_older_ones_and_the_intro_stays():
    m = load()
    entry = "## [2026-10-31] ingest | x\n- Page: [[x]]\n"
    out = m.add_to_log(LOG, entry, "2026-10-31")
    assert "updated: 2026-10-31" in out
    assert INTRO in out
    assert out.endswith(
        entry + "\n" + OLD_ENTRY
    )  # a blank line between; the old history stays a suffix, as the gate wants
    assert m.add_to_log("# Wiki log\n", entry, "2026-10-31").endswith(entry)


def test_only_pages_of_the_vault_are_taken_as_arguments(tmp_path):
    m = load()
    vault = make_vault(tmp_path).resolve()
    assert m.page_rel(vault, RULE) == RULE
    assert m.page_rel(vault, str(vault / RULE)) == RULE
    for bad in (
        SUMMARIES[0],
        "wiki/index.md",
        "wiki/meta/ledgers/source-ledger.json",
        "wiki/decisions/gone.md",
        "README.md",
    ):
        with pytest.raises(SystemExit):
            m.page_rel(vault, bad)


def test_all_decisions_lists_the_pages_in_no_source(tmp_path, capsys):
    m = load()
    vault = make_vault(tmp_path)
    assert m.main(["--root", str(vault), "--all-decisions"]) == 0
    assert capsys.readouterr().out.split() == [PROSE, RULE]


def test_a_dry_run_prints_the_bundle_and_writes_nothing(tmp_path, capsys):
    m = load()
    vault = make_vault(tmp_path)
    before = tree(vault)
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--dry-run", RULE]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert [c["text"] for c in shown["claims"]] == RULE_CLAIMS
    assert shown["operation_type"] == "ingest"
    assert shown["hot_words"] <= 500
    assert sorted(w["path"] for w in shown["writes"]) == sorted(
        ["wiki/index.md", RULE, "wiki/log.md", "wiki/hot.md", SOURCES, CLAIMS]
    )
    bundle = shown["bundle"]  # the transaction document itself, as `workflow inspect` reads it
    writes = {w["path"]: w for w in bundle["writes"]}
    assert bundle["schema"] == "claude-obsidian.transaction.v1"
    assert bundle["operation_id"] == shown["operation_id"]
    assert set(bundle["expected_hashes"]) == set(writes)
    assert all(m.sha256(w["content"]) == w["sha256"] for w in writes.values())
    assert RULE_CLAIMS[0] in writes[CLAIMS]["content"]
    assert "## [" in writes["wiki/log.md"]["content"] and shown["log_entry"] in writes["wiki/log.md"]["content"]
    assert bundle["workflow"] == {"catalogs": ["wiki/index.md"]}
    assert list(bundle["source_manifest_updates"]) == [shown["capture"]]
    assert tree(vault) == before


def test_a_page_that_differs_from_its_revision_is_refused(tmp_path):
    m = load()
    vault = make_vault(tmp_path)
    (vault / RULE).write_text(page("The rule page", RULE_BODY) + "An edit after the commit.\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="differs from its text at"):
        m.main(["--root", str(vault), "--rev", "HEAD", "--dry-run", RULE])


@needs_plugin
def test_an_ingested_page_has_its_source_its_claims_and_its_capture(ingested):
    vault, unchanged = ingested
    sources, claims = ledgers(vault)
    (sid, source), *_ = ((k, v) for k, v in sources.items() if v["pages"] == [RULE])
    assert re.fullmatch(r"decisions/the-rule-page\.md@[0-9a-f]{7}", source["title"])
    assert source["origin"]["locator"] == f".raw/captured/{source['content_sha256']}.md"
    assert (vault / source["origin"]["locator"]).read_bytes() == unchanged[RULE]
    mine = [c for c in claims.values() if c["evidence"][0]["source_id"] == sid]
    assert [c["text"] for c in mine] == RULE_CLAIMS
    lines = unchanged[RULE].decode().split("\n")
    for c in mine:
        first = int(re.fullmatch(r"L(\d+)(?:-L\d+)?", c["evidence"][0]["locator"]).group(1))
        assert " ".join(c["text"].split()[:3]) in lines[first - 1]
        assert c["location"] == {"path": RULE, "anchor": "The rule"}


@needs_plugin
def test_a_heading_with_a_code_span_is_an_anchor_the_plugin_accepts(ingested):
    vault, _ = ingested
    sources, claims = ledgers(vault)
    sid = next(k for k, v in sources.items() if v["pages"] == [PROSE])
    mine = [c for c in claims.values() if c["evidence"][0]["source_id"] == sid]
    assert sorted(c["text"] for c in mine) == sorted(PROSE_CLAIMS)
    assert {c["location"]["anchor"] for c in mine} == {"The prose page", CODE_HEADING}


@needs_plugin
def test_the_log_gets_the_newest_entry_first_and_keeps_its_history(ingested):
    vault, _ = ingested
    log = (vault / "wiki/log.md").read_text(encoding="utf-8")
    headings = re.findall(r"(?m)^## .*$", log)
    assert re.match(r"## \[\d{4}-\d{2}-\d{2}\] ingest \| decisions/the-prose-page\.md@[0-9a-f]{7}$", headings[0])
    assert re.match(r"## \[\d{4}-\d{2}-\d{2}\] ingest \| decisions/the-rule-page\.md@[0-9a-f]{7}$", headings[1])
    assert headings[2:] == ["## 2026-10-29 pages written with the work"]
    assert INTRO in log
    assert log.endswith(OLD_ENTRY)


@needs_plugin
def test_the_hot_cache_names_both_pages_and_stays_under_the_limit(ingested):
    vault, _ = ingested
    hot = (vault / "wiki/hot.md").read_text(encoding="utf-8")
    assert len(hot.split("---\n", 2)[2].split()) <= 500
    assert "[[decisions/the-rule-page|The rule page]], decided 2026-10-29, by owner." in hot
    assert "[[decisions/the-prose-page|The prose page]], decided 2026-10-29, by owner." in hot
    assert "No facts recorded" not in hot


@needs_plugin
def test_the_pages_their_summaries_and_the_index_are_unchanged(ingested):
    vault, unchanged = ingested
    for rel, text in unchanged.items():
        assert (vault / rel).read_bytes() == text, rel


@needs_plugin
def test_a_page_is_ingested_once(ingested, capsys):
    m = load()
    vault, _ = ingested
    before = tree(vault)
    capsys.readouterr()
    assert m.main(["--root", str(vault), "--rev", "HEAD", RULE]) == 0
    assert capsys.readouterr().out.startswith(f"skip {RULE}")
    assert m.main(["--root", str(vault), "--all-decisions"]) == 0
    assert capsys.readouterr().out == ""
    assert tree(vault) == before


@needs_plugin
def test_a_bundle_the_gate_refuses_stops_the_run_and_changes_nothing(tmp_path):
    m = load()
    vault = make_vault(tmp_path)
    data = (vault / RULE).read_bytes()
    label = "decisions/the-rule-page.md@abcdef0"
    m.stage(vault, RULE, data, label, m.sha256(data))
    plan = m.plan_page(vault, RULE, data, label, "abcdef0")
    plan["bundle"]["writes"] = [w for w in plan["bundle"]["writes"] if w["path"] != "wiki/log.md"]
    del plan["bundle"]["expected_hashes"]["wiki/log.md"]
    before = tree(vault)
    with pytest.raises(SystemExit, match="workflow inspect refused"):
        m.commit(vault, RULE, plan)
    assert tree(vault) == before


@needs_plugin
def test_a_failing_command_of_the_plugin_stops_the_run(tmp_path):
    m = load()
    vault = make_vault(tmp_path)
    with pytest.raises(SystemExit, match="workflow inspect failed"):
        m.core(vault, "workflow", "inspect", str(tmp_path / "missing.json"), "--vault", str(vault), ok=(0, 1))


@pytest.mark.parametrize(
    "answer",
    [
        {},
        {"summary": {}},
        {"summary": None},
        {"summary": {"category_counts": None}},
        {"summary": {"category_counts": []}},
    ],
)
def test_a_lint_answer_without_its_counts_stops_the_run(answer, monkeypatch):
    """R9 (specs/003-pipeline-economy): an answer without `summary.category_counts` is no clean vault, so the run stops
    with a message that names the key. `core` is replaced: no plugin is needed."""
    m = load()
    monkeypatch.setattr(m, "core", lambda *args, **kwargs: answer)
    with pytest.raises(SystemExit, match=r"lint after wiki/a\.md: .*summary\.category_counts"):
        m.lint(Path("."), "wiki/a.md")


def test_a_lint_answer_with_its_counts_passes_unless_a_category_is_not_tolerated(monkeypatch):
    """The counts that stay are read as before: none, zeros and a tolerated category pass; any other count stops."""
    m = load()
    tolerated = next(iter(m.ADOPT.LINT_TOLERATED))
    for counts in ({}, {"orphans": 0}, {tolerated: 2}):
        monkeypatch.setattr(m, "core", lambda *args, counts=counts, **kwargs: {"summary": {"category_counts": counts}})
        m.lint(Path("."), "wiki/a.md")
    answer = {"summary": {"category_counts": {"dead_links": 1}}, "dead_links": [{"path": "wiki/b.md"}]}
    monkeypatch.setattr(m, "core", lambda *args, **kwargs: answer)
    with pytest.raises(SystemExit, match=r"lint after wiki/a\.md: \{'dead_links': 1\}"):
        m.lint(Path("."), "wiki/a.md")


SOON = 30  # the driver's due window (DUE_WINDOW_DAYS), in days
YEAR = 365  # the period a source is due after it is recorded (REFRESH_DAYS)
NEW_PAGE = "wiki/decisions/a-page-of-the-copy.md"
NEW_BODY = """## The rule
- The copy takes the page as the real vault takes its own.
- The page adds one claim for each rule it states.
"""


REVISED = RULE_BODY.replace("- The first rule is one line.", "- The first rule is one line, as revised.")
REVISED_CLAIMS = ["The first rule is one line, as revised.", "The second rule wraps over two lines."]


def day_after(day: str, days: int) -> str:
    return (dt.date.fromisoformat(day) + dt.timedelta(days=days)).isoformat()


def provenance_errors(m, vault: Path, as_of: str) -> int:
    answer = m.core(vault, "lint", "--vault", str(vault), "--as-of", as_of, "--format", "json", ok=(0, 1))
    return answer["summary"]["category_counts"].get("provenance_errors", 0)


def age(vault: Path, due: dict[str, str]) -> None:
    """Sources as fallen due (source id -> due date), recorded a year before it. The gate refuses to record a stale
    source, so the ledgers of the temporary vault are edited."""
    paths = vault / SOURCES, vault / CLAIMS
    sources, claims = (json.loads(p.read_text(encoding="utf-8")) for p in paths)
    for sid, when in due.items():
        sources["sources"][sid].update(
            ingested_at=day_after(when, -YEAR), retrieved_at=day_after(when, -YEAR), refresh_due=when
        )
    for claim in claims["claims"].values():
        if (sid := claim["evidence"][0]["source_id"]) in due:
            claim["reviewed_at"] = day_after(due[sid], -YEAR)
    for path, ledger in zip(paths, (sources, claims), strict=True):
        path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ingest_both(m, vault: Path) -> dict[str, str]:
    for rel in (RULE, PROSE):
        assert m.main(["--root", str(vault), "--rev", "HEAD", rel]) == 0
    return {v["pages"][0]: k for k, v in ledgers(vault)[0].items()}


def revise(vault: Path, rel: str, text: str) -> None:
    """The page as another text, committed."""
    (vault / rel).write_text(text, encoding="utf-8")
    git(vault, "commit", "-aqm", f"revise {rel}")


def claims_citing(claims: dict, sid: str) -> list[tuple[str, str]]:
    """(assessment, text) of each claim that cites the source."""
    return sorted((c["assessment"], c["text"]) for c in claims.values() if c["evidence"][0]["source_id"] == sid)


def active_source_of(sources: dict, rel: str) -> str:
    (sid,) = [s for s, v in sources.items() if v["pages"] == [rel] and v["review_status"] == "active"]
    return sid


def count_superseded(vault: Path) -> int:
    """The sources the vault has already replaced by a newer text of their page: a copy of the real vault has some."""
    return [s["review_status"] for s in ledgers(vault)[0].values()].count("superseded")


def retire(text: str, by: str) -> str:
    """The page as .claude/rules/wiki.md says a revised decision is written."""
    return text.replace("decision_status: decided\n", f"decision_status: revised\nrevised_by: {by}\n")


def withdraw(text: str, why: str) -> str:
    """The page as a decision that turned out wrong is kept: `withdrawn`, with the reason, and nothing removed."""
    return text.replace("decision_status: decided\n", "decision_status: withdrawn\n") + f"\nWithdrawn: {why}.\n"


def remove(vault: Path, rel: str) -> None:
    """The page and its summary removed and committed, as .claude/rules/wiki.md said a page that turned out wrong goes."""
    git(vault, "rm", "-q", rel, rel.replace(".md", ".summary.md"))
    git(vault, "commit", "-qm", f"remove {rel}")


def as_ingested(vault: Path) -> None:
    """Each page as its active source holds it, committed: no page of the copy was edited after its ingest."""
    for record in ledgers(vault)[0].values():
        if record["review_status"] == "active":
            (rel,) = record["pages"]
            (vault / rel).write_bytes((vault / record["origin"]["locator"]).read_bytes())
    git(vault, "commit", "-aqm", "pages as ingested", "--allow-empty")


@pytest.fixture(scope="module")
def refreshed(tmp_path_factory):
    """Two ingested pages whose sources fell due 20 days ago, then one refresh that names only the rule page."""
    m = load()
    vault = make_vault(tmp_path_factory.mktemp("refresh"))
    sid = ingest_both(m, vault)
    today, before = m.now()[:10], ledgers(vault)
    age(vault, {s: day_after(today, -20) for s in sid.values()})
    stale = provenance_errors(m, vault, today)
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--refresh", RULE]) == 0
    return vault, before, today, stale


@pytest.fixture(scope="module")
def superseded(tmp_path_factory):
    """Two ingested pages whose sources fell due yesterday and the rule page revised and committed: what the refresh
    says to it (it writes nothing), then one --supersede of the rule page."""
    m = load()
    vault = make_vault(tmp_path_factory.mktemp("supersede"))
    sid = ingest_both(m, vault)
    today = m.now()[:10]
    age(vault, {s: day_after(today, -1) for s in sid.values()})
    revise(vault, RULE, page("The rule page", REVISED))
    stale, before = provenance_errors(m, vault, today), tree(vault)
    with pytest.raises(SystemExit) as refused:
        m.main(["--root", str(vault), "--rev", "HEAD", "--refresh"])
    assert tree(vault) == before
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--supersede", RULE]) == 0
    return vault, sid, today, stale, str(refused.value)


@needs_plugin
def test_an_ingested_page_is_due_a_year_after_it_is_recorded(ingested):
    vault, _ = ingested
    sources = ledgers(vault)[0].values()
    assert {s["refresh_due"] for s in sources} == {day_after(s["retrieved_at"], YEAR) for s in sources}
    assert load().REFRESH_DAYS == YEAR


@needs_plugin
def test_a_source_past_its_due_date_fails_the_lint_until_the_refresh(refreshed):
    vault, _, today, stale = refreshed
    m = load()
    assert stale > 0
    assert provenance_errors(m, vault, today) == 0
    assert provenance_errors(m, vault, day_after(today, YEAR)) == 0  # the last day it holds
    assert provenance_errors(m, vault, day_after(today, YEAR + 1)) > 0


@needs_plugin
def test_a_refresh_renews_the_named_page_and_every_page_past_its_due_date(refreshed):
    vault, before, today, _ = refreshed
    sources, claims = ledgers(vault)
    assert claims == before[1]  # the same claims, re-read today
    assert sources == {sid: {**s, "ingested_at": day_after(today, -20 - YEAR)} for sid, s in before[0].items()}


@needs_plugin
def test_a_refresh_is_one_log_entry_and_changes_no_page(refreshed):
    vault, _, today, _ = refreshed
    headings = re.findall(r"(?m)^## .*$", (vault / "wiki/log.md").read_text(encoding="utf-8"))
    assert headings[0] == f"## [{today}] ingest | refresh of 2 pages"
    assert [h.split(" | ")[1].split("@")[0] for h in headings[1:3]] == [
        "decisions/the-prose-page.md",
        "decisions/the-rule-page.md",
    ]
    hot = (vault / "wiki/hot.md").read_text(encoding="utf-8")
    assert hot.count("[[decisions/the-rule-page|") == 1  # a refresh adds no fact
    assert "- Refreshed 2 pages" in hot
    assert len(hot.split("---\n", 2)[2].split()) <= 500
    git(vault, "diff", "--exit-code", "--quiet", "HEAD", "--", RULE, PROSE, *SUMMARIES, "wiki/index.md")


@needs_plugin
def test_the_due_list_names_the_pages_that_fall_due_within_the_window(tmp_path, capsys):
    m = load()
    vault = make_vault(tmp_path)
    sid = ingest_both(m, vault)
    today = m.now()[:10]
    capsys.readouterr()
    assert m.main(["--root", str(vault), "--due"]) == 0
    assert capsys.readouterr().out == ""
    age(vault, {sid[RULE]: day_after(today, SOON), sid[PROSE]: day_after(today, SOON + 1)})
    assert m.main(["--root", str(vault), "--due"]) == 0
    assert capsys.readouterr().out.split() == [RULE, day_after(today, SOON)]
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--refresh"]) == 0  # no page named: the pages due
    due = {p: ledgers(vault)[0][s]["refresh_due"] for p, s in sid.items()}
    assert due == {RULE: day_after(today, YEAR), PROSE: day_after(today, SOON + 1)}
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--refresh", PROSE]) == 0  # a page named: due or not
    assert ledgers(vault)[0][sid[PROSE]]["refresh_due"] == day_after(today, YEAR)
    before = tree(vault)
    capsys.readouterr()
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--refresh", RULE, PROSE]) == 0
    assert "nothing to renew" in capsys.readouterr().out
    assert tree(vault) == before


@needs_plugin
def test_a_page_in_no_source_and_a_page_changed_since_its_source_are_refused(tmp_path):
    m = load()
    vault = make_vault(tmp_path)
    before = tree(vault)
    for flag in ("--refresh", "--supersede"):
        with pytest.raises(SystemExit, match="in no source yet"):
            m.main(["--root", str(vault), "--rev", "HEAD", flag, RULE])
    assert tree(vault) == before
    assert m.main(["--root", str(vault), "--rev", "HEAD", RULE]) == 0
    (vault / RULE).write_text(page("The rule page", RULE_BODY) + "A change.\n", encoding="utf-8")
    git(vault, "commit", "-aqm", "change the page")
    before = tree(vault)
    for argv in ([RULE], ["--refresh", RULE]):  # an ingest and a refresh of the page as it is now
        with pytest.raises(SystemExit, match=f"changed since its source.*--supersede {RULE}"):
            m.main(["--root", str(vault), "--rev", "HEAD", *argv])
    assert tree(vault) == before


@needs_plugin
def test_a_refresh_holds_back_a_changed_page_and_renews_the_others(tmp_path, capsys):
    m = load()
    vault = make_vault(tmp_path)
    sid = ingest_both(m, vault)
    today = m.now()[:10]
    age(vault, {s: day_after(today, SOON - 10) for s in sid.values()})  # both due, neither past its date
    revise(vault, RULE, page("The rule page", REVISED))
    old = ledgers(vault)[0][sid[RULE]]
    capsys.readouterr()
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--refresh"]) == 0
    out = capsys.readouterr().out
    assert f"held back: {RULE} changed since its source" in out and f"--supersede {RULE}" in out
    sources = ledgers(vault)[0]
    assert sources[sid[PROSE]]["refresh_due"] == day_after(today, YEAR)
    assert sources[sid[RULE]] == old  # nothing says the old text was read again
    assert provenance_errors(m, vault, today) == 0


@needs_plugin
def test_a_changed_page_past_its_date_stops_the_refresh_and_names_the_way_out(superseded):
    _, _, _, stale, refused = superseded
    assert stale > 0  # the gate refuses the whole vault at this date: the refresh could not leave the page alone
    assert RULE in refused and f"--supersede {RULE}" in refused


@needs_plugin
def test_a_supersede_retires_the_old_source_and_records_the_new_text(superseded):
    vault, sid, today, _, _ = superseded
    sources, claims = ledgers(vault)
    old, new = sid[RULE], active_source_of(sources, RULE)
    assert new != old
    assert sources[old]["review_status"] == "superseded"
    assert (vault / sources[old]["origin"]["locator"]).is_file()  # the old text stays captured
    assert (sources[new]["supersedes"], sources[new]["refresh_due"]) == (old, day_after(today, YEAR))
    assert claims_citing(claims, old) == [("deprecated", t) for t in sorted(RULE_CLAIMS)]
    assert claims_citing(claims, new) == [("accepted", t) for t in sorted(REVISED_CLAIMS)]
    assert sources[sid[PROSE]]["refresh_due"] == day_after(today, YEAR)  # renewed in the same operation


@needs_plugin
def test_after_a_supersede_the_gate_holds_for_a_year(superseded):
    vault, _, today, _, _ = superseded
    m = load()
    assert provenance_errors(m, vault, today) == 0
    assert provenance_errors(m, vault, day_after(today, YEAR)) == 0
    assert provenance_errors(m, vault, day_after(today, YEAR + 1)) > 0


@needs_plugin
def test_a_supersede_is_one_log_entry_and_changes_no_page(superseded):
    vault, _, today, _, _ = superseded
    headings = re.findall(r"(?m)^## .*$", (vault / "wiki/log.md").read_text(encoding="utf-8"))
    assert headings[0] == f"## [{today}] ingest | revision of 1 page and refresh of 1 page"
    hot = (vault / "wiki/hot.md").read_text(encoding="utf-8")
    assert "- Revised 1 page; refreshed 1 page" in hot
    assert hot.count("[[decisions/the-rule-page|") == 1  # a revision adds no fact
    assert len(hot.split("---\n", 2)[2].split()) <= 500
    git(vault, "diff", "--exit-code", "--quiet", "HEAD", "--", RULE, PROSE, *SUMMARIES, "wiki/index.md")


@needs_plugin
def test_a_text_the_source_holds_has_nothing_to_supersede(superseded):
    vault, *_ = superseded
    before = tree(vault)
    with pytest.raises(SystemExit, match="nothing to supersede"):
        load().main(["--root", str(vault), "--rev", "HEAD", "--supersede", RULE])
    assert tree(vault) == before


@needs_plugin
def test_a_decision_revised_as_the_rules_say_is_superseded_with_deprecated_claims(tmp_path):
    m = load()
    vault = make_vault(tmp_path)
    ingest_both(m, vault)
    today = m.now()[:10]
    revise(vault, RULE, retire(page("The rule page", REVISED), "decisions/the-prose-page.md"))
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--supersede", RULE]) == 0
    sources, claims = ledgers(vault)
    assert claims_citing(claims, active_source_of(sources, RULE)) == [("deprecated", t) for t in sorted(REVISED_CLAIMS)]
    assert re.search(r"(?m)^## .*$", (vault / "wiki/log.md").read_text(encoding="utf-8")).group() == (
        f"## [{today}] ingest | revision of 1 page"
    )
    assert provenance_errors(m, vault, today) == provenance_errors(m, vault, day_after(today, YEAR)) == 0
    assert provenance_errors(m, vault, day_after(today, YEAR + 1)) == len(
        PROSE_CLAIMS
    )  # the deprecated claims add none


@needs_plugin
def test_the_claims_of_a_revised_or_withdrawn_decision_are_recorded_deprecated(tmp_path):
    m = load()
    vault = make_vault(tmp_path)
    for rel, status in ((RULE, "revised"), (PROSE, "withdrawn")):
        text = (vault / rel).read_text(encoding="utf-8")
        revise(vault, rel, text.replace("decision_status: decided", f"decision_status: {status}"))
        assert m.main(["--root", str(vault), "--rev", "HEAD", rel]) == 0
    claims = ledgers(vault)[1]
    assert len(claims) == len(RULE_CLAIMS) + len(PROSE_CLAIMS)
    assert {c["assessment"] for c in claims.values()} == {"deprecated"}


@needs_plugin
def test_a_dry_run_of_a_supersede_prints_the_bundle_and_writes_nothing(tmp_path, capsys):
    m = load()
    vault = make_vault(tmp_path)
    ingest_both(m, vault)
    revise(vault, RULE, page("The rule page", REVISED))
    before = tree(vault)
    capsys.readouterr()
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--dry-run", "--supersede", RULE]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["operation_type"] == "ingest" and shown["revised"] == [RULE]
    writes = {w["path"]: w for w in shown["bundle"]["writes"]}
    assert REVISED_CLAIMS[0] in writes[CLAIMS]["content"]
    assert list(shown["bundle"]["source_manifest_updates"]) == [f".raw/captured/{m.sha256(before[RULE])}.md"]
    assert tree(vault) == before


def test_supersede_takes_pages_and_not_the_refresh_flag(tmp_path, capsys):
    m = load()
    for argv, said in (
        (["--supersede"], "--supersede takes the pages"),
        (["--supersede", "--refresh", RULE], "without --refresh"),
    ):
        with pytest.raises(SystemExit) as stop:
            m.main(["--root", str(tmp_path), *argv])
        assert stop.value.code == 2
        assert said in capsys.readouterr().err


@needs_plugin
def test_the_skip_of_an_ingested_page_names_the_way_out(ingested, capsys):
    vault, _ = ingested
    capsys.readouterr()
    assert load().main(["--root", str(vault), "--rev", "HEAD", RULE]) == 0
    assert "--refresh" in capsys.readouterr().out


@pytest.fixture(scope="module")
def removed(tmp_path_factory):
    """Two ingested pages, the rule page removed with its summary and committed: the plugin's lint then, what each
    command that writes says to it (nothing is written), and the way out the refusals name: the removal reverted, the
    page withdrawn with its reason, one --supersede."""
    m = load()
    vault = make_vault(tmp_path_factory.mktemp("removed"))
    ingest_both(m, vault)
    today = m.now()[:10]
    remove(vault, RULE)
    stale, before, refused = provenance_errors(m, vault, today), tree(vault), {}
    for argv in ([PROSE], ["--refresh"], ["--refresh", PROSE], ["--supersede", RULE], ["--supersede", PROSE]):
        with pytest.raises(SystemExit) as stop:
            m.main(["--root", str(vault), "--rev", "HEAD", *argv])
        refused[" ".join(argv)] = str(stop.value)
    assert tree(vault) == before
    git(vault, "revert", "--no-edit", "HEAD")
    revise(vault, RULE, withdraw((vault / RULE).read_text(encoding="utf-8"), "the test found it wrong"))
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--supersede", RULE]) == 0
    return vault, today, stale, refused


@needs_plugin
def test_a_removed_ingested_page_fails_the_lint_of_the_whole_vault(removed):
    _, _, stale, _ = removed
    assert stale >= len(RULE_CLAIMS)  # one error for each claim that cites the missing page, no source being due


@needs_plugin
def test_every_command_that_writes_refuses_a_removed_ingested_page_and_names_the_way_out(removed):
    _, _, _, refused = removed
    assert len(refused) == 5
    for argv, text in refused.items():
        assert RULE in text and f"--supersede {RULE}" in text, argv
        assert "restore" in text and "decision_status: withdrawn" in text, argv
        assert "git show" not in text and "no page at" not in text, argv


@needs_plugin
def test_the_way_out_the_refusal_names_ends_in_a_clean_lint(removed):
    vault, today, _, _ = removed
    sources, claims = ledgers(vault)
    new = active_source_of(sources, RULE)
    assert claims_citing(claims, new) == [("deprecated", t) for t in sorted(RULE_CLAIMS)]
    assert {c["notes"] for c in claims.values() if c["evidence"][0]["source_id"] == new} == {
        "the decision is withdrawn"
    }
    assert [s["review_status"] for s in sources.values()].count("superseded") == 1
    m = load()
    assert provenance_errors(m, vault, today) == provenance_errors(m, vault, day_after(today, YEAR)) == 0


@needs_plugin
def test_a_removed_ingested_page_past_its_date_is_refused_by_the_refresh_with_the_way_out(tmp_path):
    m = load()
    vault = make_vault(tmp_path)
    sid = ingest_both(m, vault)
    today = m.now()[:10]
    age(vault, {s: day_after(today, -1) for s in sid.values()})
    remove(vault, RULE)
    before = tree(vault)
    with pytest.raises(SystemExit) as refused:
        m.main(["--root", str(vault), "--rev", "HEAD", "--refresh"])
    assert RULE in str(refused.value) and f"--supersede {RULE}" in str(refused.value)
    assert "git show" not in str(refused.value)
    assert tree(vault) == before


def copy_checkout(tmp_path: Path) -> Path:
    """The checkout's own files (its real pages, ledgers, log, hot cache and allowlist, and the files its pages link to)
    in a fresh repository, with one page and its index line added. What git ignores stays out: the plugin's journal and
    the generated graph are no vault content; a symlink stays a symlink, as the plugin's lint does not follow it."""
    vault = tmp_path / "copy"
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        check=True,
        capture_output=True,
    ).stdout.decode()
    for name in filter(None, listed.split("\0")):
        source, target = ROOT / name, vault / name
        if not source.is_symlink() and not source.is_file():  # tracked, but deleted in the working tree
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            target.symlink_to(os.readlink(source))
        else:
            shutil.copy2(source, target)
    line = "- [A page of the copy](decisions/a-page-of-the-copy.md): a page the test adds to the copy\n"
    index = (vault / "wiki/index.md").read_text(encoding="utf-8")
    (vault / "wiki/index.md").write_text(index.replace("## Decisions\n", "## Decisions\n" + line, 1), encoding="utf-8")
    (vault / NEW_PAGE).write_text(page("A page of the copy", NEW_BODY), encoding="utf-8")
    git(vault, "init", "-q")
    git(vault, "add", "-A")
    git(vault, "commit", "-q", "-m", "copy of the checkout")
    return vault


@needs_plugin
def test_a_page_goes_into_a_copy_of_the_checkouts_vault(tmp_path):
    m = load()
    vault = copy_checkout(tmp_path)
    old_sources, old_claims = ledgers(vault)
    old_headings = re.findall(r"(?m)^## .*$", (vault / "wiki/log.md").read_text(encoding="utf-8"))
    before = tree(vault)
    assert m.main(["--root", str(vault), "--rev", "HEAD", NEW_PAGE]) == 0  # its lint step runs the real allowlist
    after = tree(vault)
    changed = {p for p in after if before.get(p) != after[p] and not p.startswith(".vault-meta/")}
    captured = f".raw/captured/{m.sha256(before[NEW_PAGE])}.md"
    assert changed == {".raw/.manifest.json", captured, "wiki/hot.md", "wiki/log.md", SOURCES, CLAIMS}
    assert after[captured] == before[NEW_PAGE]
    sources, claims = ledgers(vault)
    (sid,) = set(sources) - set(old_sources)
    assert sources[sid]["pages"] == [NEW_PAGE]
    assert set(old_claims) <= set(claims)
    mine = [c["text"] for c in claims.values() if c["evidence"][0]["source_id"] == sid]
    assert mine == [
        "The copy takes the page as the real vault takes its own.",
        "The page adds one claim for each rule it states.",
    ]
    headings = re.findall(r"(?m)^## .*$", after["wiki/log.md"].decode())
    assert re.fullmatch(r"## \[\d{4}-\d{2}-\d{2}\] ingest \| decisions/a-page-of-the-copy\.md@[0-9a-f]{7}", headings[0])
    assert headings[1:] == old_headings
    assert len(after["wiki/hot.md"].decode().split("---\n", 2)[2].split()) <= 500


@needs_plugin
def test_a_revised_page_of_the_real_vault_is_superseded_when_every_source_has_fallen_due(tmp_path):
    m = load()
    vault, today = copy_checkout(tmp_path), m.now()[:10]
    as_ingested(vault)
    age(vault, {sid: day_after(today, -1) for sid, s in ledgers(vault)[0].items() if s["review_status"] == "active"})
    rel = "wiki/decisions/collector-save-check.md"
    revise(
        vault, rel, retire((vault / rel).read_text(encoding="utf-8"), "decisions/collector-yes-then-standing-rule.md")
    )
    assert provenance_errors(m, vault, today) > 0
    before = tree(vault)
    with pytest.raises(SystemExit, match=f"{rel}.*--supersede {rel}"):
        m.main(["--root", str(vault), "--rev", "HEAD", "--refresh"])
    assert tree(vault) == before
    already = count_superseded(vault)
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--supersede", rel]) == 0
    sources = ledgers(vault)[0].values()
    assert provenance_errors(m, vault, today) == 0
    assert {s["refresh_due"] for s in sources if s["review_status"] == "active"} == {day_after(today, YEAR)}
    assert count_superseded(vault) == already + 1


@needs_plugin
def test_a_removed_page_of_the_real_vault_is_withdrawn_and_superseded_when_every_source_has_fallen_due(tmp_path):
    m = load()
    vault, today = copy_checkout(tmp_path), m.now()[:10]
    as_ingested(vault)
    age(vault, {sid: day_after(today, -1) for sid, s in ledgers(vault)[0].items() if s["review_status"] == "active"})
    rel = "wiki/decisions/collector-save-check.md"
    remove(vault, rel)
    before = tree(vault)
    for argv in (["--refresh"], ["--supersede", rel]):
        with pytest.raises(SystemExit, match=f"{rel}.*--supersede {rel}"):
            m.main(["--root", str(vault), "--rev", "HEAD", *argv])
    assert tree(vault) == before
    git(vault, "revert", "--no-edit", "HEAD")
    revise(vault, rel, withdraw((vault / rel).read_text(encoding="utf-8"), "the test found it wrong"))
    already = count_superseded(vault)
    assert m.main(["--root", str(vault), "--rev", "HEAD", "--supersede", rel]) == 0
    sources = ledgers(vault)[0].values()
    assert provenance_errors(m, vault, today) == 0
    assert {s["refresh_due"] for s in sources if s["review_status"] == "active"} == {day_after(today, YEAR)}
    assert count_superseded(vault) == already + 1
