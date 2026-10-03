---
name: generating-resume-docx
description: Turns an already-approved resume bullet selection (from `.cursor/skills/resume-alteration`) into a real, correctly-formatted `.docx` — single column, standard font, real Word bullets, section order matching Main Resume.md. This is the resume-side counterpart to generating-cover-letter-docx, and the other missing DOCX-generation mechanism named in Resume & Cover Letter - System Map.md. Use whenever an approved resume content plan needs to become a real Word document — never to choose which bullets appear.
---

# Generating a resume .docx

Format only, same division of labor as the cover-letter generator. By the time you run, `.cursor/skills/resume-alteration` has already selected which `Main Resume.md` bullets appear, in what order, per Resume Alteration Standard §2/§3. Your job is laying that approved selection into a real, ATS-safe Word document.

## Reference

[`reference/resume-reference.md`](reference/resume-reference.md) — cites `Resume Alteration Standard` §8 directly, plus a fabricated example showing the exact section order and structure.

## Precondition

Confirm the bullet selection is already approved (Resume Alteration Standard §7's gate) before generating. If not, stop and say so.

## Steps

### 1. `python-docx` (low freedom)
Already in `requirements.txt` (`python-docx==1.2.0`, shared with the cover-letter generator).

### 2. Build the `ResumePlan` (medium freedom)
`name`/`contact_line` from `Main Resume.md`'s header, verbatim, identical to what the cover-letter generator uses. `education` from the Education section, generally unchanged. `skills` — the approved, possibly-reordered category list. `experience`/`projects` — each `Entry.header` verbatim from `Main Resume.md`; `bullets` the approved, possibly-reordered, possibly-rephrased-for-JD-terminology subset of that entry's real bullets. `certifications` usually unchanged. `objective` optional — omit the field entirely if the approved plan has none.

### 3. Generate, verify, report (low freedom)
Call `build_resume(plan, output_path)` in [`scripts/generate_resume_docx.py`](scripts/generate_resume_docx.py), `output_path` = `Resumes/<Role> - <Company>.docx` (Standard §5's naming convention). Report every warning — a length warning past one page is a real per-application decision (Standard §8: two pages only where the target company's guidance explicitly says so), never resolved silently. Read the file back to confirm font/bullets/headings before reporting success.

## Output format

```
## Resume generated: <Role> - <Company>

**File:** <path>.docx
**Verified:** <font>/<size>, <bullet count>, <section headings present>
**Format warnings:** <none, or list every warning returned>
```

## What this skill does not do

- Does not select, reorder, or rephrase bullets — that's `.cursor/skills/resume-alteration`'s job.
- Does not decide whether a two-page resume is warranted — reports the warning, lets the human decide.
- Does not touch `Main Resume.md` itself — read-only source.
