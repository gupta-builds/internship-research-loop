import json
from pathlib import Path

import pytest

from core.filter import _matches_josegael, degrees_eligible, load_profile, location_eligible, matches
from ingestion.normalize import normalize_josegael, normalize_simplify

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


