---
paths:
  - "docs/**/*.md"
  - "docs/llms.txt"
---
# Documentation rules
- Every new document gets one line, `- [Title](path): one sentence`, in `docs/llms.txt` or in its folder's `README.md` when `docs/llms.txt` links that README (a new ADR: `docs/decisions/README.md`); a plan folder gets its line in `docs/exec-plans/active/README.md`, linking its `00-index.md`. An index stays one line per item and at most 12,000 bytes; links inside code are not checked (`docs/architecture/documentation.md`).
- A page the owner reads gets a short summary `<name>.summary.md` beside it, in English; a summary needs no index line.
- Decisions go to `docs/decisions/NNNN-title-with-dashes.md` from `adr-template.md`; never edit an accepted ADR: a new ADR amends or supersedes it, and the accepted one gets only a pointer line to the new one under More Information.
- Links are relative paths inside the repository; CI checks them with lychee.
- Generated files under `docs/generated/` are never edited by hand.
