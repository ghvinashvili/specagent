# Learning loop

How a failure in a run becomes a change in the harness. Nothing here is applied by an agent: the loop ends in a
pull request that a human merges.

## The path
1. Traces. The evidence is the run directory of every finished run: `state.json`, `stages/*/gate.json`, `stages/*/result.json`,
   `escalations/*.json` with their answers, the hook logs under `stages/*/logs/` (`skills.jsonl`, `stop-failure.jsonl`,
   `instructions.jsonl`) and `evals/results/`. Transcripts are not read. OpenTelemetry gives totals, not a diagnosis.
2. Taxonomy. The `analyst` assigns every failure one class from `docs/quality/failure-taxonomy.yaml` and writes
   `stages/analyze/output/taxonomy.md`: class, count, runs, files.
3. Proposal. One file per proposal from `templates/change-proposal.md` in `stages/analyze/output/proposals/`.
4. Challenge and verdict. A `critic` session looks for the weak point of every proposal; the `judge` returns accept, revise or
   reject against `evals/rubrics/change-proposal.md`; a human approves the verdict (`docs/roles/pipelines/learning.yaml`).
5. Pull request. An accepted proposal becomes the brief of an ordinary run, or a human writes the change. The pull request
   contains the change, the regression case that reproduces the failure (`evals/regression/<case>/`), a new
   `docs/roles/VERSION` and a line in `docs/roles/CHANGELOG.md`.
6. Gate. `.github/workflows/evals.yml` runs on every pull request that touches `.claude/`, `plugins/`, `templates/`,
   `schemas/`, `docs/roles/` or `evals/`: `harness version-check`. `.github/workflows/ci.yml` runs
   the tests and the regression suite graded on its recorded baselines, with no session (threshold 1.0), on every push
   and pull request; the session cases run nightly on the owner's machine (`evals/nightly.sh`).
7. Human approval: the owners in `.github/CODEOWNERS` review and merge. Active runs keep the fingerprint they started with
   (`harness refreeze` is a separate human decision); new runs use the new version.

The loop runs weekly (`docs/loops/learning-review.yaml`): its material is the runs finished in the last seven days, named in
the brief by `harness loop tick`.

## Why every instruction change has a version
- A change to an agent file, a preloaded skill, a rule without `paths`, a hook or the settings changes what a role session
  does, and it changes the cached prefix of every session of that type: the first call after the change pays for a cache write.
- `docs/roles/VERSION` is one line, `MAJOR.MINOR.PATCH`. `harness version-check --base <ref>` fails when instruction files
  changed since `<ref>` and the version did not, or when `docs/roles/CHANGELOG.md` has no heading for the new version.
- A run is tied to its configuration by the fingerprint that `harness run` records in `state.json`; the version is the name
  humans use for that configuration. The internal plugin has its own `version` in `plugin.json`.

## Skill review
- `uv run harness skill-usage --runs 20` reads `skills.jsonl` of the last runs and of `_audit/`: uses per skill, split into
  calls by Claude (the `Skill` tool) and typed commands (`/name`), and the skills that were never used.
- Skills preloaded through an agent's `skills` field (`checkpoint`, `escalate`) are always in context and never appear as a
  use. Their measure is the gate pass rate of the role types that preload them.
- A skill with no use in the reviewed runs gets a proposal: fix its `description`, merge it into another skill, or remove it.
- Aids for a human in an interactive session: `claude plugin details <name>` (always-on and on-invoke token cost),
  `/skill-doctor`, and the OpenTelemetry event `claude_code.skill_activated`.

## Self-repair
- A failing trial or run is reproduced as a case before anything is changed: `harness eval --case <name>` must fail on the
  current configuration and pass on the proposed one. Both results go into the pull request.
- Every confirmed failure stays as a regression case. A capability case that passes for three releases graduates to `regression/`.
- What is never automatic: an edit to `.claude/`, `docs/roles/`, `plugins/`, `schemas/` or `evals/` by a role session. The
  analyst's tools allow it technically; its contract, the `soft_deny` entry in `docs/roles/auto-mode.json`, the ConfigChange
  hook and CODEOWNERS are the four checks, and only the last two are enforced by code.

## What is remembered
- Only what was checked. A lesson enters `docs/`, a skill or the manager's agent memory through a pull request, after the
  gate; a role session writes lessons into `result.json`, never into a memory file.
