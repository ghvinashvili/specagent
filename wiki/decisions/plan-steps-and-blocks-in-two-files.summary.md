Decision (owner, 2026-10-30): the plan file is split, steps in task-NN.md and blocks in task-NN.code.md.
Every fenced block longer than 10 lines sits under `## Block <id>` in the code file, and the step names it (`Block 3b`).
Tests stay in full from the planner; for texts the planner gives the facts and a test, and the builder writes the prose.
harness plan-lint checks the pair; the critic reads the steps and the test blocks, the builder and verifier one block at a time.
