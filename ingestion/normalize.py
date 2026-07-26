"""Map each source's raw shape to one internal Listing dataclass."""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Listing:
    company: str
    title: str
    url: str
    source: str  # SimplifyJobs | Jose-Gael-Cruz-Lopez | vanshb03 | zshah101 | Greenhouse | Ashby
    category: str = ""
    terms: list = field(default_factory=list)
    locations: list = field(default_factory=list)
    target_year: list = field(default_factory=list)
    degrees: list = field(default_factory=list)
    active: Optional[bool] = None  # None = source didn't say; only explicit False rejects
    date_posted: Optional[int] = None
    raw_id: Optional[str] = None  # stable upstream id, present on every source
    sponsorship: str = ""  # first-party OPT-adjacent signal, only vanshb03/zshah101 carry this
    raw_text: str = ""  # free text for sources with no structured term field (Greenhouse/Ashby)


def _parse_iso_ts(s: str) -> Optional[int]:
    if not s:
        return None
    try:
        return int(datetime.fromisoformat(s).timestamp())
    except ValueError:
        return None


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    return _TAG_RE.sub(" ", html or "")


def normalize_simplify(raw: dict) -> Listing:
    return Listing(
        company=raw["company_name"],
        title=raw["title"],
        url=raw["url"],
        source="SimplifyJobs",
        category=raw.get("category", ""),
        terms=raw.get("terms", []),
        locations=raw.get("locations", []),
        degrees=raw.get("degrees", []),
        active=raw.get("active"),
        date_posted=raw.get("date_posted"),
        raw_id=raw["id"],
    )


def normalize_josegael(raw: dict) -> Listing:
    # JGCL has no `terms` field; its cycle signal is `season` — mostly year-less
    # ("Summer", "Multiple", rarely "Summer 2026"). Mapped into terms so the
    # filter can reject affirmatively-wrong cycles; leaving it unmapped is what
    # let wrong-cycle listings through until the 2026-07-18 vault audit.
    season = raw.get("season", "")
    return Listing(
        company=raw["company_name"],
        title=raw["title"],
        url=raw["url"],
        source="Jose-Gael-Cruz-Lopez",
        category=raw.get("category", ""),
        terms=[season] if season else [],
        locations=raw.get("locations", []),
        target_year=raw.get("target_year", []),
        active=raw.get("active"),
        date_posted=raw.get("date_posted"),
        raw_id=raw["id"],
    )


def normalize_vanshb03(raw: dict) -> Listing:
    # Same shape as JGCL: no `terms` array, a bare year-less `season` string
    # instead ("Summer"/"Fall"/"Winter"/"Spring") — mapped into terms the same
    # way. No `category` field at all (unlike SimplifyJobs/JGCL/zshah101) — this
    # feed isn't SWE-scoped, so category is left empty and _matches_vanshb03
    # doesn't check it, permissive like every other missing-field case here.
    season = raw.get("season", "")
    return Listing(
        company=raw["company_name"],
        title=raw["title"],
        url=raw["url"],
        source="vanshb03",
        terms=[season] if season else [],
        locations=raw.get("locations", []),
        active=raw.get("active"),
        date_posted=raw.get("date_posted"),
        raw_id=raw["id"],
        sponsorship=raw.get("sponsorship", ""),
    )


def normalize_zshah101(raw: dict) -> Listing:
    # `season` here IS year-qualified ("Summer 2027"), and `is_open` is this
    # source's active-equivalent name. `location` is a single string, not a
    # list — wrapped for location_eligible(), which takes a list.
    loc = raw.get("location")
    return Listing(
        company=raw["company"],
        title=raw["title"],
        url=raw["url"],
        source="zshah101",
        category=raw.get("category", ""),
        terms=[raw["season"]] if raw.get("season") else [],
        locations=[loc] if loc else [],
        active=raw.get("is_open"),
        date_posted=_parse_iso_ts(raw.get("posted_at", "")),
        raw_id=raw["id"],
        sponsorship=raw.get("sponsorship", ""),
    )


def normalize_greenhouse(raw: dict, company: str) -> Listing:
    # No structured term field — raw_text (title + scraped content, HTML
    # stripped) is what _matches_greenhouse text-searches for a term string.
    # No `active` field either: Greenhouse's public API only ever returns
    # currently-open postings, so a job appearing here is active by construction.
    loc = raw.get("location", {}).get("name") if isinstance(raw.get("location"), dict) else None
    return Listing(
        company=company,
        title=raw["title"],
        url=raw["absolute_url"],
        source="Greenhouse",
        locations=[loc] if loc else [],
        active=True,
        date_posted=_parse_iso_ts(raw.get("updated_at", "")),
        raw_id=str(raw["id"]),
        raw_text=_strip_html(raw.get("content", "")),
    )


def normalize_ashby(raw: dict, company: str) -> Listing:
    # Role-type triage (employmentType == "Intern") happens in fetch_ashby,
    # before this is ever called — every raw dict reaching here is already an
    # internship posting, same reasoning as Greenhouse's active-by-construction.
    loc = raw.get("location")
    return Listing(
        company=company,
        title=raw["title"],
        url=raw["jobUrl"],
        source="Ashby",
        locations=[loc] if loc else [],
        active=raw.get("isListed", True),
        date_posted=_parse_iso_ts(raw.get("publishedAt", "")),
        raw_id=raw["id"],
        raw_text=raw.get("descriptionPlain", ""),
    )


def normalize_freehire(raw: dict, company: str) -> Listing:
    # Role-type triage (enrichment.seniority == "intern") happens in
    # fetch_freehire, before this is ever called. `location` is a single
    # "city, state, country; city2, ..." string, split into a list for
    # location_eligible(). active=True unconditionally — see the module
    # docstring in ingestion/freehire.py for why closed_at isn't trustworthy.
    # The tracking query string freehire appends isn't part of the real URL.
    loc = raw.get("location", "")
    locations = [part.strip() for part in loc.split(";") if part.strip()]
    return Listing(
        company=company,
        title=raw["title"],
        url=raw["url"].split("?")[0],
        source="Freehire",
        locations=locations,
        active=True,
        date_posted=_parse_iso_ts(raw.get("posted_at", "")),
        raw_id=raw["public_slug"],
        raw_text=f"{raw.get('description', '')} {(raw.get('enrichment') or {}).get('summary', '')}".strip(),
    )


def normalize_ai_jobs(raw: dict) -> Listing:
    # Role-type triage (level == "Intern") happens in fetch_ai_jobs. This
    # feed is a fresh-generated snapshot of currently-listed jobs (like
    # Greenhouse/Ashby) — active=True unconditionally, absence from a later
    # fetch is the real closure signal, which is why (unlike freehire) this
    # source is safe to add to recheck.py's FEEDS.
    loc = raw.get("location", "")
    return Listing(
        company=raw.get("company", ""),
        title=raw["title"],
        url=raw["url"],
        source="AIJobs",
        locations=[loc] if loc else [],
        active=True,
        date_posted=_parse_iso_ts(raw.get("posted", "")),
        raw_id=raw.get("slug") or raw["url"],
    )
