# Change proposal: {short title}

- id: {run-id}/P{NN}
- class: {id from docs/quality/failure-taxonomy.yaml}
- target: {instruction | skill | rule | hook | gate | schema | stage table | eval case | template | settings}
- files: {paths that would change}

## Evidence
{one bullet per run file: its path and what it shows; every run in which the failure appears}

## Diagnosis
{why it happened, in terms of what the session received and what the gate checked}

## Proposed change
{the smallest change: the new text or the diff for the target file, and nothing else}

## Regression case
{name of the new case under evals/regression/, its fixture and graders; it fails before the change and passes after it}

## Cost of the change
{which role types lose their cached prefix; which active runs would need `harness refreeze`}

## Version
{the new docs/roles/VERSION and the docs/roles/CHANGELOG.md line}

## Rollback
{the commit to revert and what to watch after the merge}
