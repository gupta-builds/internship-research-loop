"""On-demand company-enrichment cache — sits alongside enrich.py (Layer 5,
manual-CLI, never called from run_pipeline.py's unattended path), not wired
into it yet. Standalone module only, per this session's own scope: no
`.claude/` skill, no wiring into the researching-companies skill or enrich.py's actual
call flow — that's `.claude/` work, deferred until it resumes.

Mirrors enrich.py's own real field shape verbatim (its main() computes
site_url, about, blog_url, a GitHub org + members, mx, and contacts turned
into {name, source, inferred_email, mx_ok} rows) so a future caller can
round-trip a cache hit straight into the same shape enrich.py already
produces, without reshaping anything.

A cache hit is a lead to build on, never a substitute for re-confirming a
claim before it lands in a real Contact note — same rule
.claude/skills/researching-companies/SKILL.md states for live research: a wrong
guess here is worse than an empty result, never infer a plausible name, and
if nothing real turns up, say so. A cached "nothing found" is still saying
so honestly; a cache hit is not itself grounds to skip re-confirming a
contact before writing it into a real note.

First per-key (per-company) cache directory in this codebase — every
existing state/*.json file (seen_ids, opt_cache, debate_losses,
excluded_uids, dossier_uids, interndock_seen_guides, capacity_notified) is
one flat file holding every key. This is one file per company, under
state/company_cache/<normalized-name>.json, keyed through
core.identity._norm_company (the same normalization already used for
company matching elsewhere) so "Optiver" and "OPTIVER" share one file
instead of silently duplicating.
"""
import json
from datetime import date
from pathlib import Path

from core.identity import _norm_company

CACHE_DIR = Path("state/company_cache")
DEFAULT_TTL_DAYS = 30


def _cache_path(company: str, cache_dir=CACHE_DIR) -> Path:
    return Path(cache_dir) / f"{_norm_company(company)}.json"


def is_expired(checked_date: str, ttl_days: int = DEFAULT_TTL_DAYS) -> bool:
    """Pure — no filesystem. `checked_date` is an ISO date string (as `save()`
    stamps it); anything unparseable counts as expired (fail toward a fresh
    re-check, not a stale cache hit)."""
    try:
        checked = date.fromisoformat(checked_date)
    except (TypeError, ValueError):
        return True
    return (date.today() - checked).days > ttl_days


def load(company: str, ttl_days: int = DEFAULT_TTL_DAYS, cache_dir=CACHE_DIR) -> dict | None:
    """None on: no cache file, corrupt/malformed JSON, or an entry older than
    `ttl_days` — a broken or stale cache entry must look like a plain cache
    miss to the caller, never raise. A cache hit is a lead to re-confirm, not
    an already-verified fact — see this module's own docstring."""
    path = _cache_path(company, cache_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    if not isinstance(data, dict) or "checked" not in data:
        return None
    if is_expired(data["checked"], ttl_days):
        return None
    return data


def save(company: str, data: dict, cache_dir=CACHE_DIR) -> None:
    """Stamps `checked` to today and writes `company` as the given display
    name (not the normalized filename key) — both always reflect this call,
    regardless of what `data` already carried, so the two stay trustworthy
    even if a caller passes a stale dict back in."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {**data, "company": company, "checked": date.today().isoformat()}
    _cache_path(company, cache_dir).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def demo():
    """Runnable self-check: a real write -> read -> simulated-expiry cycle,
    against a throwaway temp directory (never the real state/company_cache/)."""
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="company_cache_demo_"))
    try:
        company = "Optiver"
        enrichment = {
            "site_url": "https://www.optiver.com",
            "about": "Optiver is a leading technology- and research-driven trading firm.",
            "blog_url": "",
            "github_org": None,
            "github_members": [],
            "mx_valid": True,
            "contacts": [
                {"name": "Jane Recruiter", "source": "university recruiting search: https://example.test/1",
                 "inferred_email": "jane.recruiter@optiver.com", "mx_ok": True},
            ],
            "sources": ["https://www.optiver.com"],
        }

        print(f"1. save({company!r}, ...) -> {tmp / 'optiver.json'}")
        save(company, enrichment, cache_dir=tmp)

        loaded = load(company, cache_dir=tmp)
        print(f"2. load({company!r}) -> checked={loaded['checked']!r}, "
              f"{len(loaded['contacts'])} contact(s), site_url={loaded['site_url']!r}")
        assert loaded is not None and loaded["site_url"] == enrichment["site_url"]

        stale_checked = "2000-01-01"
        print(f"3. is_expired({stale_checked!r}, ttl_days=30) -> {is_expired(stale_checked, 30)}")
        assert is_expired(stale_checked, 30) is True

        # simulate the same file having gone stale (no wall-clock wait needed)
        raw = json.loads((tmp / "optiver.json").read_text())
        raw["checked"] = stale_checked
        (tmp / "optiver.json").write_text(json.dumps(raw))
        print(f"4. load({company!r}) after backdating 'checked' to {stale_checked!r} -> "
              f"{load(company, cache_dir=tmp)!r} (must be None: expired looks like a miss)")
        assert load(company, cache_dir=tmp) is None

        (tmp / "optiver.json").write_text("{not valid json")
        print(f"5. load({company!r}) against a hand-corrupted file -> "
              f"{load(company, cache_dir=tmp)!r} (must be None, not raise)")
        assert load(company, cache_dir=tmp) is None

        print("demo: all steps passed.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    demo()
