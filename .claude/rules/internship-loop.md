# This repo's conventions

Read `CLAUDE.md`'s "Conventions this codebase enforces" section and follow it before touching `core/`, `ingestion/`, `vault_writer/`, `run_pipeline.py`, or `recheck.py`: zero-LLM in the unattended path, permissive-by-default filtering, fail-closed write-gate ordering, every new rule cited to real data. Not restated here — `CLAUDE.md` is the canonical copy; a second copy in this file would be the exact duplication this vault's own build standard warns against ("if a sentence is true in both, one copy is wrong").

`/review-loop-change` checks a diff against all four mechanically before it ships. `testing-tools` checks new tests against the fourth (cited real data) specifically.
