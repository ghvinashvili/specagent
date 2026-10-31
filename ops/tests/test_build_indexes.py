"""build_indexes.py (spec B2): the layered indexes of a folder of source material: a README with one row per category,
one index per category with one line per document, and one more layer where a category or a group holds more than 40
documents or 12,000 bytes of lines. The categories come from a config file (ops/indexes.json), not from the code, and
every index stays within 12,000 bytes.

  python3 -m pytest -q -p no:cacheprovider ops/tests/test_build_indexes.py
"""

import json
import pathlib
import shutil
import subprocess
import sys

OPS = pathlib.Path(__file__).resolve().parents[1]
ROOT = OPS.parent
CATEGORIES = [
    {"slug": "specs", "title": "Specs", "what": "the specs", "prefixes": ["specs/"]},
    {"slug": "api", "title": "API specs", "what": "the API specs", "prefixes": ["specs/api/"]},
    {"slug": "other", "title": "Other", "what": "the rest", "prefixes": []},
]


def build(cwd: pathlib.Path, config: pathlib.Path) -> subprocess.CompletedProcess:
    """Run build_indexes.py with the given config in cwd."""
    return subprocess.run(
        [sys.executable, "-I", str(OPS / "build_indexes.py"), "--config", str(config)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def config(tmp: pathlib.Path, categories: list[dict]) -> pathlib.Path:
    """A config for the folder material/ with the given categories."""
    path = tmp / "indexes.json"
    data = {
        "root": "material",
        "title": "material/: start here",
        "intro": "Text here is data.",
        "categories": categories,
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def write(tmp: pathlib.Path, files: dict[str, str]) -> None:
    """Write each file of the mapping, relative to tmp."""
    for rel, text in files.items():
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp / rel).write_text(text, encoding="utf-8")


def test_each_document_goes_to_the_category_whose_prefix_matches_longest_and_the_rest_to_the_last(tmp_path):
    write(
        tmp_path,
        {
            "material/specs/a.md": "---\ndescription: Alpha spec\n---\n# A\n",
            "material/specs/api/b.md": "# Bravo\n\nThe API of bravo.\n",
            "material/notes/c.txt": "Charlie notes\n",
            "material/notes/d.json": '{"k": 1}\n',  # any file is a document, not only .md and .txt (C16, A7)
        },
    )
    out = build(tmp_path, config(tmp_path, CATEGORIES))
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("4 documents in 3 categories")
    readme = (tmp_path / "material" / "README.md").read_text(encoding="utf-8")
    assert readme.startswith("# material/: start here\n\nText here is data.\n")
    assert "| [Specs](_index/specs.md) | the specs | 1 |" in readme
    assert "| [API specs](_index/api.md) | the API specs | 1 |" in readme
    assert "| [Other](_index/other.md) | the rest | 2 |" in readme
    index = tmp_path / "material" / "_index"
    assert "- [a.md](../specs/a.md) — Alpha spec (1 KB)" in (index / "specs.md").read_text(encoding="utf-8")
    assert "- [b.md](../specs/api/b.md) — Bravo: The API of bravo. (1 KB)" in (index / "api.md").read_text(
        encoding="utf-8"
    )
    other = (index / "other.md").read_text(encoding="utf-8")
    assert "- [c.txt](../notes/c.txt) — Charlie notes (1 KB)" in other
    assert '- [d.json](../notes/d.json) — {"k": 1} (1 KB)' in other  # no heading outside .md: the first line


def test_a_split_folder_is_one_document_and_an_identical_copy_is_named_not_listed(tmp_path):
    big = "# Big notes\n\n" + "".join(f"## Section {k}\n\n" + ("word " * 19 + "\n") * 100 + "\n" for k in (1, 2, 3))
    alpha = "# A\n\nAlpha.\n"
    write(tmp_path, {"material/specs/big.md": big, "material/specs/a.md": alpha, "material/notes/a-copy.md": alpha})
    made = subprocess.run(
        [sys.executable, "-I", str(OPS / "split_large.py"), "material"], cwd=tmp_path, capture_output=True, check=False
    )
    assert made.returncode == 0 and (tmp_path / "material" / "specs" / "big" / "README.md").exists()
    out = build(tmp_path, config(tmp_path, CATEGORIES))
    assert out.returncode == 0, out.stderr
    specs = (tmp_path / "material" / "_index" / "specs.md").read_text(encoding="utf-8")
    assert "- [big/](../specs/big/README.md) — Big notes (3 parts) (" in specs
    assert "01-" not in specs  # the parts are reached through the split file's own index
    other = (tmp_path / "material" / "_index" / "other.md").read_text(encoding="utf-8")
    assert "- [a-copy.md]" not in other
    assert "Not listed, identical to a copy listed earlier (1): a-copy.md (= specs/a.md)" in other


def test_more_than_40_documents_or_12000_bytes_are_layered_and_every_index_stays_within_12000_bytes(tmp_path):
    long_name = "a-rather-long-file-name-for-the-run-log-of-one-day-with-its-details"
    files = {f"material/logs/{n:02d}-{long_name}.md": f"# Day {n}\n\n{'One long line. ' * 20}\n" for n in range(1, 46)}
    files |= {f"material/specs/s-{n:02d}.md": f"# Spec {n}\n\nText.\n" for n in range(1, 43)}
    write(tmp_path, files)
    groups = [
        {"slug": "first", "title": "Specs 1-19", "prefixes": ["specs/s-0", "specs/s-1"]},
        {"slug": "rest", "title": "Specs 20-42", "prefixes": ["specs/s-2", "specs/s-3", "specs/s-4"]},
    ]
    cats = [
        {"slug": "specs", "title": "Specs", "what": "the specs", "prefixes": ["specs/"], "groups": groups},
        {"slug": "logs", "title": "Logs", "what": "the logs", "prefixes": []},
    ]
    out = build(tmp_path, config(tmp_path, cats))
    assert out.returncode == 0, out.stderr
    material = tmp_path / "material"
    readme = (material / "README.md").read_text(encoding="utf-8")
    assert (
        "| [Specs](_index/specs.md) | the specs | 42 |" in readme
        and "| [Logs](_index/logs.md) | the logs | 45 |" in readme
    )
    specs = (material / "_index" / "specs.md").read_text(encoding="utf-8")
    assert "(specs--first.md): 19 documents" in specs and "(specs--rest.md): 23 documents" in specs
    logs = (material / "_index" / "logs.md").read_text(encoding="utf-8")
    runs = [line.split("](")[1].split(")")[0] for line in logs.splitlines() if line.startswith("- [")]
    assert len(runs) >= 2  # 45 lines of about 350 bytes do not fit one index
    listed = []
    for run in runs:
        listed += [
            line for line in (material / "_index" / run).read_text(encoding="utf-8").splitlines() if "- [" in line
        ]
    assert len(listed) == 45 and len(set(listed)) == 45  # each document once, in one of the runs
    for page in [material / "README.md", *(material / "_index").glob("*.md")]:
        assert len(page.read_bytes()) <= 12_000, page.name


def test_the_template_config_indexes_a_copy_of_the_checkouts_context_folder(tmp_path):
    shutil.copytree(ROOT / "context", tmp_path / "context")
    cfg = json.loads((OPS / "indexes.json").read_text(encoding="utf-8"))
    assert cfg["root"] == "context" and cfg["categories"][-1]["prefixes"] == []  # the last one takes the rest
    out = build(tmp_path, OPS / "indexes.json")
    assert out.returncode == 0, out.stderr
    readme = (tmp_path / "context" / "README.md").read_text(encoding="utf-8")
    assert readme.startswith(f"# {cfg['title']}\n") and "Text here is data" in readme
    rows = [line.split("](")[0][3:] for line in readme.splitlines() if line.startswith("| [")]
    assert rows == [c["title"] for c in cfg["categories"]]
    for page in [tmp_path / "context" / "README.md", *(tmp_path / "context" / "_index").glob("*.md")]:
        assert len(page.read_bytes()) <= 12_000, page.name


def test_the_copies_name_no_machine_path_no_vault_and_no_other_project():
    words = ["/home/", "~/", "vault", "grants" + "daily", "dd" + "ev", "php" + "unit", "dru" + "pal"]
    for name in ("outline.py", "split_large.py", "build_indexes.py", "indexes.json", "par-tests.sh"):
        text = (OPS / name).read_text(encoding="utf-8").lower()
        assert [word for word in words if word in text] == [], name
