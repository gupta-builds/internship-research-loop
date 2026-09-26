#!/usr/bin/env python3
"""Post-write consistency check for /promote-dossier's Program/Contact/Tracker trio.

Reads the three real note files and checks: every required frontmatter field
from reference/note-templates.md is present (even as null -- omission is the
violation, not a null value), and the cross-links between the three notes
point at each other correctly (Program -> Contact, Contact -> Program,
Tracker -> both).

Real limitation, disclosed rather than papered over: this only works against
real files on disk -- the sibling-git-checkout reachability path. If the vault
was reached via the Obsidian MCP tools instead, this script cannot run (a
standalone script has no access to a live MCP session) -- do the equivalent
check by hand with mcp__jarvis__vault_read on all three notes instead.

Usage:
    python3 validate_note_trio.py <program.md> <contact.md> <tracker.md>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("pyyaml not installed -- it's already in requirements.txt, install it before running this.", file=sys.stderr)
    raise

PROGRAM_REQUIRED = {
    "name", "company", "program_type", "eligible_classes", "grad_year", "role_type",
    "wave", "opens_date", "deadline_posted", "deadline_real", "pay_per_week",
    "pay_currency", "duration_weeks", "benefits", "application_url", "careers_page",
    "list_origin", "applying_note", "recruiter_contact", "tags",
}
CONTACT_REQUIRED = {
    "type", "name", "role", "company", "linkedin_url", "email", "how_found",
    "relationship", "related_programs", "last_contact_date", "tags", "next",
}
TRACKER_REQUIRED = {
    "type", "program", "contact", "company", "url", "date_noted", "date_researched",
    "date_created", "date_applied", "date_result", "result", "deadline",
    "related_notes", "tags", "next",
}


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        raise ValueError(f"{path}: no YAML frontmatter block found")
    return yaml.safe_load(m.group(1)) or {}


def check_required_fields(name: str, fm: dict, required: set[str]) -> list[str]:
    missing = required - fm.keys()
    return [f"{name}: missing required field(s): {', '.join(sorted(missing))}"] if missing else []


def wikilink_target(value) -> str | None:
    """Extract the note name out of a "[[path/to/Note]]" string, or None."""
    if not isinstance(value, str):
        return None
    m = re.match(r"\[\[(.+?)\]\]", value)
    return Path(m.group(1)).name if m else None


def check_cross_links(program_path: Path, contact_path: Path, tracker_path: Path,
                       program_fm: dict, contact_fm: dict, tracker_fm: dict) -> list[str]:
    errors = []
    program_name = program_path.stem
    contact_name = contact_path.stem

    if wikilink_target(program_fm.get("recruiter_contact")) != contact_name:
        errors.append(
            f"Program.recruiter_contact does not point to the paired Contact note "
            f"(expected a link resolving to '{contact_name}', got {program_fm.get('recruiter_contact')!r})"
        )

    related_programs = contact_fm.get("related_programs") or []
    if not any(wikilink_target(p) == program_name for p in related_programs):
        errors.append(
            f"Contact.related_programs does not include a link back to the paired "
            f"Program note (expected one resolving to '{program_name}')"
        )

    if wikilink_target(tracker_fm.get("program")) != program_name:
        errors.append(f"Tracker.program does not point to the paired Program note (expected '{program_name}')")
    if wikilink_target(tracker_fm.get("contact")) != contact_name:
        errors.append(f"Tracker.contact does not point to the paired Contact note (expected '{contact_name}')")

    for label, fm in [("Program", program_fm), ("Contact", contact_fm), ("Tracker", tracker_fm)]:
        company_vals = {program_fm.get("company"), contact_fm.get("company"), tracker_fm.get("company")}
        if len(company_vals) > 1:
            errors.append(f"company field disagrees across the trio: {company_vals}")
            break

    return errors


def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)

    program_path, contact_path, tracker_path = (Path(p) for p in sys.argv[1:4])
    for p in (program_path, contact_path, tracker_path):
        if not p.is_file():
            print(f"FAIL: {p} does not exist or is not a file.")
            sys.exit(1)

    program_fm = read_frontmatter(program_path)
    contact_fm = read_frontmatter(contact_path)
    tracker_fm = read_frontmatter(tracker_path)

    findings: list[str] = []
    findings += check_required_fields("Program", program_fm, PROGRAM_REQUIRED)
    findings += check_required_fields("Contact", contact_fm, CONTACT_REQUIRED)
    findings += check_required_fields("Tracker", tracker_fm, TRACKER_REQUIRED)
    findings += check_cross_links(program_path, contact_path, tracker_path, program_fm, contact_fm, tracker_fm)

    print(f"## validate_note_trio.py: {program_path.name}")
    print()
    if not findings:
        print("All required fields present on all three notes. Cross-links (Program<->Contact, Tracker->both) consistent.")
        return

    for f in findings:
        print(f"[FLAG] {f}")
    print()
    print(f"{len(findings)} issue(s) found -- fix before considering this promotion complete.")
    sys.exit(1)


if __name__ == "__main__":
    main()
