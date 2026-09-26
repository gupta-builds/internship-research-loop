#!/usr/bin/env python3
"""Mechanical half of /review-loop-change's four checks, run against a real git diff.

This does NOT replace the skill's own judgment -- checks 2 and 3 need a human/model
to read the actual code and decide whether a flagged line is really a violation.
What this script buys: every check runs the same way every time, a weak model gets
the same real signal a strong one would (grep patterns, not vibes), and nothing
gets missed because a diff was skimmed instead of scanned line-by-line.

Usage:
    python3 check_conventions.py                  # git diff (unstaged)
    python3 check_conventions.py --cached          # git diff --cached (staged)
    python3 check_conventions.py --against main    # git diff main...HEAD

Exit code 0 always -- this reports findings, it does not gate anything itself
(review-loop-change's own "reports-only, never modify code" rule applies here too).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field

UNATTENDED_PATH_FILES = {
    "run_pipeline.py",
    "recheck.py",
    "core/filter.py",
    "core/relevance.py",
    "core/classify.py",
}
UNATTENDED_PATH_DIRS = ("ingestion/", "vault_writer/")
# enrich.py is the one documented exception to "unattended" -- but check 1 still
# applies to it (a manual tool can still add LLM logic that shouldn't be there).
ENRICH_FILE = "enrich.py"

FILTER_CLASSIFY_FILES = {"core/filter.py", "core/relevance.py", "core/classify.py"}

LLM_SIGNAL_PATTERNS = [
    r"\bimport\s+openai\b",
    r"\bimport\s+anthropic\b",
    r"\bfrom\s+openai\b",
    r"\bfrom\s+anthropic\b",
    r"\bgpt-\d",
    r"\bclaude-\d",
    r"chat\.completions",
    r"messages\.create",
    r"api\.openai\.com",
    r"api\.anthropic\.com",
]

CITATION_HINT_PATTERN = re.compile(r"20\d{2}-\d{2}-\d{2}|confirmed|observed|real (data|posting|example|fixture)", re.IGNORECASE)


@dataclass
class Finding:
    check: str
    file: str
    line_no: int
    severity: str  # "FLAG" or "NOTE" (NOTE = needs human judgment, not a clear violation)
    detail: str


@dataclass
class DiffHunk:
    file: str
    added_lines: list[tuple[int, str]] = field(default_factory=list)  # (line_no_in_new_file, text)


def get_diff(args: argparse.Namespace) -> str:
    if args.against:
        cmd = ["git", "diff", f"{args.against}...HEAD"]
    elif args.cached:
        cmd = ["git", "diff", "--cached"]
    else:
        cmd = ["git", "diff"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"git diff failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def parse_diff(diff_text: str) -> list[DiffHunk]:
    """Minimal unified-diff parser: enough to know which file and which new-file
    line number each added (+) line lands on. Not a general-purpose diff parser --
    scoped exactly to what these four checks need."""
    hunks: list[DiffHunk] = []
    current: DiffHunk | None = None
    new_line_no = 0

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current = DiffHunk(file=line[6:])
            hunks.append(current)
            continue
        if line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            if m:
                new_line_no = int(m.group(1)) - 1
            continue
        if current is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            new_line_no += 1
            current.added_lines.append((new_line_no, line[1:]))
        elif not line.startswith("-"):
            new_line_no += 1

    return hunks


def check_1_zero_llm(hunks: list[DiffHunk]) -> list[Finding]:
    findings = []
    for hunk in hunks:
        in_scope = (
            hunk.file in UNATTENDED_PATH_FILES
            or hunk.file == ENRICH_FILE
            or any(hunk.file.startswith(d) for d in UNATTENDED_PATH_DIRS)
        )
        if not in_scope:
            continue
        for line_no, text in hunk.added_lines:
            for pattern in LLM_SIGNAL_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    findings.append(Finding(
                        check="1. Zero-LLM in unattended path",
                        file=hunk.file, line_no=line_no, severity="FLAG",
                        detail=f"matches LLM-signal pattern `{pattern}`: {text.strip()[:100]}",
                    ))
    return findings


def check_2_permissive_default(hunks: list[DiffHunk]) -> list[Finding]:
    findings = []
    reject_pattern = re.compile(r"\breturn\s+False\b|\breject\b", re.IGNORECASE)
    guard_pattern = re.compile(r"^\s*if\s+not\s+\w")
    for hunk in hunks:
        if hunk.file not in FILTER_CLASSIFY_FILES:
            continue
        added = hunk.added_lines
        for i, (line_no, text) in enumerate(added):
            if guard_pattern.match(text):
                # Look at this line and the next couple of added lines for a reject/False.
                window = " ".join(t for _, t in added[i:i + 3])
                if reject_pattern.search(window):
                    findings.append(Finding(
                        check="2. Permissive-by-default filtering",
                        file=hunk.file, line_no=line_no, severity="NOTE",
                        detail=(
                            f"`if not X:` immediately followed by a reject/False shape: "
                            f"{text.strip()[:100]} -- confirm this rejects only on an "
                            "explicit affirmative negative signal, not on missing/ambiguous "
                            "data (the repo's permissive-by-default rule)."
                        ),
                    ))
    return findings


def check_3_write_gate_order(hunks: list[DiffHunk]) -> list[Finding]:
    findings = []
    for hunk in hunks:
        if hunk.file == "vault_writer/validate.py":
            findings.append(Finding(
                check="3. Fail-closed write-gate ordering",
                file=hunk.file, line_no=0, severity="NOTE",
                detail=(
                    "validate.py touched -- manually confirm the check sequence "
                    "(required_fields -> not_duplicate -> cross_source_duplicate -> "
                    "url_liveness -> format_compliance) is unchanged, or that a "
                    "reordering/new check states its cost-based position explicitly. "
                    "This script does not parse function-call order -- read the diff."
                ),
            ))
    return findings


def check_4_cited_real_data(hunks: list[DiffHunk]) -> list[Finding]:
    findings = []
    # A new regex/list/constant assignment -- heuristic: an added line assigning to an
    # ALL_CAPS or _prefixed name, or extending a list/set literal, in a filter/classify module.
    definition_pattern = re.compile(r"^\s*(_?[A-Z][A-Z0-9_]*\s*=|\.append\(|\.add\()")
    for hunk in hunks:
        if hunk.file not in FILTER_CLASSIFY_FILES and hunk.file != "vault_writer/validate.py":
            continue
        for i, (line_no, text) in enumerate(hunk.added_lines):
            if not definition_pattern.match(text):
                continue
            # Check a small window of nearby added lines (comments often sit directly above).
            window_start = max(0, i - 2)
            window = " ".join(t for _, t in hunk.added_lines[window_start:i + 1])
            if not CITATION_HINT_PATTERN.search(window):
                findings.append(Finding(
                    check="4. Cited real data",
                    file=hunk.file, line_no=line_no, severity="FLAG",
                    detail=(
                        f"new rule/constant with no nearby date or 'confirmed/observed/real' "
                        f"citation: {text.strip()[:100]}"
                    ),
                ))
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cached", action="store_true", help="Check staged changes (git diff --cached).")
    parser.add_argument("--against", default=None, help="Check against a ref (git diff <ref>...HEAD).")
    args = parser.parse_args()

    diff_text = get_diff(args)
    if not diff_text.strip():
        print("No diff to check.")
        return

    hunks = parse_diff(diff_text)
    all_findings = (
        check_1_zero_llm(hunks)
        + check_2_permissive_default(hunks)
        + check_3_write_gate_order(hunks)
        + check_4_cited_real_data(hunks)
    )

    checked_files = sorted({h.file for h in hunks})
    print(f"## check_conventions.py: {', '.join(checked_files) if checked_files else '(no files)'}")
    print()

    if not all_findings:
        print("No mechanical findings across all four checks on the files touched.")
        print("Still confirm check 2 (permissive-by-default) and check 3 (write-gate order) by")
        print("reading the diff yourself where relevant -- this script's heuristics narrow the")
        print("search, they don't replace reading the actual logic.")
        return

    for f in all_findings:
        print(f"[{f.severity}] {f.check} -- {f.file}:{f.line_no} -- {f.detail}")

    flags = sum(1 for f in all_findings if f.severity == "FLAG")
    notes = sum(1 for f in all_findings if f.severity == "NOTE")
    print()
    print(f"{flags} FLAG (likely real violation, confirm before shipping), {notes} NOTE (needs human judgment, not automatically a violation).")


if __name__ == "__main__":
    main()
