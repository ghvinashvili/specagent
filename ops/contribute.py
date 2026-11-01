#!/usr/bin/env python3
"""Offer one page of your vault to the public commons, after the owner's yes for that page (spec 11.4):
ops/contribute.py <vault-page> [<evidence-file> ...] [--dry-run]. The page is <vault_path>/decisions/global/<name>.md
(type: decision) or <vault_path>/concepts/<name>.md (type: concept), <name> in lowercase letters, digits and hyphens;
vault_path and commons_path come from docs/template/variables.yaml. The script derives the commons page (spec 11.2:
status candidate, the vault's own origin id, each evidence file as evidence/<origin>/<file>.md, licence CC-BY-4.0) and
refuses, naming the class: path, type, missing-field, private-path (context/, ~/, /home/, /Users/, docs/handoff/, a
memory file), source (neither a public URL nor submitted evidence), origin (a project named other than by this vault's
own origin id), rule-under-two-ids (status rule: a second origin confirms a page by its own pull request), secret (by
its label only), georgian, evidence (missing, not Markdown, or not UTF-8 text), exists, size, no-clone. The page, its
file name and its evidence are scanned, the bytes scanned are the bytes committed, and a refusal line shows a secret by
its label only. No flag skips a check. Then it commits the page and the evidence to the branch
contribute/<origin>/<name> of the clone at commons_path, leaving the clone's checkout as it was, pushes the branch and
opens the pull request with gh; without gh it prints the two commands. --dry-run prints the derived page and the
refusals and writes nothing."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # a fresh python3 has no PyYAML: run again under uv with it (ops/pyyaml_or_uv.py)
    import runpy

    runpy.run_path(str(Path(__file__).resolve().parent / "pyyaml_or_uv.py"))["ensure_pyyaml"]()
    raise

ROOT = Path(__file__).resolve().parent.parent
COMMONS_URL = "https://github.com/ghvinashvili/aftpro-commons.git"  # the public commons (spec 11.3); doctor.py too
OPTIONS = {"--dry-run"}  # the only one: no option skips a check
LICENCE = "CC-BY-4.0"  # the commons's SPDX id (spec question 14 (a))
FIELDS = ("title", "summary", "type", "scope", "status", "projects", "sources", "would_change_if", "licence", "updated")
KINDS = {
    "decisions/global": ("decision", "decision"),
    "concepts": ("concept", "lesson"),
}  # folder: its type, the commons'
ORIGIN = re.compile(r"[0-9a-f]{12}")  # drawn by ops/new-vault.py: secrets.token_hex(6)
NAME = re.compile(r"[a-z0-9][a-z0-9-]*\.md")  # a page's file name: it names the branch and the commons page
URL = re.compile(r"https?://[^\s<>()\[\]\"',]+")
PRIVATE = re.compile(
    r"(?<![\w.-])context/|~/|/home/|/Users/|docs/handoff/|\.claude/projects/|\.claude/agent-memory/|MEMORY\.md"
)
# the three blocks of 8.3.11 (U+10A0-U+10FF, U+1C90-U+1CBF, U+2D00-U+2D2F)
GEORGIAN = re.compile(r"[\u10a0-\u10ff\u1c90-\u1cbf\u2d00-\u2d2f]")
MAX_BYTES = 12 * 1024  # a commons page stays under 12 KB (spec 11.2)


def scalar(value: str | list) -> str:
    value = ", ".join(value) if isinstance(value, list) else value.strip()
    return value[1:-1] if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'" else value


def listed(value: str | list) -> list[str]:
    """A frontmatter list: a block list (already split), an inline [a, b], or one bare value."""
    if isinstance(value, list):
        return [scalar(item) for item in value]
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [scalar(part) for part in value[1:-1].split(",") if part.strip()]
    return [scalar(value)] if value else []


def frontmatter(text: str) -> tuple[dict, str]:
    """The `key: value` lines between the first two `---` (as the vault's check_pages.py reads them), with a block
    list (`  - x` lines) under a key; and the body after them."""
    head = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not head:
        return {}, text
    fields: dict = {}
    key = ""
    for line in head.group(1).splitlines():
        item = re.fullmatch(r"\s+-\s+(.*)", line)
        if item and key:
            fields[key] = [*(fields[key] if isinstance(fields[key], list) else []), item.group(1)]
        elif ":" in line and not line[:1].isspace():
            key, _, value = line.partition(":")
            key = key.strip()
            fields[key] = value.strip()
    return fields, text[head.end() :]


def git(repo: Path, *args: str, env: dict | None = None, data: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], input=data, capture_output=True, env=env, check=False)


def must(repo: Path, *args: str, env: dict | None = None, data: bytes | None = None) -> str:
    done = git(repo, *args, env=env, data=data)
    if done.returncode:
        raise SystemExit(f"git {args[0]} failed in {repo}: {done.stderr.decode(errors='replace').strip()}")
    return done.stdout.decode().strip()


def index_line(vault: Path, rel: str) -> str:
    """The summary on the page's line of the vault's INDEX.md (`- [<name>](<path>): <summary>`)."""
    index = vault / "INDEX.md"
    hit = re.search(rf"\]\({re.escape(rel)}\):\s*(.+)", index.read_text(encoding="utf-8")) if index.is_file() else None
    return hit.group(1).strip() if hit else ""


def vault_origin(vault: Path) -> str:
    readme = vault / "README.md"
    value = scalar(frontmatter(readme.read_text(encoding="utf-8"))[0].get("origin", "")) if readme.is_file() else ""
    return value if ORIGIN.fullmatch(value) else ""


def utf8_text(data: bytes) -> bool:
    """Bytes that decode as UTF-8 and hold no NUL: another encoding would pass the scan and publish what it hides."""
    try:
        return "\0" not in data.decode("utf-8")
    except UnicodeDecodeError:
        return False


def take_evidence(args: list[str], found: list) -> dict[Path, bytes]:
    """The evidence files with their bytes, read once: the bytes scanned are the bytes committed."""
    kept: dict[Path, bytes] = {}
    for arg in args:
        path = Path(arg).expanduser().resolve()
        if not path.is_file():
            found.append(("evidence", f"{arg} is not a file"))
        elif path.suffix != ".md":
            found.append(("evidence", f"{arg}: evidence is a measurement written in Markdown (.md)"))
        elif {"context", ".claude"} & set(path.parts) or "/docs/handoff/" in path.as_posix():
            found.append(
                ("private-path", f"{arg} lies under context/, .claude/ or docs/handoff/: submit a public copy")
            )
        elif path.name in {kept_path.name for kept_path in kept}:
            found.append(("evidence", f"two evidence files are named {path.name}"))
        else:
            data = path.read_bytes()
            if utf8_text(data):
                kept[path] = data
            else:
                found.append(("evidence", f"{arg} is not UTF-8 text: what is scanned is what is published"))
    return kept


def scan(label: str, text: str, patterns: dict, found: list) -> None:
    """Private paths (outside URLs), secrets (by label only) and letters of the refused blocks in a text the commons would publish."""
    for hit in sorted({m.group(0) for m in PRIVATE.finditer(URL.sub("", text))}):
        found.append(("private-path", f"{label} names `{hit}`"))
    for name, pattern in patterns.items():
        if pattern.search(text):
            found.append(("secret", f"{label} matches the secret pattern `{name}`"))
    if GEORGIAN.search(text):
        found.append(("georgian", f"{label} holds a letter of a refused block; the commons is English"))


def masked(text: str, patterns: dict) -> str:
    """`text` with each secret-pattern hit replaced by the pattern's label: a refusal line shows no secret."""
    for label, pattern in patterns.items():
        text = pattern.sub(f"<{label}>", text)
    return text


def examine(page: Path, evidence: list[str], vault: Path, clone: Path, patterns: dict) -> tuple[list, dict]:
    """Every refusal of the page and its evidence, and what the commit needs (nothing when the path is refused)."""
    found: list[tuple[str, str]] = []
    page = page.expanduser().resolve()
    folder = page.parent.relative_to(vault).as_posix() if page.parent.is_relative_to(vault) else ""
    if folder not in KINDS or page.suffix != ".md" or not page.is_file():
        found.append(("path", f"{page}: only {vault}/decisions/global/<name>.md and {vault}/concepts/<name>.md go"))
        return found, {}
    if not NAME.fullmatch(page.name):  # the name is never echoed: it may hold a secret
        found.append(("path", "the page's file name is not lowercase letters, digits and hyphens: it names the branch"))
    scan("the page's file name", page.name, patterns, found)
    want, kind = KINDS[folder]
    fields, body = frontmatter(page.read_text(encoding="utf-8"))
    values = {name: scalar(fields.get(name, "")) for name in FIELDS if name not in ("projects", "sources", "licence")}
    values["summary"] = values["summary"] or index_line(vault, f"{folder}/{page.name}")
    if values["type"] and values["type"] != want:
        found.append(("type", f"type `{values['type']}` under {folder}/, which holds type: {want}"))
    for name, value in values.items():
        if not value:
            found.append(
                ("missing-field", f"`{name}`" + (" (frontmatter or the INDEX.md line)" if name == "summary" else ""))
            )
    own = vault_origin(vault)
    if not own:
        found.append(
            ("origin", f"{vault}/README.md has no `origin:` id in its frontmatter (ops/new-vault.py draws one)")
        )
    for entry in listed(fields.get("projects", "")):
        if not ORIGIN.fullmatch(entry):
            found.append(
                ("origin", f"projects entry `{entry}` is not an origin id (12 hex digits); a project is never named")
            )
        elif entry != own:
            why = "a page goes under its own vault's id; another origin confirms it by its own pull request"
            found.append(("origin", f"projects entry `{entry}` is not this vault's origin id: {why}"))
    projects = [own] if own else []
    if values["status"] == "rule":
        why = "a page enters as a candidate under one origin id; a second origin confirms it by its own pull request"
        found.append(("rule-under-two-ids", f"status rule: {why}"))
    kept = take_evidence(evidence, found)
    sources = []
    for entry in listed(fields.get("sources", "")):
        if URL.fullmatch(entry):
            sources.append(entry)
        elif Path(entry).name in {path.name for path in kept}:
            continue  # its public copy is submitted: it is listed below as evidence/<origin>/<name>
        elif PRIVATE.search(entry):
            found.append(("private-path", f"sources entry `{entry}` has no public copy among the evidence"))
        else:
            found.append(("source", f"sources entry `{entry}` is neither a public URL nor a submitted evidence file"))
    sources += [f"evidence/{own}/{path.name}" for path in kept]
    if not sources:
        found.append(("missing-field", "`sources`: no public URL and no evidence"))
    meta = {**values, "type": kind, "status": "candidate"}
    meta |= {"projects": projects, "sources": sources, "licence": LICENCE}
    shown = [f"[{path.name}](../evidence/{own}/{path.name})" for path in kept] + [
        s for s in sources if URL.fullmatch(s)
    ]
    text = "---\n" + "".join(f"{key}: {json.dumps(meta[key], ensure_ascii=False)}\n" for key in FIELDS) + "---\n"
    text += body.rstrip("\n") + "\n" + (f"\n## Evidence\n\n- `{own}`: {', '.join(shown)}\n" if shown else "")
    scan("the derived page", text, patterns, found)
    for path, data in kept.items():
        scan(f"the evidence {path.name}", data.decode("utf-8"), patterns, found)
    if len(text.encode("utf-8")) > MAX_BYTES:
        found.append(
            ("size", f"the derived page has {len(text.encode('utf-8'))} bytes; a commons page stays under 12 KB")
        )
    name = page.stem
    branch = f"contribute/{own}/{name}"
    if (clone / ".git").is_dir():
        if git(clone, "cat-file", "-e", f"HEAD:pages/{name}.md").returncode == 0:
            found.append(("exists", f"pages/{name}.md is in the commons already; confirming it is the review's work"))
        if git(clone, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}").returncode == 0:
            found.append(("exists", f"the branch {branch} exists in {clone}: push it, or delete it (git branch -D)"))
    files = {f"pages/{name}.md": text.encode("utf-8"), **{f"evidence/{own}/{p.name}": data for p, data in kept.items()}}
    pr_body = (
        f"{meta['summary']}\n\nstatus: {meta['status']}; projects: {', '.join(projects)}; licence: {LICENCE}\n"
        f"would change if: {meta['would_change_if']}\n\nOffered with ops/contribute.py; its checks passed in code."
    )
    title = f"{kind}: {meta['title']}"
    return found, {"text": text, "files": files, "branch": branch, "title": title, "body": pr_body}


def commit(clone: Path, files: dict[str, bytes], message: str) -> str:
    """A commit of `files` on top of the clone's HEAD, built in an index of its own: the clone's checkout and index stay
    as they were."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        must(clone, "read-tree", "HEAD", env=env)
        for path, data in files.items():
            blob = must(clone, "hash-object", "-w", "--stdin", data=data)
            must(clone, "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = must(clone, "write-tree", env=env)
        return must(clone, "commit-tree", tree, "-p", "HEAD", "-m", message)


def submit(clone: Path, plan: dict) -> int:
    branch = plan["branch"]
    must(clone, "branch", branch, commit(clone, plan["files"], plan["title"]))
    pr = ["gh", "pr", "create", "--head", branch, "--title", plan["title"], "--body", plan["body"]]
    steps = [
        f"  git -C {shlex.quote(str(clone))} push -u origin {branch}",
        f"  cd {shlex.quote(str(clone))} && {shlex.join(pr)}",
    ]
    if shutil.which("gh") is None:
        print(
            f"committed the branch {branch} in {clone}; gh is not on PATH, so these two steps are yours:",
            *steps,
            sep="\n",
        )
        return 0
    push = git(clone, "push", "-u", "origin", branch)
    if push.returncode:
        print(push.stderr.decode(errors="replace").strip())
        print(
            f"the push was refused; without write access, fork the commons (in {clone}: gh repo fork --remote), then:"
        )
        print(*steps, sep="\n")
        return 1
    opened = subprocess.run(pr, cwd=clone, capture_output=True, text=True, check=False)
    print((opened.stdout or opened.stderr).strip())
    return opened.returncode


def main(argv: list[str]) -> int:
    flags = {arg for arg in argv[1:] if arg.startswith("-")}
    paths = [arg for arg in argv[1:] if not arg.startswith("-")]
    unknown = sorted(flags - OPTIONS - {"-h", "--help"})
    if unknown:
        print(f"unknown option {', '.join(unknown)}: no option skips a check (the only one is --dry-run)")
        return 2
    if flags & {"-h", "--help"} or not paths:
        print(__doc__)
        return 0 if paths or flags else 2
    spec = yaml.safe_load((ROOT / "docs" / "template" / "variables.yaml").read_text(encoding="utf-8"))
    given = {v["name"]: Path(v["default"]).expanduser() for v in spec["variables"]}
    vault, clone = given["vault_path"].resolve(), given["commons_path"]
    sys.path.insert(0, str(ROOT / "templates" / "vault" / "ops"))
    sys.dont_write_bytecode = True  # the form's folder stays as git has it
    try:
        from collect_memory import PATTERNS  # the vault's own secret filter: one filter on both ends
    except ImportError:
        print(f"the secret filter {ROOT}/templates/vault/ops/collect_memory.py is missing; nothing checked")
        return 2
    dry = "--dry-run" in flags
    found, plan = examine(Path(paths[0]), paths[1:], vault, clone, PATTERNS)
    if not (clone / ".git").is_dir():
        missing = f"no clone of the commons at {clone}: git clone {COMMONS_URL} {clone}"
        if dry:
            print(missing)
        else:
            found.append(("no-clone", missing))
    if plan and dry:
        print(
            "(the derived page is not shown: it holds a secret)"
            if any(k == "secret" for k, _ in found)
            else plan["text"]
        )
    for kind, detail in found:
        print(f"refused ({kind}): {masked(detail, PATTERNS)}")
    if found:
        print(f"{len(found)} refusal(s); nothing written")
        return 1
    if dry:
        print(f"dry run: nothing written; the branch would be {plan['branch']}")
        return 0
    return submit(clone, plan)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
