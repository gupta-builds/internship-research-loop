"""revalidate.py — re-checks live dossiers against current core/ code using
their own stored content, no re-fetch. Real regression fixtures reuse the
same real content already cited in tests/test_relevance.py and
tests/test_filter.py for the 2026-08-23 dossier-audit fixes."""
from pathlib import Path

from revalidate import check_dossier, extract_posting_content, find_regressions


def test_extract_posting_content_from_enriched_dossier(tmp_path):
    path = tmp_path / "dossier.md"
    path.write_text(
        "---\ncompany: Acme\ntitle: SWE Intern\n---\n"
        "# SWE Intern\nFound 2026-08-23 via SimplifyJobs.\n"
        "## Posting (fetched 2026-08-23)\nReal job content here.\nMore content.\n"
    )
    assert extract_posting_content(path) == "Real job content here.\nMore content."


def test_extract_posting_content_from_thin_dossier(tmp_path):
    path = tmp_path / "dossier.md"
    path.write_text(
        "---\ncompany: Acme\ntitle: SWE Intern\n---\n"
        "# SWE Intern\nFound 2026-08-23 via SimplifyJobs. No posting content fetched.\n"
    )
    assert extract_posting_content(path) == ""


# --- check_dossier: real regression citations from the 2026-08-23 audit ---

def test_check_dossier_flags_real_non_us_location():
    """Real dossier: Optiver 'FPGA Internship (2027 Start)' — Netherlands,
    a _NON_US denylist gap fixed 2026-08-23."""
    fm = {"title": "FPGA Internship (2027 Start)", "company": "Optiver",
          "locations": ["Amsterdam, North Holland, Netherlands"]}
    assert check_dossier(fm, "") == "location_eligible"


def test_check_dossier_flags_real_stage1_reject_title():
    """Real dossier: Vertiv 'Product Management Intern' — matches
    stage1_reject's existing product-management-intern pattern (predates
    this session, written before that fix shipped 2026-08-21)."""
    fm = {"title": "Product Management Intern", "company": "Vertiv", "locations": []}
    assert check_dossier(fm, "") == "stage1_reject"


def test_check_dossier_flags_real_stage2_non_technical_content():
    """Real dossier: UHY 'Data Operations Intern' — Excel-only audit
    support, no signal word, now caught by the 2026-08-23 'uhy' hint."""
    fm = {"title": "Data Operations Intern", "company": "UHY", "locations": []}
    content = (
        "The Data Operations Intern supports the Shared Resources team in compiling, "
        "manipulating, and analyzing client data. Use Excel and firm-provided analytic "
        "tools. Strong knowledge of Excel."
    )
    assert check_dossier(fm, content) == "stage2_confirm"


def test_check_dossier_passes_real_genuine_posting():
    """Real dossier: Optiver 'Software Engineer Intern' style content —
    genuine technical role must still pass every check."""
    fm = {"title": "Software Engineer Intern", "company": "Acme Corp", "locations": ["Remote"]}
    assert check_dossier(fm, "Experience with Python, SQL, and REST APIs.") is None


def test_find_regressions_scans_real_vault_layout(tmp_path):
    dossiers_dir = tmp_path / "10_Areas/Career/Internships/List/Dossiers/Other"
    dossiers_dir.mkdir(parents=True)
    bad = dossiers_dir / "Data Operations Intern - UHY.md"
    bad.write_text(
        "---\ncompany: UHY\ntitle: Data Operations Intern\nlocations: []\n---\n"
        "# Data Operations Intern\nFound 2026-08-23 via SimplifyJobs.\n"
        "## Posting (fetched 2026-08-23)\nUse Excel and firm-provided analytic tools.\n"
    )
    good = dossiers_dir / "Software Engineer Intern - Acme.md"
    good.write_text(
        "---\ncompany: Acme\ntitle: Software Engineer Intern\nlocations: []\n---\n"
        "# Software Engineer Intern\nFound 2026-08-23 via SimplifyJobs.\n"
        "## Posting (fetched 2026-08-23)\nExperience with Python and SQL required.\n"
    )
    regressions = find_regressions(tmp_path)
    assert len(regressions) == 1
    assert regressions[0]["path"] == str(bad.relative_to(tmp_path))
    assert regressions[0]["reason"] == "stage2_confirm"
