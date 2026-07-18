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
