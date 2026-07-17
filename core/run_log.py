"""Two-tier run log per the plan: raw per-run JSONL in this repo, a weekly
markdown rollup appended (never rewritten) into the Jarvis vault.
"""
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROLLUP_WEEKDAY = 6  # Sunday (datetime.weekday(): Monday=0 .. Sunday=6)
ROLLUP_HOUR = 23  # UTC, matches the hourly cron


def append_run_log(runs_jsonl_path, record: dict) -> None:
    path = Path(runs_jsonl_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def load_recent_runs(runs_jsonl_path, since: datetime) -> list:
    path = Path(runs_jsonl_path)
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        ts = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
        if ts >= since:
            records.append(record)
    return records


def should_run_weekly_rollup(now: datetime) -> bool:
    return now.weekday() == ROLLUP_WEEKDAY and now.hour == ROLLUP_HOUR


def format_weekly_rollup(records: list, week_start: datetime, week_end: datetime) -> str:
    written = sum(r.get("written_count", 0) for r in records)
    halted = sum(1 for r in records if r.get("halted"))
    reason_counts = Counter(
        rej.get("check", "unknown") for r in records for rej in r.get("rejections", [])
    )
    reasons_str = ", ".join(f"{k}: {v}" for k, v in sorted(reason_counts.items())) or "none"
    date_fmt = "%Y-%m-%d"
    return (
        f"- **{week_start.strftime(date_fmt)} to {week_end.strftime(date_fmt)}**: "
        f"{written} dossiers written, {sum(reason_counts.values())} rejections ({reasons_str}), "
        f"{halted} halted run(s), {len(records)} run(s) total"
    )


_HEADER_TEMPLATE = """---
type: dashboard
status: active
created: {created}
tags:
  - internship
  - automation
  - run-log
---
# Internship Research Loop — Run Log
Weekly rollup from the internship-research-loop automation, appended automatically — not rewritten. Raw per-run data lives in that repo's logs/runs.jsonl.
"""


def append_weekly_rollup(run_log_md_path, line: str, created_date: str) -> None:
    path = Path(run_log_md_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        header = _HEADER_TEMPLATE.format(created=created_date).rstrip("\n") + "\n"
        path.write_text(header + line + "\n")
        return
    existing = path.read_text()
    if not existing.endswith("\n"):
        existing += "\n"
    path.write_text(existing + line + "\n")
