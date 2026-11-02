---
title: Every change to the template passes an independent verifier before it counts
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-11-02
review: 2027-11-02
audience: [all]
sources: []
decided: 2026-11-02
by: owner
why: the template keeper changes scripts, checks and rule texts that every later run inherits; an error in it repeats in every project, so the owner wants each change verified so that errors are ruled out
decision_status: decided
would_change_if: the owner's word
---
# Verify every template change

**Rule.** Every change to the agentic template (a script, a check, a hook, a rule text, a pack or role file), and its
copies in specagent and the projects, counts as done only after an independent verifier has passed it. The verifier
is a fresh session that did not write the change. It reads the diff, runs the tests and the change's own checks,
mutates new tests to prove they fire ([[verify-yourself-before-saying-done]]), and records findings with a repro.
Each finding is fixed and verified again. The keeper reports each step with its shas and the verifier's verdict and
record path. The manager who asked for the change checks the numbers against its run.

**How to apply.** The keeper gathers several committed steps and sends them to one verifier as a batch, not one
verifier per small change; it works on the next steps meanwhile. A step is not reported as done to the owner, nor
copied into specagent or a project as final, before the verdict.

Related: [[measure-the-effect-of-every-improvement]].
