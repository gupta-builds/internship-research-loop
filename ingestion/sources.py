"""Fetch raw listings from each source. Used both by the scheduled pipeline
and (with http_get injected) by tests — no live network calls in the suite.
"""
import requests

from ingestion.normalize import (
    normalize_ai_jobs,
    normalize_ashby,
    normalize_greenhouse,
    normalize_josegael,
    normalize_simplify,
    normalize_vanshb03,
    normalize_zshah101,
)

SIMPLIFY_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json"
JOSEGAEL_URL = "https://raw.githubusercontent.com/Jose-Gael-Cruz-Lopez/underclassmen-opportunities/main/.github/scripts/listings.json"
VANSHB03_URL = "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/dev/.github/scripts/listings.json"
ZSHAH101_URL = "https://raw.githubusercontent.com/zshah101/Automated-List-Of-Summer-2027-and-Fall-2026-Tech-Internships/main/data/jobs.json"

GREENHOUSE_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
ASHBY_JOBS_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"

# Seed list, 2026-07-25 (quant/prop-trading batch) + 2026-07-26 (AI/ML
# diversification batch): every token here was verified live to resolve with
# real job data (see the Improvement Plan note for the 07-25 check; the
# 07-26 additions were each confirmed with a direct GET against
# GREENHOUSE_JOBS_URL/ASHBY_JOBS_URL returning a non-empty jobs array —
# fireworksai: 46 jobs, scaleai: 204 jobs, cohere: 137 jobs, cursor: 120
# jobs, modal: 32 jobs, elevenlabs: 215 jobs). Expand by grepping new
# dossier URLs for a job-boards.greenhouse.io or jobs.ashbyhq.com pattern, or
# by adding a known target company and testing its guessed token the same
# way — never add a token that hasn't been confirmed live, a wrong guess
# just silently returns 0 jobs, not an error.
GREENHOUSE_COMPANIES = {
    "fccincinnati": "FC Cincinnati",
    "aquaticcapitalmanagement": "Aquatic Capital Management",
    "walleyecapital-external-students": "Walleye Capital",
    "pdtpartners": "PDT Partners",
    "virtu": "Virtu Financial",
    "mwinternshipprogram": "Marshall Wace",
    "optiverus": "Optiver",
    "fireworksai": "Fireworks AI",
    "scaleai": "Scale AI",
}
ASHBY_COMPANIES = {
    "ellipsislabs": "Ellipsis Labs",
    "quadrillion-labs": "Quadrillion",
    "circleback": "Circleback",
    "ctgt": "CTGT",
    "pylon-labs": "Pylon",
    "cohere": "Cohere",
    "cursor": "Cursor (Anysphere)",
    "modal": "Modal",
    "elevenlabs": "ElevenLabs",
}

AI_JOBS_URL = "https://artificialintelligencejobs.co/jobs.json"

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


def fetch_vanshb03(http_get=None) -> list:
    resp = (http_get or requests.get)(VANSHB03_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    return [normalize_vanshb03(raw) for raw in resp.json()]


def fetch_zshah101(http_get=None) -> list:
    # data/jobs.json is a dict keyed by id, not a list — the only source shaped
    # this way (see the Improvement Plan note for why the raw store, not the
    # smaller pre-filtered docs/api/jobs.json, was chosen as the ingestion point).
    resp = (http_get or requests.get)(ZSHAH101_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    return [normalize_zshah101(raw) for raw in resp.json().values()]


def fetch_greenhouse(http_get=None) -> list:
    # One board per company, unlike every other source here. A single
    # company's board 404ing/renaming must not halt discovery for the other
    # eleven companies across all sources this run — skip that company,
    # don't crash the fetch (mirrors recheck.py's per-source fetch isolation).
    get = http_get or requests.get
    listings = []
    for token, company in GREENHOUSE_COMPANIES.items():
        try:
            resp = get(GREENHOUSE_JOBS_URL.format(token=token), timeout=TIMEOUT)
            resp.raise_for_status()
            jobs = resp.json().get("jobs", [])
        except requests.RequestException:
            continue
        for job in jobs:
            if "intern" in job.get("title", "").lower():  # no structured role-type field on this source
                listings.append(normalize_greenhouse(job, job.get("company_name", company)))
    return listings


def fetch_ashby(http_get=None) -> list:
    get = http_get or requests.get
    listings = []
    for token, company in ASHBY_COMPANIES.items():
        try:
            resp = get(ASHBY_JOBS_URL.format(token=token), timeout=TIMEOUT)
            resp.raise_for_status()
            jobs = resp.json().get("jobs", [])
        except requests.RequestException:
            continue
        for job in jobs:
            if job.get("employmentType") == "Intern":  # structured — use it, not title text
                listings.append(normalize_ashby(job, company))
    return listings


def fetch_ai_jobs(http_get=None) -> list:
    # A single generated snapshot, not per-company — one fetch, degrade like
    # the two big JSON feeds (empty on failure, never crash the run).
    get = http_get or requests.get
    try:
        resp = get(AI_JOBS_URL, timeout=TIMEOUT)
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])
    except requests.RequestException:
        return []
    return [normalize_ai_jobs(j) for j in jobs if j.get("level") == "Intern"]
