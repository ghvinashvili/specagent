"""Attack tests for the closed-path boundary of run 20261009-022929-fix-w1-revise (R3, R6, R7, R8; plan D5, D10,
D11). Each asserts a promise the plan makes, by the names the plan gives (access.unreadable, access.settings_closed,
gates._common.closed_paths, gates._common.scope_check, gates._common.locator_problems, gates.read.opened). New file,
self-contained on tmp_path; it reads only the branch's own .claude/settings.json (REPO = parents[3]), never
evals/baseline, the main checkout, the runs root or a network host. A writer may not change this file."""

from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import Path

import pytest
import yaml
from harness import access
from harness.gates import _common, read

REPO = Path(__file__).resolve().parents[3]
POLICY = {
    "schema_version": 1,
    "defaults": {
        "dirs": ["stage"], "blind": False, "brief_drop": [], "cache_ttl": "5m", "plugins": [], "mcp_servers": [],
        "pack_files": [], "repo_deny": ["docs/handoff/**"], "blind_deny": [".claude/agents/**"],
        "never_copy": ["result.json", "logs/**"],
    },
    "types": {
        "reader": {"may_receive": ["brief", "context"], "outputs_of": []},
        "writer": {"may_receive": ["brief"], "outputs_of": [], "changes_repository": True,
                   "repo_deny_extra": ["evals/cases/**"]},
    },
}  # fmt: skip


def project(root: Path, files: dict[str, str] | None = None) -> Path:
    for rel, text in {"docs/roles/need-to-know.yaml": yaml.safe_dump(POLICY), **(files or {})}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    (root / ".claude/settings.json").write_text(
        (REPO / ".claude/settings.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return root


def git(root: Path, *args: str) -> str:
    argv = ["git", "-C", str(root), "-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
    return subprocess.run([*argv, *args], capture_output=True, text=True, check=True).stdout.strip()


def shut(rel: str, patterns) -> bool:
    return any(fnmatch.fnmatchcase(rel, p) for p in patterns)


def test_settings_closed_hides_secret_kinds_at_every_depth_and_leaves_open_files(tmp_path: Path):
    """access.settings_closed closes .env, .env.*, secrets/, *.pem, *.key and *-service-account.json at the root and
    at any depth, and closes no ordinary file."""
    patterns = access.settings_closed(project(tmp_path / "repo"))
    closed = ["secrets/token.txt", "a/b/secrets/deep/k.txt", ".env", "x/.env.local", "a/b/c/.env.production",
              "certs/server.pem", "deep/nest/x.pem", "a.key", "k/a.key", "ops/gcp-service-account.json",
              "a/b/svc-service-account.json"]  # fmt: skip
    opened = ["src/app.py", "docs/environment.md", ".envrc", "secretsmanager.py", "keys.md", "context/sample.txt"]
    assert [p for p in closed if not shut(p, patterns)] == []
    assert [p for p in opened if shut(p, patterns)] == []


def test_the_closed_paths_have_one_owner_and_unreadable_joins_the_settings(tmp_path: Path):
    """access.unreadable is the single owner of a type's closed paths: the row (repo_deny + repo_deny_extra) then,
    with the root, the project settings; no other harness module joins repo_deny_extra to a list of its own."""
    root = project(tmp_path / "repo")
    writer = access.type_row(POLICY, "writer")
    assert access.unreadable(writer) == ["docs/handoff/**", "evals/cases/**"]
    assert access.unreadable(writer, root) == ["docs/handoff/**", "evals/cases/**", *access.settings_closed(root)]
    src = REPO / "packages" / "harness" / "src" / "harness"
    users = sorted(p.relative_to(src).as_posix() for p in src.rglob("*.py") if "repo_deny_extra" in p.read_text())
    assert users == ["access.py"]


def test_closed_paths_falls_back_to_settings_when_the_manifest_or_policy_cannot_be_read(tmp_path: Path):
    """D10: gates._common.closed_paths returns access.settings_closed(root) when the manifest or policy is missing,
    empty or malformed, so a gate that cannot find the type still closes the project's secret files."""
    root = project(tmp_path / "repo")
    base = access.settings_closed(root)
    assert base  # the project settings close something
    run = tmp_path / "run"
    sd = run / "stages" / "x"
    sd.mkdir(parents=True)
    assert sorted(_common.closed_paths(root, run, sd)) == sorted(base)  # no manifest
    (run / "manifest.json").write_text("{not json", encoding="utf-8")
    assert sorted(_common.closed_paths(root, run, sd)) == sorted(base)  # malformed
    (run / "manifest.json").write_text("{}", encoding="utf-8")
    assert sorted(_common.closed_paths(root, run, sd)) == sorted(base)  # empty


@pytest.mark.parametrize(
    ("rel", "change", "refused"),
    [
        ("secrets/token.txt", "delete", True),
        ("a/b/deep.pem", "delete", True),
        (".env.example", "change", True),
        ("ops/x-service-account.json", "delete", True),
        ("src/old.py", "delete", False),
    ],
)
def test_the_scope_check_refuses_a_branch_that_changes_a_settings_closed_file(tmp_path: Path, rel, change, refused):
    """D5 / choice-1b: the write gate's check 'the branch stays out of hidden and closed paths' refuses a branch that
    deletes or changes a file the project settings close, at any depth, and passes a change to an open file."""
    root = project(tmp_path / "repo", {"src/old.py": "A = 1\n", "secrets/token.txt": "t\n", "a/b/deep.pem": "p\n",
                                       ".env.example": "X=\n", "ops/x-service-account.json": "{}\n"})  # fmt: skip
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    run = tmp_path / "run"
    run.mkdir()
    git(root, "checkout", "-q", "-b", "work-1")
    if change == "delete":
        git(root, "rm", "-q", "--", rel)
    else:
        (root / rel).write_text("changed\n", encoding="utf-8")
        git(root, "add", "--", rel)
    git(root, "commit", "-qm", "b")
    git(root, "checkout", "-q", "main")
    scope = _common.scope_check(root, run, {"role_type": "writer"}, "work-1")
    assert scope["name"] == "the branch stays out of hidden and closed paths"
    assert scope["passed"] is (not refused)
    if refused:
        assert rel in scope.get("detail", "")


def read_stage(base: Path, with_files: bool):
    root = project(base / "repo", {"context/sample.txt": "one\ntwo\nthree\n"})
    if with_files:
        for rel, text in {".env": "API_TOKEN=s3cr3t-value\n", "secrets/token.txt": "the service token\n",
                          "certs/server.pem": "CERT LINE ONE\n"}.items():  # fmt: skip
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding="utf-8")
    run = base / "run"
    sd = run / "stages" / "read"
    (sd / "output").mkdir(parents=True)
    (run / "manifest.json").write_text(
        json.dumps({"stages": [{"id": "read", "role_type": "reader"}]}), encoding="utf-8"
    )
    notes = (
        "## context/sample.txt\n\n"
        '- a. Quote: "API_TOKEN=s3cr3t-value" `.env:1`\n'
        '- b. Quote: "anything here" `.env:99`\n'
        '- c. Quote: "the service token" `secrets/token.txt:1`\n'
        '- d. Quote: "CERT LINE ONE" `certs/server.pem:1`\n'
        '- e. Quote: "two" `context/sample.txt:2`\n\n'
        "## Contradictions\n\nnone\n\n## Probes\n\nnone: nothing can be run.\n\n## Coverage\n\nall\n"
    )
    (sd / "output/notes.md").write_text(notes, encoding="utf-8")
    (sd / "output/questions.md").write_text("none\n", encoding="utf-8")
    return [(c["name"], c["passed"], c.get("detail", "")) for c in read.checks(root, run, sd)]


def test_the_read_gate_answers_the_same_about_a_closed_file_whether_it_exists_or_not(tmp_path: Path):
    """R6: the read gate runs outside the sandbox; it must not open a file the project settings close, nor tell a line
    count or a quote apart for one that exists versus one that does not."""
    there, absent = read_stage(tmp_path / "a", True), read_stage(tmp_path / "b", False)
    assert there == absent
    quote = next(c for c in there if c[0] == "every quote stands at its stated location")
    assert "the file has" not in quote[2] and "not at that place" not in quote[2]


def test_the_locator_gives_one_answer_for_an_out_of_stage_path_whether_it_exists_or_not(tmp_path: Path):
    """R7/D11: gates._common._local opens a stage's own file but no file outside the stage; an absolute path into
    another stage, an external absolute path and a `..` climb all return None, the same whether the file exists or
    not, so the locator check reports `no such file` either way and leaks no line count."""
    run = tmp_path / "run"
    sd = run / "stages" / "plan"
    (sd / "output").mkdir(parents=True)
    (sd / "output" / "plan.md").write_text("a\nb\nc\n", encoding="utf-8")
    other = run / "stages" / "verify" / "output"
    other.mkdir(parents=True)
    (other / "report.md").write_text("one\ntwo\nthree\n", encoding="utf-8")  # exists, but another stage
    (run / "state.json").write_text("{}\n", encoding="utf-8")
    external = tmp_path / "outside.txt"
    external.write_text("x\ny\n", encoding="utf-8")
    # a path the stage owns is read; everything outside the stage is None (existing or not)
    assert _common._local(run, sd, "output/plan.md") == ["a", "b", "c"]
    for path in (
        f"{run}/stages/verify/output/report.md",
        f"{run}/stages/verify/output/missing.md",
        f"{run}/state.json",
        str(external),
        str(tmp_path / "missing.txt"),
        "../verify/output/report.md",
        "/etc/hostname",
    ):
        assert _common._local(run, sd, path) is None, path


def test_opened_refuses_absolute_closed_and_climbing_paths(tmp_path: Path):
    """R6/R7: gates.read.opened returns None for an absolute path, a path that climbs out with .., and a closed path,
    whether or not a file stands there."""
    base = tmp_path / "base"
    (base / "sub").mkdir(parents=True)
    (base / "sub" / "f.txt").write_text("x\n", encoding="utf-8")
    (base / ".env").write_text("SECRET\n", encoding="utf-8")
    patterns = access.settings_closed(project(tmp_path / "s"))
    assert read.opened(base, "/etc/hostname") is None
    assert read.opened(base, "../escape.txt") is None
    assert read.opened(base, ".env", patterns) is None  # closed, though the file exists
    assert read.opened(base, "sub/f.txt") == ["x"]  # an open file is read
