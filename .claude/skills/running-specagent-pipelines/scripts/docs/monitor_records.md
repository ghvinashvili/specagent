# `monitor_records.py` — the record monitor: request lines, claims, duties, verdicts
```
python3 -I scripts/monitor_records.py watch <run-dir> [--interval 60] [--hours 8] [--bound <min>] [--grace 300]
python3 -I scripts/monitor_records.py once|report|status <run-dir>
python3 -I scripts/monitor_records.py answer <run-dir> <request-id> <text> [--refuse]
```
The manager's background command (spec 5.1.3): it reads the records every interval and exits 0 with one `WAKE` line
per new event (a `SANDBOX:`, `COPY-REQUEST:`, `CHECKOUT-REQUEST:` or `FF-REQUEST:` line, a request open past the
bound, a second claim of one task, a stalled claim, a due or overdue duty, a `VERDICT:` line, a failed merge check),
or exits 1 after `--hours`; the manager answers and re-arms it with the same command. It answers no request itself:
`answer` writes `SUPPLIED:`, `COPIED:`, `CHECKED-OUT:`, `FF-DONE:` or `REFUSED: <KIND> — <why>` with the time into the
requester's file. Files: `--state` (`_control/monitor.json`: requests with both times, alarms, the heartbeat), `--log`
(`_control/monitor.log`), `--duties` (`_control/duties.md`, ticked when a verified `Merged:` line appears), `--registry`
(`_control/registry.json`, read only), `--config` (default: the agents of `_control/_agents.json`, `_agents.json` and
`_agents-active.json`, read as `check_formats.py` reads them). `report` prints the request table for the measurement
page; `status` exits 0 while a watch is armed (its heartbeat at most 2 × interval + 5 s old), else 1 with the reason.
