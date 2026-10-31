Decision (owner, 2026-10-30): pipeline economy, four rules and one economy row per run.
A session writes its hand-over note at its unit's end; the watcher's unit-end order waits `unit_end_grace` = 600 s.
A repeat's unit is sized k = floor((handoff_at - start) / per-item) to end under 150k (ingest: 5 pages, not 9).
The verifier checks repeat units in pairs and a driver's replay once; the manager writes a facts pack `_inputs/<topic>.md`.
`score_run.py` ends with `| units | cost per unit | sessions per unit | copies per unit | findings per unit | escaped |`.
