# Gotchas by note family

Contents: all four families, then the cross-family traps.

This file holds traps only. The field list, the headings and the limits are in the family's Standard under `30_Order/Standards/Internship/`; read it, do not copy it here. Every Right and Wrong pair below is synthetic. The Standards carry the real examples from the vault.

## Program (Program Standard)
- A blank key stays blank. Right: `deadline_real:` Wrong: `deadline_real: null`. The string `null` is read as text.
- `deadline_real` comes from a company-owned page. A list site or a job board is a lead, so leave the key blank and say so.
- Every wikilink sits on one line. Right: `list_origin: "[[Example Intern - Example Co]]"` Wrong: the link folded over two lines.
- Eligibility is taken from the posting, never inferred. A PhD, clearance or citizenship line goes first.
- Company Information is specific: a project, a date, a link to the paired Contact note. A paragraph that would fit any company is wrong.
- The note records no live status ("applied", "waiting"). That belongs on the Applying note.
- Traps & Gotchas needs a real trap, not a preference.
- The file name is the dossier's file name. The Program Standard's text says `<year>-<Company>-<Role>` while the other three Standards and the notes made since say the dossier's file name. The two disagree; use the dossier's file name and report the disagreement to Anant.

## Contact (Contact Standard)
- One note per internship, not per person. It sits in `Ongoing/`, `Come Back/` or `Ended/`, and `status` follows the folder: `active`, `paused`, `archived`.
- Every fact carries its source. An empty search is a valid result: write "nothing found" under Facts rather than a name.
- `email` stays blank unless verified, and `how_found` says whether it was verified or a pattern guess.
- `name` stays blank when only a search snippet exists. Never infer a name from a profile slug.
- `related_programs` links the paired Program note and must resolve, so the Program note is written first.
- Current Draft opens with the `> [!IMPORTANT]` reminder that nothing sends itself, then reads "Not yet written" until Anant drafts. It is never presented as sent.
- The Conversation Log holds exchanges that happened. A line saying the note was created is not an entry.
- Next Action names one move with a date or a trigger.

## Applying (Applying Standard)
- `stage` and `status` are different keys. A stage word in `status` is wrong.
- `stage` starts at `Preparing`, moves to `awaiting-approval` when the packet is shown, and to `approved` only on Anant's word.
- A document key (`resume_version`, `cover_letter`) is filled only when the file exists. A path to a missing file looks like a finished document.
- `tracker` stays blank until the application is submitted.
- Each approval is a dated Log line, and an active note gets a Log line at least weekly.
- It holds seven headings in order, and none is empty.

## Tracker (Internship Tracker Standard)
- Created in `Tracker/Each One/Applied/` in the sitting the application is submitted, with `date_applied` set. Never at promotion, never `Current/` (the folder holds only trackers made before this rule). A Tracker made earlier records an application that did not happen.
- Copy `tier`, `starred`, `resume_variant` and `letter_mode` from the dossier at apply time.
- A date or result key stays blank until the real date; never `null`. `result` takes only the closed vocabulary the Standard lists.
- There is no approval key. Approval is the Applying note's `stage`.
- `/promote` never creates a Tracker. If a request asks for one before submission, stop and say why.

## Across families
- Never write a second note in the same call. If a paired note needs a change, report it.
- Check `git -C "$JARVIS_DIR" check-ignore -q "<path>"` before a write into a private folder. Exit 1 means the vault repo would publish it.
- Run `lint_note.py` after the write. It is slow (it reads the whole vault); give it a long timeout and run it in the background. A lint failure is a finding to return, not a reason to edit a second note.
- The vault write contract in the vault's root `AGENTS.md` still applies: patch by heading, keep the frontmatter, no file at the vault root.
