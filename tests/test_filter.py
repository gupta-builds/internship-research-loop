import json
from pathlib import Path

import pytest

from core.filter import load_profile, location_eligible, matches
from ingestion.normalize import normalize_josegael, normalize_simplify, parse_zapply_readme

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


def test_zapply_readme_parses_and_filters():
    text = (FIXTURES / "zapply_readme.md").read_text()
    listings = parse_zapply_readme(text)
    by_company = {l.company: l for l in listings}

    assert matches(by_company["NASA"], PROFILE) is True
    assert matches(by_company["Keploy API Fellowship"], PROFILE) is True
    assert matches(by_company["Paragon One Career Bootcamp"], PROFILE) is True

    assert matches(by_company["Dropbox SWE intern"], PROFILE) is False
    assert matches(by_company["EA Pathfinder"], PROFILE) is False
    # plain-text row with no markdown link (regex's name_plain branch, untested until now)
    assert by_company["Activision Blizzard SPARX"].url == ""
    assert matches(by_company["Activision Blizzard SPARX"], PROFILE) is False


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
    ],
)
def test_location_affirmatively_foreign_is_rejected(loc):
    assert location_eligible([loc]) is False, loc


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


def test_zapply_readme_handles_3_column_table_variant():
    """Regression test: the real README has a 3-column (Name|Year|Note) table
    alongside the usual 4-column (Name|Status|Year|Note) ones. A fixed-position
    parser misreads the Note text as the Year field for this table, silently
    dropping real matches (caught live against CodePath/Forage before phase 3)."""
    text = (FIXTURES / "zapply_readme.md").read_text()
    listings = parse_zapply_readme(text)
    by_company = {l.company: l for l in listings}

    assert by_company["CodePath"].target_year == ["All student"]
    assert by_company["Forage"].target_year == ["All student"]
    assert matches(by_company["CodePath"], PROFILE) is True
    assert matches(by_company["Forage"], PROFILE) is True
