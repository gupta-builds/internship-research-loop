---
name: promote
description: Turns one dossier or one manual lead into a Program note and a Contact note after Anant says yes. Start it by typing /promote. Never writes before consent and never creates a Tracker or an Applying note.
disable-model-invocation: true
argument-hint: [dossier file name, or a company and role for a manual lead]
allowed-tools: Read, Grep, Glob, Agent, AskUserQuestion, mcp__jarvis__vault_read, mcp__jarvis__vault_list, Bash(python3 .claude/skills/finding-resources/scripts/check_vault_reachability.py), Bash(git -C * check-ignore *)
---
# Promote
Step 4 ("Commit") of the Internship Pipeline, for tier 1 and tier 2. A tier 3 application has no Program or Contact note. The input is: $ARGUMENTS

Follow the steps in order. The main session asks every question and owns the consent gate. The two agents cannot ask Anant anything.

## Step 0: Take the input
- Run `python3 .claude/skills/finding-resources/scripts/check_vault_reachability.py`. If it exits 1, stop and say so. Never write across repos through the GitHub API as a substitute.
- A dossier: find it under `10_Areas/Career/Internships/List/Dossiers/` in `$JARVIS_DIR`, searching every subfolder. Read its frontmatter and body. Note `tier`, the role folder, the posting text and the dossier file name, which is the name of both notes.
- A manual lead: ask for company, role, URL and where it came from. The Program note's `list_origin` reads `manual-web-find (Anant, <date>)`.
- If `tier` is 3, stop and say so. A dossier may carry no `tier` key (none of the 357 dossiers read on 2026-11-26 did): then Step 1 asks Anant for it and a tier 3 answer stops here. If a Program note with this file name already exists, stop and say so: updating one is a separate request.
- If the dossier has no posting text ("No posting content fetched"), say so now. Research will have gaps, and Anant should know before he answers anything.

## Step 1: Questions
- Ask with AskUserQuestion: (0) the tier, 1 or 2 or 3, only when the dossier has none; (a) `Serious/` or `Considering/`, shown as equals, because the split is timing and never rigor; (b) the role folder, with the dossier's own folder as the default answer and "keep as classified" as one option.

## Step 2: Research
- Dispatch `company-researcher` with the dossier path, the posting text, the tier and the manual-lead facts if any. Do not pass this conversation. Show its fact sheet to Anant exactly as returned, and ask its `needs_input` questions in one list.
- If it returns a fact with no source, send it back once. A fact that still has no source moves under Gaps.

## Step 3: Consent
- Check each target folder: `git -C "$JARVIS_DIR" check-ignore -q "<folder>/x.md"` for the Program folder and for `Contacts/Each One/Ongoing/`. Exit 0 is ignored, exit 1 is tracked by the public vault repo.
- Ask plainly: "Write the Program and Contact notes now?" Say which of the two folders is tracked by the public vault repo, and what each note will hold. Answering Step 1 is not consent, and silence is not consent. On no, return to Step 1 or 2. Never write one note and leave the other.

## Step 4: Write
- Call `note-writer` for the Program note, then for the Contact note, one call each, in that order. Give each the approved facts, the dossier file name, the target folder, whether Anant acknowledged a tracked folder, and the name of its Standard. The Contact `Facts` section carries the fact sheet's sources unchanged. Its `Current Draft` reads "Not yet written".
- Show the lint output `note-writer` returns, as printed. If the Contact write fails after the Program is written, say so plainly and ask Anant what to do. Do not delete anything.

## Step 5: Report
- The two paths, the lint output, any field left blank and why, and the next move for Anant: update the dossier's state by hand as the Internship Notes Standard says, reach out from Mimic, then prepare the application. Create no Tracker and no Applying note.

## Do not use for
Preparing documents. Tier 3 applications. Updating a note that already exists.
