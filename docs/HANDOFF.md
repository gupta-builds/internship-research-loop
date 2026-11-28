# Handoff

Written by hand until a later phase ships a handoff skill. The SessionStart hook prints the live git and run facts; they are not stored here.

## Current goal
Land the C3 checks (issue #66, branch `chore/claude-checks`): `humanizer_check.py`, `evidence_check.py`, `verify_docx.py`, the phrase list and limits, and the skills `checking-evidence` and `humanizing-writing`.

## Done
- C1 (PR #77) and C2 (PR #84, with the note-writer follow-up inside it): merged.
- C3, not merged: three check scripts with 102 tests over synthetic fixtures (suite 865); both skills with references; `tests/claude_layer/evals.md` with twelve nested-session results; the lint's `PENDING_OWNER` excusal for the two skills until C4 ships their owning agents.
- Every check was shown to fail under a named mutation (49 rows, in the PR's review record). Two Sonnet red teams wrote 40 synthetic cases from `--help` alone (four wrong answers fixed); an independent Sonnet review returned REVISE with 20 findings and 7 surviving mutations, and every correctness finding and survivor is fixed and tested.

## Next
1. Anant reviews and merges the C3 PR, then runs `git pull --ff-only` in the main checkout and `graphify update .` there.
2. C4 (`chore/claude-application-flow`, issue #67) starts from `origin/master` in the same session. It ships `application-drafter` and `application-reviewer`, so it must delete both `PENDING_OWNER` entries; the lint fails once an agent owns either skill.
3. C4 decides which agent owns `finding-resources` and how the drafter and reviewer share `checking-evidence` and `humanizing-writing` (the lint allows one owner).

## Constraints carried forward
- "Never merge, never push to master, never --no-verify, never plain --force, never git add -A or git add ."
- "The repo and the vault are public: no application content or private note content anywhere."
- "No LLM in any script or hook."
- "A check is real only if it can fail": each phase shows a named test going red under a mutation.

## Decisions
- 2026-11-26 | `lint_note.py` decides from the vault linter's `FIT:` line | the linter exits 0 on a failing note | C2 build
- 2026-11-26 | Program and Contact notes take the dossier's file name | four Standards say so | C2 build
- 2026-11-27 | `PENDING_OWNER` in the lint, not LEGACY, for skills whose owner ships later | LEGACY means retired; the entry fails once an agent owns the skill | C3 build
- 2026-11-27 | `verify_docx.py` reads fonts and the word ceiling from the two generators | one copy of each number | C3 build
- 2026-11-27 | Warn findings print but never fail `humanizer_check.py` | a tell-list hit is a prompt to look, not proof | C3 build
- 2026-11-27 | `evidence_check.py` takes `--kind` and refuses `--jd` for a resume | the Plan's skill draft says the posting is never a source for a resume | C3 build

## Open questions
- [ ] Add allow entries for the C2 and C3 scripts and the Jina tools in `settings.json` (C4 edits that file)?
- [ ] Which Program file name wins: the dossier's or `<year>-<Company>-<Role>`? A vault session settles it in the Standard.
- [ ] The vault ignore rule for `Programs/` and `Applying/`, before C4.
- [ ] LibreOffice is not installed, so `verify_docx.py` never measures page count.
- [ ] `limits.json` is not in `protect_files.py`'s list (C3 could not edit hooks); `verify_docx.py` is not yet called by the generator skills (C4 fixes their text).
