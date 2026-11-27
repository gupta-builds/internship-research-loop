"""
internship-research-loop: humanizing-writing skill
Topic: the mechanical checks of the Human Writing Standard (checks 3, 4 and 5) plus
length, ask, greeting, subject, placeholder, chat-residue and character checks.

Usage: python3 humanizer_check.py DRAFT --kind resume|cover|outreach|followup
       [--channel email|message] [--sources FILE ...]
Prints one finding per line as `path:line [tier/kind] token | context`, then a count line.
Exit 0 no blocking finding, 1 blocking findings, 2 the check could not run
(`VALIDATOR NOT RUN: <reason>`). Warn findings print but never fail the check.
Spec: Claude System Implementation Plan, Script specs and Banned and warned phrases.
"""
import argparse
import json
import pathlib
import re
import sys

DATA = pathlib.Path(__file__).resolve().parent / "data"
KINDS = ("resume", "cover", "outreach", "followup")
MESSAGE_KINDS = ("outreach", "followup")

LIMITS_TEXT = """what this check cannot do:
  It matches words and patterns, not meaning. A draft can pass and still read as
  boilerplate, sound louder than its facts, or hide thin thinking (checks 1, 2, 6,
  7, 9, 10 and 11 are the reviewer's). A warn finding is a prompt to look, not proof:
  people cannot reliably tell AI text from human text. Facts are checked by
  evidence_check.py, not here."""

#### character and pattern tables

DASHES = "‒–—―"                    # figure, en, em dash, horizontal bar
ZERO_WIDTH = "​‌‍⁠﻿"
CURLY = {"“": '"', "”": '"', "‘": "'", "’": "'"}
MONTH = (r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?")
DATE_END = re.compile(r"(?:\b(?:19|20)\d\d)\s*$")       # left side of a date range
DATE_START = re.compile(rf"^\s*(?:(?:19|20)\d\d\b|{MONTH}\s+(?:19|20)\d\d\b|(?:spring|summer|fall|autumn|winter)\s+"
                        rf"(?:19|20)\d\d\b|\d{{1,2}}/(?:19|20)\d\d\b|present\b|current\b|now\b)",
                        re.IGNORECASE)
STRUCTURE = (
    (re.compile(r"\bnot only\b[^.!?\n]{0,80}?\bbut\b", re.IGNORECASE), "not only X but also Y"),
    (re.compile(r"\b(?:it's|it is|this is|that's|that is)\s+not\s+(?:just|only|merely|simply)\b"
                r"[^.!?\n]{0,80}?[,;:.]\s*(?:it's|it is|this is|that's|that is)\b", re.IGNORECASE),
     "it's not just X, it's Y"),
    (re.compile(r"\b(?:this|it|that)\s+(?:isn't|is not|wasn't|was not)\b[^.!?\n]{0,80}?[,;:.]"
                r"\s*(?:this|it|that)\s+(?:is|was)\b", re.IGNORECASE), "this isn't X, this is Y"),
)
TRIPLET = re.compile(r"\b[\w'-]+(?:\s+[\w'-]+){0,3},\s+[\w'-]+(?:\s+[\w'-]+){0,3},?\s+(?:and|or)\s+[\w'-]+",
                     re.IGNORECASE)
PLACEHOLDERS = re.compile(r"\[[A-Z][^\]\n]{0,40}\](?!\()|\{\{|\}\}|\bXYZ\b|\bTODO\b|\bTBD\b|"
                          r"<[A-Z][A-Za-z ]{1,30}>|(?i:\blorem ipsum\b|\[insert)")   # case matters: <br> and [x] are not slots
ASK = re.compile(r"\b(?:would you|could you|can you|will you|are you open|are you available|"
                 r"would it be possible|let me know if|i would love to|i'd love to|"
                 r"please (?:let|share|send|consider|connect|reply|forward))\b", re.IGNORECASE)
GREETING = re.compile(r"^(?i:hi|hello|hey|dear),?\s+([A-Z][\w'-]*(?:\s+[A-Z][\w'-]*)*)")
NOT_A_NAME = {"hiring", "team", "sir", "madam", "recruiter", "recruiting", "there", "all", "everyone", "manager",
              "platform", "engineering", "university", "campus", "people", "staff", "committee", "department",
              "friend", "to", "whom", "hr", "talent"}
WORD = re.compile(r"[A-Za-z0-9][\w'.-]*")
# the same sections evidence_check.py drops from the sources
GUIDANCE = re.compile(r"legacy|deprecated|outdated|retired|positioning|preferences|customi[sz]ation|"
                      r"tailoring notes|logged gaps|\bgaps\b|\barchive", re.IGNORECASE)
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


#### error type and argument parser

class NotRun(Exception):
    """raised when an input is missing or unreadable, so the check cannot run."""


class Parser(argparse.ArgumentParser):
    """an argument parser whose usage errors print VALIDATOR NOT RUN and exit 2."""

    def error(self, message):
        """print the not-run line and exit 2."""
        print(f"VALIDATOR NOT RUN: {message}", file=sys.stderr)
        sys.exit(2)


#### reading inputs

def read_text(path):
    """return the text of a file, or raise NotRun."""
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    # Source: https://docs.python.org/3/library/pathlib.html (read_text raises OSError; bad bytes raise UnicodeDecodeError)
    except (OSError, UnicodeDecodeError) as e:
        raise NotRun(f"cannot read {path}: {e}") from e


def blank_out(text):
    """return text with frontmatter and HTML comments replaced by newlines, so line numbers hold."""
    text = text.lstrip("\ufeff")                       # a byte-order mark must not hide frontmatter
    text = re.sub(r"\A---\n.*?\n---[ \t]*\n", keep_lines, text, flags=re.DOTALL)
    return re.sub(r"<!--.*?-->", keep_lines, text, flags=re.DOTALL)


def keep_lines(match):
    """return as many newlines as the matched span holds."""
    return "\n" * match.group(0).count("\n")


def normalize(text):
    """return text with curly quotes straightened and no-break spaces made plain."""
    for curly, plain in CURLY.items():
        text = text.replace(curly, plain)
    return text.replace(" ", " ")


def load_phrases():
    """return a list of (tier, phrase, compiled pattern, swap hint) from banned_phrases.txt."""
    rows = []
    for n, line in enumerate(read_text(DATA / "banned_phrases.txt").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2 or parts[0] not in ("block", "warn", "hws"):
            raise NotRun(f"banned_phrases.txt line {n} is not tier<TAB>phrase")
        words = [re.escape(w) for w in re.split(r"[\s-]+", parts[1].strip().lower())]
        if len(words) == 1 and words[0].isalpha():
            words[0] = inflected(words[0])             # delve also catches delves, delved, delving
        pattern = re.compile(r"(?<!\w)" + r"[\s-]+".join(words) + r"(?!\w)", re.IGNORECASE)
        rows.append((parts[0], parts[1].strip(), pattern, parts[2].strip() if len(parts) > 2 else ""))
    if not rows:
        raise NotRun("banned_phrases.txt holds no phrase rows")
    return rows


def inflected(word):
    """return a pattern for a single word and its -s, -ed and -ing forms."""
    if word.endswith("e"):
        return word[:-1] + r"(?:e|es|ed|ing)"
    return word + r"(?:s|es|ed|ing)?"


def load_limits(kind):
    """return the limits dict for one kind from limits.json."""
    try:
        limits = json.loads(read_text(DATA / "limits.json"))
    # Source: https://docs.python.org/3/library/json.html (JSONDecodeError subclasses ValueError)
    except ValueError as e:
        raise NotRun(f"limits.json does not parse: {e}") from e
    if not isinstance(limits.get(kind), dict):
        raise NotRun(f"limits.json has no entry for {kind}")
    return limits[kind]


#### helpers

def own_words(text):
    """return a source's text without guidance sections (Tailoring Notes, Logged Gaps, positioning and the like)."""
    kept, drop_below = [], None
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            if drop_below is not None and level <= drop_below:
                drop_below = None
            if drop_below is None and GUIDANCE.search(m.group(2)):
                drop_below = level
        if drop_below is None:
            kept.append(line)
    return "\n".join(kept)


def line_of(text, pos):
    """return the 1-based line number of a character offset."""
    return text.count("\n", 0, pos) + 1


def context(text, pos):
    """return the stripped line holding a character offset, cut to 80 characters."""
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return text[start:end if end != -1 else len(text)].strip()[:80]


def body_lines(text):
    """return (line number, line) for every non-empty line."""
    return [(n, line) for n, line in enumerate(text.splitlines(), 1) if line.strip()]


def message_body(text):
    """return (line number, line) of a message's lines after its subject line."""
    lines = body_lines(text)
    if lines and lines[0][1].lower().startswith("subject:"):
        return lines[1:]
    return lines


def opener(sentence):
    """return the first word of a sentence, lowercased, or an empty string."""
    words = WORD.findall(sentence)
    return words[0].lower() if words else ""


def sentences(lines):
    """return (line number, sentence) units: each bullet is one unit, prose splits at . ! ?"""
    out = []
    for n, line in lines:
        if line.lstrip().startswith("#"):
            continue                                   # a heading is not a sentence
        if BULLET.match(line):
            out.append((n, BULLET.sub("", line).strip()))
            continue
        for part in re.split(r"(?<=[.!?])\s+", line.strip()):
            if part:
                out.append((n, part))
    return out


#### checks: each returns a list of (line, tier, kind, token, context)

def check_phrases(text, kind, sources):
    """return phrase findings, one per span and the strongest tier; a phrase in the sources is exempt."""
    by_span = {}
    for tier, _, pattern, hint in load_phrases():
        if tier == "hws":
            tier = "warn" if kind == "resume" else "block"
        if sources and pattern.search(sources):
            continue                                   # Anant's own words are not overridden
        for m in pattern.finditer(text):
            if m.start() in by_span and by_span[m.start()][1] == "block":
                continue                               # leveraged matches the hws and the block row
            ctx = context(text, m.start()) + (f" (swap: {hint})" if hint else "")
            by_span[m.start()] = (line_of(text, m.start()), tier, "phrase", m.group(0), ctx)
    return list(by_span.values())


def check_dashes(text):
    """return a finding for each em or en dash, or a double hyphen, that is not inside a date range."""
    out = []
    # a double hyphen is a dash with spaces on both sides or none; "-p --model" is a command flag
    for m in re.finditer(rf"[{DASHES}]|(?<=\w)--(?=\w)|(?<=\w) -- (?=\w)|(?<=\w) - (?=\w)", text):
        left = text[max(0, m.start() - 12):m.start()]
        right = text[m.end():m.end() + 16]
        if DATE_END.search(left) and DATE_START.match(right):
            continue                                   # a range between dates is exempt
        near = text[max(0, m.start() - 30):m.end() + 30].replace("\n", " ").strip()
        out.append((line_of(text, m.start()), "block", "dash", m.group(0).strip(), near))
    return out


def check_structure(text):
    """return warn findings for negative parallelism, repeated openers and triplet density."""
    out = []
    for pattern, name in STRUCTURE:
        for m in pattern.finditer(text):
            out.append((line_of(text, m.start()), "warn", "structure", name, context(text, m.start())))
    units = sentences(body_lines(text))
    run = 1
    for i in range(1, len(units)):
        same = opener(units[i][1]) and opener(units[i][1]) == opener(units[i - 1][1])
        run = run + 1 if same else 1
        if run == 3:                                   # report once per run of three or more
            n, s = units[i - 2]
            out.append((n, "warn", "structure", f"three openers '{opener(s)}'", s[:80]))
    paragraphs = []
    for p in re.split(r"\n\s*\n", text):
        lines = [line for line in p.splitlines() if line.strip()]
        prose = lines and not lines[0].lstrip().startswith("#") and not all(BULLET.match(x) for x in lines)
        if prose and len(WORD.findall(p)) >= 15:        # a greeting or sign-off line is not a paragraph
            paragraphs.append(p)
    if len(paragraphs) >= 2 and all(TRIPLET.search(p) for p in paragraphs):
        pos = text.find(paragraphs[0])
        out.append((line_of(text, pos), "warn", "structure", "a three-part list in every paragraph",
                    context(text, pos)))
    return out


def check_characters(text):
    """return findings for zero-width characters (block) and curly quotes (warn)."""
    out = []
    for m in re.finditer(f"[{ZERO_WIDTH}]", text):
        out.append((line_of(text, m.start()), "block", "char", f"U+{ord(m.group(0)):04X}", "zero-width character"))
    for m in re.finditer("[" + "".join(CURLY) + "]", text):
        out.append((line_of(text, m.start()), "warn", "char", m.group(0), context(text, m.start())))
    return out


def check_placeholders(text):
    """return a finding for each unfilled template placeholder."""
    return [(line_of(text, m.start()), "block", "placeholder", m.group(0), context(text, m.start()))
            for m in PLACEHOLDERS.finditer(text)]


def check_limits(text, kind, channel):
    """return length, ask, greeting and subject findings for the kind's limits."""
    limits = load_limits(kind)
    out = []
    lines = message_body(text) if kind in MESSAGE_KINDS else body_lines(text)
    words = sum(len(WORD.findall(line)) for _, line in lines)
    if "max_words" in limits and words > limits["max_words"]:
        out.append((1, "block", "length", f"{words} words", f"{kind} allows at most {limits['max_words']}"))
    if "min_words" in limits and words < limits["min_words"]:
        out.append((1, "block", "length", f"{words} words", f"{kind} needs at least {limits['min_words']}"))
    if "max_asks" in limits:
        asks = []
        for n, s in sentences(lines):
            count = len(ASK.findall(s)) or (1 if s.rstrip().endswith("?") else 0)
            asks.extend([(n, s)] * count)                # two requests in one sentence are two asks
        if len(asks) > limits["max_asks"]:
            for n, s in dict.fromkeys(asks):
                out.append((n, "block", "ask", f"{len(asks)} asks", s[:80]))
    if limits.get("greeting_with_name"):
        first = lines[0][1].strip() if lines else ""
        m = GREETING.match(first)
        if not m or any(w.lower().rstrip("s") in NOT_A_NAME or w.lower() in NOT_A_NAME for w in m.group(1).split()):
            out.append((lines[0][0] if lines else 1, "block", "greeting", first[:30] or "(none)",
                        "open with the person's name, such as 'Hi <first name>,'"))
    if limits.get("subject_for_email") and channel == "email":
        all_lines = body_lines(text)
        if not all_lines or not all_lines[0][1].lower().startswith("subject:"):
            out.append((1, "block", "subject", "(none)", "an email starts with a 'Subject:' line"))
    return out


#### driver

def run(draft_path, kind, channel, source_paths):
    """return the sorted findings for one draft, or raise NotRun."""
    raw = read_text(draft_path)
    text = normalize(blank_out(raw))
    if not WORD.search(text):
        raise NotRun(f"{draft_path} has no text")
    sources = " ".join(own_words(normalize(blank_out(read_text(p)))) for p in source_paths)
    found = (check_phrases(text, kind, sources) + check_dashes(text) + check_structure(text)
             + check_characters(blank_out(raw)) + check_placeholders(text) + check_limits(text, kind, channel))
    return sorted(found, key=lambda f: (f[0], f[2]))


def main(argv=None):
    """print findings and return the exit code."""
    ap = Parser(description="check a draft against the mechanical Human Writing checks",
                epilog=LIMITS_TEXT, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft", help="the draft file (markdown or plain text)")
    ap.add_argument("--kind", required=True, choices=KINDS, help="the kind of draft; the limits differ by kind")
    ap.add_argument("--channel", default="email", choices=("email", "message"),
                    help="outreach or follow-up channel; only an email needs a subject line (default email)")
    ap.add_argument("--sources", nargs="*", default=[], metavar="FILE",
                    help="Anant's approved source files; a phrase found in them is exempt from the lists")
    args = ap.parse_args(argv)
    try:
        findings = run(args.draft, args.kind, args.channel, args.sources)
    except NotRun as e:
        print(f"VALIDATOR NOT RUN: {e}", file=sys.stderr)
        return 2
    for n, tier, kind, token, ctx in findings:
        print(f"{args.draft}:{n} [{tier}/{kind}] {token} | {ctx}")
    blocking = sum(1 for f in findings if f[1] == "block")
    print(f"{blocking} blocking, {len(findings) - blocking} warning finding(s)")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
