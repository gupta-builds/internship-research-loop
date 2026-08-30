"""Schema-drift check. Runs before the scheduled pipeline touches feeds for
real: fetches one real entry per source and confirms the fields the
normalizers actually depend on are still present. Halts (raises) rather than
letting a silently renamed/vanished upstream field produce malformed or
emptied-out results.
"""
import re

import requests

from ingestion.freehire import FREEHIRE_SEARCH_URL
from ingestion.interndock import CANDIDATE_SLUG_RE, INTERNDOCK_SITEMAP_URL
from ingestion.sources import (
    AI_JOBS_URL,
    APPLYGUY_URL,
    ASHBY_JOBS_URL,
    GREENHOUSE_JOBS_URL,
    JOSEGAEL_URL,
    LEVER_JOBS_URL,
    SIMPLIFY_URL,
    TIMEOUT,
    VANSHB03_URL,
    ZSHAH101_URL,
)

# Every field normalize_simplify/normalize_josegael read, not just the ones
# that would KeyError — a renamed "category" wouldn't crash (normalize_*
# falls back to .get(..., "")), it would just silently reject everything in
# the filter layer forever, which is exactly the drift this check exists for.
# "active"/"degrees"/"season" are load-bearing the other way around: renamed,
# they'd silently make every listing pass those checks (permissive defaults).
SIMPLIFY_REQUIRED_KEYS = {"id", "company_name", "title", "url", "category", "terms", "locations", "date_posted", "active", "degrees"}
JOSEGAEL_REQUIRED_KEYS = {"id", "company_name", "title", "url", "category", "locations", "target_year", "date_posted", "active", "season"}
VANSHB03_REQUIRED_KEYS = {"id", "company_name", "title", "url", "locations", "date_posted", "active", "season", "sponsorship"}
ZSHAH101_REQUIRED_KEYS = {"id", "company", "title", "url", "location", "posted_at", "is_open", "season", "sponsorship", "category"}
# "url" isn't in this set even though normalize_applyguy reads it — it's only
# a fallback (raw.get("listingUrl") or raw["url"]), so a renamed "url" alone
# wouldn't KeyError or silently degrade anything; "listingUrl" is the one
# that's load-bearing (every real entry checked 2026-08-24 has it).
APPLYGUY_REQUIRED_KEYS = {"id", "company", "title", "listingUrl", "category", "season", "location", "posted"}

# Greenhouse/Ashby/Lever are a dozen per-company endpoints, not one feed —
# checking every company's schema before every run would multiply request
# volume for a company set that already degrades gracefully per-token in
# fetch_greenhouse/fetch_ashby/fetch_lever (a renamed/closed board silently
# returns nothing for that one company, not malformed data — and the
# per-source zero-match-rate alert in run_pipeline.py catches that
# operationally). But a vendor-wide API shape change — Ashby renaming
# "employmentType", Greenhouse renaming "absolute_url" — hits every company
# on that vendor at once, and none of the three fetchers would notice: they
# all fail open (try/except RequestException, or a KeyError from
# normalize_ashby/normalize_greenhouse/normalize_lever would actually crash
# the whole run instead, worse than the silent-zero case the docstring above
# describes). So each of the three checks ONE real, high-volume, currently-
# live company (confirmed live 2026-08-28 against the real API — see the
# _SCHEMA_CHECK_TOKEN comments below) — enough to catch a vendor-wide drift,
# without the per-company request multiplication that was ruled out above.
#
# InternDock is different in kind, not just degree: it has no JSON API to
# schema-check at all. fetch_interndock_drop_candidates() only ever touches
# interndock.com/sitemap.xml (plain XML, checked below — that part IS
# checkable for free). The actual posting shape (POSTING_LINE_RE) only shows
# up after a paid Firecrawl fetch of one specific guide page, and there's no
# guarantee any given sitemap URL is currently a real drop (see
# ingestion/interndock.py's own docstring on "summer-2027-internship-
# programs-open-now" reading exactly like a drop by name while being a
# zero-posting prose article) — spending a Firecrawl call here to pre-flight
# a schema, and maybe hitting a non-drop page and calling that "healthy" or a
# real drop and calling a slug mismatch "drift", wouldn't mean anything
# reliable. check_interndock_sitemap below checks what's actually checkable.

# High-volume, currently-live tokens (2026-08-28) — see the block comment
# above for why one company per vendor is the right amount of pre-flight
# checking here, not a stand-in for "this specific company matters more."
GREENHOUSE_SCHEMA_CHECK_TOKEN = "scaleai"  # 219 open reqs live 2026-08-28
ASHBY_SCHEMA_CHECK_TOKEN = "elevenlabs"  # 249 open reqs live 2026-08-28
LEVER_SCHEMA_CHECK_TOKEN = "palantir"  # 307 open reqs live 2026-08-28, longest-tracked of the 4
FREEHIRE_SCHEMA_CHECK_SLUG = "google"  # of the 2 tracked companies, the higher-volume one

# Confirmed live 2026-08-28 against https://boards-api.greenhouse.io/v1/boards/scaleai/jobs
# (no ?content=true query param on GREENHOUSE_JOBS_URL, so "content" never
# appears in this response shape at all — not a required key here even
# though normalize_greenhouse also reads raw.get("content", "")).
GREENHOUSE_REQUIRED_KEYS = {"id", "title", "absolute_url", "location", "updated_at"}
# Confirmed live 2026-08-28 against https://api.ashbyhq.com/posting-api/job-board/elevenlabs .
# employmentType is the field fetch_ashby's own role-type triage reads
# (job.get("employmentType") == "Intern") — renamed, every company silently
# stops matching any intern posting at all, the exact failure shape this
# check exists to catch (see the 2026-08-21..08-28 Ashby zero-match
# investigation, Prompt 19 Task 1).
ASHBY_REQUIRED_KEYS = {"id", "title", "jobUrl", "location", "isListed", "publishedAt", "descriptionPlain", "employmentType"}
# Confirmed live 2026-08-28 against https://api.lever.co/v0/postings/palantir?mode=json .
# "text" is also what fetch_lever's own role-type triage reads
# (job.get("text", "").lower()) — same reasoning as Ashby's employmentType
# above. applyUrl, not hostedUrl, per normalize_lever's own docstring on
# which one is the real employer link.
LEVER_REQUIRED_KEYS = {"id", "text", "applyUrl", "categories", "createdAt", "descriptionPlain"}
# Confirmed live 2026-08-28 against
# https://freehire.me/api/v1/jobs/search?company_slug=google&seniority=intern&limit=200 .
# "enrichment" additionally must contain "seniority" — see
# check_freehire_schema below; that nested field is what fetch_freehire's own
# role-type triage reads.
FREEHIRE_REQUIRED_KEYS = {"title", "url", "location", "posted_at", "public_slug", "description", "enrichment"}
# Confirmed live 2026-08-28 against https://artificialintelligencejobs.co/jobs.json .
# "level" is what fetch_ai_jobs' own role-type triage reads (raw.get("level") == "Intern").
AI_JOBS_REQUIRED_KEYS = {"title", "url", "company", "location", "posted", "slug", "level"}

# sitemap.xml's real shape, confirmed live 2026-08-28: 68 total <loc> entries,
# 43 under /tracker/guides/, 12 of those matching CANDIDATE_SLUG_RE — the
# same loose pre-filter fetch_interndock_drop_candidates() itself uses.
_LOC_RE = re.compile(r"<loc>([^<]*)</loc>")


class SchemaDriftError(Exception):
    pass


def _check_json_source(name: str, url: str, required_keys: set, http_get, *, is_dict: bool = False, allow_empty: bool = False) -> None:
    resp = http_get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if is_dict:
        if allow_empty and isinstance(data, dict) and not data:
            return  # nothing to check field shapes against — not itself a drift signal, see allow_empty callers
        if not isinstance(data, dict) or not data:
            raise SchemaDriftError(f"{name}: expected a non-empty JSON object, got {type(data).__name__}")
        first_entry = next(iter(data.values()))
    else:
        if allow_empty and isinstance(data, list) and not data:
            return
        if not isinstance(data, list) or not data:
            raise SchemaDriftError(f"{name}: expected a non-empty JSON list, got {type(data).__name__}")
        first_entry = data[0]
    missing = required_keys - set(first_entry.keys())
    if missing:
        raise SchemaDriftError(
            f"{name}: missing expected keys {sorted(missing)} (entry keys: {sorted(first_entry.keys())})"
        )


def check_simplify_schema(http_get=None) -> None:
    _check_json_source("SimplifyJobs", SIMPLIFY_URL, SIMPLIFY_REQUIRED_KEYS, http_get or requests.get)


def check_josegael_schema(http_get=None) -> None:
    _check_json_source("Jose-Gael-Cruz-Lopez", JOSEGAEL_URL, JOSEGAEL_REQUIRED_KEYS, http_get or requests.get)


def check_vanshb03_schema(http_get=None) -> None:
    _check_json_source("vanshb03", VANSHB03_URL, VANSHB03_REQUIRED_KEYS, http_get or requests.get)


def check_zshah101_schema(http_get=None) -> None:
    _check_json_source("zshah101", ZSHAH101_URL, ZSHAH101_REQUIRED_KEYS, http_get or requests.get, is_dict=True)


def check_applyguy_schema(http_get=None) -> None:
    # A third real shape, neither of _check_json_source's two: a dict wrapping
    # a "jobs" list ({"updatedAt": ..., "jobs": [...]}), not a bare list
    # (SimplifyJobs/JGCL/vanshb03) or a dict keyed by posting id (zshah101) —
    # not worth generalizing the shared helper for one shape, same "small
    # dedicated function beats a bent-to-fit shared one" call as elsewhere in
    # this codebase.
    resp = (http_get or requests.get)(APPLYGUY_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list) or not jobs:
        raise SchemaDriftError(f"ApplyGuy: expected a non-empty 'jobs' list, got {type(data).__name__}")
    missing = APPLYGUY_REQUIRED_KEYS - set(jobs[0].keys())
    if missing:
        raise SchemaDriftError(f"ApplyGuy: missing expected keys {sorted(missing)} (entry keys: {sorted(jobs[0].keys())})")


def _check_wrapped_jobs_source(name: str, url: str, required_keys: set, http_get, *, allow_empty: bool = False) -> None:
    """Greenhouse/Ashby/AIJobs' shared shape: a dict wrapping a "jobs" list —
    same shape check_applyguy_schema already handles bespoke, now shared
    since three more sources use it."""
    resp = http_get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if allow_empty and isinstance(jobs, list) and not jobs:
        return  # nothing to check field shapes against — not itself a drift signal, see allow_empty callers
    if not isinstance(jobs, list) or not jobs:
        raise SchemaDriftError(f"{name}: expected a non-empty 'jobs' list, got {type(data).__name__}")
    missing = required_keys - set(jobs[0].keys())
    if missing:
        raise SchemaDriftError(f"{name}: missing expected keys {sorted(missing)} (entry keys: {sorted(jobs[0].keys())})")


# allow_empty=True on Greenhouse/Ashby/Lever/Freehire (unlike AIJobs below):
# each of these checks ONE specific company/slug, and that one company
# legitimately having zero open reqs right now (a hiring pause, between
# postings) is mundane and unrelated to the vendor's API shape — it's
# exactly the same "company-level absence is not drift" reasoning the block
# comment above already applies to fetch_greenhouse/fetch_ashby/fetch_lever
# themselves. Treating an empty response here as SchemaDriftError would
# halt the entire run (all 10 sources) over one company's temporary hiring
# lull — a real, plausible failure mode this check must not introduce.
# AIJobs, by contrast, aggregates postings across the whole feed; a
# genuinely empty AIJobs response IS as suspicious as SimplifyJobs' own
# feed going empty, so it keeps the default allow_empty=False.
def check_greenhouse_schema(http_get=None) -> None:
    _check_wrapped_jobs_source(
        "Greenhouse", GREENHOUSE_JOBS_URL.format(token=GREENHOUSE_SCHEMA_CHECK_TOKEN),
        GREENHOUSE_REQUIRED_KEYS, http_get or requests.get, allow_empty=True,
    )


def check_ashby_schema(http_get=None) -> None:
    _check_wrapped_jobs_source(
        "Ashby", ASHBY_JOBS_URL.format(token=ASHBY_SCHEMA_CHECK_TOKEN),
        ASHBY_REQUIRED_KEYS, http_get or requests.get, allow_empty=True,
    )


def check_lever_schema(http_get=None) -> None:
    # Lever's own shape is a bare list (mode=json), not a "jobs"-wrapped dict —
    # same shape as Simplify/JGCL/vanshb03, reuse that helper instead.
    _check_json_source(
        "Lever", LEVER_JOBS_URL.format(token=LEVER_SCHEMA_CHECK_TOKEN),
        LEVER_REQUIRED_KEYS, http_get or requests.get, allow_empty=True,
    )


def check_freehire_schema(http_get=None) -> None:
    # A fourth real shape: {"data": [...]}, plus a nested field
    # (enrichment.seniority) that's load-bearing for fetch_freehire's own
    # role-type triage — not caught by a flat top-level key check alone, so
    # this one stays a dedicated function rather than folding into
    # _check_json_source or _check_wrapped_jobs_source. allow_empty reasoning
    # as above: one company (google), zero current intern-tagged postings
    # there isn't drift.
    resp = (http_get or requests.get)(FREEHIRE_SEARCH_URL.format(slug=FREEHIRE_SCHEMA_CHECK_SLUG), timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    jobs = data.get("data") if isinstance(data, dict) else None
    if isinstance(jobs, list) and not jobs:
        return
    if not isinstance(jobs, list) or not jobs:
        raise SchemaDriftError(f"Freehire: expected a non-empty 'data' list, got {type(data).__name__}")
    first_entry = jobs[0]
    missing = FREEHIRE_REQUIRED_KEYS - set(first_entry.keys())
    if missing:
        raise SchemaDriftError(f"Freehire: missing expected keys {sorted(missing)} (entry keys: {sorted(first_entry.keys())})")
    if "seniority" not in (first_entry.get("enrichment") or {}):
        raise SchemaDriftError("Freehire: 'enrichment' entry missing expected key 'seniority'")


def check_ai_jobs_schema(http_get=None) -> None:
    _check_wrapped_jobs_source("AIJobs", AI_JOBS_URL, AI_JOBS_REQUIRED_KEYS, http_get or requests.get)


def check_interndock_sitemap(http_get=None) -> None:
    """Not a field-schema check (InternDock has no JSON API — see the block
    comment above) — confirms interndock.com/sitemap.xml itself still parses
    as XML with <loc> entries and that at least one still looks drop-shaped
    per CANDIDATE_SLUG_RE, the same loose pre-filter
    fetch_interndock_drop_candidates() applies to real results."""
    resp = (http_get or requests.get)(INTERNDOCK_SITEMAP_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    locs = _LOC_RE.findall(resp.text)
    if not locs:
        raise SchemaDriftError("InternDock: sitemap.xml has no <loc> entries — feed shape changed or sitemap is empty")
    if not any(CANDIDATE_SLUG_RE.search(u) for u in locs):
        raise SchemaDriftError(
            f"InternDock: sitemap.xml has {len(locs)} <loc> entries but none match the drop-shaped slug pattern"
        )


def check_all(http_get=None) -> None:
    """Runs every check in order; raises SchemaDriftError from whichever
    fails first. Callers should treat any exception here as "halt the run,
    write nothing" per the plan's fail-closed design."""
    check_simplify_schema(http_get)
    check_josegael_schema(http_get)
    check_vanshb03_schema(http_get)
    check_zshah101_schema(http_get)
    check_applyguy_schema(http_get)
    check_greenhouse_schema(http_get)
    check_ashby_schema(http_get)
    check_lever_schema(http_get)
    check_freehire_schema(http_get)
    check_ai_jobs_schema(http_get)
    check_interndock_sitemap(http_get)
