# Handoff

Written by hand until a later phase ships a handoff skill. The SessionStart hook prints the live git and run facts; they are not stored here.

## Current goal
Land the C2 follow-up (issue #87, branch `chore/claude-c2-follow-up`): the allow entries, the loop contract record, the vault ignore rule, and mutation-checked tests for the three C2 scripts. Then C4 (issue #67) is next.

## Done
- C1 (PR #77), C2 (PR #84, with the note-writer follow-up inside it) and C3 (PR #90) are merged.
- C3: three check scripts (`humanizer_check.py`, `evidence_check.py`, `verify_docx.py`) with synthetic fixtures; the skills `checking-evidence` and `humanizing-writing`; `tests/claude_layer/evals.md`; the lint's `PENDING_OWNER` excusal for the two skills until their owning agents ship. Every check was shown to fail under a named mutation (49 rows, in the PR's review record); an independent Sonnet review returned REVISE and every correctness finding and surviving mutation was fixed and tested.
- C2 follow-up (this branch): `/promote` was run interactively by Anant (questions through `AskUserQuestion`, he declined at the consent question, nothing was written); seven read-only allow entries added to `.claude/settings.json` by his choice; 10 tests added after mutation checks (every mutation of the three C2 scripts now turns a named test red); three lines on removing merged worktrees in `docs/TWO_LAPTOP_WORKFLOW.md`.
- Vault side, by Anant's approval: the `Internship Promotion Agents` record names the current command, agents and skills; the vault `.gitignore` ignores Programs, Applying, Tracker and Cover Letters.

## Next
1. Anant reviews and merges the follow-up PR, then runs `git pull --ff-only` and `graphify update .` in the main checkout.
2. Anant runs the two `git rm -r --cached` commands from the C2 run note's Follow-up section (they stop the vault repo tracking those four folders). The agents never run them.
3. C4 (`chore/claude-application-flow`, issue #67) pushes next, from the Opus session. It ships `application-drafter` and `application-reviewer`, so it must delete both `PENDING_OWNER` entries; the lint fails once an agent owns either skill.
4. C4 decides which agent owns `finding-resources` and how the drafter and reviewer share `checking-evidence` and `humanizing-writing` (the lint allows one owner).
5. A vault session edits the Program Standard's file-name line to "the dossier's file name" and decides what to do with the 74 vault notes that still name retired agents (list in the run note).

## Constraints carried forward
- "Never merge, never push to master, never --no-verify, never plain --force, never git add -A or git add ."
- "The repo and the vault are public: no application content or private note content anywhere."
- "No LLM in any script or hook."
- "A check is real only if it can fail": each phase shows a named test going red under a mutation, run with bytecode cleared (a same-size, same-second edit can leave a stale `.pyc` that hides it).
- A vault write goes only through `/promote` and its consent question. Tracker notes are created at submission, never at promotion.

## Decisions
- 2026-11-26 | `lint_note.py` decides from the vault linter's `FIT:` line | the linter exits 0 on a failing note | C2 build
- 2026-11-27 | Program and Contact notes take the dossier's file name | Anant chose it over `<year>-<Company>-<Role>`; the Program Standard line is out of date | C2 follow-up
- 2026-11-27 | `Agent(note-writer)` is not on the allow list | dispatching the writer should still prompt; the consent gate is the only step before a vault write | C2 follow-up
- 2026-11-27 | the vault `.gitignore` ignores `Programs/*`, `Applying/*`, `Tracker/*` and `Cover Letters/*` | the vault repo is public; files already tracked stay tracked until `git rm --cached` | Anant, C2 follow-up
- 2026-11-27 | `AGENTS.md` and `.codex/` still name the retired skills and agents | C6 rebuilds both | C2 prompt
- 2026-11-27 | `PENDING_OWNER` in the lint, not LEGACY, for skills whose owner ships later | LEGACY means retired; the entry fails once an agent owns the skill | C3 build
- 2026-11-27 | `verify_docx.py` reads fonts and the word ceiling from the two generators | one copy of each number | C3 build

## Open questions
- [ ] Allow entries for the C3 scripts (`humanizer_check.py`, `evidence_check.py`, `verify_docx.py`) in `settings.json`; C4 edits that file.
- [ ] LibreOffice is not installed, so `verify_docx.py` never measures page count.
- [ ] `limits.json` is not in `protect_files.py`'s list (C3 could not edit hooks); `verify_docx.py` is not yet called by the generator skills (C4 fixes their text).
- [ ] When Jina has credit again, re-read the posting used for the `/promote` proof: the live page said "Summer 2027" through a summary, the dossier copy said "winter or summer 2027".
- [ ] The permission check could not show a prompt disappearing: neither an allowed nor an unlisted Agent dispatch prompted in the follow-up session, so whether `Agent(company-researcher)` was needed is not shown.
