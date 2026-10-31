"""The material of a stage is cut into pieces and chosen by script: no model takes part and the manager spends no
turn on it. Run: `uv run pytest -q packages/harness/tests/test_pieces.py`."""

from __future__ import annotations

from pathlib import Path

from harness import pieces


def spans(path: str, text: str) -> list[tuple[int, int]]:
    return [(a, b) for _, a, b, _ in pieces.cut_text(path, text)]


def test_a_file_is_cut_at_its_natural_seams():
    md = "intro\n\n# One\ntext\n```\n# not a heading\n```\n\n## Two\nmore\n"
    assert spans("a.md", md) == [(1, 1), (3, 7), (9, 10)]  # a line inside a code fence starts nothing
    assert [t for *_, t in pieces.cut_text("a.md", md)] == ["intro", "# One", "## Two"]
    py = "import os\n\nX = 1\n\n\n@dec\ndef f():\n    return 1\n\n\nY = f()\nZ = 2\n\n\nclass C:\n    pass\n"
    assert spans("m.py", py) == [(1, 3), (6, 8), (11, 12), (15, 16)]  # a decorator belongs to its definition
    js = "const a = 1;\nfunction f() {\n  return 1;\n}\nexport class K {}\nconst g = (x) => x;\n"
    assert spans("m.mjs", js) == [(1, 1), (2, 4), (5, 5), (6, 6)]
    assert spans("t.yaml", "version: 1\nstages:\n  - id: read\n  - id: plan\nother: x\n") == [(1, 1), (2, 4), (5, 5)]
    assert spans("p.toml", "[a]\nx = 1\n\n[b]\ny = 2\n") == [(1, 2), (4, 5)]
    assert spans("bad.py", "def (:\n") == [(1, 1)]  # code that does not parse is one piece
    assert spans("long.txt", "".join(f"{n}\n" for n in range(1, 401))) == [(1, 160), (161, 320), (321, 400)]
    assert pieces.cut_text("empty.md", "") == []


def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    app = "".join(f"def f{n}():\n    return {n}\n\n\n" for n in range(1, 6))  # five pieces of four lines
    files = {
        "src/app.py": app,
        "src/small.py": "VALUE = 1\n",
        "src/large.py": "".join(f"x{n} = {n}\n" for n in range(500)),
        "docs/retry.md": "# Retry\n\nThe client waits with backoff and jitter before a retry.\n",
        "docs/other.md": "# Colours\n\nThe palette of the site.\n",
        "secret/x.md": "retry backoff jitter\n",
        "context/m.md": "# Material\n\nretry backoff jitter, as the tool documents them\n",
        "wiki/p.md": "retry backoff jitter\n",
        "CLAUDE.md": "retry backoff jitter\n",
        "img/logo.png": "not text that a session reads as text\n",
    }
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def test_the_harness_gives_what_the_texts_cite_and_name_and_what_matches_the_job(tmp_path: Path):
    root = repo(tmp_path)
    texts = [
        (
            "See `src/app.py:6` and src/app.py:6-7, then src/app.py:14; `src/small.py`, `src/large.py`, "
            "`docs/none.md`, secret/x.md:1, context/m.md:1 and img/logo.png."
        ),
        "The plan changes src/app.py:6 again.",
    ]
    chosen = pieces.select(root, ["secret/**"], True, texts, "retry with backoff and jitter", {"CLAUDE.md"})
    assert chosen == [
        ("src/app.py", 5, 6, "cited"),  # cited three times, so it comes first
        ("src/app.py", 13, 14, "cited"),  # then in the order of the first citation
        ("context/m.md", 1, 3, "cited"),
        ("src/app.py", 1, None, "named"),  # short files the texts name are given whole
        ("src/small.py", 1, None, "named"),
        ("context/m.md", 1, None, "named"),
        ("docs/retry.md", 1, 3, "related"),
        ("context/m.md", 1, 3, "related"),
    ]
    # closed paths, files outside the repository, long files, binary files, the wiki and the pack are never chosen
    flat = " ".join(f"{p}" for p, *_ in chosen)
    assert not any(x in flat for x in ("secret", "large", "none", "logo", "wiki", "CLAUDE", "other"))
    assert pieces.select(root, ["secret/**"], True, texts, "retry with backoff and jitter", {"CLAUDE.md"}) == chosen


def test_context_reaches_only_the_types_and_stages_that_receive_it(tmp_path: Path):
    root = repo(tmp_path)
    texts = ["context/m.md:1 and `context/m.md`"]
    no_type = pieces.select(root, [], False, texts, "retry backoff jitter")
    assert all(not p.startswith("context/") for p, *_ in no_type)
    notes_only = pieces.select(root, [], True, texts, "retry backoff jitter", run_material=False)
    assert [(p, why) for p, _, _, why in notes_only if p.startswith("context/")] == [("context/m.md", "cited")]


def test_the_word_match_keeps_to_its_budget(tmp_path: Path):
    root = repo(tmp_path)
    assert [p for p, *_ in pieces.related(root, ["docs/retry.md", "docs/other.md"], "retry backoff")] == [
        "docs/retry.md"
    ]
    assert pieces.related(root, ["docs/retry.md"], "retry backoff", budget=10) == []
    assert pieces.related(root, ["docs/retry.md"], "the and with") == []  # no word that tells pieces apart
