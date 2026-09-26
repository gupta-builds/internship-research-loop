---
name: generating-cover-letter-docx
description: Turns an already-approved cover letter content plan (from the `applying` agent or `.cursor/skills/cover-letter-alteration`) into a real, correctly-formatted `.docx` — one page, Times New Roman 11-12pt, single-spaced with a blank line between paragraphs, closing with a typed name and the same contact/links line as the resume header. This is the missing DOCX-generation mechanism named in `Resume & Cover Letter - System Map.md`'s Status section. Use whenever a cover letter content plan has been approved and needs to become a real Word document — never to choose what the letter says.
---

# Generating a cover letter .docx

You are the last, mechanical step in the cover-letter pipeline: format, not content. By the time you run, a human has already approved which experiences, hook, and closing go in the letter (`applying` agent's Step 4, or `.cursor/skills/cover-letter-alteration`'s approval gate) — your only job is laying that approved text into a real Word document that matches the sourced format rules, and telling the truth if it doesn't fit.

## Reference

[`reference/cover-letter-reference.md`](reference/cover-letter-reference.md) — every format rule, cited to its real source, plus a fabricated example showing the exact structure. Read this before generating anything if you haven't — it documents a real correction to an initial double-spaced/two-page assumption.

## Precondition — do not skip

**You are never the one deciding what the letter says.** Confirm the content you've been given is an *already-approved* plan (the `applying` agent's own "Ready for approval — nothing written yet" gate having actually been answered "yes," or equivalent) before generating anything. If it hasn't been through that gate, stop and say so.

## Steps

### 1. `python-docx` (low freedom)
Already in `requirements.txt` (`python-docx==1.2.0`, added 2026-09-06).

### 2. Build the `ContentPlan` (medium freedom — shape fixed, wording is the approved content verbatim)
`sender_name`/`contact_line` from `Main Resume.md`'s header, verbatim. `date` today, written out. `recipient_lines` from the Applying/Program note. `greeting` — "Dear \<Company\> Hiring Team," unless a real named contact exists. `paragraphs` — the approved plan's paragraphs verbatim, never paraphrased at this step. Leave `closing`/`font`/`font_size` at defaults unless there's a stated reason to deviate.

### 3. Generate, verify, report (low freedom)
Call `build_cover_letter(plan, output_path)` in [`scripts/generate_cover_letter_docx.py`](scripts/generate_cover_letter_docx.py), `output_path` = `Cover Letters/<Role> - <Company>.docx` (Cover Letter Alteration Standard §4's naming convention). Report every warning it returns — even on success, a warning is real information the human should see, not something this skill quietly absorbs. Read the file back with `python-docx` (margins/font/paragraph count/word count) before reporting success — a clean function return alone is not sufficient evidence.

## Output format

```
## Cover letter generated: <Role> - <Company>

**File:** <path>.docx
**Verified:** <margins>, <font>/<size>, <paragraph count>, <word count>
**Format warnings:** <none, or list every warning returned>
```

## What this skill does not do

- Does not select experiences, hook, or closing content — that's upstream.
- Does not run the Humanizer gate — that happens on the approved plan before this skill runs.
- Does not paraphrase or "improve" approved wording — lay it out, don't rewrite it.
- Does not shrink font/margins below the Standard's range to force a fit — report the warning, let a human decide.
