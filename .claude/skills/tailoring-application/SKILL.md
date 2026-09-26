---
name: tailoring-application
description: Runs the Tailor sequence (draft, plan, human approval, Humanizer gate, write, link) for one real application's resume and cover letter, per Application Document Preparation. Use when a real Applying note exists and its documents need drafting. Resume-side blocker cleared 2026-08-29 (Main Resume.md is real); cover-letter-side still blocked on Main Cover Letter.md not existing — see the skill's own first step, which checks current state before doing anything, rather than trusting either "still blocked" or "already cleared" as a given.
---

# /tailoring-application

Thin entry point over the `applying` subagent (`.claude/agents/applying.md`), which owns the actual `draft`/`plan` logic. This skill's only job beyond invoking that agent is the parts of `Application Document Preparation`'s sequence that happen around it: confirming current block state (don't trust a stale note — check the real files), and handing the approved plan onward to the Humanizer gate and the write step, which now has real tooling (see Step 4).

## 0. Check the block first — check real files, not a note about them

**Corrected 2026-09-06**: this step used to say "Main Resume.md is still generic filler" — that was true when written (2026-08-28) and stale by the next day (2026-08-29, when the file was actually rebuilt). Don't repeat that mistake: read `20_Progress/Internship/Resumes/Main Resume.md` directly and check whether it still carries `#evidence/user-confirmed-<date>` tags and real Experience/Projects content, rather than trusting this note's own claim about it. As of 2026-09-06 it does — the resume half is real. Separately, check `20_Progress/Internship/Cover Letters/Main Cover Letter.md` directly — if it doesn't exist, or exists with most fragment slots still `#evidence/needed` placeholders, **stop here for the cover-letter half and tell the user** (`.claude/agents/cover-letter-builder.md`, promoted 2026-09-08, is what fills this in). Do not invoke `applying` against filler content for whichever half is still blocked — check both independently, since one clearing doesn't mean the other has.

## Steps (once the block above has actually cleared)

### 1. Confirm the Applying note exists
Per `Application Document Preparation`'s `prepare` step — this skill runs *for* an existing Applying note (`status: Preparing`), it does not create one. If none exists yet for this application, that's a separate, earlier step (creating the note from `Applying Template`), not this skill's job.

### 2. Invoke `applying`
Hand it the Applying note's path. It reads the JD/fit/networking fields, `Main Resume.md`/`Main Cover Letter.md`, drafts, and returns a content plan for approval — it does not write past that point.

### 3. Relay the plan for approval
Present `applying`'s content plan to the user exactly as returned. On approval, the plan moves to the Humanizer gate (`30_Order/Standards/Humanized Writing Standard`) — still manual as of this writing (the Humanizer gate itself has no automated tooling yet); flag that clearly rather than assuming it's been run.

### 4. Write — real tooling now exists (added 2026-09-06)

Once a plan has passed the Humanizer gate, hand the approved resume content to `generating-resume-docx` and the approved cover-letter content to `generating-cover-letter-docx` (both `.claude/skills/`, sibling to this one). Each is format-only — they lay out already-approved content into a real `.docx`, they do not decide anything. Report back both generated file paths and any format warnings either skill returns; a warning (e.g. content running long) is the human's call, not something to resolve silently.

### 5. Link

Once both documents are written, update the Applying note's `resume_version`/`cover_letter` fields to point at the real files — per `Application Document Preparation`'s `link` step. This skill does the update; it is not automatic.

## What this skill does not do

- Does not draft content itself — that's `applying`.
- Does not decide the letter's or resume's actual wording — `generating-cover-letter-docx`/`generating-resume-docx` lay out already-approved content, they don't write it.
- Does not run the Humanizer gate itself — that's a separate, still-manual step before Step 4.
- Does not create the Applying note — that's a separate, earlier vault-side step.
