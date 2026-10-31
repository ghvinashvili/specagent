# Finished plans

A plan whose run is merged moves here from `../active/`, a folder `<plan>/` with its `00-index.md`, its `task-NN.md` files
and its `.summary.md`; the text stays as it was when the run ended, except that a path it names follows the move
(`exec-plans/active/<plan>` became `exec-plans/done/<plan>`, the template's README became `docs/template/PROJECTS.md`),
and a name the template renamed follows the rename (SpecAgent session, role type). `harness plan-lint` reads
`../active/` only, so a plan
here is history, not a form to follow: write a new plan in `../active/` (rules in `../active/README.md`). Each plan folder
gets one line below, linking its `00-index.md`; its task files need no line of their own.

## Plans
- [pipeline-fold](pipeline-fold/00-index.md): fewer hand-overs in the SpecAgent pipeline, measured (six tasks)
- [manager-build](manager-build/00-index.md): the template's manager-build run, eleven tasks to release 1.5.0
