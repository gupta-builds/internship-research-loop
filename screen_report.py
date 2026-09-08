#!/usr/bin/env python3
"""Read-only ready-to-screen report: every dossier currently in the vault
(excluding Viewed/), grouped by bucket, sorted preferred-company-first
(core/company_registry.py's TIER_RANK) then most-recently-posted-first,
top N per bucket. Builds Improvement Plan §4(b)'s previously-scoped-but-
unbuilt idea ("surface a per-bucket ready-to-screen view"), made urgent by
reseed.py's ability to produce 100+ new dossiers in one run that a human
then has to triage by hand. Read-only: never writes, moves, or deletes a
single dossier — only scan_dossiers() (vault_writer/writer.py), which is
already used this way by recheck.py, is called against the vault.

    JARVIS_DIR=... python screen_report.py [--top N]
"""
import argparse
import os
from pathlib import Path

from core.classify import BUCKET_FOLDERS
from core.company_registry import TIER_RANK
from vault_writer.writer import VIEWED_SUBPATH, scan_dossiers

DEFAULT_TOP_N = 15


def _tier_rank(preference_tier) -> int:
    # Same "falsy tier ranks last" rule as core/debate.py's _preference_rank.
    return TIER_RANK.get(preference_tier, 1) if preference_tier else 1


def build_report(dossiers: list, top_n: int = DEFAULT_TOP_N) -> str:
    """dossiers: scan_dossiers()'s own return shape (frontmatter dicts with a
    _path key). Excludes anything in a Viewed/ folder; anything not in one of
    BUCKET_FOLDERS' own folders is left out too (there's no bucket to file it
    under). Two-pass stable sort — date descending first, then tier
    ascending — so within a tier, ties break by recency, and preferred
    companies always sort ahead of non-preferred regardless of date."""
    folder_to_bucket = {folder: bucket for bucket, folder in BUCKET_FOLDERS.items()}
    by_bucket = {bucket: [] for bucket in BUCKET_FOLDERS}
    for fm in dossiers:
        folder_name = fm["_path"].parent.name
        if folder_name == VIEWED_SUBPATH.name:
            continue
        bucket = folder_to_bucket.get(folder_name)
        if bucket is None:
            continue
        by_bucket[bucket].append(fm)

    lines = ["# Ready To Screen"]
    for bucket in BUCKET_FOLDERS:
        entries = sorted(by_bucket[bucket], key=lambda fm: fm.get("date_posted") or "", reverse=True)
        entries = sorted(entries, key=lambda fm: _tier_rank(fm.get("preference_tier")))
        shown = entries[:top_n]
        lines.append(f"\n## {bucket} ({len(entries)} total, showing top {len(shown)})")
        for fm in shown:
            tier = fm.get("preference_tier") or "—"
            date = fm.get("date_posted") or "—"
            url = fm.get("url", "")
            lines.append(
                f"- **{fm.get('company', '?')}** — {fm.get('title', '?')} — "
                f"[{url}]({url}) — tier: {tier} — posted: {date}"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N)
    args = parser.parse_args()
    dossiers = scan_dossiers(os.environ["JARVIS_DIR"])
    print(build_report(dossiers, top_n=args.top))


if __name__ == "__main__":
    main()
