# Measurement: test files run 4 at a time (grants run, 2026-10-25)

Summary written by the writer of spec 006 (2026-10-31) from the record `context/owner-statements/2026-10-25-grants-run-lessons.md`
(item 3), a verbatim copy made 2026-10-29 of lines 58-74 of the grants run's `lessons.md`, which the run's main session
wrote on 2026-10-25 15:55 UTC. The main session took the measurement; the owner agreed to the rule that follows from it.
Pages that use it: [[checks-once-each]].

Quoted from the record:
- "Task 14's Step 5 ran 41 PHPUnit runs one after another: 2 h 35 min."
- "The main session measured four gd_lists kernel files in one DDEV project: 157 s one after another, 63 s at once, the same
  tests and assertions passing (each kernel test takes its own database prefix), at least 13.5 GB of memory free."
- The rule drawn: run two or more test files four at a time, slowest first; "A test that fails only in the parallel run and
  passes alone is a finding `(code)` (it shares state), not a reason to run one after another." At most 4 at once per role
  ("`PAR_JOBS` stays 4"), because the builder, the verifier and the plan roles' prototypes share one machine.
