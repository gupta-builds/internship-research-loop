"""Task N (Prompt 5) — consecutive-loss tracking and the excluded-uid list.

update_debate_losses is tested as a pure function first (deterministic,
easy to construct exact "4 losses"/"5th loss"/"wins before excluded"
scenarios) — decomposed this way rather than grinding through 5-6 sequential
full run_once() calls with mutable per-round HTTP fixtures, since the three
named behaviors (still-in-pool, excluded-at-threshold, win-resets-count) are
properties of the counting arithmetic itself, not of the surrounding fetch/
validate machinery. A separate, focused integration test then covers the
"skip an already-excluded uid entirely, never even fetch it" guarantee
against the real run_once() pipeline, using pre-seeded state (an uid already
at the exclusion threshold) rather than manufacturing 5 real prior runs.
"""
import json

import run_pipeline
from core.identity import compute_uid
from ingestion.normalize import Listing, normalize_simplify
from test_run_pipeline import PROFILE, _fake_http_get, _run_once_kwargs, _simplify_raw


def _candidate(uid, company="Acme", title="Software Engineer Intern", url=None):
    listing = Listing(company=company, title=title, url=url or f"https://acme.example/{uid}",
                      source="SimplifyJobs", raw_id=uid, date_posted=1700000000)
    return (f"SimplifyJobs:{uid}", listing)


# --- update_debate_losses: pure-function tests ---

def test_deferred_up_to_threshold_minus_one_still_in_pool_not_excluded():
    losses = {}
    deferred = [_candidate("x")]
    for _ in range(run_pipeline.MAX_DEBATE_LOSSES - 1):
        losses, newly_excluded = run_pipeline.update_debate_losses(losses, deferred, written_uids=[])
        assert newly_excluded == []
    assert losses["SimplifyJobs:x"] == run_pipeline.MAX_DEBATE_LOSSES - 1


def test_deferred_nth_time_excludes_and_removes_from_losses():
    losses = {}
    deferred = [_candidate("x")]
    for _ in range(run_pipeline.MAX_DEBATE_LOSSES - 1):
        losses, _ = run_pipeline.update_debate_losses(losses, deferred, written_uids=[])
    losses, newly_excluded = run_pipeline.update_debate_losses(losses, deferred, written_uids=[])
    assert [uid for uid, _listing in newly_excluded] == ["SimplifyJobs:x"]
    assert "SimplifyJobs:x" not in losses  # removed once excluded, not left at threshold


def test_wins_on_attempt_3_never_excluded():
    """Loses twice (deferred), then wins (written) on the third attempt —
    its loss count must be wiped, not merely paused, so a LATER unrelated
    deferral starts counting from zero rather than resuming near threshold."""
    uid, listing = _candidate("x")
    losses = {}
    losses, excluded_1 = run_pipeline.update_debate_losses(losses, [(uid, listing)], written_uids=[])
    losses, excluded_2 = run_pipeline.update_debate_losses(losses, [(uid, listing)], written_uids=[])
    assert losses[uid] == 2
    assert excluded_1 == [] and excluded_2 == []

    # Attempt 3: wins (written), not deferred.
    losses, excluded_3 = run_pipeline.update_debate_losses(losses, deferred=[], written_uids=[uid])
    assert uid not in losses
    assert excluded_3 == []

    # Confirm it never gets excluded even after this reset: 4 more real
    # losses (fewer than MAX_DEBATE_LOSSES) leave it un-excluded.
    for _ in range(4):
        losses, excluded_n = run_pipeline.update_debate_losses(losses, [(uid, listing)], written_uids=[])
        assert excluded_n == []
    assert losses[uid] == 4


def test_should_alert_on_exclusion_spike_threshold():
    """Real incident, 2026-08-21: 287 of 304 total excluded-log entries
    (94%) were excluded on that single day, TikTok alone contributing 106
    — the burst the 20-count threshold is picked to catch. Every other run
    in logs/runs.jsonl carries newly_excluded_count of 0-2, so 20 is
    comfortably above the normal trickle."""
    assert run_pipeline.should_alert_on_exclusion_spike(20) is False
    assert run_pipeline.should_alert_on_exclusion_spike(21) is True
    assert run_pipeline.should_alert_on_exclusion_spike(0) is False


def test_written_uid_not_in_losses_is_a_no_op_pop():
    """A uid that wins without ever having lost before (the common case)
    must not error on the pop — dict.pop(uid, None) already handles this,
    this test just pins the behavior."""
    losses, newly_excluded = run_pipeline.update_debate_losses({}, deferred=[], written_uids=["SimplifyJobs:never-lost"])
    assert losses == {}
    assert newly_excluded == []


# --- fetch_and_filter / dedup_new: excluded uids are skipped ---

def test_fetch_and_filter_skips_excluded_uid():
    real_uid = compute_uid(normalize_simplify(_simplify_raw()[0]))
    results = run_pipeline.fetch_and_filter(PROFILE, http_get=_fake_http_get, excluded_ids=frozenset({real_uid}))
    all_matched_uids = {
        compute_uid(l) for info in results.values() for l in info["matched"]
    }
    assert real_uid not in all_matched_uids


def test_dedup_new_skips_excluded_uid():
    real_uid = compute_uid(normalize_simplify(_simplify_raw()[0]))
    matched_by_source = run_pipeline.fetch_and_filter(PROFILE, http_get=_fake_http_get)
    new_listings, _ = run_pipeline.dedup_new(matched_by_source, seen_ids=set(), excluded_ids=frozenset({real_uid}))
    assert real_uid not in [uid for uid, _listing in new_listings]


# --- integration: an already-excluded uid is never fetched via run_once ---

def test_run_once_never_fetches_an_already_excluded_uid(tmp_path):
    """Pre-seed state/excluded_uids.json with a real candidate's uid already
    at the exclusion threshold (rather than manufacturing 5 real prior
    runs) and confirm a single run_once() never calls fetch_page_fn with
    that candidate's URL — other, non-excluded candidates in the same
    fixture set may still legitimately fetch, so the assertion is scoped to
    the specific excluded listing's own URL, not "never fetched anything"."""
    excluded_listing = normalize_simplify(_simplify_raw()[0])
    real_uid = compute_uid(excluded_listing)
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    (state_dir / run_pipeline.EXCLUDED_UIDS_FILENAME).write_text(json.dumps([real_uid]))

    calls = []

    def guarded_fetch(url):
        calls.append(url)
        if url == excluded_listing.url:
            raise AssertionError("fetched the excluded uid's URL — exclusion did not take effect")
        return ""

    kwargs = _run_once_kwargs(tmp_path, state_dir=state_dir, fetch_page_fn=guarded_fetch)
    record = run_pipeline.run_once(**kwargs)

    assert excluded_listing.url not in calls
    assert record["errors"] == []


def test_run_once_files_issue_on_exclusion_spike(tmp_path, monkeypatch):
    """Integration-level confirmation that run_once actually wires
    should_alert_on_exclusion_spike to issue_fn — the threshold logic
    itself is covered by the pure-function test above, so this only needs
    to prove the two are connected. update_debate_losses is monkeypatched
    to return 25 fake newly-excluded candidates rather than manufacturing
    5 real prior runs across 25+ distinct fixture listings."""
    from ingestion.normalize import Listing

    def fake_update_debate_losses(losses, deferred, written_uids):
        fake_excluded = [
            (f"SimplifyJobs:spike-{i}", Listing(company="Acme", title="SWE Intern",
                                                 url=f"https://acme.example/{i}", source="SimplifyJobs"))
            for i in range(25)
        ]
        return losses, fake_excluded

    monkeypatch.setattr(run_pipeline, "update_debate_losses", fake_update_debate_losses)
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    kwargs = _run_once_kwargs(tmp_path, state_dir=state_dir)
    record = run_pipeline.run_once(**kwargs)

    assert record["newly_excluded_count"] == 25
    spike_calls = [c for c in kwargs["issue_fn"].call_args_list if "exclusion spike" in c.args[1]]
    assert len(spike_calls) == 1
    assert "25 candidates crossed" in spike_calls[0].args[2]
