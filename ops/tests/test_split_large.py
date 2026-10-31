"""split_large.py (spec B2): a large raw file becomes titled parts of at most 12,000 bytes behind an index, so an agent
opens one part instead of the whole file. The template's copy takes its files and folders as arguments (the vault's
copy took context/ from the vault root) and counts a part's own header within the 12,000 bytes (the vault's copy
joined parts up to 14,000).

  python3 -m pytest -q -p no:cacheprovider ops/tests/test_split_large.py
"""

import pathlib
import re
import subprocess
import sys

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "split_large.py"
PART_HEAD = re.compile(
    r"<!-- part (\d+) of (\d+) of (\S+), lines (\d+)-(\d+); split \d{4}-\d{2}-\d{2} by ops/split_large\.py; "
    r"index: README\.md -->"
)


def split(cwd: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    """Run split_large.py with args in cwd."""
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def paragraph(size: int, tag: str) -> str:
    """Lines of 99 bytes, about size bytes in all, then a blank line."""
    row = f"{tag} " + "word " * 19 + "\n"
    return row * (size // len(row)) + "\n"


def big_notes() -> str:
    """A Markdown file of about 36 KB: one title, then sections of about 10,500 and 1,500 bytes in turn."""
    text = "# Big notes\n\n"
    for k in range(1, 7):
        text += f"## Section {k}\n\n" + paragraph(10_500 if k % 2 else 1_500, f"s{k}")
    return text


def test_a_large_markdown_file_becomes_titled_parts_of_at_most_12000_bytes_behind_an_index(tmp_path):
    (tmp_path / "notes").mkdir()
    text = big_notes()
    (tmp_path / "notes" / "big.md").write_text(text, encoding="utf-8")
    out = split(tmp_path, "notes")
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("split notes/big.md: 6 parts")
    assert not (tmp_path / "notes" / "big.md").exists()
    folder = tmp_path / "notes" / "big"
    index = (folder / "README.md").read_text(encoding="utf-8")
    assert index.startswith("# Big notes — index of 6 parts\n")
    parts = sorted(folder.glob("0*.md"))
    assert [p.name[:3] for p in parts] == ["01-", "02-", "03-", "04-", "05-", "06-"]
    body, end = "", 0
    for n, part in enumerate(parts, 1):
        assert len(part.read_bytes()) <= 12_000, part.name  # the vault's copy wrote 12,132 bytes here
        lines = part.read_text(encoding="utf-8").split("\n")
        head = PART_HEAD.fullmatch(lines[0])
        assert head and head.group(1, 2, 3) == (str(n), "6", "notes/big.md") and int(head.group(4)) == end + 1
        end = int(head.group(5))
        assert lines[1] == ("# Big notes" if n == 1 else f"## Section {n}")  # each part starts at its heading
        assert f"]({part.name})" in index
        body += "\n".join(lines[1:])
    assert body == text and end == text.count("\n")  # nothing lost, nothing added


def test_the_limit_decides_what_is_split_a_text_is_cut_at_blank_lines_and_a_dry_run_writes_nothing(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    page = "# Page\n\n" + "".join(f"## Part {k}\n\n" + paragraph(3_100, f"p{k}") for k in range(1, 5))
    log = "".join(paragraph(1_000, f"l{k}") for k in range(30))  # 30 paragraphs, no heading
    (notes / "page.md").write_text(page, encoding="utf-8")
    (notes / "run.txt").write_text(log, encoding="utf-8")
    assert 12_000 < len(page.encode()) <= 24_000 < len(log.encode())
    out = split(tmp_path, "--dry-run", "notes")
    assert out.returncode == 0 and "split notes/run.txt: " in out.stdout and "page.md" not in out.stdout
    assert sorted(p.name for p in notes.iterdir()) == ["page.md", "run.txt"]  # a dry run writes nothing
    assert split(tmp_path, "notes").returncode == 0
    assert (notes / "page.md").exists() and not (notes / "run.txt").exists()  # the default limit is 24,000 bytes
    parts = sorted((notes / "run").glob("0*.md"))
    assert len(parts) >= 3
    for part in parts:
        text = part.read_text(encoding="utf-8")
        assert len(text.encode()) <= 12_000 and text.split("\n")[1].startswith("# l0 word")  # titled by its text
        assert text.endswith("\n\n")  # cut between paragraphs, never inside one
    out = split(tmp_path, "--limit", "12000", "notes/page.md")
    assert out.returncode == 0 and out.stdout.startswith("split notes/page.md: ")
    assert (notes / "page" / "README.md").exists() and not (notes / "page.md").exists()
    assert split(tmp_path, "notes/missing.md").returncode == 2


def test_an_identical_copy_points_at_the_first_and_relink_rewrites_the_cited_paths(tmp_path):
    for folder in ("a", "b", "docs"):
        (tmp_path / folder).mkdir()
    text = big_notes()
    (tmp_path / "a" / "big.md").write_text(text, encoding="utf-8")
    (tmp_path / "b" / "big.md").write_text(text, encoding="utf-8")
    page = "See `a/big.md` and b/big.md. Not a/big.md5 or a/big.md-old.\n"
    (tmp_path / "docs" / "page.md").write_text(page, encoding="utf-8")
    out = split(tmp_path, "--relink", "docs", "a", "b")  # the first path given is the one a copy points at
    assert out.returncode == 0, out.stderr
    assert "dup  b/big.md = a/big.md" in out.stdout
    pointer = (tmp_path / "b" / "big" / "README.md").read_text(encoding="utf-8")
    assert pointer.startswith("# big.md: the same text as `a/big.md`\n") and "`a/big/README.md`" in pointer
    assert [p.name for p in (tmp_path / "b" / "big").iterdir()] == ["README.md"]
    assert not (tmp_path / "b" / "big.md").exists()
    rewritten = "See `a/big/README.md` and a/big/README.md. Not a/big.md5 or a/big.md-old.\n"
    assert (tmp_path / "docs" / "page.md").read_text(encoding="utf-8") == rewritten


def api_reference(functions: int) -> str:
    """An engine's API reference: a `##` module per 50 functions, a `###` heading and about 320 bytes per function."""
    text = "# Engine API reference\n\n"
    for m in range(functions // 50):
        text += f"## Module {m}: rendering and scene graph helpers\n\n"
        for f in range(50):
            body = "Sets the local transform of a node; the world transform is recomputed on the next frame. " * 3
            text += f"### `scene_node_set_transform_{m}_{f}(node, matrix)`\n\n{body}\n\n"
    return text


def test_a_heading_dense_file_gets_an_index_of_at_most_12000_bytes_that_lists_or_counts_every_heading(tmp_path):
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "ref.md").write_text(api_reference(300), encoding="utf-8")
    out = split(tmp_path, "api")
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("split api/ref.md: 12 parts")
    folder = tmp_path / "api" / "ref"
    index = (folder / "README.md").read_text(encoding="utf-8")
    assert len(index.encode()) <= 12_000  # without a cap on the index: 12,287 bytes
    assert index.startswith("# Engine API reference — index of 12 parts\n")
    parts = sorted(folder.glob("[0-9]*.md"))
    rows = [line for line in index.split("\n") if line.startswith("| [")]
    assert len(parts) == len(rows) == 12
    for part, row in zip(parts, rows, strict=True):
        assert row.startswith(f"| [{part.name}]({part.name}) | ")
    for part, row in zip(parts[1:], rows[1:], strict=True):  # after the first, a part holds two heading levels
        held = len(re.findall(r"^#{2,3} ", part.read_text(encoding="utf-8"), re.MULTILINE))
        cell = re.fullmatch(r"\| .+ \| (.+) · \+(\d+) more \|", row)
        assert cell and len(cell.group(1).split(" · ")) + int(cell.group(2)) == held, row  # listed or counted


def wide(n: int, seed: int) -> str:
    """n CJK ideographs picked by seed, three bytes each in UTF-8, as in a heading of a language with wide letters."""
    return "".join(chr(0x4E00 + (seed * 101 + i * 7) % 20_000) for i in range(n))


def wide_notes() -> str:
    """About 180 KB: a title, then 5 sections of 5 subsections of about 7,000 bytes; every heading 60 wide letters."""
    text = f"# {wide(60, 0)}\n\n"
    for s in range(1, 6):
        text += f"## {wide(60, s)}\n\n"
        for t in range(1, 6):
            text += f"### {wide(60, 10 * s + t)}\n\n" + paragraph(7_000, f"w{s}{t}")
    return text


def test_a_file_whose_flat_index_passes_12000_bytes_with_no_heading_listed_is_grouped(tmp_path):
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "wide.md").write_text(wide_notes(), encoding="utf-8")
    out = split(tmp_path, "notes")
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("split notes/wide.md: 25 parts")  # GROUP parts, which alone keep an index flat
    folder = tmp_path / "notes" / "wide"
    index = (folder / "README.md").read_text(encoding="utf-8")
    assert index.startswith(f"# {wide(60, 0)} — index: 6 groups, 25 parts\n")
    groups = sorted(folder.glob("_group-*.md"))
    assert len(groups) == 6 and all(f"]({group.name})" in index for group in groups)
    rows = "".join(group.read_text(encoding="utf-8") for group in groups)
    parts = sorted(folder.glob("[0-9]*.md"))
    assert len(parts) == 25 and all(rows.count(f"]({part.name})") == 1 for part in parts)
    for written in [folder / "README.md", *groups]:
        assert len(written.read_bytes()) <= 12_000, written.name


def regulation(heading: int) -> str:
    """About 640 KB: a title, then 3 chapters of 30 articles of about 7,000 bytes; chapter headings 60 wide letters."""
    text = f"# {wide(60, 0)}\n\n"
    for c in range(1, 4):
        text += f"## {wide(60, c)}\n\n"
        for r in range(1, 31):
            text += f"### {wide(heading, 100 * c + r)}\n\n" + paragraph(7_000, f"r{c}{r}")
    return text


def test_a_group_index_of_30_parts_with_long_wide_headings_keeps_within_12000_bytes_in_brief_rows(tmp_path):
    (tmp_path / "law").mkdir()
    (tmp_path / "law" / "act.md").write_text(regulation(45), encoding="utf-8")
    out = split(tmp_path, "law")
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("split law/act.md: 90 parts")
    folder = tmp_path / "law" / "act"
    groups = sorted(folder.glob("_group-*.md"))
    rows = "".join(group.read_text(encoding="utf-8") for group in groups)
    parts = sorted(folder.glob("[0-9]*.md"))
    assert len(groups) == 4 and len(parts) == 90 and all(rows.count(f"]({part.name})") == 1 for part in parts)
    for written in [folder / "README.md", *groups]:
        assert len(written.read_bytes()) <= 12_000, written.name  # with no heading listed: 14,987 bytes in group 2
    assert f"| [{parts[0].name}]({parts[0].name}) | " in rows  # group 1 fits with its full row
    assert f"| [31]({parts[30].name}) | " in rows  # group 3 does not: a brief row links a part by its number
