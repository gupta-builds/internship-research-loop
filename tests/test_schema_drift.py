import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from core.schema_drift import (
    SchemaDriftError,
    check_all,
    check_josegael_schema,
    check_simplify_schema,
)

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


def test_check_all_passes_when_both_are_healthy(simplify_raw, josegael_raw):
    call_log = []

    def http_get(url, timeout):
        call_log.append(url)
        from ingestion.sources import JOSEGAEL_URL, SIMPLIFY_URL

        if url == SIMPLIFY_URL:
            return _json_response(simplify_raw)
        if url == JOSEGAEL_URL:
            return _json_response(josegael_raw)
        raise AssertionError(f"unexpected url: {url}")

    check_all(http_get=http_get)  # does not raise
    assert len(call_log) == 2


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
