# internship-research-loop

24/7 internship discovery automation — polls SimplifyJobs, Jose-Gael-Cruz-Lopez, and
zapplyjobs, filters against a profile, dedups, and writes dossiers into an Obsidian
vault through a validated template + four-check write gate.

Full spec lives in the Jarvis vault: `Internship/Building System/Research Loop —
Implementation Plan.md`.

## Status

Phase 1 (ingestion + filter + identity, tested against fixtures) and phase 2
(vault_writer's template + four-check write gate, tested against a throwaway
vault) complete. Phase 3 (wired to the real vault via a scheduled GitHub Actions
run) not started — see Build Order in the spec.

## Local dev

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -v
```
