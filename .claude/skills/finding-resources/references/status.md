# Tool and vault state, as measured 2026-11-26

This file is dated. Check each line again before you rely on it, and replace the line with what you measured.

## Tools
- **Jina** is the primary web provider. `web-read --usage` reads the day's use. It was working on 2026-11-26.
- **Firecrawl** has no credits on the account (`web-read --usage` showed 0 tokens on 2026-11-26), so `web-read` cannot fall back to it. The pipeline's own posting fetch still uses it and fails open (issue #74).
- **`mineru-pdf`** is the PDF wrapper on this machine (`~/.local/bin`). Never read a PDF any other way.
- **`node`** runs the vault linter (v24 under `~/.nvm`). Its run is slow: one note took several minutes on 2026-11-26 because it reads the whole vault, so run it in the background and never per edit.
- **`git` inside the vault** can be slow on the `/mnt/d` mount (one command that included `git status` ran past the 120-second limit). `git check-ignore` alone took about 4 seconds. Use `check-ignore`, not `status`.
- **`contact_signals.py`** uses the public GitHub search without a token (60 requests an hour). Its best-match organization can be wrong: a search for "Nuro" returned `NurOS-Linux` on 2026-11-26. Read the organization page before you cite it.

## Vault state
- Git-ignored in the vault repo (checked with `check-ignore`): `Contacts/`. Not ignored: `Programs/` and `Applying/`. Treat both as private anyway; see the Privacy line in `jarvis-map.md`.
- Missing folders the Standards expect: `Tracker/Each One/Applied/` and `Result/`, `20_Progress/Internship/Sent/`, dossier folders `Applied` and `Archived`. The first move creates each.
- `Cover Letters/Main Cover Letter.md` does not exist.
