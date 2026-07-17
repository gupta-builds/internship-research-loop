# internship-research-loop

24/7 internship discovery automation — polls SimplifyJobs, Jose-Gael-Cruz-Lopez, and
zapplyjobs, filters against a profile, dedups, and writes dossiers into an Obsidian
vault through a validated template + four-check write gate.

Full spec lives in the Jarvis vault: `Internship/Building System/Research Loop —
Implementation Plan.md`.

## Status

Phase 1 (ingestion + filter + identity), phase 2 (vault_writer's template +
four-check write gate, tested against a throwaway vault), and phase 3's code
(schema-drift check, git push-with-retry, two-tier run log, run_pipeline.py
orchestration) are built and tested. `.github/workflows/run.yml` — the
scheduled trigger that actually writes into `gupta-builds/Jarvis` — is held
back from the default branch until `JARVIS_PUSH_TOKEN` (a fine-grained PAT
scoped to that repo, `contents:write` only) exists as a repo secret, since
pushing the workflow activates its hourly cron immediately.

## Local dev

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -v
```
