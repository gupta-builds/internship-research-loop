import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from core.schema_drift import (
    ASHBY_SCHEMA_CHECK_TOKEN,
    FREEHIRE_SCHEMA_CHECK_SLUG,
    GREENHOUSE_SCHEMA_CHECK_TOKEN,
    LEVER_SCHEMA_CHECK_TOKEN,
    SchemaDriftError,
    check_ai_jobs_schema,
    check_all,
    check_applyguy_schema,
    check_ashby_schema,
    check_freehire_schema,
    check_greenhouse_schema,
    check_interndock_sitemap,
    check_josegael_schema,
    check_lever_schema,
    check_simplify_schema,
    check_vanshb03_schema,
    check_zshah101_schema,
)
from ingestion.freehire import FREEHIRE_SEARCH_URL
from ingestion.interndock import INTERNDOCK_SITEMAP_URL
from ingestion.sources import AI_JOBS_URL, ASHBY_JOBS_URL, GREENHOUSE_JOBS_URL, LEVER_JOBS_URL

FIXTURES = Path(__file__).parent / "fixtures"


def _json_response(payload):
    resp = Mock(status_code=200)
    resp.json.return_value = payload
    return resp


def _text_response(text):
    return Mock(status_code=200, text=text)


def _strip_case_keys(raws):
    """Fixtures carry a test-only _case label; real upstream entries don't."""
    return [{k: v for k, v in r.items() if k != "_case"} for r in raws]


@pytest.fixture
def simplify_raw():
    return _strip_case_keys(json.loads((FIXTURES / "simplifyjobs.json").read_text()))


@pytest.fixture
def josegael_raw():
    return _strip_case_keys(json.loads((FIXTURES / "josegael.json").read_text()))


@pytest.fixture
def vanshb03_raw():
    return _strip_case_keys(json.loads((FIXTURES / "vanshb03.json").read_text()))


@pytest.fixture
def zshah101_raw():
    # zshah101's real feed is a dict keyed by id, not a list — check_zshah101_schema
    # expects that shape (see is_dict=True in schema_drift.py).
    return {r["id"]: r for r in _strip_case_keys(json.loads((FIXTURES / "zshah101.json").read_text()))}


@pytest.fixture
def applyguy_raw():
    # ApplyGuy's real feed is {"updatedAt": ..., "jobs": [...]} — a third
    # shape check_applyguy_schema handles with its own bespoke check.
    return {"updatedAt": "2026-08-24T00:00:00Z", "jobs": _strip_case_keys(json.loads((FIXTURES / "applyguy.json").read_text()))}


# --- fixtures for the 6 sources added in Task 2 (Prompt 19, 2026-08-28) ---
# Real, verbatim single-entry shapes, same literals used in
# tests/test_sources.py / tests/test_freehire.py for the same live sources.

@pytest.fixture
def greenhouse_raw():
    return {"jobs": [{
        "id": 1, "title": "Summer 2027 Software Engineering Intern", "absolute_url": "https://x/1",
        "location": {"name": "NYC"}, "updated_at": "2026-07-24T15:05:09-04:00",
    }]}


@pytest.fixture
def ashby_raw():
    return {"jobs": [{
        "id": "a", "title": "Software Engineer Intern", "location": "SF", "jobUrl": "https://x/a",
        "publishedAt": "2026-06-01T00:00:00+00:00", "isListed": True, "descriptionPlain": "",
        "employmentType": "Intern",
    }]}


@pytest.fixture
def lever_raw():
    return [{
        "id": "cbde47db-c60b-4339-a8f4-a8e4f30505ab", "text": "Quantitative Trading Intern - Summer 2027",
        "categories": {"commitment": "Intern", "location": "Chicago, Illinois"},
        "hostedUrl": "https://jobs.lever.co/belvederetrading/cbde47db",
        "applyUrl": "https://jobs.lever.co/belvederetrading/cbde47db/apply",
        "createdAt": 1785864478389, "descriptionPlain": "Belvedere Trading is a proprietary trading firm.",
    }]


@pytest.fixture
def freehire_raw():
    return {"data": _strip_case_keys(json.loads((FIXTURES / "freehire.json").read_text()))[:1]}


@pytest.fixture
def ai_jobs_raw():
    return {"jobs": [{
        "title": "Product Management Intern (Summer 2027)", "location": "San Francisco",
        "url": "https://jobs.ashbyhq.com/databricks/some-real-posting-id", "posted": "2026-07-24",
        "company": "Databricks", "companyUrl": "https://databricks.com", "category": "Product",
        "level": "Intern", "remote": False, "region": "US", "slug": "databricks-product-management-intern-x1",
    }]}


@pytest.fixture
def interndock_sitemap_text():
    # Real shape confirmed live 2026-08-28: <loc> entries, some drop-shaped.
    return (
        "<urlset>"
        "<url><loc>https://www.interndock.com/tracker/guides/summer-2027-internships-mega-drop-257-roles</loc></url>"
        "<url><loc>https://www.interndock.com/pricing</loc></url>"
        "</urlset>"
    )


# --- happy path, one per source ---

def test_simplify_schema_passes_on_real_shape(simplify_raw):
    http_get = Mock(return_value=_json_response(simplify_raw))
    check_simplify_schema(http_get=http_get)  # does not raise


def test_josegael_schema_passes_on_real_shape(josegael_raw):
    http_get = Mock(return_value=_json_response(josegael_raw))
    check_josegael_schema(http_get=http_get)  # does not raise


# --- drift: a field the normalizer depends on vanishes ---

def test_simplify_schema_detects_renamed_key(simplify_raw):
    drifted = [{("company" if k == "company_name" else k): v for k, v in r.items()} for r in simplify_raw]
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="company_name"):
        check_simplify_schema(http_get=http_get)


def test_simplify_schema_detects_dropped_optional_field(simplify_raw):
    """category is read via .get() so a rename wouldn't crash the normalizer —
    it would just silently reject everything downstream. Drift check must
    still catch it."""
    drifted = [{k: v for k, v in r.items() if k != "category"} for r in simplify_raw]
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="category"):
        check_simplify_schema(http_get=http_get)


def test_josegael_schema_detects_renamed_key(josegael_raw):
    drifted = [{("year_target" if k == "target_year" else k): v for k, v in r.items()} for r in josegael_raw]
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="target_year"):
        check_josegael_schema(http_get=http_get)


def test_simplify_schema_detects_empty_list():
    http_get = Mock(return_value=_json_response([]))
    with pytest.raises(SchemaDriftError, match="non-empty"):
        check_simplify_schema(http_get=http_get)


def test_simplify_schema_detects_wrong_shape():
    http_get = Mock(return_value=_json_response({"not": "a list"}))
    with pytest.raises(SchemaDriftError, match="non-empty"):
        check_simplify_schema(http_get=http_get)


# --- check_all halts on the first failure ---

def test_check_all_raises_on_first_failing_source(simplify_raw, josegael_raw):
    responses = {
        "simplify": _json_response([]),  # drifted
    }
    call_count = {"n": 0}

    def http_get(url, timeout):
        call_count["n"] += 1
        return responses["simplify"]

    with pytest.raises(SchemaDriftError):
        check_all(http_get=http_get)
    assert call_count["n"] == 1  # halted before ever checking josegael


def test_check_all_passes_when_all_sources_are_healthy(
    simplify_raw, josegael_raw, vanshb03_raw, zshah101_raw, applyguy_raw,
    greenhouse_raw, ashby_raw, lever_raw, freehire_raw, ai_jobs_raw, interndock_sitemap_text,
):
    call_log = []

    def http_get(url, timeout):
        call_log.append(url)
        from ingestion.sources import APPLYGUY_URL, JOSEGAEL_URL, SIMPLIFY_URL, VANSHB03_URL, ZSHAH101_URL

        if url == SIMPLIFY_URL:
            return _json_response(simplify_raw)
        if url == JOSEGAEL_URL:
            return _json_response(josegael_raw)
        if url == VANSHB03_URL:
            return _json_response(vanshb03_raw)
        if url == ZSHAH101_URL:
            return _json_response(zshah101_raw)
        if url == APPLYGUY_URL:
            return _json_response(applyguy_raw)
        if url == GREENHOUSE_JOBS_URL.format(token=GREENHOUSE_SCHEMA_CHECK_TOKEN):
            return _json_response(greenhouse_raw)
        if url == ASHBY_JOBS_URL.format(token=ASHBY_SCHEMA_CHECK_TOKEN):
            return _json_response(ashby_raw)
        if url == LEVER_JOBS_URL.format(token=LEVER_SCHEMA_CHECK_TOKEN):
            return _json_response(lever_raw)
        if url == FREEHIRE_SEARCH_URL.format(slug=FREEHIRE_SCHEMA_CHECK_SLUG):
            return _json_response(freehire_raw)
        if url == AI_JOBS_URL:
            return _json_response(ai_jobs_raw)
        if url == INTERNDOCK_SITEMAP_URL:
            return _text_response(interndock_sitemap_text)
        raise AssertionError(f"unexpected url: {url}")

    check_all(http_get=http_get)  # does not raise
    assert len(call_log) == 11


# --- vanshb03 / zshah101 ---

def test_vanshb03_schema_passes_on_real_shape(vanshb03_raw):
    http_get = Mock(return_value=_json_response(vanshb03_raw))
    check_vanshb03_schema(http_get=http_get)  # does not raise


def test_vanshb03_schema_detects_dropped_sponsorship_field(vanshb03_raw):
    drifted = [{k: v for k, v in r.items() if k != "sponsorship"} for r in vanshb03_raw]
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="sponsorship"):
        check_vanshb03_schema(http_get=http_get)


def test_zshah101_schema_passes_on_real_shape(zshah101_raw):
    http_get = Mock(return_value=_json_response(zshah101_raw))
    check_zshah101_schema(http_get=http_get)  # does not raise


def test_zshah101_schema_detects_wrong_shape():
    """The one source shaped as a dict, not a list — a schema check that
    assumed list-shape would misread this as empty/drifted."""
    http_get = Mock(return_value=_json_response([]))
    with pytest.raises(SchemaDriftError, match="non-empty JSON object"):
        check_zshah101_schema(http_get=http_get)


def test_zshah101_schema_detects_dropped_is_open_field(zshah101_raw):
    drifted = {k: {kk: vv for kk, vv in v.items() if kk != "is_open"} for k, v in zshah101_raw.items()}
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="is_open"):
        check_zshah101_schema(http_get=http_get)


# --- the permissive-default fields: renamed upstream, they'd silently make
# every listing pass their checks — drift must catch them (2026-07-18) ---

@pytest.mark.parametrize("key", ["active", "degrees"])
def test_simplify_schema_detects_dropped_permissive_field(simplify_raw, key):
    drifted = [{k: v for k, v in r.items() if k != key} for r in simplify_raw]
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match=key):
        check_simplify_schema(http_get=http_get)


@pytest.mark.parametrize("key", ["active", "season"])
def test_josegael_schema_detects_dropped_permissive_field(josegael_raw, key):
    drifted = [{k: v for k, v in r.items() if k != key} for r in josegael_raw]
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match=key):
        check_josegael_schema(http_get=http_get)


# --- ApplyGuy (Task 2, 2026-08-24) — a third real shape: {"updatedAt", "jobs": [...]} ---

def test_applyguy_schema_passes_on_real_shape(applyguy_raw):
    http_get = Mock(return_value=_json_response(applyguy_raw))
    check_applyguy_schema(http_get=http_get)  # does not raise


def test_applyguy_schema_detects_dropped_season_field(applyguy_raw):
    """season is read via .get() so a rename wouldn't crash the normalizer —
    every entry would silently become the permissive no-season case instead."""
    drifted = {**applyguy_raw, "jobs": [{k: v for k, v in r.items() if k != "season"} for r in applyguy_raw["jobs"]]}
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="season"):
        check_applyguy_schema(http_get=http_get)


def test_applyguy_schema_detects_dropped_listing_url_field(applyguy_raw):
    drifted = {**applyguy_raw, "jobs": [{k: v for k, v in r.items() if k != "listingUrl"} for r in applyguy_raw["jobs"]]}
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="listingUrl"):
        check_applyguy_schema(http_get=http_get)


def test_applyguy_schema_detects_wrong_shape():
    """Not a bare list (SimplifyJobs/JGCL/vanshb03) or a dict keyed by posting
    id (zshah101) — a dict missing its own "jobs" wrapper key entirely."""
    http_get = Mock(return_value=_json_response({"updatedAt": "2026-08-24"}))
    with pytest.raises(SchemaDriftError, match="non-empty 'jobs' list"):
        check_applyguy_schema(http_get=http_get)


def test_applyguy_schema_detects_empty_jobs_list():
    http_get = Mock(return_value=_json_response({"updatedAt": "2026-08-24", "jobs": []}))
    with pytest.raises(SchemaDriftError, match="non-empty 'jobs' list"):
        check_applyguy_schema(http_get=http_get)


# --- Greenhouse (Task 2, 2026-08-28) — one representative company (scaleai) ---

def test_greenhouse_schema_passes_on_real_shape(greenhouse_raw):
    http_get = Mock(return_value=_json_response(greenhouse_raw))
    check_greenhouse_schema(http_get=http_get)  # does not raise


def test_greenhouse_schema_hits_the_schema_check_token(greenhouse_raw):
    http_get = Mock(return_value=_json_response(greenhouse_raw))
    check_greenhouse_schema(http_get=http_get)
    called_url = http_get.call_args[0][0]
    assert called_url == GREENHOUSE_JOBS_URL.format(token=GREENHOUSE_SCHEMA_CHECK_TOKEN)


def test_greenhouse_schema_detects_renamed_absolute_url(greenhouse_raw):
    """absolute_url is read via raw["absolute_url"] — a rename would crash
    normalize_greenhouse, not silently degrade it, but the drift check must
    still catch it before that ever happens in the real run."""
    drifted = {"jobs": [{("url" if k == "absolute_url" else k): v for k, v in j.items()} for j in greenhouse_raw["jobs"]]}
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="absolute_url"):
        check_greenhouse_schema(http_get=http_get)


def test_greenhouse_schema_passes_on_empty_jobs_list():
    """One company (scaleai) legitimately having zero open reqs right now
    is mundane, not drift — must not halt the whole run over it (see the
    allow_empty block comment in core/schema_drift.py)."""
    http_get = Mock(return_value=_json_response({"jobs": []}))
    check_greenhouse_schema(http_get=http_get)  # does not raise


# --- Ashby (Task 2, 2026-08-28) — one representative company (elevenlabs) ---

def test_ashby_schema_passes_on_real_shape(ashby_raw):
    http_get = Mock(return_value=_json_response(ashby_raw))
    check_ashby_schema(http_get=http_get)  # does not raise


def test_ashby_schema_hits_the_schema_check_token(ashby_raw):
    http_get = Mock(return_value=_json_response(ashby_raw))
    check_ashby_schema(http_get=http_get)
    called_url = http_get.call_args[0][0]
    assert called_url == ASHBY_JOBS_URL.format(token=ASHBY_SCHEMA_CHECK_TOKEN)


def test_ashby_schema_detects_dropped_employment_type(ashby_raw):
    """employmentType is what fetch_ashby's own role-type triage reads
    (job.get("employmentType") == "Intern") — the exact field whose real
    2026-08-21..08-28 drift-shaped incident (Prompt 19 Task 1) this check
    exists to catch early, even though it turned out not to be drift there."""
    drifted = {"jobs": [{k: v for k, v in j.items() if k != "employmentType"} for j in ashby_raw["jobs"]]}
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="employmentType"):
        check_ashby_schema(http_get=http_get)


def test_ashby_schema_passes_on_empty_jobs_list():
    """One company (elevenlabs) legitimately having zero open reqs right
    now is mundane, not drift — same reasoning as Greenhouse's own
    allow_empty test above."""
    http_get = Mock(return_value=_json_response({"jobs": []}))
    check_ashby_schema(http_get=http_get)  # does not raise


# --- Lever (Task 2, 2026-08-28) — one representative company (palantir) ---

def test_lever_schema_passes_on_real_shape(lever_raw):
    http_get = Mock(return_value=_json_response(lever_raw))
    check_lever_schema(http_get=http_get)  # does not raise


def test_lever_schema_hits_the_schema_check_token(lever_raw):
    http_get = Mock(return_value=_json_response(lever_raw))
    check_lever_schema(http_get=http_get)
    called_url = http_get.call_args[0][0]
    assert called_url == LEVER_JOBS_URL.format(token=LEVER_SCHEMA_CHECK_TOKEN)


def test_lever_schema_detects_dropped_text_field(lever_raw):
    """text is what both normalize_lever (raw["text"]) and fetch_lever's own
    role-type triage (job.get("text", "")) read."""
    drifted = [{k: v for k, v in j.items() if k != "text"} for j in lever_raw]
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="text"):
        check_lever_schema(http_get=http_get)


def test_lever_schema_passes_on_empty_list():
    """One company (palantir) legitimately having zero open reqs right now
    is mundane, not drift — same reasoning as Greenhouse's own allow_empty
    test above."""
    http_get = Mock(return_value=_json_response([]))
    check_lever_schema(http_get=http_get)  # does not raise


# --- Freehire (Task 2, 2026-08-28) — a fourth shape: {"data": [...]} plus a
# nested enrichment.seniority field ---

def test_freehire_schema_passes_on_real_shape(freehire_raw):
    http_get = Mock(return_value=_json_response(freehire_raw))
    check_freehire_schema(http_get=http_get)  # does not raise


def test_freehire_schema_hits_the_schema_check_slug(freehire_raw):
    http_get = Mock(return_value=_json_response(freehire_raw))
    check_freehire_schema(http_get=http_get)
    called_url = http_get.call_args[0][0]
    assert called_url == FREEHIRE_SEARCH_URL.format(slug=FREEHIRE_SCHEMA_CHECK_SLUG)


def test_freehire_schema_detects_dropped_public_slug(freehire_raw):
    drifted = {"data": [{k: v for k, v in j.items() if k != "public_slug"} for j in freehire_raw["data"]]}
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="public_slug"):
        check_freehire_schema(http_get=http_get)


def test_freehire_schema_detects_dropped_nested_seniority(freehire_raw):
    """seniority lives nested under enrichment — what fetch_freehire's own
    role-type triage reads ((job.get("enrichment") or {}).get("seniority")).
    A flat top-level key check alone wouldn't catch this."""
    drifted = {"data": [
        {**j, "enrichment": {k: v for k, v in j["enrichment"].items() if k != "seniority"}}
        for j in freehire_raw["data"]
    ]}
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="seniority"):
        check_freehire_schema(http_get=http_get)


def test_freehire_schema_passes_on_empty_data_list():
    """The one company (google) legitimately having zero intern-tagged
    postings right now is mundane, not drift — same reasoning as
    Greenhouse's own allow_empty test above."""
    http_get = Mock(return_value=_json_response({"data": []}))
    check_freehire_schema(http_get=http_get)  # does not raise


# --- AIJobs (Task 2, 2026-08-28) — one generated snapshot feed ---

def test_ai_jobs_schema_passes_on_real_shape(ai_jobs_raw):
    http_get = Mock(return_value=_json_response(ai_jobs_raw))
    check_ai_jobs_schema(http_get=http_get)  # does not raise


def test_ai_jobs_schema_hits_the_real_url(ai_jobs_raw):
    http_get = Mock(return_value=_json_response(ai_jobs_raw))
    check_ai_jobs_schema(http_get=http_get)
    called_url = http_get.call_args[0][0]
    assert called_url == AI_JOBS_URL


def test_ai_jobs_schema_detects_dropped_level_field(ai_jobs_raw):
    """level is what fetch_ai_jobs' own role-type triage reads
    (raw.get("level") == "Intern")."""
    drifted = {"jobs": [{k: v for k, v in j.items() if k != "level"} for j in ai_jobs_raw["jobs"]]}
    http_get = Mock(return_value=_json_response(drifted))
    with pytest.raises(SchemaDriftError, match="level"):
        check_ai_jobs_schema(http_get=http_get)


def test_ai_jobs_schema_detects_empty_jobs_list():
    http_get = Mock(return_value=_json_response({"jobs": []}))
    with pytest.raises(SchemaDriftError, match="non-empty 'jobs' list"):
        check_ai_jobs_schema(http_get=http_get)


# --- InternDock (Task 2, 2026-08-28) — no JSON API, so this checks the
# sitemap's own real shape instead of a field schema (see the block comment
# in core/schema_drift.py for why a deeper content-shape check isn't possible
# here without spending a real Firecrawl call on a URL that might not even be
# a real drop) ---

def test_interndock_sitemap_passes_on_real_shape(interndock_sitemap_text):
    http_get = Mock(return_value=_text_response(interndock_sitemap_text))
    check_interndock_sitemap(http_get=http_get)  # does not raise


def test_interndock_sitemap_hits_the_real_url(interndock_sitemap_text):
    http_get = Mock(return_value=_text_response(interndock_sitemap_text))
    check_interndock_sitemap(http_get=http_get)
    called_url = http_get.call_args[0][0]
    assert called_url == INTERNDOCK_SITEMAP_URL


def test_interndock_sitemap_detects_no_loc_entries():
    http_get = Mock(return_value=_text_response("<urlset></urlset>"))
    with pytest.raises(SchemaDriftError, match="no <loc> entries"):
        check_interndock_sitemap(http_get=http_get)


def test_interndock_sitemap_detects_no_drop_shaped_candidates():
    """Every real URL is still there, but none look drop-shaped anymore —
    e.g. interndock renamed its guide-slug convention entirely."""
    http_get = Mock(return_value=_text_response(
        "<urlset><url><loc>https://www.interndock.com/pricing</loc></url></urlset>"
    ))
    with pytest.raises(SchemaDriftError, match="none match the drop-shaped slug pattern"):
        check_interndock_sitemap(http_get=http_get)
