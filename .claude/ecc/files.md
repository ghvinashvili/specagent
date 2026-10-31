# ECC files

Every upstream file this repository copies from ECC at commit `25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b`: its sha256
there, its copy here, and the upstream lines the review dropped with the criterion of [ECC sources](sources.md),
"Review" (K1-K5, M).

| Upstream file | sha256 at the pin | Copy | Dropped upstream lines |
| --- | --- | --- | --- |
| `rules/python/coding-style.md` | `f9d6d7a39c5f5ea809579fecac591f390fa9264c088c7e209d464d5244747003` | `.claude/rules/ecc/python/coding-style.md` | 8-9 K2; 34-39 "Formatting" (black, isort) K4: formatting is `uv run ruff format .` (justfile, `fmt`) |
| `rules/python/patterns.md` | `d9cab9b536321ea7efc6180668fd48820deaf571400db732f0ca17bdda92b7d0` | `.claude/rules/ecc/python/patterns.md` | 8-9 K2 |
| `rules/python/testing.md` | `92655aa5047ee456501ad6605c428680bac6433965f89ce531fe79627004e8c6` | `.claude/rules/ecc/python/testing.md` | 8-9 K2; 14-19 "Coverage" (`pytest --cov`) K3 |
| `rules/cpp/coding-style.md` | `3d25db0df6aa37cd58117d927020102b4e991fb820b9a6ff193058f0652be611` | `.claude/rules/ecc/cpp/coding-style.md` | 13-14 K2 |
| `rules/cpp/patterns.md` | `0d4ad5083495eb234e43f65ed6e097494c06cf6886774d870fa27e6f11ffb27c` | `.claude/rules/ecc/cpp/patterns.md` | 13-14 K2 |
| `rules/cpp/security.md` | `16ca65265e3202d59046a70bd925d8f882d7f8494152e4839f1e5b89a6c5a2cd` | `.claude/rules/ecc/cpp/security.md` | 13-14 K2 |
| `rules/cpp/testing.md` | `07f8098577dbcf2bdefb24721ec571badd7c646fbe760cc2a2293455515da5dd` | `.claude/rules/ecc/cpp/testing.md` | 13-14 K2 |
| `rules/typescript/coding-style.md` | `cb6fbe555d700a65d466fc27377fbb66d6da0e2bcf4411656918f6a45402af1a` | `.claude/rules/ecc/typescript/coding-style.md` | 10-11 K2; 199 "See hooks for automatic detection" K1 |
| `rules/typescript/patterns.md` | `20870f78aa32429fe13f35b415e9f6f8f7809e39c460cf8146d181b7306159fd` | `.claude/rules/ecc/typescript/patterns.md` | 10-11 K2 |
| `rules/typescript/security.md` | `86b14a5a56f4e61750ab30ca50bd264f52f90f5358303f3028d41030a4c50f18` | `.claude/rules/ecc/typescript/security.md` | 10-11 K2; 25-28 "Agent Support" (the agent `security-reviewer`) K1 |
| `rules/typescript/testing.md` | `92e3d02b4fff30899bc1a2af043d74941adbf3b2c0e972d2fcd2c68c9c2ea70b` | `.claude/rules/ecc/typescript/testing.md` | 10-11 K2; 15-18 "Agent Support" (the agent `e2e-runner`) K1 |
| `skills/python-patterns/SKILL.md` | `103e0130dac33a49d26705fc5a2df804980fcab6a0138d65bc7f370a987d49f6` | `.claude/skills/python-patterns/` (split) | 544-546 `pip install isort` K3; 619-685 "Python Tooling Integration" (black, isort, pylint, mypy, `pytest --cov`, bandit, pip-audit and their `pyproject.toml` block) K3, K4 |
| `skills/python-testing/SKILL.md` | `8f8c24020abbf953727c5995abce8aabeb28d2a593cbc39b7e5de36cf5002abd` | `.claude/skills/python-testing/` (split) | 46-50 `pytest --cov` K3; 293-311 "Parametrized Fixtures" over SQLite, PostgreSQL and MySQL K4: `AGENTS.md`, "Testing": "Tests that need a database run on the database engine production uses (PostgreSQL where production runs PostgreSQL, in a container or a local server), never SQLite or an in-memory stand-in to save time."; 334-360 "Run Specific Tests" (bare `pytest`) and "Configure Markers in pytest.ini" K3; 731-810 "pytest Configuration" and "Running Tests" (bare `pytest`, `--cov`) K3; 819 and 822, the `pytest -m` and `pytest --cov` rows of "Quick Reference" K3 |
| `skills/cpp-coding-standards/SKILL.md` | `f870b47d3493b0ad0b6e3808a679ac3c429b60f03193af6c9dc0e0d9e6981436` | `.claude/skills/cpp-coding-standards/` (split) | none |
| `skills/cpp-testing/SKILL.md` | `a92fb5da9b7e3cd1b4dee185b3eb9d0a55352af6396bf996d2eef72d683784df` | `.claude/skills/cpp-testing/` | none |
| `skills/postgres-patterns/SKILL.md` | `9c8c391ae9e9aa87faa7ca091e1d395c97766df14080d0bfbea8a97721776163` | `.claude/skills/postgres-patterns/` | 10-11 (the agent `database-reviewer`) K1; 64-69 an RLS policy on `auth.uid()`, a Supabase function ("Supabase provides helper functions that simplify RLS if you are using Supabase Auth.", `https://supabase.com/docs/guides/database/postgres/row-level-security`) K5; 140-145 "Related" (the agent `database-reviewer`, the skills `clickhouse-io` and `backend-patterns`) K1; the credit line to Supabase stays |
| `skills/docs-governance/SKILL.md` | `499ac59071e6e2b8fb60f085e337a3a1ec16e200adb8f5b8bc027afb338cf3eb` | `.claude/skills/docs-governance/` | 36-39 and 83-84, routes to the skills `living-docs-governance`, `architecture-decision-records`, `ai-regression-testing` and `loop-design-check` K1 (decisions are recorded with this repository's `adr` skill) |
| `skills/docs-governance/references/artifact-role-contract.md` | `4c22a702c6b0c44659d7999d2cf0a706b7af064562025e28a425c753f0393183` | `.claude/skills/docs-governance/references/artifact-role-contract.md` | none |
| `skills/docs-governance/scripts/audit-docs.py` | `889156ec7b22fa5f08b4f9e5b9a9c918c53b357b24c5aa9f322fdc7e97107622` | `.claude/skills/docs-governance/scripts/audit-docs.py` | none: standard library only, reads files and runs only `git rev-parse` and `git show`; ruff skips it (`pyproject.toml`, `extend-exclude`) |
| `skills/docs-governance/scripts/markdown_links.py` | `148cc371d8143bd5070a9a5c5a1a7cc3e142acfad53c7dae4c4c5f9896ec0b20` | `.claude/skills/docs-governance/scripts/markdown_links.py` | none, as above |
| `skills/conventional-commit-review/SKILL.md` | `c81397a4bfc2ec66986aae7a4dff5a02f78c519bc9774a80778fa9055e7fa2fe` | `.claude/skills/conventional-commit-review/` | 101-106 "Related Skills" (`git-workflow`, `coding-standards`) K1 |
| `skills/agent-security-hardening/SKILL.md` | `0e0895ada90aa8fa085e4257961ebe15f2dff43b843785b1533d4c731186ad81` | `.claude/skills/agent-security-hardening/` | 168-169 (the skills `security-review`, `security-scan`) K1; 172-177 "Related Skills" K1 |
| `skills/eval-harness/SKILL.md` | `3a5339a5a80099a5c9d55da9b6c8e05a690f5befc6f78d779c75dd79d818ca07` | `.claude/skills/eval-harness/` | 6 `tools:` M; 239-272 "Local Framework Utilities" (ECC's `scripts/eval-harness.js` and `scripts/lib/eval-harness/`) K1 |
| `skills/agent-eval/SKILL.md` | `57fa683e356b6f5612bc6d7dc101ae39c126e6edf9a48f4ec53afea3e80d7e5d` | `.claude/skills/agent-eval/` | 7 `tools:` M; 41-42 and 111-112, a `pytest` judge that runs a bare `pytest` K3 |
| `skills/agent-self-evaluation/SKILL.md` | `96bb21eb37760f596789f84ec0a5dad4ef92fc2255e35cd7b88dc4234062b8c1` | `.claude/skills/agent-self-evaluation/` | 18 (a Stop hook, `references/hook-integration.md`) K1; 181-182 (the skills `verification-loop`, `security-review`) K1 |
| `skills/agent-self-evaluation/examples/high-score-example.md` | `59467219aaaa41365953f904d7ffebb46b55c13d497e3646b0561a9ef5f56b0e` | `.claude/skills/agent-self-evaluation/examples/high-score-example.md` | none |
| `skills/agent-self-evaluation/examples/low-score-example.md` | `ee286d3adcbab489c5f277ae094a25e38e9401dc01b6c39987c3f5bf3b61706e` | `.claude/skills/agent-self-evaluation/examples/low-score-example.md` | none |
| `skills/agent-self-evaluation/references/evaluation-criteria.md` | `d1ccdbc90dfe2485a42e7aef2f06b71506dca3010da1ea8765382b8f038f7c61` | `.claude/skills/agent-self-evaluation/references/evaluation-criteria.md` | none |
| `skills/agent-self-evaluation/scripts/evaluate.py` | `04b2a9460a7baba2a8d86993c8aecb068380ee72c5de8ca07d996c4055dcaf5c` | `.claude/skills/agent-self-evaluation/scripts/evaluate.py` | none: standard library only, reads the file it is given; ruff skips it (`pyproject.toml`, `extend-exclude`) |
| `skills/agent-self-evaluation/templates/evaluation-report.md` | `5fc8a0820de9bc74e0a1470e55aaa50b3957aa1b0f947c4b458213b8e39fedbe` | `.claude/skills/agent-self-evaluation/templates/evaluation-report.md` | none |
| `agents/<name>.md` (70 files) | in `agents/README.md` | `.claude/ecc/agents/` | 4-5 `tools:`, `model:` M in every file; the rest per file in `agents/README.md` |
| `hooks/README.md` | `bb7400ce341c526c06c42096469c5c99f2c830ea3cd0f2d38cb0225acba0744a` | `.claude/ecc/hook-recipes.md` | all but 254-306 ("Common Hook Recipes") |
| `LICENSE` | `326146379f01bb137c0a5d3c54770c1aa31076705c8b88a7f6b26a460f6221b2` | `LICENSE` in each unit | none |
