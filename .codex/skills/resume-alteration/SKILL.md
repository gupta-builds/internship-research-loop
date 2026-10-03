---
name: resume-alteration
description: >-
  Drafts a traceable, evidence-only content plan for one application's tailored resume
  from the Jarvis vault's Main Resume, gets explicit human approval and a Humanizer pass,
  then writes it as Resumes/<Role> - <Company>.docx. Use when an Applying note exists (or
  is being created) and needs its resume prepared — Application Document Preparation's
  draft/plan/humanize/write sequence, resume half.
disable-model-invocation: true
---

# resume-alteration

Drafts and writes the tailored resume for one application, per the Jarvis vault's `20_Progress/Internship/Building System/Resume Alteration.md` design note and its enforceable rules in `30_Order/Standards/Resume Alteration Standard.md`. This is a human-in-the-loop step: it never invents a claim it can't source, and it never writes a file without explicit approval of the content plan **and** a pass through the Humanizer gate.

## Prerequisite — read this before running

**Needs the Jarvis vault reachable**, same two paths `promote-dossier` documents (a sibling git checkout, or the `user-jarvis` MCP namespace — confirm with `vault_list` before assuming it's connected). This skill is vault-side work; it does not touch this repo's own pipeline code.

**Read the design contract first, every run** — don't work from memory of what these say:
- `20_Progress/Internship/Building System/Resume Alteration.md` — the narrative and per-application flow.
- `30_Order/Standards/Resume Alteration Standard.md` — the enforceable evidence/tailoring/naming/overwrite rules.
- `30_Order/Standards/Humanized Writing Standard.md` — the tone checklist the draft must pass before writing.

**Stop if `Resumes/Main Resume.md` is not in evidence-tagged shape yet.** As of this skill's authoring (2026-08-28), Main Resume is still generic filler, not a bullet bank with sourced claims — that rebuild is separate, gated work. Running this skill against the current Main Resume would mean tailoring from unreliable source material. If that rebuild hasn't happened, say so and stop rather than drafting from what's there today.

## Steps

### 1. Take the input
Accept an Applying note path (`20_Progress/Internship/Applying/<name>.md`) or a Program note to prepare one for. Read its `program`, `tracker`, `company`, `job_url` fields and its Job Description / Fit / Networking one-liners. If the Applying note doesn't exist yet, create it from `30_Order/Templates/Career/Applying Template.md` first (`status: Preparing`, `date_applied: null`) — this is Application Document Preparation's `prepare` step.

### 2. Gather evidence
Read `Resumes/Main Resume.md` in full. Read the JD (via `job_url` or whatever the Applying note/Program note already captured). Read any Jarvis project notes the Main Resume's bullets cite. For every JD requirement, check whether it's covered by an existing Main Resume bullet or a cited project note — per the Standard's §2, a requirement with no match anywhere is a **gap**, not something to fill by inventing a bullet. If the human is present, ask about a genuine gap rather than skip it silently.

### 3. Propose the content plan — before writing anything
Present, as a short structured list, not the final document text:
- Which existing bullets are selected, in what order, and why (which JD requirement each one answers).
- What wording is rephrased to mirror JD terminology, with the original next to it, so the human can see the change is cosmetic, not factual.
- Any honest gaps (JD requirements with no matching evidence).
Ask explicitly: "Approve this content plan?" — a yes/no, not implied by the human having read it.

### 4. Humanizer gate
Only after approval, run the plan's actual bullet text against `30_Order/Standards/Humanized Writing Standard.md`'s checklist. Flag anything that matches a prohibited pattern (generic filler, corporate padding words, repetitive structure, tone louder than the underlying fact) with the specific phrase and a suggested fix — never silently rewrite it yourself without showing the flag. Loop back to step 3 for any fix, then re-check, until the draft passes clean.

### 5. Write the file
On a clean pass, write `Resumes/<Role> - <Company>.docx` (sanitized filename, per the Standard's §5 — never `Main Resume.*`, never a subfolder). **If no DOCX-generation mechanism is set up in this environment yet**, stop before this step and tell the human plainly — offer to write the approved, humanized content plan as a Markdown file instead (e.g. alongside the Applying note) so the work isn't lost, but do not fabricate a DOCX-writing tool call that doesn't exist. Overwrite in place if this application's resume already exists and `date_applied` is still null; if `date_applied` is already set, stop and ask before touching the file — per the Standard's §6, a submitted application's resume is historical.

### 6. Link back
Set the Applying note's `resume_version` field to the new file's path, and add a one-line summary of what the resume leads with under its Documents section — not the full plan, which stays in this conversation / the Program note's own history.

## What this skill does not do

- Does not rebuild `Main Resume.md` — that's separate, gated work (see the design note's "Not Yet Built").
- Does not draft the cover letter — that's `cover-letter-alteration`, run alongside this one per `Application Document Preparation`, sharing the same Applying note and approval gate.
- Does not submit the application or change `date_applied`/`status` — that's Internship Pipeline Step 7, a later, separate human action.
- Does not silently rewrite a draft to fix a Humanizer flag — every fix is shown, never applied invisibly.
