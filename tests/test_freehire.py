"""freehire — real ground-truth records only (see fixtures/freehire.json):
Google's exact posting a manual clipping audit flagged as a miss (freehire
found it ~7 hours before SimplifyJobs did, per the real created_at/date_posted
comparison in the Improvement Plan note), and Nuro's exact posting (the other
confirmed miss). No synthetic examples — both cases are real API responses.
"""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from core.filter import load_profile, matches
from ingestion.freehire import FREEHIRE_COMPANIES, fetch_freehire, lookup_company_on_freehire
from ingestion.normalize import normalize_freehire

FIXTURES = Path(__file__).parent / "fixtures"
PROFILE = load_profile()


def _load():
    return json.loads((FIXTURES / "freehire.json").read_text())


def _by_case(case):
    return next(r for r in _load() if r["_case"] == case)


def test_normalize_freehire_strips_tracking_param_and_splits_locations():
    raw = _by_case("should-match-google-exact-ground-truth-summer2027-in-title")
    listing = normalize_freehire(raw, "Google")

    assert listing.url == "https://www.google.com/about/careers/applications/jobs/results/85564713261245126"
    assert "?utm_source" not in listing.url
    assert listing.locations == ["Mountain View, CA, USA", "Atlanta, GA, USA", "Austin, TX, USA"]
    assert listing.active is True  # unconditional — see ingestion/freehire.py docstring
    assert listing.raw_id == "software-engineering-intern-bs-summer-2027-google-iyvtwjtd"


def test_google_ground_truth_posting_matches():
    """The literal miss this whole investigation started from — confirmed
    reachable via freehire when it was reachable nowhere else this session."""
    raw = _by_case("should-match-google-exact-ground-truth-summer2027-in-title")
    listing = normalize_freehire(raw, "Google")
    assert matches(listing, PROFILE) is True


def test_nuro_ground_truth_posting_rejects_no_year_anywhere():
    """Real and correct: Nuro's actual freehire record never states a year in
    title or description, so the permissive bare-year fallback has nothing to
    match — this posting would still need the discovery-time content fetch
    (or a human) to confirm timing, same as any other ambiguous case."""
    raw = _by_case("should-reject-nuro-exact-ground-truth-no-year-mentioned-anywhere")
    listing = normalize_freehire(raw, "Nuro")
    assert matches(listing, PROFILE) is False


def _search_response(jobs):
    resp = Mock(status_code=200)
    resp.json.return_value = {"data": jobs}
    return resp


def test_fetch_freehire_filters_to_structured_intern_seniority():
    intern_job = {**_by_case("should-match-google-exact-ground-truth-summer2027-in-title")}
    non_intern_job = {**intern_job, "public_slug": "senior-swe-google", "title": "Senior Software Engineer",
                       "enrichment": {"seniority": "senior"}}

    def fake_get(url, timeout=None):
        return _search_response([intern_job, non_intern_job])

    listings = fetch_freehire(http_get=fake_get)
    assert len(listings) == len(FREEHIRE_COMPANIES)  # one intern job per seeded company
    assert all(l.source == "Freehire" for l in listings)


def test_fetch_freehire_skips_a_dead_company_without_crashing():
    import requests

    def flaky_get(url, timeout=None):
        if "google" in url:
            raise requests.ConnectionError("simulated: freehire down for this query")
        return _search_response([])

    listings = fetch_freehire(http_get=flaky_get)
    assert listings == []  # no crash


def test_lookup_company_on_freehire_found():
    resp = Mock(status_code=200)
    resp.json.return_value = {"data": {"company": {"slug": "google", "name": "Google", "job_count": 3651}}}
    result = lookup_company_on_freehire("Google", http_get=Mock(return_value=resp))
    assert result["job_count"] == 3651


def test_lookup_company_on_freehire_not_found_returns_empty_dict():
    resp = Mock(status_code=404)
    result = lookup_company_on_freehire("Some Nonexistent Company", http_get=Mock(return_value=resp))
    assert result == {}


def test_lookup_company_on_freehire_slugifies_the_company_name():
    captured = {}

    def fake_get(url, timeout=None):
        captured["url"] = url
        return Mock(status_code=200, json=lambda: {"data": {"company": {}}})

    lookup_company_on_freehire("Western Digital, Inc.", http_get=fake_get)
    assert "western-digital-inc" in captured["url"]
