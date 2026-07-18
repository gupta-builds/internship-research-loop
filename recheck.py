#!/usr/bin/env python3
"""Daily post-write liveness recheck. Scans the dossier files actually present
in the vault checkout (file existence is the truth — seen_ids.json diverged
from the vault after the 2026-07-18 manual cleanup and stays untouched here),
cross-refs each against its source's live feed, and removes any dossier whose
posting is now inactive or gone from the feed entirely. Runs on its own daily
cron (.github/workflows/recheck.yml) — postings don't close often enough to
justify rechecking every hour.

    JARVIS_DIR=... python recheck.py [--dry-run]
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.git_ops import GitPushError, commit_and_push_with_retry
from core.run_log import append_run_log
from ingestion.sources import fetch_josegael, fetch_simplify
from run_pipeline import file_github_issue
from vault_writer.writer import scan_dossiers

FEEDS = {
    "SimplifyJobs": fetch_simplify,
    "Jose-Gael-Cruz-Lopez": fetch_josegael,
}
RECHECKS_LOG = Path(__file__).parent / "logs" / "rechecks.jsonl"
ISSUE_REPO = "gupta-builds/internship-research-loop"


def plan_removals(dossiers: list, feeds_by_source: dict) -> list:
    """[{uid, path, reason}] for dossiers whose posting closed. A source that
    failed to fetch is absent from feeds_by_source — its dossiers are skipped
    entirely, never treated as gone."""
    removals = []
    for fm in dossiers:
        source, _, raw_id = fm["uid"].partition(":")
        if source not in feeds_by_source:
            continue
        active_by_id = feeds_by_source[source]
        if raw_id not in active_by_id:
            removals.append({"uid": fm["uid"], "path": fm["_path"], "reason": "absent from live feed"})
        elif active_by_id[raw_id] is False:
            removals.append({"uid": fm["uid"], "path": fm["_path"], "reason": "active: false upstream"})
    return removals


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report removals, delete nothing")
    args = ap.parse_args()
    jarvis_dir = os.environ["JARVIS_DIR"]
    now = datetime.now(timezone.utc)

    dossiers = scan_dossiers(jarvis_dir)

    feeds_by_source, errors = {}, []
    for source, fetch_fn in FEEDS.items():
        try:
            feeds_by_source[source] = {l.raw_id: l.active for l in fetch_fn()}
        except Exception as exc:  # fetch failure must not read as "everything absent"
            errors.append(f"{source} fetch failed, its dossiers skipped: {exc}")

    removals = plan_removals(dossiers, feeds_by_source)
    record = {
        "timestamp": now.isoformat(),
        "type": "recheck",
        "scanned": len(dossiers),
        "removals": [{"uid": r["uid"], "reason": r["reason"]} for r in removals],
        "errors": errors,
        "halted": False,
        "halt_reason": None,
    }

    # ponytail: crude mass-deletion brake — a truncated/glitched feed must not
    # wipe the vault. Threshold is arbitrary but safe; tune if it ever trips wrongly.
    if len(removals) > max(5, len(dossiers) // 2):
        record["halted"] = True
        record["halt_reason"] = f"would remove {len(removals)} of {len(dossiers)} dossiers — feed glitch?"
        if not args.dry_run:
            _commit_log(record, now)
            file_github_issue(
                ISSUE_REPO,
                f"Recheck halted: mass-deletion brake at {now.isoformat()}",
                f"{record['halt_reason']}\n\nNothing was removed. Removal list:\n"
                + "\n".join(f"- `{r['uid']}`: {r['reason']}" for r in removals),
            )
        print(record["halt_reason"])
        sys.exit(1)

    for r in removals:
        print(f"{'would remove' if args.dry_run else 'removing'}: {r['uid']} — {r['reason']}")
    if args.dry_run:
        print(f"dry run: {len(removals)} of {len(dossiers)} would be removed")
        return

    if removals:
        for r in removals:
            Path(r["path"]).unlink()
        try:
            commit_and_push_with_retry(
                jarvis_dir, f"Remove {len(removals)} closed posting(s) — recheck {now.date().isoformat()}"
            )
        except GitPushError as exc:
            record["errors"].append(f"Jarvis push failed: {exc}")
            file_github_issue(
                ISSUE_REPO,
                f"Recheck push to Jarvis failed at {now.isoformat()}",
                f"Removals were made in the checkout but the push failed after retry:\n\n```\n{exc}\n```",
            )
    _commit_log(record, now)
    print(f"removed {len(removals)} of {len(dossiers)} dossiers; {len(errors)} fetch error(s)")
    if record["errors"]:
        sys.exit(1)


def _commit_log(record: dict, now: datetime) -> None:
    append_run_log(RECHECKS_LOG, record)
    commit_and_push_with_retry(Path(__file__).parent, f"Recheck log — {now.date().isoformat()}")


if __name__ == "__main__":
    main()
