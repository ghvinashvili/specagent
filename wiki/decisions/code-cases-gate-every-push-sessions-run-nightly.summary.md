Decision (owner, 2026-10-29): code cases gate every push, session cases run nightly.
ci.yml grades the fourteen code cases and every session case's code graders on its recorded baseline, at threshold 1.0.
The session cases run nightly on the owner's machine (evals/nightly.sh) at 1.0, under a worst-case cost cap.
Each lesson class of 2026-10-29 has a case or a lint; access-probe-critic is removed. Supersedes ADR-0028's lines.
