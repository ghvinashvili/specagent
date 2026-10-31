# Learning record (form)

One lesson as a record, in the shape of ECC's instinct model without its hooks. Roles write only the run's
`lessons.md` and their own record; the manager writes records into pages, and only what was checked is remembered.

- trigger: <what was seen, in one sentence>
- action: <the rule that answers it, in one sentence>
- evidence: <path>:<line> of the record that shows it (a finding, a log line, a measurement)
- confidence: <0.3 to 0.9> (0.3 for one sighting, raised as it recurs or is measured)
- scope: run | project | global (the run's `lessons.md`, the project's `wiki/decisions/`, the vault's `decisions/global/`)

Promotion, by hand (the ladder in the pipeline skill's `SKILL.md`, "Briefs"): a cause shared by two findings becomes a
one-line rule under "Lessons from this run"; a record whose trigger recurs in two runs or two projects becomes a rule
where its reader is: a decision page (`wiki/decisions/` for a project; `decisions/global/` for all, only with its proof
page and the owner's yes, see `rules.md`) or a line in the skill or the brief template. Two findings share a cause when
they cite the same checklist item;
`python3 -I <skill>/scripts/manager/measure_manager.py checklist <run>/critique.md <run>/verify.md` lists the items
by the number of findings citing them, highest first. Before a run's "Read first" is compacted, `audit_read_first.py`
shows what would be lost; a finding with a read-only command becomes an eval case by `replay_cases.py`.
