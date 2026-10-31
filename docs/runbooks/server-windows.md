# Runbook: an unattended window on a server

A measurement that must run for hours or days on a server (a soak test, a long crawl, a trial window) runs with nobody
logged in: the window's start script schedules the window's probe and its end as transient systemd timers, and every
result lands in one folder on the server that the main session reads over ssh and never writes.

## The three scripts
They live with the run (its folder outside the repository), not in the product's code, and run as root on the server.
- `<window>-start.sh`, in this order, each step safe to repeat:
  1. the server's checkout is clean (`git status --porcelain` prints nothing), else it stops and changes nothing;
  2. the commit under test is checked out, and the service's units are installed and stopped;
  3. one health check of what the window needs (a ping of the service or of its provider); on a failure the old units
     start again and the script exits 1;
  4. a fresh data folder for the window, so nothing of an earlier window is counted;
  5. the units start only inside the hours the window allows (UTC); outside them the script prints `not started` and
     exits 1, and runs again later;
  6. one line with the start time (T0) in `<out>/start.txt`, then the probe and the end are scheduled (below).
- `<window>-probe.sh <out>`: one check during the window (a crash probe, a count); appends its result to `<out>/probe.txt`.
- `<window>-end.sh <out> <owner>`: stops the units, writes the window's report and copies its data into `<out>/`
  (`end.txt` and the report files), owned by `<owner>`.

The scheduling part of the start script (`OUT=/home/<owner>/<window>`, `OWNER` the user who reads it, `probe` and `end`
in epoch seconds):

```bash
install -d -o "$OWNER" -m 700 "$OUT"
install -m 700 /tmp/<window>-probe.sh /root/<window>-probe.sh
install -m 700 /tmp/<window>-end.sh /root/<window>-end.sh
systemctl stop <window>-probe.timer <window>-end.timer 2>/dev/null || true
systemctl reset-failed <window>-probe.service <window>-end.service 2>/dev/null || true
systemd-run --unit=<window>-probe --on-calendar="$(date -u -d @"$probe" '+%F %T') UTC" \
  --timer-property=AccuracySec=1s /bin/bash /root/<window>-probe.sh "$OUT"
systemd-run --unit=<window>-end --on-calendar="$(date -u -d @"$end" '+%F %T') UTC" \
  --timer-property=AccuracySec=1s /bin/bash /root/<window>-end.sh "$OUT" "$OWNER"
systemctl list-timers '<window>-*' --no-pager
```

## Start
- By hand: `scp <window>-start.sh <window>-probe.sh <window>-end.sh <host>:/tmp/`, then
  `ssh -t <host> 'sudo bash /tmp/<window>-start.sh'`.
- Unattended (a timer or a loop on another machine starts it at a set time): `scp -q -o BatchMode=yes … <host>:/tmp/`
  and `ssh -o BatchMode=yes <host> 'sudo -n bash /tmp/<window>-start.sh'`. `BatchMode=yes` and `sudo -n` fail instead
  of asking for a password, so a start that nobody watches never hangs.

## During the window
- The main session only reads: `ssh <host> 'cat /home/<owner>/<window>/probe.txt'` and the other files of `<out>/`. It
  never writes on the server.
- `ssh <host> "systemctl list-timers '<window>-*' --no-pager"` shows what is still scheduled.

## When it goes wrong
- The server rebooted: transient units live under `/run/systemd/transient/` and are gone. After the window's end time,
  run the end script by hand: `ssh -t <host> 'sudo bash /root/<window>-end.sh /home/<owner>/<window> <owner>'`.
- The window must stop early: `sudo systemctl stop <window>-probe.timer <window>-end.timer` on the server, then the end
  script by hand as above.
- `not started`: the start ran outside the allowed hours; run it again inside them.
