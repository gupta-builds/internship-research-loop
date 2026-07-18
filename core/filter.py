"""Layer 2 — pure field matching against each feed's own schema. No LLM, deterministic."""
import re
from pathlib import Path

import yaml

PROFILE_PATH = Path(__file__).parent / "profile.yaml"


def load_profile(path=PROFILE_PATH) -> dict:
    return yaml.safe_load(Path(path).read_text())


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


# Built from live feed data 2026-07-17 (1216 distinct location strings across both
# JSON sources; zapplyjobs carries no location data at all). Rule: a US signal
# always wins, an affirmative foreign token loses, everything ambiguous passes —
# permissive by design, so 'Multiple Locations' / 'Virtual' / bare 'Remote' match
# and only listings that affirmatively say Canada/UK/etc. are dropped.
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO", "MS", "MT",
    "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY", "DC", "PR",
}
_US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho", "illinois",
    "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland",
    "massachusetts", "michigan", "minnesota", "mississippi", "missouri", "montana",
    "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah",
    "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming",
}
# Every foreign token actually observed in live data, plus a few obvious neighbors.
# ponytail: denylist can't name every country — a new foreign token passes until
# added here; acceptable because a US signal is never falsely rejected.
_NON_US = re.compile(
    r"\b(canada|can|uk|united kingdom|germany|india|france|spain|singapore|europe"
    r"|south america|united arab emirates|mexico|japan|china|ireland|australia)\b"
)
# ',' or '.' before the state code tolerates real dirty data ('Dallas. TX');
# case-insensitive via upper() tolerates 'Carlsbad, Ca'.
_STATE_SUFFIX = re.compile(r"[.,]\s*([A-Za-z]{2})$")


def _entry_is_us_or_remote(loc: str) -> bool:
    l = _norm(loc)
    m = _STATE_SUFFIX.search(loc.strip())
    if m and m.group(1).upper() in _US_STATES:
        return True
    if l.split(",")[-1].strip() in _US_STATE_NAMES:
        return True  # 'New Mexico' before the denylist sees 'mexico'
    return not _NON_US.search(l)


def location_eligible(locations: list) -> bool:
    if not locations:
        return True  # no location data at all = unrestricted posting
    return any(_entry_is_us_or_remote(x) for x in locations)


def matches(listing, profile: dict) -> bool:
    if listing.active is False:
        return False  # affirmatively closed upstream; None (source silent) passes
    if listing.source == "SimplifyJobs":
        ok = _matches_simplify(listing, profile)
    elif listing.source == "Jose-Gael-Cruz-Lopez":
        ok = _matches_josegael(listing, profile)
    else:
        raise ValueError(f"unknown source: {listing.source}")
    if ok and profile.get("locations_allow") == "us_remote":
        ok = location_eligible(listing.locations)
    if ok:
        ok = degrees_eligible(listing.degrees, profile)
    return ok


def degrees_eligible(degrees: list, profile: dict) -> bool:
    """Permissive like locations: no degrees data passes; non-empty data must
    include an allowed degree (PhD-only/Master's-only listings aren't
    Bachelor's-eligible). Real values use the apostrophe form ("Bachelor's")."""
    allowed = profile.get("degrees_allow")
    if not allowed or not degrees:
        return True
    return bool(set(degrees) & set(allowed))


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


# JGCL seasons are mostly year-less ("Summer" 66, "Multiple" 35 of 112 live
# entries, 2026-07-18) — they can't affirm "Summer 2027", only exclude wrong
# cycles. Reject affirmatively-wrong ones; pass Summer/Multiple/Year-Round/
# Not Specified/missing, permissive like every other rule here.
_WRONG_CYCLE_SEASONS = {"spring", "fall", "winter"}


def _matches_josegael(listing, profile: dict) -> bool:
    excluded_terms = {_norm(t) for t in profile.get("exclude_terms", [])}
    for term in listing.terms:  # season, mapped in normalize_josegael
        t = _norm(term)
        if not t:
            continue  # whitespace-only season would IndexError the split below
        if t in excluded_terms or t.split()[0] in _WRONG_CYCLE_SEASONS:
            return False
    if not listing.target_year:
        return profile.get("accept_unrestricted", False)
    eligible = [_norm(t) for t in profile["eligible_class_tags"]]
    have = [_norm(t) for t in listing.target_year]
    return any(e in h for e in eligible for h in have)
