# Internship Research Loop — PRD

**Status:** Verified against live repo/GitHub/vault state on 2026-10-03 (`git log`, `pytest` [528 passing], `gh api` workflow list and run history, Jarvis repo commit history, direct vault folder listings — not assumed from memory). Sections not re-verified that day are marked with their own date. Still not independently product-reviewed; this was built spec-first in conversation, not PRD-first. Read this file alone for orientation — it does not require the Jarvis vault to make sense. For build history, decisions, and how each number below was verified, see `20_Progress/Internship/Building System/Phases 1-3 Run.md` (original build) and `System - Build Log.md` (ongoing) in the Jarvis vault; neither is required reading to pick this project up, only to understand *why* it looks this way.

## Problem

Manually checking internship-listing repos/boards for new postings that match a specific eligibility window (class year, term, category, location, work authorization) is repetitive and easy to let slip. Postings also go stale fast — a manually-curated list rots, and a thin link-only list still forces a manual page visit to screen each posting.

## Goal

A 24/7 background process that watches known internship-listing sources, keeps only postings the user is actually eligible for under **three hard criteria** — timing (Summer 2027 or the Dec 2026–Jan 2027 winter window), location (US/Remote), and OPT eligibility (excluded only on an explicit citizenship/clearance/no-OPT signal) — and writes a live, deduplicated, dead-link-free, **content-carrying** list into the user's Obsidian vault (Jarvis), so screening happens in the vault without visiting posting pages by hand.

## User

Single user (repo owner) — a rising junior CS student, grad Spring 2028, F-1 student targeting Summer 2027 (or Dec 2026–Jan 2027) SWE/AI/data internships in the US. Not built as a multi-tenant product; `core/profile.yaml` is hardcoded to one person's eligibility.

## In Scope — Built (Phases 1–6, complete and live)

- Poll eleven internship-listing sources hourly (GitHub Actions cron): SimplifyJobs, Jose-Gael-Cruz-Lopez, vanshb03, zshah101, ApplyGuy, Greenhouse, Ashby, Lever, Freehire, AIJobs, plus sitemap-detected InternDock. zapplyjobs was removed 2026-07-18 — its entries are program landing pages, not deadline-bearing postings
- Filter deterministically against the profile: term (incl. `Winter 2027` = Dec 2026–Feb 2027 per live term-adjacency evidence), category, class year, `active` status, `degrees` (Bachelor's), locations (US signal wins / foreign token loses / ambiguous passes), JGCL `season` cycle check
- Deduplicate two ways: persistent per-source uid seen-set, plus a punctuation-insensitive cross-source company+title key checked against the dossier files actually in the vault
- Five-check write gate (required fields, uid dedup, cross-source dedup, URL liveness, format compliance), fail-closed
- **OPT-eligibility gate at discovery:** each new validated match's posting page is fetched once (Firecrawl), checked per-posting for explicit exclusion signals (US-person/citizenship required, clearance required, OPT/CPT not accepted — EEO boilerplate and "no visa sponsorship" deliberately don't trigger), verdict cached in `state/opt_cache.json`
- **Content-carrying dossiers:** the same fetch fills a verbatim, trimmed "Posting" section (role, requirements, comp) in each dossier — no LLM anywhere; fail-open to a thin dossier if the fetch fails
- Daily post-write recheck (`recheck.yml`): moves dossiers whose posting went `active: false` or vanished upstream into `Dossiers/Viewed/` (never deletes), with a mass-move brake and per-source fetch-failure isolation. Covers 8 of the 11 sources — ApplyGuy, Freehire and InternDock dossiers are never rechecked (`recheck.py` `FEEDS`)
- **Write pacing (2026-09-07/08):** the hourly run writes an exact per-bucket quota (`QUOTA_PER_RUN` = 2 AI/ML + 1 Fullstack + 1 CyS & Finance + 2 Other, all-or-nothing), and disables its own workflow at 300 live dossiers (`HARD_PAUSE_TOTAL_THRESHOLD`) — a deliberate, human-decided reversal of the older notify-never-refuse rule for total volume only
- **Deadlines on every dossier (2026-10-03):** `deadline_posted` (the posting's own stated deadline, read from the fetched text by `ingestion/posting_page.py`'s `extract_deadline`) or, when none is stated, `own_deadline` = `date_found` + 7 days; exactly one is set, enforced by the write gate
- **Company registry:** `core/company_registry.py` holds the quant-firm bucket-override list and adjacent-field company list that `classify.py` and `relevance.py` share; the preference-tier rank (`debate.py`) is still a single grade
- Weekly `revalidate.yml` re-checks live dossiers against current rules and files one digest issue (moves nothing); manual `reseed.yml` does a one-off cold-start pull; `screen_report.py` prints a read-only ready-to-screen list
- Push safely against the vault's own auto-commit cycle (pull-rebase + retry-once, never force-push)
- Halt, log, and file a GitHub issue on schema drift **or any source fetch failure** (network errors no longer crash unrecorded), push failure, or systemic write-gate rejection
- Log every run (`logs/runs.jsonl`, `logs/rechecks.jsonl`; weekly rollup into the vault fires Sundays 23:00 UTC)
- Promotion-triggered tools, outside the automated loop: `enrich.py` (Layer 5 company/contact research — public sources only; built, unit-tested, never yet run end-to-end) and `grade_resume.py` (Layer 6 keyword-overlap resume grader, verified against a real JD; reads `$JARVIS_DIR/...Main Resume.md`, no longer a hardcoded path)

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

Repo layout: `ingestion/` (`sources.py`, `normalize.py`, `posting_page.py`), `core/` (`filter.py`, `identity.py`, `profile.yaml`, `schema_drift.py`, `git_ops.py`, `run_log.py`), `vault_writer/` (template + `validate.py` + `writer.py`), `run_pipeline.py`, `recheck.py`, `enrich.py`, `grade_resume.py`, `tests/` (528 tests), `state/` (`seen_ids.json`, `opt_cache.json`, `excluded_uids.json`, `debate_losses.json`, `write_gate_failures.json`, `dossier_uids.json`, ...), `logs/`, `.github/workflows/` (`run.yml` hourly, `recheck.yml` daily 06:30 UTC, `revalidate.yml` weekly, `reseed.yml` manual, `test.yml` on push/PR). Also `core/debate.py`, `core/classify.py`, `core/relevance.py`, `core/company_registry.py`, `core/company_cache.py` (not yet wired in), `reseed.py`, `revalidate.py`, `screen_report.py`. `.claude/`, `.cursor/`, `.agents/` and `.codex/` hold the agent/skill/hook layer described in `CLAUDE.md`.

## Current Status (verified 2026-10-03)

- `pytest`: **528 passing**; local `master` equals `origin/master`; PR #12 (two-laptop cleanup) merged 2026-09-26.
- **Scheduled automation is not observably running.** The Actions API lists `run`, `recheck`, `revalidate`, `reseed` and `test` as `active` but returns zero workflow runs for any of them (only one unrelated dependency-graph run exists repo-wide). Evidence of last real activity: `logs/runs.jsonl` ends 2026-08-29 09:34 UTC (687 lines; the human paused `run.yml` then — `disabled_manually`; the workflow's `updated_at` of 2026-09-22 suggests it was re-enabled that day, an inference, not a logged fact); the last bot commit in this repo is `Recheck log — 2026-09-20`; the last bot commit in the vault repo is `Move 1 closed posting(s) to Viewed/ — recheck 2026-09-17`. No scheduled run has left a trace since. Cause not determined (history deleted? cron not firing? expired `JARVIS_PUSH_TOKEN` failing the checkout step before any log line?). A `workflow_dispatch` would answer it but was deliberately not run.
- Vault dossiers (excluding `Viewed/`): **278** — AI/ML 130, Fullstack 41, CyS & Finance 48, Other 59 (the AI/ML figure is the parallel vault sweep's own count; the other three were counted directly from folder listings 2026-10-03), under the 300 hard-pause. Plus 67 in `Viewed/` and 11 in `_Career Fair/` (not counted toward the pause — `count_dossiers_by_bucket` only globs the four bucket folders).
- Promotion: `Programs/Serious/` and `Considering/` hold the 2026-08/09 batches; no live `Applying/` note exists, so Steps 4–9 of the vault's Internship Pipeline are still unexercised.
- **Open GitHub issues:** #4–8 (stale 2026-08-21 capacity notifications) and #9–11 (the same 15 dossiers flagged by `revalidate.yml` on 08-31, 09-07 and 09-14; six are Microsoft dossiers whose stored content predates the sidebar-extraction fix and cannot be re-extracted by `revalidate.py`).
- `FIRECRAWL_API_KEY` and `JARVIS_PUSH_TOKEN` exist as Actions secrets (created 2026-07-18 and 2026-07-17).

## Success Metrics

1. **Run reliability** — fraction of triggered runs completing without crash/halt (`gh run list` × `runs.jsonl`). Fetch-failure crashes with no record are no longer possible (halt + log + issue since 2026-07-18).
2. **Write-gate outcome breakdown** — `written_count` vs `rejections` by check, now including `opt_eligibility`; summarized weekly by the rollup (first real firing: 2026-07-19 23:00 UTC).
3. **Dedup correctness** — no duplicate dossiers in the vault (uid + cross-source key); currently holding at 20/20 verified-unique.
4. **Vault hygiene** — the recheck should keep the vault free of closed postings within a day of upstream closure; measurable from `rechecks.jsonl` once it starts firing.

**Not measurable without new tracking:** applications submitted, response rate, time saved — downstream behavior lives in the vault's `Applying/` flow, unlinked to this system.

## Open Backlog

- ~~Confirm the first real Sunday 23:00 UTC weekly rollup~~ — **done**: `Run Log.md` shows five weekly rollups firing continuously since 2026-07-19, most recently 2026-08-09 to 2026-08-16
- ~~Confirm the first scheduled recheck run behaves against the post-audit vault~~ — **done**: `recheck.yml` has run daily since, 10/10 most recent runs successful, now moving closed postings to `Viewed/` (2026-08-21)
- ~~Confirm the first live discovery-time enriched write~~ — **done**: all 391 current dossiers carry real fetched posting content
- Cadence decision on/after 2026-07-24 — still hourly, unchanged; over a month of clean runs since (20/20 recent success) makes this the settled default, though no explicit decision note exists
- Layer 5 `enrich.py` first live end-to-end run — **still unconfirmed**; the `/promote-dossier` skill and `contact-researcher` agent (built on `enrich.py`'s functions, see `CLAUDE.md`) have run live for the Appian promotion, but no direct evidence `enrich.py`'s own CLI has been run end-to-end was found this pass

## Risks

- **All-or-nothing quota and the debate-loss counter (found 2026-10-03, fixed 2026-10-04).** A short bucket pool used to charge every candidate a debate loss each run, excluding them permanently after `MAX_DEBATE_LOSSES` (48) runs with nothing written. `_select_exact_quota` now defers only real comparison losers; shortfall-held candidates are not charged.
- **Fixes reach new dossiers only.** The Microsoft sidebar fix, the quant-firm override, the denylist additions: none re-evaluates a dossier written before it landed. `revalidate.py` re-checks against *stored* content, so it can flag but not repair a stale-extraction dossier.
- **Fine-grained PAT (`JARVIS_PUSH_TOKEN`) expires or is revoked.** Fails the checkout step before Python runs — no run-log entry, no issue; only GitHub's failed-workflow email. Expiry date still recorded nowhere. *Unchanged, still the biggest silent-failure risk.*
- **Firecrawl dependency.** The discovery loop now calls a paid third-party API. Failure mode is deliberately soft (fail-open thin dossiers, no run failure), but quota exhaustion would silently degrade dossiers back to thin — watch `opt_cache.json` growth and Firecrawl usage; no in-repo monitoring exists.
- **Neither secret's expiry date is checkable programmatically.** GitHub deliberately doesn't expose a fine-grained PAT's expiry via `gh`/the API, and Firecrawl has no such API either — confirmed 2026-08-22, not assumed. This needs a one-time **manual** check by the human: `JARVIS_PUSH_TOKEN` at github.com/settings/tokens, `FIRECRAWL_API_KEY` on Firecrawl's own dashboard. Recorded here as a dated, visible gap rather than a silent one.
- **GitHub Actions public-repo minutes policy changes; usage still unmonitored.** Confirmed 2026-08-22: the billing/usage API (`/users/gupta-builds/settings/billing/actions`) returns 404 with this token's scopes (`gist`, `read:org`, `repo`, `workflow` — no `user` scope, which the endpoint requires); the org-billing variant also 404s since `gupta-builds` is a user account, not an org. Actual current minutes usage could not be verified with the available token — this risk stays noted as still-unmonitored, not guessed at.
- ~~Source repo goes offline → uncaught crash with no record~~ — **mitigated 2026-07-18**: any `requests` failure during drift-check/fetch now halts with a logged record and an auto-filed issue.

## Source Of Truth

This file is the standalone orientation document. `20_Progress/Internship/Building System/Phases 1-3 Run.md` in the Jarvis vault is the deeper record: build-by-build history, bugs found and fixed, audit evidence, and reasoning. If the two disagree on a fact, re-verify against live state — most-recently-verified wins, and the disagreement itself means one of them needs updating.
