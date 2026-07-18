"""Fetch raw listings from each source. Used both by the scheduled pipeline
and (with http_get injected) by tests — no live network calls in the suite.
"""
import requests

from ingestion.normalize import normalize_josegael, normalize_simplify

SIMPLIFY_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json"
JOSEGAEL_URL = "https://raw.githubusercontent.com/Jose-Gael-Cruz-Lopez/underclassmen-opportunities/main/.github/scripts/listings.json"

TIMEOUT = 30


def fetch_simplify(http_get=None) -> list:
    # http_get resolved at call time, not bound as a default at import time —
    # a `default=requests.get` here would capture the pre-patch function
    # object, silently defeating `patch("requests.get", ...)` in tests (and
    # letting them hit the real network instead of failing loudly).
    resp = (http_get or requests.get)(SIMPLIFY_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    return [normalize_simplify(raw) for raw in resp.json()]


def fetch_josegael(http_get=None) -> list:
    resp = (http_get or requests.get)(JOSEGAEL_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    return [normalize_josegael(raw) for raw in resp.json()]
