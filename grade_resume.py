#!/usr/bin/env python3
"""Layer 6 — resume grader: keyword-overlap scorer, no LLM, no network.

Ranks Main Resume.md's `#skill/*`-tagged bullets against a pasted JD so the
top-third tailoring step of the Internship Pipeline starts from evidence,
not vibes:

    python grade_resume.py jd.txt            # or: pbpaste | python grade_resume.py -
    python grade_resume.py jd.txt --resume "path/to/Main Resume.md"

Without --resume, reads $JARVIS_DIR/20_Progress/Internship/Resumes/Main Resume.md.
"""
import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

# Vault-relative, resolved against JARVIS_DIR — the same env var run_pipeline.py,
# recheck.py, revalidate.py and screen_report.py already use for "where is the
# Jarvis checkout". This used to be a hardcoded /mnt/d/Users/_Anant/... path
# that only existed on the original laptop (found 2026-10-03 during the
# two-laptop migration audit: it fails outright on dell-latitude).
RESUME_RELPATH = "20_Progress/Internship/Resumes/Main Resume.md"
# Just enough stopwords to keep JD boilerplate from scoring; not a linguistics project.
STOP = set("""a an and are as at be by for from has have in is it of on or our the
to we will with you your this that they them their its into within using able
work team who what when where required preferred qualifications responsibilities
experience years strong skills ability including etc more than least about
""".split())
_TAG_RE = re.compile(r"#skill/[\w-]+")
_WORD_RE = re.compile(r"[a-z][a-z0-9.+#/-]{2,}")


def parse_bullets(resume_md: str) -> list:
    """(text, tags) for every '- ' line carrying at least one #skill tag."""
    out = []
    for line in resume_md.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        tags = _TAG_RE.findall(line)
        if not tags:
            continue
        text = _TAG_RE.sub("", line[2:]).replace("`", "").strip()
        out.append((text, tags))
    return out


def keywords(text: str) -> set:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in STOP}


def grade(resume_md: str, jd_text: str) -> list:
    """Bullets ranked by distinct-JD-keyword overlap: (score, text, tags, matched)."""
    jd = keywords(jd_text)
    scored = []
    for text, tags in parse_bullets(resume_md):
        matched = sorted(jd & keywords(text))
        scored.append((len(matched), text, tags, matched))
    return sorted(scored, key=lambda s: -s[0])


def resolve_resume_path(resume_arg, environ=None) -> str:
    """--resume wins; otherwise $JARVIS_DIR/<RESUME_RELPATH>. Exits with a
    clear message (never guesses a path) when neither is available."""
    if resume_arg:
        return resume_arg
    environ = os.environ if environ is None else environ
    jarvis_dir = environ.get("JARVIS_DIR")
    if not jarvis_dir:
        sys.exit("no resume path: pass --resume PATH, or set JARVIS_DIR to your Jarvis vault checkout")
    return str(Path(jarvis_dir) / RESUME_RELPATH)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("jd", help="path to a file with the pasted JD, or '-' for stdin")
    ap.add_argument("--resume", default=None, help="path to Main Resume.md (default: $JARVIS_DIR/" + RESUME_RELPATH + ")")
    ap.add_argument("--top", type=int, default=5, help="bullets to recommend")
    args = ap.parse_args()

    jd_text = sys.stdin.read() if args.jd == "-" else open(args.jd, encoding="utf-8").read()
    resume_md = open(resolve_resume_path(args.resume), encoding="utf-8").read()
    ranked = grade(resume_md, jd_text)
    if not ranked:
        sys.exit("no #skill-tagged bullets found in the resume file")

    tag_totals = Counter()
    for score, _, tags, _ in ranked:
        for t in tags:
            tag_totals[t] += score

    print(f"Top {args.top} bullets for this JD (lead with these):\n")
    for score, text, tags, matched in ranked[: args.top]:
        print(f"  [{score:2d}] {text}")
        print(f"       {' '.join(tags)} — matched: {', '.join(matched) or 'nothing'}")
    print("\nTag emphasis (reorder Skills section to match):")
    for tag, total in tag_totals.most_common():
        print(f"  {total:3d}  {tag}")
    rest = ranked[args.top:]
    if rest:
        print(f"\nRemaining {len(rest)} bullets scored "
              f"{rest[0][0]} down to {rest[-1][0]}.")


if __name__ == "__main__":
    main()
