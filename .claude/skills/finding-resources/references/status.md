# Tool and vault state, as measured 2026-11-26

This file is dated. Check each line again before you rely on it, and replace the line with what you measured.

## Tools
- **Jina** is the primary web provider, but on 2026-11-26 both the Jina MCP `read_url` and `web-read` returned `HTTP 402: Account balance not enough` after about 4.2 million tokens that day (`web-read --usage`). It had worked earlier the same day. When it returns 402, read pages with `WebFetch`, which returns a model-written summary of the page and not its text, so quote nothing from it as exact and say so in the fact sheet.
- **Firecrawl** has no credits on the account until 2026-11-27 09:55 UTC (the CLI said so on 2026-11-26), so `web-read` cannot fall back to it. The pipeline's own posting fetch still uses it and fails open (issue #74).
- **`mineru-pdf`** is the PDF wrapper on this machine (`~/.local/bin`). Never read a PDF any other way.
- **`node`** runs the vault linter (v24 under `~/.nvm`). Its run is slow: linting one note took 9 minutes 55 seconds and then 16 minutes 25 seconds on 2026-11-26 because it reads the whole vault, so run it in the background and never per edit. It exits 0 even when the note fails (`FIT: 0/1`); `lint_note.py` reads the `FIT:` line instead.
- **`git` inside the vault** can be slow on the `/mnt/d` mount (one command that included `git status` ran past the 120-second limit). `git check-ignore` alone took about 4 seconds. Use `check-ignore`, not `status`.
- **`contact_signals.py`** uses the public GitHub search without a token (60 requests an hour). Its best-match organization can be wrong: a search for "Nuro" returned `NurOS-Linux` on 2026-11-26. Read the organization page before you cite it.

## Vault state
- Git-ignored in the vault repo (checked with `check-ignore`): `Contacts/`. Not ignored: `Programs/` and `Applying/`. Treat both as private anyway; see the Privacy line in `jarvis-map.md`.
- Missing folders the Standards expect: `Tracker/Each One/Applied/` and `Result/`, `20_Progress/Internship/Sent/`, dossier folders `Applied` and `Archived`. The first move creates each.
- `Cover Letters/Main Cover Letter.md` does not exist.
