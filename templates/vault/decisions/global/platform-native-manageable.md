---
title: Builds on a platform use the platform's own tools and stay manageable by the owner without AI
type: decision
scope: global
kind: order
template: yes
status: verified
updated: 2026-10-31
audience: [planner, builder, critic]
sources: []
decided: 2026-10-10
by: owner
review: 2027-10-31
why: a platform is chosen for its capabilities, and the owner must be able to manage the result without AI
decision_status: decided
would_change_if: never
---
# Platform-native and owner-manageable

**Rule.** When a site or app is built on a platform (Drupal, WordPress, any CMS or framework with admin tooling), the planner's brief says from the start: use the platform's own tools; everything manageable in the admin interface without AI; custom code only through the platform's extension points and only where the platform has no tool. Static prototypes are the reference for the look and the quality gates, not markup to copy byte for byte.

**Why.** A brief that said to reproduce the prototypes' markup and that nobody edits by hand, together with a cap of three packages, made the planner build lists, page chrome, a contact form and video in custom code; the brief was corrected mid-run. The point of a platform is its capabilities, and the owner must be able to run the result when no AI is at hand.

**How to apply.**
- Name the platform's own tools in the brief (for Drupal: Views, blocks, menus, view modes, SDC, config forms, security-covered contrib modules).
- Check the first planned tasks for custom code that replaces a platform tool.
- Related features are built together: what they share lives in one base module, and each feature is its own module depending on it.
- Every visible label and button goes through the platform's translation system, so the text can be translated later.
