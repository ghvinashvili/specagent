# Quality score

| Component | Score (0–5) | What lowers it | Measured by |
| --- | --- | --- | --- |
| packages/<package> | — | fill in per package | `just test <package>`, coverage |
| packages/harness | 2 | not re-scored since TD-001 was closed as stale (manager-build Task 9); the release review scores it | `harness validate`, tests |
| .claude configuration | 4 | the pinned version (`requiredMinimumVersion`, Dockerfile) not yet agreed | `harness validate` |
| docs | 3 | two design docs in draft | `harness docs-check` |

Rules: a score changes only with a linked measurement; the file is reviewed at every release.
