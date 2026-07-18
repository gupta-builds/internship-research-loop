"""Schema-drift check. Runs before the scheduled pipeline touches feeds for
real: fetches one real entry per source and confirms the fields the
normalizers actually depend on are still present. Halts (raises) rather than
letting a silently renamed/vanished upstream field produce malformed or
emptied-out results.
"""
import requests

from ingestion.sources import JOSEGAEL_URL, SIMPLIFY_URL, TIMEOUT

# Every field normalize_simplify/normalize_josegael read, not just the ones
# that would KeyError — a renamed "category" wouldn't crash (normalize_*
# falls back to .get(..., "")), it would just silently reject everything in
# the filter layer forever, which is exactly the drift this check exists for.
# "active"/"degrees"/"season" are load-bearing the other way around: renamed,
# they'd silently make every listing pass those checks (permissive defaults).
SIMPLIFY_REQUIRED_KEYS = {"id", "company_name", "title", "url", "category", "terms", "locations", "date_posted", "active", "degrees"}
JOSEGAEL_REQUIRED_KEYS = {"id", "company_name", "title", "url", "category", "locations", "target_year", "date_posted", "active", "season"}


class SchemaDriftError(Exception):
    pass


def _check_json_source(name: str, url: str, required_keys: set, http_get) -> None:
    resp = http_get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list) or not data:
        raise SchemaDriftError(f"{name}: expected a non-empty JSON list, got {type(data).__name__}")
    missing = required_keys - set(data[0].keys())
    if missing:
        raise SchemaDriftError(
            f"{name}: missing expected keys {sorted(missing)} (entry keys: {sorted(data[0].keys())})"
        )


def check_simplify_schema(http_get=None) -> None:
    _check_json_source("SimplifyJobs", SIMPLIFY_URL, SIMPLIFY_REQUIRED_KEYS, http_get or requests.get)


def check_josegael_schema(http_get=None) -> None:
    _check_json_source("Jose-Gael-Cruz-Lopez", JOSEGAEL_URL, JOSEGAEL_REQUIRED_KEYS, http_get or requests.get)


def check_all(http_get=None) -> None:
    """Runs both checks in order; raises SchemaDriftError from whichever
    fails first. Callers should treat any exception here as "halt the run,
    write nothing" per the plan's fail-closed design."""
    check_simplify_schema(http_get)
    check_josegael_schema(http_get)
