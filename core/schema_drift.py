"""Schema-drift check. Runs before the scheduled pipeline touches feeds for
real: fetches one real entry per source and confirms the fields the
normalizers actually depend on are still present. Halts (raises) rather than
letting a silently renamed/vanished upstream field produce malformed or
emptied-out results.
"""
import requests

from ingestion.sources import APPLYGUY_URL, JOSEGAEL_URL, SIMPLIFY_URL, TIMEOUT, VANSHB03_URL, ZSHAH101_URL

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

# Only the two curated single-feed JSON sources get a pre-fetch drift check,
# same as SimplifyJobs/JGCL always have. Greenhouse/Ashby/Lever are a dozen
# per-company endpoints, not one feed — checking each company's schema before
# every run would multiply request volume for a company set that already
# degrades gracefully per-token in fetch_greenhouse/fetch_ashby/fetch_lever (a
# renamed board silently returns nothing for that one company, not malformed
# data).


class SchemaDriftError(Exception):
    pass


def _check_json_source(name: str, url: str, required_keys: set, http_get, *, is_dict: bool = False) -> None:
    resp = http_get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if is_dict:
        if not isinstance(data, dict) or not data:
            raise SchemaDriftError(f"{name}: expected a non-empty JSON object, got {type(data).__name__}")
        first_entry = next(iter(data.values()))
    else:
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


def check_all(http_get=None) -> None:
    """Runs every check in order; raises SchemaDriftError from whichever
    fails first. Callers should treat any exception here as "halt the run,
    write nothing" per the plan's fail-closed design."""
    check_simplify_schema(http_get)
    check_josegael_schema(http_get)
    check_vanshb03_schema(http_get)
    check_zshah101_schema(http_get)
    check_applyguy_schema(http_get)
