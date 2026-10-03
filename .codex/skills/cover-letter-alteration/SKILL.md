---
name: cover-letter-alteration
description: >-
  Drafts a traceable, evidence-only content plan for one application's cover letter from
  the Jarvis vault's Main Cover Letter bank, gets explicit human approval and a Humanizer
  pass, then writes it as Cover Letters/<Role> - <Company>.docx. Use when an Applying note
  exists (or is being created) and needs its cover letter prepared — Application Document
  Preparation's draft/plan/humanize/write sequence, cover-letter half.
disable-model-invocation: true
---

# cover-letter-alteration

Drafts and writes the tailored cover letter for one application, per the Jarvis vault's `20_Progress/Internship/Building System/Cover Letter Alteration.md` design note and its enforceable rules in `30_Order/Standards/Cover Letter Alteration Standard.md`. Sibling to `resume-alteration`, sharing the same Applying note, the same approval gate, and the same Humanizer pass — see `Application Document Preparation` for how the two run together.

## Prerequisite — read this before running

Same vault-access prerequisite as `resume-alteration` (sibling git checkout or the `user-jarvis` MCP namespace, confirmed with `vault_list` first).

Read every run, not from memory:
- `20_Progress/Internship/Building System/Cover Letter Alteration.md` — narrative and flow.
- `30_Order/Standards/Cover Letter Alteration Standard.md` — enforceable evidence/length/naming/overwrite rules.
- `30_Order/Standards/Humanized Writing Standard.md` — shared tone checklist.

**Stop if `Cover Letters/Main Cover Letter.md` does not exist yet.** Unlike Main Resume, this file has never been built — there is no paragraph bank to draft from. As of this skill's authoring (2026-08-28) that master doesn't exist. If it's missing, say so and stop rather than writing a cover letter's narrative content from nothing.

## Steps

### 1. Take the input
Same Applying note as `resume-alteration` — read `program`, `tracker`, `company`, `job_url`, and its Job Description / Fit / Networking one-liners. Don't recreate the Applying note if `resume-alteration` (or the human) already created it in this session.

### 2. Gather evidence
Read `Cover Letters/Main Cover Letter.md` in full — its opening hooks, experience paragraphs, and closings. Read the Program note's Company Information section for a real, specific company fact to open with (never a generic mission-statement line). Every paragraph must trace to a Main Cover Letter fragment, a linked Jarvis project note, or an explicit human-supplied fact — per the Standard's §2, inventing a company-specific detail or a personal claim ("I've always dreamed of...") is exactly the failure mode this rule blocks, not an exception to it.

### 3. Propose the content plan — before writing anything
Present:
- The opening hook and the specific company fact it's built from.
- 2–3 selected experiences, each with the JD requirement it maps to and which source (fragment / project note / human input) it traces to.
- A target word count within the Standard's 250–350 word default (or a stated reason for deviating).
- Any honest gap (a JD ask with nothing real to map to).
Ask explicitly: "Approve this content plan?"

### 4. Humanizer gate
Same as `resume-alteration` step 4 — check the actual paragraph text against `30_Order/Standards/Humanized Writing Standard.md`, flag specific phrases with fixes, never silently rewrite, loop until clean. Cover letters are the format most prone to generic-enthusiasm filler ("passionate about your mission") — check for it explicitly.

### 5. Write the file
On a clean pass, write `Cover Letters/<Role> - <Company>.docx` (sanitized filename; never `Main Cover Letter.*`). **If no DOCX-generation mechanism exists in this environment**, stop and say so — offer a Markdown fallback of the approved, humanized text instead of fabricating a tool call. Overwrite in place while `date_applied` is null on the Applying note; if it's already set, stop and ask first.

### 6. Link back
Set the Applying note's `cover_letter` field to the new file's path, and add a one-line summary of what the letter opens with under its Documents section.

## What this skill does not do

- Does not build `Main Cover Letter.md` itself — that's separate work, and this skill is blocked until it exists (see Prerequisite).
- Does not draft the resume — that's `resume-alteration`.
- Does not submit the application or change `date_applied`/`status`.
- Does not silently fix a Humanizer flag without showing it first.
