# Handoff

Written by hand until a later phase ships a handoff skill. The SessionStart hook prints the live git and run facts; they are not stored here.

## Current goal
Land the C2 research and notes layer (issue #65, PR #84): `finding-resources`, `researching-companies`, `writing-internship-notes`, the agents `company-researcher` and `note-writer`, and the `/promote` command.

## Done
- C1 (PR #77, merged): the lint, five hooks, `settings.json`, CLAUDE.md, three path rules.
- C2, branch `chore/claude-research-and-notes` (PR #84, not merged): the three skills with their references, `check_vault_reachability.py`, `contact_signals.py` and `lint_note.py` with 28 tests, the two agents, `/promote`. Six agents and skills retired with their LEGACY rows, plus `.claude/rules/jarvis.md`.
- `/promote` was run end to end on one real dossier and stopped at the consent question with a sourced fact sheet; no vault note was written and no Tracker exists.

## Next
1. Anant reviews and merges PR #84, then runs `git pull --ff-only` in the main checkout and `graphify update .` there.
2. C5 (`chore/claude-code-review`, issue #68) starts from a new worktree, launched inside it, per `docs/TWO_LAPTOP_WORKFLOW.md`.
3. Before C4, `finding-resources` is preloaded by `application-drafter` as well as `company-researcher`; the lint requires exactly one owning agent, so C4 decides which one owns it.

## Constraints carried forward
- "Never merge, never push to master, never --no-verify, never plain --force, never git add -A or git add ."
- "The repo and the vault are public: no application content or private note content anywhere."
- "No LLM in any script or hook."
- A vault write goes only through `/promote` and its consent question. Tracker notes are created at submission, never at promotion.

## Decisions
- 2026-11-26 | `AGENTS.md` and `.codex/` still name the retired skills and agents | C6 rebuilds both and Codex still loads the `.codex/skills/` copies | C2 prompt
- 2026-11-26 | `lint_note.py` decides from the vault linter's `FIT:` line | the linter exits 0 even when a note fails (measured `FIT: 0/1`) | C2 build
- 2026-11-26 | Program and Contact notes take the dossier's file name | four Standards and the notes made since say so; the Program Standard's `<year>-<Company>-<Role>` disagrees | C2 build, reported to Anant
- 2026-11-26 | the `/promote` consent question names which target folder the public vault repo tracks | `Programs/` is not git-ignored; `Contacts/` is | C2 build
- 2026-11-26 | `settings.json` allow list unchanged by C2 | the auto-mode classifier denied adding script entries; a session prompts for the three scripts and the Jina tools | C2 build

## Open questions
- [ ] Add allow entries for the three C2 scripts, `git -C * check-ignore *` and the Jina tools, or keep the prompts?
- [ ] Which Program file name wins: the dossier's or `<year>-<Company>-<Role>`? A vault session settles it in the Standard.
- [ ] The vault ignore rule for `Programs/` and `Applying/`, before C4.
