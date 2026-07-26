"""Offline tests for enrich.py's pure logic — no network, per the suite's rule."""
from unittest.mock import Mock, patch

import pytest

import enrich
from enrich import extract_bylines, infer_email, linkedin_recruiter_snippet, read_dossier, replace_enrichment

DOSSIER = """---
uid: SimplifyJobs:abc
company: Fidelity Investments
url: https://example.com/job
---
# Fidelity Investments — Undergraduate Intern
Auto-discovered line.
"""


def test_read_dossier_parses_frontmatter():
    assert read_dossier(DOSSIER)["company"] == "Fidelity Investments"


def test_read_dossier_rejects_non_dossier():
    with pytest.raises(ValueError):
        read_dossier("# just a note\nno frontmatter")


def test_replace_enrichment_appends_then_replaces():
    once = replace_enrichment(DOSSIER, "## Enrichment (2026-07-18)\nv1\n")
    assert once.count("## Enrichment") == 1 and "v1" in once
    twice = replace_enrichment(once, "## Enrichment (2026-07-19)\nv2\n")
    assert twice.count("## Enrichment") == 1
    assert "v2" in twice and "v1" not in twice
    assert "Auto-discovered line." in twice  # original body untouched


def test_extract_bylines():
    md = ("Posted by Jane Doe on the blog.\n"
          "By [John Smith-Jones](https://x.com/j)\n"
          "by mentioning nothing capitalized here\n"
          "Nearby text that should not match.")
    assert extract_bylines(md) == ["Jane Doe", "John Smith-Jones"]


def test_infer_email():
    assert infer_email("Jane Doe", "acme.com") == "jane.doe@acme.com"
    assert infer_email("John Smith-Jones", "acme.com") == "john.smithjones@acme.com"
    assert infer_email("madonna", "acme.com") is None  # single name — no pattern
    assert infer_email("Jane Doe", "") is None  # no domain discovered


# Real hit shapes confirmed live 2026-07-26 against Firecrawl's /search API
# (Anduril recruiter/site:linkedin.com queries): each hit is
# {"url", "title", "description"} — Indeed/Glassdoor/simplify.jobs/LinkedIn
# job-post hits are exactly the kind of noise these must filter out.
_MIXED_HITS = [
    {"url": "https://www.linkedin.com/in/janedoe", "title": "Jane Doe - Recruiter at Acme"},
    {"url": "https://www.indeed.com/cmp/Acme/jobs", "title": "Acme jobs on Indeed"},
    {"url": "https://www.glassdoor.com/Overview/Acme", "title": "Acme on Glassdoor"},
    {"url": "https://simplify.jobs/p/acme-swe-intern", "title": "Acme SWE Intern"},
    {"url": "https://www.linkedin.com/jobs/view/12345", "title": "Acme is hiring"},
    {"url": "https://acme.com/careers", "title": "Careers at Acme"},
]


def test_excluded_contact_domains_filters_indeed_glassdoor_simplify_linkedin_jobs():
    with patch.object(enrich, "fc_search", return_value=_MIXED_HITS):
        survivors = enrich._search_and_filter("Acme recruiter", "fc-key")
    assert [h["url"] for h in survivors] == [
        "https://www.linkedin.com/in/janedoe",
        "https://acme.com/careers",
    ]


def test_linkedin_recruiter_snippet_never_calls_fc_scrape():
    hits = [{"url": "https://www.linkedin.com/in/katiekeaton",
            "title": "Katie Nielsen - Senior Recruiter at Acme", "description": ""}]
    scrape = Mock(side_effect=AssertionError("linkedin_recruiter_snippet must never scrape"))
    with patch.object(enrich, "fc_search", return_value=hits), patch.object(enrich, "fc_scrape", scrape):
        results = linkedin_recruiter_snippet("Acme", "fc-key")
    scrape.assert_not_called()
    assert results == [("Katie Nielsen - Senior Recruiter at Acme", "", "https://www.linkedin.com/in/katiekeaton")]


def test_linkedin_recruiter_snippet_ignores_non_linkedin_hits():
    """fc_search for a site:linkedin.com query can still return a stray
    non-LinkedIn hit (a page that quotes/links to LinkedIn) — must be
    dropped, not surfaced as a contact."""
    hits = [{"url": "https://example.com/mentions-linkedin", "title": "Some Page"}]
    with patch.object(enrich, "fc_search", return_value=hits):
        assert linkedin_recruiter_snippet("Acme", "fc-key") == []
