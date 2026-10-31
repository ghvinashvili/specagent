# `findings_report.py` — findings per kind and the escape table
```
python3 -I scripts/findings_report.py <run-dir> [--json]
```
Markdown: per kind (C, A, B, BK, V, VK, M, O, J, P) the ids defined, answered and open; V and VK by cause and severity;
J by severity; per task the C, A and V counts; and the escape table, one row per stage that caught a defect (critic
C+A, builder's own B+BK, verifier V+VK, main session M, judge J, owner after the build O) with its count and share,
ending with `escapes past the pipeline's gates: J + O = <n> of <all>`. Exit 2 when the folder is missing.
