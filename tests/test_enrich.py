"""Offline tests for enrich.py's pure logic — no network, per the suite's rule."""
import pytest

from enrich import extract_bylines, infer_email, read_dossier, replace_enrichment

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
