"""Task (Prompt 20) — write_gate_failures.json: a uid that keeps winning its
bucket's debate_compare ranking but keeps failing the SAME write-gate check
is structurally doomed, not merely out-ranked, and needs a distinct, faster
exclusion path from debate_losses.json/MAX_DEBATE_LOSSES.

Real, citable case: SimplifyJobs:de926b0a-99e7-4dbd-94cd-334ec565be9f failed
url_liveness (HTTP 403) in every one of 186 runs it appeared in between
2026-08-10 and 2026-08-28 while sitting in none of debate_losses.json,
excluded_uids.json, or seen_ids.json. Its real uid string is used directly
below (built via a Listing with that raw_id, not by editing the shared
simplifyjobs.json fixture other tests depend on for exact match counts)."""
import json

import run_pipeline
from ingestion.normalize import Listing
from test_run_pipeline import PROFILE, _fake_http_head_all_live, _run_once_kwargs

REAL_DEAD_LINK_UID = "SimplifyJobs:de926b0a-99e7-4dbd-94cd-334ec565be9f"
REAL_DEAD_LINK_URL = "https://simplify.jobs/p/de926b0a-99e7-4dbd-94cd-334ec565be9f"


def _dead_link_listing():
    return Listing(company="Acme", title="Software Engineer Intern", url=REAL_DEAD_LINK_URL,
                    source="SimplifyJobs", raw_id="de926b0a-99e7-4dbd-94cd-334ec565be9f")


def _rejection(check="url_liveness", reason="HTTP 403", uid=REAL_DEAD_LINK_UID):
    return {"uid": uid, "check": check, "reason": reason}


# --- update_write_gate_failures: pure-function tests ---

def test_below_threshold_stays_in_pool_not_excluded():
    failures = {}
    for _ in range(run_pipeline.WRITE_GATE_FAILURE_THRESHOLD - 1):
        failures, newly_excluded = run_pipeline.update_write_gate_failures(
            failures, [_rejection()], written_uids=[], now_iso="2026-08-28T00:00:00Z",
        )
        assert newly_excluded == []
    assert failures[REAL_DEAD_LINK_UID]["count"] == run_pipeline.WRITE_GATE_FAILURE_THRESHOLD - 1
    assert failures[REAL_DEAD_LINK_UID]["check"] == "url_liveness"


def test_nth_same_check_failure_excludes_and_removes_from_state():
    failures = {}
    for _ in range(run_pipeline.WRITE_GATE_FAILURE_THRESHOLD - 1):
        failures, _ = run_pipeline.update_write_gate_failures(
            failures, [_rejection()], written_uids=[], now_iso="2026-08-28T00:00:00Z",
        )
    failures, newly_excluded = run_pipeline.update_write_gate_failures(
        failures, [_rejection()], written_uids=[], now_iso="2026-08-28T07:57:52Z",
    )
    assert newly_excluded == [(REAL_DEAD_LINK_UID, "url_liveness", "HTTP 403")]
    assert REAL_DEAD_LINK_UID not in failures  # removed once excluded, not left at threshold


def test_checks_outside_write_gate_failure_checks_are_ignored():
    """required_fields/format_compliance (systemic, our own bug) and
    not_duplicate (structurally can't repeat, see the constant's citation)
    never accumulate here, no matter how many times they show up."""
    failures = {}
    for check in ("required_fields", "format_compliance", "not_duplicate", "opt_eligibility", "cs_relevance"):
        for _ in range(run_pipeline.WRITE_GATE_FAILURE_THRESHOLD + 5):
            failures, newly_excluded = run_pipeline.update_write_gate_failures(
                failures, [_rejection(check=check, uid=f"SimplifyJobs:{check}")],
                written_uids=[], now_iso="2026-08-28T00:00:00Z",
            )
            assert newly_excluded == []
    assert failures == {}


def test_a_different_check_restarts_the_streak_instead_of_accumulating():
    failures = {}
    failures, _ = run_pipeline.update_write_gate_failures(
        failures, [_rejection(check="url_liveness")], written_uids=[], now_iso="2026-08-26T00:00:00Z",
    )
    assert failures[REAL_DEAD_LINK_UID]["count"] == 1
    failures, newly_excluded = run_pipeline.update_write_gate_failures(
        failures, [_rejection(check="cross_source_duplicate", reason="company+title already in vault")],
        written_uids=[], now_iso="2026-08-27T00:00:00Z",
    )
    assert newly_excluded == []
    assert failures[REAL_DEAD_LINK_UID] == {
        "check": "cross_source_duplicate", "count": 1, "first_seen": "2026-08-27T00:00:00Z",
    }


def test_written_uid_clears_prior_failure_history():
    """A URL that was dead can come back alive — a win must wipe the slate,
    same semantics as update_debate_losses's written_uids handling."""
    failures = {}
    failures, _ = run_pipeline.update_write_gate_failures(
        failures, [_rejection()], written_uids=[], now_iso="2026-08-26T00:00:00Z",
    )
    assert REAL_DEAD_LINK_UID in failures
    failures, newly_excluded = run_pipeline.update_write_gate_failures(
        failures, [], written_uids=[REAL_DEAD_LINK_UID], now_iso="2026-08-27T00:00:00Z",
    )
    assert REAL_DEAD_LINK_UID not in failures
    assert newly_excluded == []


def test_written_uid_not_in_failures_is_a_no_op_pop():
    failures, newly_excluded = run_pipeline.update_write_gate_failures(
        {}, [], written_uids=["SimplifyJobs:never-failed"], now_iso="2026-08-28T00:00:00Z",
    )
    assert failures == {}
    assert newly_excluded == []


# --- integration: the real cited dead link is skipped on a simulated next run ---

def test_real_dead_link_uid_is_excluded_after_threshold_runs_of_validate_and_write(tmp_path):
    """validate_and_write itself never knows about write_gate_failures.json
    (that bookkeeping is run_once's job, same layering as debate_losses) —
    this drives the real uid through validate_and_write WRITE_GATE_FAILURE_
    THRESHOLD times with a 403 HEAD response, feeding each run's rejections
    into update_write_gate_failures the same way run_once does, and confirms
    the real cited uid crosses into exclusion on schedule, not before."""
    listing = _dead_link_listing()
    uid = REAL_DEAD_LINK_UID
    dead_head = lambda url, timeout=None, allow_redirects=True: type("R", (), {"status_code": 403})()

    failures = {}
    for i in range(run_pipeline.WRITE_GATE_FAILURE_THRESHOLD):
        written, rejections = run_pipeline.validate_and_write(
            [(uid, listing)], PROFILE, tmp_path, seen_ids=set(), date_found="2026-08-28", http_head=dead_head,
        )
        assert written == []
        assert rejections == [{"uid": uid, "check": "url_liveness", "reason": "HTTP 403"}]
        failures, newly_excluded = run_pipeline.update_write_gate_failures(
            failures, rejections, written_uids=[], now_iso=f"2026-08-{10 + i:02d}T00:00:00Z",
        )
        if i < run_pipeline.WRITE_GATE_FAILURE_THRESHOLD - 1:
            assert newly_excluded == []
    assert newly_excluded == [(uid, "url_liveness", "HTTP 403")]
    assert uid not in failures


def test_run_once_excludes_and_never_refetches_real_dead_link_after_threshold(tmp_path):
    """End-to-end via run_once: pre-seed write_gate_failures.json with the
    real cited uid one run short of the threshold, run once more with that
    uid's URL 403ing — confirms it (a) crosses into excluded_uids.json and
    write_gate_failures.json is cleared for it, then (b) a follow-up run
    never fetches its URL again, mirroring test_debate_losses.py's own
    already-excluded integration test."""
    from core.identity import compute_uid

    listing = _dead_link_listing()
    uid = compute_uid(listing)
    assert uid == REAL_DEAD_LINK_UID

    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / run_pipeline.WRITE_GATE_FAILURES_FILENAME).write_text(json.dumps({
        uid: {"check": "url_liveness", "count": run_pipeline.WRITE_GATE_FAILURE_THRESHOLD - 1,
              "first_seen": "2026-08-10T23:25:36Z"},
    }))

    def http_get_with_dead_link(url, timeout=None):
        from test_run_pipeline import _fake_http_get, _simplify_raw
        from ingestion.sources import SIMPLIFY_URL
        if url == SIMPLIFY_URL:
            from unittest.mock import Mock
            resp = Mock(status_code=200)
            resp.json.return_value = _simplify_raw() + [{
                "source": "Simplify", "category": "Software", "company_name": "Acme",
                "id": "de926b0a-99e7-4dbd-94cd-334ec565be9f",
                "title": "Software Engineer Intern", "active": True,
                "terms": ["Summer 2027"], "date_posted": 1765581501,
                "url": REAL_DEAD_LINK_URL, "locations": ["Remote"], "degrees": [],
            }]
            return resp
        return _fake_http_get(url, timeout=timeout)

    def http_head_dead_only(url, timeout=None, allow_redirects=True):
        from unittest.mock import Mock
        if url == REAL_DEAD_LINK_URL:
            return Mock(status_code=403)
        return _fake_http_head_all_live(url, timeout=timeout, allow_redirects=allow_redirects)

    # Generous budget so the real dead-link candidate isn't itself squeezed
    # out by _prioritize_and_cap before ever reaching validate_and_write.
    import pytest
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        run_pipeline, "MAX_NEW_WRITES_PER_RUN",
        {"AI/ML": 20, "Fullstack": 20, "CyS & Finance": 20, "Other": 20},
    )
    try:
        kwargs = _run_once_kwargs(
            tmp_path, state_dir=state_dir, http_get=http_get_with_dead_link, http_head=http_head_dead_only,
        )
        record = run_pipeline.run_once(**kwargs)
    finally:
        monkeypatch.undo()

    assert record["write_gate_excluded_count"] == 1
    excluded = run_pipeline.load_excluded_uids(state_dir)
    assert uid in excluded
    write_gate_failures = run_pipeline.load_write_gate_failures(state_dir)
    assert uid not in write_gate_failures

    log_path = kwargs["jarvis_dir"] / run_pipeline.WRITE_GATE_EXCLUDED_LOG_SUBPATH
    assert uid in log_path.read_text()

    # Follow-up run: the now-excluded real uid must never be fetched again.
    calls = []

    def guarded_fetch(url):
        calls.append(url)
        if url == REAL_DEAD_LINK_URL:
            raise AssertionError("fetched the write-gate-excluded uid's URL again")
        return ""

    kwargs2 = _run_once_kwargs(
        tmp_path, state_dir=state_dir, http_get=http_get_with_dead_link, http_head=http_head_dead_only,
        fetch_page_fn=guarded_fetch, jarvis_dir=kwargs["jarvis_dir"],
    )
    run_pipeline.run_once(**kwargs2)
    assert REAL_DEAD_LINK_URL not in calls
