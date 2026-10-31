---
status: accepted
date: 2026-10-03
decision-makers: the human, who chose the user-space way and failIfUnavailable on 2026-10-03; drafted by server-e6, reviewed by server-19
consulted: harness maintainers
informed: all package owners
---

# No command to type, at most one password per machine

## Context and Problem Statement
`docs/decisions/0009-a-checkout-sets-itself-up.md` makes a checkout set itself up and names what needs the
administrator as a command. The human sharpened the requirement: after a clone, nothing is typed in a terminal, so a
fix that `doctor` names as a command is not enough; on Ubuntu one password at most. Two gaps were left, both seen on
the machine the template was built on: `claude --bg`, which starts every role session, refused a checkout Claude Code
had not recorded as trusted, and nothing recorded it; and the role sessions ran their commands unsandboxed, with a
warning that a background session shows nobody.

## Decision Drivers
* After a clone nothing is typed in a terminal; a command that `harness doctor` names is not enough.
* At most one password per machine, and none where the kernel lets a user make a namespace.
* No role session runs unsandboxed without anybody knowing: a background session's warning reaches nobody.
* What the distribution protects stays protected unless the human gives it up knowingly.

## Considered Options
* The launcher records the trust; a role session needs the sandbox; the sandbox is set up as the user where that
  works, with one administrator password where only that helps.
* `harness doctor` names the commands, and the human types them (ADR-0009 as it was).
* The sandbox is required only where untrusted text is read (the quarantine reader); other role sessions run
  without it where it is missing.

## Decision Outcome
Chosen option: the first, because it alone meets every driver. The human chose it on 2026-10-03, after seeing that the
role sessions of the machine the template was built on had run unsandboxed.
- **Trust.** `claude --bg`, which starts every role session, refuses a folder Claude Code has not recorded as trusted,
  and Claude Code looks for the record from the folder up to the repository's root and no higher. A checkout moved into
  a trusted container folder was refused, and a session in bypass mode never showed the dialog that would have
  recorded it. The launcher now records it before `harness launch` or `harness resume` starts a role session
  (`harness/trust.py`): the human asked for the run in this checkout, and its sessions run the checkout's code
  already. The record is the flag alone, and it is given up and tried again when Claude Code changed the file while
  it was prepared. Nothing writes the file while a session starts, and no command a session runs writes it.
- **The sandbox.** Without `socat`, Claude Code ran a role session's commands unsandboxed and only warned, which a
  background session shows nobody; with `socat` and an AppArmor profile that refuses the user namespace inside
  bubblewrap (Zorin OS ships `bwrap-userns-restrict-patched`, Ubuntu offers `bwrap-userns-restrict`), every command
  fails. A role session's settings now hold `sandbox.failIfUnavailable`, so it does not start without the sandbox, and
  the launcher names the reason before it spends a session (`doctor.sandbox_problem`, status `no_sandbox`), with the
  PATH the session will have: a background session inherits the PATH of Claude Code's background service, which
  keeps the one it started with. `ops/machine-setup.py` sets the sandbox up in one of two ways:
  - As this user, without a password, where the kernel lets every program make a user namespace (Ubuntu's
    restriction off, as on Zorin OS; no AppArmor, as in WSL2): a copy of bubblewrap in `~/.local/bin`, which comes
    before `/usr/bin` on PATH, is not the file a distribution's profile attaches to and makes the namespace, which any
    program there may do already; `socat` is unpacked from its Debian package into the same folder. Each copy is
    checked before it moves in, and `socat` only after the namespace works. The SessionStart hook starts this in the
    background and says so in one line; it also refreshes the copies when the system's bubblewrap changed (an update)
    or, once a day, when apt has another version of a package. A failure is remembered for a day, or until the system's
    bubblewrap changes, and meanwhile the session offers the administrator's way with the reason; `--undo` takes the
    copies out and remembers the decline, which only `--user` lifts. The distribution's profile, and the Flatpak
    applications it guards, stay as they are. The human chose this way for that machine over the password.
  - With the administrator, where only that helps (Ubuntu's restriction on, no apt, `~/.local/bin` not first on PATH):
    every change goes into one shell script that runs with one password, `pkexec` opening the system's password window
    in a desktop session, `sudo` asking in a terminal. It disables each AppArmor profile that attaches to
    `/usr/bin/bwrap`, puts in the profile of Claude Code's documentation (bubblewrap may make user namespaces; the
    commands it runs are not confined by it), and installs `socat` last, only when the namespace works or is fixed by
    the same script. The session tells the human what is given up before the password: where Ubuntu's restriction is
    on, any program can then make a user namespace through bubblewrap; where it is off, no program gains a power and
    Flatpak applications lose the distribution's extra layer. The script reaches the root shell as an argument, never
    as a file this user could change in between, and the script that undoes the change is kept. This command, and its
    `--user` and `--undo`, are in `sandbox.excludedCommands` by their exact names: where the sandbox starts but refuses
    the namespace, no command runs inside it, root is out of its reach, and the user-space way writes in ~/.local,
    outside the checkout. Role sessions are denied every excluded command (docs/decisions/0010).
  `--plan` shows what either way would change, without changing it.

### Consequences
- Good: after a clone nothing is typed; on Zorin OS and in WSL2 no password at all, on Ubuntu with its restriction one
  password, once.
- Good: no role session runs unsandboxed without anybody knowing: it does not start, and the launcher says why.
- Bad: the user-space copies shadow the system's `bwrap` and `socat` for every program of this user that finds them on
  PATH (Flatpak calls `/usr/bin/bwrap` by its path); where the restriction is off they can do nothing a program could
  not do already. They follow the system only as often as a session starts. Undo: `python3 ops/machine-setup.py
  --undo`.
- Bad: the administrator's way changes the machine, not the checkout: Flatpak applications lose the distribution's
  extra AppArmor layer, and a distribution update may bring the profile back, after which `doctor` and the hook name
  the same command again. Only the four package managers known here (apt-get, dnf, zypper, pacman) are served.
- Open: a session that is not a role session may still change checkout code with a sandboxed command and then run it
  through an excluded command (`uv run harness launch`, `python3 ops/machine-setup.py`); role sessions are closed to it.

### Confirmation
The tests of `packages/harness/tests/test_trust.py`, `test_machine_setup.py`, `test_setup.py` and `test_access.py`;
`harness doctor` names a missing sandbox with its reason; `harness launch` and `harness resume` answer `no_sandbox`
before a session is spent.

## Pros and Cons of the Options

### `harness doctor` names the commands
* Good, because nothing changes the machine without the human.
* Bad, because the human types commands after a clone, which the requirement rules out.

### The sandbox only for the quarantine reader
* Good, because the other sessions start on any machine.
* Bad, because a role session runs unattended, can change the checkout's code and reach the network; without the
  sandbox only the permission rules stand between it and the machine.

## More Information
- Amends `docs/decisions/0009-a-checkout-sets-itself-up.md`, which stays accepted and points here.
- Role sessions are denied every excluded command: `docs/decisions/0010-a-run-ends-with-integrate-or-abort.md`.
