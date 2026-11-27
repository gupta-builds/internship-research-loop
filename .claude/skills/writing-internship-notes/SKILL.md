---
name: writing-internship-notes
description: Writes one Program, Contact, Applying or Tracker note in the Jarvis vault from facts Anant already approved, following the vault's Standard for that family, and lints the result. Use when a promotion or a submission needs a vault note. Never creates a Tracker before submission.
---
# Writing internship notes
The vault's Standards own every field list and heading. This skill points at them and holds only the traps writers keep falling into.

## Inputs and preconditions
- The note family, the facts to write (already approved by Anant), the dossier file name, and `$JARVIS_DIR`.
- Read the family's Standard in `30_Order/Standards/Internship/` and its Template under `30_Order/Templates/Career/` before you write. Do not remember the field list: it changed on 2026-11-21 and six copies of it already disagreed.
- Run `python3 .claude/skills/finding-resources/scripts/check_vault_reachability.py`. It is the one copy of that script. Stop if it exits 1.

## Workflow
1. Find the family: Program, Contact, Applying or Tracker. The file name is the dossier's file name for all four.
2. Read the Standard's Spec block. Required keys and required headings are in it.
3. Read `references/gotchas.md`, then fill the Template. Leave a key blank when the fact is unknown. Never write the string `null`. Keep every wikilink on one line.
4. Check the target path before you write: `git -C "$JARVIS_DIR" check-ignore -q "<path>"`. Exit 0 means ignored. Exit 1 means the public vault repo would track it: write only if your input says Anant acknowledged that, otherwise stop and return it under needs_input.
5. Write the note with the jarvis vault write tool. Read it back from the vault.
6. Run `python3 .claude/skills/writing-internship-notes/scripts/lint_note.py "<path>"` and return its output. It reads the whole vault, so give it a long timeout. If it prints VALIDATOR NOT RUN, say so and stop on that item.
7. Return the path, the fields set, any field left blank and why.

## Output contract
`## Note written: <path>`, the family, the fields set, the lint output as printed, the blanks.

## Rules
- Program: static research only, no live status. The Standard's headings in order. Company Information specific enough that a generic paragraph would be obviously wrong. `deadline_real` comes from a company-owned page, never a list site.
- Contact: one note per internship, status by folder. Every fact has a source. An empty search is a valid result. `Current Draft` is an unsent message under a reminder that nothing sends itself.
- Applying: created when preparation starts. `stage` is never written into `status`. A document key is filled only when the file exists.
- Tracker: created in `Tracker/Each One/Applied/` in the sitting the application is submitted, with `date_applied` set. Never create one earlier, and never in `Current/`.
- Never touch a second note. Report what the paired notes need and let the main session coordinate.
- The Standard owns the numbers (how many lines, which keys). If the Standard and the Template disagree, follow the Standard and report the difference.

## Verification gate
Done when the note was read back from the vault and `lint_note.py` ran. Report its exit code. A lint failure is returned as a finding.

## Do not use for
Notes outside these four families, dossiers (written by the loop), and anything Anant has not approved.

## Reference index
- `references/gotchas.md`: the per-family traps with one wrong and one right example each. Read at step 3.
