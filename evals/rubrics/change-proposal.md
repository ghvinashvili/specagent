# Rubric: a change proposal is ready for a pull request

Grade each criterion as pass, partial or fail and quote the evidence. Answer "Unknown" where the material does not let you judge.

1. Every evidence bullet names a file that exists in a run directory and states what that file shows.
2. The class is the one whose `signal` in docs/quality/failure-taxonomy.yaml the evidence matches.
3. The diagnosis follows from the evidence: no cause is stated without a file.
4. The change is the smallest that removes the cause and touches only the files listed under `files`.
5. The regression case reproduces the failure, and its graders are deterministic wherever the outcome allows it.
6. The cost section names every role type whose instructions change.
7. Nothing in the proposal contradicts `specs/constitution.md` or section 9 of `docs/roles/MANAGER.md`.

Verdict: accept when 1 to 5 pass and none fails; revise when any is partial; reject when 1, 3 or 5 fails.
