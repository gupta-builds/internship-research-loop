---
created: 2026-09-07
type: reference
tags: [internship-research-loop, promote-dossier, example]
---

# Worked example — one full `/promote-dossier` run

Fabricated dossier (Acme, a fictional company), used only to show the real sequence end to end — including running the two new scripts. Never a source of real content.

## 1. Input
Dossier at `List/Dossiers/1 - AI & ML/Software Engineer Intern - Acme.md`, auto-classified into bucket `1 - AI & ML`.

## 2. Reachability check (run first, mechanically — added 2026-09-07)

```
$ python3 .claude/skills/promote-dossier/scripts/check_vault_reachability.py
## Vault reachability check

Sibling git checkout: NOT FOUND -- ...
MCP registration:     POSSIBLE -- jarvis/jarvis-fs MCP server registered in: ~/.claude/.mcp.json ...

Recommended path: Obsidian MCP tools. Before proceeding, actually call
mcp__jarvis__vault_list and confirm it returns real vault content...
```

Confirmed live via `mcp__jarvis__vault_list` before proceeding — the script's config-presence check is necessary, not sufficient.

## 3. The two `AskUserQuestion` questions

- (a) Target folder → human picks `Programs/Serious/`.
- (b) Priority/category override → human keeps the auto-assigned `1 - AI & ML`.

## 4. Contact research

`contact-researcher` subagent invoked with "Acme" — returns, say, "nothing found" across all four categories (a small, low-visibility company). Shown to the human as-is before anything is written.

## 5. Explicit go-ahead

Human answers "yes, write all three notes now."

## 6. Write the trio

`program-writer` writes the Program note, `tracking` writes the Tracker note, this skill writes the Contact note directly (folding in contact-researcher's "nothing found" honestly, not padded).

## 7. Validate the trio (run after writing, mechanically — added 2026-09-07)

```
$ python3 .claude/skills/promote-dossier/scripts/validate_note_trio.py \
    "Programs/Serious/Software Engineer Intern - Acme.md" \
    "Contacts/Each One/Software Engineer Intern - Acme.md" \
    "Tracker/Each One/Software Engineer Intern - Acme.md"

All required fields present on all three notes. Cross-links (Program<->Contact, Tracker->both) consistent.
```

If this instead reported a `[FLAG]` (a missing field, or a cross-link pointing at the wrong note), that's a real defect to fix before reporting the promotion as complete — not something to note and move past.

**Real limitation**: this script only runs against real files on disk (the sibling-checkout reachability path). If the vault was reached via the MCP tools instead (as in this worked example), do the equivalent check by hand — read all three notes back with `mcp__jarvis__vault_read` and manually confirm the same required-fields and cross-link rules the script checks. This is disclosed, not silently skipped.

## 8. Report

```
## Promoted: Software Engineer Intern - Acme

- Programs/Serious/Software Engineer Intern - Acme.md
- Contacts/Each One/Software Engineer Intern - Acme.md
- Tracker/Each One/Software Engineer Intern - Acme.md

Contact research: nothing found (small/low-visibility company).
Validation: all required fields present, cross-links consistent.
```
