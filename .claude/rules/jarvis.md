# Reaching the Jarvis vault

Every agent or skill in this repo that reads or writes vault notes (`program-writer`, `tracking`, `promotion`, `applying`, `/promote-dossier`, `/promote-manual-find`, `/tailoring-application`) needs the Jarvis vault (`gupta-builds/Jarvis`) reachable. There are exactly two ways, and neither should be assumed silently:

1. **Sibling git checkout** — this repo's own automation already expects this layout (`run_pipeline.py`'s `JARVIS_DIR` env var, `jarvis-checkout/` in CI):
   ```
   internship-research-loop/     <- this repo
   Jarvis/                       <- gupta-builds/Jarvis, checked out alongside it
   ```
   If this is how the vault is reachable, use plain `Read`/`Edit`/`Write` on `../Jarvis/...` (confirm the actual path if it's not obviously sibling), and check `git status`/`git diff` in that checkout before committing so a human can see exactly what's about to change.

2. **Obsidian MCP tools** (`jarvis`, `jarvis-fs`) — if Obsidian is running locally with its Local REST API plugin enabled. **Always confirm with a cheap `mcp__jarvis__vault_list` call before relying on it** — an error means "not connected," not "empty vault." This is what `/promote-dossier` was actually verified against on 2026-07-26.

If neither is available: **stop and say so.** Do not guess at vault paths, do not fabricate vault content from memory of what a doc says the vault contains, and do not write across repos via the GitHub API (`mcp__github__create_or_update_file`) as a substitute — `core/git_ops.py` exists specifically to solve the two-writer collision problem for this repo's *one* automated writer; a second interactive writer through a different mechanism reintroduces that race with no retry/rebase handling.

## The write itself is always consent-gated

None of the agents above write a vault note without an explicit human go-ahead, shown *what* will be written first (see `promote-dossier`, `promotion`). This file governs *how* the vault is reached; the consent gate itself is each skill's own job, not repeated here.

## Note-shape contracts

Field-by-field frontmatter for every note type this repo writes lives in `CLAUDE.md`'s "Note-template contracts" section and `.claude/skills/promote-dossier/reference/note-templates.md` — read one of those, not this file, for the actual fields.
