---
name: <type-name>
description: '<Sentence 1: what this type does. Sentence 2 starts with "Use when:" and names the exact situations the manager matches. Sentence 3 starts with "Never" and names what it must not do.>'
model: sonnet
effort: medium
tools: Read, Glob, Grep, Bash, Write, Edit, Skill
skills:
  - checkpoint
  - escalate
color: blue
---
# <Type name>

## Purpose
<one paragraph>

## Receives
<what the first message (prompt.md) contains; which paths are inputs>

## Returns
<which files under stages/<stage>/output/ and what result.json says>

## Working method
<ordered steps; every step ends with a checkpoint>
<every numbered step ends with its rule, <!-- check: ... --> in the language of packages/harness/src/harness/gates/steps.py: read:, ran:, wrote:, output:, when:, trust:>

## When you stop
<complete: result.json status complete; escalation: file written, status escalated; otherwise keep going>

## What you never do
<explicit list>
