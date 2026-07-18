"""Map each source's raw shape to one internal Listing dataclass."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Listing:
    company: str
    title: str
    url: str
    source: str  # SimplifyJobs | Jose-Gael-Cruz-Lopez
    category: str = ""
    terms: list = field(default_factory=list)
    locations: list = field(default_factory=list)
    target_year: list = field(default_factory=list)
    degrees: list = field(default_factory=list)
    active: Optional[bool] = None  # None = source didn't say; only explicit False rejects
    date_posted: Optional[int] = None
    raw_id: Optional[str] = None  # stable upstream id, present on both JSON sources


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
