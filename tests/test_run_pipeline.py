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


def _fake_http_get(url, timeout=None):
    from ingestion.sources import JOSEGAEL_URL, SIMPLIFY_URL

    resp = Mock(status_code=200)
    if url == SIMPLIFY_URL:
        resp.json.return_value = _simplify_raw()
    elif url == JOSEGAEL_URL:
        resp.json.return_value = _josegael_raw()
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
    assert any(dossiers_dir.glob("*.md"))


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
    assert not list(dossiers_dir.glob("*.md")) if dossiers_dir.exists() else True


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
    assert len(list(dossiers_dir.glob("*.md"))) == record["written_count"]

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
    assert not dossiers_dir.exists() or not list(dossiers_dir.glob("*.md"))
    kwargs["issue_fn"].assert_called_once()
    assert "Schema drift" in kwargs["issue_fn"].call_args[0][1]


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
    assert len(list(dossiers_dir.glob("*.md"))) > 0

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


def test_run_once_second_run_does_not_rewrite_already_seen_items(tmp_path):
    kwargs = _run_once_kwargs(tmp_path)
    first = run_pipeline.run_once(**kwargs)
    assert first["written_count"] > 0

    kwargs2 = _run_once_kwargs(tmp_path, jarvis_dir=kwargs["jarvis_dir"])
    kwargs2["state_path"] = kwargs["state_path"]
    kwargs2["runs_log_path"] = kwargs["runs_log_path"]
    second = run_pipeline.run_once(**kwargs2)

    assert second["written_count"] == 0
    assert second["already_seen_count"] == first["written_count"] + first["already_seen_count"]
