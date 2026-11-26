---
paths:
  - "core/**/*.py"
  - "ingestion/**/*.py"
  - "vault_writer/**/*.py"
  - "run_pipeline.py"
  - "recheck.py"
---
# Pipeline conventions
Applies when you edit the discovery and write path. Adds to CLAUDE.md.

## Do
- Keep the unattended path zero-LLM. Keyword, regex and structural logic only (`core/relevance.py` is the elaborate-but-zero-LLM example). `enrich.py` is the one manual tool, run by a human, and it stays zero-LLM too.
- Make an eligibility check permissive by default: missing or ambiguous data passes, and only a named negative signal rejects, such as a denylist token like `_NON_US` in `core/filter.py`.
- Keep the write gate order in `vault_writer/validate.py`: `required_fields`, `not_duplicate`, `cross_source_duplicate`, `url_liveness`, `format_compliance`. Free checks run before the one that makes a network call, and the first failure wins. Put a new check where the cheap ones come first, and say why.
- Cite real data on every new rule: the posting, company or fixture it was checked against, and the date, in a comment beside it.
- Before you report done, run `python3 .claude/skills/review-loop-change/scripts/check_conventions.py --against origin/master`, or `/review-loop-change` for the full review.

## Never
- Never add an LLM SDK import, an LLM HTTP call, or a prompt-shaped string to the unattended path. Add the logic as a rule instead.
- Never make an eligibility gate reject on missing data. That silently drops real postings before a human sees them. The write gate in `vault_writer/validate.py` is the one fail-closed exception.
- Never write a dossier to the vault unless `validate()` returned `passed` for that item.
