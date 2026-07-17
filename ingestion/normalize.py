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


_LINK_RE = re.compile(r"^\[([^\]]+)\]\(([^)]+)\)")


def _split_row(line: str) -> list:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_zapply_readme(text: str) -> list:
    """Extract table rows from the zapplyjobs README (no JSON feed, markdown table only).

    Column positions are read from each table's own header row rather than
    assumed fixed — the README has at least two layouts in the wild (most
    tables are Name|Status|Year|Note, but "Special Programs & Resources" is
    Name|Year|Note with no Status column). A fixed-position parser silently
    misparses the 3-column table's Note text into the Year field.
    """
    rows = []
    name_idx = year_idx = None
    for line in text.splitlines():
        if not line.startswith("|"):
            name_idx = year_idx = None  # table ended; next table gets its own header
            continue
        cells = _split_row(line)
        if all(set(c) <= {"-"} for c in cells if c):
            continue  # separator row (e.g. |---|---|---|)
        if "Name" in cells and "Year" in cells:
            name_idx, year_idx = cells.index("Name"), cells.index("Year")
            continue
        if name_idx is None or len(cells) <= max(name_idx, year_idx):
            continue  # no header seen yet for this table, or a short/malformed row

        name_cell = cells[name_idx]
        m = _LINK_RE.match(name_cell)
        company, url = (m.group(1), m.group(2)) if m else (name_cell, "")
        if not company:
            continue
        rows.append(
            Listing(company=company, title=company, url=url, source="zapplyjobs",
                    target_year=[cells[year_idx]])
        )
    return rows
