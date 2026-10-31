#!/usr/bin/env python3
"""Create a project from this template: copy the tracked files into <target-dir>, replace the template's literal
values (docs/template/variables.yaml) with the new project's, move the template's README to docs/template/README.md
(its links re-rooted) and write a stub README.md in its place, and set the project up on this machine (ops/bootstrap.py:
uv, the workspace, just, the git hooks, the plugins, the language servers, the sandbox, the first code graph, graphify's
skill, the user-level pipeline skill and harness doctor). Usage: ops/new-project.py <target-dir> name=value ...
[--no-setup]
[--container]. With --container, <target-dir> holds the whole project: the repository goes to <target-dir>/<repo_name>,
beside it runs/ (marked as the runs root, docs/roles/RUNS.md), experiments/ (copies made for trials) and
docs/handoff/ (the manager's hand-over notes), as ops/container.py lays them out. With
vault_path=<path> and no <path>/INDEX.md, ops/new-vault.py first makes the vault there; its refusal stops the project."""

import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

OPTIONS = {"--no-setup", "--container"}
RUNS_MARKER = ".harness-runs"  # harness state.RUNS_MARKER: the file that makes a runs/ folder the runs root
LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")  # harness catalog.LINK: a Markdown link, fragment cut
FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")  # harness catalog.FENCE: a line that opens or closes a fenced block
# a code span (text), or the target of an inline link or of a reference-style definition (not a footnote): head, target
TARGET = re.compile(r"(`+).+?\1|(\[[^\]]*\]\()([^)\s#]+)|^(\[(?!\^)[^\]]+\]:[ \t]*)(\S+)")
KEPT = "docs/template/README.md"  # where a project keeps the template's README (harness catalog.KEPT_README)
PROJECTS_LINK = "(template/PROJECTS.md)"  # the line of docs/llms.txt that the kept README is listed after
LLMS_LINE = "- [Template README](template/README.md): the template's README, kept from the day this project was made"
STUB = """# {name}

Made from the SpecAgent template. Say here what this project is.

- [What the template is and how its pipelines run](docs/template/README.md), kept from the day this project was made
- [What this project owns, and how template updates reach it](docs/template/PROJECTS.md)
- [Where every document is](docs/llms.txt)
"""


def checkout(path: Path) -> bool:
    try:
        return (path / ".git").exists()
    except OSError:  # a folder this user may not read is no checkout of theirs (harness state._checkout)
        return False


def omitted_links_dropped(text: str, rel: str, root: Path, omit: list[str]) -> str:
    """The text without each line that links into an omitted folder (resolved from the file's own folder, links
    followed): the project has no such file, and its docs-check and wiki-lint would report the link."""
    base, folder, prefixes = root.resolve(), (root / rel).parent, tuple(omit)

    def omitted(link: str) -> bool:
        if "://" in link or link.startswith("/"):
            return False
        path = (folder / link).resolve()
        return path.is_relative_to(base) and (path.relative_to(base).as_posix() + "/").startswith(prefixes)

    return "\n".join(line for line in text.split("\n") if not any(omitted(link) for link in LINK.findall(line)))


def copy_tracked(root: Path, target: Path, spec: dict, given: dict[str, str]) -> None:
    """Copy the tracked files, omitted ones left out, into target: the given values replace the template's."""
    replace = [(v["default"], given[v["name"]]) for v in spec["variables"] if v["name"] in given]
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    for rel in tracked:
        if any(rel.startswith(prefix) for prefix in spec.get("omit", [])):
            continue
        src, dest = root / rel, target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():  # a tracked link (wiki/plans) stays a link with the same target text
            dest.symlink_to(os.readlink(src))
            continue
        data = src.read_bytes()
        if not any(rel.startswith(prefix) for prefix in spec["skip"]):
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = None  # binary: copied as is
            if text is not None:
                if rel.endswith(".md"):  # a line that links into an omitted folder would break the project's checks
                    text = omitted_links_dropped(text, rel, root, spec.get("omit", []))
                for old, new in replace:
                    text = text.replace(old, new)
                data = text.encode("utf-8")
        dest.write_bytes(data)
        dest.chmod(src.stat().st_mode)


def links_rerooted(text: str) -> str:
    """The relative link targets of a README, inline and reference-style, outside code, with `../../` in front: the copy
    lives two folders below the root its links are written from. A URL, an anchor and an absolute path stay."""

    def up(found: re.Match[str]) -> str:
        head, link = (found[2], found[3]) if found[2] else (found[4], found[5])
        if found[1] or re.match(r"[a-z][a-z0-9+.-]*:|[/#]", link):  # a code span, or a target that is not relative
            return found[0]
        return f"{head}../../{link}"

    lines, fence = text.split("\n"), ""
    for i, line in enumerate(lines):
        mark = FENCE.match(line)
        if fence:  # inside a block, only a run of the same character at least as long, then blanks, closes it
            if mark and mark[1][0] == fence[0] and len(mark[1]) >= len(fence) and not mark[2].strip():
                fence = ""
        elif mark:
            fence = mark[1]
        else:
            lines[i] = TARGET.sub(up, line)
    return "\n".join(lines)


def project_readme(target: Path, name: str) -> None:
    """The README that was copied becomes the project's own: the template's moves to docs/template/README.md with its
    links re-rooted, a stub named after the project takes its place, and docs/llms.txt lists the moved one after the
    template page. A template without a README keeps none and stubs none."""
    readme = target / "README.md"
    if not readme.is_file():
        return
    (target / KEPT).parent.mkdir(parents=True, exist_ok=True)
    (target / KEPT).write_text(links_rerooted(readme.read_text(encoding="utf-8")), encoding="utf-8")
    readme.write_text(STUB.format(name=name), encoding="utf-8")
    llms = target / "docs" / "llms.txt"
    if llms.is_file():
        lines = llms.read_text(encoding="utf-8").splitlines()
        at = next((i + 1 for i, line in enumerate(lines) if PROJECTS_LINK in line), len(lines))
        llms.write_text("\n".join([*lines[:at], LLMS_LINE, *lines[at:]]) + "\n", encoding="utf-8")


def prepare(root: Path, target: Path, spec: dict, given: dict[str, str]) -> int:
    """Refuse a target inside the template or not empty; then make a missing vault from its form (ops/new-vault.py), so
    that a vault the script refuses stops the project before anything is copied. 0 when the copy may start."""
    if target == root or root in target.parents:
        print(f"{target} is inside the template; a project lives beside it")
        return 1
    if target.exists() and any(target.iterdir()):
        print(f"{target} is not empty")
        return 1
    vault = given.get("vault_path")
    if not vault or (Path(vault).expanduser() / "INDEX.md").is_file():
        return 0
    commons = given.get("commons_path") or next(v["default"] for v in spec["variables"] if v["name"] == "commons_path")
    made = subprocess.run(
        [sys.executable, str(root / "ops" / "new-vault.py"), vault, f"commons_path={commons}"], check=False
    )
    return made.returncode


def main(argv: list[str]) -> int:
    # seen: `--help` was taken for the target, and a project was created in a directory of that name
    if len(argv) < 2 or argv[1].startswith("-"):
        print(__doc__)
        return 0 if argv[1:2] in (["-h"], ["--help"]) else 2
    root = Path(__file__).resolve().parent.parent
    spec = yaml.safe_load((root / "docs" / "template" / "variables.yaml").read_text(encoding="utf-8"))
    flags = {arg for arg in argv[2:] if arg.startswith("--")}
    if flags - OPTIONS:
        print(f"unknown options: {sorted(flags - OPTIONS)}")
        return 2
    given = dict(arg.split("=", 1) for arg in argv[2:] if not arg.startswith("--"))
    unknown = set(given) - {v["name"] for v in spec["variables"]}
    if unknown:
        print(f"unknown variables: {sorted(unknown)}")
        return 1
    name = given.get("repo_name") or next(v["default"] for v in spec["variables"] if v["name"] == "repo_name")
    target = container = Path(argv[1]).resolve()
    if "--container" in flags:  # the project's own folder: its repository, its runs and its experiments
        target = container / name
        others = sorted(p.name for p in container.iterdir() if checkout(p)) if container.is_dir() else []
        if others:  # the marked runs/ would be the runs root of these checkouts too (harness state.runs_root)
            print(f"{container} holds other checkouts ({', '.join(others)}); a project gets a container of its own")
            return 1
        runs = container / "runs"
        if runs.exists() and not (runs / RUNS_MARKER).is_file():  # a runs/ folder of something else is not taken
            print(f"{runs} exists and is not a runs root (no {RUNS_MARKER}); choose another container")
            return 1
    refused = prepare(root, target, spec, given)
    if refused:
        return refused
    copy_tracked(root, target, spec, given)
    project_readme(target, name)
    if "--container" in flags:
        (container / "runs").mkdir(exist_ok=True)
        (container / "runs" / RUNS_MARKER).write_text(
            f"runs of the checkout {target.name} beside this folder (harness state.runs_root)\n", encoding="utf-8"
        )
        (container / "experiments").mkdir(exist_ok=True)
        (container / "docs" / "handoff").mkdir(parents=True, exist_ok=True)
    print(
        f"created {target} from SpecAgent {(root / 'docs' / 'template' / 'VERSION').read_text(encoding='utf-8').strip()}",
        flush=True,  # before the setup's own output
    )
    if "--no-setup" in flags:
        return 0
    return subprocess.run([sys.executable, str(target / "ops" / "bootstrap.py"), "--wait"], check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv))
