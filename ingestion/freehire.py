"""freehire (github.com/strelov1/freehire) — a real, live, no-auth public API
aggregating 3.4M+ postings from 187,542+ companies across 78 ATS platforms,
including direct company crawls (Google, Uber) that no ATS-token approach can
ever reach. Verified live 2026-07-25 against three real ground-truth misses a
manual clipping audit surfaced: exact match found for Nuro's posting; exact
match found for Google's — freehire's own created_at (17:01:40Z) predates
SimplifyJobs' date_posted for the same posting (23:56:31Z) by ~7 hours, real
evidence it can be faster than the curated lists; Uber's exact req wasn't
found, but the same-titled "Career Prep" campaign was, under a different req
number, posted a few days earlier — a real but partial match, reported as
such rather than rounded up.

Scoped deliberately: NOT a crawl of the whole 3.4M-job dataset. Queried
per-company, for companies confirmed (this session, live) to have no
reachable Greenhouse/Ashby/Lever token — that's the value freehire adds over
the other 7 sources; querying it for companies we already reach directly
would just be redundant traffic against someone else's free API.

Reliability, checked before depending on it: no documented rate limit
anywhere (README, SECURITY.md, robots.txt all checked; robots.txt fully
permits crawling). Single-maintainer open-source project — real, but no SLA,
no committed uptime. fetch_freehire degrades the same way fetch_greenhouse/
fetch_ashby do: a failure on one company, or the whole API being down, is
caught and skipped there, never allowed to propagate and halt the run for
the other 7 sources.

freehire's own `closed_at` field is deliberately NOT used as our active
signal. Checked directly: the exact Google posting above is still
`closed_at: null` in freehire's data days after the real page confirmed it's
actually closed (fetched live — the page still returns HTTP 200, the body
now reads "closed"; a status-code-only check can't catch that either, and
neither can freehire's absence-from-feed, since the posting is still present
in a fresh company-scoped query). Every freehire-sourced Listing is marked
active=True unconditionally, same as Greenhouse/Ashby — url_liveness at
write time and the daily recheck are the real backstops, imperfect against
this specific "200 but the body says closed" failure mode, but that's a
pre-existing, shared limitation, not something freehire made worse. Because
that staleness is real, freehire is deliberately NOT wired into recheck.py's
FEEDS — "absent from freehire's feed" would not reliably mean "closed," so
recheck would offer false confidence there, not real coverage.
"""
import re

import requests

from ingestion.normalize import normalize_freehire

# seniority=intern is a real structured filter on freehire's search endpoint,
# not just a q= free-text guess — confirmed live 2026-07-25 after an early
# version of this fetcher (company_slug + limit=200, no seniority filter,
# client-side filtered) silently missed Google's own ground-truth posting: a
# company with thousands of total listings (Google: 3,842) doesn't return
# any intern-level jobs in its first 200 results by default order, so a
# fixed-limit unfiltered fetch can miss real matches at high-volume
# companies without ever erroring. Filtering server-side avoids that same
# failure class recurring at any other high-volume company on this list.
FREEHIRE_SEARCH_URL = "https://freehire.me/api/v1/jobs/search?company_slug={slug}&seniority=intern&limit=200"
FREEHIRE_COMPANY_URL = "https://freehire.me/api/v1/companies/{slug}"
TIMEOUT = 30

# Seed list, 2026-07-25: narrower than first built, on real evidence, not a
# guess. Every slug here was verified to have no reachable Greenhouse/Ashby/
# Lever token AND to have real job data on freehire — but Western Digital,
# Wells Fargo, and Grant Thornton were dropped after a live dry run: all
# three are ALREADY reachable directly via SimplifyJobs (confirmed — we have
# real dossiers from all three sourced that way), so freehire added zero
# unique coverage there, only noise. And it was real, measured noise: Wells
# Fargo alone contributed ~20 of 28 intern-tagged postings that were clearly
# non-tech by title (HR, Audit, Branch Manager Trainee, Wealth Management),
# and freehire's own `enrichment.category` field can't safely filter them —
# it's None on most postings (including genuinely-tech ones) and it
# mistagged an actual banking-analyst program as `data_analytics`. A title
# keyword denylist was considered and rejected: one of our own real,
# already-verified dossiers is Wells Fargo's "Corporate Risk Development
# Program Intern - Core Risk" — tagged `category: AI/ML/Data` by
# SimplifyJobs' own curators despite the generic "Risk" title. A keyword
# filter would have silently excluded a confirmed-good match, exactly the
# false-negative failure mode this whole project treats as worse than noise.
# Google and Uber stay: genuinely unreachable any other way, and their
# freehire results were on-topic without needing any extra filtering.
FREEHIRE_COMPANIES = {
    "google": "Google",
    "uber": "Uber",
}


def fetch_freehire(http_get=None) -> list:
    get = http_get or requests.get
    listings = []
    for slug, company in FREEHIRE_COMPANIES.items():
        try:
            resp = get(FREEHIRE_SEARCH_URL.format(slug=slug), timeout=TIMEOUT)
            resp.raise_for_status()
            jobs = resp.json().get("data", [])
        except requests.RequestException:
            continue
        for job in jobs:
            if (job.get("enrichment") or {}).get("seniority") == "intern":
                listings.append(normalize_freehire(job, company))
    return listings


def lookup_company_on_freehire(company_name: str, http_get=None) -> dict:
    """Checks freehire's own company mapping before ever guessing a token
    ourselves for the Greenhouse/Ashby watch-list — freehire's sources/*.yml
    already tracks 187K+ real, crawler-verified company-to-ATS-platform
    tokens, a much stronger source of truth than a blind slugify-and-test
    guess (which can resolve with zero jobs and look successful when it
    isn't — "optiver" does exactly that; the real token is "optiverus").

    Returns freehire's company record (job_count, etc.) if found under the
    guessed slug, or {} if not found or the lookup itself failed. This is
    the cheap first check, not the last word — a real company can still be
    indexed under a slug this simple slugify doesn't happen to guess.

    NOTE: this is the lookup primitive only. Wiring it into an automatic
    "every run, check every newly-seen company" loop is a separate step,
    not built here — that needs its own persisted state (a seen-companies
    set, distinct from seen_ids.json, which is per-posting) and its own
    cadence decision, the same way recheck.py earned a separate daily cron
    instead of running inside the hourly discovery loop.
    """
    get = http_get or requests.get
    slug = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
    try:
        resp = get(FREEHIRE_COMPANY_URL.format(slug=slug), timeout=TIMEOUT)
    except requests.RequestException:
        return {}
    if resp.status_code != 200:
        return {}
    return resp.json().get("data", {}).get("company", {})
