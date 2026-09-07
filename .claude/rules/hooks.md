# Hooks in this repo

Two hooks, both advisory only — **hooks here inform, they never deny.** The
`ask` entries in `.claude/settings.json`'s permissions block are the actual
gate (currently just `mcp__jarvis__vault_delete` and a few `git`/`gh`
commands); a hook's job is to surface the right context at the right moment,
not to duplicate that gate. Both fail open on any parse problem — a broken
hook must never block real work.

- **`hooks/review-reminder.sh`** (`PostToolUse`, matches `Write|Edit|MultiEdit`) —
  fires after a local edit to one of this repo's four convention-sensitive
  files (`core/filter.py`, `core/relevance.py`, `core/classify.py`,
  `vault_writer/validate.py`, `run_pipeline.py`, `recheck.py`,
  `ingestion/*.py`) and points at `/review-loop-change` plus the specific
  convention from `CLAUDE.md` most relevant to the file just touched.
- **`hooks/vault-write-guard.sh`** (`PreToolUse`, matches the Jarvis
  write-family tools) — fires before `mcp__jarvis__vault_write/patch/move`,
  `mcp__jarvis__vault_delete`, and the `jarvis-fs` write/edit/move tools.
  For a write/patch/move: reminds that the human consent gate
  ([[jarvis]]) should already have happened and the note shape must match
  `CLAUDE.md`'s "Note-template contracts" section. For `vault_delete`
  specifically: reminds it's the one call this repo always asks approval
  for ([[mcp-permissions]]) and to confirm it's a real, single,
  human-approved deletion.

New hooks that touch the vault-writing agents (`program-writer`, `tracking`,
`promotion`, `applying`, `/promote-dossier`, `/promote-manual-find`) should
keep this same shape: advisory, fail-open, one line of `additionalContext`.
If a genuine blocking guard is ever needed, say so explicitly when adding it
— don't silently upgrade an existing advisory hook to a denying one.
