"""Fetch raw listings from each source. Not called by tests — those run against
tests/fixtures/ directly. Wired into the scheduled workflow in a later phase.
"""
import requests

from ingestion.normalize import normalize_josegael, normalize_simplify, parse_zapply_readme

SIMPLIFY_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json"
JOSEGAEL_URL = "https://raw.githubusercontent.com/Jose-Gael-Cruz-Lopez/underclassmen-opportunities/main/.github/scripts/listings.json"
ZAPPLY_README_URL = "https://raw.githubusercontent.com/zapplyjobs/underclassmen-internships/main/README.md"

TIMEOUT = 30


def fetch_simplify() -> list:
    resp = requests.get(SIMPLIFY_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    return [normalize_simplify(raw) for raw in resp.json()]


def fetch_josegael() -> list:
    resp = requests.get(JOSEGAEL_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    return [normalize_josegael(raw) for raw in resp.json()]


def fetch_zapply() -> list:
    resp = requests.get(ZAPPLY_README_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    return parse_zapply_readme(resp.text)
