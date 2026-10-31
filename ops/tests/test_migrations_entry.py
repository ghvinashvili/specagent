"""R7 (spec 006): a change to a template-owned path is named in the `## Unreleased` entry of
docs/template/MIGRATIONS.md, in the same commit.

The check is state based: from the commit that last set docs/template/VERSION (the release the entry is written after)
to the working tree, every path that changed (committed, staged, unstaged, untracked or deleted) is named in the entry,
as the path or as a folder of it ending in `/`. Exempt: the migrations file itself, CHANGELOG.md, the VERSION file, the
`omit:` prefixes of docs/template/variables.yaml and the template's generated records (.raw/, wiki/meta/, wiki/index.md,
wiki/log.md, wiki/hot.md). A release moves the entry under its number; the entry of the new VERSION must then name the
paths. A project's checkout (it keeps the template's README at docs/template/README.md) and a checkout with no history
are skipped.

`unnamed()` is that check. `unrecorded()` is the same rule for each commit (V3): every commit from the release to HEAD
that changes a template-owned path must change the newest entry of the migrations file (its first `## ` section: the
line it adds) or have its short sha (7 to 40 letters of it) written in the entry, as the back-fill lines do for a commit
made before its line existed; the uncommitted changes are the commit in the making and are held to the same rule. A
merge commit is not asked: its parents are. `problems()` returns both lists.

It is a test and not a flag of `harness version-check`: .github/workflows/evals.yml is copied to every project and runs
that command there, where the template's migration lines are not the project's to write.

  uv run pytest -q ops/tests/test_migrations_entry.py
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = "docs/template/MIGRATIONS.md"
VERSION = "docs/template/VERSION"
VARIABLES = "docs/template/variables.yaml"
KEPT_README = "docs/template/README.md"  # where a project keeps the template's README (ops/new-project.py)
EXEMPT = (MIGRATIONS, VERSION, "CHANGELOG.md", ".raw/", "wiki/meta/", "wiki/index.md", "wiki/log.md", "wiki/hot.md")
LEAKED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX", "GIT_OBJECT_DIRECTORY")
ENTRY_LINE = re.compile(r"- (\d{4}-\d{2}-\d{2}, |Checks: |Breaks active runs: )")
SHA = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,40}(?![0-9A-Za-z])")  # a commit named in a line of the entry


def clean_env() -> dict[str, str]:
    """The environment without the variables a running git hook leaks, and with no optional lock or index refresh."""
    env = {k: v for k, v in os.environ.items() if k not in LEAKED and not k.startswith("GIT_ALTERNATE")}
    return {**env, "GIT_OPTIONAL_LOCKS": "0"}


def git(root: Path, *args: str) -> str | None:
    """The output of one git command in `root`, or None when git fails (no git, no repository, an unknown commit)."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True, env=clean_env(), timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def release_base(root: Path) -> str | None:
    """The commit that last set docs/template/VERSION."""
    out = git(root, "log", "-1", "--format=%H", "--", VERSION)
    return (out or "").strip() or None


def skipped(root: Path) -> str | None:
    """Why the check does not apply to this checkout, or None."""
    if (root / KEPT_README).exists():
        return "a project's checkout: the migration entries are the template's to write"
    if release_base(root) is None:
        return "no history of docs/template/VERSION here (not a git checkout)"
    return None


def changed(root: Path, base: str) -> list[str] | None:
    """The paths that differ from `base` in the working tree, deleted ones and untracked ones included."""
    tracked = git(root, "diff", "-z", "--name-only", "--no-renames", base)
    untracked = git(root, "ls-files", "-z", "--others", "--exclude-standard")
    if tracked is None or untracked is None:
        return None
    return sorted({path for path in (tracked + untracked).split("\0") if path})


def exempt_prefixes(root: Path) -> tuple[str, ...]:
    """The paths that need no line: the exempt ones, and what docs/template/variables.yaml never copies (`omit:`)."""
    path = root / VARIABLES
    omit = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("omit") or [] if path.is_file() else []
    return (*EXEMPT, *omit)


def entry_of(text: str, heading: str) -> str | None:
    """The body of the `## <heading>` entry of the migrations file, or None."""
    found = re.search(rf"(?ms)^## {re.escape(heading)}(?![\w.])[^\n]*(?:\n|\Z)(.*?)(?=^## |\Z)", text)
    return found.group(1) if found else None


def names(entry: str, path: str) -> bool:
    """True when the entry writes `path`, or a folder above it ending in `/`, as a whole token."""
    parts = path.split("/")
    folders = ["/".join(parts[:i]) + "/" for i in range(1, len(parts))]
    left = r"(?<![\w./-])"
    if any(re.search(left + re.escape(folder) + r"(?![\w.-])", entry) for folder in folders):
        return True
    return re.search(left + re.escape(path) + r"(?![\w/-]|\.\w)", entry) is not None


def checked_entry(root: Path, base: str) -> tuple[str, str | None]:
    """The heading of the entry that must hold the lines, and its body (None when the file has no such entry)."""
    heading = "Unreleased"
    at_base = git(root, "show", f"{base}:{VERSION}")
    now = (root / VERSION).read_text(encoding="utf-8").strip() if (root / VERSION).is_file() else ""
    if at_base is not None and now and now != at_base.strip():
        heading = now  # a release in the making: its entry is the one that names the paths
    file = root / MIGRATIONS
    return heading, entry_of(file.read_text(encoding="utf-8"), heading) if file.is_file() else None


def first_entry(text: str | None) -> str | None:
    """The newest entry of the migrations file, heading included: its first `## ` section."""
    found = re.search(r"(?ms)^## .*?(?=^## |\Z)", text or "")
    return found.group(0) if found else None


def entry_changed(before: str | None, after: str | None) -> bool:
    """True when the newest entry of the migrations file differs between two states of the file."""
    now = first_entry(after)
    return now is not None and now != first_entry(before)


def shown_paths(paths: list[str]) -> str:
    return ", ".join(paths[:4]) + (f", ... ({len(paths)} paths)" if len(paths) > 4 else "")


def unrecorded(root: Path) -> list[str]:
    """The commits since the release that change a template-owned path and neither change the newest entry nor are
    named in it by their short sha, then the uncommitted changes (the commit in the making) held to the same rule."""
    base = release_base(root)
    if base is None:
        return []  # `unnamed` says why
    listed = git(root, "log", "--no-merges", "--reverse", "--format=%H %s", f"{base}..HEAD")
    pending = changed(root, "HEAD")
    if listed is None or pending is None:
        return [f"git could not list the changes since the release commit {base[:7]}"]
    heading, entry = checked_entry(root, base)
    named = SHA.findall(entry or "")
    prefixes = exempt_prefixes(root)
    adds_no_line = f"adds no line to the `## {heading}` entry of {MIGRATIONS}"
    found = []
    for line in listed.splitlines():
        sha, _, subject = line.partition(" ")
        out = git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", "--no-renames", sha)
        if out is None:
            found.append(f"git could not read the paths of commit {sha[:7]}")
            continue
        paths = [path for path in out.split("\0") if path]
        owned = [path for path in paths if not path.startswith(prefixes)]
        if not owned or any(sha.startswith(token) for token in named):
            continue
        if MIGRATIONS in paths and entry_changed(
            git(root, "show", f"{sha}^:{MIGRATIONS}"), git(root, "show", f"{sha}:{MIGRATIONS}")
        ):
            continue
        found.append(
            f"{sha[:7]} {subject}: changes {shown_paths(owned)} and {adds_no_line}; add the line in the commit"
            " (a commit already made is named by its short sha in the entry)"
        )
    owned = [path for path in pending if not path.startswith(prefixes)]
    if owned:
        file = root / MIGRATIONS
        after = file.read_text(encoding="utf-8") if file.is_file() else None
        if not entry_changed(git(root, "show", f"HEAD:{MIGRATIONS}"), after):
            found.append(
                f"uncommitted changes to {shown_paths(owned)} add no line to the `## {heading}` entry of"
                f" {MIGRATIONS}: the commit in the making carries its line"
            )
    return found


def unnamed(root: Path) -> list[str]:
    """What the migration entry fails to name: one line per path, or one line when the entry itself is missing."""
    base = release_base(root)
    if base is None:
        return [f"{VERSION} has no commit here: git cannot say which release the entry is written after"]
    paths = changed(root, base)
    if paths is None:
        return [f"git could not compare the working tree with the release commit {base[:7]}"]
    prefixes = exempt_prefixes(root)
    owned = [path for path in paths if not path.startswith(prefixes)]
    if not owned:
        return []
    heading, entry = checked_entry(root, base)
    if entry is None:
        shown = ", ".join(owned[:6]) + (", ..." if len(owned) > 6 else "")
        missing = (
            f"{MIGRATIONS} has no `## {heading}` entry, and {len(owned)} template-owned path(s) changed since the"
            f" release commit {base[:7]}: {shown}"
        )
        return [missing]
    fix = "add a line with the date, the path (or its folder ending in `/`) and the step a project takes"
    return [
        f"{path}: changed since the release commit {base[:7]} and not named in the `## {heading}` entry of"
        f" {MIGRATIONS}; {fix}"
        for path in owned
        if not names(entry, path)
    ]


def problems(root: Path) -> list[str]:
    """Everything the rule refuses: a path the entry does not name, then a commit that adds no line."""
    return [*unnamed(root), *unrecorded(root)]


def format_problems(entry: str) -> list[str]:
    """A line of the entry starts with a date, `Checks:` or `Breaks active runs:`; a continuation is indented."""
    return [
        f"line {n} of the entry: {line[:70]}"
        for n, line in enumerate(entry.splitlines(), 1)
        if line.strip() and not line.startswith(" ") and not ENTRY_LINE.match(line)
    ]


# ---- the template itself ----


def test_the_template_names_every_change_since_its_release_in_its_migration_entry():
    reason = skipped(ROOT)
    if reason:
        pytest.skip(reason)
    found = unnamed(ROOT)
    assert found == [], "\n".join(found)


def test_the_unreleased_entry_is_made_of_dated_lines():
    entry = entry_of((ROOT / MIGRATIONS).read_text(encoding="utf-8"), "Unreleased")
    if entry is None:
        pytest.skip("no Unreleased entry: the last commit is a release")
    assert format_problems(entry) == []


def test_the_head_of_the_migrations_file_states_the_rule():
    head = " ".join((ROOT / MIGRATIONS).read_text(encoding="utf-8").split("\n## ", 1)[0].split())  # lines unwrapped
    for words in (
        "`## Unreleased` entry",
        "in the same commit",
        "ops/tests/test_migrations_entry.py",
        "adds no line",
        "short sha",
    ):
        assert words in head, words


# ---- the check, on small repositories ----

HEAD = "# Template migrations\n\nOne entry per template version, newest first.\n\n"
OLD = "## 1.0.0\n- First version. Nothing to migrate.\n"
TOOL = "- 2026-10-31, the tool: `ops/tool.py`. Copy it.\n"


def sealed_env() -> dict[str, str]:
    """A git identity and no global or system configuration: the result does not depend on this machine's git setup."""
    who = {
        f"GIT_{role}_{key}": val for role in ("AUTHOR", "COMMITTER") for key, val in (("NAME", "t"), ("EMAIL", "t@t"))
    }
    return {**clean_env(), **who, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def setup(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], env=sealed_env(), check=True, capture_output=True, timeout=60)


def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")


def commit(root: Path, message: str) -> None:
    setup(root, "add", "-A")
    setup(root, "commit", "-q", "-m", message)


def released(tmp_path: Path, lines: str | None = "") -> Path:
    """A repository whose last commit sets 1.0.0, with an `## Unreleased` entry holding `lines` (None: no entry)."""
    root = tmp_path / "repo"
    root.mkdir()
    entry = "" if lines is None else f"## Unreleased (after 1.0.0)\n{lines}\n"
    write(
        root,
        {
            VERSION: "1.0.0\n",
            MIGRATIONS: HEAD + entry + OLD,
            VARIABLES: "omit:   # never copied\n  - design/\n",
            "ops/tool.py": "x = 1\n",
            "design/idea.md": "# idea\n",
        },
    )
    setup(root, "init", "-q")
    commit(root, "release 1.0.0")
    return root


def test_a_changed_path_the_entry_does_not_name_is_refused(tmp_path: Path):
    root = released(tmp_path, "- 2026-10-31, the docs: `docs/other.md`. Copy it.\n")
    write(root, {"ops/tool.py": "x = 2\n"})
    commit(root, "change the tool")
    (found,) = unnamed(root)
    assert found.startswith("ops/tool.py: changed since the release commit"), found
    assert "not named in the `## Unreleased` entry of docs/template/MIGRATIONS.md" in found


@pytest.mark.parametrize(
    "naming", ["`ops/tool.py`", "`ops/`", "`ops/**`", "the folder ops/ and more", "(`ops/tool.py`)"]
)
def test_a_path_named_by_itself_or_by_a_folder_above_it_passes(tmp_path: Path, naming: str):
    root = released(tmp_path, f"- 2026-10-31, the tool: {naming}. Copy it.\n")
    write(root, {"ops/tool.py": "x = 2\n"})
    commit(root, "change the tool")
    assert unnamed(root) == []


@pytest.mark.parametrize(
    "naming",
    [
        "`templates/vault/ops/tool.py`",
        "`other/ops/`",
        "`ops/tool.pyc`",
        "`ops/tool.py.bak`",
        "`ops/tool/`",
        "`ops/tools.py`",
    ],
)
def test_a_longer_path_or_a_lookalike_does_not_name_a_path(tmp_path: Path, naming: str):
    root = released(tmp_path, f"- 2026-10-31, the tool: {naming}. Copy it.\n")
    write(root, {"ops/tool.py": "x = 2\n"})
    commit(root, "change the tool")
    assert len(unnamed(root)) == 1


def test_a_mention_of_a_path_below_a_folder_does_not_name_the_folder(tmp_path: Path):
    root = released(tmp_path, "- 2026-10-31, the docs: `docs/other.md`. Copy it.\n")
    write(root, {"docs/new.md": "# new\n"})
    commit(root, "add a doc")
    (found,) = unnamed(root)
    assert found.startswith("docs/new.md: changed since")


def test_a_missing_unreleased_entry_is_refused(tmp_path: Path):
    root = released(tmp_path, None)
    assert unnamed(root) == []  # nothing changed since the release
    write(root, {"ops/tool.py": "x = 2\n"})
    commit(root, "change the tool")
    (found,) = unnamed(root)
    assert "has no `## Unreleased` entry" in found and "ops/tool.py" in found


@pytest.mark.parametrize("how", ["unstaged", "staged", "untracked", "deleted", "renamed"])
def test_a_change_not_yet_committed_counts(tmp_path: Path, how: str):
    root = released(tmp_path, "- 2026-10-31, the docs: `docs/other.md`. Copy it.\n")
    if how == "untracked":
        write(root, {"ops/new.py": "y = 1\n"})
    elif how == "deleted":
        (root / "ops" / "tool.py").unlink()
    elif how == "renamed":
        setup(root, "mv", "ops/tool.py", "ops/tool2.py")
    else:
        write(root, {"ops/tool.py": "x = 2\n"})
        if how == "staged":
            setup(root, "add", "ops/tool.py")
    found = unnamed(root)
    assert len(found) == (2 if how == "renamed" else 1), found  # a rename is a deleted path and a new one


def test_exempt_paths_need_no_line_but_the_templates_other_records_do(tmp_path: Path):
    root = released(tmp_path, "- 2026-10-31, the docs: `docs/other.md`. Copy it.\n")
    write(
        root,
        {
            ".raw/captured/a.md": "a\n",
            ".raw/.manifest.json": "{}\n",
            "wiki/meta/ledgers/claim-ledger.json": "{}\n",
            "wiki/log.md": "log\n",
            "wiki/hot.md": "hot\n",
            "wiki/index.md": "index\n",
            "CHANGELOG.md": "# Changelog\n",
            "design/idea.md": "# changed\n",  # `omit:` in the repository's own variables.yaml
        },
    )
    commit(root, "records and an omitted folder")
    assert unnamed(root) == []
    write(root, {"wiki/decisions/x.md": "x\n", "specs/007/spec.md": "s\n", "drafts/y.md": "y\n"})
    commit(root, "a decision page, a spec and a draft")
    assert sorted(line.split(":")[0] for line in unnamed(root)) == [
        "drafts/y.md",
        "specs/007/spec.md",
        "wiki/decisions/x.md",
    ]


def test_the_omit_list_is_the_one_in_variables_yaml(tmp_path: Path):
    root = released(tmp_path, "- 2026-10-31, the variables: `docs/template/variables.yaml`. Merge it by hand.\n")
    write(root, {"design/idea.md": "# changed\n", "drafts/y.md": "y\n"})
    commit(root, "two folders")
    assert [line.split(":")[0] for line in unnamed(root)] == ["drafts/y.md"]
    write(root, {VARIABLES: "omit:\n  - drafts/\n"})
    commit(root, "omit the drafts")
    assert [line.split(":")[0] for line in unnamed(root)] == ["design/idea.md"]


def test_a_release_moves_the_entry_and_the_new_entry_names_the_paths(tmp_path: Path):
    root = released(tmp_path, TOOL)
    text = (root / MIGRATIONS).read_text(encoding="utf-8")
    write(root, {"ops/tool.py": "x = 2\n", VERSION: "1.1.0\n"})
    (found,) = unnamed(root)  # the version moved, the entry is still called Unreleased
    assert "has no `## 1.1.0` entry" in found, found
    write(root, {MIGRATIONS: text.replace("## Unreleased (after 1.0.0)", "## 1.1.0")})
    assert unnamed(root) == []
    write(root, {MIGRATIONS: text.replace("## Unreleased (after 1.0.0)", "## 1.1.0").replace(TOOL, "- nothing\n")})
    (found,) = unnamed(root)
    assert found.startswith("ops/tool.py: changed since") and "not named in the `## 1.1.0` entry" in found, found


def test_after_a_release_nothing_is_asked_until_the_next_change_and_then_an_unreleased_entry(tmp_path: Path):
    root = released(tmp_path, TOOL)
    text = (root / MIGRATIONS).read_text(encoding="utf-8")
    entry = text.replace("## Unreleased (after 1.0.0)", "## 1.1.0")
    write(root, {"ops/tool.py": "x = 2\n", VERSION: "1.1.0\n", MIGRATIONS: entry})
    commit(root, "release 1.1.0")
    assert unnamed(root) == []  # the base is the release commit, and no Unreleased entry is asked for
    write(root, {"ops/tool.py": "x = 3\n"})
    commit(root, "change the tool again")
    (found,) = unnamed(root)  # the 1.1.0 entry names the tool, and it must not stand in for the next one
    assert "has no `## Unreleased` entry" in found, found
    unreleased = "## Unreleased (after 1.1.0)\n" + TOOL.replace("2026-10-31", "2026-11-01") + "\n"
    write(root, {MIGRATIONS: entry.replace("## 1.1.0", unreleased + "## 1.1.0")})
    assert unnamed(root) == []


def test_a_project_or_a_folder_without_history_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "GIT_CEILING_DIRECTORIES", str(tmp_path)
    )  # a folder here is not looked for in a repository above
    root = released(tmp_path, "")
    assert skipped(root) is None
    write(root, {KEPT_README: "# The template\n"})
    assert "a project's checkout" in (skipped(root) or "")
    bare = tmp_path / "bare"
    bare.mkdir()
    write(bare, {VERSION: "1.0.0\n"})
    assert "not a git checkout" in (skipped(bare) or "")
    empty = tmp_path / "empty"
    empty.mkdir()
    setup(empty, "init", "-q")
    assert "no history" in (skipped(empty) or "")


def test_a_line_of_the_entry_starts_with_a_date_or_is_a_closing_line():
    good = "- 2026-10-31, the tool: `ops/tool.py`.\n  a continuation, indented\n- Checks: `uv run pytest -q`\n- Breaks active runs: no.\n"
    assert format_problems(good) == []
    bad = "- the tool changed\n2026-10-31 the tool\n- 2026-10-3, the tool\n"
    assert len(format_problems(bad)) == 3


# ---- a commit carries its own line (V3) ----

AGAIN = "- 2026-11-01, the tool again: `ops/tool.py`. Copy it.\n"


def head_sha(root: Path) -> str:
    return (git(root, "rev-parse", "HEAD") or "").strip()


def with_line(root: Path, line: str) -> str:
    """The migrations file of `root` with `line` added after the tool's line in the Unreleased entry."""
    text = (root / MIGRATIONS).read_text(encoding="utf-8")
    assert TOOL in text
    return text.replace(TOOL, TOOL + line)


def test_a_second_commit_on_a_path_the_entry_already_names_needs_its_own_line(tmp_path: Path):
    root = released(tmp_path, TOOL)  # the entry names ops/tool.py since the release
    write(root, {"ops/tool.py": "x = 2\n"})
    commit(root, "change the tool again")
    (found,) = problems(root)
    assert found.startswith(f"{head_sha(root)[:7]} change the tool again: changes ops/tool.py"), found
    assert "adds no line to the `## Unreleased` entry of docs/template/MIGRATIONS.md" in found, found


def test_a_commit_that_adds_its_line_to_the_entry_passes(tmp_path: Path):
    root = released(tmp_path, TOOL)
    write(root, {"ops/tool.py": "x = 2\n", MIGRATIONS: with_line(root, AGAIN)})
    commit(root, "change the tool again")
    assert problems(root) == []


@pytest.mark.parametrize("edit", ["the head", "an older entry"])
def test_a_commit_that_edits_the_migrations_file_but_not_the_newest_entry_is_refused(tmp_path: Path, edit: str):
    root = released(tmp_path, TOOL)
    text = (root / MIGRATIONS).read_text(encoding="utf-8")
    old, new = ("newest first.", "newest first, always.") if edit == "the head" else ("First version.", "The first.")
    assert old in text
    write(root, {"ops/tool.py": "x = 2\n", MIGRATIONS: text.replace(old, new)})
    commit(root, "change the tool and reword the file")
    (found,) = problems(root)
    assert "adds no line to the `## Unreleased` entry" in found, found


@pytest.mark.parametrize(
    ("naming", "passes"), [("short sha", True), ("full sha", True), ("six letters", False), ("another sha", False)]
)
def test_a_past_commit_passes_when_the_entry_names_its_sha(tmp_path: Path, naming: str, passes: bool):
    root = released(tmp_path, TOOL)
    write(root, {"ops/tool.py": "x = 2\n"})
    commit(root, "change the tool again")
    sha = head_sha(root)
    token = {"short sha": sha[:7], "full sha": sha, "six letters": sha[:6], "another sha": "0123456"}[naming]
    write(root, {MIGRATIONS: with_line(root, f"- 2026-11-01, wording fix of the tool ({token}). Nothing to do.\n")})
    assert (problems(root) == []) is passes, problems(root)


@pytest.mark.parametrize("how", ["unstaged", "staged", "untracked", "deleted"])
def test_an_uncommitted_change_is_the_commit_in_the_making_and_needs_its_line(tmp_path: Path, how: str):
    root = released(tmp_path, "- 2026-10-31, the tool: `ops/`. Copy it.\n")  # the entry names the folder
    if how == "untracked":
        write(root, {"ops/new.py": "y = 1\n"})
    elif how == "deleted":
        (root / "ops" / "tool.py").unlink()
    else:
        write(root, {"ops/tool.py": "x = 2\n"})
        if how == "staged":
            setup(root, "add", "ops/tool.py")
    (found,) = problems(root)
    assert found.startswith("uncommitted changes to ") and "add no line to the `## Unreleased` entry" in found, found
    text = (root / MIGRATIONS).read_text(encoding="utf-8")
    write(
        root,
        {MIGRATIONS: text.replace("Copy it.\n", "Copy it.\n- 2026-11-01, the folder again: `ops/`. Copy it.\n", 1)},
    )
    assert problems(root) == []


def test_a_commit_that_changes_no_owned_path_needs_no_line(tmp_path: Path):
    root = released(tmp_path, TOOL)
    exempt = {
        ".raw/a.md": "a\n",
        "wiki/log.md": "l\n",
        "wiki/hot.md": "h\n",
        "CHANGELOG.md": "c\n",
        "design/idea.md": "# x\n",
    }
    write(root, exempt)
    commit(root, "records, the changelog and an omitted folder")
    write(root, {MIGRATIONS: with_line(root, AGAIN)})
    commit(root, "a line and nothing else")
    assert problems(root) == []


def test_a_merge_commit_is_not_asked_for_a_line_of_its_own(tmp_path: Path):
    root = released(tmp_path, TOOL)
    setup(root, "checkout", "-q", "-b", "side")
    write(root, {"ops/tool.py": "x = 2\n", MIGRATIONS: with_line(root, AGAIN)})
    commit(root, "change the tool, with its line")
    setup(root, "checkout", "-q", "-")
    write(root, {"CHANGELOG.md": "c\n"})
    commit(root, "the changelog")
    setup(root, "merge", "-q", "--no-ff", "-m", "merge the side", "side")
    assert problems(root) == []


def test_a_release_in_the_making_and_the_commits_after_it_carry_their_lines(tmp_path: Path):
    root = released(tmp_path, TOOL)
    entry = (root / MIGRATIONS).read_text(encoding="utf-8").replace("## Unreleased (after 1.0.0)", "## 1.1.0")
    write(root, {"ops/tool.py": "x = 2\n", VERSION: "1.1.0\n", MIGRATIONS: entry})
    assert problems(root) == []  # the release commit in the making: the entry moved under its number
    commit(root, "release 1.1.0")
    assert problems(root) == []  # the base is the release commit now
    unreleased = "## Unreleased (after 1.1.0)\n" + AGAIN + "\n"
    write(root, {"ops/tool.py": "x = 3\n", MIGRATIONS: entry.replace("## 1.1.0", unreleased + "## 1.1.0")})
    commit(root, "change the tool again, with its line")
    assert problems(root) == []
    write(root, {"ops/tool.py": "x = 4\n"})
    commit(root, "change it a third time, with no line")
    (found,) = problems(root)
    assert "change it a third time, with no line: changes ops/tool.py" in found, found


def test_every_commit_since_the_release_that_changes_a_template_owned_path_carries_its_line():
    reason = skipped(ROOT)
    if reason:
        pytest.skip(reason)
    found = unrecorded(ROOT)
    assert found == [], "\n".join(found)
