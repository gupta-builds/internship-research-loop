# Internship Research Loop — PRD

**Status:** Verified against live repo/GitHub state on 2026-07-18 (git log, `pytest` [167/167], `gh run list`, `gh api`, live feed fetches — not assumed from memory). Still not independently product-reviewed; this was built spec-first in conversation, not PRD-first. Read this file alone for orientation — it does not require the Jarvis vault to make sense. For build history, decisions, and how each number below was verified, see `20_Progress/Internship/Building System/Phases 1-3 Run.md` in the Jarvis vault; it is not required reading to pick this project up, only to understand *why* it looks this way.

## Problem

Manually checking internship-listing repos/boards for new postings that match a specific eligibility window (class year, term, category, location, work authorization) is repetitive and easy to let slip. Postings also go stale fast — a manually-curated list rots, and a thin link-only list still forces a manual page visit to screen each posting.

## Goal

A 24/7 background process that watches known internship-listing sources, keeps only postings the user is actually eligible for under **three hard criteria** — timing (Summer 2027 or the Dec 2026–Jan 2027 winter window), location (US/Remote), and OPT eligibility (excluded only on an explicit citizenship/clearance/no-OPT signal) — and writes a live, deduplicated, dead-link-free, **content-carrying** list into the user's Obsidian vault (Jarvis), so screening happens in the vault without visiting posting pages by hand.

## User

Single user (repo owner) — a rising junior CS student, grad Spring 2028, F-1 student targeting Summer 2027 (or Dec 2026–Jan 2027) SWE/AI/data internships in the US. Not built as a multi-tenant product; `core/profile.yaml` is hardcoded to one person's eligibility.

## In Scope — Built (Phases 1–6, complete and live)

- Poll two internship-listing sources hourly (GitHub Actions cron); zapplyjobs was removed 2026-07-18 — its entries are program landing pages, not deadline-bearing postings
- Filter deterministically against the profile: term (incl. `Winter 2027` = Dec 2026–Feb 2027 per live term-adjacency evidence), category, class year, `active` status, `degrees` (Bachelor's), locations (US signal wins / foreign token loses / ambiguous passes), JGCL `season` cycle check
- Deduplicate two ways: persistent per-source uid seen-set, plus a punctuation-insensitive cross-source company+title key checked against the dossier files actually in the vault
- Five-check write gate (required fields, uid dedup, cross-source dedup, URL liveness, format compliance), fail-closed
- **OPT-eligibility gate at discovery:** each new validated match's posting page is fetched once (Firecrawl), checked per-posting for explicit exclusion signals (US-person/citizenship required, clearance required, OPT/CPT not accepted — EEO boilerplate and "no visa sponsorship" deliberately don't trigger), verdict cached in `state/opt_cache.json`
- **Content-carrying dossiers:** the same fetch fills a verbatim, trimmed "Posting" section (role, requirements, comp) in each dossier — no LLM anywhere; fail-open to a thin dossier if the fetch fails
- Daily post-write recheck (`recheck.yml`): removes dossiers whose posting went `active: false` or vanished upstream, with a mass-deletion brake and per-source fetch-failure isolation
- Push safely against the vault's own auto-commit cycle (pull-rebase + retry-once, never force-push)
- Halt, log, and file a GitHub issue on schema drift **or any source fetch failure** (network errors no longer crash unrecorded), push failure, or systemic write-gate rejection
- Log every run (`logs/runs.jsonl`, `logs/rechecks.jsonl`; weekly rollup into the vault fires Sundays 23:00 UTC)
- Promotion-triggered tools, outside the automated loop: `enrich.py` (Layer 5 company/contact research — public sources only; built, unit-tested, never yet run end-to-end) and `grade_resume.py` (Layer 6 keyword-overlap resume grader, verified against a real JD)

## Explicitly Out Of Scope

- Any login-walled scraping (LinkedIn, etc.), CAPTCHA bypass, or stealth browser automation — a hard non-goal, not a resourcing decision
- Any Claude/Anthropic LLM call in the automated path — Firecrawl fetches return page markdown; all extraction is mechanical line filtering
- Grad-year-requirement parsing ("must graduate in 2027") — found in real postings but left to the human screen of the now-present dossier content, not codified
- Tightening cadence below hourly — still gated on a week of clean runs (evaluable on/after 2026-07-24)

## Architecture (Summary)

Deterministic pipeline, no LLM calls anywhere in the loop:

```
ingestion (fetch + normalize) → filter (term/category/class/active/degrees/location/season)
  → dedup (uid) → write gate (5 mechanical checks) → posting fetch (Firecrawl, fail-open)
  → OPT check (per-posting, cached) → write content-carrying dossier → push (retry-safe)
  → mark seen (only after confirmed push) → log
daily: recheck (remove closed postings)     weekly: rollup into vault Run Log
```

Repo layout: `ingestion/` (`sources.py`, `normalize.py`, `posting_page.py`), `core/` (`filter.py`, `identity.py`, `profile.yaml`, `schema_drift.py`, `git_ops.py`, `run_log.py`), `vault_writer/` (template + `validate.py` + `writer.py`), `run_pipeline.py`, `recheck.py`, `enrich.py`, `grade_resume.py`, `tests/` (167 tests), `state/` (`seen_ids.json`, `opt_cache.json`), `logs/`, `.github/workflows/` (`run.yml` hourly, `recheck.yml` daily 06:30 UTC, `test.yml` on push).

## Current Status (verified 2026-07-18)

- `pytest`: **167/167 passing**; CI green on every push
- `run.yml`: firing on schedule and succeeding — 8/8 most recent scheduled runs successful (GitHub cron jitter skips some hours; that's platform behavior, not failures). `recheck.yml`: registered and active, **zero runs yet** — first scheduled opportunity 2026-07-19 06:30 UTC
- Vault dossiers: **20**, every one individually re-audited 2026-07-18 against all three criteria and carrying real posting content. `state/seen_ids.json` holds 137 — deliberately larger than the vault (117 uids belong to audited-out postings that must never be rewritten)
- Filter yield against live feeds at final config: SimplifyJobs 14,907 fetched → **36** match, JGCL 112 → **5** (was 103+17+22 before the phase 5–6 gates)
- `FIRECRAWL_API_KEY` present as an Actions secret (set 2026-07-18); first live discovery-time enriched write still pending a new upstream match
- Zero GitHub issues filed to date

## Success Metrics

1. **Run reliability** — fraction of triggered runs completing without crash/halt (`gh run list` × `runs.jsonl`). Fetch-failure crashes with no record are no longer possible (halt + log + issue since 2026-07-18).
2. **Write-gate outcome breakdown** — `written_count` vs `rejections` by check, now including `opt_eligibility`; summarized weekly by the rollup (first real firing: 2026-07-19 23:00 UTC).
3. **Dedup correctness** — no duplicate dossiers in the vault (uid + cross-source key); currently holding at 20/20 verified-unique.
4. **Vault hygiene** — the recheck should keep the vault free of closed postings within a day of upstream closure; measurable from `rechecks.jsonl` once it starts firing.

**Not measurable without new tracking:** applications submitted, response rate, time saved — downstream behavior lives in the vault's `Applying/` flow, unlinked to this system.

## Open Backlog

- Confirm the first real Sunday 23:00 UTC weekly rollup (opportunity: 2026-07-19; check `Run Log.md` Monday 2026-07-20)
- Confirm the first scheduled recheck run (2026-07-19 06:30 UTC) behaves against the post-audit vault
- Confirm the first live discovery-time enriched write (needs a new upstream match; the 7 Winter-2027 additions were unseen at push time and should exercise it within hours)
- Cadence decision on/after 2026-07-24
- Layer 5 `enrich.py` first live end-to-end run (key now exists; run it at the next real promotion)

## Risks

- **Fine-grained PAT (`JARVIS_PUSH_TOKEN`) expires or is revoked.** Fails the checkout step before Python runs — no run-log entry, no issue; only GitHub's failed-workflow email. Expiry date still recorded nowhere. *Unchanged, still the biggest silent-failure risk.*
- **Firecrawl dependency.** The discovery loop now calls a paid third-party API. Failure mode is deliberately soft (fail-open thin dossiers, no run failure), but quota exhaustion would silently degrade dossiers back to thin — watch `opt_cache.json` growth and Firecrawl usage; no in-repo monitoring exists.
- **GitHub Actions public-repo minutes policy changes.** Unchanged; no minutes monitoring.
- ~~Source repo goes offline → uncaught crash with no record~~ — **mitigated 2026-07-18**: any `requests` failure during drift-check/fetch now halts with a logged record and an auto-filed issue.

## Source Of Truth

This file is the standalone orientation document. `20_Progress/Internship/Building System/Phases 1-3 Run.md` in the Jarvis vault is the deeper record: build-by-build history, bugs found and fixed, audit evidence, and reasoning. If the two disagree on a fact, re-verify against live state — most-recently-verified wins, and the disagreement itself means one of them needs updating.
