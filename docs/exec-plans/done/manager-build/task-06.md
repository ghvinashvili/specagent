# Task 6 — The garbage collector: dry run, the save check, the refusals, the deletion

planner: c
builder: c
depends_on: —
files: `S/scripts/collect_run.py` (new), `S/scripts/tests/test_collect_run.py` (new), `S/scripts/README.md` (a ``### `collect_run.py` `` section at the end of the section that holds ``### `clean_jobs_tmp.py` ``); `S/scripts/clean_jobs_tmp.py` is not touched (the collector does not call it, departure 7); S = `.claude/skills/running-specagent-pipelines`
acceptance: 10.14 (all three refusals and the afterwards clause, by the tests of Step 1; the verifier re-runs them, Step 5)

All paths below are relative to the checkout; `S` is the skill folder above. Builder C starts from
`feat/manager-build-c` at f70e84c (main). The skill's files there are identical to the plan branch's at 4f0c974
(`git diff --stat f70e84c 4f0c974 -- .claude/skills/running-specagent-pipelines` prints nothing), where every figure
below was measured. Standard library only, Python 3.12 (D2); no letter of a refused block anywhere (D1).

## Goal

A skill run's leftovers go only after its record is checked as saved (spec 5.9.4, 8.2.13, 8.3.6, TD-010, question 4).
`collect_run.py` lists every deletion with what it loses (the run's worktrees and branches, `scratch/`, the job folders
of the run's sessions, the paths the manager names), runs the save check, refuses when any part of it fails, and
deletes only with `--apply`: on the owner's yes for the exact list (`--yes <digest>`) for three runs, then by the
standing rule, after which the owner reads `collected.md` in the run folder. Order: save, verify the save, delete.

## Departures (from the spec, with the reason)

1. The check "every lesson of the run is in lessons.md and in the skill" (5.9.4) has no form in the spec. Here: each
   item of `## Lessons from this run` carries a mark `(skill: <sha>)`, the commit that carried it into the skill, which
   must be an ancestor of the main branch, or `(skill: none)` for a lesson that stays with the run; an item that records
   a merge (`Merged: <x> at <sha>`, `lessons.md` Read first 3) is not a lesson. A script cannot judge whether a rule's
   meaning reached the skill; it can check that the manager marked each one and that the commit is merged.
2. Stricter than the spec's list of checks: a run worktree with uncommitted or untracked paths, a worktree HEAD or a
   branch with commits not in the main branch, and a session of the run still running are refusals too. Each of those
   deletions would lose work that is not saved ("save, verify the save, then delete"). An untracked path that
   holds nothing is no work but the sandbox's mount point (C505: this run's plan worktree holds five, `.mcp.json`
   files and a `.claude/` of 0-byte files): it is counted apart, never refused, and removed right before its
   worktree, since `git worktree remove` without `--force` refuses any untracked file.
3. "The final commit is merged": every `Task N: done — <sha>` line of the run's build logs (`check_formats.py:43`'s
   form) and each `--final` must be an ancestor of the main branch; when none is named the check fails. The spec names
   one commit; the build logs name each commit the run built, so none can be left out.
4. Eval result copies and preview copies (5.9.4) are named by `--also`: no file of a run lists them today.
5. The owner's yes (question 4 (a)) is bound to the list it was given for: the dry run prints a 12-hex digest of the
   deletions and `--apply` needs `--yes <digest>`; a list that changed since (a branch moved, a worktree added) needs a
   new yes. The standing rule (question 4 (b)) starts once the history file next to the run folder records three runs
   applied with a yes; `--apply` alone then runs when the check passes, and the owner reads `collected.md` afterwards.
6. "The manager runs it, never a sandboxed role": the collector reads the run's agents file under `_control/` first,
   which every role's settings deny (10.15; this planner's own settings deny `<run>/_control`), so a role's call stops
   at exit 2 before anything is listed. No sandbox test by environment variable: none was verified.
7. The job outputs (5.9.4, 10.14 "`~/.claude/jobs` show nothing of the run"): the whole `<jobs>/<id>/` folder of each
   finished session of the run, matched by the row's `name` and `cwd` against the agents file. `clean_jobs_tmp.py`
   (the `tmp/` of any finished job) stays as it is and is not called.

## Contracts (what Task 6 provides; `manager/plan-fixer` carries them into the tasks named)

- K1 for Task 11 (the tracker rows of the Deferred items, index row 11 and Coverage :152): the collector counts a
  Deferred item as "in the tracker" when its text names a `TD-NNN` that is a row of
  `docs/exec-plans/tech-debt-tracker.md` on the main branch, or when a row of that file contains the item's key: the
  item's first line up to its first `: ` (the whole first line when it has none), compared without backticks, with
  whitespace collapsed, case-insensitive. Deferred items are the `- ` and `N. ` items under each `## Deferred…` or
  `### Deferred…` heading of the `*.md` files directly in the plan folder (the index and the task files), outside
  fenced code (the tasks' test fixtures hold such headings: none of their items needs a row). So each row
  Task 11 adds for a Deferred item quotes the item's key in its Plan cell, e.g.
  `manager-build Deferred: 8.3.17 per-plugin start-up cost`; an item that already names a row (TD-003, TD-004, TD-005)
  needs nothing.
- K2 for Task 7 (`docs/roles/manager-chat.md`, the manager's steps after a run): before the collector, the manager marks
  each item of `## Lessons from this run` with `(skill: <sha>)` or `(skill: none)` (departure 1); then it runs
  `python3 -I <skill>/scripts/collect_run.py <run> --repo <checkout> --plan <plan folder> --kept <page> …`, shows the
  owner the list, and on the owner's yes runs it again with `--apply --yes <digest>`; after three such runs `--apply`
  alone, and the owner reads `<run>/collected.md`.

## Interfaces

`S/scripts/collect_run.py`, run as `python3 -I scripts/collect_run.py` (the tests call only this command line):

```
collect_run.py RUN_DIR --repo DIR --plan PATH --kept PATH [--kept PATH ...] [--main BRANCH] [--final SHA ...]
               [--worktree DIR ...] [--branch NAME ...] [--also PATH ...] [--agents FILE] [--jobs DIR]
               [--history FILE] [--apply] [--yes DIGEST]
```

| Option | Meaning | Default |
| --- | --- | --- |
| `RUN_DIR` | the run folder; kept, except its `scratch/` | required |
| `--repo DIR` | the main worktree of the run's repository (never removed) | required |
| `--plan PATH` | the plan folder, relative to the repository, read on the main branch | required |
| `--kept PATH` | a file or folder that must exist before and after (the measurement page, the summaries); repeatable | required, at least one |
| `--main BRANCH` | the branch everything must be merged into | `main` |
| `--final SHA` | a commit that must be an ancestor of `--main`, besides the build logs' done lines; repeatable | none |
| `--worktree DIR` | a run worktree no agent's `cwd` names (a verifier's checkout); repeatable | none |
| `--branch NAME` | a run branch with no worktree; repeatable | none |
| `--also PATH` | an eval result copy or preview copy to remove; repeatable | none |
| `--agents FILE` | the run's agents file (the watcher's) | `RUN_DIR/_control/_agents.json` |
| `--jobs DIR` | the background jobs folder | `~/.claude/jobs` |
| `--history FILE` | the runs applied so far, one JSON line each | `RUN_DIR/../collect-history.jsonl` |
| `--apply` | remove; without it nothing is removed | off |
| `--yes DIGEST` | the owner's yes for the dry run's digest; only with `--apply` | none |

What the run owns (the deletions, in this order):
1. Worktrees: the entries of `git -C REPO worktree list --porcelain` (blocks of `worktree <path>`, `HEAD <sha>`,
   `branch refs/heads/<name>` or `detached`) whose real path is an agent's `cwd` in `agents` of the agents file
   (`{"agents": {"<name>": {"cwd": …}}}`, `S/example/agents.json:43-45`; a relative `cwd` is taken from `RUN_DIR`) or
   a `--worktree`, in the order of their real paths, each printed as git prints it (every other path is printed as
   given). The first block is the main worktree: never a deletion. A `--worktree` that is not in the list is a refusal.
2. Branches: the branch of each run worktree in the same order, then each `--branch` in the order given (one that is
   already listed is not listed twice).
3. `RUN_DIR/scratch` when it exists (a symlink is reported `skipped <path>: a symlink` and never followed).
4. Job folders: `<jobs>/<id>` for each row of `claude agents --json --all` whose `id` is 8 hex digits, whose `name` is
   an agent of the agents file and whose `cwd` is that agent's `cwd` (real paths), in `id` order. Such a row with a
   `pid`, or with a `state` outside `done`, `failed`, `stopped`, is a refusal and never a deletion; a folder that is a
   symlink is reported `skipped <path>: a symlink`; a folder that is gone is skipped silently.
5. Each `--also` path, in the order given.

Output, one line each, in this order (`<sha7>` is the first 7 hex digits, sizes as `clean_jobs_tmp.py:109` prints them,
`{bytes / 1_000_000:.1f} MB`, counting regular files without following symlinks):
- `would remove worktree <path> (branch <name>, HEAD <sha7>): loses <what>`; a detached worktree prints `detached` in
  place of `branch <name>`. `<what>` is `nothing`, or these parts joined by `; `, in this order: `<n> uncommitted paths`
  (the lines of `git -C <path> status --porcelain --ignored` that do not start with `!! `, less the empty ones),
  `<n> empty untracked paths` (C505: the `?? ` lines whose path, `<path>` joined with the line from its 4th
  character, holds nothing: a 0-byte regular file, or a folder whose every entry under `os.walk` is a folder or a
  0-byte regular file, each read with `os.lstat`, so a symlink is never empty; a path that does not exist as printed,
  such as one git quotes, is not empty), `<n> commits not in <main>` (a detached HEAD only:
  `git rev-list --count <main>..<HEAD>`), `ignored ` and the `!! ` entries joined by `, ` in git's order
  (`ignored .venv/`).
- `would delete branch <name> at <sha7>: loses nothing (in <main>)`, or `loses <n> commits not in <main>`
  (`git rev-list --count <main>..refs/heads/<name>`)
- `would remove <path>: loses <n> files, <MB> MB` for `scratch/` and each `--also` (a single file counts as 1 file)
- `would remove job <jobs>/<id> (<name>, <state>): loses <n> files, <MB> MB`
- `skipped <path>: a symlink` for a `scratch` or a job folder that is a symlink, after every `would` line
- `keep <path>`: each record file (below) in name order, then `RUN_DIR/lessons.md`, then each `--kept` in the order
  given
- `refused: <reason>` for each failed check (below), then the last line `nothing removed: <n> refusals`, exit 3; no
  digest is printed for a list that is refused
- otherwise, without `--apply`, the last line
  `total: <w> worktrees, <b> branches, <j> job folders, <p> paths; digest <12 hex>; nothing removed without --apply`
  (`<p>` counts `scratch/` and the `--also` paths)
- with `--apply` (the check passed, the yes holds), in the deletion order: `removed worktree <path>`,
  `deleted branch <name> at <sha7>`, `removed <path>`, `removed job <jobs>/<id>`, or
  `failed <kind> <target>: <reason>` (`<kind>` is `worktree`, `branch`, `path` or `job`; `<reason>` is git's first
  stderr line, `exit <n>` when git printed none, or the OS error) and the rest continues; then each `--kept` is checked
  again (`failed kept <path>: missing`); the last line
  `done: <w> worktrees, <b> branches, <j> job folders, <p> paths removed; <f> failed`.

The digest: `hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()[:12]` over one line per deletion:
`worktree <real path> <40-hex HEAD>`, `branch <name> <40-hex sha>`, `path <real path>` (scratch, `--also`),
`job <id>`. Sizes and file counts are not in it, so a scratch file written after the dry run keeps the owner's yes.

The save check (every refusal is a `refused:` line; all are collected before anything is removed):
- records: a `*.md` directly in `RUN_DIR` whose line 1 starts with `STATUS: ` is a record file, taken in name order;
  line 1 must match `STATUS: done` followed by whitespace or the end (`STATUS: done after Task 2` is final, as Task 2's
  A501): `refused: <name> line 1 is "<line 1>", not "STATUS: done"`. Then
  `<the running interpreter> -I <the collector's folder>/check_formats.py RUN_DIR --repo REPO` must exit 0 (without
  `--repo` and a checkout line, `check_formats.py` skips its done-sha check, `check_formats.py:195-198`):
  `refused: check_formats.py exit <n>: <the first line of its stdout, or of its stderr when stdout is empty>`.
- lessons: `RUN_DIR/lessons.md` exists (`refused: <path> is missing`, and the rest of this item is skipped) and has a
  line that starts with `## Lessons from this run` (`refused: lessons.md has no "## Lessons from this run" section`).
  The section runs to the next line that starts with `# `, `## ` or `### `; an item of it is a line that starts with
  `- ` or `<digits>. `, plus the indented non-blank lines that follow it (a blank or unindented line ends the item).
  Fenced code is neither heading nor item, here and in the Deferred check below: from a line that is, after any
  indentation, three or more backticks and an optional info string, to the line that is, after any indentation, at
  least as many backticks and nothing else (CommonMark's closing rule: a shorter fence inside, or one with an info
  string, is content); the plan's task files hold their tests' fixtures in such blocks (`lessons.md`, the 21:49 UTC
  rule), this task's own Step 1 among them. The section goes on after a fenced block.
  The item's text is its words joined by single spaces, without the leading `- ` or `N. `. Each item whose text is not
  a merge record (`Merged: \S+ at [0-9a-f]{7,40}`) holds `(skill: none)` or `(skill: <7-40 hex>)`:
  `refused: lesson without a (skill: <sha>|none) mark: <the first 60 characters of the text>`; a marked commit that is
  not an ancestor of `--main`: `refused: lesson mark <sha> is not in <main>`.
- kept: each `--kept` exists (`refused: kept <path> is missing`) and lies, by real path, inside no worktree, path or
  job deletion (a branch has no path): `refused: kept <path> lies inside <the first such deletion's path>`.
- commits: the done lines (`DONE`) of `RUN_DIR/build-log.md`, then `RUN_DIR/build-log-kb.md`, then the other
  `RUN_DIR/build-log*.md` in name order, then each `--final` in the order given (none at all:
  `refused: no final commit named (no "Task N: done — <sha>" line in a build log, no --final)`); for each,
  `git merge-base --is-ancestor <sha> <main>` exit 1: `refused: <sha7> (<source>) is not an ancestor of <main>`, any
  other non-zero exit: `refused: <sha> (<source>) is not a commit of <repo>`; `<source>` is `<log name> Task <N>` or
  `--final`.
- Deferred: K1 (Contracts), read with `git show <main>:<path>` (never the working tree) from the `*.md` files directly
  in `--plan` (`git ls-tree --name-only <main> <plan>/`, in name order; a TD id counts only when it is a `| TD-NNN |`
  row): `refused: Deferred item "<key>" (<file name>) is not in the tracker`; no such file:
  `refused: no <plan>/*.md on <main>`; no tracker file there:
  `refused: no docs/exec-plans/tech-debt-tracker.md on <main>` (and no item is checked).
- unsaved work (departure 2): for each run worktree `refused: worktree <path> has <n> uncommitted paths` (the lines of
  `git -C <path> status --porcelain --ignored` that do not start with `!! `, less `<what>`'s empty untracked paths, so
  a worktree that holds only those is not refused) and, for a detached worktree only (one on
  a branch is checked by its branch), `refused: worktree <path> HEAD <sha7> is not in <main>`; for each branch
  `refused: branch <name> at <sha7> has <n> commits not in <main>` (`git rev-list --count <main>..refs/heads/<name>`);
  for each run row `refused: session <name> (<id>) is still running` (a row with a `pid`, or a `state` outside `done`,
  `failed`, `stopped`).
- targets: `refused: <path> holds the run folder or the main worktree` (a `--worktree`, a run worktree or an `--also`
  whose real path is the real `RUN_DIR` or the main worktree, the list's first block, or above either; it is never a
  deletion), `refused: <path> is not a worktree of <repo>` (a `--worktree`), `refused: branch <name> is the main branch`
  (a `--branch`, or a run worktree's branch, equal to `--main`), `refused: no branch <name>`,
  `refused: branch <name> is checked out in <path>` (in a worktree that is not the run's), `refused: <path> is missing`
  (an `--also`).
- the yes: with `--apply`, a `--yes` that differs from the digest:
  `refused: the list changed since the owner's yes (digest <now>, yes given for <given>)`; no `--yes` while the history
  holds fewer than three lines with `"yes": true`:
  `refused: --apply needs --yes <digest> until the owner has said yes for three runs (<k> of 3 in <history>)`.

The order of the `refused:` lines: the save check's first (records in name order, then `check_formats.py`; lessons;
kept; commits; Deferred), then the targets' and the unsaved work's, deletion by deletion: each `--worktree` in the order
given (holds, else not a worktree); each run worktree in real-path order (holds; else uncommitted, then the detached
HEAD); each `--branch` in the order given (the main branch, else missing, else checked out); each branch in the deletion
order (the main branch, else its commits); each running session in `id` order; each `--also` in the order given
(missing, else holds). The yes is checked only when nothing else is refused, so it is never one of several refusals.

After an apply, also one in which a removal failed: a block is appended to `RUN_DIR/collected.md` (made when missing):
`# Collected <YYYY-MM-DD HH:MM> UTC`, then `digest <12 hex>; the owner's yes` when a `--yes` was given, else
`digest <12 hex>; the standing rule`, then every line printed, in order; and one JSON line is appended to the history
(its folder made when missing): `{"run": "<real RUN_DIR>", "at": "<UTC, %Y-%m-%dT%H:%M:%SZ>", "digest": "<12 hex>",
"yes": true|false}`, `"yes"` being whether a `--yes` was given. The yes count is the number of history lines whose
`"yes"` is `true`; a missing or unreadable history counts 0, and a line that is not JSON counts nothing.

Removal: for a worktree, first its empty untracked paths, found again by `<what>`'s rule from a fresh
`git -C <path> status --porcelain --ignored` (`shutil.rmtree` for a folder, `Path.unlink` for a file; C505), then
`git -C REPO worktree remove <path>` (no `--force`: git refuses a dirty worktree a second time),
`git -C REPO branch -D <name>` (`-d` compares with the checkout's HEAD, not with `--main`; the ancestor check above is
the guard), `shutil.rmtree` for folders, `Path.unlink` for files.

Exit codes: 0 listed or removed; 1 a removal failed or a kept item is missing afterwards; 3 refused; 2, before anything
is listed, for an `argparse` error (`--yes` without `--apply` is one: `parser.error("--yes needs --apply")`) or for one
stderr line `collect_run.py: <reason>`, the first that holds of: `no run folder <RUN_DIR>`;
`cannot read the agents file <path>: <the error>` (unreadable, not JSON, or no `agents` object);
`no branch <main> in <repo>`; `claude agents --json --all failed or printed no JSON list` (a non-zero exit, output that
is not a JSON list, or no answer within 300 seconds).

Functions (the builder's shape, each with type hints and a one-line docstring and under 50 lines,
`.claude/rules/python.md:7` and `:9`; the tests call the command line only; a reference built on these names passed
the 18 tests of Step 1 in scratch (the planner's 17, then A503 with `holds_nothing` and `clear_empty`, C505) and is
not shipped):

```python
PROG = "collect_run.py"
HERE = pathlib.Path(__file__).resolve().parent      # the folder of check_formats.py
FINISHED = {"done", "failed", "stopped"}
TRACKER = "docs/exec-plans/tech-debt-tracker.md"
FINAL = re.compile(r"STATUS: done(?:\s|$)")
DONE = re.compile(r"^(?:- )?Task (\d+): done — ([0-9a-f]{7,40})\b", re.MULTILINE)  # check_formats.py:43
MERGED = re.compile(r"Merged: \S+ at [0-9a-f]{7,40}\b")
MARK = re.compile(r"\(skill: (none|[0-9a-f]{7,40})\)")
TD = re.compile(r"\bTD-\d{3}\b")
TD_ROW = re.compile(r"^\| (TD-\d{3}) \|")
JOB_ID = re.compile(r"[0-9a-f]{8}")                 # fullmatch on a row's id
DEFERRED = re.compile(r"#{2,3} Deferred")
LESSONS = re.compile(r"## Lessons from this run")
HEADING = re.compile(r"#{1,3} ")
ITEM = re.compile(r"(?:- |\d+\. )")
FENCE = re.compile(r"\s*(`{3,})(.*)")               # a fence line: its backticks, then the info string
KINDS = ("worktree", "branch", "job", "path")       # the order of the total: and done: counts

class Usage(Exception): ...                         # a reason to exit 2

@dataclasses.dataclass
class Deletion:
    kind: str      # "worktree", "branch", "path", "job"
    target: str    # the path as printed, or the branch name
    ident: str     # its digest line
    line: str      # its `would …` line
    sha: str = ""  # a branch's 40-hex sha, for its `deleted branch` line

def git(repo: str | pathlib.Path, *args: str) -> subprocess.CompletedProcess: ...  # git -C, text, check=False
def ancestor(repo: str, sha: str, main: str) -> int: ...       # the exit code of merge-base --is-ancestor
def real(path: str | pathlib.Path) -> str: ...                 # os.path.realpath
def worktrees(repo: str) -> list[dict]: ...         # {"path", "head", "branch" (None when detached)}, git's order
def items(text: str, heading: re.Pattern[str]) -> list[str]: ...  # the items under matching headings, unfenced
def key(item: str) -> str: ...                      # its first line up to the first ": "
def norm(text: str) -> str: ...                     # no backticks, whitespace collapsed, lower case
def count(path: pathlib.Path) -> tuple[int, int]: ...  # regular files and bytes, no symlink followed
def size(path: pathlib.Path) -> str: ...            # "<n> files, <MB> MB"
def holds(path: pathlib.Path, protected: list[pathlib.Path]) -> bool: ...  # a protected path or above one
def listing() -> list[dict]: ...                    # claude agents --json --all; Usage when it fails
def picked_worktrees(args, agents, trees, protected) -> tuple[list[tuple[str, dict]], list[str]]: ...
def holds_nothing(path: pathlib.Path) -> bool: ...  # an empty untracked path (C505): no byte, no symlink
def clear_empty(tree: str) -> None: ...             # removes a worktree's empty untracked paths before git does
def worktree_deletion(args, p: str, t: dict) -> tuple[Deletion, list[str]]: ...
def worktree_deletions(args, agents, trees, protected) -> tuple[list[Deletion], list[str], list[dict]]: ...
def branch_names(args, run_trees, trees) -> tuple[list[str], list[str]]: ...
def branch_deletions(args, run_trees, trees) -> tuple[list[Deletion], list[str]]: ...
def scratch_deletion(args) -> tuple[list[Deletion], list[str]]: ...   # and its `skipped` line
def run_rows(args, agents, rows) -> list[dict]: ...                   # the run's rows, in id order
def job_deletions(args, agents, rows) -> tuple[list[Deletion], list[str], list[str]]: ...
def also_deletions(args, protected) -> tuple[list[Deletion], list[str]]: ...
def deletions(args, agents, rows, trees) -> tuple[list[Deletion], list[str], list[str]]: ...  # found, refusals, notes
def first_line(path: pathlib.Path) -> str: ...
def records(run: pathlib.Path) -> list[pathlib.Path]: ...      # the record files, in name order
def check_records(args) -> list[str]: ...
def check_lessons(args) -> list[str]: ...
def check_kept(args, found: list[Deletion]) -> list[str]: ...
def done_lines(run: pathlib.Path) -> list[tuple[str, str]]: ...  # (sha, "<log name> Task <N>")
def check_commits(args) -> list[str]: ...
def check_deferred(args) -> list[str]: ...
def check(args, found: list[Deletion]) -> list[str]: ...       # records + lessons + kept + commits + Deferred
def digest(found: list[Deletion]) -> str: ...
def yeses(history: pathlib.Path) -> int: ...
def check_yes(args, history: pathlib.Path, now: str) -> list[str]: ...
def remove(args, d: Deletion) -> str: ...           # one removal's line; an OSError carries the reason
def apply(args, found: list[Deletion]) -> tuple[list[str], int]: ...  # the lines, the failures
def record(args, history: pathlib.Path, now: str, printed: list[str], acted: list[str]) -> None: ...
def load(args) -> dict: ...                         # the agents; Usage for the first three reasons of exit 2
def collect(args) -> int: ...
def main(argv: list[str] | None = None) -> int: ...
```

## Steps

`W` is builder C's worktree, `/home/tite/Desktop/agentic-flow-template/manager-build-c` on `feat/manager-build-c`
(`_builder-c-assignment.md:1`), at f70e84c when the task starts; `S` as above. Every `Expected:` was measured on a
tree extracted from f70e84c (`git archive f70e84c | tar -x`) with the planner's reference collector, and the two
blocks below are the measured files byte for byte. Each command runs in a subshell, never with a top-level `cd`, with
`ulimit -v 8388608` and `timeout -k 10` (`lessons.md` Read first 4).

- [ ] Step 1: the tests, `S/scripts/tests/test_collect_run.py` (new, in full below), and the red run.

  The file builds a finished run in `tmp_path` (class `Run`): a repository whose `main` holds the demo plan
  (`docs/exec-plans/active/demo/`: `00-index.md` with a `## Deferred (with the reason)` list, `task-01.md`), the
  tracker with its `| TD-NNN |` rows and the merged work of two run worktrees; the run folder with final records, a
  `lessons.md` whose items are marked, a build log with its done lines and `_control/_agents.json`; the job folders
  of the run's sessions (3 files, 1,000 bytes each folder) and their rows, which the stub `claude` of the suite's
  `transcript_home.py` (`Home`, unchanged) answers to `agents --json --all`. Each test breaks one part of the saved
  run and checks the exact lines, the exit code and, for a refusal, that nothing was removed (`Run.untouched`); every
  expected value is written from the fixture, and the digest is computed in the test from the digest lines of the
  Interfaces, never read from the output. No test starts a session or touches `~/.claude`. The block is fenced with
  five backticks because `TASK_2` holds a four-backtick fence (the Deferred check must skip it, Interfaces
  "lessons"): copy the lines between the two fence lines.

`````python
"""collect_run.py: a finished run built in tmp_path (a repository whose main branch holds the plan, the tracker and
the merged work of two run worktrees; the run folder with final records and marked lessons; the jobs of its sessions
under the stub `claude` of transcript_home.py), the dry run's list, the save check's refusals, the owner's yes and the
removal (spec 5.9.4, 10.14).
"""

import ast
import hashlib
import json
import pathlib
import re
import subprocess

from transcript_home import Home

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "collect_run.py"
PLAN = "docs/exec-plans/active/demo"
TRACKER = "docs/exec-plans/tech-debt-tracker.md"
INDEX = """# Demo plan

## Deferred (with the reason)
- TD-003 the learning system (instinct model): stays by hand (spec 7.6).
- 8.3.17 per-plugin start-up cost: needs a per-plugin measurement
  that the catalogue does not make.

## Coverage
- 5.9.4 the collector: Task 6.
"""
TASK = """# Task 1 — Demo

## Deferred

1. A live check of the `--bg` output forms: copied from a verbatim log.

## Verified
- nothing deferred here: this item is under Verified.
"""
TASK_2 = """# Task 2 — Demo two

### Deferred
- TD-099 a row nobody wrote: names an id the tracker does not have.

  ````python
  ```markdown
  ````text
## Deferred
- A fixture item between fence lines: a test's fixture, never a Deferred item.
  ```
  ````

2. The registry ids: matched once the registry is merged.
"""
ROWS = """# Tech debt tracker

| Id | Area | Debt | Impact | Owner | Priority | Plan |
| --- | --- | --- | --- | --- | --- | --- |
| TD-003 | learning | the learning system | runs repeat mistakes | maintainers | medium | a later run |
| TD-013 | catalogue | per-plugin cost | unmeasured | maintainers | low | demo Deferred: 8.3.17 per-plugin start-up cost |
| TD-014 | watcher | the output forms | untested live | maintainers | low | demo Deferred: a live check of the --bg OUTPUT  forms |
"""
LESSONS = """# Lessons

## Read first
1. A rule from before the run: not checked.

## Lessons from this run
(roles add one-line rules here, with the finding ids)
- 10:00 UTC (planner; C1): an Expected count covers only the tests
  the steps so far can make green (skill: {main})
- 10:05 UTC (builder; B2): this run's scratch path was long (skill: none)
- 10:10 UTC (main session): Merged: a->b at {a}
"""


class Run:
    """A finished run whose record is saved, so the check passes; each test breaks one part of it."""

    def __init__(self, tmp_path: pathlib.Path):
        self.home = Home(tmp_path)
        self.repo = tmp_path / "repo"
        self.wt_a, self.wt_b = tmp_path / "wt-a", tmp_path / "wt-b"
        self.run = tmp_path / "runs" / "demo-run"
        self.jobs = tmp_path / "home" / ".claude" / "jobs"
        self.page = tmp_path / "vault" / "measurement.md"
        self.summary = self.repo / PLAN / "demo.summary.md"
        self.copy = tmp_path / "eval-copy"
        self.history = tmp_path / "runs" / "collect-history.jsonl"
        self.repo.mkdir()
        self.git(self.repo, "init", "-q", "-b", "main")
        self.write(self.repo / ".gitignore", ".venv/\n")
        self.write(self.repo / TRACKER, ROWS)
        self.write(self.repo / PLAN / "00-index.md", INDEX)
        self.write(self.repo / PLAN / "task-01.md", TASK)
        self.write(self.summary, "# Demo summary\n")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-q", "-m", "base")
        for name, tree in (("a", self.wt_a), ("b", self.wt_b)):
            self.git(self.repo, "worktree", "add", "-q", "-b", f"feat/demo-{name}", str(tree))
            self.write(tree / f"{name}.txt", f"work {name}\n")
            self.git(tree, "add", "-A")
            self.git(tree, "commit", "-q", "-m", f"work {name}")
            self.git(self.repo, "merge", "-q", "--no-ff", f"feat/demo-{name}", "-m", f"merge {name}")
        self.write(self.wt_a / ".venv" / "lib" / "site.py", "# ignored\n")
        self.sha_a = self.git(self.repo, "rev-parse", "feat/demo-a")
        self.sha_b = self.git(self.repo, "rev-parse", "feat/demo-b")
        self.main = self.git(self.repo, "rev-parse", "main")
        for name in ("plan-log.md", "judge.md"):
            self.write(self.run / name, f"STATUS: done\n# {name}\n")
        self.write(self.run / "build-log-a.md", f"STATUS: done\n# Build log a\nTask 1: done — {self.sha_a}\n")
        self.write(self.run / "build-log-b.md", f"STATUS: done\n# Build log b\nTask 2: done — {self.sha_b[:7]}\n")
        self.write(self.run / "lessons.md", LESSONS.format(main=self.main[:12], a=self.sha_a[:7]))
        agents = {
            "demo/builder-a": {"cwd": str(self.wt_a)},
            "demo/builder-b": {"cwd": str(self.wt_b)},
            "demo/critic": {"cwd": str(self.run)},
        }
        self.write(self.run / "_control" / "_agents.json", json.dumps({"run_dir": str(self.run), "agents": agents}))
        self.write(self.run / "scratch" / "planner" / "notes.md", "abc")
        (self.run / "scratch" / "copy.bin").write_bytes(b"x" * 1_260_000)
        self.write(self.page, "# Measurement\n")
        self.write(self.copy / "result.json", "{}\n")
        self.job("0000000a", "demo/builder-a", self.wt_a, "done")
        self.job("0000000b", "demo/builder-b", self.wt_b, "stopped")
        self.job("0000000c", "demo/critic", self.run, "failed")
        self.job("0000000d", "demo/builder-a", tmp_path / "elsewhere", "done")  # the same name in another run
        self.job("0000000e", "other/planner", self.wt_a, "done")  # a role that is not in the agents file

    def git(self, cwd: pathlib.Path, *args: str) -> str:
        out = subprocess.run(
            ["git", "-C", str(cwd), "-c", "user.name=Demo", "-c", "user.email=demo@example.com"]
            + ["-c", "commit.gpgsign=false", *args],
            capture_output=True,
            text=True,
            check=True,
            env={**self.home.env(), "GIT_CONFIG_NOSYSTEM": "1"},
        )
        return out.stdout.strip()

    def git_error(self, *args: str) -> str:
        """The first stderr line of a git command in the main worktree that fails."""
        out = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            capture_output=True,
            text=True,
            check=False,
            env={**self.home.env(), "GIT_CONFIG_NOSYSTEM": "1"},
        )
        assert out.returncode != 0, out.stdout
        return out.stderr.strip().splitlines()[0]

    @staticmethod
    def write(path: pathlib.Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def job(self, ident: str, name: str, cwd: pathlib.Path, state: str, pid: int | None = None) -> None:
        """A row of `claude agents --json --all` in the live shape and its folder: 3 files, 1,000 bytes."""
        row = {
            "id": ident,
            "name": name,
            "sessionId": f"s-{ident}",
            "state": state,
            "kind": "background",
            "cwd": str(cwd),
            "startedAt": 1_761_000_000_000,
        }
        if pid is not None:
            row["pid"] = pid
        self.home.rows.append(row)
        self.home.save_rows()
        self.write(self.jobs / ident / "state.json", "{}\n")
        self.write(self.jobs / ident / "timeline.jsonl", "")
        self.write(self.jobs / ident / "tmp" / "out.txt", "x" * 997)

    def collect(self, *extra: str) -> subprocess.CompletedProcess:
        return self.home.run(
            "collect_run.py",
            str(self.run),
            "--repo",
            str(self.repo),
            "--plan",
            PLAN,
            "--kept",
            str(self.page),
            "--kept",
            str(self.summary),
            "--also",
            str(self.copy),
            *extra,
        )

    def digest(self) -> str:
        out = self.collect()
        assert out.returncode == 0, out.stdout + out.stderr
        return re.search(r"; digest ([0-9a-f]{12}); ", out.stdout.splitlines()[-1]).group(1)

    def side_commit(self) -> str:
        """A commit of the repository on no branch: not in main."""
        return self.git(self.repo, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "side")

    def untouched(self) -> bool:
        listed = self.git(self.repo, "worktree", "list", "--porcelain").splitlines()
        branches = self.git(self.repo, "branch", "--format=%(refname:short)").splitlines()
        return (
            [line for line in listed if line.startswith("worktree ")]
            == [f"worktree {self.repo}", f"worktree {self.wt_a}", f"worktree {self.wt_b}"]
            and sorted(branches) == ["feat/demo-a", "feat/demo-b", "main"]
            and (self.run / "scratch" / "copy.bin").is_file()
            and all((self.jobs / i / "state.json").is_file() for i in ("0000000a", "0000000b", "0000000c"))
            and (self.copy / "result.json").is_file()
        )


def refusals(out: subprocess.CompletedProcess) -> list[str]:
    return [line for line in out.stdout.splitlines() if line.startswith("refused: ")]


def test_a_dry_run_lists_every_deletion_with_what_it_loses_and_removes_nothing(tmp_path):
    r = Run(tmp_path)
    out = r.collect()
    assert out.returncode == 0, out.stdout + out.stderr
    a7, b7 = r.sha_a[:7], r.sha_b[:7]
    assert out.stdout.splitlines()[:-1] == [
        f"would remove worktree {r.wt_a} (branch feat/demo-a, HEAD {a7}): loses ignored .venv/",
        f"would remove worktree {r.wt_b} (branch feat/demo-b, HEAD {b7}): loses nothing",
        f"would delete branch feat/demo-a at {a7}: loses nothing (in main)",
        f"would delete branch feat/demo-b at {b7}: loses nothing (in main)",
        f"would remove {r.run / 'scratch'}: loses 2 files, 1.3 MB",
        f"would remove job {r.jobs / '0000000a'} (demo/builder-a, done): loses 3 files, 0.0 MB",
        f"would remove job {r.jobs / '0000000b'} (demo/builder-b, stopped): loses 3 files, 0.0 MB",
        f"would remove job {r.jobs / '0000000c'} (demo/critic, failed): loses 3 files, 0.0 MB",
        f"would remove {r.copy}: loses 1 files, 0.0 MB",
        f"keep {r.run / 'build-log-a.md'}",
        f"keep {r.run / 'build-log-b.md'}",
        f"keep {r.run / 'judge.md'}",
        f"keep {r.run / 'plan-log.md'}",
        f"keep {r.run / 'lessons.md'}",
        f"keep {r.page}",
        f"keep {r.summary}",
    ]
    assert re.fullmatch(
        r"total: 2 worktrees, 2 branches, 3 job folders, 2 paths; digest [0-9a-f]{12}; nothing removed without --apply",
        out.stdout.splitlines()[-1],
    )
    assert r.untouched() and (r.wt_a / ".venv" / "lib" / "site.py").is_file()
    assert r.home.claude_calls() == ["agents --json --all"]


def test_apply_with_the_owner_s_yes_removes_the_run_and_keeps_the_records(tmp_path):
    r = Run(tmp_path)
    digest = r.digest()
    out = r.collect("--apply", "--yes", digest)
    assert out.returncode == 0, out.stdout + out.stderr
    assert [line for line in out.stdout.splitlines() if line.startswith(("removed ", "deleted ", "failed "))] == [
        f"removed worktree {r.wt_a}",
        f"removed worktree {r.wt_b}",
        f"deleted branch feat/demo-a at {r.sha_a[:7]}",
        f"deleted branch feat/demo-b at {r.sha_b[:7]}",
        f"removed {r.run / 'scratch'}",
        f"removed job {r.jobs / '0000000a'}",
        f"removed job {r.jobs / '0000000b'}",
        f"removed job {r.jobs / '0000000c'}",
        f"removed {r.copy}",
    ]
    assert out.stdout.splitlines()[-1] == "done: 2 worktrees, 2 branches, 3 job folders, 2 paths removed; 0 failed"
    # 10.14, afterwards: git worktree list, git branch, scratch/ and the jobs folder show nothing of the run ...
    listed = r.git(r.repo, "worktree", "list", "--porcelain").splitlines()
    assert [line for line in listed if line.startswith("worktree ")] == [f"worktree {r.repo}"]
    assert r.git(r.repo, "branch", "--format=%(refname:short)").splitlines() == ["main"]
    assert not (r.run / "scratch").exists() and not r.copy.exists() and not r.wt_a.exists()
    assert sorted(p.name for p in r.jobs.iterdir()) == ["0000000d", "0000000e"]
    # ... and the kept items exist.
    for name in ("build-log-a.md", "build-log-b.md", "judge.md", "plan-log.md", "lessons.md", "_control/_agents.json"):
        assert (r.run / name).is_file(), name
    assert r.page.is_file() and r.summary.is_file()
    collected = (r.run / "collected.md").read_text(encoding="utf-8")
    assert re.match(
        r"# Collected \d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC\ndigest " + digest + "; the owner's yes\n", collected
    )
    assert f"\nremoved worktree {r.wt_a}\n" in collected and collected.endswith("; 0 failed\n")
    (line,) = r.history.read_text(encoding="utf-8").splitlines()
    record = json.loads(line)
    assert record == {"run": str(r.run), "at": record["at"], "digest": digest, "yes": True}
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", record["at"])


def test_a_removal_git_refuses_is_reported_and_the_rest_continues(tmp_path):
    r = Run(tmp_path)
    # A run worktree that holds a submodule: git removes it only with --force, which the collector never passes.
    sub = tmp_path / "sub"
    sub.mkdir()
    r.git(sub, "init", "-q", "-b", "main")
    r.write(sub / "s.txt", "s\n")
    r.git(sub, "add", "-A")
    r.git(sub, "commit", "-q", "-m", "s")
    r.git(r.wt_b, "-c", "protocol.file.allow=always", "submodule", "add", str(sub), "lib")
    r.git(r.wt_b, "commit", "-q", "-m", "lib")
    r.git(r.repo, "merge", "-q", "--no-ff", "feat/demo-b", "-m", "merge lib")
    digest = r.digest()
    out = r.collect("--apply", "--yes", digest)
    assert out.returncode == 1, out.stdout + out.stderr
    # git's own first stderr line for the same two removals, which still fail the same way
    wt_error = r.git_error("worktree", "remove", str(r.wt_b))
    branch_error = r.git_error("branch", "-D", "feat/demo-b")
    assert "submodule" in wt_error and "feat/demo-b" in branch_error
    assert [line for line in out.stdout.splitlines() if line.startswith(("removed ", "deleted ", "failed "))] == [
        f"removed worktree {r.wt_a}",
        f"failed worktree {r.wt_b}: {wt_error}",
        f"deleted branch feat/demo-a at {r.sha_a[:7]}",
        f"failed branch feat/demo-b: {branch_error}",
        f"removed {r.run / 'scratch'}",
        f"removed job {r.jobs / '0000000a'}",
        f"removed job {r.jobs / '0000000b'}",
        f"removed job {r.jobs / '0000000c'}",
        f"removed {r.copy}",
    ]
    assert out.stdout.splitlines()[-1] == "done: 1 worktrees, 1 branches, 3 job folders, 2 paths removed; 2 failed"
    assert (r.wt_b / "b.txt").is_file()
    assert r.git(r.repo, "branch", "--format=%(refname:short)").splitlines() == ["feat/demo-b", "main"]
    assert (r.run / "collected.md").read_text(encoding="utf-8").endswith("; 2 failed\n")
    assert json.loads(r.history.read_text(encoding="utf-8"))["yes"] is True


def test_a_record_whose_line_1_is_not_final_refuses_and_nothing_is_removed(tmp_path):
    r = Run(tmp_path)
    digest = r.digest()
    r.write(r.run / "judge.md", "STATUS: judging\n# Judge\n")
    r.write(r.run / "critique.md", "STATUS: reviewed, not done\n# Critique\n")
    r.write(r.run / "verify.md", "# Verify\nno STATUS line\n")
    r.write(r.run / "plan-log.md", "STATUS: done — Task 3 written last\n# Plan log\n")
    out = r.collect("--apply", "--yes", digest)
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        'refused: critique.md line 1 is "STATUS: reviewed, not done", not "STATUS: done"',
        'refused: judge.md line 1 is "STATUS: judging", not "STATUS: done"',
        "refused: check_formats.py exit 1: ERROR verify.md: line 1 is not `STATUS: …`",
    ]
    assert out.stdout.splitlines()[-1] == "nothing removed: 3 refusals"
    assert "digest" not in out.stdout and r.untouched()


def test_a_deferred_item_absent_from_the_tracker_on_main_refuses_and_fenced_code_holds_none(tmp_path):
    r = Run(tmp_path)
    # TASK_2's fenced block (indented; four backticks, holding a shorter fence and a longer-or-equal one with an info
    # string, neither of which closes it) holds a heading and an item: neither counts.
    r.write(r.repo / PLAN / "task-02.md", TASK_2)
    r.git(r.repo, "add", "-A")
    r.git(r.repo, "commit", "-q", "-m", "task 2")
    # The task file deleted in the main worktree and a row for one of its items added there, neither committed:
    # the check reads the main branch.
    (r.repo / PLAN / "task-02.md").unlink()
    with (r.repo / TRACKER).open("a", encoding="utf-8") as f:
        f.write("| TD-015 | watcher | ids | none | maintainers | low | demo Deferred: The registry ids |\n")
    out = r.collect()
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        'refused: Deferred item "TD-099 a row nobody wrote" (task-02.md) is not in the tracker',
        'refused: Deferred item "The registry ids" (task-02.md) is not in the tracker',
    ]


def test_a_final_commit_that_is_not_an_ancestor_of_main_refuses(tmp_path):
    r = Run(tmp_path)
    side = r.side_commit()
    lost = "fedcba9876543210fedcba9876543210fedcba98"
    with (r.run / "build-log-a.md").open("a", encoding="utf-8") as f:
        f.write(f"Task 4: done — {lost}\n")
    with (r.run / "build-log-b.md").open("a", encoding="utf-8") as f:
        f.write(f"- Task 3: done — {side}\n")
    unknown = "0123456789abcdef0123456789abcdef01234567"
    out = r.collect("--final", r.main, "--final", unknown)
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: check_formats.py exit 1: ERROR build-log-a.md: Task 4: done — {lost} is not a commit of {r.repo}",
        f"refused: {lost} (build-log-a.md Task 4) is not a commit of {r.repo}",
        f"refused: {side[:7]} (build-log-b.md Task 3) is not an ancestor of main",
        f"refused: {unknown} (--final) is not a commit of {r.repo}",
    ]


def test_no_final_commit_named_refuses_until_one_is_given(tmp_path):
    r = Run(tmp_path)
    for name in ("build-log-a.md", "build-log-b.md"):
        r.write(r.run / name, "STATUS: done\n# Build log\n")
    out = r.collect()
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        'refused: no final commit named (no "Task N: done — <sha>" line in a build log, no --final)'
    ]
    out = r.collect("--final", r.main)
    assert out.returncode == 0, out.stdout + out.stderr


def test_unsaved_work_in_a_run_worktree_or_on_a_run_branch_refuses(tmp_path):
    r = Run(tmp_path)
    r.write(r.wt_a / "draft.txt", "never committed\n")
    r.write(r.wt_a / "a.txt", "changed\n")
    r.git(r.wt_b, "commit", "-q", "--allow-empty", "-m", "late work")
    late = r.git(r.wt_b, "rev-parse", "HEAD")
    loose_tree = tmp_path / "wt-c"
    r.git(r.repo, "worktree", "add", "-q", "--detach", str(loose_tree))
    r.git(loose_tree, "commit", "-q", "--allow-empty", "-m", "detached work")
    loose = r.git(loose_tree, "rev-parse", "HEAD")
    out = r.collect("--worktree", str(loose_tree))
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: worktree {r.wt_a} has 2 uncommitted paths",
        f"refused: worktree {loose_tree} HEAD {loose[:7]} is not in main",
        f"refused: branch feat/demo-b at {late[:7]} has 1 commits not in main",
    ]
    lines = out.stdout.splitlines()
    a7 = r.sha_a[:7]
    assert (
        f"would remove worktree {r.wt_a} (branch feat/demo-a, HEAD {a7}): loses 2 uncommitted paths; ignored .venv/"
        in lines
    )
    assert f"would remove worktree {r.wt_b} (branch feat/demo-b, HEAD {late[:7]}): loses nothing" in lines
    assert f"would remove worktree {loose_tree} (detached, HEAD {loose[:7]}): loses 1 commits not in main" in lines
    assert f"would delete branch feat/demo-b at {late[:7]}: loses 1 commits not in main" in lines


def test_a_run_worktree_whose_only_untracked_paths_are_empty_placeholders_is_collected(tmp_path):
    r = Run(tmp_path)  # C505: the sandbox leaves 0-byte mount points, untracked, in a role's worktree
    r.write(r.wt_a / "docs" / ".mcp.json", "")
    r.write(r.wt_a / "docs" / ".claude" / "settings.json", "")
    r.write(r.wt_b / "notes" / "sub" / "empty.txt", "")
    link = r.wt_b / "notes" / "sub" / "link"
    link.symlink_to("empty.txt")  # a symlink is never empty, not even one to a 0-byte file
    out = r.collect()
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [f"refused: worktree {r.wt_b} has 1 uncommitted paths"]
    link.unlink()
    out = r.collect()
    assert out.returncode == 0, out.stdout + out.stderr
    a7, b7 = r.sha_a[:7], r.sha_b[:7]
    lines = out.stdout.splitlines()
    assert (
        f"would remove worktree {r.wt_a} (branch feat/demo-a, HEAD {a7}): loses 2 empty untracked paths; ignored .venv/"
        in lines
    )
    assert f"would remove worktree {r.wt_b} (branch feat/demo-b, HEAD {b7}): loses 1 empty untracked paths" in lines
    assert (r.wt_a / "docs" / ".mcp.json").is_file()  # the dry run removes nothing
    out = r.collect("--apply", "--yes", r.digest())
    assert out.returncode == 0, out.stdout + out.stderr
    done = [line for line in out.stdout.splitlines() if line.startswith(("removed worktree", "deleted ", "failed "))]
    assert done == [
        f"removed worktree {r.wt_a}",
        f"removed worktree {r.wt_b}",
        f"deleted branch feat/demo-a at {a7}",
        f"deleted branch feat/demo-b at {b7}",
    ]
    assert not r.wt_a.exists() and not r.wt_b.exists()


def test_a_session_of_the_run_still_running_refuses(tmp_path):
    r = Run(tmp_path)
    r.job("0000000f", "demo/builder-b", r.wt_b, "done", pid=4242)
    r.job("00000010", "demo/critic", r.run, "waiting")
    r.job("00000011", "demo/critic", tmp_path / "elsewhere", "running")  # another run's session
    out = r.collect()
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        "refused: session demo/builder-b (0000000f) is still running",
        "refused: session demo/critic (00000010) is still running",
    ]


def test_a_lesson_without_a_skill_mark_refuses_and_a_merge_record_needs_none(tmp_path):
    r = Run(tmp_path)
    side = r.side_commit()
    unmarked = "10:20 UTC (verifier; V3): an unmarked rule that never reached the skill"
    with (r.run / "lessons.md").open("a", encoding="utf-8") as f:
        f.write(f"- {unmarked}\n- 10:25 UTC (builder; B4): marked with a commit off main (skill: {side[:9]})\n")
    out = r.collect()
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: lesson without a (skill: <sha>|none) mark: {unmarked[:60]}",
        f"refused: lesson mark {side[:9]} is not in main",
    ]


def test_a_missing_kept_item_or_one_inside_a_deletion_refuses(tmp_path):
    r = Run(tmp_path)
    missing = tmp_path / "vault" / "missing.md"
    notes = r.run / "scratch" / "planner" / "notes.md"
    out = r.collect("--kept", str(missing), "--kept", str(notes), "--kept", str(r.wt_a / "a.txt"))
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: kept {missing} is missing",
        f"refused: kept {notes} lies inside {r.run / 'scratch'}",
        f"refused: kept {r.wt_a / 'a.txt'} lies inside {r.wt_a}",
    ]


def test_the_owner_s_yes_holds_for_the_list_it_was_given_for(tmp_path):
    r = Run(tmp_path)
    digest = r.digest()
    lines = [
        f"worktree {r.wt_a} {r.sha_a}",
        f"worktree {r.wt_b} {r.sha_b}",
        f"branch feat/demo-a {r.sha_a}",
        f"branch feat/demo-b {r.sha_b}",
        f"path {r.run / 'scratch'}",
        "job 0000000a",
        "job 0000000b",
        "job 0000000c",
        f"path {r.copy}",
    ]
    assert digest == hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()[:12]
    r.git(r.wt_b, "commit", "-q", "--allow-empty", "-m", "late work")
    r.git(r.repo, "merge", "-q", "--no-ff", "feat/demo-b", "-m", "merge late work")
    now = r.digest()
    assert now != digest
    out = r.collect("--apply", "--yes", digest)
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [f"refused: the list changed since the owner's yes (digest {now}, yes given for {digest})"]
    assert r.untouched()
    r.write(r.run / "scratch" / "late.log", "written after the dry run\n")
    out = r.collect("--apply", "--yes", now)
    assert out.returncode == 0, out.stdout + out.stderr
    assert not (r.run / "scratch").exists()


def test_apply_without_a_yes_waits_for_three_runs_applied_with_one(tmp_path):
    r = Run(tmp_path)
    old = [
        {"run": "/runs/r1", "at": "2026-10-21T10:00:00Z", "digest": "0" * 12, "yes": True},
        {"run": "/runs/r2", "at": "2026-10-22T10:00:00Z", "digest": "1" * 12, "yes": False},
        {"run": "/runs/r3", "at": "2026-10-23T10:00:00Z", "digest": "2" * 12, "yes": True},
    ]
    r.write(r.history, "".join(json.dumps(x) + "\n" for x in old))
    out = r.collect("--apply")
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: --apply needs --yes <digest> until the owner has said yes for three runs (2 of 3 in {r.history})"
    ]
    assert r.untouched()
    with r.history.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"run": "/runs/r4", "at": "2026-10-24T10:00:00Z", "digest": "3" * 12, "yes": True}) + "\n")
    out = r.collect("--apply")
    assert out.returncode == 0, out.stdout + out.stderr
    record = json.loads(r.history.read_text(encoding="utf-8").splitlines()[-1])
    assert record["yes"] is False and record["run"] == str(r.run)
    assert "; the standing rule\n" in (r.run / "collected.md").read_text(encoding="utf-8")


def test_a_deletion_that_holds_the_run_folder_or_the_main_worktree_refuses(tmp_path):
    r = Run(tmp_path)
    r.git(r.repo, "worktree", "add", "-q", "-b", "feat/demo-x", str(tmp_path / "wt-x"))
    (tmp_path / "plain").mkdir()
    out = r.collect(
        "--worktree",
        str(r.repo),
        "--worktree",
        str(tmp_path / "plain"),
        "--branch",
        "main",
        "--branch",
        "feat/none",
        "--branch",
        "feat/demo-x",
        "--also",
        str(tmp_path / "runs"),
        "--also",
        str(tmp_path / "gone"),
    )
    assert out.returncode == 3, out.stdout + out.stderr
    assert refusals(out) == [
        f"refused: {r.repo} holds the run folder or the main worktree",
        f"refused: {tmp_path / 'plain'} is not a worktree of {r.repo}",
        "refused: branch main is the main branch",
        "refused: no branch feat/none",
        f"refused: branch feat/demo-x is checked out in {tmp_path / 'wt-x'}",
        f"refused: {tmp_path / 'runs'} holds the run folder or the main worktree",
        f"refused: {tmp_path / 'gone'} is missing",
    ]


def test_a_symlinked_scratch_is_skipped_and_never_followed(tmp_path):
    r = Run(tmp_path)
    elsewhere = tmp_path / "shared-scratch"
    (r.run / "scratch").rename(elsewhere)
    (r.run / "scratch").symlink_to(elsewhere, target_is_directory=True)
    out = r.collect()
    assert out.returncode == 0, out.stdout + out.stderr
    lines = out.stdout.splitlines()
    assert (
        lines[lines.index(f"would remove {r.copy}: loses 1 files, 0.0 MB") + 1]
        == f"skipped {r.run / 'scratch'}: a symlink"
    )
    assert not [line for line in lines if line.startswith(f"would remove {r.run / 'scratch'}")]
    assert lines[-1].startswith("total: 2 worktrees, 2 branches, 3 job folders, 1 paths; digest ")
    out = r.collect("--apply", "--yes", r.digest())
    assert out.returncode == 0, out.stdout + out.stderr
    assert (r.run / "scratch").is_symlink() and (elsewhere / "copy.bin").is_file()


def test_every_function_of_the_collector_is_under_50_lines():
    """.claude/rules/python.md:9: keep functions under 50 lines."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    lengths = {
        node.name: node.end_lineno - node.lineno + 1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "main" in lengths
    assert {name: n for name, n in lengths.items() if n >= 50} == {}


def test_a_missing_run_folder_agents_file_or_main_branch_or_a_failed_listing_exits_2(tmp_path):
    r = Run(tmp_path)
    out = r.home.run("collect_run.py", str(tmp_path / "no-run"), "--repo", str(r.repo), "--plan", PLAN, "--kept", "x")
    assert (out.returncode, out.stdout) == (2, "")
    assert out.stderr == f"collect_run.py: no run folder {tmp_path / 'no-run'}\n"
    out = r.collect("--main", "trunk")
    assert (out.returncode, out.stdout, out.stderr) == (2, "", f"collect_run.py: no branch trunk in {r.repo}\n")
    out = r.collect("--yes", "0" * 12)
    assert out.returncode == 2 and "collect_run.py: error: --yes needs --apply" in out.stderr
    (r.home.stub / "agents.json").write_text("not json", encoding="utf-8")
    out = r.collect()
    assert (out.returncode, out.stdout) == (2, "")
    assert out.stderr == "collect_run.py: claude agents --json --all failed or printed no JSON list\n"
    (r.run / "_control" / "_agents.json").unlink()
    out = r.collect()
    assert (out.returncode, out.stdout) == (2, "")
    assert out.stderr.startswith(f"collect_run.py: cannot read the agents file {r.run / '_control' / '_agents.json'}: ")
    assert r.untouched()
`````

  Run: `(cd "${W:?}" && uv sync -q && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests/test_collect_run.py 2>&1 | tail -n 1)`
  Expected: `18 failed` (every test runs, or for the length test reads, the missing `collect_run.py`)

- [ ] Step 2: `S/scripts/collect_run.py` against the tests, and the green run of the new file.

  Write the script to the Interfaces: Python 3.12 standard library only, a module docstring as
  `S/scripts/clean_jobs_tmp.py` has, ending in `if __name__ == "__main__": sys.exit(main())`. No shebang line and no
  `chmod`: line 1 is the docstring, the script runs as `python3 -I scripts/collect_run.py` (the tests start it so,
  `transcript_home.py:170-172`), and git keeps it at mode 100644. ruff 0.16.10 reports EXE001 for a shebang in a file
  that is not executable, which fails `just lint`, and `.claude/skills/` takes no `chmod` (a protected path;
  `lessons.md` 22:23); the older scripts keep their shebang and mode 100755. When a test and the Interfaces disagree,
  change neither: send `manager/plan-fixer-b` the proof (Task 6 is even).

  Run: `sed -n '1{/^#!/p}' "${W:?}/.claude/skills/running-specagent-pipelines/scripts/collect_run.py" | wc -l`
  Expected: `0` (no shebang line)
  Run: the command of Step 1.
  Expected: `18 passed`

- [ ] Step 3: the README section; `test_docs.py` and the whole skill suite green.

  `test_docs.py:90-102` wants, for every script in `S/scripts/`, a README heading that names it, the line
  `python3 -I scripts/<name>` and each of its `--` options, so the new script fails two of its tests until the section
  is in.
  Run: `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests/test_docs.py 2>&1 | tail -n 1)`
  Expected: `2 failed, 7 passed`

  Insert the block's lines and then one blank line right before the line `## Config v2` of `S/scripts/README.md`
  (:212 at f70e84c), so the section follows the ``### `clean_jobs_tmp.py` `` section (:199-211) and the blank line
  that ends it. Nothing else in the README changes: Task 3 edits its :55 and :138 on lane B, so the main session's
  `Merged: c->b` stays clean, and Task 10 splits the README later (TD-008). `test_docs.py` is not edited.

````markdown
### `collect_run.py` — a finished run's leftovers, removed only after its record is checked as saved
```
python3 -I scripts/collect_run.py RUN_DIR --repo DIR --plan PATH --kept PATH [--kept PATH ...] [--main BRANCH]
    [--final SHA ...] [--worktree DIR ...] [--branch NAME ...] [--also PATH ...] [--agents FILE] [--jobs DIR]
    [--history FILE] [--apply] [--yes DIGEST]
```
The manager runs it after the run, never a role: it reads the run's agents file first (`--agents`, default
`RUN_DIR/_control/_agents.json`), which every role's settings deny. It lists what the run owns, in this order, with
what each deletion loses: the worktrees of `--repo` whose path is an agent's `cwd` or a `--worktree`
(`would remove worktree <path> (branch <name>, HEAD <sha7>): loses …`), their branches and each `--branch`
(`would delete branch <name> at <sha7>: loses …`), `RUN_DIR/scratch`, the `<id>` folder under `--jobs` (default
`~/.claude/jobs`) of each finished session whose `claude agents --json --all` row has an agent's `name` and `cwd`, and
each `--also` path (eval result copies, preview copies); then `keep <path>` for the record files, `lessons.md` and each
`--kept`. The save check refuses (`refused: <reason>`, then `nothing removed: <n> refusals`, exit 3) when a record's
line 1 is not `STATUS: done`; `check_formats.py --repo` fails; an item of `## Lessons from this run` has no
`(skill: <sha>)` or `(skill: none)` mark, or its commit is not in `--main` (default `main`); a `--kept` item is missing
or lies inside a deletion; a build log's `Task N: done — <sha>` or a `--final` is not an ancestor of `--main`, or none
is named; an item under a `Deferred` heading of the `--plan` files on `--main`, outside fenced code, is not in the
tracker (it names a `TD-` row there, or a row quotes its key); a run worktree has uncommitted paths (an empty
untracked path, such as the sandbox's 0-byte mount points, is not one: it is listed apart and removed right before
its worktree); a run branch or
detached HEAD has commits not in `--main`; or a session of the run is still running. Otherwise it prints
`total: …; digest <12 hex>; nothing removed without --apply`. `--apply --yes <digest>` removes the list the owner said
yes to (a list that changed needs a new yes); once `--history` (default `RUN_DIR/../collect-history.jsonl`) holds three
runs applied with a yes, `--apply` alone runs by the standing rule. Each apply appends to `RUN_DIR/collected.md` and
adds a history line. A `scratch` or job folder that is a symlink is reported (`skipped <path>: a symlink`) and never
followed. Exit 0 listed or removed; 1 a removal failed (the rest continues); 2 a usage error, a missing run folder, an
unreadable agents file, an unknown `--main` or a failed listing (one stderr line); 3 refused.
````

  Run: the `test_docs.py` command above.
  Expected: `9 passed`
  Run: `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 600 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests 2>&1 | tail -n 1)`
  Expected: `164 passed` (146 at f70e84c and the 18 of Step 1)
  Run: `wc -c < "${W:?}/.claude/skills/running-specagent-pipelines/scripts/README.md"`
  Expected: `21812` (19,156 at f70e84c)

- [ ] Step 4: lint and format.

  Run: `command -v just`
  Expected: `/home/tite/.local/bin/just`
  Run: `(cd "${W:?}" && timeout -k 10 300 just lint 2>&1 | tail -n 2)` (`justfile:9-10`: `uv run ruff check . && uv run ruff format --check .`)
  Expected: `All checks passed!`, then `198 files already formatted` (196 at f70e84c and the two new Python files)
  Run: `grep -cP '[\x{10A0}-\x{10FF}\x{1C90}-\x{1CBF}\x{2D00}-\x{2D2F}]' "${W:?}/.claude/skills/running-specagent-pipelines/scripts/collect_run.py" "${W:?}/.claude/skills/running-specagent-pipelines/scripts/tests/test_collect_run.py" "${W:?}/.claude/skills/running-specagent-pipelines/scripts/README.md"`
  Expected: three lines, each ending in `:0` (no letter of a refused block, D1)

- [ ] Step 5: 10.14 for the verifier: each clause and the test that proves it.

  | 10.14 (spec.md:1120-1122) | Test in `test_collect_run.py` |
  | --- | --- |
  | the dry run lists every deletion with what it loses | `test_a_dry_run_lists_every_deletion_with_what_it_loses_and_removes_nothing` (the `loses <n> …` forms also in `test_unsaved_work_in_a_run_worktree_or_on_a_run_branch_refuses`) |
  | it refuses when a record's line 1 is not final | `test_a_record_whose_line_1_is_not_final_refuses_and_nothing_is_removed` |
  | … a `Deferred` item is absent from the tracker | `test_a_deferred_item_absent_from_the_tracker_on_main_refuses_and_fenced_code_holds_none` |
  | … or the final commit is not an ancestor of `main` | `test_a_final_commit_that_is_not_an_ancestor_of_main_refuses`, `test_no_final_commit_named_refuses_until_one_is_given` |
  | afterwards `git worktree list`, `git branch`, `scratch/` and `~/.claude/jobs` show nothing of the run and the kept items exist | `test_apply_with_the_owner_s_yes_removes_the_run_and_keeps_the_records` (`--jobs` stands for `~/.claude/jobs`, whose real folder no test touches) |

  Run: `(cd "${W:?}" && ulimit -v 8388608 && timeout -k 10 300 uv run pytest -q -p no:cacheprovider .claude/skills/running-specagent-pipelines/scripts/tests/test_collect_run.py -k 'dry_run_lists or apply_with_the_owner or record_whose_line_1 or deferred_item_absent or final_commit_that_is_not or no_final_commit_named' 2>&1 | tail -n 1)`
  Expected: `6 passed, 12 deselected`

- [ ] Step 6: commit and log.

  Run: `git -C "${W:?}" add .claude/skills/running-specagent-pipelines/scripts/collect_run.py .claude/skills/running-specagent-pipelines/scripts/tests/test_collect_run.py .claude/skills/running-specagent-pipelines/scripts/README.md && git -C "${W:?}" commit -q -m "feat(skill): Task 6 — the garbage collector: dry run, the save check, the refusals, the deletion" -- .claude/skills/running-specagent-pipelines/scripts/collect_run.py .claude/skills/running-specagent-pipelines/scripts/tests/test_collect_run.py .claude/skills/running-specagent-pipelines/scripts/README.md && git -C "${W:?}" show --stat --format=%h HEAD | tail -n 1 && git -C "${W:?}" ls-files -s .claude/skills/running-specagent-pipelines/scripts/collect_run.py | cut -c1-6`
  Expected: ` 3 files changed, <n> insertions(+)` (git indents it by one space and prints no deletion count: the README
  only gains lines), then `100644` (not executable; measured on a scratch repository at f70e84c with git 2.43.0)
  Then append `Task 6: done — <sha7 of HEAD>` to `build-log-c.md` in the run folder, as your assignment says.

## For Task 11
Task 11 adds these decision pages, each `wiki/decisions/<name>.md` with its `.summary.md`, a `wiki/index.md` line and a
`wiki/log.md` line (builder C writes no `wiki/` file), and closes one tracker row.
- `collector-yes-then-standing-rule` (question 4, answer 4a): the collector removes a run's leftovers on the owner's
  yes for the exact list, `--apply --yes <digest>` with the dry run's digest, for three runs; then by the standing rule,
  `--apply` alone once the history file holds three runs applied with a yes, the owner reading `collected.md`
  afterwards (departure 5). Evidence: spec 5.9.4 (spec.md:737-751), question 4 (spec.md:1059-1061),
  `manager-spec-2026-10-29/_owner-answers.md:2` ("4 (a) for three runs, then (b)").
- `collector-save-check` (spec 5.9.4, 8.2.13): a run is collected only after its record is checked as saved: final
  record lines, each lesson of the run marked `(skill: <sha>)` with that commit in the main branch or `(skill: none)`
  (departure 1: a script cannot judge whether a lesson's meaning reached the skill, so the manager marks each one and
  the collector checks the marks), every build log's done commit and each `--final` in the main branch (departure 3),
  every Deferred item of the plan, outside fenced code, a tracker row (K1), and nothing unsaved in what goes
  (departure 2). Evidence: spec.md:737-751; TD-010.
- TD-010 (tracker :14, "no garbage collector when a run is done"): closed with Task 6's commit (the `Task 6: done`
  line of `build-log-c.md`).

## Deferred
- The live `cwd` key of `claude agents --json --all` rows: the rows' shape (`id`, `name`, `cwd`, `state`, `pid`) is
  the suite's stub's (`transcript_home.py`, `Home`), because the listing is denied in the planner's sandbox; a row
  whose `cwd` matches no agent is not a run row, so a wrong key removes nothing. The manager checks one live row at the
  first collection.
- Job folders matched by the registry's session ids: Task 2's `_control/registry.json` records each session's id at
  launch; matching by it instead of `name` and `cwd` waits until both are merged (Task 6 depends on no task).
- A sandbox marker for the collector: no environment variable that tells a sandboxed role was verified; the deny of
  `<run>/_control` in every role's settings is the guard (departure 6).

## Verified
- CommonMark 0.31.2, 4.5 Fenced code blocks (https://spec.commonmark.org/0.31.2/): the closing fence has "at least as
  many backticks or tildes as the opening code fence" and "may be followed only by spaces or tabs"; no plan file uses
  a tilde fence (`grep -c '^ *~~~'` over the plan folder: 0 each), so the rule names backticks; the plan's tasks 2, 3,
  4 and 7 use indented and four-backtick fences (`grep -c`), hence "after any indentation".
- git 2.43.0 (`git --version`): `worktree list --porcelain` blocks (`worktree`, `HEAD`, `branch refs/heads/<b>` or
  `detached`; the main worktree first), `merge-base --is-ancestor` (0 yes, 1 no, other an error), and the two refusals
  of the removal test, measured: `fatal: working trees containing submodules cannot be moved or removed` and
  `error: cannot delete branch '<b>' used by worktree at '<path>'`.
- `S/scripts/check_formats.py:43` (the done line, `DONE`), `:195-198` (`args.repo or by_log.get(name) or builder`;
  without `--repo` and a checkout line the done-sha check is skipped).
- `S/scripts/clean_jobs_tmp.py:109` (`{bytes / 1_000_000:.1f} MB`); `S/scripts/tests/transcript_home.py:170-172`
  (`Home.run` starts a script as `sys.executable -I`); `lessons.md` 22:23 (EXE001; no `chmod` under `.claude/skills/`);
  `S/example/agents.json:43-45` (`{"agents": {"<name>": {"cwd": …}}}`).
- `S/scripts/usage_report.py:7` and `:38`: `claude agents --json --all`, the listing's flags as the skill already
  calls them (`claude agents --help` was denied in this session); `S/scripts/tests/transcript_home.py:50-181` (`Home`:
  `save_rows`, `env`, `run`, `claude_calls`).
- `S/scripts/tests/test_docs.py:90-102` (a heading, `python3 -I scripts/<name>` and each `--` option per script).
- `.claude/rules/python.md:7` and `:9`; `justfile:9-10`; `pyproject.toml:17-18` (`line-length = 120`); ruff 0.16.10
  and Python 3.12.3 (`.venv/bin/ruff --version`, `.venv/bin/python --version`); both test blocks pass
  `ruff check --stdin-filename` and `ruff format --check --stdin-filename` (`lessons.md` 21:34 and 21:57).
- Python 3.12 standard library: `os.path.realpath`, `pathlib.PurePath.is_relative_to` (3.9), `datetime.UTC` (3.11),
  `hashlib.sha256`, `shutil.rmtree`, `argparse.ArgumentParser.error` (exits 2), `subprocess.run(timeout=…)` raising
  `TimeoutExpired`, a `SubprocessError`.
- Measured on the tree of f70e84c (`scratch/planner-c/t6/measure2.sh`, the reference without its shebang and with no
  `chmod`): suite 146 -> 163 passed; the new file `17 failed` -> `17 passed`; `test_docs.py` `2 failed, 7 passed` ->
  `9 passed`; `All checks passed!` and 196 -> 198 files formatted; README 19,156 -> 21,812 bytes; Step 5
  `6 passed, 11 deselected`; no shebang line; Step 6 on a scratch repository: ` 3 files changed, 1194 insertions(+)`,
  then `100644`; no letter of a refused block.
- Wrong versions (`scratch/planner-c/t6/mutate.py`): 41 versions of the reference, each run once, all red; among them
  the five fence versions (not skipped, column 0 only, toggled by any fence line, closed by a shorter fence, closed
  despite an info string), all caught by the Deferred test, and the length test's own wrong version (a function over 50
  lines).
- Spec 10.14 spec.md:1120-1122; 5.9.4 spec.md:737-751; question 4 spec.md:1059-1061; 8.2.13 spec.md:1007; 8.3.6
  spec.md:1012-1045 (item 6); builder C's worktree `_builder-c-assignment.md:1`.
- C505, A503 (plan-fixer-b, `scratch/plan-fixer-b/t6/c505.py` on the planner's reference): with `holds_nothing` and
  `clear_empty` the file passes 18 of 18, ruff check and format clean; 6 wrong versions fail A503 alone (empties
  counted as uncommitted; left for `git worktree remove`; a folder not walked; symlinks followed, `os.stat`; only a
  folder's own entries; removed by the dry run). The planner's measured figures above predate A503: the suite and
  the new file now count one more test (Steps 1, 2, 4 and 5). git 2.43.0 here, `worktree remove` of a worktree
  holding one 0-byte untracked file (exit 128):
  `fatal: '../wt' contains modified or untracked files, use --force to delete it`. This plan worktree's
  `git status --porcelain` lists five such paths (`docs/.mcp.json`, `docs/exec-plans/.mcp.json`,
  `docs/exec-plans/active/.mcp.json`, `docs/exec-plans/done/manager-build/.mcp.json` and
  `docs/exec-plans/done/manager-build/.claude/`); `find <each> -type f -size +0 -o -type l` prints nothing.
