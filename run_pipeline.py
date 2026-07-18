"""Phase 3 orchestration: schema-drift check -> fetch -> filter -> dedup ->
validate -> write (Jarvis checkout) -> push (Jarvis, retry-safe) -> mark seen
ONLY on confirmed push -> run log -> push (this repo) -> GH issue on
schema-drift, push failure, or a systemic (not routine) write-gate rejection.

Invoked by .github/workflows/run.yml as `python run_pipeline.py`.
"""
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.filter import load_profile, matches
from core.git_ops import GitPushError, commit_and_push_with_retry
from core.identity import compute_uid
from core.run_log import (
    append_run_log,
    append_weekly_rollup,
    format_weekly_rollup,
    load_recent_runs,
    should_run_weekly_rollup,
)
from core.identity import cross_source_key
from core.schema_drift import SchemaDriftError
from core.schema_drift import check_all as check_schema_drift
from ingestion.sources import fetch_josegael, fetch_simplify
from vault_writer.validate import validate
from vault_writer.writer import render_dossier, scan_dossiers, write_dossier

SOURCES = (
    ("SimplifyJobs", fetch_simplify),
    ("Jose-Gael-Cruz-Lopez", fetch_josegael),
)

RUN_LOG_MD_SUBPATH = Path("10_Areas/Career/Internships/List/Run Log.md")

# A required_fields or format_compliance rejection means OUR normalizer/writer
# produced something malformed — a real bug, worth an issue. url_liveness and
# not_duplicate rejections are routine (a stale posting, an already-seen item)
# and would spam an issue on every ordinary run if treated the same way.
SYSTEMIC_REJECTION_CHECKS = {"required_fields", "format_compliance"}


def load_seen_ids(state_path) -> set:
    path = Path(state_path)
    if not path.exists():
        return set()
    return set(json.loads(path.read_text()))


def save_seen_ids(state_path, seen_ids: set) -> None:
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(seen_ids), indent=2) + "\n")


def build_matched_reason(listing, profile: dict) -> str:
    if listing.source == "SimplifyJobs":
        term = ", ".join(sorted(set(listing.terms) & set(profile["terms"])))
        return f"{term}, {listing.category}" if listing.category else term
    if listing.source == "Jose-Gael-Cruz-Lopez":
        return "Junior-eligible" if listing.target_year else "unrestricted (no class-year field)"
    return "matched"


def fetch_and_filter(profile: dict, http_get=None) -> dict:
    """Returns {source_name: {"fetch_count": int, "matched": [Listing, ...]}}."""
    results = {}
    for name, fetch_fn in SOURCES:
        listings = fetch_fn(http_get)
        results[name] = {"fetch_count": len(listings), "matched": [l for l in listings if matches(l, profile)]}
    return results


def dedup_new(matched_by_source: dict, seen_ids: set):
    """Returns ([(uid, listing), ...] for genuinely new items, already_seen_count)."""
    new = []
    already_seen = 0
    seen_this_run = set()
    for _name, info in matched_by_source.items():
        for listing in info["matched"]:
            uid = compute_uid(listing)
            if uid in seen_ids or uid in seen_this_run:
                already_seen += 1
                continue
            seen_this_run.add(uid)
            new.append((uid, listing))
    return new, already_seen


def validate_and_write(new_listings, profile: dict, jarvis_dir, seen_ids: set, date_found: str, http_head=None):
    """Renders + validates each new listing; writes the ones that pass into
    the Jarvis checkout. Does NOT push and does NOT mutate seen_ids — the
    caller must only do that after a confirmed push. Returns
    (written_uids: list[str], rejections: list[dict])."""
    # Cross-source dedup truth is the files actually in the checkout (they
    # diverged from seen_ids after the 2026-07-18 manual cleanup), plus
    # whatever this run writes — first source in SOURCES order wins.
    dossier_keys = {
        cross_source_key(fm.get("company", ""), fm.get("title", "")) for fm in scan_dossiers(jarvis_dir)
    }
    written_uids = []
    rejections = []
    for uid, listing in new_listings:
        markdown = render_dossier(listing, uid, date_found, build_matched_reason(listing, profile))
        result = validate(listing, uid, markdown, seen_ids, http_head=http_head, dossier_keys=dossier_keys)
        if result.passed:
            write_dossier(jarvis_dir, uid, markdown)
            written_uids.append(uid)
            dossier_keys.add(cross_source_key(listing.company, listing.title))
        else:
            rejections.append({"uid": uid, "check": result.check, "reason": result.reason})
    return written_uids, rejections


def file_github_issue(repo: str, title: str, body: str, run_gh=None) -> None:
    run_gh = run_gh or (lambda args: subprocess.run(args, capture_output=True, text=True))
    run_gh(["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body])


def run_once(
    *,
    jarvis_dir,
    state_path,
    runs_log_path,
    now: datetime,
    profile: dict = None,
    http_get=None,
    http_head=None,
    push_fn=commit_and_push_with_retry,
    issue_fn=file_github_issue,
    issue_repo: str = "gupta-builds/internship-research-loop",
) -> dict:
    profile = profile or load_profile()
    timestamp = now.isoformat()
    record = {
        "timestamp": timestamp,
        "fetch_counts": {},
        "filter_match_counts": {},
        "new_count": 0,
        "already_seen_count": 0,
        "written_count": 0,
        "rejections": [],
        "errors": [],
        "halted": False,
        "halt_reason": None,
    }

    try:
        check_schema_drift(http_get)
    except SchemaDriftError as exc:
        record["halted"] = True
        record["halt_reason"] = str(exc)
        append_run_log(runs_log_path, record)
        issue_fn(
            issue_repo,
            f"Schema drift detected — run halted at {timestamp}",
            f"The scheduled run halted before touching any feeds for real.\n\n```\n{exc}\n```\n\n"
            "Nothing was fetched, filtered, or written this run.",
        )
        return record

    seen_ids = load_seen_ids(state_path)
    matched_by_source = fetch_and_filter(profile, http_get)
    for name, info in matched_by_source.items():
        record["fetch_counts"][name] = info["fetch_count"]
        record["filter_match_counts"][name] = len(info["matched"])

    new_listings, already_seen_count = dedup_new(matched_by_source, seen_ids)
    record["new_count"] = len(new_listings)
    record["already_seen_count"] = already_seen_count

    written_uids, rejections = validate_and_write(
        new_listings, profile, jarvis_dir, seen_ids, now.date().isoformat(), http_head
    )
    record["rejections"] = rejections

    if should_run_weekly_rollup(now):
        week_start = now - timedelta(days=7)
        recent = load_recent_runs(runs_log_path, since=week_start)
        line = format_weekly_rollup(recent, week_start, now)
        append_weekly_rollup(Path(jarvis_dir) / RUN_LOG_MD_SUBPATH, line, created_date=now.date().isoformat())

    pushed = False
    try:
        pushed = push_fn(jarvis_dir, f"Auto-discovered {len(written_uids)} internship(s) — {now.date().isoformat()}")
    except GitPushError as exc:
        record["errors"].append(f"Jarvis push failed: {exc}")
        issue_fn(
            issue_repo,
            f"Jarvis push failed at {timestamp}",
            f"{len(written_uids)} validated dossier(s) were written locally but the push to "
            f"gupta-builds/Jarvis failed after retry:\n\n```\n{exc}\n```\n\n"
            "state/seen_ids.json was NOT updated for these — they'll be retried next run.",
        )

    if written_uids and not pushed:
        # Push failed (or, in principle, never ran) — do NOT mark these as
        # seen. They are still "new" next run and will be retried. This is
        # the ordering guarantee: seen-state only advances on confirmed push.
        pass
    else:
        seen_ids.update(written_uids)
        record["written_count"] = len(written_uids)

    save_seen_ids(state_path, seen_ids)
    append_run_log(runs_log_path, record)

    systemic = [r for r in rejections if r["check"] in SYSTEMIC_REJECTION_CHECKS]
    if systemic:
        details = "\n".join(f"- `{r['uid']}` ({r['check']}): {r['reason']}" for r in systemic)
        issue_fn(
            issue_repo,
            f"Write-gate rejected {len(systemic)} item(s) on required_fields/format_compliance at {timestamp}",
            f"These indicate a bug in our own normalizer or template rendering, not routine "
            f"upstream noise (a stale URL or an already-seen item wouldn't trigger this):\n\n{details}",
        )

    return record


if __name__ == "__main__":
    REPO_ROOT = Path(__file__).parent
    now = datetime.now(timezone.utc)

    result = run_once(
        jarvis_dir=os.environ["JARVIS_DIR"],
        state_path=REPO_ROOT / "state" / "seen_ids.json",
        runs_log_path=REPO_ROOT / "logs" / "runs.jsonl",
        now=now,
    )
    commit_and_push_with_retry(REPO_ROOT, f"Update state + logs — {now.date().isoformat()}")

    if result["halted"] or result["errors"]:
        raise SystemExit(1)
