---
name: testing
description: "Runs and interprets this repo's pytest suite, and drafts a new test file (for human review, never auto-added) when a new ingestion source or filter rule needs one — a thin entry point over the `testing-tools` agent. Use before committing new tests, when the suite fails and the reason isn't obvious, or when adding a source and unsure whether it needs the schema-drift test pattern."
trigger: /testing
---

# /testing

Thin entry point over the `testing-tools` subagent (`.claude/agents/testing-tools.md`), which owns the actual suite-running, failure-interpretation, and test-drafting logic — matching this repo's own `promoting-manual-find` → `promotion` and `tailoring-application` → `applying` pattern (a slash trigger for a human to type, delegating the real work to an agent scoped tightly to this codebase's own conventions).

## Why this needed building (2026-09-06)

This skill's folder existed but was empty — no `SKILL.md` — while `testing-tools.md`'s own agent file was real and complete. Unlike `tracking`/`program-writer` (correctly agent-only, invoked internally by `promotion`/`promote-dossier`, never by a human directly), `testing-tools` is described as something to "use proactively before committing new tests" — a standalone tool a human reaches for directly, same shape as `/review-loop-change`. That means it needed a real slash-trigger entry point; the empty folder was a genuine gap, not intentional agent-only scoping.

## Steps

### 1. Take the input
No argument → run the full suite and report. An argument naming a source/module → check whether it needs a new test (the schema-drift pattern) rather than assuming. A described failure → interpret it against the actual failing test and the code it exercises, not the assertion message alone.

### 2. Invoke `testing-tools`
Hand it exactly what was given in Step 1. It runs `python -m pytest -q` for real, reads real failures against real code, and — only when explicitly asked to draft a test — writes the actual `test_*.py` content, never a prose description of what a test should check.

### 3. Relay its report as-is
Present `testing-tools`'s output exactly as returned, including its own read-only discipline (it never edits `core/`/`ingestion/`/`vault_writer/`, never commits a new test file itself). If it drafted a test file, that draft is for human review before it's added to the tree — say so plainly, don't imply it's already part of the suite.

## What this skill does not do

- Does not run the suite itself, interpret failures itself, or draft tests itself — `testing-tools` owns all of that; this is a thin dispatcher.
- Does not edit application code under any circumstance.
- Does not add a drafted test file to the tree — that's a separate, explicit human (or follow-up edit) action.
