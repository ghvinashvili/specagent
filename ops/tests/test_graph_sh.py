"""ops/graph.sh (spec A3), the body of `just graph`: `graphify update .`, `graphify export wiki`, the export moved to
wiki/graph/ and layered by ops/graph_index.py; the git hooks that run it with --quick after each commit, merge and
checkout; and what keeps the graph generated and out of git: the ignore files, the recipe, `skip:` of the template's
variables, the map in CLAUDE.md and the runbook row."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash") or "/bin/bash"
FAKE = """#!/bin/sh
echo "$* | $GRAPHIFY_OUT | $(pwd -P)" >> "$FAKE_LOG"
case "$1" in
  update) mkdir -p "$GRAPHIFY_OUT" && echo '{"nodes": [], "links": []}' > "$GRAPHIFY_OUT/graph.json" ;;
  export) mkdir -p "$GRAPHIFY_OUT/wiki" && cp "$FAKE_WIKI"/*.md "$GRAPHIFY_OUT/wiki/" ;;
esac
"""


def checkout(tmp_path: Path) -> Path:
    """The files of this repository that ops/graph.sh uses, copied to tmp_path/repo."""
    repo = tmp_path / "repo"
    (repo / "ops").mkdir(parents=True)
    for name in ("graph.sh", "graph_index.py", "split_large.py"):
        shutil.copy2(REPO / "ops" / name, repo / "ops" / name)
    for name in (".graphifyignore", ".gitignore"):
        shutil.copy2(REPO / name, repo / name)
    return repo


def fake_graphify(tmp_path: Path) -> dict[str, str]:
    """An environment whose graphify logs its calls and writes a graph and a one-article export."""
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    (fakebin / "graphify").write_text(FAKE, encoding="utf-8")
    (fakebin / "graphify").chmod(0o755)
    flat = tmp_path / "flat"
    flat.mkdir()
    (flat / "index.md").write_text("# Knowledge Graph Index\n", encoding="utf-8")
    (flat / "core.md").write_text(
        "# core\n\n> 3 nodes\n\n## Key Concepts\n\n- **load()** (2 connections) — `pkg/core.py`\n", encoding="utf-8"
    )
    path = f"{fakebin}{os.pathsep}{os.environ['PATH']}"
    return dict(
        os.environ, PATH=path, GRAPHIFY_OUT="somewhere-else", FAKE_LOG=str(tmp_path / "calls.log"), FAKE_WIKI=str(flat)
    )


def graph_sh(repo: Path, cwd: Path, env: dict[str, str], *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, str(repo / "ops" / "graph.sh"), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def test_the_recipe_updates_exports_and_moves_the_layered_wiki_into_place(tmp_path):
    repo = checkout(tmp_path)
    env = fake_graphify(tmp_path)
    rows = "\n".join(f"- `pkg/{'deep/' * 60}mod{i:02d}.py`" for i in range(20))
    core = tmp_path / "flat" / "core.md"
    core.write_text(
        core.read_text(encoding="utf-8") + f"\n## Relationships\n\n{rows}\n\n## Source Files\n\n{rows}\n",
        encoding="utf-8",
    )
    assert len(core.read_bytes()) > 12_000
    earlier = repo / "wiki" / "graph" / "core"  # what the last build's split of core.md left
    earlier.mkdir(parents=True)
    (earlier / "README.md").write_text("# core — index of 2 parts\n", encoding="utf-8")
    (earlier / "02-earlier.md").write_text("# core — part 2 of 2\n", encoding="utf-8")
    (repo / "wiki" / "graph" / "stale.md").write_text("# stale\n", encoding="utf-8")

    done = graph_sh(repo, tmp_path, env)

    assert done.returncode == 0, done.stderr
    calls = (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines()
    assert calls == [f"update . | graphify-out | {repo.resolve()}", f"export wiki | graphify-out | {repo.resolve()}"]
    graph = repo / "wiki" / "graph"
    assert (graph / "index.md").read_text(encoding="utf-8").splitlines()[0] == "# Code graph"
    assert (graph / "_index" / "pkg.md").is_file() and (graph / "core" / "README.md").is_file()
    assert done.stdout.splitlines()[-1].endswith(", 1 split")
    assert "](core/README.md)" in (graph / "core.md").read_text(encoding="utf-8")
    assert not (graph / "core" / "02-earlier.md").exists() and not (graph / "stale.md").exists()
    assert not (repo / "graphify-out" / "wiki").exists() and (repo / "graphify-out" / "graph.json").is_file()


def test_a_machine_without_graphify_is_told_how_to_install_it(tmp_path):
    repo = checkout(tmp_path)
    bare = tmp_path / "bin"
    bare.mkdir()
    (bare / "dirname").symlink_to(shutil.which("dirname"))

    done = graph_sh(repo, tmp_path, {"PATH": str(bare)})

    assert done.returncode == 3
    assert "graphify is not installed" in done.stderr and "uv tool install graphifyy==0.9.64" in done.stderr
    assert not (repo / "graphify-out").exists() and not (repo / "wiki").exists()


@pytest.mark.skipif(shutil.which("graphify") is None, reason="graphify is not installed (graphifyy 0.9.64)")
def test_real_graphify_reads_no_ignored_path_and_no_earlier_build(tmp_path):
    repo = checkout(tmp_path)
    files = {
        "pkg/core.py": "def load(path):\n    return parse(path)\n\n\ndef parse(path):\n    return str(path)\n",
        "pkg/use.py": "from pkg.core import load\n\n\ndef main():\n    return load('x')\n",
        "pkg/context/state.py": "def state():\n    return 1\n",
        "docs/exec-plans/active/p/00-index.md": "# Plan p\n\n## Task order\n",
        "context/raw.py": "def raw():\n    return 1\n",
        "schemas/thing.schema.json": '{"type": "object"}\n',
        "plugins/p/vendor.mjs": "export function vendor() {\n  return 1;\n}\n",
        "evals/case.py": "def case():\n    return 1\n",
        ".obsidian/app.json": "{}\n",
        "wiki/graph/old.md": "# old\n",
    }
    for rel, text in files.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    (repo / "wiki" / "plans").symlink_to("../docs/exec-plans/active")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    env = {key: value for key, value in os.environ.items() if key != "GRAPHIFY_OUT"}

    done = graph_sh(repo, repo, env, timeout=300)

    assert done.returncode == 0, done.stderr
    nodes = json.loads((repo / "graphify-out" / "graph.json").read_text(encoding="utf-8"))["nodes"]
    sources = {node["source_file"] for node in nodes if node.get("source_file")}
    assert {src for src in sources if not src.startswith("ops/")} == {
        "pkg/core.py",
        "pkg/use.py",
        "pkg/context/state.py",
        "docs/exec-plans/active/p/00-index.md",
    }
    assert (repo / "wiki" / "graph" / "index.md").read_text(encoding="utf-8").startswith("# Code graph\n")
    assert (repo / "wiki" / "graph" / "_index" / "pkg.md").is_file()
    assert not (repo / "wiki" / "graph" / "old.md").exists()


def test_generated_paths_are_ignored_and_the_shared_obsidian_settings_are_not():
    ignored = [
        "graphify-out/graph.json",
        "graphify-out/GRAPH_REPORT.md",
        "wiki/graph/index.md",
        "wiki/graph/_index/docs.md",
        ".obsidian/workspace.json",
        ".obsidian/workspace-mobile.json",
        ".obsidian/plugins/x/data.json",
        ".vault-meta/transactions/op/journal.json",
    ]
    kept = [
        ".obsidian/app.json",
        ".obsidian/appearance.json",
        ".obsidian/core-plugins.json",
        ".obsidian/graph.json",
        ".obsidian/snippets/vault-colors.css",
        ".vault-meta/lint-allowlist.json",
        "wiki/index.md",
        "wiki/plans",
    ]

    done = subprocess.run(
        ["git", "-c", "core.excludesFile=/dev/null", "check-ignore", "--no-index", *ignored, *kept],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )

    assert done.stdout.splitlines() == ignored
    lines = (REPO / ".graphifyignore").read_text(encoding="utf-8").splitlines()
    assert lines[1:4] == ["evals/results/", ".claude/worktrees/", ".venv/"]
    new = [
        "/context/",
        "schemas/**/*.json",
        "plugins/**/*.mjs",
        "evals/",
        "graphify-out/",
        "wiki/graph/",
        "wiki/plans/",
        ".obsidian/",
        ".raw/",
        ".vault-meta/",
        "inbox/",
    ]
    assert [pattern for pattern in new if pattern not in lines] == []
    variables = yaml.safe_load((REPO / "docs" / "template" / "variables.yaml").read_text(encoding="utf-8"))
    assert {"graphify-out/", "wiki/graph/"} <= set(variables["skip"])


def test_the_vault_lint_leaves_the_generated_graph_alone():
    """V7: the 600 and more pages of wiki/graph/ are no vault page; without this entry `just validate` fails in a project
    that built its graph (ambiguous targets, duplicate basenames, missing frontmatter)."""
    allowlist = json.loads((REPO / ".vault-meta" / "lint-allowlist.json").read_text(encoding="utf-8"))
    assert "wiki/graph/*" in allowlist["exclude"]


def test_the_graph_recipe_runs_the_script():
    justfile = (REPO / "justfile").read_text(encoding="utf-8")

    assert "\ngraph:\n    bash ops/graph.sh\n" in justfile
    assert "    graphify update .\n" not in justfile


def test_the_map_sends_agents_to_graphify_query_and_the_owner_to_the_layered_index():
    claude = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    section = claude.split("\n## Knowledge graph\n", 1)[1].split("\n## ", 1)[0]

    for text in (
        'graphify query "<question>" --budget 1500',
        "wiki/graph/index.md",
        "bash ops/graph.sh",
        "The git hooks in `.githooks/` run it after each commit, merge (`git pull`) and checkout",
        "`GRAPH_SKIP=1` skips it",
        "sets `core.hooksPath` to `.githooks`",
    ):
        assert text in section, text
    for text in (
        "graphify install --project",
        "graphify claude install",
        "graphify hook install",
        "invoke the `graphify` skill",
        "after `git pull`",
        "](wiki/graph",
        "](graphify-out",
    ):
        assert text not in claude, text
    assert "`just graph` — rebuild the code graph (`bash ops/graph.sh`)" in claude
    runbooks = (REPO / "docs" / "runbooks" / "README.md").read_text(encoding="utf-8").splitlines()
    rows = [line for line in runbooks if line.startswith("| the code graph is missing or out of date")]
    assert len(rows) == 1 and "`bash ops/graph.sh`" in rows[0] and "core.hooksPath" in rows[0]


def test_the_git_hooks_refresh_the_graph_after_each_commit_checkout_and_merge(tmp_path):
    repo = checkout(tmp_path)
    shutil.copytree(REPO / ".githooks", repo / ".githooks")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    env = dict(fake_graphify(tmp_path), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    for args in (
        "init -q -b main",
        "config core.hooksPath .githooks",
        "add -A",
        "commit -q -m base",  # post-commit
        "checkout -q -b side",  # post-checkout
        "commit -q --allow-empty -m side",  # post-commit
        "checkout -q main",  # post-checkout
        "merge -q --ff-only side",  # post-merge, as at the end of `git pull`
    ):
        done = subprocess.run([*git, *args.split()], cwd=repo, env=env, capture_output=True, text=True, check=False)
        assert done.returncode == 0 and not done.stderr, (args, done.stderr)

    once = [f"update . | graphify-out | {repo.resolve()}", f"export wiki | graphify-out | {repo.resolve()}"]
    assert (tmp_path / "calls.log").read_text(encoding="utf-8").splitlines() == once * 5
    assert (repo / "wiki" / "graph" / "index.md").read_text(encoding="utf-8").startswith("# Code graph\n")


def test_the_hooks_form_never_fails_and_says_when_the_graph_was_not_refreshed(tmp_path):
    repo = checkout(tmp_path)
    env = fake_graphify(tmp_path)
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "graphify").write_text("#!/bin/sh\nexit 4\n", encoding="utf-8")
    (broken / "graphify").chmod(0o755)

    runs = [
        graph_sh(repo, tmp_path, dict(env, GRAPH_SKIP="1"), "--quick"),
        graph_sh(repo, tmp_path, {"PATH": str(tmp_path / "nothing")}, "--quick"),
        graph_sh(repo, tmp_path, dict(env, PATH=f"{broken}{os.pathsep}{os.environ['PATH']}"), "--quick"),
        graph_sh(repo, tmp_path, env, "--full"),
    ]

    assert [run.returncode for run in runs] == [0, 0, 0, 2]
    assert [run.stdout + run.stderr for run in runs[:2]] == ["", ""] and runs[2].stdout == ""
    assert runs[2].stderr == "graph: the code graph was not refreshed (exit 4); bash ops/graph.sh shows why\n"
    assert runs[3].stderr == "usage: bash ops/graph.sh [--quick]\n"
    assert not (tmp_path / "calls.log").exists() and not (repo / "wiki").exists()
