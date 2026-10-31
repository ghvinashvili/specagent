set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

test pkg="":
    if [ -z "{{pkg}}" ]; then uv run pytest -q; else uv run pytest -q packages/{{pkg}}; fi

lint:
    uv run ruff check . && uv run ruff format --check .

fmt:
    uv run ruff format .

manager:
    d="$(uv run harness runs-root --plain)" && claude --agent manager --add-dir "$d"

run slug brief:
    uv run harness run --slug {{slug}} --brief {{brief}}

# launch, resume, poll and the session suite of eval have no recipe: they start or list Claude sessions and must be
# typed exactly (`uv run harness launch|resume|poll|eval …`), because sandbox.excludedCommands covers those
# commands, not `just`; `just evals` runs only what needs no session.

gate run stage:
    uv run harness gate --run {{run}} --stage {{stage}}

approve run stage decision="approved":
    uv run harness approve --run {{run}} --stage {{stage}} --decision {{decision}}

refreeze run:
    uv run harness refreeze --run {{run}}

catalog:
    uv run harness catalog

validate:
    uv run harness validate && claude plugin validate ./plugins && python3 ops/adopt-obsidian.py lint

wiki-lint:
    python3 ops/adopt-obsidian.py lint

graph:
    bash ops/graph.sh

# the regression cases without a session, then the report of the run folder RUN_DIR
evals run_dir:
    uv run harness eval --suite regression --no-sessions --threshold 1.0
    uv run harness pipeline-report {{run_dir}}
