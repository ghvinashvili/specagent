Decision (owner, 2026-10-30): the critic reviews the plan only; the verifier reads each built commit's diff.
The critic keeps one coverage round per task (C and A ids) and never opens a checkout's code.
The verifier reads the diff by file against the task's steps and the spec; each V id is `(code)`, `(plan)` or `(spec)`.
R ids are retired for new runs, old runs still parse; one critic by default, the odd/even parity stays an option.
