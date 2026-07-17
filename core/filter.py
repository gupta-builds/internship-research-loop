"""Layer 2 — pure field matching against each feed's own schema. No LLM, deterministic."""
import re
from pathlib import Path

import yaml

PROFILE_PATH = Path(__file__).parent / "profile.yaml"


def load_profile(path=PROFILE_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text())


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def matches(listing, profile: dict) -> bool:
    if listing.source == "SimplifyJobs":
        return _matches_simplify(listing, profile)
    if listing.source == "Jose-Gael-Cruz-Lopez":
        return _matches_josegael(listing, profile)
    if listing.source == "zapplyjobs":
        return _matches_zapply(listing, profile)
    raise ValueError(f"unknown source: {listing.source}")


def _matches_simplify(listing, profile: dict) -> bool:
    have_terms = {_norm(t) for t in listing.terms}
    excluded_terms = {_norm(t) for t in profile.get("exclude_terms", [])}
    if have_terms & excluded_terms:
        return False  # reject even if an allowed term is also present (multi-term/rotational postings)
    wanted_terms = {_norm(t) for t in profile["terms"]}
    if not (wanted_terms & have_terms):
        return False
    allowed_categories = {_norm(c) for c in profile["categories"]}
    return _norm(listing.category) in allowed_categories


def _matches_josegael(listing, profile: dict) -> bool:
    if not listing.target_year:
        return profile.get("accept_unrestricted", False)
    eligible = [_norm(t) for t in profile["eligible_class_tags"]]
    have = [_norm(t) for t in listing.target_year]
    return any(e in h for e in eligible for h in have)


def _matches_zapply(listing, profile: dict) -> bool:
    # target_year holds the raw README "Year" column value for this source.
    year = _norm(listing.target_year[0]) if listing.target_year else ""
    return bool(re.match(r"^all students?$", year))
