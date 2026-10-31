# A page that refuses a bot: summary for the owner

- Only after the bot was refused and where robots.txt allows it: one read by an ordinary Chromium window on an Xvfb
  display of its own, with its own user agent and its sandbox on. Nothing is disguised.
- One browser per machine (a lock), closed in `finally`, then a sweep of what it left; under systemd
  `KillMode=control-group` and a memory limit, never `ulimit -v`.
- A page the browser is refused too is the site's answer.
