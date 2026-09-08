#!/usr/bin/env python3
"""One-off cold-start reseed: the same pipeline as run_pipeline.py, run once
with a much larger write budget against an isolated copy of state/, for the
specific scenario where the vault's dossier pile is empty or being
deliberately relaunched and a human wants one large pull across all 11
sources. Never scheduled — .github/workflows/reseed.yml is workflow_dispatch
only, gated behind a literal confirm-string input. Does not change run.yml's
own cadence or MAX_NEW_WRITES_PER_RUN.

Why an isolated state copy, not the real one, for seen_ids.json: if the vault
was wiped but the real state/seen_ids.json still marks those uids seen,
nothing looks "new" and there's nothing to reseed. Running against a fresh
copy makes the whole current catalog reconsiderable again.

Why excluded_uids.json and opt_cache.json still seed from the real files:
those are still-valid findings (a dead URL doesn't come back to life, an
already-checked OPT verdict doesn't change) because the vault was wiped —
skipping them saves real Firecrawl calls and re-fetches.

Why debate_losses.json / capacity_notified.json are never seeded from the
real file and never merged back: they reflect competition under the normal
10/run budget and per-bucket capacity history. Running them through this
run's much larger budget would distort the hourly cadence's own
MAX_DEBATE_LOSSES clock and capacity thresholds for reasons that have nothing
to do with those candidates' real standing under normal conditions.

After a successful run, only seen_ids.json, excluded_uids.json, and
opt_cache.json — the files whose entries must stay valid for run.yml's very
next hourly run, or this recreates the exact write-budget-squatting bug the
2026-08-26 write-starvation postmortem found — are merged back into the real
state/ before it's committed.

    JARVIS_DIR=... FIRECRAWL_API_KEY=... python reseed.py
"""
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import run_pipeline
from ingestion.interndock import fetch_interndock_drop
from ingestion.posting_page import fetch_posting_markdown

REPO_ROOT = Path(__file__).parent

# Far above the hourly loop's own per-run pace (run_pipeline.py's
# MAX_NEW_WRITES_PER_RUN ceiling, or the newer QUOTA_PER_RUN exact quota it
# runs by default as of 2026-09-07 — either way, single digits per bucket)
# — high enough to meaningfully drain a wiped vault in one run, far below the
# thousands-per-week new_count figures the write-starvation postmortem cites
# (those were cumulative across many stalled hourly runs, not one catalog
# snapshot — a single fresh pull across all 11 sources has been observed at
# 219-233 matches in one hour even mid-incident). Costed in the reseed plan,
# 2026-09-07: ~100-150 Firecrawl calls (one per write, per
# validate_and_write's own cost note — Firecrawl only runs after the write
# gate passes), an estimated ~10-20 min added GitHub Actions time.
RESEED_BUDGET = {"AI/ML": 40, "Fullstack": 40, "CyS & Finance": 40, "Other": 20}

OPT_CACHE_FILENAME = "opt_cache.json"  # inline literal in run_pipeline.py's own __main__ too — no named constant there to import


def _union_json_list(scratch_path: Path, real_path: Path) -> None:
    scratch_ids = set(json.loads(scratch_path.read_text())) if scratch_path.exists() else set()
    real_ids = set(json.loads(real_path.read_text())) if real_path.exists() else set()
    real_path.parent.mkdir(parents=True, exist_ok=True)
    real_path.write_text(json.dumps(sorted(scratch_ids | real_ids), indent=2) + "\n")


def _merge_dict_json(scratch_path: Path, real_path: Path) -> None:
    """opt_cache.json is a dict keyed by uid ({uid: {verdict, signal,
    checked}}), not a JSON list like seen_ids/excluded_uids — a set union
    doesn't apply. Scratch's entries are this run's own freshest verdicts, so
    they win on key collision."""
    scratch_data = json.loads(scratch_path.read_text()) if scratch_path.exists() else {}
    real_data = json.loads(real_path.read_text()) if real_path.exists() else {}
    real_path.parent.mkdir(parents=True, exist_ok=True)
    merged = {**real_data, **scratch_data}
    real_path.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n")


def run_reseed(
    *,
    jarvis_dir,
    real_state_dir,
    runs_log_path,
    now: datetime,
    budget: dict = None,
    fetch_page_fn=None,
    interndock_fetch_fn=None,
    push_fn=None,
    **run_once_kwargs,
) -> dict:
    """Explicit-args orchestration function — mirrors run_pipeline.py's own
    split between run_once() (explicit args, no env reads) and its
    __main__ block (env reads only). push_fn here, like run_once's own
    push_fn, is the JARVIS push; this repo's own state/logs commit happens
    separately, in __main__, exactly like run_pipeline.py's.

    **run_once_kwargs forwards straight through to run_pipeline.run_once()
    (e.g. profile=, http_get=, http_head=, issue_fn= for tests) — deliberately
    permissive since this is an internal orchestration function, not a public
    API; a caller passing state_path/state_dir/opt_cache_path here would
    override the scratch paths this function sets up, so don't.

    Returns the run_once() result dict."""
    real_state_dir = Path(real_state_dir)
    scratch_dir = Path(tempfile.mkdtemp(prefix="reseed_state_"))
    try:
        real_excluded = real_state_dir / run_pipeline.EXCLUDED_UIDS_FILENAME
        if real_excluded.exists():
            shutil.copy(real_excluded, scratch_dir / run_pipeline.EXCLUDED_UIDS_FILENAME)

        real_opt_cache = real_state_dir / OPT_CACHE_FILENAME
        if real_opt_cache.exists():
            shutil.copy(real_opt_cache, scratch_dir / OPT_CACHE_FILENAME)

        kwargs = dict(
            jarvis_dir=jarvis_dir,
            state_path=scratch_dir / "seen_ids.json",
            runs_log_path=runs_log_path,
            now=now,
            fetch_page_fn=fetch_page_fn,
            opt_cache_path=scratch_dir / OPT_CACHE_FILENAME,
            state_dir=scratch_dir,
            interndock_fetch_fn=interndock_fetch_fn,
            # run_once's own budget= param (2026-09-07): the old "up to N"
            # _prioritize_and_cap ceiling, not the hourly loop's new
            # exact-quota-or-nothing default — reseed wants whatever's
            # available, not an exact target.
            budget=budget or RESEED_BUDGET,
        )
        if push_fn is not None:
            kwargs["push_fn"] = push_fn
        kwargs.update(run_once_kwargs)
        result = run_pipeline.run_once(**kwargs)

        _union_json_list(scratch_dir / "seen_ids.json", real_state_dir / "seen_ids.json")
        _union_json_list(scratch_dir / run_pipeline.EXCLUDED_UIDS_FILENAME, real_excluded)
        _merge_dict_json(scratch_dir / OPT_CACHE_FILENAME, real_opt_cache)
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)
    return result


if __name__ == "__main__":
    now = datetime.now(timezone.utc)
    firecrawl_key = os.environ.get("FIRECRAWL_API_KEY")
    result = run_reseed(
        jarvis_dir=os.environ["JARVIS_DIR"],
        real_state_dir=REPO_ROOT / "state",
        runs_log_path=REPO_ROOT / "logs" / "reseed_runs.jsonl",
        now=now,
        fetch_page_fn=(lambda url: fetch_posting_markdown(url, firecrawl_key)) if firecrawl_key else None,
        interndock_fetch_fn=(lambda url: fetch_interndock_drop(url, firecrawl_key)) if firecrawl_key else None,
    )

    print(
        f"reseed: written {result['written_count']}, new {result['new_count']}, "
        f"deferred {result['deferred_count']}"
    )

    run_pipeline.commit_and_push_with_retry(REPO_ROOT, f"Cold-start reseed — {now.date().isoformat()}")

    if result["halted"] or result["errors"]:
        raise SystemExit(1)
