"""Map each source's raw shape to one internal Listing dataclass."""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Listing:
    company: str
    title: str
    url: str
    source: str  # SimplifyJobs | Jose-Gael-Cruz-Lopez | zapplyjobs
    category: str = ""
    terms: list = field(default_factory=list)
    locations: list = field(default_factory=list)
    target_year: list = field(default_factory=list)
    date_posted: Optional[int] = None
    raw_id: Optional[str] = None  # upstream id, present for JSON sources; None for zapplyjobs


def normalize_simplify(raw: dict) -> Listing:
    return Listing(
        company=raw["company_name"],
        title=raw["title"],
        url=raw["url"],
        source="SimplifyJobs",
        category=raw.get("category", ""),
        terms=raw.get("terms", []),
        locations=raw.get("locations", []),
        date_posted=raw.get("date_posted"),
        raw_id=raw["id"],
    )


def normalize_josegael(raw: dict) -> Listing:
    return Listing(
        company=raw["company_name"],
        title=raw["title"],
        url=raw["url"],
        source="Jose-Gael-Cruz-Lopez",
        category=raw.get("category", ""),
        locations=raw.get("locations", []),
        target_year=raw.get("target_year", []),
        date_posted=raw.get("date_posted"),
        raw_id=raw["id"],
    )


_ROW_RE = re.compile(
    r"^\|\s*(?:\[(?P<name_linked>[^\]]+)\]\((?P<url>[^)]+)\)|(?P<name_plain>[^|]+?))\s*\|"
    r"\s*(?P<status>[^|]*)\|\s*(?P<year>[^|]*)\|"
)


def parse_zapply_readme(text: str) -> list:
    """Extract table rows from the zapplyjobs README (no JSON feed, markdown table only)."""
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        m = _ROW_RE.match(line)
        if not m:
            continue
        name = (m.group("name_linked") or m.group("name_plain") or "").strip()
        if name in ("", "Name") or set(name) <= {"-", " "}:
            continue  # header / separator rows
        rows.append(
            Listing(
                company=name,
                title=name,
                url=m.group("url") or "",
                source="zapplyjobs",
                target_year=[m.group("year").strip()],
            )
        )
    return rows
