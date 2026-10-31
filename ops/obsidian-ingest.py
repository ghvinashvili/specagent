#!/usr/bin/env python3
"""Ingest wiki pages through the claude-obsidian plugin (owner, 2026-10-30): a page is one source and one `ingest`
operation, so its text is in `.raw/captured/`, its claims in the claim ledger citing that source and its entry in
`wiki/log.md` and `wiki/hot.md`, as if the vault had been built on the plugin
(wiki/decisions/the-checkout-is-a-claude-obsidian-vault.md).
  ops/obsidian-ingest.py [--rev REV] [--dry-run] PAGE...   ingest pages (paths under wiki/), one operation each
  ops/obsidian-ingest.py --all-decisions                   list the wiki/decisions pages that are in no source yet
  ops/obsidian-ingest.py --due                             list the pages whose source is due within 30 days
  ops/obsidian-ingest.py [--rev REV] [--dry-run] --refresh [PAGE...]   renew the sources of the pages named and of the due
  ops/obsidian-ingest.py [--rev REV] [--dry-run] --supersede PAGE...   record the new text of pages changed since their source
A source is due REFRESH_DAYS after it is recorded (`refresh_due`; a decision is revised by its `would_change_if`, the date only
has the ledger read again once a year). The plugin's gate checks the whole ledger against today, so one source past its date
refuses every later operation: `--refresh` renews the pages named and every page due within 30 days in one operation, the
pages and their claims as they were; ops/night-tick.sh runs it for the loop `wiki-ingest`.
A page whose text changed after its ingest is held back by `--refresh` (its claims describe the old text, so no renewal would
be true) and fails it once its source is past its date. `--supersede` records the new text as a new source with its claims,
sets the old source `superseded` and the claims that rest on it alone `deprecated`, and renews the due pages: one operation,
for the gate checks the whole ledger at once. The claims of a page whose `decision_status` is revised or withdrawn are
recorded `deprecated` (.claude/rules/wiki.md: a changed decision is a new page, the old one gets `revised`).
An ingested page is never removed: the plugin refuses every operation of a vault whose claims cite a missing page, so each
command that writes stops with the way out (restore it; a decision that turned out wrong is `withdrawn`; `--supersede`).
Per page: 1. stage: the page's text at REV (default HEAD, `git show`) is copied into inbox/ and the plugin's `capture
apply` (a dry run, then the same plan applied with its hash) stores it as .raw/captured/<sha256>.md; the copy in inbox/
goes. 2. commit: one `ingest` bundle with the page unchanged: both ledgers, the log entry, the hot cache and the index,
checked with `workflow inspect` and applied with `workflow apply`. 3. lint. The claims are the bullets of the page's
`## The rule` section or, without one, its sentences, outside `## Record and source`; each cites its lines. The vault
is changed only by the plugin's commands; a command that fails stops the run."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
SOURCE_LEDGER, CLAIM_LEDGER = "wiki/meta/ledgers/source-ledger.json", "wiki/meta/ledgers/claim-ledger.json"
REFRESH_DAYS = 365  # a source is due this many days after it is recorded, and again after each refresh
DUE_WINDOW_DAYS = (
    30  # `--due` lists the sources due within this many days, `--refresh` renews them with the pages named
)
HOT_WORDS = 480  # the plugin's workflow gate refuses a hot cache of more than 500 words
CHANGES_KEPT = 6
RULE_SECTION = "the rule"
RETIRED = {"revised", "withdrawn"}  # `decision_status` of a page whose rules no longer stand
SOURCE_SECTIONS = {"record and source"}  # links to the record, not rules
ABBREVIATIONS = {"e.g", "i.e", "vs", "cf"}  # a full stop after one of these ends no sentence
NOT_PAGES = {"meta", "plans", "graph"}  # folders of wiki/ that hold no page
NO_FACTS = "- No facts recorded."
SENTENCE_END = re.compile(r"(?P<end>[.!?][\"')\]]*)\s+(?=[A-Z\"'(\[`])")
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*$")
ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def load_adopt():
    """ops/adopt-obsidian.py: where the plugin's CLI is found and which lint categories are tolerated."""
    spec = importlib.util.spec_from_file_location("adopt_obsidian", Path(__file__).with_name("adopt-obsidian.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ADOPT = load_adopt()


def now() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def days_after(day: str, days: int) -> str:
    return (dt.date.fromisoformat(day) + dt.timedelta(days=days)).isoformat()


def sha256(data: bytes | str) -> str:
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def source_id(locator: str, digest: str) -> str:
    """The plugin's stable identity of a file source (claude_obsidian/ledgers.py: stable_source_id)."""
    return "src-" + sha256(f"file\0{locator}\0{digest}")[:20]


def words(text: str) -> int:
    """The words of a page's body, counted as the plugin's gate counts them (frontmatter left out)."""
    return len(re.sub(r"\A---\r?\n.*?\r?\n---(?:\r?\n|$)", "", text, count=1, flags=re.DOTALL).split())


def core(root: Path, *args: str, ok: tuple[int, ...] = (0,)) -> dict:
    """One call of the plugin's CLI. An exit code outside `ok`, an answer that is no JSON object and an `error` key stop the run."""
    tool = ADOPT.cli(root)
    if tool is None:
        raise SystemExit(
            "the claude-obsidian plugin is not installed on this machine: python3 ops/bootstrap.py installs it"
        )
    done = subprocess.run(
        [sys.executable, "-I", str(tool), *args], capture_output=True, text=True, check=False, timeout=300
    )
    try:
        answer = json.loads(done.stdout)
    except ValueError:
        answer = None
    if done.returncode not in ok or not isinstance(answer, dict) or answer.get("error"):
        detail = (done.stderr.strip() or done.stdout.strip())[-900:]
        raise SystemExit(f"{' '.join(args[:2])} failed (exit {done.returncode}): {detail}")
    return answer


def git(root: Path, *args: str) -> bytes:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {done.stderr.decode('utf-8', 'replace').strip()[:300]}")
    return done.stdout


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    """The top-level `key: value` lines of a page's frontmatter; lists and nested keys are left out."""
    found = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    pairs = (line.partition(":") for line in (found.group(1).split("\n") if found else []))
    return {k.strip(): v.strip().strip("\"'") for k, sep, v in pairs if sep and k and not k.startswith((" ", "-"))}


def mask_code(line: str) -> str:
    """A code span becomes spaces, as the plugin's anchor index reads a heading."""
    chars, cursor = list(line), 0
    while cursor < len(chars):
        if chars[cursor] != "`":
            cursor += 1
            continue
        run = 1
        while cursor + run < len(chars) and chars[cursor + run] == "`":
            run += 1
        closing = line.find("`" * run, cursor + run)
        end = len(chars) if closing < 0 else closing + run
        chars[cursor:end] = " " * (end - cursor)
        cursor = end
    return "".join(chars)


def sentences(parts: list[tuple[int, str]]) -> list[tuple[str, int, int]]:
    """A paragraph's sentences, each with the first and the last line it spans."""
    joined, owner = "", []
    for number, line in parts:
        line = line.strip()
        if joined:
            joined, owner = joined + " ", owner + [number]
        joined, owner = joined + line, owner + [number] * len(line)
    found, begin = [], 0
    for match in SENTENCE_END.finditer(joined):
        before = joined[begin : match.start()].rsplit(None, 1)
        if before and before[-1].lower() in ABBREVIATIONS:
            continue
        found.append((joined[begin : match.end("end")], owner[begin], owner[match.end("end") - 1]))
        begin = match.end()
    if joined[begin:].strip():
        found.append((joined[begin:], owner[begin], owner[-1]))
    return found


def claims_of(text: str) -> list[dict]:
    """The claims of a page: each bullet of its `The rule` section, else each bullet and sentence outside `Record and
    source`. A claim is {text, anchor (the nearest heading), first, last (the lines of the page)}."""
    lines = text.split("\n")
    start = next((n for n in range(1, len(lines)) if lines[n].strip() == "---"), -1) + 1 if lines[0] == "---" else 0
    stack: list[tuple[int, str, str]] = []  # (level, name, anchor) of the headings that enclose the line
    blocks: list[dict] = []
    block: dict | None = None
    fence = None

    def flush():
        nonlocal block
        if block:
            blocks.append(block)
        block = None

    for number in range(start + 1, len(lines) + 1):
        line = lines[number - 1]
        mark = FENCE.match(line)
        if fence:
            if mark and mark.group(1)[0] == fence[0] and len(mark.group(1)) >= len(fence):
                fence = None
            continue
        if mark:
            flush()
            fence = mark.group(1)
            continue
        heading = HEADING.match(line)
        if heading:
            flush()
            level, title = len(heading.group(1)), heading.group(2)
            while stack and stack[-1][0] >= level:
                stack.pop()
            anchor = mask_code(title).strip().rstrip("#").strip()
            stack.append((level, anchor.casefold(), anchor))
        elif not line.strip() or line.lstrip().startswith("|"):
            flush()
        elif item := ITEM.match(line):
            flush()
            block = {"kind": "item", "parts": [(number, item.group(1))]}
        elif block:
            block["parts"].append((number, line.lstrip("> ") if line.startswith(">") else line))
        else:
            block = {"kind": "paragraph", "parts": [(number, line.lstrip("> ") if line.startswith(">") else line)]}
        if block and "names" not in block:
            block.update(names={name for _, name, _ in stack}, anchor=stack[-1][2] if stack else None)
    flush()
    chosen = [b for b in blocks if RULE_SECTION in b["names"]] or [
        b for b in blocks if not b["names"] & SOURCE_SECTIONS
    ]
    claims = []
    for b in chosen:
        if b["kind"] == "item":
            claims.append(
                {
                    "text": " ".join(" ".join(t.split()) for _, t in b["parts"]),
                    "anchor": b["anchor"],
                    "first": b["parts"][0][0],
                    "last": b["parts"][-1][0],
                }
            )
        else:
            claims += [
                {"text": " ".join(s.split()), "anchor": b["anchor"], "first": first, "last": last}
                for s, first, last in sentences(b["parts"])
            ]
    return claims


def count(n: int, noun: str) -> str:
    return f"{n} {noun}" + ("" if n == 1 else "s")


def link_of(rel: str) -> str:
    """The wikilink target of a page: its path under wiki/ without the suffix."""
    return rel.removeprefix("wiki/").removesuffix(".md")


def locator(claim: dict) -> str:
    return f"L{claim['first']}" if claim["first"] == claim["last"] else f"L{claim['first']}-L{claim['last']}"


def page_rel(root: Path, arg: str) -> str:
    """A page argument as a path under wiki/ relative to the root; the file must be a page of the vault."""
    path = Path(arg)
    rel = PurePosixPath((path.resolve().relative_to(root) if path.is_absolute() else path).as_posix())
    if rel.parts[:1] != ("wiki",) or rel.suffix != ".md" or rel.name.endswith(".summary.md") or len(rel.parts) < 3:
        raise SystemExit(f"{arg}: not a page, give a path like wiki/decisions/<slug>.md ({rel})")
    if rel.parts[1] in NOT_PAGES or not (root / rel).is_file():
        raise SystemExit(f"{arg}: no page at {rel}")
    return rel.as_posix()


def recorded(root: Path) -> dict[str, dict]:
    """The sources of the source ledger by id."""
    return json.loads(read(root, SOURCE_LEDGER))["sources"]


def active_sources(root: Path) -> dict[str, dict]:
    """The sources that stand by id: a superseded source holds no page and is due never."""
    return {sid: record for sid, record in recorded(root).items() if record.get("review_status") == "active"}


def ingested(root: Path) -> dict[str, set[str]]:
    """The pages an active source lists, with the sources that list them."""
    pages: dict[str, set[str]] = {}
    for sid, record in active_sources(root).items():
        for page in record.get("pages", []):
            pages.setdefault(page, set()).add(sid)
    return pages


def missing(root: Path) -> dict[str, int]:
    """The pages that claims of the claim ledger cite and the checkout lacks, with the number of claims. The plugin
    checks the page of every claim, a deprecated one too, so one such page makes it refuse every operation of the vault."""
    cited: dict[str, int] = {}
    for claim in json.loads(read(root, CLAIM_LEDGER))["claims"].values():
        page = claim["location"]["path"]
        cited[page] = cited.get(page, 0) + 1
    return {page: n for page, n in sorted(cited.items()) if not (root / page).is_file()}


def gone(pages: dict[str, int]) -> str:
    """The refusal for pages that claims cite and the checkout lacks: an ingested page is never removed. One that turned
    out wrong stays, corrected or, for a decision, `withdrawn` with its reason, and `--supersede` records it."""
    listing = ", ".join(f"{rel} ({count(n, 'claim')})" for rel, n in pages.items())
    return (
        f"{listing}: cited by claims of the ledger, absent from the checkout. The plugin refuses every operation of a "
        "vault with such a claim, so an ingested page is never removed: restore it (`git revert` of the commit that "
        "removed it); a page that turned out wrong stays, corrected or, for a decision, with `decision_status: "
        f"withdrawn` and the reason, and `python3 ops/obsidian-ingest.py --supersede {' '.join(pages)}` records it"
    )


def due_date(record: dict) -> str:
    return record.get("refresh_due") or "0000-00-00"  # the plugin counts an active source with no date as stale


def due_pages(root: Path, day: str) -> list[tuple[str, str]]:
    """The pages whose active source is due within DUE_WINDOW_DAYS of `day` or already past it, as (page, due date), earliest first."""
    limit, due = days_after(day, DUE_WINDOW_DAYS), []
    for record in active_sources(root).values():
        if due_date(record) <= limit:
            due += [(page, due_date(record)) for page in record.get("pages", [])]
    return sorted(due, key=lambda item: (item[1], item[0]))


def lapsed(root: Path, rel: str, day: str) -> list[str]:
    """The active sources of the page that are past their date on `day`: the plugin's gate calls them stale."""
    return [
        sid for sid, record in active_sources(root).items() if rel in record.get("pages", []) and due_date(record) < day
    ]


def open_threads(root: Path, rel: str | None = None) -> list[str]:
    """The hot cache's Active Threads: the decision pages still to ingest, `rel` being ingested now."""
    left = [p for p in decision_pages(root) if p != rel and p not in ingested(root)]
    if left:
        return [
            f"- {len(left)} decision pages are not ingested yet: `python3 ops/obsidian-ingest.py --all-decisions` lists them."
        ]
    return ["- Add a source to `inbox/`, then ingest it."]


def decision_pages(root: Path) -> list[str]:
    folder = root / "wiki" / "decisions"
    return sorted(p.relative_to(root).as_posix() for p in folder.glob("*.md") if not p.name.endswith(".summary.md"))


def update_hot(text: str, fact: str | None, change: str, last: str, threads: list[str], day: str) -> str:
    """The hot cache with the new fact (a refresh has none) and change, the oldest lines folded out until it fits."""
    head, *parts = re.split(r"(?m)^## ", text)
    sections = {
        name.strip(): [ln for ln in body.split("\n") if ln.strip()]
        for name, _, body in (part.partition("\n") for part in parts)
    }
    facts = [ln for ln in sections.get("Key Recent Facts", []) if ln != NO_FACTS] + ([fact] if fact else [])
    changes = (sections.get("Recent Changes", []) + [change])[-CHANGES_KEPT:]
    head = re.sub(r"(?m)^updated: .*$", f"updated: {day}", head, count=1)

    def render() -> str:
        sections.update(
            {"Last Updated": [last], "Key Recent Facts": facts, "Recent Changes": changes, "Active Threads": threads}
        )
        return "\n".join(
            [head.rstrip("\n") + "\n"] + [f"## {name}\n\n" + "\n".join(body) + "\n" for name, body in sections.items()]
        )

    while words(render()) > HOT_WORDS and len(facts) > 1:
        facts.pop(0)
    if words(render()) > HOT_WORDS:
        raise SystemExit(f"wiki/hot.md stays over {HOT_WORDS} words with one fact: shorten its other sections")
    return render()


def add_to_log(text: str, entry: str, day: str) -> str:
    """The log with the entry above every older one, a blank line between (the plugin's gate wants the newest ingest first)."""
    text = re.sub(r"(?m)^updated: .*$", f"updated: {day}", text, count=1)
    first = re.search(r"(?m)^## ", text)
    if first is None:
        return text.rstrip("\n") + "\n\n" + entry
    return text[: first.start()] + entry.rstrip("\n") + "\n\n" + text[first.start() :]


def add_claims(
    claim_ledger: dict, rel: str, sid: str, claims: list[dict], day: str, retired: str | None = None
) -> None:
    """One claim per rule of the page in the claim ledger, each citing the source and the lines it came from: accepted,
    or deprecated when `retired` names why the decision no longer stands (revised, withdrawn)."""
    for number, claim in enumerate(claims):
        claim_ledger["claims"]["clm-" + sha256(f"{sid}\0{number}\0{claim['text']}")[:16]] = {
            "text": claim["text"],
            "location": {"path": rel, "anchor": claim["anchor"]},
            "risk": "normal",
            "assessment": "deprecated" if retired else "accepted",
            "confidence": "high",
            "evidence": [{"source_id": sid, "relation": "supports", "locator": locator(claim)}],
            "reviewed_at": day,
            "supersedes": None,
            "notes": f"the decision is {retired}" if retired else None,
        }


def record_page(
    source_ledger: dict, claim_ledger: dict, rel: str, data: bytes, label: str, day: str, supersedes: str | None = None
) -> tuple[str, list[dict]]:
    """The page's text as an active source due REFRESH_DAYS after `day`, and one claim per rule citing it; the id of the
    source and the claims. A text that was recorded before is recorded again under its id."""
    text, digest = data.decode("utf-8"), sha256(data)
    claims = claims_of(text)
    if not claims:
        raise SystemExit(f"{rel}: no claim found in the page")
    stored = f".raw/captured/{digest}.md"
    sid = source_id(stored, digest)
    source_ledger["sources"][sid] = {
        "origin": {"kind": "file", "locator": stored},
        "content_kind": "document",
        "title": label,
        "authority": "primary",
        "content_sha256": digest,
        "ingested_at": day,
        "retrieved_at": day,
        "refresh_due": days_after(day, REFRESH_DAYS),
        "review_status": "active",
        "independence_key": str(PurePosixPath(rel).parent),
        "pages": [rel],
        "supersedes": supersedes,
    }
    status = frontmatter(text).get("decision_status")
    add_claims(claim_ledger, rel, sid, claims, day, status if status in RETIRED else None)
    return sid, claims


def retire_sources(source_ledger: dict, claim_ledger: dict, old: list[str], new: str, day: str) -> int:
    """The sources `old` as superseded by `new`, and the claims that rest on them alone as deprecated: the plugin asks no
    fresh support of a deprecated claim. How many claims were deprecated."""
    for sid in old:
        source_ledger["sources"][sid]["review_status"] = "superseded"
    found = [
        c
        for c in claim_ledger["claims"].values()
        if c["evidence"] and c["assessment"] != "deprecated" and all(e["source_id"] in old for e in c["evidence"])
    ]
    for claim in found:
        claim.update(assessment="deprecated", reviewed_at=day, notes=f"superseded: the page changed, see source {new}")
    return len(found)


def make_bundle(root: Path, operation_id: str, contents: dict[str, str], manifest: dict) -> dict:
    """One `ingest` transaction that replaces each file in `contents`, checked against the files as they are on disk."""
    return {
        "schema": "claude-obsidian.transaction.v1",
        "operation_id": operation_id,
        "operation_type": "ingest",
        "expected_hashes": {p: sha256((root / p).read_bytes()) for p in contents},
        "writes": [{"path": p, "mode": "replace", "content": c, "sha256": sha256(c)} for p, c in contents.items()],
        "address_requests": [],
        "source_manifest_updates": manifest,
        "workflow": {"catalogs": ["wiki/index.md"]},
    }


def source_of(root: Path, rel: str, digest: str) -> tuple[str | None, list[str]]:
    """The active source that holds exactly this text of the page (None when there is none) and the active sources that
    hold another text of it: a page in no source has neither."""
    sid, known = source_id(f".raw/captured/{digest}.md", digest), ingested(root).get(rel, set())
    return (sid if sid in known else None), sorted(known - {sid})


def changed_since(rel: str, others: list[str]) -> str:
    return f"{rel} changed since its source ({', '.join(others)}): --supersede {rel} records its new text"


def committed(root: Path, rel: str, rev: str) -> tuple[bytes, str]:
    """The page's text at `rev` and the short name of that commit; the page on disk has to be that text."""
    full = git(root, "rev-parse", "--verify", f"{rev}^{{commit}}").decode().strip()
    short = rev if re.fullmatch(r"[0-9a-f]{7,40}", rev) and full.startswith(rev) else full[:7]
    data = git(root, "show", f"{full}:{rel}")
    if (root / rel).read_bytes() != data:
        raise SystemExit(
            f"{rel} differs from its text at {short}: ingest the page as committed (--rev HEAD) or restore it"
        )
    return data, short


def plan_page(root: Path, rel: str, data: bytes, label: str, rev: str) -> dict:
    """Everything one page's ingest writes, from the vault as it is: the bundle and the pieces the output names."""
    text, digest, day = data.decode("utf-8"), sha256(data), now()[:10]
    stored, slug, meta = f".raw/captured/{digest}.md", PurePosixPath(rel).stem, frontmatter(text)
    source_ledger, claim_ledger = json.loads(read(root, SOURCE_LEDGER)), json.loads(read(root, CLAIM_LEDGER))
    source_ledger["generated_at"] = claim_ledger["generated_at"] = now()
    sid, claims = record_page(source_ledger, claim_ledger, rel, data, label, day)
    threads = open_threads(root, rel)
    link = link_of(rel)
    by = f", by {meta['by']}" if meta.get("by") else ""
    entry = (
        f"## [{day}] ingest | {label}\n- Source: `{stored}` (the page's text at {rev})\n- Page: [[{link}]]\n"
        f"- Claims: {len(claims)}; source `{sid}`\n"
    )
    hot = update_hot(
        read(root, "wiki/hot.md"),
        f"- [[{link}|{meta.get('title', slug)}]], decided {meta.get('decided', day)}{by}.",
        f"- Ingested {label}: {len(claims)} claims, source `{sid}`.",
        f"{now()}: ingest of {label}.",
        threads,
        day,
    )
    contents = {
        "wiki/index.md": read(root, "wiki/index.md"),
        rel: text,
        "wiki/log.md": add_to_log(read(root, "wiki/log.md"), entry, day),
        "wiki/hot.md": hot,
        SOURCE_LEDGER: json.dumps(source_ledger, indent=2, sort_keys=True) + "\n",
        CLAIM_LEDGER: json.dumps(claim_ledger, indent=2, sort_keys=True) + "\n",
    }
    manifest = {
        stored: {"hash": digest, "ingested_at": day, "source_id": sid, "pages_created": [], "pages_updated": [rel]}
    }
    return {
        "bundle": make_bundle(root, f"ingest-{slug}-{digest[:8]}", contents, manifest),
        "stored": stored,
        "source_id": sid,
        "claims": claims,
        "source": source_ledger["sources"][sid],
        "log_entry": entry,
        "hot_words": words(hot),
    }


def plan_refresh(
    root: Path,
    texts: dict[str, bytes],
    sids: dict[str, str],
    day: str,
    revised: dict[str, tuple[str, list[str]]] | None = None,
) -> dict:
    """The renewal of the pages' sources as one bundle: each source recorded again `day` and due REFRESH_DAYS later, the
    claims citing it reviewed `day`, the pages and the rest of both ledgers as they were. `texts` holds every page of the
    bundle. `revised` maps a page whose text changed to the label of its new text and the sources that hold its old one:
    the new text is recorded as a source with its claims, the old sources are superseded and their claims deprecated."""
    revised = revised or {}
    source_ledger, claim_ledger = json.loads(read(root, SOURCE_LEDGER)), json.loads(read(root, CLAIM_LEDGER))
    source_ledger["generated_at"] = claim_ledger["generated_at"] = now()
    due, lines, notes, manifest, new = days_after(day, REFRESH_DAYS), [], [], {}, []
    for rel, sid in sids.items():
        source_ledger["sources"][sid].update(retrieved_at=day, refresh_due=due)
        mine = [c for c in claim_ledger["claims"].values() if any(e["source_id"] == sid for e in c["evidence"])]
        for claim in mine:
            claim["reviewed_at"] = day
        lines.append(f"- [[{link_of(rel)}]]: {len(mine)} claims, source `{sid}`\n")
    for rel, (title, old) in revised.items():
        sid, claims = record_page(source_ledger, claim_ledger, rel, texts[rel], title, day, supersedes=old[0])
        deprecated, digest = retire_sources(source_ledger, claim_ledger, old, sid, day), sha256(texts[rel])
        manifest[f".raw/captured/{digest}.md"] = {
            "hash": digest,
            "ingested_at": day,
            "source_id": sid,
            "pages_created": [],
            "pages_updated": [rel],
        }
        notes.append(
            f"- Revised [[{link_of(rel)}]]: its new text is source `{sid}` ({len(claims)} claims, due {due}); "
            f"superseded {', '.join(f'`{o}`' for o in old)} ({deprecated} claims deprecated)\n"
        )
        new.append(sid)
    done = [(len(revised), "revision", "revised"), (len(sids), "refresh", "refreshed")]
    label = " and ".join(f"{noun} of {count(n, 'page')}" for n, noun, _ in done if n)
    change = "; ".join(f"{verb} {count(n, 'page')}" for n, _, verb in done if n).capitalize()
    entry = f"## [{day}] ingest | {label}\n" + "".join(notes)
    if sids:
        entry += f"- Sources recorded again, due {due}; the pages and their claims are as they were.\n" + "".join(lines)
    hot = update_hot(
        read(root, "wiki/hot.md"),
        None,
        f"- {change}: sources due {due}.",
        f"{now()}: {label}.",
        open_threads(root),
        day,
    )
    contents = {
        "wiki/index.md": read(root, "wiki/index.md"),
        **{rel: data.decode("utf-8") for rel, data in texts.items()},
        "wiki/log.md": add_to_log(read(root, "wiki/log.md"), entry, day),
        "wiki/hot.md": hot,
        SOURCE_LEDGER: json.dumps(source_ledger, indent=2, sort_keys=True) + "\n",
        CLAIM_LEDGER: json.dumps(claim_ledger, indent=2, sort_keys=True) + "\n",
    }
    operation_id = (
        f"ingest-{'revise' if revised else 'refresh'}-{day}-{sha256(' '.join(sorted([*sids.values(), *new])))[:8]}"
    )
    return {
        "bundle": make_bundle(root, operation_id, contents, manifest),
        "label": label,
        "pages": list(texts),
        "due": due,
        "log_entry": entry,
        "hot_words": words(hot),
    }


def stage(root: Path, rel: str, data: bytes, label: str, digest: str) -> str:
    """The page's text in inbox/, captured by the plugin into .raw/captured/; the copy in inbox/ goes either way."""
    stored = f".raw/captured/{digest}.md"
    if (
        root / stored
    ).is_file():  # captured before (a run that stopped after this step): content-addressed, so the same text
        return stored
    name = label.replace(".md@", "@").replace("/", "--") + ".md"
    copy = root / "inbox" / name
    if copy.exists() and copy.read_bytes() != data:
        raise SystemExit(f"inbox/{name} exists with other text: remove it or ingest it by hand")
    copy.write_bytes(data)
    try:
        args = [
            "capture",
            "apply",
            "--vault",
            str(root),
            "--operation-id",
            f"capture-{PurePosixPath(rel).stem}-{digest[:8]}",
            "--generated-at",
            now(),
            str(copy),
        ]
        approval = core(root, *args).get("approved_plan_sha256")
        done = core(root, *args, "--approved-plan-sha256", approval or "missing", "--apply")
        item = done["items"][0] if done.get("status") == "applied" and done.get("items") else {}
        if item.get("stored_path") != stored or item.get("source_identity") != digest:
            raise SystemExit(
                f"capture of {rel} stored {item.get('stored_path')}, not {stored}: {json.dumps(done)[:400]}"
            )
    finally:
        copy.unlink(missing_ok=True)
    return stored


def commit(root: Path, rel: str, plan: dict) -> list[str]:
    """workflow inspect, then workflow apply of the page's bundle; both stop on anything the gate finds."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "bundle.json"
        path.write_text(json.dumps(plan["bundle"]), encoding="utf-8")
        inspected = core(root, "workflow", "inspect", str(path), "--vault", str(root), ok=(0, 1))
        if not inspected.get("storage_valid") or not inspected.get("workflow_complete"):
            raise SystemExit(f"workflow inspect refused {rel}: {json.dumps(inspected.get('workflow_findings'))[:1200]}")
        applied = core(
            root,
            "workflow",
            "apply",
            str(path),
            "--vault",
            str(root),
            "--approved-plan-sha256",
            inspected["approval_sha256"],
        )
    return applied.get("changed_paths") or inspected["changed_paths"]


def lint(root: Path, rel: str) -> None:
    """The plugin's lint after the page; its tolerated categories are those of ops/adopt-obsidian.py. An answer without
    its counts stops the run: read as none, it would pass as a clean vault."""
    answer = core(root, "lint", "--vault", str(root), "--as-of", now()[:10], "--format", "json", ok=(0, 1))
    summary = answer.get("summary")
    counts = summary.get("category_counts") if isinstance(summary, dict) else None
    if not isinstance(counts, dict):
        shown = json.dumps(answer)[:300]
        raise SystemExit(f"lint after {rel}: the plugin's answer has no summary.category_counts: {shown}")
    errors = {kind: n for kind, n in counts.items() if n and kind not in ADOPT.LINT_TOLERATED}
    if errors:
        raise SystemExit(f"lint after {rel}: {errors}: {json.dumps({k: answer.get(k, [])[:3] for k in errors})[:900]}")


def sizes(bundle: dict) -> list[dict]:
    """What a bundle writes, for the dry run: the path, mode and size of each file."""
    return [{"path": w["path"], "mode": w["mode"], "bytes": len(w["content"].encode())} for w in bundle["writes"]]


def ingest(root: Path, rel: str, rev: str, dry_run: bool) -> None:
    data, short = committed(root, rel, rev)
    label = f"{rel.removeprefix('wiki/')}@{short}"
    digest = sha256(data)
    sid, others = source_of(root, rel, digest)
    if others:
        raise SystemExit(changed_since(rel, others))
    if sid is not None:
        due = recorded(root)[sid].get("refresh_due")
        print(f"skip {rel}: already ingested from this text (its source is due {due}; --refresh renews it)")
        return
    if dry_run:
        plan = plan_page(root, rel, data, label, short)
        view = {
            "operation_id": plan["bundle"]["operation_id"],
            "operation_type": "ingest",
            "capture": plan["stored"],
            "source_id": plan["source_id"],
            "source": plan["source"],
            "writes": sizes(plan["bundle"]),
            "claims": [{"anchor": c["anchor"], "lines": locator(c), "text": c["text"]} for c in plan["claims"]],
            "log_entry": plan["log_entry"],
            "hot_words": plan["hot_words"],
            "bundle": plan["bundle"],
        }
        print(json.dumps(view, indent=1, ensure_ascii=False))
        return
    stored = stage(root, rel, data, label, digest)
    plan = plan_page(root, rel, data, label, short)
    assert plan["stored"] == stored
    changed = commit(root, rel, plan)
    lint(root, rel)
    print(
        f"ingested {label}: {len(plan['claims'])} claims, source {plan['source_id']}, {len(changed)} paths, hot {plan['hot_words']} words"
    )


def refresh(root: Path, pages: list[str], rev: str, dry_run: bool, supersede: bool = False) -> None:
    """Renew the sources of the pages named and of every page due within the window, as one operation: the gate checks
    the whole ledger against today, so a source past its date has to be renewed in the same operation. A page whose text
    changed since its source is held back (its claims describe the old text); with `supersede` the pages named have their
    new text recorded instead, in the same operation. A held page past its date stops the run before anything is written:
    the gate would refuse the operation for it."""
    day = now()[:10]
    texts, sids, titles, revised, held = {}, {}, {}, {}, {}

    def hold(rel: str, reason: str) -> None:
        if rel in pages:  # a page named is refused, a page that is merely due waits
            raise SystemExit(reason)
        held[rel] = reason

    for rel in sorted({*pages, *(page for page, _ in due_pages(root, day))}):
        try:
            data, short = committed(root, rel, rev)
        except SystemExit as stop:  # a page edited and not committed waits like a changed one
            hold(rel, str(stop))
            continue
        current, others = source_of(root, rel, sha256(data))
        if current is None and not others:
            raise SystemExit(f"{rel} is in no source yet: ingest it first")
        if supersede and rel in pages:
            if not others:
                raise SystemExit(f"{rel} has nothing to supersede: its source holds this text")
            titles[rel] = f"{rel.removeprefix('wiki/')}@{short}"
            texts[rel], revised[rel] = data, (titles[rel], others)
        elif others:
            hold(rel, changed_since(rel, others))
        else:
            record = recorded(root)[current]
            if record.get("retrieved_at") == day and record.get("refresh_due") == days_after(day, REFRESH_DAYS):
                print(f"skip {rel}: its source was renewed today")
                continue
            texts[rel], sids[rel], titles[rel] = data, current, record["title"]
    if late := [reason for rel, reason in held.items() if lapsed(root, rel, day)]:
        raise SystemExit("a source past its date refuses every operation of the vault:\n" + "\n".join(late))
    for reason in held.values():
        print(f"held back: {reason}")
    if not texts:
        print("nothing to renew")
        return
    if dry_run:
        plan = plan_refresh(root, texts, sids, day, revised)
        view = {
            "operation_id": plan["bundle"]["operation_id"],
            "operation_type": "ingest",
            "pages": plan["pages"],
            "revised": list(revised),
            "held_back": held,
            "due": plan["due"],
            "writes": sizes(plan["bundle"]),
            "log_entry": plan["log_entry"],
            "hot_words": plan["hot_words"],
            "bundle": plan["bundle"],
        }
        print(json.dumps(view, indent=1, ensure_ascii=False))
        return
    for rel, data in texts.items():
        stage(root, rel, data, titles[rel], sha256(data))
    plan = plan_refresh(root, texts, sids, day, revised)
    changed = commit(root, plan["label"], plan)
    lint(root, plan["label"])
    print(f"{plan['label']}: sources due {plan['due']}, {len(changed)} paths, hot {plan['hot_words']} words")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pages", nargs="*", help="pages under wiki/, e.g. wiki/decisions/<slug>.md")
    parser.add_argument("--rev", default="HEAD", help="the commit whose text of each page is its source (default HEAD)")
    parser.add_argument("--dry-run", action="store_true", help="print each page's bundle and write nothing")
    parser.add_argument(
        "--all-decisions", action="store_true", help="list the wiki/decisions pages that are in no source yet"
    )
    parser.add_argument(
        "--due",
        action="store_true",
        help=f"list the pages whose source is due within {DUE_WINDOW_DAYS} days, or past it, with the date",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="renew the sources of the pages named and of the pages that are due, in one operation",
    )
    parser.add_argument(
        "--supersede",
        action="store_true",
        help="record the new text of the pages named, whose text changed since their source (the old source is superseded, "
        "its claims deprecated), and renew the pages that are due, in one operation",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.all_decisions:
        done = ingested(root)
        left = [p for p in decision_pages(root) if p not in done]
        if left:
            print("\n".join(left))
        return 0
    if args.due:
        for page, due in due_pages(root, now()[:10]):
            print(page, due)
        return 0
    if args.supersede and args.refresh:
        parser.error("--supersede renews the due pages too: give it without --refresh")
    if args.supersede and not args.pages:
        parser.error("--supersede takes the pages whose new text it records")
    if (args.pages or args.refresh or args.supersede) and (lost := missing(root)):
        raise SystemExit(gone(lost))
    if args.refresh or args.supersede:
        refresh(root, [page_rel(root, page) for page in args.pages], args.rev, args.dry_run, args.supersede)
        return 0
    if not args.pages:
        parser.error("give the pages to ingest, or --all-decisions, --due, --refresh or --supersede PAGE...")
    for rel in [page_rel(root, page) for page in args.pages]:
        ingest(root, rel, args.rev, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
