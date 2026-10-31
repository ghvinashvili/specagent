---
status: accepted
date: 2026-10-29
decision-makers: the owner, in the spec of the template-core run and the orders of 2026-10-29 on the code graph, the sandbox and blind roles
consulted: the template-core run's planner, critic and plan fixers
informed: every project created from this template
---

# A checkout sets up its hooks, sandbox and graph

## Context and Problem Statement

ADR-0009 made a checkout set itself up. This run adds three things to that setup: `just`, which a fresh machine
lacks; the code graph, refreshed after every commit, merge and checkout; and the sandbox on each OS. A hook that
refreshes the graph runs the scripts of the tree it checks out, and in a role's worktree those scripts are the role's
unmerged code (R4 of the template-core run). How does a checkout set all of this up by itself without running a role's
unmerged code outside the sandbox?

## Decision Drivers

* A fresh clone works on Linux, WSL2 and macOS without a manual step.
* What is done in the template reaches the graph by itself.
* No role's unmerged code runs outside every role's sandbox.
* A refused step is reported, and the sandbox is never weakened.

## Considered Options

* Bootstrap and the SessionStart hook set everything up, and the harness's own git runs no hook
* `graphify hook install` in each checkout
* No hooks, `just graph` by hand after each change

## Decision Outcome

Chosen option: "Bootstrap and the SessionStart hook set everything up, and the harness's own git runs no hook",
because it alone sets up a fresh clone on each OS, keeps the layered graph current after commits, merges and
checkouts, and keeps a role's unmerged code inside the sandbox.

* `ops/bootstrap.py` runs its steps in this order, each skipped when it is done: uv; the workspace; `just` when it is
  missing; the git hooks (`core.hooksPath=.githooks`; a value the checkout already holds is kept); the plugins; the
  language servers; the sandbox; the first code graph (`bash ops/graph.sh`).
* The sandbox step, when `.claude/settings.json` enables the sandbox: `ops/machine-setup.py --auto` on Linux and WSL2,
  the seatbelt (`sandbox-exec`) checked on macOS. On native Windows bootstrap prints the WSL2 path, and no role session
  starts there: a role session's settings hold `sandbox.failIfUnavailable: true`.
* A step that fails is named in bootstrap's last lines, with the fix `harness doctor` gives; no step turns the sandbox
  off.
* The SessionStart hook calls bootstrap's `git_hooks` in every session, so a checkout set up earlier and a project
  made before `git init` turn their hooks on at their next session.
* `harness doctor` names `just` and the sandbox's state on each OS.
* Every git command of `packages/harness` starts `git -c core.hooksPath=/dev/null` (`harness.gitcall.GIT`), and the
  main session does the same on a role's unmerged commit (the pipeline skill's `references/launch.md`).
* The hooks in `.githooks/` (`post-commit`, `post-merge` and `post-checkout`, each `bash ops/graph.sh --quick`) serve
  people's and agents' own commits, merges and checkouts. The merge into the trunk is where a role's code becomes the
  project's.

### Consequences

* Good, because a clone needs `python3 ops/bootstrap.py --wait` at most, and the graph follows the code.
* Bad, because each commit, merge and checkout also runs the incremental graph update (`GRAPH_SKIP=1` skips it).
* Bad, because native Windows starts no role session.

### Confirmation

`packages/harness/tests/test_setup.py` (a set-up checkout turns its hooks on and keeps another hooks path; native
Windows is sent to WSL2), `packages/harness/tests/test_git_runs_no_hook.py` (no git command of the harness without the
prefix; a gate and a stage checkout run no hook) and `packages/harness/tests/test_doctor_sandbox.py` (the sandbox's
items on each OS).

## Pros and Cons of the Options

### Bootstrap and the SessionStart hook set everything up, and the harness's own git runs no hook

* Good, because a fresh clone on Linux, WSL2 or macOS sets itself up, and a checkout set up earlier turns its hooks on
  at its next session.
* Good, because the hooks refresh the layered `wiki/graph/` after commits, merges and checkouts.
* Good, because the harness's git fires no hook, so a role's unmerged code runs only inside the sandbox.
* Bad, because every commit, merge and checkout waits for the incremental graph update.

### `graphify hook install` in each checkout

* Good, because graphify installs, checks and removes its hooks itself.
* Bad, because graphify 0.9.64 writes `post-commit` and `post-checkout` only, with no `post-merge`.
* Bad, because its hooks rebuild `graphify-out/`, not the layered `wiki/graph/`.

### No hooks, `just graph` by hand after each change

* Good, because no git command runs code of the tree.
* Bad, because the graph falls behind whenever a change is not followed by `just graph`, against the order that what
  is done in the template reaches the graph by itself.

## More Information

* Amends [ADR-0009](0009-a-checkout-sets-itself-up.md).
* R4 of the template-core run: git runs hooks on a checkout, a merge and every reference update (githooks(5):
  post-checkout, reference-transaction, post-index-change).
* Revisit when Claude Code's sandbox runs on native Windows or graphify's own hooks cover merges and export the layered
  wiki/graph/.
