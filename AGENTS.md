# AGENTS.md

## Project overview
Python monorepo managed with uv (`packages/*`). `packages/harness` is the CLI that runs multi-session
agent work; the other packages are the product. Nested `AGENTS.md` files in packages take precedence
for files under them.

## Setup and commands
- `uv sync` — install the workspace
- `uv run pytest -q packages/<pkg>` — tests of one package (`uv run` builds the environment of a fresh worktree on first use)
- `uv run ruff check . && uv run ruff format --check .` — lint and format check
- `just validate` — harness self-check (schemas, role types, skills, settings)

## Code style
- Python 3.12, type hints on public functions, `ruff` rules from the root `pyproject.toml`.
- Small modules; one responsibility per file; no top-level side effects on import.

## Testing
- Every change ships with tests in the package's `tests/`.
- Never delete or weaken an existing test to make a change pass; report it instead.
- Tests that need a database run on the database engine production uses (PostgreSQL where production runs
  PostgreSQL, in a container or a local server), never SQLite or an in-memory stand-in to save time.
- The tests of `packages/harness` read `docs/roles/`, which a role session cannot see: in a role session run the
  tests of the packages you work on. The gate runs the whole suite outside the session.

## Security
- Secrets come from the environment; commit only `.env.example`.
- Do not add network calls to new hosts without an entry in `docs/quality/SECURITY.md`.

## Commits and pull requests
- Conventional Commits (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `build`, `perf`, `style`).
- Use `.github/PULL_REQUEST_TEMPLATE.md`; link the spec or ADR the change implements.
- Every new document gets one line in `docs/llms.txt`, or in its folder's `README.md` when `docs/llms.txt` links that
  README; a plan folder gets its line in `docs/exec-plans/active/README.md` (`.claude/rules/docs.md`).
- A code change carries its pages under `wiki/`, `docs/runbooks/` or `docs/decisions/` in the same commit, or its task's
  entry in the planner's `tasks.json` says why not (`docs: none — <reason>`; ADR-0027).
