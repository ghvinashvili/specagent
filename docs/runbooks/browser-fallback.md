# Runbook: a page that refuses a bot

A fetcher of the project (a crawler, an ingest, a checker) that a site refuses may read that one page through an
ordinary browser window. The rules come from an earlier project of the owner, where this read every refusing page it was
tried on (three government sites), and where a changed user agent stopped an agent at the safety check for an hour.

## When, and when never
- Only after the bot was refused (a 202 without a body, 401, 403, 406 or 429), and only where robots.txt lets the bot in.
- Nothing disguised: the browser's own user agent, `navigator.webdriver` as Chromium sets it, Chromium's sandbox on, no
  stealth plugin.
- A page the browser is refused too is the site's answer: it is recorded as refused and never tried another way.
- The record of the page says it was read `via: browser`.

## How the read runs
- Playwright's Chromium in a window, `headless=False` (Playwright's default is headless), on an Xvfb display of its own:
  `Xvfb -nolisten tcp -screen 0 1280x900x24 -displayfd <fd>`, which writes the free display number on `<fd>`.
- `chromium_sandbox=True` at launch: Playwright's default is `false`, which turns Chromium's sandbox off.
- Only the page's host is resolved; images, media and fonts are refused; service workers are blocked
  (`service_workers="block"`); the URL the read ends at is checked as each of the bot's own hops is (a public address,
  robots.txt).
- One Chromium on the machine at a time: each read takes one lock file under `/run/lock/`, shared by every reader of the
  machine that starts a browser, waits up to 600 s for it, and fails having opened nothing when it is held longer.
- The browser and its display are closed in `finally`; then a sweep kills any process of the read still alive, found by
  an environment variable that carries the read's folder, and logs what it killed.

## Memory and systemd
- A unit that runs the browser: `KillMode=control-group` (systemd's default, written out), `TimeoutStopSec=30s`,
  `MemoryMax=3G` and `MemorySwapMax=0`, so a hung browser dies with its unit.
- Never under `ulimit -v`: Chromium dies at launch (SIGTRAP) under every address-space limit tried (8, 16 and 32 GB). A
  manual run goes under `systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=0 <command>`.

## Install and failures
- `playwright install chromium` as the user that runs the reads, `playwright install-deps chromium` as root for the
  system libraries, and the package `xvfb` (`command -v Xvfb` prints a path).
- `no display` (Xvfb failed): install the `xvfb` package. `BrowserType.launch_persistent_context: …`: Chromium or its
  libraries, or, where `/proc/sys/kernel/apparmor_restrict_unprivileged_userns` holds 1, an AppArmor profile that lets
  Chromium's sandbox create its namespaces.
- The lock was held for 600 s: another read holds the browser; `pgrep -a chrome` lists what runs.
