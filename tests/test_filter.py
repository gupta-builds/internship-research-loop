import json
from pathlib import Path

import pytest

from core.filter import load_profile, matches
from ingestion.normalize import normalize_josegael, normalize_simplify, parse_zapply_readme

FIXTURES = Path(__file__).parent / "fixtures"
PROFILE = load_profile()


def _load(name):
    return json.loads((FIXTURES / name).read_text())


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
