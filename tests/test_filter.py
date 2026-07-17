import json
from pathlib import Path

import pytest

from core.filter import load_profile, matches
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
