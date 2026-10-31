---
paths:
  - "specs/**"
---
# Spec rules
- `spec.md` says WHAT and WHY; implementation choices belong to `plan.md`.
- Mark every guess as `[NEEDS CLARIFICATION: question]`; the plan gate fails while any marker remains.
- `plan.md` keeps the "Phase -1 gates" section filled against `specs/constitution.md`; a failed gate needs a line in "Complexity Tracking".
- `tasks.md` lists tasks with explicit dependencies; the planner turns it into `tasks.json`.
