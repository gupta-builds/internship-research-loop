#!/usr/bin/env python3
"""Periodic re-validation: re-checks every live dossier against current
core/ code (location_eligible, stage1_reject, stage2_confirm) using each
dossier's own already-stored frontmatter/content — no re-fetch, no network
call beyond `gh issue create`. Catches drift where a code fix (e.g. a
denylist gap, a relevance-hint gap) lands after dossiers were already
written under the old, weaker rules — exactly the class of finding the
2026-08-23 dossier audit had to do by hand across 390 files. Files ONE
digest issue listing every newly-failing dossier; never moves or deletes
anything itself — a human still decides removal, same move-not-delete
discipline as recheck.py.

degrees_eligible/exclude_terms aren't re-checked: build_frontmatter() never
persists a dossier's original `degrees` field, and `terms`'s original
matched-term intent isn't reliably reconstructable from the stored value
alone — same scope limit the 2026-08-23 audit itself had.

    JARVIS_DIR=... python revalidate.py [--dry-run]
"""
import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from core.filter import location_eligible
from core.relevance import stage1_reject, stage2_confirm
from run_pipeline import file_github_issue
from vault_writer.writer import scan_dossiers

ISSUE_REPO = "gupta-builds/internship-research-loop"

_POSTING_HEADING_RE = re.compile(r"^## Posting \(fetched [^)]*\)\n", re.M)


def extract_posting_content(path) -> str:
    """The dossier's own already-fetched content (verbatim, as originally
    written) — never re-fetched. '' for a thin dossier ("No posting content
    fetched."), same degrade-to-thin convention extract_content() itself
    uses at write time."""
    text = Path(path).read_text(encoding="utf-8")
    m = _POSTING_HEADING_RE.search(text)
    return text[m.end():].strip() if m else ""


def check_dossier(fm: dict, posting_content: str) -> str:
    """The first rule this dossier would now fail under current code, or
    None if it still passes. posting_content stands in for stage1_reject's
    raw_text param too — the dossier's real fetched content is a strictly
    better signal than the pre-extraction raw_text ever was for the
    structured sources that never carried one."""
    title = fm.get("title", "")
    company = fm.get("company", "")
    locations = fm.get("locations") or []
    if not location_eligible(locations):
        return "location_eligible"
    if stage1_reject(title, posting_content):
        return "stage1_reject"
    if not stage2_confirm(title, company, posting_content):
        return "stage2_confirm"
    return None


def find_regressions(vault_root) -> list:
    """[{path, company, title, reason}] for every live dossier that would
    now fail a check it passed at write time."""
    vault_root = Path(vault_root)
    regressions = []
    for fm in scan_dossiers(vault_root):
        path = fm["_path"]
        posting_content = extract_posting_content(path)
        reason = check_dossier(fm, posting_content)
        if reason:
            regressions.append({
                "path": str(path.relative_to(vault_root)),
                "company": fm.get("company", ""),
                "title": fm.get("title", ""),
                "reason": reason,
            })
    return regressions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report regressions, file no issue")
    args = ap.parse_args()
    jarvis_dir = os.environ["JARVIS_DIR"]
    now = datetime.now(timezone.utc)

    regressions = find_regressions(jarvis_dir)

    for r in regressions:
        print(f"would flag: {r['path']} ({r['reason']})")
    print(f"revalidate: {len(regressions)} dossier(s) newly fail current rules")

    if not regressions or args.dry_run:
        return

    details = "\n".join(
        f"- `{r['path']}` ({r['reason']}) — {r['company']}: {r['title']}" for r in regressions
    )
    file_github_issue(
        ISSUE_REPO,
        f"Revalidate: {len(regressions)} live dossier(s) now fail current rules ({now.date().isoformat()})",
        "These passed the write-gate when written but no longer pass the current "
        "core/filter.py / core/relevance.py rules against their own stored content — "
        "a code fix (denylist/hint-list change) landed after they were written. Review "
        "and remove/keep by hand; this job never moves or deletes a dossier itself.\n\n"
        f"{details}",
    )


if __name__ == "__main__":
    main()
