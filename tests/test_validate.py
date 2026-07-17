import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from ingestion.normalize import normalize_simplify
from vault_writer.validate import (
    check_format_compliance,
    check_not_duplicate,
    check_required_fields,
    check_url_live,
    validate,
)
from vault_writer.writer import render_dossier

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def listing():
    raw = json.loads((FIXTURES / "simplifyjobs.json").read_text())[0]
    return normalize_simplify(raw)


@pytest.fixture
def uid(listing):
    return f"{listing.source}:{listing.raw_id}"


def _ok_response(status=200):
    return Mock(status_code=status)


# --- check_required_fields ---

def test_required_fields_pass(listing, uid):
    assert check_required_fields(listing, uid).passed is True


def test_required_fields_rejects_missing_company(listing, uid):
    listing.company = ""
    result = check_required_fields(listing, uid)
    assert result.passed is False
    assert result.check == "required_fields"
    assert "company" in result.reason


def test_required_fields_rejects_missing_uid(listing):
    result = check_required_fields(listing, uid="")
    assert result.passed is False
    assert "uid" in result.reason


# --- check_url_live ---

def test_url_live_passes_on_2xx(listing):
    head = Mock(return_value=_ok_response(200))
    assert check_url_live(listing.url, http_head=head).passed is True


def test_url_live_passes_on_3xx(listing):
    head = Mock(return_value=_ok_response(301))
    assert check_url_live(listing.url, http_head=head).passed is True


def test_url_live_rejects_404(listing):
    head = Mock(return_value=_ok_response(404))
    result = check_url_live(listing.url, http_head=head)
    assert result.passed is False
    assert result.check == "url_liveness"
    assert "404" in result.reason


def test_url_live_rejects_on_request_exception(listing):
    import requests

    head = Mock(side_effect=requests.ConnectionError("dns lookup failed"))
    result = check_url_live(listing.url, http_head=head)
    assert result.passed is False
    assert result.check == "url_liveness"


# --- check_not_duplicate ---

def test_not_duplicate_passes_when_uid_unseen(uid):
    assert check_not_duplicate(uid, seen_ids=set()).passed is True


def test_not_duplicate_rejects_seen_uid(uid):
    result = check_not_duplicate(uid, seen_ids={uid})
    assert result.passed is False
    assert result.check == "not_duplicate"


# --- check_format_compliance ---

def test_format_compliance_passes_on_rendered_dossier(listing, uid):
    md = render_dossier(listing, uid, "2026-07-17", "Junior-eligible, Summer 2027, Software Engineering")
    assert check_format_compliance(md).passed is True


def test_format_compliance_rejects_blank_line_after_frontmatter(listing, uid):
    md = render_dossier(listing, uid, "2026-07-17", "reason")
    lines = md.splitlines()
    closing_idx = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    lines.insert(closing_idx + 1, "")
    broken = "\n".join(lines) + "\n"
    result = check_format_compliance(broken)
    assert result.passed is False
    assert "blank line" in result.reason


def test_format_compliance_rejects_duplicate_frontmatter_key(listing, uid):
    md = render_dossier(listing, uid, "2026-07-17", "reason")
    broken = md.replace("status: unreviewed", "status: unreviewed\nstatus: duplicate", 1)
    result = check_format_compliance(broken)
    assert result.passed is False
    assert "duplicate" in result.reason


def test_format_compliance_rejects_missing_frontmatter_field(listing, uid):
    md = render_dossier(listing, uid, "2026-07-17", "reason")
    lines = [l for l in md.splitlines() if not l.startswith("matched_reason:")]
    broken = "\n".join(lines) + "\n"
    result = check_format_compliance(broken)
    assert result.passed is False
    assert "matched_reason" in result.reason


def test_format_compliance_rejects_dashes_in_body(listing, uid):
    md = render_dossier(listing, uid, "2026-07-17", "reason")
    broken = md.rstrip("\n") + "\n---\nmore text\n"
    result = check_format_compliance(broken)
    assert result.passed is False
    assert "---" in result.reason


def test_format_compliance_rejects_stray_blank_line_in_body(listing, uid):
    md = render_dossier(listing, uid, "2026-07-17", "reason")
    lines = md.splitlines()
    lines.insert(len(lines) - 1, "")  # blank line mid-body, not after a blockquote
    broken = "\n".join(lines) + "\n"
    result = check_format_compliance(broken)
    assert result.passed is False


def test_format_compliance_allows_blank_line_after_callout(listing, uid):
    md = render_dossier(listing, uid, "2026-07-17", "reason")
    broken = md.rstrip("\n") + "\n> [!NOTE]\n> a callout\n\nmore prose after it\n"
    result = check_format_compliance(broken)
    assert result.passed is True


def test_format_compliance_rejects_trailing_blank_line(listing, uid):
    md = render_dossier(listing, uid, "2026-07-17", "reason")
    broken = md + "\n"
    result = check_format_compliance(broken)
    assert result.passed is False


def test_format_compliance_rejects_trailing_blank_line_after_callout(listing, uid):
    """The mid-body loop explicitly allows a blank line after a callout — but not
    when that blank line is the very last line in the file."""
    md = render_dossier(listing, uid, "2026-07-17", "reason")
    broken = md.rstrip("\n") + "\n> [!NOTE]\n> a callout\n\n"
    result = check_format_compliance(broken)
    assert result.passed is False
    assert "trailing" in result.reason


# --- validate() orchestrator ---

def test_validate_happy_path(listing, uid):
    md = render_dossier(listing, uid, "2026-07-17", "Junior-eligible, Summer 2027, Software Engineering")
    head = Mock(return_value=_ok_response(200))
    result = validate(listing, uid, md, seen_ids=set(), http_head=head)
    assert result.passed is True


def test_validate_stops_at_first_failing_check(listing, uid):
    """required_fields runs before url_liveness — a missing field should reject
    without ever making an HTTP call."""
    listing.company = ""
    md = render_dossier(listing, uid, "2026-07-17", "reason")
    head = Mock(side_effect=AssertionError("should not be called"))
    result = validate(listing, uid, md, seen_ids=set(), http_head=head)
    assert result.passed is False
    assert result.check == "required_fields"
    head.assert_not_called()


def test_validate_rejects_duplicate_uid(listing, uid):
    md = render_dossier(listing, uid, "2026-07-17", "reason")
    head = Mock(return_value=_ok_response(200))
    result = validate(listing, uid, md, seen_ids={uid}, http_head=head)
    assert result.passed is False
    assert result.check == "not_duplicate"
