# internship-research-loop

24/7 internship discovery automation — polls SimplifyJobs and Jose-Gael-Cruz-Lopez,
filters against a profile, dedups (per-source uid + cross-source company+title), and
writes dossiers into an Obsidian vault through a validated template + five-check
write gate. A daily recheck (`recheck.yml`) removes dossiers whose postings close
upstream. (zapplyjobs was dropped as a source 2026-07-18 — its entries are program
landing pages, not deadline-bearing postings.)

Full spec lives in the Jarvis vault: `Internship/Building System/Research Loop —
Implementation Plan.md`.

## Status

Phases 1–3 are live. `.github/workflows/run.yml` runs hourly against the real
`gupta-builds/Jarvis` repo — schema-drift check, fetch, filter, dedup,
validate, write, push (retry-safe against the vault's own independent
auto-commit cycle), with `state/seen_ids.json` only updated after a confirmed
push. First live run (2026-07-17) wrote 137 real dossiers into
`10_Areas/Career/Internships/List/Dossiers/`; a follow-up run correctly
recognized all 137 as already-seen and wrote zero duplicates. Per the plan's
build order: watch the Run Log rollup for a full week before tightening the
cadence past hourly.

## Local dev

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -v
```
