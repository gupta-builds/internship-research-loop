"""OPT signals and content extraction — every eligibility string below marked
'real' was copied verbatim from a live posting page fetched 2026-07-18."""
from pathlib import Path
from unittest.mock import Mock

import pytest

from ingestion.posting_page import extract_content, fetch_posting_markdown, opt_exclusion

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
