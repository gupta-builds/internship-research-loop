"""_union_json_list and _merge_dict_json are reseed.py's whole merge-back
decision surface for the two respective state-file shapes (a uid list vs. a
uid-keyed dict) — the one piece that must be correct, or a newly-written uid
never reaches the real state/seen_ids.json and becomes a repeat squatter in
the very next run.yml run (the exact write-starvation bug the 2026-08-26
postmortem found).

test_run_reseed_end_to_end_* below then exercises run_reseed() itself against
the real run_pipeline.run_once() with the same fakes tests/test_run_pipeline.py
already uses — proving the seed-then-merge behavior actually happens through
the real orchestration, not just in the two helper functions in isolation."""
import json
from datetime import datetime, timezone
from unittest.mock import Mock

import run_pipeline
from core.identity import compute_uid
from ingestion.normalize import normalize_simplify
from reseed import _merge_dict_json, _union_json_list, run_reseed
from test_run_pipeline import PROFILE, _fake_http_get, _fake_http_head_all_live, _simplify_raw


def test_unions_scratch_and_real_ids(tmp_path):
    scratch = tmp_path / "scratch.json"
    real = tmp_path / "real.json"
    scratch.write_text(json.dumps(["SimplifyJobs:new1", "SimplifyJobs:new2"]))
    real.write_text(json.dumps(["SimplifyJobs:old1"]))

    _union_json_list(scratch, real)

    assert json.loads(real.read_text()) == ["SimplifyJobs:new1", "SimplifyJobs:new2", "SimplifyJobs:old1"]


def test_missing_real_file_is_created_from_scratch(tmp_path):
    scratch = tmp_path / "scratch.json"
    real = tmp_path / "nested" / "real.json"
    scratch.write_text(json.dumps(["SimplifyJobs:new1"]))

    _union_json_list(scratch, real)

    assert json.loads(real.read_text()) == ["SimplifyJobs:new1"]


def test_missing_scratch_file_leaves_real_ids_untouched(tmp_path):
    scratch = tmp_path / "scratch.json"  # never created
    real = tmp_path / "real.json"
    real.write_text(json.dumps(["SimplifyJobs:old1"]))

    _union_json_list(scratch, real)

    assert json.loads(real.read_text()) == ["SimplifyJobs:old1"]


def test_merge_dict_json_scratch_wins_on_collision(tmp_path):
    scratch = tmp_path / "scratch.json"
    real = tmp_path / "real.json"
    scratch.write_text(json.dumps({"SimplifyJobs:a": {"verdict": "eligible", "signal": None, "checked": "2026-09-07"}}))
    real.write_text(json.dumps({
        "SimplifyJobs:a": {"verdict": "excluded", "signal": "stale", "checked": "2026-01-01"},
        "SimplifyJobs:b": {"verdict": "excluded", "signal": "OPT", "checked": "2026-01-01"},
    }))

    _merge_dict_json(scratch, real)

    merged = json.loads(real.read_text())
    assert merged["SimplifyJobs:a"]["verdict"] == "eligible"  # scratch's fresher verdict wins
    assert merged["SimplifyJobs:b"]["verdict"] == "excluded"  # untouched real-only entry preserved


def test_merge_dict_json_missing_scratch_leaves_real_untouched(tmp_path):
    scratch = tmp_path / "scratch.json"  # never created
    real = tmp_path / "real.json"
    real.write_text(json.dumps({"SimplifyJobs:b": {"verdict": "excluded", "signal": "OPT", "checked": "2026-01-01"}}))

    _merge_dict_json(scratch, real)

    assert json.loads(real.read_text()) == {"SimplifyJobs:b": {"verdict": "excluded", "signal": "OPT", "checked": "2026-01-01"}}


def _page_with(text):
    return f"# Great Intern Job\nRole details here.\n{text}\nMore details."


def test_run_reseed_end_to_end_merges_state_and_respects_seeded_opt_cache(tmp_path):
    """Seeds a real state/ dir with a pre-existing excluded_uids.json entry
    and a pre-existing opt_cache.json cached-excluded verdict for a real
    fixture uid, runs run_reseed() against the same fakes
    tests/test_run_pipeline.py uses, and checks the real state/ afterward:
    the cached-excluded uid was never re-fetched or written, the pre-existing
    excluded_uids.json entry survived, and newly-written uids/verdicts landed
    in the real seen_ids.json/opt_cache.json."""
    real_state_dir = tmp_path / "state"
    real_state_dir.mkdir()

    pre_existing_excluded_uid = "SimplifyJobs:pre-existing-dead-link"
    (real_state_dir / run_pipeline.EXCLUDED_UIDS_FILENAME).write_text(json.dumps([pre_existing_excluded_uid]))

    cached_listing = normalize_simplify(_simplify_raw()[0])
    cached_uid = compute_uid(cached_listing)
    (real_state_dir / "opt_cache.json").write_text(json.dumps({
        cached_uid: {"verdict": "excluded", "signal": "U.S. Person status is required", "checked": "2026-01-01"},
    }))

    def fake_fetch_page(url):
        if url == cached_listing.url:
            raise AssertionError("must not fetch a posting cached as opt_eligibility-excluded")
        return _page_with("Great role. Qualifications: Python.")

    jarvis_dir = tmp_path / "jarvis"
    jarvis_dir.mkdir()

    result = run_reseed(
        jarvis_dir=jarvis_dir,
        real_state_dir=real_state_dir,
        runs_log_path=tmp_path / "logs" / "reseed_runs.jsonl",
        now=datetime(2026, 7, 17, 15, 0, tzinfo=timezone.utc),
        fetch_page_fn=fake_fetch_page,
        profile=PROFILE,
        http_get=_fake_http_get,
        http_head=_fake_http_head_all_live,
        push_fn=lambda repo_dir, message: True,
        issue_fn=Mock(),
    )

    assert result["written_count"] > 0
    assert not result["halted"]

    seen_after = json.loads((real_state_dir / "seen_ids.json").read_text())
    assert cached_uid not in seen_after  # cached-excluded uid was never written
    assert len(seen_after) == result["written_count"]  # merge-back reached the real file exactly

    excluded_after = json.loads((real_state_dir / run_pipeline.EXCLUDED_UIDS_FILENAME).read_text())
    assert pre_existing_excluded_uid in excluded_after  # pre-existing entry survived the merge

    opt_cache_after = json.loads((real_state_dir / "opt_cache.json").read_text())
    assert opt_cache_after[cached_uid]["verdict"] == "excluded"  # pre-existing cached verdict survived
    assert any(
        v["verdict"] == "eligible" for k, v in opt_cache_after.items() if k != cached_uid
    )  # this run's own fresh verdict merged in
