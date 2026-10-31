# Plan — calculator

## Task order
| Task | title | builder | depends_on | files | milestone |
|---|---|---|---|---|---|
| 1 | Parser | a | — | `src/{parser,lexer}.py`, `tests/test_parser.py` (new) | M1 |
| 2 | Docs | b | — | `docs/guide.md`, `src/lexer.py` | M1 |
| 3 | Tests | a | 1 | `tests/test_parser.py`, `tests/**` | M1 |
| 4 | Build | b | 2 | `build/*.cfg`, `docs/guide.md` | M2 |
