import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

import run_pipeline
from core.filter import load_profile
from core.git_ops import GitPushError
from core.identity import compute_uid
from core.schema_drift import SchemaDriftError
from ingestion.normalize import normalize_josegael, normalize_simplify

FIXTURES = Path(__file__).parent / "fixtures"
PROFILE = load_profile()


def _strip_case_keys(raws):
    return [{k: v for k, v in r.items() if k != "_case"} for r in raws]


def _simplify_raw():
    return _strip_case_keys(json.loads((FIXTURES / "simplifyjobs.json").read_text()))


def _josegael_raw():
    return _strip_case_keys(json.loads((FIXTURES / "josegael.json").read_text()))


def _vanshb03_raw():
    return _strip_case_keys(json.loads((FIXTURES / "vanshb03.json").read_text()))


def _zshah101_raw():
    # real feed shape: a dict keyed by id, not a list
    return {r["id"]: r for r in _strip_case_keys(json.loads((FIXTURES / "zshah101.json").read_text()))}


def _fake_http_get(url, timeout=None):
    from ingestion.freehire import FREEHIRE_SEARCH_URL
    from ingestion.sources import (
        AI_JOBS_URL,
        ASHBY_JOBS_URL,
        GREENHOUSE_JOBS_URL,
        JOSEGAEL_URL,
        SIMPLIFY_URL,
        VANSHB03_URL,
        ZSHAH101_URL,
    )

    resp = Mock(status_code=200)
    if url == SIMPLIFY_URL:
        resp.json.return_value = _simplify_raw()
    elif url == JOSEGAEL_URL:
        resp.json.return_value = _josegael_raw()
    elif url == VANSHB03_URL:
        resp.json.return_value = _vanshb03_raw()
    elif url == ZSHAH101_URL:
        resp.json.return_value = _zshah101_raw()
    elif url.startswith(GREENHOUSE_JOBS_URL.split("{")[0]) or url.startswith(ASHBY_JOBS_URL.split("{")[0]):
        # per-company board endpoints — pipeline-orchestration tests don't need
        # real per-company data, that's covered in test_sources.py directly
        resp.json.return_value = {"jobs": []}
    elif url.startswith(FREEHIRE_SEARCH_URL.split("{")[0]):
        resp.json.return_value = {"data": []}
    elif url == AI_JOBS_URL:
        resp.json.return_value = {"jobs": []}
    else:
        raise AssertionError(f"unexpected url: {url}")
    return resp


def _fake_http_head_all_live(url, timeout=None, allow_redirects=True):
    return Mock(status_code=200)


# --- small helpers ---

def test_load_save_seen_ids_round_trips(tmp_path):
    path = tmp_path / "seen_ids.json"
    run_pipeline.save_seen_ids(path, {"a:1", "b:2"})
    assert run_pipeline.load_seen_ids(path) == {"a:1", "b:2"}


def test_load_seen_ids_missing_file_returns_empty_set(tmp_path):
    assert run_pipeline.load_seen_ids(tmp_path / "nope.json") == set()


# --- backlog cap (2026-07-25 decision: throttle, don't absorb or discard) ---

def _listing_with_date(uid_suffix, date_posted):
    listing = normalize_simplify(_simplify_raw()[0])
    listing.raw_id = f"{listing.raw_id}-{uid_suffix}"
    listing.date_posted = date_posted
    return (compute_uid(listing), listing)


def test_prioritize_and_cap_keeps_most_recent_first():
    # _listing_with_date's base fixture (Palantir "Forward Deployed Software
    # Engineer - Internship - US Government") classifies to the 'Other'
    # bucket — all three items land in the same bucket's queue.
    items = [_listing_with_date(i, date_posted) for i, date_posted in enumerate([100, 300, 200])]
    this_run, deferred = run_pipeline._prioritize_and_cap(items, budget={"Other": 2})

    assert [d for _, l in this_run for d in [l.date_posted]] == [300, 200]
    assert [l.date_posted for _, l in deferred] == [100]


def test_prioritize_and_cap_missing_date_posted_sorts_last():
    items = [_listing_with_date("known", 500), _listing_with_date("unknown", None)]
    this_run, deferred = run_pipeline._prioritize_and_cap(items, budget={"Other": 1})

    assert this_run[0][1].date_posted == 500
    assert deferred[0][1].date_posted is None


def test_prioritize_and_cap_orders_preferred_company_first_within_bucket():
    """Task L integration: two 'Other'-bucket candidates, non-preferred one
    posted more recently — the debate comparator's preferred-company stage
    must still put the preferred company first when preferred_companies is
    supplied, overriding the bare-recency behavior of the pre-Task-L sort."""
    non_preferred_recent = _listing_with_date("recent", 1700000000)
    non_preferred_recent[1].company = "Random Startup Inc"
    preferred_older = _listing_with_date("older", 1600000000)
    preferred_older[1].company = "Google"

    this_run, deferred = run_pipeline._prioritize_and_cap(
        [non_preferred_recent, preferred_older], budget={"Other": 1},
        preferred_companies={"Google": "high"},
    )
    assert this_run[0][1].company == "Google"
    assert deferred[0][1].company == "Random Startup Inc"


def test_prioritize_and_cap_without_preferred_companies_keeps_recency_only_order():
    """preferred_companies=None (the default) must reproduce the exact
    pre-Task-L recency-only behavior — every existing caller/test that
    doesn't pass it should see no change."""
    items = [_listing_with_date(i, date_posted) for i, date_posted in enumerate([100, 300, 200])]
    this_run, deferred = run_pipeline._prioritize_and_cap(items, budget={"Other": 2})
    assert [l.date_posted for _, l in this_run] == [300, 200]
    assert [l.date_posted for _, l in deferred] == [100]


def test_prioritize_and_cap_scopes_budget_per_bucket():
    """A bucket with 0 eligible candidates this run must not let another
    bucket's items borrow its unused slots — each bucket draws only from its
    own ordered queue."""
    other_items = [_listing_with_date(i, date_posted) for i, date_posted in enumerate([100, 300, 200])]
    this_run, deferred = run_pipeline._prioritize_and_cap(
        other_items, budget={"Other": 2, "AI/ML": 5, "Fullstack": 5, "CyS & Finance": 5},
    )
    assert len(this_run) == 2  # AI/ML's unused slots don't spill over into Other
    assert len(deferred) == 1


def test_prioritize_and_cap_grants_reserved_slot_to_preferred_company_losing_the_debate():
    """Task A (2026-08-23): two preferred companies compete for a 1-slot
    budget — stage 1 ties (both 'high'), so recency alone decides the
    normal slot, and the older preferred company would lose entirely under
    the pre-Task-A behavior. The reserved slot is additive: both preferred
    candidates get written, deferred stays empty."""
    preferred_recent = _listing_with_date("recent", 1700000000)
    preferred_recent[1].company = "Google"
    preferred_older = _listing_with_date("older", 1600000000)
    preferred_older[1].company = "Citadel"

    this_run, deferred = run_pipeline._prioritize_and_cap(
        [preferred_recent, preferred_older], budget={"Other": 1},
        preferred_companies={"Google": "high", "Citadel": "high"},
    )
    assert {l.company for _, l in this_run} == {"Google", "Citadel"}
    assert deferred == []


def test_prioritize_and_cap_reserved_slot_is_a_noop_with_no_preferred_candidates():
    """A bucket with zero preferred candidates this run behaves exactly as
    before — no extra write, budget still caps normally."""
    items = [_listing_with_date(i, date_posted) for i, date_posted in enumerate([100, 300, 200])]
    this_run, deferred = run_pipeline._prioritize_and_cap(
        items, budget={"Other": 2}, preferred_companies={"Google": "high"},
    )
    assert len(this_run) == 2
    assert len(deferred) == 1


def test_prioritize_and_cap_reserved_slot_recency_tiebreak_among_preferred():
    """Three preferred companies competing for a 1-slot budget + 1 reserved
    slot — the most recent two get in (normal slot, then reserved slot);
    the third still loses the debate and stays deferred."""
    recent = _listing_with_date("recent", 1700000000)
    recent[1].company = "Google"
    middle = _listing_with_date("middle", 1600000000)
    middle[1].company = "Citadel"
    old = _listing_with_date("old", 1500000000)
    old[1].company = "Microsoft"

    this_run, deferred = run_pipeline._prioritize_and_cap(
        [recent, middle, old], budget={"Other": 1},
        preferred_companies={"Google": "high", "Citadel": "high", "Microsoft": "high"},
    )
    assert {l.company for _, l in this_run} == {"Google", "Citadel"}
    assert [l.company for _, l in deferred] == ["Microsoft"]


def test_run_once_defers_beyond_the_cap_and_leaves_it_for_next_run(tmp_path, monkeypatch):
    """The core guarantee: a deferred item is not marked seen, so it's neither
    lost (no silent drop) nor duplicated (no re-write) — it just naturally
    reappears as 'new' on the next run, same as any other unseen match."""
    monkeypatch.setattr(run_pipeline, "MAX_NEW_WRITES_PER_RUN", {"Other": 1})
    kwargs = _run_once_kwargs(tmp_path)
    record = run_pipeline.run_once(**kwargs)

    total_matched = sum(len(info["matched"]) for info in
                        run_pipeline.fetch_and_filter(PROFILE, http_get=_fake_http_get).values())
    assert record["written_count"] == 1
    assert record["deferred_count"] == total_matched - 1

    seen = run_pipeline.load_seen_ids(kwargs["state_path"])
    assert len(seen) == 1  # only the one actually written is seen — nothing deferred was marked


def test_build_matched_reason_per_source():
    simplify = normalize_simplify(_simplify_raw()[0])
    assert "Summer 2027" in run_pipeline.build_matched_reason(simplify, PROFILE)

    josegael_junior = normalize_josegael(_josegael_raw()[0])
    assert run_pipeline.build_matched_reason(josegael_junior, PROFILE) == "Junior-eligible"


def test_fetch_and_filter_counts_and_matches():
    results = run_pipeline.fetch_and_filter(PROFILE, http_get=_fake_http_get)
    assert results["SimplifyJobs"]["fetch_count"] == len(_simplify_raw())
    assert results["Jose-Gael-Cruz-Lopez"]["fetch_count"] == len(_josegael_raw())
    # every fixture set has at least one should-match case
    assert len(results["SimplifyJobs"]["matched"]) > 0
    assert len(results["Jose-Gael-Cruz-Lopez"]["matched"]) > 0


def test_dedup_new_splits_new_vs_already_seen():
    matched_by_source = run_pipeline.fetch_and_filter(PROFILE, http_get=_fake_http_get)
    all_matched = [l for info in matched_by_source.values() for l in info["matched"]]
    already_seen_uid = compute_uid(all_matched[0])

    new_listings, already_seen_count = run_pipeline.dedup_new(matched_by_source, seen_ids={already_seen_uid})

    assert already_seen_count == 1
    assert already_seen_uid not in [uid for uid, _ in new_listings]
    assert len(new_listings) == len(all_matched) - 1


def test_dedup_new_dedupes_within_the_same_run():
    """If the exact same uid were somehow matched twice in one run, it should
    only appear once in new_listings — not double-written."""
    listing = normalize_simplify(_simplify_raw()[0])
    matched_by_source = {"SimplifyJobs": {"fetch_count": 2, "matched": [listing, listing]}}

    new_listings, already_seen_count = run_pipeline.dedup_new(matched_by_source, seen_ids=set())

    assert len(new_listings) == 1
    assert already_seen_count == 1


def test_validate_and_write_happy_path(tmp_path):
    listing = normalize_simplify(_simplify_raw()[0])
    uid = compute_uid(listing)

    written, rejections = run_pipeline.validate_and_write(
        [(uid, listing)], PROFILE, tmp_path, seen_ids=set(), date_found="2026-07-17",
        http_head=_fake_http_head_all_live,
    )

    assert written == [uid]
    assert rejections == []
    dossiers_dir = tmp_path / "10_Areas/Career/Internships/List/Dossiers"
    assert any(dossiers_dir.glob("**/*.md"))


def test_validate_and_write_rejects_dead_url(tmp_path):
    listing = normalize_simplify(_simplify_raw()[0])
    uid = compute_uid(listing)
    dead_head = Mock(return_value=Mock(status_code=404))

    written, rejections = run_pipeline.validate_and_write(
        [(uid, listing)], PROFILE, tmp_path, seen_ids=set(), date_found="2026-07-17", http_head=dead_head,
    )

    assert written == []
    assert len(rejections) == 1
    assert rejections[0]["check"] == "url_liveness"
    dossiers_dir = tmp_path / "10_Areas/Career/Internships/List/Dossiers"
    assert not list(dossiers_dir.glob("**/*.md")) if dossiers_dir.exists() else True


def test_validate_and_write_rejects_cross_source_duplicate(tmp_path):
    """Same program via two sources (two distinct uids, one company+title) —
    the second write must be rejected by the cross_source_duplicate gate.
    MLH Fellowship landed twice this way before the 2026-07-18 cleanup."""
    listing = normalize_simplify(_simplify_raw()[0])
    twin_raw = {**_simplify_raw()[0], "id": "a-different-upstream-id"}
    twin = normalize_josegael({  # same company+title arriving via JGCL
        "id": "jgcl-twin", "company_name": listing.company, "title": listing.title,
        "url": listing.url, "season": "Summer", "active": True,
        "target_year": ["Junior (3rd year)"],
    })
    del twin_raw

    written, rejections = run_pipeline.validate_and_write(
        [(compute_uid(listing), listing), (compute_uid(twin), twin)],
        PROFILE, tmp_path, seen_ids=set(), date_found="2026-07-18",
        http_head=_fake_http_head_all_live,
    )

    assert written == [compute_uid(listing)]
    assert len(rejections) == 1
    assert rejections[0]["check"] == "cross_source_duplicate"


def test_validate_and_write_seeds_dedup_keys_from_existing_vault_files(tmp_path):
    """Keys come from the dossier files actually in the checkout — a listing
    whose company+title already sits in the vault (even under another uid,
    written by an earlier run) is rejected, not re-written."""
    listing = normalize_simplify(_simplify_raw()[0])
    first_uid = compute_uid(listing)
    run_pipeline.validate_and_write(
        [(first_uid, listing)], PROFILE, tmp_path, seen_ids=set(),
        date_found="2026-07-18", http_head=_fake_http_head_all_live,
    )

    twin = normalize_josegael({
        "id": "jgcl-twin", "company_name": listing.company, "title": listing.title,
        "url": listing.url, "season": "Summer", "active": True,
        "target_year": ["Junior (3rd year)"],
    })
    written, rejections = run_pipeline.validate_and_write(
        [(compute_uid(twin), twin)], PROFILE, tmp_path, seen_ids={first_uid},
        date_found="2026-07-18", http_head=_fake_http_head_all_live,
    )

    assert written == []
    assert rejections[0]["check"] == "cross_source_duplicate"


def test_file_github_issue_calls_gh_with_expected_args():
    calls = []
    run_pipeline.file_github_issue("owner/repo", "title", "body", run_gh=calls.append)

    assert len(calls) == 1
    args = calls[0]
    assert args[:3] == ["gh", "issue", "create"]
    assert "owner/repo" in args
    assert "title" in args
    assert "body" in args


# --- run_once integration tests ---

def _run_once_kwargs(tmp_path, **overrides):
    kwargs = dict(
        jarvis_dir=tmp_path / "jarvis",
        state_path=tmp_path / "state" / "seen_ids.json",
        runs_log_path=tmp_path / "logs" / "runs.jsonl",
        now=datetime(2026, 7, 17, 15, 0, tzinfo=timezone.utc),  # a Friday, not rollup time
        profile=PROFILE,
        http_get=_fake_http_get,
        http_head=_fake_http_head_all_live,
        push_fn=lambda repo_dir, message: True,
        issue_fn=Mock(),
    )
    kwargs.update(overrides)
    (tmp_path / "jarvis").mkdir(parents=True, exist_ok=True)
    return kwargs


def test_run_once_happy_path_marks_seen_and_writes_dossiers(tmp_path):
    kwargs = _run_once_kwargs(tmp_path)
    record = run_pipeline.run_once(**kwargs)

    assert record["halted"] is False
    assert record["written_count"] > 0
    assert not record["errors"]

    seen = run_pipeline.load_seen_ids(kwargs["state_path"])
    assert len(seen) == record["written_count"]

    dossiers_dir = kwargs["jarvis_dir"] / "10_Areas/Career/Internships/List/Dossiers"
    assert len(list(dossiers_dir.glob("**/*.md"))) == record["written_count"]

    logged = json.loads((kwargs["runs_log_path"]).read_text().splitlines()[0])
    assert logged["written_count"] == record["written_count"]

    kwargs["issue_fn"].assert_not_called()  # nothing systemic happened


def test_run_once_halts_on_schema_drift_and_writes_nothing(tmp_path, monkeypatch):
    def drifted_check(http_get=None):
        raise SchemaDriftError("SimplifyJobs: missing expected keys ['category']")

    monkeypatch.setattr(run_pipeline, "check_schema_drift", drifted_check)
    kwargs = _run_once_kwargs(tmp_path)
    record = run_pipeline.run_once(**kwargs)

    assert record["halted"] is True
    assert "missing expected keys" in record["halt_reason"]
    assert not run_pipeline.load_seen_ids(kwargs["state_path"])
    dossiers_dir = kwargs["jarvis_dir"] / "10_Areas/Career/Internships/List/Dossiers"
    assert not dossiers_dir.exists() or not list(dossiers_dir.glob("**/*.md"))
    kwargs["issue_fn"].assert_called_once()
    assert "SchemaDriftError" in kwargs["issue_fn"].call_args[0][1]


def test_run_once_does_not_mark_seen_when_push_fails(tmp_path):
    """The critical ordering guarantee: a validated, written dossier whose
    push fails must NOT be recorded in seen_ids — otherwise it's gone
    forever (never in the vault, never retried, because dedup thinks it
    already landed)."""

    def failing_push(repo_dir, message):
        raise GitPushError("simulated rejected push, retry also failed")

    kwargs = _run_once_kwargs(tmp_path, push_fn=failing_push)
    record = run_pipeline.run_once(**kwargs)

    assert record["errors"], "push failure must be recorded"
    assert record["written_count"] == 0  # not counted as durably written

    # the dossier files DO exist locally in the Jarvis checkout (validation
    # passed, write happened) — what must NOT have happened is seen_ids
    # advancing, since the push that would make them durable failed.
    dossiers_dir = kwargs["jarvis_dir"] / "10_Areas/Career/Internships/List/Dossiers"
    assert len(list(dossiers_dir.glob("**/*.md"))) > 0

    seen = run_pipeline.load_seen_ids(kwargs["state_path"])
    assert seen == set(), "a failed push must leave seen_ids empty so the item is retried next run"

    kwargs["issue_fn"].assert_called_once()
    assert "push failed" in kwargs["issue_fn"].call_args[0][1].lower()


def test_run_once_files_issue_on_systemic_rejection_not_routine_one(tmp_path):
    # url_liveness (routine) should NOT trigger an issue
    kwargs = _run_once_kwargs(tmp_path, http_head=Mock(return_value=Mock(status_code=404)))
    record = run_pipeline.run_once(**kwargs)
    assert all(r["check"] == "url_liveness" for r in record["rejections"])
    kwargs["issue_fn"].assert_not_called()


def test_run_once_second_run_does_not_rewrite_already_seen_items(tmp_path, monkeypatch):
    # Generous per-bucket budget so every fixture match fits in the first run
    # — this test is about seen-state idempotency across runs, not pacing.
    monkeypatch.setattr(
        run_pipeline, "MAX_NEW_WRITES_PER_RUN",
        {"AI/ML": 20, "Fullstack": 20, "CyS & Finance": 20, "Other": 20},
    )
    kwargs = _run_once_kwargs(tmp_path)
    first = run_pipeline.run_once(**kwargs)
    assert first["written_count"] > 0
    assert first["deferred_count"] == 0

    kwargs2 = _run_once_kwargs(tmp_path, jarvis_dir=kwargs["jarvis_dir"])
    kwargs2["state_path"] = kwargs["state_path"]
    kwargs2["runs_log_path"] = kwargs["runs_log_path"]
    second = run_pipeline.run_once(**kwargs2)

    assert second["written_count"] == 0
    assert second["already_seen_count"] == first["written_count"] + first["already_seen_count"]


def test_run_once_halts_and_files_issue_on_fetch_network_failure(tmp_path):
    """A source going offline (DNS failure, deleted repo, 5xx) must produce a
    logged, issue-filed halt — not an uncaught crash with no record (the
    PRD's previously-unmitigated 'source repo goes offline' risk)."""
    import requests as _requests

    def dying_http_get(url, timeout=None):
        raise _requests.ConnectionError("simulated: upstream repo unreachable")

    kwargs = _run_once_kwargs(tmp_path, http_get=dying_http_get)
    record = run_pipeline.run_once(**kwargs)

    assert record["halted"] is True
    assert "ConnectionError" in record["halt_reason"]
    logged = json.loads(kwargs["runs_log_path"].read_text().splitlines()[0])
    assert logged["halted"] is True
    kwargs["issue_fn"].assert_called_once()
    assert not run_pipeline.load_seen_ids(kwargs["state_path"])


def _page_with(text):
    return f"# Great Intern Job\nRole details here.\n{text}\nMore details."


def test_opt_exclusion_rejects_and_caches(tmp_path):
    listing = normalize_simplify(_simplify_raw()[0])
    uid = compute_uid(listing)
    cache = {}
    # real Anduril exclusion text, verbatim from the live page 2026-07-18
    fetch = Mock(return_value=_page_with(
        "U.S. Person status is required as this position needs to access export controlled data."))

    written, rejections = run_pipeline.validate_and_write(
        [(uid, listing)], PROFILE, tmp_path, seen_ids=set(), date_found="2026-07-18",
        http_head=_fake_http_head_all_live, fetch_page_fn=fetch, opt_cache=cache,
    )

    assert written == []
    assert rejections[0]["check"] == "opt_eligibility"
    assert cache[uid]["verdict"] == "excluded"


def test_opt_cache_short_circuits_before_fetch(tmp_path):
    listing = normalize_simplify(_simplify_raw()[0])
    uid = compute_uid(listing)
    cache = {uid: {"verdict": "excluded", "signal": "U.S. Person status is required", "checked": "2026-07-18"}}
    fetch = Mock(side_effect=AssertionError("must not fetch a cached-excluded posting"))

    written, rejections = run_pipeline.validate_and_write(
        [(uid, listing)], PROFILE, tmp_path, seen_ids=set(), date_found="2026-07-18",
        http_head=_fake_http_head_all_live, fetch_page_fn=fetch, opt_cache=cache,
    )

    assert written == [] and rejections[0]["check"] == "opt_eligibility"
    fetch.assert_not_called()


def test_fetch_failure_fails_open_to_thin_dossier(tmp_path):
    listing = normalize_simplify(_simplify_raw()[0])
    uid = compute_uid(listing)
    fetch = Mock(side_effect=ConnectionError("firecrawl down"))

    written, rejections = run_pipeline.validate_and_write(
        [(uid, listing)], PROFILE, tmp_path, seen_ids=set(), date_found="2026-07-18",
        http_head=_fake_http_head_all_live, fetch_page_fn=fetch, opt_cache={},
    )

    assert written == [uid] and rejections == []
    dossier = next((tmp_path / "10_Areas/Career/Internships/List/Dossiers").glob("**/*.md")).read_text()
    assert "No posting content fetched" in dossier  # thin body, discovery not blocked


def test_eligible_posting_gets_content_section(tmp_path):
    listing = normalize_simplify(_simplify_raw()[0])
    uid = compute_uid(listing)
    fetch = Mock(return_value=_page_with("Great role. Qualifications: Python."))

    written, _ = run_pipeline.validate_and_write(
        [(uid, listing)], PROFILE, tmp_path, seen_ids=set(), date_found="2026-07-18",
        http_head=_fake_http_head_all_live, fetch_page_fn=fetch, opt_cache={},
    )

    assert written == [uid]
    dossier = next((tmp_path / "10_Areas/Career/Internships/List/Dossiers").glob("**/*.md")).read_text()
    assert "## Posting (fetched 2026-07-18)" in dossier
    assert "Qualifications: Python." in dossier


def test_cross_source_key_punctuation_insensitive_marmon_case():
    """Real dup from the 2026-07-18 audit: same Workday req via two routes,
    titled 'Intern Co-op' vs 'Intern/Co-op'."""
    from core.identity import cross_source_key
    assert cross_source_key("Marmon Holdings", "Data Engineering Intern Co-op") == \
        cross_source_key("Marmon Holdings", "Data Engineering Intern/Co-op")


# --- Task A: per-bucket write budget + capacity notification (not a refusal) ---

DOSSIERS_SUBPATH = Path("10_Areas/Career/Internships/List/Dossiers")


def _seed_bucket(jarvis_dir, bucket_folder, count):
    d = Path(jarvis_dir) / DOSSIERS_SUBPATH / bucket_folder
    d.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (d / f"seed-{i}.md").write_text("placeholder\n")


def test_count_dossiers_by_bucket_counts_real_files(tmp_path):
    _seed_bucket(tmp_path, "Other", 5)
    _seed_bucket(tmp_path, "1 - AI & ML", 2)
    counts = run_pipeline.count_dossiers_by_bucket(tmp_path)
    assert counts["Other"] == 5
    assert counts["AI/ML"] == 2
    assert counts["Fullstack"] == 0


@pytest.mark.parametrize("seed_count,expect_at_capacity", [(48, False), (49, True), (50, True)])
def test_run_once_reports_bucket_at_capacity_without_refusing_writes(tmp_path, seed_count, expect_at_capacity):
    """Real fixture set writes exactly 1 'Other'-bucket item per run under the
    default budget — seeding N existing files means the post-write count is
    N+1. The write must happen either way (49 -> 50, or 50 -> 51); only
    whether the notification fires differs."""
    kwargs = _run_once_kwargs(tmp_path, state_dir=tmp_path / "state")
    _seed_bucket(kwargs["jarvis_dir"], "Other", seed_count)
    record = run_pipeline.run_once(**kwargs)

    assert record["written_count"] > 0  # the write happened regardless
    assert ("Other" in record["bucket_at_capacity"]) is expect_at_capacity


def test_run_once_files_issue_once_per_bucket_crossing_capacity(tmp_path):
    kwargs = _run_once_kwargs(tmp_path, state_dir=tmp_path / "state")
    _seed_bucket(kwargs["jarvis_dir"], "Other", 49)
    first = run_pipeline.run_once(**kwargs)
    assert "Other" in first["bucket_at_capacity"]
    capacity_issue_calls = [c for c in kwargs["issue_fn"].call_args_list if "at/over" in c.args[1]]
    assert len(capacity_issue_calls) == 1

    kwargs2 = _run_once_kwargs(
        tmp_path, jarvis_dir=kwargs["jarvis_dir"], state_path=kwargs["state_path"],
        runs_log_path=kwargs["runs_log_path"], state_dir=kwargs["state_dir"],
    )
    second = run_pipeline.run_once(**kwargs2)
    assert "Other" in second["bucket_at_capacity"]  # still at/over capacity
    capacity_issue_calls_2 = [c for c in kwargs2["issue_fn"].call_args_list if "at/over" in c.args[1]]
    assert len(capacity_issue_calls_2) == 0  # not refiled — already notified


@pytest.mark.parametrize(
    "seed_total,expect_dossier_total,expect_issue",
    [(186, 189, False), (187, 190, True), (197, 200, True)],
)
def test_run_once_global_total_thresholds(tmp_path, seed_total, expect_dossier_total, expect_issue):
    """150/170 stay informational-only (logged via dossier_total, no issue);
    190/200 additionally file a GitHub issue the first time each is crossed.
    The fixture set writes exactly 3 dossiers/run under the default budget
    (1 Other + 1 Fullstack + 1 CyS & Finance), so seed_total + 3 lands on the
    exact milestone under test."""
    kwargs = _run_once_kwargs(tmp_path, state_dir=tmp_path / "state")
    _seed_bucket(kwargs["jarvis_dir"], "Other", seed_total)
    record = run_pipeline.run_once(**kwargs)

    assert record["dossier_total"] == expect_dossier_total
    global_issue_calls = [c for c in kwargs["issue_fn"].call_args_list if "Total dossier count crossed" in c.args[1]]
    assert bool(global_issue_calls) is expect_issue
