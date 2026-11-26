# Handoff

Written by hand until a later phase ships a handoff skill. The SessionStart hook prints the live git and run facts; they are not stored here.

## Current goal
Land the C1 Claude-layer foundation (issue #64, PR #77): the lint, the hooks, settings, CLAUDE.md and the path rules.

## Done
- C1, PR #77 (draft until its checks are green): `scripts/lint_claude_layer.py` run as a test; hooks `bash_guard.py`, `protect_files.py`, `session_context.py`, `stop_gate.py`, and `verdict_check.py` (unwired); `settings.json`; CLAUDE.md; rules `conventions.md`, `tests.md`, `workflows.md`.

## Next
1. Anant reviews and merges PR #77, then runs `git pull --ff-only` in the main checkout.
2. The next phase (C2) starts from a new worktree, launched inside it, per `docs/TWO_LAPTOP_WORKFLOW.md`.
3. C2 retires the note-writing agents and skills it replaces and deletes their entries from the LEGACY table in `scripts/lint_claude_layer.py`.

## Constraints carried forward
- "Never merge, never push to master, never --no-verify, never plain --force, never git add -A or git add ."
- "The repo and the vault are public: no application content or private note content anywhere."
- "No LLM in any script or hook."

## Decisions
- 2026-11-26 | `Bash(gh api *)` leaves the allow list | it approved API merges and ref writes with no prompt | C1 Execution Map, approved by Anant
- 2026-11-26 | `git commit -a` is blocked by `bash_guard.py` | it stages every tracked change | C1 Execution Map, approved by Anant
- 2026-11-26 | the lint runs as a pytest test; `scripts/hooks/pre-push` is not edited | CI and pre-push already run the suite | C1 Execution Map, approved by Anant
- 2026-11-26 | `verdict_check.py` is built and tested in C1, wired in C4 | no reviewer agent exists yet | C1 Execution Map, approved by Anant
- 2026-11-26 | the graphify post-merge hook keeps a plain detached `graphify update` once the vault export is removed | same as post-commit and post-checkout | Anant's answer to the C1 map

## Open questions
- [ ] None recorded for this repo. Vault-side follow-ups live in the vault's C1 run note.
