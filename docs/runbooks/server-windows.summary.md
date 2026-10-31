# An unattended window on a server: summary for the owner

- A long measurement on a server runs with nobody logged in. Its start script checks the checkout, starts the service
  only inside the allowed hours, and schedules a probe and the end as transient systemd timers.
- Every result goes to one folder on the server; the main session reads it over ssh and never writes there.
- A reboot drops the timers: after the window's end time, run the end script by hand.
