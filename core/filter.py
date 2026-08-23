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
# netherlands/hong kong/poland/israel added 2026-08-23 (dossier audit) — three
# real dossiers passed with no US signal at all despite an affirmative foreign
# country token already present in their stored locations field: Optiver
# "Quantitative Research Internship (2027 Start)" and "FPGA Internship (2027
# Start)" (["Amsterdam, North Holland, Netherlands"]), Google "HardwareSilicon
# Engineering PhD Intern, 2027" (["Tel Aviv, Israel"]), Google "Data Science
# PhD Intern, 2027" (["Warsaw, Poland"]), Marshall Wace "Technology Intern -
# Hong Kong - 2027" (["Hong Kong"]).
_NON_US = re.compile(
    r"\b(canada|can|uk|united kingdom|germany|india|france|spain|singapore|europe"
    r"|south america|united arab emirates|mexico|japan|china|ireland|australia"
    r"|netherlands|hong kong|poland|israel)\b"
)
# ',' or '.' before the state code tolerates real dirty data ('Dallas. TX');
# case-insensitive via upper() tolerates 'Carlsbad, Ca'.
_STATE_SUFFIX = re.compile(r"[.,]\s*([A-Za-z]{2})$")

# Bare foreign city names carrying no country/state token at all — the
# _NON_US regex above only ever sees a country word, so a location field
# that's just the bare city name slips through entirely. Real dossier, same
# 2026-08-23 audit: Marshall Wace "Technology Intern - London - 2027" stores
# locations as exactly ["London"], no "UK"/"United Kingdom" anywhere. Checked
# as an exact whole-string match (not a substring) so a real US city sharing
# the name — e.g. "New London, CT" — is never caught by this.
_NON_US_BARE_CITIES = {"london"}


def _entry_is_us_or_remote(loc: str) -> bool:
    l = _norm(loc)
    m = _STATE_SUFFIX.search(loc.strip())
    if m and m.group(1).upper() in _US_STATES:
        return True
    if l.split(",")[-1].strip() in _US_STATE_NAMES:
        return True  # 'New Mexico' before the denylist sees 'mexico'
    if l in _NON_US_BARE_CITIES:
        return False
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
    elif listing.source == "vanshb03":
        ok = _matches_vanshb03(listing, profile)
    elif listing.source == "zshah101":
        ok = _matches_zshah101(listing, profile)
    elif listing.source == "Greenhouse":
        ok = _matches_greenhouse(listing, profile)
    elif listing.source == "Ashby":
        ok = _matches_ashby(listing, profile)
    elif listing.source == "Freehire":
        ok = _matches_freehire(listing, profile)
    elif listing.source == "AIJobs":
        ok = _matches_ai_jobs(listing, profile)
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


# Year-less seasons ("Summer", "Multiple") can't affirm "Summer 2027", only
# exclude wrong cycles. Reject affirmatively-wrong ones; pass Summer/Multiple/
# Year-Round/Not Specified/missing, permissive like every other rule here.
# Shared by every source whose season/terms field can carry a bare, year-less
# cycle name (JGCL, vanshb03) — SimplifyJobs and zshah101 always carry a year.
# "winter" stays here even though Winter 2027 is wanted, and "spring" stays
# here even though Spring 2027 is now wanted too (profile.yaml terms) — a bare
# "Winter"/"Spring" from these two sources is ambiguous between the wanted
# cycle and an already-excluded one (Winter 2026 rotted off, Spring 2026 is in
# exclude_terms), same reasoning that keeps "fall" here. Only "summer" gets
# the permissive year-less pass; JGCL/vanshb03 postings for the other wanted
# cycles need their year-qualified form to match here, same pre-existing gap
# for winter as for spring — not introduced by this change.
_WRONG_CYCLE_SEASONS = {"spring", "fall", "winter"}


_HAS_YEAR = re.compile(r"\d{4}")


def _has_wrong_cycle_season(terms: list, excluded_terms: set) -> bool:
    for term in terms:
        t = _norm(term)
        if not t:
            continue  # whitespace-only season would IndexError the split below
        if t in excluded_terms:
            return True
        # The bare-season reject only applies to year-less strings — a
        # year-qualified one ("Winter 2027", "Spring 2027") is unambiguous and
        # must reach the real match logic below (target_year for JGCL,
        # wanted_terms for vanshb03) instead of being killed on the season
        # word alone, regardless of the correct year being present.
        if not _HAS_YEAR.search(t) and t.split()[0] in _WRONG_CYCLE_SEASONS:
            return True
    return False


def _matches_josegael(listing, profile: dict) -> bool:
    excluded_terms = {_norm(t) for t in profile.get("exclude_terms", [])}
    if _has_wrong_cycle_season(listing.terms, excluded_terms):  # season, mapped in normalize_josegael
        return False
    if not listing.target_year:
        return profile.get("accept_unrestricted", False)
    eligible = [_norm(t) for t in profile["eligible_class_tags"]]
    have = [_norm(t) for t in listing.target_year]
    return any(e in h for e in eligible for h in have)


# vanshb03's own structured signal for the OPT exclusion criterion — a first-party
# field beats the posting_page.py regex-on-scraped-text check, so reject here,
# before ever spending a Firecrawl call. "Does Not Offer Sponsorship" is
# deliberately NOT an exclusion (same "no visa sponsorship" != "no OPT" rule as
# everywhere else in this pipeline) — only an explicit citizenship requirement is.
_VANSHB03_CITIZENSHIP_REQUIRED = "u.s. citizenship is required"


def _matches_vanshb03(listing, profile: dict) -> bool:
    excluded_terms = {_norm(t) for t in profile.get("exclude_terms", [])}
    if _has_wrong_cycle_season(listing.terms, excluded_terms):  # season, mapped in normalize_vanshb03
        return False
    wanted_terms = {_norm(t) for t in profile["terms"]}
    have_terms = {_norm(t) for t in listing.terms}
    # wanted_terms are year-qualified ("summer 2027"); vanshb03's season is bare
    # ("summer") — match on the cycle word only, same permissive-by-default
    # posture as the wrong-cycle check above (can't affirm the year, can only
    # avoid rejecting a real match over a year vanshb03 never states).
    if not any(w.split()[0] in have_terms or w.split()[0] == h.split()[0] for w in wanted_terms for h in have_terms):
        return False
    if listing.sponsorship and _norm(listing.sponsorship) == _VANSHB03_CITIZENSHIP_REQUIRED:
        return False
    return True


# zshah101's season is year-qualified like SimplifyJobs' terms, and its
# category taxonomy differs from SimplifyJobs' own — map the two values we
# actually see onto the same intent, not the literal profile.categories list
# (which is SimplifyJobs-specific string spelling).
_ZSHAH101_CATEGORIES = {"software", "data & ml/ai"}
_ZSHAH101_CITIZENS_ONLY = "citizens-only"


def _matches_zshah101(listing, profile: dict) -> bool:
    excluded_terms = {_norm(t) for t in profile.get("exclude_terms", [])}
    have_terms = {_norm(t) for t in listing.terms}
    if have_terms & excluded_terms:
        return False
    wanted_terms = {_norm(t) for t in profile["terms"]}
    if not (wanted_terms & have_terms):
        return False
    if _norm(listing.category) not in _ZSHAH101_CATEGORIES:
        return False
    if listing.sponsorship and _norm(listing.sponsorship) == _ZSHAH101_CITIZENS_ONLY:
        return False
    return True


# Neither Greenhouse nor Ashby's public job APIs carry a structured term
# field — title + description text is all there is, and real postings on our
# own seeded companies (Marshall Wace's "Technology Intern - 2027", Ellipsis
# Labs' "Software Engineer - 2027 Interns") state the year without a season
# word at all. A strict "must contain the literal 'Summer 2027' string" rule
# would silently reject both — exactly the false-negative-is-worse-than-
# false-positive failure mode every other rule in this file was built to
# avoid. So: an explicit exclude_terms string always rejects; an explicit
# wanted term string always accepts; and a bare mention of the target year
# (with no season word) passes too, permissive like every other ambiguous
# case here — text with no wanted-term phrase AND no bare target-year digit
# anywhere still rejects, since that's no longer ambiguous, it's absent.
def _text_has_any(text: str, terms) -> bool:
    t = _norm(text)
    return any(_norm(term) in t for term in terms)


def _target_years(terms) -> set:
    return {re.search(r"\d{4}", t).group(0) for t in terms if re.search(r"\d{4}", t)}


def _matches_free_text_source(listing, profile: dict) -> bool:
    haystack = f"{listing.title} {listing.raw_text}"
    if _text_has_any(haystack, profile.get("exclude_terms", [])):
        return False
    if _text_has_any(haystack, profile["terms"]):
        return True
    # Fallback: no exact "Summer 2027"-style phrase, but the bare target year
    # is present — pass, permissive by design. Anything without even a bare
    # target-year digit string (wrong year, or no year mentioned at all)
    # rejects here; that's still permissive relative to the strict-phrase
    # rule, just not unconditionally permissive.
    t = _norm(haystack)
    return any(y in t for y in _target_years(profile["terms"]))


_matches_greenhouse = _matches_free_text_source
_matches_ashby = _matches_free_text_source
# Freehire's own postings often do state the term literally (Google's real
# posting title was "Software Engineering Intern, BS, Summer 2027"), but its
# aggregated sources are uneven — same free-text/bare-year fallback applies.
_matches_freehire = _matches_free_text_source
_matches_ai_jobs = _matches_free_text_source
