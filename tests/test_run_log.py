from datetime import datetime

from core.run_log import (
    append_run_log,
    append_weekly_rollup,
    format_weekly_rollup,
    load_recent_runs,
    should_run_weekly_rollup,
)


def _ts(s):
    return datetime.fromisoformat(s)


def test_append_run_log_writes_one_json_line_per_call(tmp_path):
    path = tmp_path / "logs" / "runs.jsonl"
    append_run_log(path, {"timestamp": "2026-07-17T10:00:00+00:00", "written_count": 2})
    append_run_log(path, {"timestamp": "2026-07-17T11:00:00+00:00", "written_count": 1})

    lines = path.read_text().splitlines()
    assert len(lines) == 2
    import json

    assert json.loads(lines[0])["written_count"] == 2
    assert json.loads(lines[1])["written_count"] == 1


def test_load_recent_runs_filters_by_timestamp(tmp_path):
    path = tmp_path / "runs.jsonl"
    append_run_log(path, {"timestamp": "2026-07-01T00:00:00+00:00", "written_count": 5})
    append_run_log(path, {"timestamp": "2026-07-16T00:00:00+00:00", "written_count": 3})
    append_run_log(path, {"timestamp": "2026-07-17T00:00:00+00:00", "written_count": 1})

    recent = load_recent_runs(path, since=_ts("2026-07-15T00:00:00+00:00"))
    assert [r["written_count"] for r in recent] == [3, 1]


def test_load_recent_runs_on_missing_file_returns_empty(tmp_path):
    assert load_recent_runs(tmp_path / "nope.jsonl", since=_ts("2026-01-01T00:00:00+00:00")) == []


def test_should_run_weekly_rollup_only_fires_sunday_2300_utc():
    assert should_run_weekly_rollup(_ts("2026-07-19T23:00:00+00:00")) is True  # a Sunday
    assert should_run_weekly_rollup(_ts("2026-07-19T22:00:00+00:00")) is False  # wrong hour
    assert should_run_weekly_rollup(_ts("2026-07-18T23:00:00+00:00")) is False  # a Saturday


def test_format_weekly_rollup_aggregates_written_and_rejections():
    records = [
        {
            "written_count": 3,
            "halted": False,
            "rejections": [{"check": "url_liveness"}, {"check": "url_liveness"}],
        },
        {
            "written_count": 2,
            "halted": False,
            "rejections": [{"check": "not_duplicate"}],
        },
        {"written_count": 0, "halted": True, "rejections": []},
    ]
    line = format_weekly_rollup(records, _ts("2026-07-13T00:00:00+00:00"), _ts("2026-07-20T00:00:00+00:00"))

    assert "2026-07-13 to 2026-07-20" in line
    assert "5 dossiers written" in line
    assert "3 rejections" in line
    assert "url_liveness: 2" in line
    assert "not_duplicate: 1" in line
    assert "1 halted run(s)" in line
    assert "3 run(s) total" in line


def test_format_weekly_rollup_handles_zero_activity():
    line = format_weekly_rollup([], _ts("2026-07-13T00:00:00+00:00"), _ts("2026-07-20T00:00:00+00:00"))
    assert "0 dossiers written" in line
    assert "0 rejections (none)" in line


def test_append_weekly_rollup_creates_file_with_header(tmp_path):
    path = tmp_path / "Run Log.md"
    append_weekly_rollup(path, "- **2026-07-13 to 2026-07-20**: 5 dossiers written", created_date="2026-07-17")

    text = path.read_text()
    assert text.startswith("---\n")
    assert "type: dashboard" in text
    assert "created: 2026-07-17" in text
    assert text.rstrip("\n").endswith("5 dossiers written")


def test_append_weekly_rollup_appends_without_rewriting(tmp_path):
    path = tmp_path / "Run Log.md"
    append_weekly_rollup(path, "- week 1 line", created_date="2026-07-17")
    append_weekly_rollup(path, "- week 2 line", created_date="2026-07-17")

    text = path.read_text()
    assert "- week 1 line" in text
    assert "- week 2 line" in text
    # week 1's line must still be present verbatim — appended, not rewritten
    lines = [l for l in text.splitlines() if l.startswith("- week")]
    assert lines == ["- week 1 line", "- week 2 line"]


def test_appended_run_log_note_has_no_blank_lines_or_stray_dashes(tmp_path):
    """Not a Dossier (doesn't go through validate.validate()'s dossier-specific
    frontmatter checks), but it's still an Obsidian note the vault's
    zero-blank-line and no-stray-'---' body rules apply to."""
    path = tmp_path / "Run Log.md"
    append_weekly_rollup(path, "- **2026-07-13 to 2026-07-20**: 5 dossiers written", created_date="2026-07-17")
    append_weekly_rollup(path, "- **2026-07-20 to 2026-07-27**: 2 dossiers written", created_date="2026-07-17")

    lines = path.read_text().splitlines()
    closing_idx = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    body_lines = lines[closing_idx + 1:]

    assert body_lines[0].strip() != ""  # no blank line between frontmatter close and title
    assert not any(l.strip() == "" for l in body_lines)  # zero blank lines anywhere in the body
    assert not any(l.strip() == "---" for l in body_lines)  # no '---' used as a body separator
