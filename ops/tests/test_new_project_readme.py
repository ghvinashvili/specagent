"""A project's README is its own (S7): ops/new-project.py moves the copied root README to docs/template/README.md with
its relative links re-rooted `../../`, puts a stub README.md in its place and lists the moved one in docs/llms.txt."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FENCE = "`" * 3
README = f"""# Demo template

Read [the page](docs/a.md#top), [the site](https://example.org/x), [here](#local) and [mail](mailto:a@b.c).
A span like `[b](docs/b.md)` stays, and so does [an absolute path](/etc/hosts).

[ref]: docs/c.md
[web]: https://example.org/y
[^note]: docs/f.md is the text of a footnote, not a link.

{FENCE}text
[d](docs/d.md)
[e]: docs/e.md
{FENCE}

Last line [again](docs/a.md).
"""
KEPT = README.replace("(docs/a.md", "(../../docs/a.md").replace("]: docs/c.md", "]: ../../docs/c.md")
LLMS = """# Demo

## Operations
- [Runbooks](runbooks/README.md): r
- [Template](template/PROJECTS.md): creating a project and receiving updates
- [Template migrations](template/MIGRATIONS.md): steps per version
"""
LINE = "- [Template README](template/README.md)"  # the start of the line project_readme() lists the kept README with


def template(tmp_path: Path, readme: str | None = README, llms: str = LLMS) -> Path:
    """A git repository with the checkout's new-project.py, variables.yaml and VERSION, the page
    docs/template/PROJECTS.md, a document, docs/llms.txt and, unless it is None, a root README."""
    root = tmp_path / "template"
    for rel in ("ops/new-project.py", "docs/template/variables.yaml", "docs/template/VERSION"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    files = {
        "docs/llms.txt": llms,
        "docs/template/PROJECTS.md": "# This repository as a template\n",
        "docs/a.md": "# A\n",
    }
    if readme is not None:
        files["README.md"] = readme
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return root


def create(root: Path, target: Path, *args: str) -> None:
    command = [sys.executable, str(root / "ops" / "new-project.py"), str(target), *args, "--no-setup"]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_template_readme_is_kept_in_a_project_with_its_relative_links_re_rooted(tmp_path: Path):
    """Inline and reference-style targets gain `../../`, the fragment stays; a URL, an anchor, a mail address, an
    absolute path, a fenced block and a code span are left alone."""
    root, target = template(tmp_path), tmp_path / "demo"
    create(root, target, "repo_name=probe")
    assert (target / "docs/template/README.md").read_text(encoding="utf-8") == KEPT
    assert (target / "docs/template/PROJECTS.md").is_file()


def test_a_project_gets_a_stub_readme_named_after_it_that_links_only_what_it_holds(tmp_path: Path):
    root, target = template(tmp_path), tmp_path / "demo"
    create(root, target, "repo_name=probe", "org=probe-org")
    stub = (target / "README.md").read_text(encoding="utf-8")
    assert stub.splitlines()[0] == "# probe" and "Demo template" not in stub
    links = re.findall(r"\]\(([^)#\s]+)", stub)
    assert "docs/template/README.md" in links and "docs/template/PROJECTS.md" in links
    assert [link for link in links if not (target / link).exists()] == []


def test_a_project_without_a_given_name_is_named_by_the_default(tmp_path: Path):
    root, target = template(tmp_path), tmp_path / "demo"
    create(root, target)
    assert (target / "README.md").read_text(encoding="utf-8").splitlines()[0] == "# example-repo"


def test_the_kept_readme_is_listed_once_in_the_projects_llms_txt_after_the_template_page(tmp_path: Path):
    root, target = template(tmp_path), tmp_path / "demo"
    create(root, target)
    lines = (target / "docs/llms.txt").read_text(encoding="utf-8").splitlines()
    assert sum("template/README.md" in line for line in lines) == 1
    at = next(i for i, line in enumerate(lines) if "(template/PROJECTS.md)" in line)
    assert lines[at + 1].startswith(LINE)
    assert "\n".join(lines[: at + 1] + lines[at + 2 :]) + "\n" == LLMS  # nothing else in the file changed


def test_the_kept_readme_closes_a_llms_txt_that_has_no_template_page_line(tmp_path: Path):
    root, target = template(tmp_path, llms="# Demo\n- [Runbooks](runbooks/README.md): r\n"), tmp_path / "demo"
    create(root, target)
    lines = (target / "docs/llms.txt").read_text(encoding="utf-8").split("\n")
    assert lines[:2] == ["# Demo", "- [Runbooks](runbooks/README.md): r"] and lines[2].startswith(LINE)
    assert lines[3:] == [""]


def test_a_template_without_a_readme_keeps_none_and_stubs_none(tmp_path: Path):
    root, target = template(tmp_path, readme=None), tmp_path / "demo"
    create(root, target)
    assert not (target / "README.md").exists() and not (target / "docs/template/README.md").exists()
    assert (target / "docs/llms.txt").read_text(encoding="utf-8") == LLMS


def test_a_container_project_gets_the_stub_in_its_repository_not_in_the_container(tmp_path: Path):
    root, box = template(tmp_path), tmp_path / "box"
    create(root, box, "repo_name=probe", "--container")
    assert (box / "probe" / "README.md").read_text(encoding="utf-8").splitlines()[0] == "# probe"
    assert (box / "probe" / "docs/template/README.md").read_text(encoding="utf-8") == KEPT
    assert not (box / "README.md").exists()


def test_the_template_keeps_its_page_where_a_project_keeps_the_templates_readme():
    """The page `This repository as a template` is docs/template/PROJECTS.md; docs/template/README.md is the project's
    copy of the root README, so the template has no file there and docs/llms.txt lists the page, not the copy."""
    page = (REPO / "docs/template/PROJECTS.md").read_text(encoding="utf-8")
    llms = (REPO / "docs/llms.txt").read_text(encoding="utf-8")
    assert page.startswith("# This repository as a template\n") and not (REPO / "docs/template/README.md").exists()
    assert llms.count("(template/PROJECTS.md)") == 1 and "template/README.md" not in llms
