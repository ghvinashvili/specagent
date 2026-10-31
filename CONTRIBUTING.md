# Contributing

1. Open an issue with the template; a feature becomes a spec (`/spec`) before code.
2. Branch from `main`; commit with Conventional Commits; the pre-commit hooks must pass (`pre-commit install`).
3. Open a pull request with the template; CI runs tests, `harness validate`, docs lint and Claude review; evals run when harness files change.
4. Decisions are recorded as ADRs (`/adr`); accepted ADRs are superseded, never edited.
5. Role sessions never push; a human pushes and merges.
