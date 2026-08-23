import json
from pathlib import Path

import pytest

from core.filter import _matches_josegael, degrees_eligible, load_profile, location_eligible, matches
from ingestion.normalize import (
    Listing,
    normalize_ai_jobs,
    normalize_ashby,
    normalize_greenhouse,
    normalize_josegael,
    normalize_lever,
    normalize_simplify,
    normalize_vanshb03,
    normalize_zshah101,
)

FIXTURES = Path(__file__).parent / "fixtures"
PROFILE = load_profile()


def _load(name):
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.parametrize("fixture_name", ["simplifyjobs.json", "josegael.json"])
def test_fixture_has_both_match_and_reject_cases(fixture_name):
    """Guards against silent test evaporation: pytest.mark.parametrize collects
    zero tests (no error) if a _case label typo empties one of the lists above."""
    cases = [r["_case"] for r in _load(fixture_name)]
    assert any(c.startswith("should-match") for c in cases), f"{fixture_name}: no should-match case"
    assert any(c.startswith("should-reject") for c in cases), f"{fixture_name}: no should-reject case"


@pytest.mark.parametrize(
    "raw",
    [r for r in _load("simplifyjobs.json") if r["_case"].startswith("should-match")],
)
def test_simplify_should_match(raw):
    assert matches(normalize_simplify(raw), PROFILE) is True, raw["_case"]


@pytest.mark.parametrize(
    "raw",
    [r for r in _load("simplifyjobs.json") if r["_case"].startswith("should-reject")],
)
def test_simplify_should_reject(raw):
    assert matches(normalize_simplify(raw), PROFILE) is False, raw["_case"]


@pytest.mark.parametrize(
    "raw",
    [r for r in _load("josegael.json") if r["_case"].startswith("should-match")],
)
def test_josegael_should_match(raw):
    assert matches(normalize_josegael(raw), PROFILE) is True, raw["_case"]


@pytest.mark.parametrize(
    "raw",
    [r for r in _load("josegael.json") if r["_case"].startswith("should-reject")],
)
def test_josegael_should_reject(raw):
    assert matches(normalize_josegael(raw), PROFILE) is False, raw["_case"]


# --- degrees gate (real live values, fetched 2026-07-18: apostrophe forms) ---

@pytest.mark.parametrize(
    "degrees,expected",
    [
        ([], True),  # 4676 live entries carry no degrees data — permissive pass
        (["Bachelor's"], True),
        (["Bachelor's", "Master's"], True),
        (["Master's", "PhD"], False),
        (["PhD"], False),
        (["Master's"], False),
        (["Associate's"], False),
    ],
)
def test_degrees_eligible(degrees, expected):
    assert degrees_eligible(degrees, PROFILE) is expected


def test_active_false_rejects_any_source():
    raw = next(r for r in _load("simplifyjobs.json") if r["_case"].startswith("should-match"))
    assert matches(normalize_simplify({**raw, "active": False}), PROFILE) is False


# --- JGCL season regression (real feed entries verbatim; _matches_josegael
# tested directly because every wrong-season entry in the live feed is also
# active:false, and the active gate in matches() would mask the season rule) ---

def test_josegael_season_rejects_wrong_cycles_real_entries():
    by_id = {r["id"]: r for r in _load("josegael.json")}
    partiful = normalize_josegael(by_id["partiful-campus-growth-manager-spring-2026"])
    assert partiful.terms == ["Spring"]  # season reaches Listing.terms — the dropped-field fix
    assert _matches_josegael(partiful, PROFILE) is False

    womentech = normalize_josegael(by_id["c2d3e4f5-6a7b-8c9d-0e1f-a2b3c4d5e6f7"])
    assert womentech.terms == ["Summer 2026"]
    assert _matches_josegael(womentech, PROFILE) is False


def test_josegael_yearless_summer_passes_real_mlh_entry():
    raw = next(r for r in _load("josegael.json") if r["id"] == "mlh-fellowship-summer-2026")
    listing = normalize_josegael(raw)
    assert listing.terms == ["Summer"]
    assert matches(listing, PROFILE) is True  # active true, Junior-eligible, year-less season


# Every string below was observed verbatim in live feed data 2026-07-17 —
# none are invented. The dirty ones ('Carlsbad, Ca', 'Dallas. TX') are real.
@pytest.mark.parametrize(
    "loc",
    [
        "Westlake, TX", "Carlsbad, Ca", "Dallas. TX", "NYC", "SF", "LA",
        "United States", "Remote", "Remote in USA", "Remote in USa",
        "Remote, US", "New Mexico", "Long Island, New York",
        "Hawaii, United States", "Multiple Locations", "Multiple HBCUs",
        "Virtual", "Hybrid", "U.S. Virgin Islands", "Multiple US Cities",
    ],
)
def test_location_us_or_ambiguous_is_eligible(loc):
    assert location_eligible([loc]) is True, loc


@pytest.mark.parametrize(
    "loc",
    [
        "Toronto, ON, Canada", "Toronto, ON, CAN", "Ontario, Canada",
        "London, UK", "Remote in Canada", "Remote in UK", "Remote in Germany",
        "Remote in India", "Bangalore, India", "Singapore", "Europe",
        "Dubai - United Arab Emirates", "Munich, Germany",
        # real, from the 2026-08-23 dossier audit's _NON_US denylist-gap finding
        "Amsterdam, North Holland, Netherlands",  # Optiver "Quantitative Research Internship (2027 Start)"
        "Tel Aviv, Israel",  # Google "HardwareSilicon Engineering PhD Intern, 2027"
        "Warsaw, Poland",  # Google "Data Science PhD Intern, 2027"
        "Hong Kong",  # Marshall Wace "Technology Intern - Hong Kong - 2027"
        "London",  # Marshall Wace "Technology Intern - London - 2027" — bare city, no country token
    ],
)
def test_location_affirmatively_foreign_is_rejected(loc):
    assert location_eligible([loc]) is False, loc


def test_location_new_london_ct_is_not_caught_by_bare_london_fallback():
    """The bare-city fallback added for 'London' alone must be an exact
    whole-string match, not a substring — a real US city sharing the name
    ('New London, CT') must still pass."""
    assert location_eligible(["New London, CT"]) is True


def test_location_no_data_is_unrestricted():
    assert location_eligible([]) is True  # zapplyjobs carries no locations at all


def test_location_one_us_entry_among_foreign_is_enough():
    assert location_eligible(["London, UK", "Boston, MA"]) is True


def test_matches_rejects_foreign_only_listing_end_to_end():
    raw = next(
        r for r in _load("simplifyjobs.json") if r["_case"].startswith("should-match")
    )
    listing = normalize_simplify({**raw, "locations": ["Toronto, ON, Canada"]})
    assert matches(listing, PROFILE) is False




def test_josegael_whitespace_only_season_does_not_crash():
    raw = next(r for r in _load("josegael.json") if r["id"] == "mlh-fellowship-summer-2026")
    listing = normalize_josegael({**raw, "season": " "})
    assert matches(listing, PROFILE) is True  # degenerate season ignored, not IndexError


# --- vanshb03 (real feed entries verbatim, 2026-07-25) ---

@pytest.mark.parametrize(
    "raw",
    [r for r in _load("vanshb03.json") if r["_case"].startswith("should-match")],
)
def test_vanshb03_should_match(raw):
    assert matches(normalize_vanshb03(raw), PROFILE) is True, raw["_case"]


@pytest.mark.parametrize(
    "raw",
    [r for r in _load("vanshb03.json") if r["_case"].startswith("should-reject")],
)
def test_vanshb03_should_reject(raw):
    assert matches(normalize_vanshb03(raw), PROFILE) is False, raw["_case"]


def test_vanshb03_no_sponsorship_is_not_an_exclusion():
    """'Does Not Offer Sponsorship' means no H-1B, not no OPT — same rule as
    everywhere else in this pipeline. Only 'U.S. Citizenship is Required' rejects."""
    raw = next(r for r in _load("vanshb03.json") if r["_case"] == "should-match-no-sponsorship-is-not-an-exclusion")
    listing = normalize_vanshb03(raw)
    assert listing.sponsorship == "Does Not Offer Sponsorship"
    assert matches(listing, PROFILE) is True


# --- zshah101 (real feed entries verbatim, 2026-07-25) ---

@pytest.mark.parametrize(
    "raw",
    [r for r in _load("zshah101.json") if r["_case"].startswith("should-match")],
)
def test_zshah101_should_match(raw):
    assert matches(normalize_zshah101(raw), PROFILE) is True, raw["_case"]


@pytest.mark.parametrize(
    "raw",
    [r for r in _load("zshah101.json") if r["_case"].startswith("should-reject")],
)
def test_zshah101_should_reject(raw):
    assert matches(normalize_zshah101(raw), PROFILE) is False, raw["_case"]


def test_zshah101_citizens_only_real_anduril_entry():
    raw = next(r for r in _load("zshah101.json") if r["_case"] == "should-reject-citizens-only-real-anduril-else-matches")
    listing = normalize_zshah101(raw)
    assert listing.sponsorship == "citizens-only"
    assert listing.terms == ["Summer 2027"] and listing.category == "Software"  # everything else about it matches
    assert matches(listing, PROFILE) is False


# --- Greenhouse / Ashby (real jobs on our seeded company boards, 2026-07-25) ---

def test_greenhouse_matches_literal_term_in_title():
    listing = Listing(company="PDT Partners", title="Summer 2027 Software Engineering Intern",
                       url="https://job-boards.greenhouse.io/pdtpartners/jobs/8077685", source="Greenhouse",
                       active=True, raw_text="")
    assert matches(listing, PROFILE) is True


def test_greenhouse_rejects_explicit_wrong_year_in_content():
    listing = Listing(company="Acme", title="Software Engineering Intern",
                       url="https://job-boards.greenhouse.io/acme/jobs/1", source="Greenhouse",
                       active=True, raw_text="Join us for our Summer 2026 internship program.")
    assert matches(listing, PROFILE) is False


def test_greenhouse_bare_year_with_no_season_word_passes_permissively():
    """Real case: Marshall Wace's live 'Technology Intern - 2027' postings state
    the year with no season word anywhere. A strict 'Summer 2027' literal-string
    match would silently reject a real match — the false-negative-is-worse-than-
    false-positive principle this whole file is built around applies here too."""
    listing = Listing(company="Marshall Wace", title="Technology Intern - 2027 - Singapore",
                       url="https://job-boards.greenhouse.io/mwinternshipprogram/jobs/1", source="Greenhouse",
                       active=True, raw_text="Join our 2027 internship cohort in Singapore.")
    assert matches(listing, PROFILE) is True


def test_greenhouse_bare_wrong_year_with_no_right_year_rejects():
    listing = Listing(company="Acme", title="Software Intern - 2026 Cohort",
                       url="https://job-boards.greenhouse.io/acme/jobs/2", source="Greenhouse",
                       active=True, raw_text="Our 2026 internship program.")
    assert matches(listing, PROFILE) is False


def test_ashby_matches_literal_term_in_description():
    listing = Listing(company="Centerfield", title="Software Engineer Intern",
                       url="https://jobs.ashbyhq.com/centerfield/1", source="Ashby",
                       active=True, raw_text="Join our team for Summer 2027.")
    assert matches(listing, PROFILE) is True


def test_ashby_bare_year_real_ellipsis_labs_case_passes():
    """Real case: Ellipsis Labs' live 'Software Engineer - 2027 Interns' posting
    never says 'Summer 2027' either, same reasoning as the Greenhouse case above."""
    listing = Listing(company="Ellipsis Labs", title="Software Engineer - 2027 Interns",
                       url="https://jobs.ashbyhq.com/ellipsislabs/1", source="Ashby",
                       active=True, raw_text="Ellipsis Labs is a profitable, venture-backed startup.")
    assert matches(listing, PROFILE) is True


def test_normalize_greenhouse_strips_html_and_maps_fields():
    raw = {"id": 8077685, "title": "Summer 2027 Software Engineering Intern",
           "absolute_url": "https://job-boards.greenhouse.io/pdtpartners/jobs/8077685",
           "location": {"name": "New York, NY"}, "updated_at": "2026-07-24T15:05:09-04:00",
           "content": "<p>Join our <strong>team</strong></p>"}
    listing = normalize_greenhouse(raw, "PDT Partners")
    assert listing.company == "PDT Partners"
    assert listing.locations == ["New York, NY"]
    assert listing.active is True
    assert "<" not in listing.raw_text and "Join our" in listing.raw_text
    assert listing.raw_id == "8077685"


def test_normalize_ashby_maps_fields():
    raw = {"id": "abc-123", "title": "Software Engineer Intern", "location": "Los Angeles, California",
           "jobUrl": "https://jobs.ashbyhq.com/centerfield/abc-123", "publishedAt": "2026-06-09T21:39:58+00:00",
           "isListed": True, "descriptionPlain": "Real description text."}
    listing = normalize_ashby(raw, "Centerfield")
    assert listing.company == "Centerfield"
    assert listing.locations == ["Los Angeles, California"]
    assert listing.active is True
    assert listing.raw_text == "Real description text."
    assert listing.raw_id == "abc-123"


# --- Lever (real jobs on our seeded company boards, 2026-08-24) ---

def test_lever_matches_literal_term_in_description():
    listing = Listing(company="Hermeus", title="Flight Software Engineering Intern - Summer 2027",
                       url="https://jobs.lever.co/hermeus/1/apply", source="Lever",
                       active=True, raw_text="Join our Summer 2027 internship cohort.")
    assert matches(listing, PROFILE) is True


def test_lever_bare_year_with_no_season_word_passes_permissively():
    """Real case: Belvedere Trading's live 'Quantitative Trading Intern -
    Summer 2027' description never repeats the season in raw_text, same
    reasoning as the Greenhouse/Ashby bare-year cases above."""
    listing = Listing(company="Belvedere Trading", title="Quantitative Trading Intern - 2027",
                       url="https://jobs.lever.co/belvederetrading/1/apply", source="Lever",
                       active=True, raw_text="Rotate between Belvedere's trading desks in 2027.")
    assert matches(listing, PROFILE) is True


def test_lever_rejects_explicit_wrong_year():
    listing = Listing(company="Acme", title="Software Engineering Intern",
                       url="https://jobs.lever.co/acme/1/apply", source="Lever",
                       active=True, raw_text="Join us for our Summer 2026 internship program.")
    assert matches(listing, PROFILE) is False


def test_normalize_lever_maps_fields_and_prefers_apply_url():
    # Real, verbatim shape from belvederetrading's live board, 2026-08-24.
    raw = {"id": "cbde47db-c60b-4339-a8f4-a8e4f30505ab", "text": "Quantitative Trading Intern - Summer 2027",
           "categories": {"commitment": "Intern", "location": "Chicago, Illinois"},
           "hostedUrl": "https://jobs.lever.co/belvederetrading/cbde47db",
           "applyUrl": "https://jobs.lever.co/belvederetrading/cbde47db/apply",
           "createdAt": 1785864478389, "descriptionPlain": "Belvedere Trading is a proprietary trading firm."}
    listing = normalize_lever(raw, "Belvedere Trading")
    assert listing.company == "Belvedere Trading"
    assert listing.locations == ["Chicago, Illinois"]
    assert listing.active is True
    assert listing.url == "https://jobs.lever.co/belvederetrading/cbde47db/apply"
    assert listing.raw_text == "Belvedere Trading is a proprietary trading firm."
    assert listing.raw_id == "cbde47db-c60b-4339-a8f4-a8e4f30505ab"
    assert listing.date_posted == 1785864478389 // 1000


def test_normalize_lever_falls_back_to_hosted_url_when_no_apply_url():
    raw = {"id": "x", "text": "Software Engineer Intern", "categories": {},
           "hostedUrl": "https://jobs.lever.co/acme/x", "createdAt": None}
    listing = normalize_lever(raw, "Acme")
    assert listing.url == "https://jobs.lever.co/acme/x"
    assert listing.date_posted is None


# --- Spring 2027 (low-weight wanted term, added 2026-07-26) ---

def test_terms_weight_present_and_correct():
    assert PROFILE["terms_weight"] == {
        "Summer 2027": "high",
        "Winter 2027": "high",
        "Spring 2027": "low",
    }


def test_simplify_matches_spring_2027_only():
    raw = next(r for r in _load("simplifyjobs.json") if r["_case"].startswith("should-match: Spring 2027 only"))
    assert raw["terms"] == ["Spring 2027"]
    assert matches(normalize_simplify(raw), PROFILE) is True


def test_josegael_matches_year_qualified_spring_2027():
    """Regression for the _has_wrong_cycle_season bug: a year-qualified season
    ("Spring 2027") was being rejected on the bare season word alone, same as
    it always has been for "Winter 2027" — the year makes it unambiguous and
    it must reach the target_year check instead of being killed upfront."""
    raw = next(r for r in _load("josegael.json") if r["id"] == "synthetic-spring-2027-example")
    listing = normalize_josegael(raw)
    assert listing.terms == ["Spring 2027"]
    assert matches(listing, PROFILE) is True


def test_josegael_bare_spring_still_rejects():
    """Bare, year-less "Spring" stays ambiguous (could be excluded Spring 2026
    or wanted Spring 2027) — same conservative treatment as bare "Winter"."""
    raw = next(r for r in _load("josegael.json") if r["id"] == "partiful-campus-growth-manager-spring-2026")
    assert _matches_josegael(normalize_josegael(raw), PROFILE) is False


def test_vanshb03_bare_spring_still_rejects():
    raw = next(r for r in _load("vanshb03.json") if r["_case"].startswith("should-reject-bare-spring"))
    assert matches(normalize_vanshb03(raw), PROFILE) is False


def test_zshah101_matches_spring_2027():
    raw = next(r for r in _load("zshah101.json") if r["_case"] == "should-match-spring-2027-low-weight-term-software")
    listing = normalize_zshah101(raw)
    assert listing.terms == ["Spring 2027"]
    assert matches(listing, PROFILE) is True


def test_greenhouse_matches_spring_2027_literal_term():
    listing = Listing(company="Acme", title="Software Engineering Intern - Spring 2027",
                       url="https://job-boards.greenhouse.io/acme/jobs/3", source="Greenhouse",
                       active=True, raw_text="")
    assert matches(listing, PROFILE) is True


def test_ashby_matches_spring_2027_literal_term():
    listing = Listing(company="Centerfield", title="Software Engineer Intern",
                       url="https://jobs.ashbyhq.com/centerfield/2", source="Ashby",
                       active=True, raw_text="Join our team for Spring 2027.")
    assert matches(listing, PROFILE) is True


def test_normalize_ai_jobs_maps_fields_and_matches_real_intern_record():
    """Real record, fetched 2026-07-25: Databricks 'Product Management Intern
    (Summer 2027)', level: Intern. AI Jobs API has no 'active' field — every
    entry is a currently-listed snapshot, same reasoning as Greenhouse/Ashby."""
    raw = {"title": "Product Management Intern (Summer 2027)", "location": "San Francisco",
           "url": "https://jobs.ashbyhq.com/databricks/some-real-posting-id", "posted": "2026-07-24",
           "company": "Databricks", "level": "Intern", "slug": "databricks-product-management-intern-x1"}
    listing = normalize_ai_jobs(raw)
    assert listing.company == "Databricks"
    assert listing.locations == ["San Francisco"]
    assert listing.active is True
    assert listing.source == "AIJobs"
    assert matches(listing, PROFILE) is True
