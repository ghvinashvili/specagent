---
status: accepted
date: 2026-10-02
decision-makers: platform team
consulted: harness maintainers
informed: all package owners
---

# What the first complete live run changed

## Context and Problem Statement
The harness was written from the documentation of Claude Code. The first complete run of the default table on a
real machine (read, plan, write, verify, critique, judge, integrate) showed where a role session behaves differently
from what the documentation suggests. Each point below stopped a stage or silently changed its result.

## Decision Drivers
* A role session has nobody to answer a prompt: whatever can ask must be decided before it starts.
* A stage must review the work, not the base it was made from.
* The model a human chose for a stage must be the model that runs.

## Considered Options
* Leave each point to the role's instruction
* Decide each point in the launcher, the settings and the hooks, and check it

## Decision Outcome
Chosen option: launcher, settings and hooks, each with a test.

| Seen live | Decision |
| --- | --- |
| A sandboxed command that reached for a host outside the list made Claude Code ask, and a background session waited forever | `sandbox.network.strictAllowlist` in the session settings; the project's own allowed hosts and write paths are repeated there, because with the strict list the project file's entries no longer count |
| With the read block on, sandboxed commands saw nothing under the home directory, so `uv` did not exist | `toolchain` in the access table: paths re-opened for sandboxed commands |
| A deny rule on `.venv` hid the system interpreter, because the environment's `python` is a link to it | no deny rule on `.venv`, `dist`, `build` |
| A background session cannot edit the shared checkout, and with `--agent` Claude Code's own instruction to enter a worktree is gone | types that change the repository list `EnterWorktree`, their instruction names the step, the first message names the checkout |
| `git status` inside the sandbox shows hidden files as deleted | `git add -A`, `git add .` and `git commit -a` are refused in a role session; the write gate checks the branch's scope |
| A reviewing stage received an empty directory: the work was on a branch | the work commit, a checkout of it and `changes.patch` (`harness/work.py`); `guard-checkout` keeps a session out of the shared checkout |
| `claude --resume` ran the resumed session on the user's default model | `--model` and `--effort` on every start and resume, the model again as a setting; `cache-report` lists sessions outside the model policy |
| A background session inherited the environment of the background service, not of the launching command | what a session needs is in the `env` block of its settings; `VIRTUAL_ENV` is cleared there; `harness doctor` reports a service started inside a Python environment |
| A finished session stayed listed as `blocked` or `working` | poll decides from the result file and the end of the session's log |
| `claude respawn` restarted a process and left the conversation idle | a unit is always resumed with a message |
| The judge returned its verdict as text: the agent file's tool list hid `StructuredOutput` | print-stage types list the tool; `harness validate` checks it; a text result that matches the schema is taken |
| In a fresh checkout `uv run --package <pkg> pytest` found no pytest | the test command is `uv run pytest -q packages/<pkg>` |
| The full output of a test run was written where the session could not read it | it goes to the stage's `logs/` directory |

### Consequences
* Good, because each point is enforced where it cannot be forgotten, and has a test in `packages/harness/tests/`.
* Bad, because the harness depends on behaviour of Claude Code that its documentation does not promise. `harness
  doctor` and the live eval suite are where a change of that behaviour shows first.

### Confirmation
Run `20261002-030221-e2e-count` (default table) ended with every gate passed, the judge's verdict recorded, and one
branch built by `harness integrate`. `uv run pytest -q` holds one test per row above.

## More Information
What is still open: a verdict of `revise` has no loop inside a run (`docs/roles/HUMAN.md`); a human who types into a
role session continues it as a copy on their own default model; `.env.example` is hidden from role sessions by the
same rule that hides `.env.*`.
