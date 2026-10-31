# This repository as a template

## What a project owns, and what the template owns

| Owner | Paths | Rule |
| --- | --- | --- |
| project | `context/`, `wiki/`, `specs/`, `docs/decisions/`, `docs/exec-plans/`, `docs/design-docs/`, `packages/<pkg>/` (not `packages/harness/`), `.claude/agent-memory/`, `README.md`, `CHANGELOG.md` | never overwritten by a template update |
| template | `.claude/agents/`, `.claude/skills/`, `.claude/hooks/`, `.claude/rules/harness.md`, `.claude/settings.json`, `schemas/`, `templates/`, `packages/harness/`, `docs/roles/`, `docs/loops/`, `docs/quality/`, `docs/runbooks/`, `ops/`, `.github/workflows/`, `.devcontainer/` | changed upstream first; a local change is a pull request against the template |
| plugin | `plugins/code-intel/` | distributed through the internal marketplace with its own `version` |

## Creating a project
1. `python3 ops/new-project.py <target-dir> repo_name=<name> org=<org> vault_path=<path>`: copies the tracked files
   except the paths under `omit` in `docs/template/variables.yaml` (the template's own records, which left the
   repository on 2026-10-29; the names stay so that a project never receives them; decision pages that cite `context/fix-20261004/` or
   `design/` refer to those records), replaces the literal values listed there (`vault_path` is the folder of the owner's notes, which the
   project's `CLAUDE.md` reads on need), leaves `docs/template/VERSION` as the version the project started from,
   keeps the template's `README.md` in the project's `docs/template/` (its links re-rooted, listed in the project's
   `docs/llms.txt`), writes a stub `README.md` named after the project, and sets the project up on this machine with
   `ops/bootstrap.py`: uv, the workspace, `just`, the git hooks, the plugins,
   the language servers, the sandbox, the first code graph, graphify's skill, the user-level pipeline skill and
   `harness doctor` (each step in its docstring; `docs/decisions/0009-a-checkout-sets-itself-up.md`). `--no-setup`
   copies only. `--container` makes `<target-dir>` the project's own folder: the repository goes to
   `<target-dir>/<repo_name>/`, beside it `runs/` (marked `.harness-runs`: the runs root, `docs/roles/RUNS.md`),
   `experiments/` (copies made for trials) and `docs/handoff/` (the manager's hand-over notes); a `<target-dir>` that
   holds another checkout is refused, as that checkout would take the same runs root. Without it the
   runs live in `../<repo_name>-runs/`, so that projects that share a parent folder do not share a `runs/`. A checkout that already exists gets the same folders beside it with `python3 ops/container.py`
   (`runs/`, `experiments/`, `docs/handoff/`; refused when the parent holds another checkout).
   A `vault_path` without an `INDEX.md` gets a vault first: `python3 ops/new-vault.py <path> [commons_path=<path>]`
   copies `templates/vault/` (the vault form: `rules.md`, `INDEX.md`, `log.md`, the folders and `ops/` with the
   vault's scripts), draws the vault's opaque `origin` id, names `commons_path` (default `~/aftpro-commons`, the clone
   of the public commons) in its `INDEX.md`, makes one commit and prints the user's own step, a private remote; a
   folder that is not empty is refused, and the project with it. `harness doctor` checks both paths. After the owner's
   yes, `python3 ops/contribute.py <vault-page> [<evidence> ...] [--dry-run]` offers a global decision or concept to
   the commons by pull request and refuses private material in code (`wiki/decisions/the-shared-knowledge-base.md`).
2. In the new directory: `git init`, `uv run harness validate`, `just catalog`, then the first commit.
3. Add the project's packages under `packages/` beside `harness`, its source material under `context/` and its pages
   under `wiki/` (the template ships none: owner, 2026-10-29).
4. Decide the open questions the template leaves to a human (owners in `.github/CODEOWNERS`, budgets, the version pin).

## Receiving template updates
1. Compare `docs/template/VERSION` with the template's. Read every entry of the template's `docs/template/MIGRATIONS.md`
   between the two versions.
2. Conventions that live in the plugin arrive by themselves: the marketplace entry carries the new plugin `version`.
3. Template-owned files: apply the migration entry, by hand or as an ordinary run whose brief is that entry. The pull request
   passes the same gates as any instruction change (`docs/quality/LEARNING.md`): `harness validate`, `harness version-check`,
   the regression evals.
4. Set `docs/template/VERSION` to the new version in the same pull request. Active runs keep their frozen configuration.

## Versions
- `docs/template/VERSION`: version of the template this project was created from or last updated to.
- `docs/roles/VERSION`: version of the instruction set inside this project (`docs/roles/CHANGELOG.md`).
- `plugins/code-intel/.claude-plugin/plugin.json` `version`: version of the plugin.
- `minimumVersion` in `.claude/settings.json` and the pinned version in `.devcontainer/` and CI: the Claude Code version.

The repository's one-line description on GitHub is `docs/template/DESCRIPTION.txt`; `gh repo edit --description
"$(cat docs/template/DESCRIPTION.txt)"` sets it.
