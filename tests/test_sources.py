"""Covers the fetch->normalize wiring in ingestion/sources.py. requests.get is
mocked throughout — no live network calls, matching the rest of the suite."""
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from ingestion import sources

FIXTURES = Path(__file__).parent / "fixtures"


def test_fetch_simplify_calls_correct_url_and_normalizes():
    raw = json.loads((FIXTURES / "simplifyjobs.json").read_text())
    fake_resp = Mock(status_code=200)
    fake_resp.json.return_value = raw
    with patch("requests.get", return_value=fake_resp) as mock_get:
        listings = sources.fetch_simplify()

    mock_get.assert_called_once_with(sources.SIMPLIFY_URL, timeout=sources.TIMEOUT)
    fake_resp.raise_for_status.assert_called_once()
    assert len(listings) == len(raw)
    assert listings[0].source == "SimplifyJobs"
    assert listings[0].company == raw[0]["company_name"]


def test_fetch_josegael_calls_correct_url_and_normalizes():
    raw = json.loads((FIXTURES / "josegael.json").read_text())
    fake_resp = Mock(status_code=200)
    fake_resp.json.return_value = raw
    with patch("requests.get", return_value=fake_resp) as mock_get:
        listings = sources.fetch_josegael()

    mock_get.assert_called_once_with(sources.JOSEGAEL_URL, timeout=sources.TIMEOUT)
    fake_resp.raise_for_status.assert_called_once()
    assert len(listings) == len(raw)
    assert listings[0].source == "Jose-Gael-Cruz-Lopez"


def test_fetch_simplify_propagates_http_errors():
    fake_resp = Mock(status_code=500)
    fake_resp.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    with patch("requests.get", return_value=fake_resp):
        with pytest.raises(requests.HTTPError):
            sources.fetch_simplify()


def test_fetch_vanshb03_calls_correct_url_and_normalizes():
    raw = json.loads((FIXTURES / "vanshb03.json").read_text())
    raw = [{k: v for k, v in r.items() if k != "_case"} for r in raw]
    fake_resp = Mock(status_code=200)
    fake_resp.json.return_value = raw
    with patch("requests.get", return_value=fake_resp) as mock_get:
        listings = sources.fetch_vanshb03()

    mock_get.assert_called_once_with(sources.VANSHB03_URL, timeout=sources.TIMEOUT)
    assert len(listings) == len(raw)
    assert listings[0].source == "vanshb03"


def test_fetch_zshah101_handles_dict_shape_and_normalizes():
    """zshah101's data/jobs.json is a dict keyed by id, not a list — the only
    source shaped this way. fetch_zshah101 must iterate .values(), not the feed."""
    raw = json.loads((FIXTURES / "zshah101.json").read_text())
    raw = [{k: v for k, v in r.items() if k != "_case"} for r in raw]
    as_dict = {r["id"]: r for r in raw}
    fake_resp = Mock(status_code=200)
    fake_resp.json.return_value = as_dict
    with patch("requests.get", return_value=fake_resp) as mock_get:
        listings = sources.fetch_zshah101()

    mock_get.assert_called_once_with(sources.ZSHAH101_URL, timeout=sources.TIMEOUT)
    assert len(listings) == len(raw)
    assert listings[0].source == "zshah101"


def _gh_response(jobs):
    resp = Mock(status_code=200)
    resp.json.return_value = {"jobs": jobs}
    return resp


def test_fetch_greenhouse_polls_every_seeded_company_and_filters_to_intern_titles():
    intern_job = {"id": 1, "title": "Summer 2027 Software Engineering Intern",
                  "absolute_url": "https://x/1", "location": {"name": "NYC"},
                  "updated_at": "2026-07-24T15:05:09-04:00", "content": "", "company_name": "PDT Partners"}
    non_intern_job = {"id": 2, "title": "Senior Software Engineer",
                       "absolute_url": "https://x/2", "location": {"name": "NYC"},
                       "updated_at": "2026-07-24T15:05:09-04:00", "content": "", "company_name": "PDT Partners"}

    def fake_get(url, timeout=None):
        return _gh_response([intern_job, non_intern_job])

    listings = sources.fetch_greenhouse(http_get=fake_get)
    assert len(listings) == len(sources.GREENHOUSE_COMPANIES)  # one intern job per seeded company
    assert all(l.source == "Greenhouse" for l in listings)
    assert all("Intern" in l.title for l in listings)


def test_fetch_greenhouse_skips_a_dead_company_board_without_crashing():
    """One company's board 404ing/renaming must not halt discovery for the
    other seeded companies (or the other 3 sources this run)."""
    tokens_seen = []

    def flaky_get(url, timeout=None):
        tokens_seen.append(url)
        if "pdtpartners" in url:
            raise requests.ConnectionError("simulated: board renamed")
        return _gh_response([])

    listings = sources.fetch_greenhouse(http_get=flaky_get)
    assert listings == []  # no crash, just nothing from the dead board or the empty ones
    assert len(tokens_seen) == len(sources.GREENHOUSE_COMPANIES)  # every company was still attempted


def _ashby_response(jobs):
    resp = Mock(status_code=200)
    resp.json.return_value = {"jobs": jobs}
    return resp


def test_fetch_ashby_filters_to_structured_intern_employment_type():
    intern_job = {"id": "a", "title": "Software Engineer Intern", "location": "SF",
                  "jobUrl": "https://x/a", "publishedAt": "2026-06-01T00:00:00+00:00",
                  "isListed": True, "descriptionPlain": "", "employmentType": "Intern"}
    fulltime_job = {"id": "b", "title": "Software Engineer", "location": "SF",
                    "jobUrl": "https://x/b", "publishedAt": "2026-06-01T00:00:00+00:00",
                    "isListed": True, "descriptionPlain": "", "employmentType": "FullTime"}

    def fake_get(url, timeout=None):
        return _ashby_response([intern_job, fulltime_job])

    listings = sources.fetch_ashby(http_get=fake_get)
    assert len(listings) == len(sources.ASHBY_COMPANIES)  # one Intern job per seeded company
    assert all(l.source == "Ashby" for l in listings)


def test_fetch_ashby_skips_a_dead_company_board_without_crashing():
    def flaky_get(url, timeout=None):
        if "ellipsislabs" in url:
            raise requests.ConnectionError("simulated: board renamed")
        return _ashby_response([])

    listings = sources.fetch_ashby(http_get=flaky_get)
    assert listings == []
