#!/usr/bin/env python3
"""Daily post-write liveness recheck. Scans the dossier files actually present
in the vault checkout (file existence is the truth — seen_ids.json diverged
from the vault after the 2026-07-18 manual cleanup and stays untouched here),
cross-refs each against its source's live feed, and moves any dossier whose
posting is now inactive or gone from the feed entirely into Viewed/ (never
deletes — Internship Notes Standard §4: a closed posting's history is real
information). Runs on its own daily cron (.github/workflows/recheck.yml) —
postings don't close often enough to justify rechecking every hour.

    JARVIS_DIR=... python recheck.py [--dry-run]
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.git_ops import GitPushError, commit_and_push_with_retry
from core.run_log import append_run_log
from ingestion.sources import (
    fetch_ai_jobs,
    fetch_ashby,
    fetch_greenhouse,
    fetch_josegael,
    fetch_lever,
    fetch_simplify,
    fetch_vanshb03,
    fetch_zshah101,
)
from run_pipeline import file_github_issue
from vault_writer.writer import load_dossier_uids, move_dossier_to_viewed, scan_dossiers

# 2026-07-25: was still SimplifyJobs/JGCL only after the 4-source batch shipped
# earlier the same day — dossiers from vanshb03/zshah101/Greenhouse/Ashby were
# silently never rechecked. Greenhouse/Ashby/Lever/AIJobs never expose an
# active:false flag (their public APIs only ever return currently-open jobs —
# Lever added 2026-08-24, same per-company postings-list shape, confirmed no
# closed postings appear in a live query), so for those four "absent from
# feed" is the only closure signal there is — which is exactly the existing
# absent-from-feed branch below, no special-casing needed. Freehire is
# deliberately NOT here: checked live,
# its own closed_at field lags real closures by days (see
# ingestion/freehire.py's docstring) and the posting stays present in a
# fresh company-scoped query even after it's actually closed — "absent from
# feed" wouldn't be a real signal for it, so adding it would be false
# confidence, not real coverage.
FEEDS = {
    "SimplifyJobs": fetch_simplify,
    "Jose-Gael-Cruz-Lopez": fetch_josegael,
    "vanshb03": fetch_vanshb03,
    "zshah101": fetch_zshah101,
    "Greenhouse": fetch_greenhouse,
    "Ashby": fetch_ashby,
    "Lever": fetch_lever,
    "AIJobs": fetch_ai_jobs,
}
RECHECKS_LOG = Path(__file__).parent / "logs" / "rechecks.jsonl"
STATE_DIR = Path(__file__).parent / "state"
ISSUE_REPO = "gupta-builds/internship-research-loop"


def plan_removals(dossiers: list, feeds_by_source: dict, uid_by_path: dict, jarvis_dir) -> list:
    """[{uid, path, reason}] for dossiers whose posting closed. A source that
    failed to fetch is absent from feeds_by_source — its dossiers are skipped
    entirely, never treated as gone. A dossier with no dossier_uids.json
    manifest entry (written before the manifest existed, or hand-edited into
    the vault, e.g. Software Engineer - Ellipsis Labs.md) is skipped too —
    unknown means leave alone, not removable. A dossier already moved to
    Viewed/ (status: removed) is skipped too — real, reproducible bug found
    2026-08-23: scan_dossiers() globs Viewed/ along with every live bucket (by
    design, for cross-source dedup), so a dossier that stayed closed kept
    getting swept up here again on every subsequent run and re-moved via
    move_dossier_to_viewed(), which — finding the base filename already taken
    by itself — wrote a new '(2)', '(3)', ... suffixed copy and deleted the
    original every single day. Confirmed live: all 4 real dossiers in Viewed/
    as of 2026-08-23 already carried a spurious '(2)' suffix from this."""
    removals = []
    jarvis_dir = Path(jarvis_dir)
    for fm in dossiers:
        if fm.get("status") == "removed":
            continue
        uid = uid_by_path.get(str(fm["_path"].relative_to(jarvis_dir)))
        if uid is None:
            continue
        source, _, raw_id = uid.partition(":")
        if source not in feeds_by_source:
            continue
        active_by_id = feeds_by_source[source]
        if raw_id not in active_by_id:
            removals.append({"uid": uid, "path": fm["_path"], "reason": "absent from live feed"})
        elif active_by_id[raw_id] is False:
            removals.append({"uid": uid, "path": fm["_path"], "reason": "active: false upstream"})
    return removals


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report removals, delete nothing")
    args = ap.parse_args()
    jarvis_dir = os.environ["JARVIS_DIR"]
    now = datetime.now(timezone.utc)

    dossiers = scan_dossiers(jarvis_dir)
    uid_by_path = load_dossier_uids(STATE_DIR)

    feeds_by_source, errors = {}, []
    for source, fetch_fn in FEEDS.items():
        try:
            feeds_by_source[source] = {l.raw_id: l.active for l in fetch_fn()}
        except Exception as exc:  # fetch failure must not read as "everything absent"
            errors.append(f"{source} fetch failed, its dossiers skipped: {exc}")

    removals = plan_removals(dossiers, feeds_by_source, uid_by_path, jarvis_dir)
    record = {
        "timestamp": now.isoformat(),
        "type": "recheck",
        "scanned": len(dossiers),
        "removals": [{"uid": r["uid"], "reason": r["reason"]} for r in removals],
        "errors": errors,
        "halted": False,
        "halt_reason": None,
    }

    # ponytail: crude mass-move brake — a truncated/glitched feed must not
    # empty the vault into Viewed/. Threshold is arbitrary but safe; tune if it
    # ever trips wrongly. Same protective logic as before this was a move
    # instead of a delete — the risk (a feed glitch wiping real dossiers out
    # of the live buckets) is identical either way.
    if len(removals) > max(5, len(dossiers) // 2):
        record["halted"] = True
        record["halt_reason"] = f"would move {len(removals)} of {len(dossiers)} dossiers to Viewed/ — feed glitch?"
        if not args.dry_run:
            _commit_log(record, now)
            file_github_issue(
                ISSUE_REPO,
                f"Recheck halted: mass-move brake at {now.isoformat()}",
                f"{record['halt_reason']}\n\nNothing was moved. Removal list:\n"
                + "\n".join(f"- `{r['uid']}`: {r['reason']}" for r in removals),
            )
        print(record["halt_reason"])
        sys.exit(1)

    for r in removals:
        print(f"{'would move' if args.dry_run else 'moving'}: {r['uid']} — {r['reason']}")
    if args.dry_run:
        print(f"dry run: {len(removals)} of {len(dossiers)} would be moved to Viewed/")
        return

    if removals:
        for r in removals:
            move_dossier_to_viewed(
                jarvis_dir, r["path"], r["reason"], now.date().isoformat(), state_dir=STATE_DIR
            )
        try:
            commit_and_push_with_retry(
                jarvis_dir, f"Move {len(removals)} closed posting(s) to Viewed/ — recheck {now.date().isoformat()}"
            )
        except GitPushError as exc:
            record["errors"].append(f"Jarvis push failed: {exc}")
            file_github_issue(
                ISSUE_REPO,
                f"Recheck push to Jarvis failed at {now.isoformat()}",
                f"Removals were made in the checkout but the push failed after retry:\n\n```\n{exc}\n```",
            )
    _commit_log(record, now)
    print(f"moved {len(removals)} of {len(dossiers)} dossiers to Viewed/; {len(errors)} fetch error(s)")
    if record["errors"]:
        sys.exit(1)


def _commit_log(record: dict, now: datetime) -> None:
    append_run_log(RECHECKS_LOG, record)
    commit_and_push_with_retry(Path(__file__).parent, f"Recheck log — {now.date().isoformat()}")


if __name__ == "__main__":
    main()
