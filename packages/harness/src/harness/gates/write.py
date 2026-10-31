"""harness/gates/write.py — the writer stage gate, run per shard: every task proven, tests green on the branch, no credential."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from .. import state
from . import _common
from ._common import TEST_PATH, branch_of, changed_files, check, git, result, scope_check, secrets_check
from ._common import text as stage_text

PAGE_FOLDERS = ("wiki/", "docs/runbooks/", "docs/decisions/")  # spec A2
INDEX_FILES = ("index.md", "log.md", "README.md")  # an index, a log or a folder README is no page
NOT_CODE = ("docs/", "wiki/", "context/")  # documents, pages and raw material; a .md file anywhere is no code either
DOCS_NONE = re.compile(r"none — \S")  # matched at the start of a task's "docs"
PAGES_CHECK = "the code comes with its pages, or every task says docs: none with a reason"


def is_page(path: str) -> bool:
    """A page the pages rule counts: a .md file under PAGE_FOLDERS that is no index, log, README or .summary.md summary."""
    name = path.rsplit("/", 1)[-1]
    return (
        path.startswith(PAGE_FOLDERS)
        and path.endswith(".md")
        and name not in INDEX_FILES
        and not name.endswith(".summary.md")
    )


def is_code(path: str) -> bool:
    """A path the pages rule counts as code: outside NOT_CODE and not a .md file (tests, configuration, schemas, CI)."""
    return not path.startswith(NOT_CODE) and not path.endswith(".md")


def pages_problem(changed: list[str], tasks: list[dict], planned: list[dict]) -> str:
    """The detail of the failed pages check, or "" when it passes (spec A2, ADR-0027)."""
    if not any(is_code(p) for p in changed) or any(is_page(p) for p in changed):
        return ""
    docs = {t.get("id"): t.get("docs") for t in planned}  # the planner's word; a task's own "docs" is never read
    lacking = [t["id"] for t in tasks if not DOCS_NONE.match(str(docs.get(t["id"]) or ""))]
    if tasks and not lacking:
        return ""
    return "no page under wiki/, docs/runbooks/ or docs/decisions/; no docs: none — <reason> on " + ", ".join(lacking)


def planned_tasks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    """The planner's tasks the launcher took this stage's tasks.json from (launch.split_tasks, own_tasks), read where
    no writer writes; [] when the stage's row names no task list or it cannot be read."""
    try:
        stage_id = stage_dir.relative_to(run_dir / "stages").parts[0]  # a shard's folder is stages/<id>/<NN>
        table = state.table_path(root, _common._manifest(run_dir).get("pipeline", "default"))
        row = next(r for r in yaml.safe_load(table.read_text(encoding="utf-8"))["stages"] if r.get("id") == stage_id)
        dep, rel = next(i for i in row["inputs"] if i.endswith(":tasks.json")).split(":", 1)  # as split_tasks does
        tasks = json.loads((run_dir / "stages" / dep / rel).read_text(encoding="utf-8"))["tasks"]
    except (OSError, ValueError, LookupError, TypeError, AttributeError, StopIteration, yaml.YAMLError):
        return []  # no task is exempt: the safer side
    return [t for t in tasks if isinstance(t, dict)] if isinstance(tasks, list) else []


def session_checks(root: Path, run_dir: Path, stage_dir: Path) -> list[dict]:
    """The gate without the test suite it runs outside any session: what the stop hook holds a writer to."""
    return checks(root, run_dir, stage_dir, suite=False)


def report_problem(root: Path, stage_dir: Path, tasks: list[dict], branch: str | None) -> str:
    """What `report.md` of the shard lacks, or an empty string. The report is what the author states about its work:
    the session that verifies the work checks it statement by statement, so it names the commits and has an entry
    for every task. Without it a verifier has the task list alone, and what the author decided or noticed beyond
    the plan reaches nobody."""
    report = stage_text(stage_dir, "report.md")
    if not report.strip():
        return "report.md is missing beside tasks.json"
    absent = [t["id"] for t in tasks if t["id"] not in report]
    if absent:
        return "no entry for " + ", ".join(absent[:6])
    if branch:
        base = git(root, "merge-base", "HEAD", branch).stdout.strip()
        commits = git(root, "rev-list", f"{base}..{branch}").stdout.split()
        if commits and not any(c[:7] in report for c in commits):
            return "none of the commits of the branch is named"
    return ""


def _unexpected(evidence: list[dict]) -> list[str]:
    """The evidence entries without a command, or whose command did not end as it should."""
    # 0 unless the entry says the command is meant to fail (`expected_exit_code`): a check that has to report a problem
    return [
        str(e.get("command") or e.get("claim", ""))[:60]
        for e in evidence
        if not e.get("command") or "exit_code" not in e or e["exit_code"] != e.get("expected_exit_code", 0)
    ]


def _seen_to_fail(changed: list[str], evidence: list[dict]) -> list[dict]:
    """The check that a changed test was seen to fail, on a branch that changes a test; [] on any other branch."""
    if not any(TEST_PATH.search(f) for f in changed):
        return []
    # a test that cannot fail proves nothing: the author broke the behaviour once and saw the test catch it
    caught = [e for e in evidence if e.get("expected_exit_code") and e.get("exit_code") == e["expected_exit_code"]]
    hint = "an evidence entry of a test run that failed as expected (`expected_exit_code`) on a broken copy"
    return [check("a test was seen to fail when the behaviour is broken", bool(caught), hint)]


def checks(root: Path, run_dir: Path, stage_dir: Path, suite: bool = True) -> list[dict]:
    path = _common.stage_file(stage_dir, "tasks.json")  # None for a link out of the stage directory
    tasks = json.loads(path.read_text(encoding="utf-8"))["tasks"] if path else []
    res = result(stage_dir)
    evidence = res.get("evidence", [])
    unexpected = _unexpected(evidence)
    out = [
        check("the shard has tasks", bool(tasks)),
        check(
            "every task passes",
            bool(tasks) and all(t["passes"] for t in tasks),
            ", ".join(t["id"] for t in tasks if not t["passes"]),
        ),
        check("every passed task carries evidence", all(t.get("evidence", "").strip() for t in tasks if t["passes"])),
        check("result.json has one evidence entry per task at least", len(evidence) >= len(tasks)),
        check(
            "every evidence entry names its command, and the command ended as it should",
            bool(evidence) and not unexpected,
            "; ".join(unexpected[:5]),
        ),
    ]
    branch = branch_of(root, res)
    out.append(check("result.json names the branch of the work", branch is not None))
    lacking = report_problem(root, stage_dir, tasks, branch)
    out.append(check("report.md states the work: its commits and every task", not lacking, lacking))
    if branch:
        code = [o["path"] for o in res.get("outputs", []) if o.get("kind") == "code"]
        missing = [p for p in code if git(root, "cat-file", "-e", f"{branch}:{p}").returncode != 0]
        out.append(check("every output of kind code exists on the branch", not missing, ", ".join(missing[:5])))
        changed = changed_files(root, branch)
        detail = pages_problem(changed, tasks, planned_tasks(root, run_dir, stage_dir))
        out.append(check(PAGES_CHECK, not detail, detail))
        out += _seen_to_fail(changed, evidence)
        out.append(scope_check(root, run_dir, res, branch))
        given, unread = _common.protected_tests(root, run_dir, stage_dir)  # the plan's and the critic's tests
        differ = [rel for rel, data in sorted(given.items()) if _common.blob(root, branch, rel) != data]
        out.append(check("the plan's and the critic's tests are on the branch as given", not differ and not unread,
                         unread or ", ".join(differ[:5])))  # fmt: skip
        if suite:
            ran = _common.suite_checks(root, branch, given)
            out += ran
            record_checks(stage_dir, ran[:1])
        out.append(secrets_check(root, branch))
    elif suite:
        record_checks(stage_dir, [])
    return out


def record_checks(stage_dir: Path, done: list[dict]) -> None:
    """`checks.json` of the shard: what the harness itself ran on the work, outside any session. The stage that
    reviews the work receives it as material about the work (a command and how it ended), not as a verdict: a
    session whose sandbox cannot run the whole suite cites it instead of leaving the claim unchecked. The file is
    replaced, not written into: the sandbox may have left an empty, read-only one there (the mount point of its
    denyWrite rule)."""
    rows = [
        {
            "command": " ".join(_common.TEST_CMD),
            "exit_code": 0 if c["passed"] else 1,
            "output_tail": c.get("detail", ""),
        }
        for c in done
    ]
    record = {
        "schema_version": 1,
        "ran": "by the harness on the branch of this shard, outside any session",
        "checks": rows,
    }
    state.write_atomic(stage_dir / "checks.json", json.dumps(record, indent=2) + "\n")
