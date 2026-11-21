# Architecture memory

Last deep-read: 2026-10-03. This is an orientation map, not a substitute for live code or Jarvis standards.

## System boundary

This repository is a single-user, deterministic internship-discovery service. GitHub Actions discovers and maintains dossier notes in the separate private Jarvis vault. Human judgment begins after discovery: screening, promotion, outreach, tailoring, applying, and outcomes remain consent-gated and evidence-only.

## Runtime flow

`ingestion/` fetches eleven source shapes and normalizes them to `Listing` objects. `core/schema_drift.py` preflights representative source schemas. `core/filter.py` applies eligibility gates; ambiguous or missing data passes and only explicit negative evidence rejects. `core/relevance.py` rejects clearly irrelevant titles and confirms adjacent roles from fetched content. `core/identity.py` owns source UID and cross-source identity. `core/debate.py` ranks candidates; `core/classify.py` assigns one dossier bucket.

`run_pipeline.py` orchestrates discovery, quotas, posting fetches, content/OPT checks, validation, dossier writes, Jarvis push, state advancement, logs, and notifications. `vault_writer/validate.py` owns the ordered five-check gate: required fields, UID duplicate, cross-source duplicate, URL liveness, format compliance. `vault_writer/writer.py` renders, scans, writes, and moves dossiers. A UID is marked seen only after a confirmed Jarvis push.

Maintenance paths:

- `recheck.py`: daily upstream liveness sweep; closed dossiers move to `Viewed/`, never delete.
- `revalidate.py`: weekly read-only application of current rules to stored dossier content; reports regressions by issue.
- `reseed.py`: manual, high-cost cold-start refill guarded by an exact confirmation input.
- `screen_report.py`: read-only per-bucket screening view.
- `enrich.py`, `grade_resume.py`: manual tools, outside unattended discovery.

## Persistence and external systems

- `state/`: seen IDs, posting-content/OPT cache, debate losses, exclusions, UID-to-path manifest, capacity notification state, InternDock guide state.
- `logs/`: append-only discovery and recheck JSONL history.
- Jarvis: dossier output plus downstream Program, Contact, Tracker, Applying, resume, and cover-letter artifacts.
- External services: source feeds/ATS APIs, Firecrawl, employer URLs, GitHub, and Google DNS-over-HTTPS.

GitHub Actions schedules discovery hourly, recheck daily at 06:30 UTC, revalidation Mondays at 08:00 UTC, and tests on push/PR; reseed is manual. Discovery/recheck/reseed write directly to Jarvis `master` and commit owned state/logs here. Pushes use pull-rebase and one retry, never force-push.

## Non-negotiable design rules

1. Zero LLM calls in unattended code.
2. Eligibility is permissive by default; explicit negative signals reject.
3. Preserve the write-gate order and first-failure behavior.
4. Every new deterministic rule cites dated real data beside the code.
5. Vault writes outside unattended dossier automation require explicit human consent and exact template compliance.
6. Durable Program facts stay separate from changing Tracker/Applying state.
7. Unsupported application claims are gaps, never inventions.

## Known engineering risk zones

- Cross-repository operations are not fully transactional: Jarvis files, local state, logs, and notifications can diverge after a failed push.
- Per-company ATS failures can be swallowed into a partial source result; recheck may interpret missing jobs as closed.
- URL liveness uses `HEAD`; repeated false failures can permanently exclude valid postings.
- Some unexpected JSON/filesystem/git failures bypass structured run logging.
- Tests do not fully pin every transition in the five-check validation order.
- Documentation and live Jarvis templates contain known drift; live code plus current standards/templates must be compared before changing contracts.

## Jarvis downstream model

The human pipeline is Find → Screen → Commit → Reach Out → Tailor → Deep Dive → Apply → Prep → Close. Promotion creates a Program, Contact, and Tracker together. Tracker maintenance occurs only on deadline change, tailoring start, submission, or outcome. Applying becomes the changing-state source of truth when tailoring starts. Document preparation is prepare → draft → plan → approve → humanize → write → link → apply.
