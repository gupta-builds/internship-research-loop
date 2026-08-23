"""Real, live-verified InternDock fixtures (2026-08-24, Task 3) — no live
network calls in the suite, matching every other source's test file."""
from pathlib import Path
from unittest.mock import Mock

import requests

from ingestion.interndock import (
    MIN_POSTINGS_FOR_DROP,
    fetch_interndock_drop,
    fetch_interndock_drop_candidates,
    parse_interndock_postings,
)

FIXTURES = Path(__file__).parent / "fixtures"

# Real excerpt from https://www.interndock.com/sitemap.xml, fetched 2026-08-24 —
# a real drop page, a real drop-shaped-but-actually-advice page (checked live,
# see ingestion/interndock.py's module docstring), a plain non-guide page, and
# a real non-drop guide, verbatim.
_REAL_SITEMAP_EXCERPT = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.interndock.com/</loc></url>
  <url><loc>https://www.interndock.com/pricing</loc></url>
  <url><loc>https://www.interndock.com/tracker/guides/summer-2027-internship-drop-august-2026</loc></url>
  <url><loc>https://www.interndock.com/tracker/guides/summer-2027-internships-mega-drop-257-roles</loc></url>
  <url><loc>https://www.interndock.com/tracker/guides/summer-2027-internship-programs-open-now</loc></url>
  <url><loc>https://www.interndock.com/tracker/guides/harvard-resume-template-guide</loc></url>
</urlset>"""


def test_fetch_interndock_drop_candidates_loosely_filters_sitemap():
    fake_resp = Mock(status_code=200, text=_REAL_SITEMAP_EXCERPT)
    fake_get = Mock(return_value=fake_resp)

    candidates = fetch_interndock_drop_candidates(http_get=fake_get)

    assert "https://www.interndock.com/tracker/guides/summer-2027-internship-drop-august-2026" in candidates
    assert "https://www.interndock.com/tracker/guides/summer-2027-internships-mega-drop-257-roles" in candidates
    # Drop-shaped slug too — the loose pre-filter can't tell this apart from a
    # real drop by URL alone (confirmed live: it's actually a prose advice
    # article with zero real postings) — that's fetch_interndock_drop()'s job.
    assert "https://www.interndock.com/tracker/guides/summer-2027-internship-programs-open-now" in candidates
    assert "https://www.interndock.com/tracker/guides/harvard-resume-template-guide" not in candidates
    assert "https://www.interndock.com/pricing" not in candidates
    assert "https://www.interndock.com/" not in candidates


def test_parse_interndock_postings_real_fixture():
    """Real verbatim content (WebFetch, 2026-08-24) — the first 15 entries of
    interndock.com/tracker/guides/summer-2027-internship-drop-august-2026."""
    markdown = (FIXTURES / "interndock_drop.md").read_text(encoding="utf-8")

    postings = parse_interndock_postings(markdown)

    assert len(postings) == 15
    first = postings[0]
    assert first == {
        "title": "Summer 2027 Software Engineering Intern",
        "url": "https://job-boards.greenhouse.io/thenuclearcompany/jobs/5383236008",
        "company": "The Nuclear Company",
        "location": "",  # InternDock's own "See posting" placeholder maps to no location
    }
    req_id_entry = next(p for p in postings if "RQ225450" in p["title"])
    assert req_id_entry["title"] == "Summer 2027 Software Developer Internship — RQ225450"
    assert req_id_entry["company"] == "GDIT"
    assert req_id_entry["location"] == "Annapolis Junction, MD"
    lever_entry = next(p for p in postings if "belvederetrading" in p["url"])
    assert lever_entry["company"] == "Belvedere Trading"
    assert lever_entry["location"] == "Chicago, IL"


def test_parse_interndock_postings_ignores_non_matching_lines():
    markdown = "# Some Guide\n\nJust prose here, no postings.\n- A bullet with no Apply link at all.\n"
    assert parse_interndock_postings(markdown) == []


def test_fetch_interndock_drop_returns_postings_above_threshold():
    # Real fixture excerpt has 15 entries (the live page has 650+) — still
    # above MIN_POSTINGS_FOR_DROP=10, a real above-threshold case.
    markdown = (FIXTURES / "interndock_drop.md").read_text(encoding="utf-8")
    resp = Mock(status_code=200)
    resp.json.return_value = {"data": {"markdown": markdown}}
    fake_post = Mock(return_value=resp)

    postings = fetch_interndock_drop("https://x.example/drop", "fc-key", http_post=fake_post)

    assert len(postings) == 15
    assert len(postings) >= MIN_POSTINGS_FOR_DROP


def test_fetch_interndock_drop_returns_empty_when_below_threshold():
    """Real case, confirmed live 2026-08-24: 'summer-2027-internship-programs-open-now'
    is drop-shaped by slug but is actually a prose advice article — structurally
    not a drop, must not be treated as one just because it was Firecrawl-fetched."""
    resp = Mock(status_code=200)
    resp.json.return_value = {"data": {"markdown": "# Advice\n\nJust paragraphs about nine companies, no postings."}}
    fake_post = Mock(return_value=resp)

    assert fetch_interndock_drop("https://x.example/advice", "fc-key", http_post=fake_post) == []


def test_fetch_interndock_drop_fails_open_on_firecrawl_error():
    fake_post = Mock(side_effect=requests.ConnectionError("simulated: Firecrawl down"))
    assert fetch_interndock_drop("https://x.example/drop", "fc-key", http_post=fake_post) == []
