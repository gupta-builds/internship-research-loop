---
name: tailoring-application
description: Runs the Tailor sequence (draft, plan, human approval, Humanizer gate, write, link) for one real application's resume and cover letter, per Application Document Preparation. Use when a real Applying note exists and its documents need drafting. Currently blocked on Main Resume.md/Main Cover Letter.md not being real yet — see the skill's own first step, which checks this before doing anything else.
---

# /tailoring-application

Thin entry point over the `applying` subagent (`.claude/agents/applying.md`), which owns the actual `draft`/`plan` logic. This skill's only job beyond invoking that agent is the parts of `Application Document Preparation`'s sequence that happen around it: confirming the block hasn't already been checked and reported, and handing the approved plan onward to the Humanizer gate and the write step once those exist.

## 0. Check the block first — do not skip this

Read `20_Progress/Internship/Building System/Resume & Cover Letter - System Map.md`'s Status section directly. If `Main Resume.md` is still generic filler or `Main Cover Letter.md` doesn't exist, **stop here and tell the user** — do not invoke `applying` against filler content. This check exists specifically because the block is the expected state as of this writing; running past it silently would produce a content plan built on fake evidence, exactly what the evidence rule (Resume/Cover Letter Alteration Standard §2) exists to prevent.

## Steps (once the block above has actually cleared)

### 1. Confirm the Applying note exists
Per `Application Document Preparation`'s `prepare` step — this skill runs *for* an existing Applying note (`status: Preparing`), it does not create one. If none exists yet for this application, that's a separate, earlier step (creating the note from `Applying Template`), not this skill's job.

### 2. Invoke `applying`
Hand it the Applying note's path. It reads the JD/fit/networking fields, `Main Resume.md`/`Main Cover Letter.md`, drafts, and returns a content plan for approval — it does not write past that point.

### 3. Relay the plan for approval
Present `applying`'s content plan to the user exactly as returned. On approval, the plan moves to the Humanizer gate (`30_Order/Standards/Humanized Writing Standard`) — not yet automated as of this writing; flag that the `humanize`/`write`/`link` steps are still manual until that tooling exists, same honesty `Application Document Preparation`'s own "What Actually Runs Today" section states.

## What this skill does not do

- Does not draft content itself — that's `applying`.
- Does not write a `.docx`/`.pdf` file — no tooling for that exists yet in this repo.
- Does not create the Applying note — that's a separate, earlier vault-side step.
