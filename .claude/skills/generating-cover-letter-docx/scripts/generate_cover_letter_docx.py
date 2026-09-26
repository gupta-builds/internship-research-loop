#!/usr/bin/env python3
"""Generate a cover letter .docx that matches this skill's researched format rules.

This script owns FORMAT only (page size, font, spacing, margins, the closing block).
It does not select content, check evidence, or decide what a letter says — that is
Cover Letter Alteration Standard's job and .cursor/skills/cover-letter-alteration's
job. This script's only input is an already-approved content plan; it never asks
"is this true," only "does this fit the page and look like a real business letter."

Rules implemented, each cited in reference/cover-letter-format-rules.md:
  - One page target (soft-enforced via a word-count warning, not a hard page count,
    since page rendering depends on the reader's own Word/LibreOffice font metrics).
  - Times New Roman by default (Arial/Calibri/Tahoma are the other Standard-approved
    choices — pass --font to use one of them), one font throughout, no bold/italic
    in body text.
  - Font size 11 by default (10-12 is the approved range).
  - Single line spacing within paragraphs, one blank line between paragraphs
    (implemented as space_after on each paragraph, not literal blank paragraphs).
  - 1-inch margins on all sides.
  - Closing: "Sincerely," + typed name + the same contact line as the header --
    no blank lines reserved for a handwritten signature (this produces a digital
    .docx for upload/email, never a printed letter).

Usage as a library (the intended real usage -- an agent/skill calls this function
with a real, human-approved content plan, never fabricates one itself):

    from generate_cover_letter_docx import build_cover_letter, ContentPlan
    plan = ContentPlan(
        sender_name="...", contact_line="...", date="...",
        recipient_lines=["...", "...", "..."], greeting="...",
        paragraphs=["...", "...", "...", "..."],
    )
    build_cover_letter(plan, "Cover Letters/Role - Company.docx")

Usage from the command line (for a demo/self-check only -- see __main__ below):
    python3 generate_cover_letter_docx.py --demo --out /tmp/demo-cover-letter.docx
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_LINE_SPACING
except ImportError:
    print(
        "python-docx is not installed in this environment. "
        "Install it (matching internship-research-loop's own requirements.txt "
        "convention, e.g. `python-docx==1.2.0`) before running this script for real.",
        file=sys.stderr,
    )
    raise

APPROVED_FONTS = {"Times New Roman", "Arial", "Calibri", "Tahoma"}
MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 12
# Soft ceiling for a one-page letter at 11-12pt with 1in margins. Real page count
# depends on the reader's renderer, so this is a warning, never a hard failure --
# per this whole project's own "disclose a real limitation, don't silently pretend
# past it" discipline, the script tells the caller when it's likely over a page
# instead of guessing that it fit.
ONE_PAGE_WORD_CEILING = 420


@dataclass
class ContentPlan:
    """Everything this script needs, and nothing it's allowed to invent.

    Every field here must already be human-approved content -- this dataclass
    has no defaults for sender_name/paragraphs/etc. on purpose, so a caller
    can't accidentally build a ContentPlan with placeholder content and pass
    it through as if it were real.
    """

    sender_name: str
    contact_line: str  # e.g. "612-555-0143 · name@example.edu · linkedin.com/... · github.com/..."
    date: str  # e.g. "September 6, 2026" -- caller's job to format, not this script's
    recipient_lines: list[str]  # e.g. ["Hiring Team", "Acme Robotics", "Minneapolis, MN"]
    greeting: str  # e.g. "Dear Acme Robotics Hiring Team,"
    paragraphs: list[str]  # 3-5 body paragraphs, per Columbia SEAS's "4 or 5 brief paragraphs"
    closing: str = "Sincerely,"
    font: str = "Times New Roman"
    font_size: int = 11


def _validate(plan: ContentPlan) -> list[str]:
    """Real checks against the sourced rules -- returns a list of warnings, never
    raises, so the caller (a human reviewing output, or an agent reporting back)
    decides what to do with a warning rather than the script silently failing
    closed on something a human might have a good reason to override."""
    warnings: list[str] = []

    if plan.font not in APPROVED_FONTS:
        warnings.append(
            f"Font '{plan.font}' is not one of the Standard-approved fonts "
            f"({', '.join(sorted(APPROVED_FONTS))}) per Columbia SEAS's own rule."
        )
    if not (MIN_FONT_SIZE <= plan.font_size <= MAX_FONT_SIZE):
        warnings.append(
            f"Font size {plan.font_size}pt is outside the sourced 10-12pt range."
        )
    if not (3 <= len(plan.paragraphs) <= 5):
        warnings.append(
            f"{len(plan.paragraphs)} body paragraphs -- Columbia SEAS's rule is "
            "4 or 5 brief paragraphs (a lean 3-paragraph letter is a judgment "
            "call, not a violation, but check it's genuinely complete)."
        )

    word_count = len(plan.greeting.split()) + sum(len(p.split()) for p in plan.paragraphs)
    if word_count > ONE_PAGE_WORD_CEILING:
        warnings.append(
            f"~{word_count} words in the body -- likely over one page at "
            f"{plan.font_size}pt with 1in margins (soft ceiling: {ONE_PAGE_WORD_CEILING} "
            "words). Cut content rather than shrinking the font/margins past the "
            "Standard's own range to force a fit."
        )

    return warnings


def build_cover_letter(plan: ContentPlan, output_path: str) -> list[str]:
    """Builds the .docx at output_path. Returns the list of format warnings found
    (empty list means everything matched the sourced rules) -- always writes the
    file even if there are warnings, since a format warning is something for a
    human to weigh, not a reason to silently produce nothing."""
    warnings = _validate(plan)

    document = Document()

    section = document.sections[0]
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)

    normal_style = document.styles["Normal"]
    normal_style.font.name = plan.font
    normal_style.font.size = Pt(plan.font_size)
    normal_style.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    normal_style.paragraph_format.space_after = Pt(plan.font_size)  # ~one blank line

    def add_line(text: str, *, space_after_pt: float | None = None) -> None:
        p = document.add_paragraph(text)
        if space_after_pt is not None:
            p.paragraph_format.space_after = Pt(space_after_pt)

    # Header block: name, then the contact line -- identical shape to the closing
    # block (reference/cover-letter-format-rules.md's "mirrors the resume header").
    add_line(plan.sender_name)
    add_line(plan.contact_line, space_after_pt=plan.font_size * 2)

    add_line(plan.date, space_after_pt=plan.font_size * 2)

    for i, line in enumerate(plan.recipient_lines):
        is_last = i == len(plan.recipient_lines) - 1
        add_line(line, space_after_pt=(plan.font_size * 2 if is_last else None))

    add_line(plan.greeting, space_after_pt=plan.font_size * 2)

    for paragraph in plan.paragraphs:
        add_line(paragraph, space_after_pt=plan.font_size)

    # One blank-line gap before the close, matching the body-paragraph spacing.
    add_line(plan.closing, space_after_pt=plan.font_size)
    # No blank lines reserved for a handwritten signature -- this is a digital
    # .docx for upload/email, per the "Digital vs. printed signature" reference note.
    add_line(plan.sender_name)
    add_line(plan.contact_line)

    document.save(output_path)
    return warnings


def _demo_plan() -> ContentPlan:
    """The example-cover-letter.md exemplar, reproduced as a ContentPlan -- fabricated
    person, used only to self-check that this script actually produces the right
    format. Never call this for a real application."""
    contact = "612-555-0143 · jordan.lee@example.edu · linkedin.com/in/jordanlee-example · github.com/jlee-example"
    return ContentPlan(
        sender_name="Jordan Lee",
        contact_line=contact,
        date="September 6, 2026",
        recipient_lines=["Hiring Team", "Acme Robotics", "Minneapolis, MN"],
        greeting="Dear Acme Robotics Hiring Team,",
        paragraphs=[
            "I'm a Computer Science student at a large public university, and I'm applying "
            "for the Software Engineering Intern role on your Perception team. Acme's recent "
            "work on low-latency object tracking for warehouse robots is exactly the kind of "
            "real-time, resource-constrained systems problem I've spent the last year working "
            "on -- building a Rust-based logging middleware that captures and structures "
            "high-frequency event streams for a university research group, where every added "
            "millisecond of processing time was a real cost, not an abstraction.",
            "That project taught me to think about data pipelines the way your Perception team "
            "has to: correctness under real-time pressure, not correctness in isolation. I "
            "designed the middleware's ingestion layer to structure incoming events without "
            "blocking the stream, and built the observability tooling the team now uses daily "
            "to catch pipeline stalls before they become data loss. Separately, as a Web "
            "Development Intern, I built and deployed a production-facing application end to "
            "end -- Next.js and React on the frontend, a Strapi backend for dynamic content -- "
            "which gave me the discipline of shipping something real users depended on.",
            "I also care about the tools I use adding up to a system, not a pile of scripts -- "
            "most recently by extending my own note-taking setup with a small computer-vision "
            "layer to visualize how my ideas connect over time, the same instinct I'd bring to "
            "making Acme's own tooling more legible to the next engineer who touches it.",
            "I'd welcome the chance to talk about how this experience maps to what your "
            "Perception team needs this summer.",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Build the fabricated example letter as a self-check.")
    parser.add_argument("--out", default="demo-cover-letter.docx", help="Output .docx path.")
    args = parser.parse_args()

    if not args.demo:
        parser.error("This CLI entry point only runs the --demo self-check. Call build_cover_letter() "
                      "directly from an agent/skill with a real, human-approved ContentPlan for real use.")

    warnings = build_cover_letter(_demo_plan(), args.out)
    print(f"Wrote {args.out}")
    if warnings:
        print("Format warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("No format warnings -- matches every sourced rule in reference/cover-letter-format-rules.md.")
