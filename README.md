# internship-research-loop

24/7 internship discovery automation — polls SimplifyJobs, Jose-Gael-Cruz-Lopez, and
zapplyjobs, filters against a profile, dedups, and writes dossiers into an Obsidian
vault through a validated template + four-check write gate.

Full spec lives in the Jarvis vault: `Internship/Building System/Research Loop —
Implementation Plan.md`.

## Status

Phase 1 (ingestion + filter + identity, tested against fixtures) complete.
Phase 2 (vault_writer, throwaway vault) and phase 3 (wired to the real vault) not
started yet — see Build Order in the spec.

## Local dev

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -v
```
