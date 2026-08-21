"""OPT signals and content extraction — every eligibility string below marked
'real' was copied verbatim from a live posting page fetched 2026-07-18."""
from pathlib import Path
from unittest.mock import Mock

import pytest

from ingestion.posting_page import (
    _content_fetch_url,
    extract_content,
    fetch_posting_markdown,
    opt_exclusion,
    phd_only_exclusion,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "text",
    [
        # real — Anduril SWE Intern JD, the exclusion that removed it from the vault
        "U.S. Person status is required as this position needs to access export controlled data.",
        # constructed from the Phase 6 note's named signals (not observed live yet)
        "An active security clearance is required for this role.",
        "U.S. citizenship required due to government contract requirements.",
        "OPT/CPT candidates are not accepted for this position.",
        "Must be a U.S. citizen.",
        # real — Saronic SWE Intern (Fall 2026), fetched 2026-07-25: the
        # export-control/ITAR phrasing our original 6 patterns never covered
        "If this role is based in the United States, it requires access to export-controlled "
        "information or items that require “U.S. Person” status.",
        # real — Hermeus SWE Intern (HIL), fetched 2026-07-25
        "U.S. EXPORT CONTROL COMPLIANCE STATUS\nThe person hired will have access to information "
        "and items subject to U.S. export controls, and therefore, must either be a "
        "“U.S. person” as defined by 22 C.F.R. § 120.62.",
        # real — Varda Space Flight Software Internship, fetched 2026-07-25
        "ITAR Requirements\nVarda, like all employers, must ensure that its employees working in "
        "the United States are lawfully authorized to work in the U.S. Additionally, our employees "
        "are exposed to and have access to certain export-controlled technology. "
        "“US person” means: U.S. citizen, U.S. lawful permanent resident.",
    ],
)
def test_explicit_negative_signals_exclude(text):
    assert opt_exclusion(text) is not None, text


@pytest.mark.parametrize(
    "text",
    [
        # real — Palantir US Gov FDSE: conditional background investigation is NOT
        # a clearance requirement; kept per the permissive rule
        "Willingness to undergo a US government background investigation, depending on US government project requirements.",
        # real — Grant Thornton EEO boilerplate: 'citizenship status' in a
        # nondiscrimination clause must not trigger
        "without regard to race, color, religion, national origin, citizenship status, veteran status, disability",
        # real — Aquatic's sponsorship QUESTION (asks, doesn't exclude); and
        # 'no visa sponsorship' means no H-1B, not no OPT (Phase 6 semantics)
        "Will you require the firm's sponsorship to obtain, maintain, or extend your employment authorization?",
        "We are unable to provide visa sponsorship for this role.",
        # real — CTGT affirmatively sponsors
        "Base Salary $8K – $12K per month • Will Sponsor",
    ],
)
def test_non_signals_stay_eligible(text):
    assert opt_exclusion(text) is None, text


def test_extract_content_from_real_page():
    md = (FIXTURES / "posting_fiverings.md").read_text(encoding="utf-8")
    content = extract_content(md)
    assert content.startswith("# Summer Intern 2027 - Software Developer")
    assert "About Five Rings" in content
    assert "Back to jobs" not in content  # nav stripped
    assert "\n\n" not in content  # vault rule: no blank lines in body
    assert not any(l.strip() == "---" for l in content.splitlines())  # no body separators


def test_fetch_posting_markdown_calls_firecrawl():
    resp = Mock(status_code=200)
    resp.json.return_value = {"data": {"markdown": "# A Job"}}
    post = Mock(return_value=resp)
    assert fetch_posting_markdown("https://x.example/job", "fc-key", http_post=post) == "# A Job"
    _, kwargs = post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer fc-key"
    assert kwargs["json"]["url"] == "https://x.example/job"


def test_extract_content_from_real_ashby_page():
    """Real CTGT posting (jobs.ashbyhq.com), fetched 2026-07-26 — confirms the
    full JD (About/Role/Responsibilities/Qualifications) extracts cleanly."""
    md = (FIXTURES / "posting_ashby_ctgt.md").read_text(encoding="utf-8")
    content = extract_content(md)
    assert content.startswith("# Software Engineering Intern (Summer 2027)")
    assert "About CTGT" in content
    assert "What You Will Do" in content
    assert "Who You Are" in content
    assert "Apply for this Job" not in content  # trailing apply link stripped
    assert "\n\n" not in content
    assert not any(l.strip() == "---" for l in content.splitlines())


def test_content_fetch_url_strips_ashby_application_suffix():
    """Real bug, confirmed live 2026-07-26: the same CTGT posting returned
    4015 chars of full content at its base URL vs 1099 chars of bare
    application-form fields at its /application URL. listing.url (used for
    display/apply) must stay untouched — only the fetch target changes."""
    url = "https://jobs.ashbyhq.com/ellipsislabs/02136b22-35b1-4b3d-8bef-567c3380a849/application"
    assert _content_fetch_url(url) == "https://jobs.ashbyhq.com/ellipsislabs/02136b22-35b1-4b3d-8bef-567c3380a849"


def test_content_fetch_url_leaves_non_ashby_urls_alone():
    url = "https://job-boards.greenhouse.io/fiveringsllc/jobs/123/application"
    assert _content_fetch_url(url) == url


def test_content_fetch_url_leaves_ashby_non_application_urls_alone():
    url = "https://jobs.ashbyhq.com/ctgt/f657c2f5-125e-42b6-a68a-646bbea3d155"
    assert _content_fetch_url(url) == url


def test_fetch_posting_markdown_strips_ashby_application_suffix_before_calling_firecrawl():
    resp = Mock(status_code=200)
    resp.json.return_value = {"data": {"markdown": "# A Job"}}
    post = Mock(return_value=resp)
    fetch_posting_markdown("https://jobs.ashbyhq.com/acme/abc123/application", "fc-key", http_post=post)
    _, kwargs = post.call_args
    assert kwargs["json"]["url"] == "https://jobs.ashbyhq.com/acme/abc123"


# --- Task E: Google careers search-results-listing-shell extraction bug ---

def test_extract_content_skips_google_careers_listing_shell():
    """Real bug, confirmed 2026-07-26 on both Google dossiers sourced via
    Freehire (BS and MS tracks): the fetched markdown contains a whole
    unrelated search-results listing page (~20 job titles, 'Back to jobs
    search' nav, 'N jobs matched', pagination) before the real posting's own
    content. classify() fired on an unrelated listed job's title
    ('Senior Product Engineer, Machine Learning Accelerators') as a result.
    Fixture is the real captured content (tests/fixtures/posting_google_careers.md)."""
    md = (FIXTURES / "posting_google_careers.md").read_text(encoding="utf-8")
    content = extract_content(md)

    assert content.startswith("## Software Engineering Intern, MS, Summer 2027")
    assert "pursuing a Master's degree program in Computer Science" in content
    # none of the unrelated listed jobs survive
    assert "Regulatory and Litigation Counsel" not in content
    assert "Staff Software Developer, Embedded Systems" not in content
    assert "Corporate Development Associate" not in content
    assert "Senior Product Engineer, Machine Learning Accelerators" not in content
    assert "jobs matched" not in content
    assert "Back to jobs search" not in content


# --- Task F: content-level PhD-only degree gate ---

def test_phd_only_exclusion_rejects_real_optiver_text():
    """Real Optiver 'Quantitative Research Intern, PhD (Summer 2027)'
    (Greenhouse job id 8451781002) — no structured degrees field, so
    degrees_eligible() waved it through on missing-data permissiveness. Its
    real content states the PhD requirement as an enrollment condition rather
    than a blunt 'PhD required'."""
    text = (
        "As part of our assessment process, you may be invited to participate in a multi-day, on-site "
        "evaluative program.\nWho You Are:\n- Currently enrolled in a PhD program in Statistics, Computer "
        "Science, Machine Learning, Mathematics, or a related STEM field with outstanding academic "
        "performance\n- Expected graduation between December 2027 - June 2029"
    )
    assert phd_only_exclusion(text) is not None


@pytest.mark.parametrize(
    "text",
    [
        # real — Aquatic Capital Management "Software Engineer, Intern (Summer 2027)"
        "Active student pursuing a BS, MS, or PhD in mathematics, statistics, machine learning, physics, "
        "computer science, or other scientific disciplines with an expected graduation date between "
        "Fall 2027 and Spring 2028.",
        # real — Appian "Software Engineering Intern"
        "Currently pursuing a Bachelor's or Master's degree in Computer Science or Computer Engineering "
        "with a strong academic record.",
        # real — Manhattan Associates "A.I. Developer Co-Op (Boston, MA)"
        "Currently enrolled in a bachelor's or master's degree program in Computer Science, Artificial "
        "Intelligence, Software Engineering, Data Science, or a related discipline",
        # never reject on 'preferred'
        "A PhD is preferred but not required for this role.",
        # never reject on PhD merely listed among acceptable degrees
        "Open to Bachelor's, Master's, or PhD candidates.",
    ],
)
def test_phd_only_exclusion_does_not_reject_bachelors_masters_eligible_real_text(text):
    assert phd_only_exclusion(text) is None, text


def test_phd_only_exclusion_rejects_explicit_equivalent_phrasing():
    assert phd_only_exclusion("This role is open to doctoral candidates only.") is not None
    assert phd_only_exclusion("PhD required for this position.") is not None


# --- Task I: readable, structured dossier body content ---

def test_extract_content_dedupes_repeated_paragraph_real_conagra_case():
    """Real bug: the Conagra Brands 'Demand Science Rotational Analyst'
    fixture has its whole 'About Us' paragraph appearing twice verbatim."""
    about_us = (
        "At Conagra Brands, we have a rich heritage of making great food. We aspire to have the most "
        "impactful, energized and inclusive culture in food. As a member of our 18,000+ person team "
        "across 40+ locations, you are empowered to reach your potential, make an impact and own your "
        "career."
    )
    md = (
        f"# Demand Science Rotational Analyst - Summer 2027\n\n"
        f"{about_us}\n\n"
        f"Some other real content in between.\n\n"
        f"### About Us\n{about_us}\n"
    )
    content = extract_content(md)
    assert content.count("At Conagra Brands, we have a rich heritage") == 1
    assert "Some other real content in between." in content
    assert "### About Us" in content


def test_extract_content_splits_ats_chrome_run_ons_real_conagra_case():
    md = (
        "# Demand Science Rotational Analyst - Summer 2027\n"
        "locationsChicago, Illinois\n"
        "time typeFull time\n"
        "posted onPosted Today\n"
        "job requisition idReq-039400\n"
        "Have a taste for something big?\n"
    )
    content = extract_content(md)
    assert "locations\nChicago, Illinois" in content
    assert "time type\nFull time" in content
    assert "posted on\nPosted Today" in content
    assert "job requisition id\nReq-039400" in content


def test_extract_content_renders_real_section_names_as_headings():
    """Real shape from the Appian/Conagra fixtures: a fully-bolded standalone
    line naming a canonical section (Qualifications/Benefits/Compensation)
    becomes a real '###' heading; a non-canonical bolded line ('Why should
    you kick off your career with Conagra?') stays flattened prose — no
    invented section boundary."""
    md = (
        "# Software Engineering Intern\n"
        "**Why should you kick off your career with Conagra?**\n"
        "**Basic Qualifications**\n"
        "- Currently pursuing a degree in Computer Science.\n"
        "**Benefits**\n"
        "Comprehensive healthcare plans.\n"
    )
    content = extract_content(md)
    assert "### Basic Qualifications" in content
    assert "### Benefits" in content
    assert "**Why should you kick off your career with Conagra?**" in content  # not invented as a heading


def test_extract_content_strips_read_more_and_follow_us_chrome_real_manhattan_case():
    """Real: the Manhattan Associates 'A.I. Developer Co-Op' fixture ends
    with a 'Read More' truncation marker and a duplicated LinkedIn/X/Facebook
    'Follow Us' link block."""
    md = (
        "# A.I. Developer Co-Op (Boston, MA)\n"
        "### About Us\n"
        "At Manhattan Associates our supply chain and omnichannel technology positively affect how "
        "people work, shop and live.\n"
        "Read More\n"
        "#### Follow Us\n"
        "- [LinkedIn](https://www.linkedin.com/company/4376)\n"
        "- [X](https://twitter.com/ManhAssocNews)\n"
        "- [Facebook](https://www.facebook.com/pages/Manhattan-Associates/113391905337615)\n"
    )
    content = extract_content(md)
    assert "Read More" not in content
    assert "Follow Us" not in content
    assert "linkedin.com" not in content
    assert "twitter.com" not in content


def test_extract_content_with_no_internal_structure_stays_one_block():
    """A posting with no stated section names at all must not have section
    boundaries invented — same real-content-only rule as the heading test."""
    md = (
        "# Summer Intern 2027 - Software Developer\n"
        "About Five Rings. We are a proprietary trading firm.\n"
        "We are looking for driven students to join our team.\n"
    )
    content = extract_content(md)
    assert "###" not in content
    assert "About Five Rings" in content
