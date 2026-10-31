"""The repository paths a role session may not read have one owner (access.unreadable): its type's row and the paths the
project's own settings close to every session. The write gate refuses a branch that changes one (R3 of run
20261009-022929-fix-w1-revise), the read gate, its probe check and the locator check open none of them and nothing
outside the stage, and answer alike whether such a path exists or not (R6, R7, R8), and the launcher puts none of them
into a session's material (docs/decisions/0025)."""

from __future__ import annotations

import fnmatch
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from harness import access, launch, pack
from harness.gates import _common, read

REPO = Path(__file__).resolve().parents[3]
POLICY = {
    "schema_version": 1,
    "defaults": {
        "dirs": ["stage"], "blind": False, "brief_drop": [], "cache_ttl": "5m", "plugins": [], "mcp_servers": [],
        "pack_files": [], "repo_deny": ["docs/handoff/**"], "blind_deny": [".claude/agents/**"],
        "never_copy": ["result.json", "progress.md", "prompt.md", "pack.md", "gate.json", "escalation.json", "logs/**",
                       "input/**"],
    },
    "types": {
        "reader": {"may_receive": ["brief", "context"], "outputs_of": []},
        "planner": {"may_receive": ["brief"], "outputs_of": ["reader"], "trial_checkout": True},
        "writer": {"may_receive": ["brief"], "outputs_of": ["planner"], "changes_repository": True,
                   "repo_deny_extra": ["evals/cases/**"]},
        "verifier": {"may_receive": ["brief"], "outputs_of": ["writer"], "blind": True, "alias": {"writer": "work"}},
    },
}  # fmt: skip
CLOSED = [".env", ".env.example", "deploy/.env.production", "secrets", "secrets/token.txt", "pkg/secrets/key.txt",
          "certs/server.pem", "a.key", "ops/gcp-service-account.json"]  # fmt: skip
OPEN = ["src/app.py", "docs/environment.md", ".envrc", "secretsmanager.py", "keys.md", "context/sample.txt"]


def project(root: Path, files: dict[str, str] | None = None) -> Path:
    """A repository with the project's own settings, a policy of four types and the given files."""
    for rel, text in {"docs/roles/need-to-know.yaml": yaml.safe_dump(POLICY), **(files or {})}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / ".claude" / "settings.json", root / ".claude" / "settings.json")
    return root


def git(root: Path, *args: str) -> str:
    argv = ["git", "-C", str(root), "-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
    return subprocess.run([*argv, *args], capture_output=True, text=True, check=True).stdout.strip()


def shut(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(rel, p) for p in patterns)


def test_the_project_settings_close_their_secret_files_to_every_session(tmp_path: Path):
    """The `Read(...)` deny rules and `sandbox.filesystem.denyRead` of .claude/settings.json, as globs from the
    repository root that hold below a closed folder and at any depth."""
    patterns = access.settings_closed(project(tmp_path / "repo"))
    assert [p for p in CLOSED if not shut(p, patterns)] == []
    assert [p for p in OPEN if shut(p, patterns)] == []


@pytest.mark.parametrize("content", ["", "{", "[]", "null", '{"permissions": []}', '{"permissions": {"deny": "x"}}',
                                     '{"sandbox": {"filesystem": {"denyRead": [1, null, {}]}}}', "DIR", "LINK"])  # fmt: skip
def test_a_settings_file_that_cannot_be_read_adds_nothing_and_raises_nothing(tmp_path: Path, content: str):
    """An empty, broken or wrongly shaped settings.local.json, a folder or a link in its place (seen in a role
    session's sandbox: an empty stub) leaves the closed paths of settings.json as they are."""
    root = project(tmp_path / "repo")
    alone = access.settings_closed(root)
    local = root / ".claude" / "settings.local.json"
    if content == "DIR":
        local.mkdir()
    elif content == "LINK":
        (tmp_path / "other.json").write_text('{"permissions": {"deny": ["Read(./src/**)"]}}', encoding="utf-8")
        local.symlink_to(tmp_path / "other.json")
    else:
        local.write_text(content, encoding="utf-8")
    assert access.settings_closed(root) == alone


def test_a_settings_rule_outside_the_repository_closes_nothing_inside_it(tmp_path: Path):
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    deny = ["Read(~/.ssh/**)", "Read(//etc/**)", f"Read(/{'private'}/**)", f"Read(/{root.as_posix()}/vault/**)",
            "Bash(curl *)", "Edit(./src/**)"]  # fmt: skip
    (root / ".claude/settings.json").write_text(json.dumps({"permissions": {"deny": deny}}), encoding="utf-8")
    patterns = access.settings_closed(root)
    assert shut("private/a.txt", patterns) and shut("vault/a.txt", patterns)
    assert not shut("src/app.py", patterns) and not shut("etc/hosts", patterns) and not shut(".ssh/id", patterns)


def test_the_closed_paths_of_a_type_are_its_row_and_then_the_project_settings(tmp_path: Path):
    root = project(tmp_path / "repo")
    writer, verifier = access.type_row(POLICY, "writer"), access.type_row(POLICY, "verifier")
    assert access.unreadable(writer) == ["docs/handoff/**", "evals/cases/**"]
    assert access.unreadable(writer, root) == ["docs/handoff/**", "evals/cases/**", *access.settings_closed(root)]
    assert ".claude/agents/**" in access.unreadable(verifier)  # a blind type's row holds blind_deny


@pytest.fixture()
def branch_rig(tmp_path: Path):
    """A repository whose base tracks a file of every closed kind and a plain one, and a run of a writer."""
    root = project(tmp_path / "repo", {"src/old.py": "A = 1\n", "secrets/token.txt": "t\n", "certs/server.pem": "p\n",
                                       "deploy/.env.production": "X=1\n", ".env.example": "X=\n"})  # fmt: skip
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    run = tmp_path / "runs" / "20261009-000000-r1"
    run.mkdir(parents=True)
    return root, run


@pytest.mark.parametrize(
    ("path", "change", "passes"),
    [("secrets/token.txt", "delete", False), ("certs/server.pem", "delete", False),
     ("deploy/.env.production", "delete", False), (".env.example", "change", False), ("src/old.py", "delete", True)],
)  # fmt: skip
def test_a_branch_that_changes_a_file_the_project_settings_hide_is_refused(branch_rig, path, change, passes):
    """R3, the effect check: a sandboxed shell sees a closed folder empty and a closed file as a device, so a whole-tree
    `git add` or `git commit` stages the deletion or the change of a file its author could not read. The write gate's
    scope check refuses such a branch, whatever command made it; a deletion of a file the author could read, which a
    plan may ask for, passes."""
    root, run = branch_rig
    git(root, "checkout", "-q", "-b", "work-1")
    if change == "delete":
        git(root, "rm", "-q", path)
    else:
        (root / path).write_text("changed\n", encoding="utf-8")
        git(root, "add", path)
    git(root, "commit", "-qm", "the branch")
    git(root, "checkout", "-q", "main")
    scope = _common.scope_check(root, run, {"role_type": "writer"}, "work-1")
    assert scope["passed"] is passes
    assert passes or path in scope["detail"]


def read_stage(base: Path, with_files: bool) -> list[tuple]:
    """A reader's stage whose notes cite closed files; the files exist only `with_files`. What the read gate says."""
    root = project(base / "repo", {"context/sample.txt": "one\ntwo\nthree\n"})
    if with_files:
        for rel, text in {".env": "API_TOKEN=s3cr3t-value\n", "secrets/token.txt": "the token of the service\n",
                          "certs/server.pem": "CERTIFICATE LINE ONE\n", "deploy/.env.local": "LOCAL=value here\n"}.items():  # fmt: skip
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding="utf-8")
    run = base / "runs" / "20261009-000000-r1"
    sd = run / "stages" / "read"
    (sd / "output").mkdir(parents=True)
    (run / "manifest.json").write_text(
        json.dumps({"stages": [{"id": "read", "role_type": "reader"}]}), encoding="utf-8"
    )
    notes = (
        "## context/sample.txt\n\n"
        '- a. Quote: "API_TOKEN=s3cr3t-value" `.env:1`\n'
        '- b. Quote: "anything at all here" `.env:99`\n'
        '- c. Quote: "the token of the service" `secrets/token.txt:1`\n'
        '- d. Quote: "CERTIFICATE LINE ONE" `certs/server.pem:1`\n'
        '- e. Quote: "LOCAL=value here" `deploy/.env.local:1`\n'
        '- f. Quote: "two" `context/sample.txt:2`\n\n'
        "## Contradictions\n\n"
        '1. The token. `.env:1`: "API_TOKEN=s3cr3t-value" against `secrets/token.txt:1`: "the token of the service"\n\n'
        "## Probes\n\nnone: nothing in the material can be run.\n\n## Coverage\n\nall\n"
    )
    (sd / "output/notes.md").write_text(notes, encoding="utf-8")
    (sd / "output/questions.md").write_text("none\n", encoding="utf-8")
    return [(c["name"], c["passed"], c.get("detail", "")) for c in read.checks(root, run, sd)]


def test_the_read_gate_answers_the_same_about_a_closed_file_whether_it_exists_or_not(tmp_path: Path):
    """R6: the read gate runs outside the sandbox and its details reach the session; it opened `.env` and the other
    files the project's settings close to every session, and told a line count or a quote apart."""
    there, absent = read_stage(tmp_path / "a", True), read_stage(tmp_path / "b", False)
    assert there == absent
    quote = next(c for c in there if c[0] == "every quote stands at its stated location")
    assert "the file has" not in quote[2] and "not at that place" not in quote[2]


def test_the_locator_check_opens_nothing_outside_the_stage_and_the_repository(tmp_path: Path):
    """R7: an absolute path outside the run and the repository was opened and its line count reported; so were another
    stage's file, the run's state.json and a path that climbs out of the stage with `..`. Each is now `no such file`,
    the same whether it exists or not; the stage's own files and the repository's are read as before, and a file the
    project's settings close is no file of the repository."""
    root = project(tmp_path / "repo", {"src/app.py": "a = 1\nb = 2\nc = 3\n", "secrets/token.txt": "t\n",
                                       "deploy/.env.production": "X=1\nY=2\n"})  # fmt: skip
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("".join(f"token-{n}\n" for n in range(1, 8)), encoding="utf-8")
    run = tmp_path / "runs" / "20261009-000000-r1"
    manifest = {"base_commit": git(root, "rev-parse", "HEAD"),
                "stages": [{"id": "plan", "role_type": "planner"}, {"id": "verify", "role_type": "verifier"}]}  # fmt: skip
    (run / "stages/verify/output").mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run / "state.json").write_text('{"stages": {}}\n', encoding="utf-8")
    (run / "stages/verify/output/report.md").write_text("one\ntwo\nthree\n", encoding="utf-8")
    sd = run / "stages" / "plan"
    (sd / "output").mkdir(parents=True)
    refused = [f"{outside}/secret.txt:99", f"{outside}/missing.txt:99", "../../../../outside/secret.txt:99",
               "../../../../outside/missing.txt:99", f"{run}/stages/verify/output/report.md:99", f"{run}/state.json:99",
               "secrets/token.txt:99", "deploy/.env.production:99"]  # fmt: skip
    kept = ["output/plan.md:1", "src/app.py:2", f"{sd}/output/plan.md:1"]
    text = "# Plan\n\n" + "".join(f"- `{loc}`\n" for loc in [*refused, *kept, "src/app.py:9"])
    (sd / "output/plan.md").write_text(text, encoding="utf-8")
    problems = _common.locator_problems(root, run, sd)
    said = {p.split("` in ", 1)[0].strip("`"): p.rsplit(": ", 1)[1] for p in problems}
    assert said == {**{loc: "no such file" for loc in refused}, "src/app.py:9": "the file has 3 lines"}


def test_the_probe_check_answers_the_same_about_a_path_outside_the_stage_whether_it_exists_or_not(tmp_path: Path):
    """R8: a probe entry's `..` took the check out of the stage, and it told an existing file from a missing one."""
    sd = tmp_path / "runs" / "20261009-000000-r1" / "stages" / "read"
    (sd / "output" / "probes").mkdir(parents=True)
    (sd / "output/probes/real.txt").write_text("$ tool\nexit 0\n", encoding="utf-8")
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "secret.txt").write_text("x\n", encoding="utf-8")
    climb = "probes/../" + os.path.relpath(tmp_path / "outside", sd / "output")
    body = (f"- p1. Does it run? `output/{climb}/secret.txt`\n- p2. And this? `output/{climb}/missing.txt`\n"
            "- p3. The real one. `output/probes/real.txt`\n")  # fmt: skip
    problems = read.probe_problems(sd, body)
    assert sorted(problems) == sorted(f"{climb}/{name}: no such file" for name in ("secret.txt", "missing.txt"))


def test_a_file_the_project_settings_close_is_never_material(tmp_path: Path):
    """The launcher runs outside the sandbox: a closed file that an earlier stage's text cites, names, or that a brief
    lists, is not put into a session's system prompt."""
    root = project(tmp_path / "repo", {"secrets/notes.md": "# Notes\nsecret words of the vault\n",
                                       "src/app.py": "def vault():\n    return 1\n"})  # fmt: skip
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    inp = tmp_path / "runs" / "r1" / "stages" / "plan" / "input"
    (inp / "read").mkdir(parents=True)
    (inp / "brief.md").write_text("# Brief\n\n## Goal of this run\nRead the vault notes.\n", encoding="utf-8")
    (inp / "read/notes.md").write_text("- The vault, `secrets/notes.md:2`; see `secrets/notes.md` and `src/app.py:1`\n",
                                       encoding="utf-8")  # fmt: skip
    row = {"id": "plan", "role_type": "planner", "inputs": ["brief", "read:output/"]}
    chosen = launch.stage_material(root, POLICY, row, inp)["extra"]
    assert chosen and not [piece for piece in chosen if piece[0].startswith("secrets/")]
    given = pack.material_parts(root, POLICY, "planner", ["secrets/notes.md", "src/app.py"])["given"]
    assert [g["piece"] for g in given] == ["src/app.py"]


def test_the_closed_paths_have_one_owner():
    """One function builds a type's closed paths (access.unreadable); no other module of the harness joins
    `repo_deny_extra` to its own list."""
    src = REPO / "packages" / "harness" / "src" / "harness"
    users = sorted(p.relative_to(src).as_posix() for p in src.rglob("*.py") if "repo_deny_extra" in p.read_text())
    assert users == ["access.py"]
