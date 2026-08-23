"""Phase 3 orchestration: schema-drift check -> fetch -> filter -> dedup ->
validate -> write (Jarvis checkout) -> push (Jarvis, retry-safe) -> mark seen
ONLY on confirmed push -> run log -> push (this repo) -> GH issue on
schema-drift, push failure, or a systemic (not routine) write-gate rejection.

Invoked by .github/workflows/run.yml as `python run_pipeline.py`.
"""
import json
import os
import subprocess
from functools import cmp_to_key

import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.classify import BUCKET_FOLDERS, classification_callout, classify
from core.debate import compute_bucket_urgency, debate_compare
from core.filter import load_profile, matches
from core.git_ops import GitPushError, commit_and_push_with_retry
from core.identity import company_matches_preference, compute_uid
from core.relevance import stage1_reject, stage2_confirm
from core.run_log import (
    append_excluded_log,
    append_run_log,
    append_weekly_rollup,
    format_weekly_rollup,
    load_recent_runs,
    should_run_weekly_rollup,
)
from core.identity import cross_source_key
from core.schema_drift import SchemaDriftError
from core.schema_drift import check_all as check_schema_drift
from ingestion.freehire import fetch_freehire
from ingestion.posting_page import extract_content, fetch_posting_markdown, opt_exclusion, phd_only_exclusion
from ingestion.sources import (
    fetch_ai_jobs,
    fetch_ashby,
    fetch_greenhouse,
    fetch_josegael,
    fetch_simplify,
    fetch_vanshb03,
    fetch_zshah101,
)
from vault_writer.validate import check_format_compliance, validate
from vault_writer.writer import DOSSIER_SUBPATH, render_dossier, scan_dossiers, write_dossier

SOURCES = (
    ("SimplifyJobs", fetch_simplify),
    ("Jose-Gael-Cruz-Lopez", fetch_josegael),
    ("vanshb03", fetch_vanshb03),
    ("zshah101", fetch_zshah101),
    ("Greenhouse", fetch_greenhouse),
    ("Ashby", fetch_ashby),
    ("Freehire", fetch_freehire),
    ("AIJobs", fetch_ai_jobs),
)

# 2026-07-25 decision: turning on 4 sources at once produced a one-time backlog
# (186 new candidates, 171 write-gate-passing) far above the steady-state <100/
# month Firecrawl budget Phase 6 was sized for. Neither absorbing the whole
# backlog in one run (dumps 100+ dossiers on a promotion queue already at zero)
# nor pre-seeding seen_ids to silently skip it (throws away real, currently-
# open postings — the reason these sources were added) was acceptable. Cap
# instead, and let it drain over several runs. No structured deadline field
# exists across all 6 sources (Greenhouse sometimes has one via metadata, the
# other 5 sources never do) — most-recently-posted first is the prioritization
# that's actually available everywhere, not a compromise on the chosen rule.
#
# Revised 2026-07-29 (Task A): split per bucket instead of one flat number —
# a tunable dict, not magic numbers spread through the function. Still caps
# at roughly 10/run to protect Firecrawl budget and review throughput; a
# bucket with 0 eligible candidates this run never lets another bucket borrow
# its unused slots (each bucket only draws from its own ordered queue).
MAX_NEW_WRITES_PER_RUN = {"AI/ML": 3, "Fullstack": 3, "CyS & Finance": 3, "Other": 1}

# Per-bucket vault capacity, per the original design (Dossiers-to-Create.md,
# Source of Truth.md) — but per the user's explicit 2026-07-29 override, this
# is a NOTIFICATION mechanism, never a write refusal: the false-exclusion-
# worse-than-false-inclusion asymmetry that governs every other gate in this
# codebase applies here too (a hard-refusal cap would silently drop a real,
# currently-open posting for no benefit — the scarce resource is human review
# attention, not vault storage). See run_once()'s bucket_at_capacity handling.
BUCKET_CAPACITY = 50
# Global total across List/Dossiers/ excluding Viewed/. 150/170 are logged in
# the run record only (informational); 190/200 additionally file a GitHub
# issue the first time each is crossed (same "notify once" state as buckets).
GLOBAL_INFO_THRESHOLDS = (150, 170)
GLOBAL_ISSUE_THRESHOLDS = (190, 200)
CAPACITY_STATE_FILENAME = "capacity_notified.json"


def _prioritize_and_cap(new_listings: list, budget: dict, preferred_companies: dict = None) -> tuple:
    """Scoped per-bucket per the tunable budget dict — each bucket fills only
    from its own ordered queue, so an empty bucket this run can't let another
    bucket's items borrow its slots. Bucket is the same degraded-signal
    classify() (title/category only, no fetched content yet)
    validate_and_write() itself falls back to before a posting's content is
    fetched — pacing doesn't need the refined, content-informed bucket, only
    the final written folder does. Returns (this_run, deferred) — deferred
    items are simply not passed to validate_and_write and therefore never
    marked seen, so dedup_new() naturally re-offers them next run without any
    extra state to manage.

    Ordering within each bucket is now the Task L "debate" comparator
    (preferred-company tier -> bucket fill-need -> recency) instead of a bare
    recency sort — preferred_companies=None degrades to the original
    recency-only order (every candidate ties at stage 1, and stage 2 never
    fires within a single bucket's own list regardless, so recency alone
    decides), which is also exactly what every pre-Task-L caller/test gets
    for free."""
    by_bucket = {}
    for uid, listing in new_listings:
        bucket, _ = classify(listing.title, listing.category, "")
        by_bucket.setdefault(bucket, []).append((uid, listing))

    bucket_urgency = compute_bucket_urgency(new_listings, budget)
    cmp_key = cmp_to_key(lambda x, y: debate_compare(x, y, preferred_companies or {}, bucket_urgency))

    preferred_companies = preferred_companies or {}
    this_run, deferred = [], []
    for bucket, items in by_bucket.items():
        ordered = sorted(items, key=cmp_key)
        limit = budget.get(bucket, 0)
        selected, remainder = ordered[:limit], ordered[limit:]
        # Task A (Phase 4, 2026-08-23 decision): a reserved preferred-company
        # slot, additive on top of the bucket's normal budget — never carved
        # from it, so no non-preferred candidate loses ground to make room.
        # Real cause: Citadel's posting classified into 'Other' (a generic
        # "Software Engineer Intern" title hits no bucket-specific regex) —
        # the smallest budget (1/run) — and kept losing recency ties to
        # OTHER preferred companies' fresher arrivals, since preference_tier
        # is a binary gate with no further differentiation (see the Task 7
        # audit's Archive entry). debate_compare already sorts every
        # preferred candidate ahead of every non-preferred one within a
        # bucket, so remainder[0] being preferred means it's the single
        # best-ranked preferred candidate that still lost the normal-budget
        # debate — grant it one extra slot. If multiple preferred candidates
        # are competing for it, debate_compare's existing recency tie-break
        # already picked the winner; this doesn't redesign that.
        if remainder and company_matches_preference(remainder[0][1].company, preferred_companies):
            selected = selected + remainder[:1]
            remainder = remainder[1:]
        this_run.extend(selected)
        deferred.extend(remainder)
    return this_run, deferred


def count_dossiers_by_bucket(vault_root) -> dict:
    """Real per-bucket file counts in the vault checkout — Viewed/ isn't one
    of BUCKET_FOLDERS' values, so it's excluded automatically, matching the
    Standard's '201 total excluding Viewed/' scope."""
    vault_root = Path(vault_root)
    counts = {}
    for bucket, folder in BUCKET_FOLDERS.items():
        d = vault_root / DOSSIER_SUBPATH / folder
        counts[bucket] = len(list(d.glob("*.md"))) if d.is_dir() else 0
    return counts


def load_capacity_notified(state_dir) -> dict:
    path = Path(state_dir) / CAPACITY_STATE_FILENAME
    if not path.exists():
        return {"buckets": [], "global": []}
    return json.loads(path.read_text())


def save_capacity_notified(state_dir, notified: dict) -> None:
    path = Path(state_dir) / CAPACITY_STATE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(notified, indent=2, sort_keys=True) + "\n")

RUN_LOG_MD_SUBPATH = Path("10_Areas/Career/Internships/List/Run Log.md")

# Task N (Prompt 5) — a candidate that loses the debate comparator's sort
# (falls outside its bucket's budget, i.e. ends up in _prioritize_and_cap's
# "deferred" list) accumulates a loss count across runs. 5 was chosen to give
# a real posting several genuine chances across multiple hourly runs before
# conceding it structurally can't out-rank the field — not an arbitrary
# guess dressed as one, but still a tunable to retune from real data once
# this has run for a while, same as every other tunable in this codebase.
MAX_DEBATE_LOSSES = 5
DEBATE_LOSSES_FILENAME = "debate_losses.json"
EXCLUDED_UIDS_FILENAME = "excluded_uids.json"
EXCLUDED_LOG_SUBPATH = Path("10_Areas/Career/Internships/List/Excluded — Losing The Debate.md")

# Task (Phase 4, 2026-08-23 dossier audit): a per-run alert when a burst of
# new candidates all cross MAX_DEBATE_LOSSES together — real incident,
# 2026-08-21: 287 of the excluded log's 304 total entries (94%) were
# excluded on that single day, TikTok alone contributing 106. The gap this
# surfaces isn't "one company needs its own cap" — it's that a transient
# candidate backlog converts into permanent exclusion within
# MAX_DEBATE_LOSSES runs (~5 hours) with no signal to a human that it's
# happening. 20 is comfortably above the normal handful-per-run trickle
# (every other run in logs/runs.jsonl carries newly_excluded_count of 0-2)
# while still catching a burst early, not just after the fact in a manual
# audit.
NEWLY_EXCLUDED_ALERT_THRESHOLD = 20


def should_alert_on_exclusion_spike(newly_excluded_count: int) -> bool:
    return newly_excluded_count > NEWLY_EXCLUDED_ALERT_THRESHOLD


def load_debate_losses(state_dir) -> dict:
    path = Path(state_dir) / DEBATE_LOSSES_FILENAME
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_debate_losses(state_dir, losses: dict) -> None:
    path = Path(state_dir) / DEBATE_LOSSES_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(losses, indent=2, sort_keys=True) + "\n")


def load_excluded_uids(state_dir) -> set:
    path = Path(state_dir) / EXCLUDED_UIDS_FILENAME
    if not path.exists():
        return set()
    return set(json.loads(path.read_text()))


def save_excluded_uids(state_dir, excluded: set) -> None:
    path = Path(state_dir) / EXCLUDED_UIDS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(excluded), indent=2) + "\n")


def update_debate_losses(losses: dict, deferred: list, written_uids: list) -> tuple:
    """Returns (updated_losses, newly_excluded: [(uid, listing), ...]).
    Increments the loss count for every deferred uid (a candidate that lost
    this run's per-bucket comparator sort); removes any uid that won (got
    written) this run entirely — it's in seen_ids.json now, its loss history
    is moot. A uid whose count reaches MAX_DEBATE_LOSSES is returned in
    newly_excluded and removed from losses — callers add it to the excluded
    set and log it; this function only does the counting."""
    losses = dict(losses)
    for uid in written_uids:
        losses.pop(uid, None)
    newly_excluded = []
    for uid, listing in deferred:
        losses[uid] = losses.get(uid, 0) + 1
        if losses[uid] >= MAX_DEBATE_LOSSES:
            newly_excluded.append((uid, listing))
            del losses[uid]
    return losses, newly_excluded

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


def fetch_and_filter(profile: dict, http_get=None, excluded_ids: frozenset = frozenset()) -> dict:
    """Returns {source_name: {"fetch_count": int, "matched": [Listing, ...]}}.
    excluded_ids (Task N, Prompt 5) drops a uid that already lost the debate
    comparator MAX_DEBATE_LOSSES consecutive times here, before it's even
    counted as matched — the earliest seam available, so an excluded uid
    never reaches the Firecrawl content-fetch in validate_and_write either."""
    results = {}
    for name, fetch_fn in SOURCES:
        listings = fetch_fn(http_get)
        results[name] = {
            "fetch_count": len(listings),
            "matched": [
                l for l in listings
                if matches(l, profile) and not stage1_reject(l.title, l.raw_text)
                and compute_uid(l) not in excluded_ids
            ],
        }
    return results


def dedup_new(matched_by_source: dict, seen_ids: set, excluded_ids: frozenset = frozenset()):
    """Returns ([(uid, listing), ...] for genuinely new items, already_seen_count).
    excluded_ids is also checked here (belt-and-suspenders with
    fetch_and_filter's own check above) so nothing slips through if a caller
    ever builds matched_by_source some other way."""
    new = []
    already_seen = 0
    seen_this_run = set()
    for _name, info in matched_by_source.items():
        for listing in info["matched"]:
            uid = compute_uid(listing)
            if uid in excluded_ids:
                continue
            if uid in seen_ids or uid in seen_this_run:
                already_seen += 1
                continue
            seen_this_run.add(uid)
            new.append((uid, listing))
    return new, already_seen


def validate_and_write(new_listings, profile: dict, jarvis_dir, seen_ids: set, date_found: str,
                       http_head=None, fetch_page_fn=None, opt_cache=None, state_dir=None):
    """Renders + validates each new listing; writes the ones that pass into
    the Jarvis checkout. Does NOT push and does NOT mutate seen_ids — the
    caller must only do that after a confirmed push. Returns
    (written_uids: list[str], rejections: list[dict]).

    fetch_page_fn (url -> markdown or raises) enables the discovery-time
    posting fetch: one Firecrawl call per new validated match serves both the
    dossier's content section and the OPT-eligibility check. Fail-open — any
    fetch failure writes the thin dossier and never blocks discovery. Ordering
    is deliberate: the fetch runs only AFTER the write gate passes, so the
    18-a-run dead-URL rejections never cost a Firecrawl credit.

    opt_cache (uid -> {verdict, signal, checked}) persists across runs: an
    OPT-rejected posting is never marked seen (so it's retried hourly), and
    the cache is what stops that retry from re-fetching the same page every
    hour. Checked per-posting, not per-company — Palantir's US Government and
    Commercial roles differ on exactly this axis (verified 2026-07-18)."""
    opt_cache = opt_cache if opt_cache is not None else {}
    # Cross-source dedup truth is the files actually in the checkout (they
    # diverged from seen_ids after the 2026-07-18 manual cleanup), plus
    # whatever this run writes — first source in SOURCES order wins.
    dossier_keys = {
        cross_source_key(fm.get("company", ""), fm.get("title", ""), fm.get("url", ""))
        for fm in scan_dossiers(jarvis_dir)
    }
    written_uids = []
    rejections = []
    for uid, listing in new_listings:
        cached = opt_cache.get(uid)
        if cached and cached.get("verdict") == "excluded":
            rejections.append({"uid": uid, "check": "opt_eligibility",
                              "reason": f"{cached['signal']} (cached {cached['checked']})"})
            continue
        markdown = render_dossier(listing, uid, date_found, build_matched_reason(listing, profile),
                                  preferred_companies=profile.get("preferred_companies"))
        result = validate(listing, uid, markdown, seen_ids, http_head=http_head, dossier_keys=dossier_keys)
        if not result.passed:
            rejections.append({"uid": uid, "check": result.check, "reason": result.reason})
            continue
        posting_content = ""
        # Degraded-signal default: no content fetched yet (or ever, if
        # fetch_page_fn is None) — title/category alone still classify,
        # since every write needs a bucket. Refined below once/if real
        # posting content comes back.
        bucket, signal = classify(listing.title, listing.category, "")
        if fetch_page_fn is not None:
            try:
                page_md = fetch_page_fn(listing.url)
            except Exception:
                page_md = ""  # fail-open: thin dossier beats a blocked run
            if page_md:
                posting_content = extract_content(page_md)
                # Adjacent-field content confirmation (Task A stage 2): needs
                # the fetched page, so it runs here rather than at the cheap
                # title-only stage1_reject seam in fetch_and_filter.
                if not stage2_confirm(listing.title, listing.company, posting_content):
                    rejections.append({"uid": uid, "check": "cs_relevance",
                                       "reason": "adjacent-field posting, no software signal in content"})
                    continue
                opt_signal = opt_exclusion(page_md)
                if opt_signal:
                    opt_cache[uid] = {"verdict": "excluded", "signal": opt_signal, "checked": date_found}
                    rejections.append({"uid": uid, "check": "opt_eligibility", "reason": opt_signal})
                    continue
                degree_signal = phd_only_exclusion(page_md)
                if degree_signal:
                    rejections.append({"uid": uid, "check": "degree_eligibility", "reason": degree_signal})
                    continue
                opt_cache[uid] = {"verdict": "eligible", "signal": None, "checked": date_found}
                bucket, signal = classify(listing.title, listing.category, posting_content)
                enriched = render_dossier(listing, uid, date_found,
                                          build_matched_reason(listing, profile), posting_content,
                                          classification_callout(bucket, signal),
                                          preferred_companies=profile.get("preferred_companies"))
                # The gate validated the thin render; re-check format on the
                # enriched one — an extraction bug degrades to thin, never
                # writes malformed markdown into the vault.
                if check_format_compliance(enriched).passed:
                    markdown = enriched
        write_dossier(jarvis_dir, uid, markdown, listing.title, listing.company, BUCKET_FOLDERS[bucket],
                     state_dir=state_dir)
        written_uids.append(uid)
        dossier_keys.add(cross_source_key(listing.company, listing.title, listing.url))
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
    fetch_page_fn=None,
    opt_cache_path=None,
    state_dir=None,
) -> dict:
    profile = profile or load_profile()
    timestamp = now.isoformat()
    record = {
        "timestamp": timestamp,
        "fetch_counts": {},
        "filter_match_counts": {},
        "new_count": 0,
        "already_seen_count": 0,
        "deferred_count": 0,
        "written_count": 0,
        "rejections": [],
        "errors": [],
        "halted": False,
        "halt_reason": None,
        "bucket_at_capacity": [],
        "dossier_total": 0,
        "newly_excluded_count": 0,
    }

    excluded_ids = load_excluded_uids(state_dir) if state_dir is not None else set()

    try:
        check_schema_drift(http_get)
        seen_ids = load_seen_ids(state_path)
        matched_by_source = fetch_and_filter(profile, http_get, excluded_ids=excluded_ids)
    except (SchemaDriftError, requests.RequestException) as exc:
        # RequestException too — a deleted repo, DNS failure, or 5xx used to
        # crash the process before any run-log record or issue existed (the
        # PRD's "source repo goes offline" risk, previously unmitigated).
        record["halted"] = True
        record["halt_reason"] = f"{type(exc).__name__}: {exc}"
        append_run_log(runs_log_path, record)
        issue_fn(
            issue_repo,
            f"Run halted ({type(exc).__name__}) at {timestamp}",
            f"Schema drift or source fetch failure — nothing was fetched, filtered, "
            f"or written this run.\n\n```\n{type(exc).__name__}: {exc}\n```",
        )
        return record

    for name, info in matched_by_source.items():
        record["fetch_counts"][name] = info["fetch_count"]
        record["filter_match_counts"][name] = len(info["matched"])

    new_listings, already_seen_count = dedup_new(matched_by_source, seen_ids, excluded_ids=excluded_ids)
    record["new_count"] = len(new_listings)
    record["already_seen_count"] = already_seen_count

    this_run, deferred = _prioritize_and_cap(
        new_listings, MAX_NEW_WRITES_PER_RUN, preferred_companies=profile.get("preferred_companies")
    )
    record["deferred_count"] = len(deferred)

    opt_cache = {}
    if opt_cache_path and Path(opt_cache_path).exists():
        opt_cache = json.loads(Path(opt_cache_path).read_text())
    written_uids, rejections = validate_and_write(
        this_run, profile, jarvis_dir, seen_ids, now.date().isoformat(), http_head,
        fetch_page_fn=fetch_page_fn, opt_cache=opt_cache, state_dir=state_dir,
    )
    if opt_cache_path and opt_cache:
        Path(opt_cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(opt_cache_path).write_text(json.dumps(opt_cache, indent=2, sort_keys=True) + "\n")
    record["rejections"] = rejections

    # Task N (Prompt 5): count this run's debate loss for every deferred
    # candidate; a uid that won (got written) has its loss history dropped
    # entirely. A uid crossing MAX_DEBATE_LOSSES moves to the excluded set
    # and gets one line in a reviewable markdown log — not a silent,
    # permanent exclusion.
    if state_dir is not None:
        debate_losses = load_debate_losses(state_dir)
        debate_losses, newly_excluded = update_debate_losses(debate_losses, deferred, written_uids)
        save_debate_losses(state_dir, debate_losses)
        record["newly_excluded_count"] = len(newly_excluded)
        if newly_excluded:
            excluded_ids = load_excluded_uids(state_dir)
            excluded_ids.update(uid for uid, _listing in newly_excluded)
            save_excluded_uids(state_dir, excluded_ids)
            for uid, listing in newly_excluded:
                line = (
                    f"- **{listing.company}** — {listing.title} — [{listing.url}]({listing.url}) — "
                    f"excluded {now.date().isoformat()} — lost the debate {MAX_DEBATE_LOSSES} consecutive runs"
                )
                append_excluded_log(
                    Path(jarvis_dir) / EXCLUDED_LOG_SUBPATH, line, created_date=now.date().isoformat(),
                    max_losses=MAX_DEBATE_LOSSES,
                )
        if should_alert_on_exclusion_spike(record["newly_excluded_count"]):
            issue_fn(
                issue_repo,
                f"Debate-loss exclusion spike: {record['newly_excluded_count']} in one run ({timestamp})",
                f"{record['newly_excluded_count']} candidates crossed MAX_DEBATE_LOSSES "
                f"({MAX_DEBATE_LOSSES} consecutive losses) and were permanently excluded in this single "
                "run — well above the normal handful-per-run trickle. This usually means a burst of new "
                "candidates arrived together and lost the debate to each other, not that they're "
                "individually undesirable (see the 2026-08-21 incident: 287 of 304 total exclusions "
                "happened in one day). Review the newly-excluded entries in "
                "`Excluded — Losing The Debate.md` before treating any of them as a real quality signal.",
            )

    # Task A resource-limit notification (Standard §5): a bucket at/over
    # capacity or the global total crossing a threshold is surfaced, never a
    # write refusal — the writes above already happened regardless.
    bucket_counts = count_dossiers_by_bucket(jarvis_dir)
    record["bucket_at_capacity"] = sorted(b for b, c in bucket_counts.items() if c >= BUCKET_CAPACITY)
    record["dossier_total"] = sum(bucket_counts.values())

    notified = load_capacity_notified(state_dir) if state_dir is not None else {"buckets": [], "global": []}
    newly_notified = False
    for bucket in record["bucket_at_capacity"]:
        if bucket not in notified["buckets"]:
            notified["buckets"].append(bucket)
            newly_notified = True
            issue_fn(
                issue_repo,
                f"Bucket '{bucket}' at/over its {BUCKET_CAPACITY}-dossier notification threshold ({timestamp})",
                f"'{bucket}' now has {bucket_counts[bucket]} dossiers in List/Dossiers/ — this is a "
                "notification, not a write refusal (a full bucket is a signal to review more urgently, "
                "not a reason to lose a real posting). New matches keep writing into this bucket.",
            )
    for threshold in GLOBAL_ISSUE_THRESHOLDS:
        if record["dossier_total"] >= threshold and threshold not in notified["global"]:
            notified["global"].append(threshold)
            newly_notified = True
            issue_fn(
                issue_repo,
                f"Total dossier count crossed {threshold} ({timestamp})",
                f"List/Dossiers/ (excluding Viewed/) now has {record['dossier_total']} dossiers total.",
            )
    if state_dir is not None and newly_notified:
        save_capacity_notified(state_dir, notified)

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

    firecrawl_key = os.environ.get("FIRECRAWL_API_KEY")
    result = run_once(
        jarvis_dir=os.environ["JARVIS_DIR"],
        state_path=REPO_ROOT / "state" / "seen_ids.json",
        runs_log_path=REPO_ROOT / "logs" / "runs.jsonl",
        now=now,
        fetch_page_fn=(lambda url: fetch_posting_markdown(url, firecrawl_key)) if firecrawl_key else None,
        opt_cache_path=REPO_ROOT / "state" / "opt_cache.json",
        state_dir=REPO_ROOT / "state",
    )
    commit_and_push_with_retry(REPO_ROOT, f"Update state + logs — {now.date().isoformat()}")

    if result["halted"] or result["errors"]:
        raise SystemExit(1)
