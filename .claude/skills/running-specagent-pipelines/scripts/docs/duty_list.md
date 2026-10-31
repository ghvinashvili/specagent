# `duty_list.py` — the manager's duty list from the plan
```
python3 -I scripts/duty_list.py extract <plan-dir> [--out <run-dir>/_control/duties.md]
python3 -I scripts/duty_list.py tick <duty-file> D<n> <evidence>
```
Spec 5.1.2: after the index is written and before the launch, every merge the task table implies (a dependency in
another builder's lane, or a `Merged:` marker in a depends_on cell), every marker the prose names, every
`Request point: <KIND> — <why>` line of a task file and the judge's approval, each with the task it blocks. A second
run appends only the new duties. `tick` writes the `date -u` time and the evidence.
