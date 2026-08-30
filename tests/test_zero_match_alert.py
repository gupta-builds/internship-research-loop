"""Task 3 (Prompt 19, 2026-08-28) — per-source zero-match-rate alert.

Same "pure function first, integration test proves the wiring" decomposition
as tests/test_debate_losses.py: update_zero_match_streaks's counting rules
are properties of the counting arithmetic itself, easiest pinned directly;
a separate integration test then only needs to confirm run_once actually
calls issue_fn when the threshold is crossed.
"""
import json

import run_pipeline
from test_run_pipeline import _run_once_kwargs


# --- update_zero_match_streaks: pure-function tests ---

def test_zero_match_streak_increments_while_fetching_but_not_matching():
    streaks = {}
    for i in range(1, 4):
        streaks, alerting = run_pipeline.update_zero_match_streaks(streaks, {"Ashby": 4}, {"Ashby": 0})
        assert alerting == []
        assert streaks["Ashby"]["streak"] == i


def test_zero_match_streak_never_alerts_if_source_never_matched():
    """A source that has never once produced a match isn't drifting, it's
    just structurally not matching anything — no alert, ever, no matter how
    long the streak runs, until it proves it CAN match at least once."""
    streaks = {}
    for _ in range(run_pipeline.ZERO_MATCH_STREAK_ALERT_THRESHOLD + 5):
        streaks, alerting = run_pipeline.update_zero_match_streaks(streaks, {"NewSource": 2}, {"NewSource": 0})
        assert alerting == []
    assert streaks["NewSource"]["ever_matched"] is False
    assert streaks["NewSource"]["streak"] == run_pipeline.ZERO_MATCH_STREAK_ALERT_THRESHOLD + 5


def test_zero_match_streak_fires_exactly_once_at_threshold():
    streaks = {"Ashby": {"streak": 0, "ever_matched": True}}
    fired_runs = []
    for i in range(1, run_pipeline.ZERO_MATCH_STREAK_ALERT_THRESHOLD + 3):
        streaks, alerting = run_pipeline.update_zero_match_streaks(streaks, {"Ashby": 4}, {"Ashby": 0})
        if alerting:
            fired_runs.append(i)
    assert fired_runs == [run_pipeline.ZERO_MATCH_STREAK_ALERT_THRESHOLD]  # only once, not every run after


def test_zero_match_streak_resets_on_a_real_match_and_marks_ever_matched():
    streaks = {}
    streaks, _ = run_pipeline.update_zero_match_streaks(streaks, {"Lever": 3}, {"Lever": 0})
    streaks, _ = run_pipeline.update_zero_match_streaks(streaks, {"Lever": 3}, {"Lever": 0})
    assert streaks["Lever"]["streak"] == 2

    streaks, alerting = run_pipeline.update_zero_match_streaks(streaks, {"Lever": 3}, {"Lever": 1})
    assert alerting == []
    assert streaks["Lever"]["streak"] == 0
    assert streaks["Lever"]["ever_matched"] is True


def test_zero_match_streak_unaffected_by_a_zero_fetch_run():
    """A single fetch hiccup (fetch_count == 0, e.g. a swallowed
    RequestException) neither advances nor resets an in-progress streak."""
    streaks = {"Ashby": {"streak": 5, "ever_matched": True}}
    streaks, alerting = run_pipeline.update_zero_match_streaks(streaks, {"Ashby": 0}, {"Ashby": 0})
    assert alerting == []
    assert streaks["Ashby"]["streak"] == 5


def test_zero_match_streak_real_ashby_incident_shape():
    """Pins the real, concrete incident this task was built from (Prompt 19
    Task 1): fetch_count frozen at 4, filter_match_count frozen at 0, for
    115 consecutive runs — confirms the alert threshold (24) would have
    fired well before a human noticed at run 115."""
    streaks = {}
    alert_runs = []
    for i in range(1, 116):
        streaks, alerting = run_pipeline.update_zero_match_streaks(
            {**streaks, "Ashby": {"streak": streaks.get("Ashby", {}).get("streak", 0), "ever_matched": True}},
            {"Ashby": 4}, {"Ashby": 0},
        )
        if alerting:
            alert_runs.append(i)
    assert alert_runs == [run_pipeline.ZERO_MATCH_STREAK_ALERT_THRESHOLD]
    assert alert_runs[0] < 115


def test_load_save_zero_match_streaks_round_trips(tmp_path):
    state_dir = tmp_path / "state"
    run_pipeline.save_zero_match_streaks(state_dir, {"Ashby": {"streak": 3, "ever_matched": True}})
    assert run_pipeline.load_zero_match_streaks(state_dir) == {"Ashby": {"streak": 3, "ever_matched": True}}


def test_load_zero_match_streaks_missing_file_returns_empty_dict(tmp_path):
    assert run_pipeline.load_zero_match_streaks(tmp_path / "state") == {}


# --- integration: run_once wires update_zero_match_streaks to issue_fn ---

def test_run_once_files_issue_and_persists_state_on_zero_match_streak(tmp_path, monkeypatch):
    """Integration-level confirmation that run_once actually calls issue_fn
    once the persisted streak crosses the threshold — the counting logic
    itself is covered by the pure-function tests above, this only proves
    the two are wired together and that state persists across calls."""
    monkeypatch.setattr(run_pipeline, "check_schema_drift", lambda http_get=None: None)
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    run_pipeline.save_zero_match_streaks(
        state_dir, {"Ashby": {"streak": run_pipeline.ZERO_MATCH_STREAK_ALERT_THRESHOLD - 1, "ever_matched": True}},
    )

    def fake_fetch_and_filter(profile, http_get=None, excluded_ids=frozenset()):
        return {"Ashby": {"fetch_count": 4, "matched": []}}

    monkeypatch.setattr(run_pipeline, "fetch_and_filter", fake_fetch_and_filter)
    kwargs = _run_once_kwargs(tmp_path, state_dir=state_dir)
    record = run_pipeline.run_once(**kwargs)

    assert record["zero_match_alerts"] == ["Ashby"]
    alert_calls = [c for c in kwargs["issue_fn"].call_args_list if "stuck at 0" in c.args[1]]
    assert len(alert_calls) == 1
    assert "Ashby" in alert_calls[0].args[1]

    persisted = run_pipeline.load_zero_match_streaks(state_dir)
    assert persisted["Ashby"]["streak"] == run_pipeline.ZERO_MATCH_STREAK_ALERT_THRESHOLD


def test_run_once_does_not_alert_below_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr(run_pipeline, "check_schema_drift", lambda http_get=None: None)
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)

    def fake_fetch_and_filter(profile, http_get=None, excluded_ids=frozenset()):
        return {"Ashby": {"fetch_count": 4, "matched": []}}

    monkeypatch.setattr(run_pipeline, "fetch_and_filter", fake_fetch_and_filter)
    kwargs = _run_once_kwargs(tmp_path, state_dir=state_dir)
    record = run_pipeline.run_once(**kwargs)

    assert record["zero_match_alerts"] == []
    assert not any("stuck at 0" in c.args[1] for c in kwargs["issue_fn"].call_args_list)
