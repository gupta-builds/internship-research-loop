"""Discovery-time posting-page fetch: one Firecrawl call per NEW match serves
both dossier content (verbatim extraction, trimmed) and the OPT-eligibility
check. Fail-open by design — a Firecrawl outage writes a thin dossier and
never blocks discovery. No LLM call: Firecrawl returns page markdown, the
extraction below is mechanical line filtering.

OPT semantics (per the Phase 6 decision in the Run note): OPT is work
authorization the F-1 student already holds — NOT H-1B sponsorship. Exclude
only on an explicit negative signal: citizenship/US-person requirement,
security-clearance requirement, or an explicit OPT/CPT-not-accepted
statement. "No visa sponsorship" and "background investigation" do NOT
exclude. Signals are checked PER POSTING, not per company — verified against
real data 2026-07-18: Palantir's US Government and Commercial internships
differ on exactly this axis within the same company.
"""
import re
from urllib.parse import urlparse

import requests

FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"
FETCH_TIMEOUT = 120
CONTENT_LIMIT = 7000

# Real bug, confirmed live 2026-07-26: some sources (e.g. SimplifyJobs, for an
# Ellipsis Labs posting) store the Ashby *application-form* URL
# (jobs.ashbyhq.com/<company>/<id>/application) as listing.url instead of the
# posting page itself. That form-only URL renders no job description at all —
# A/B fetched the same live CTGT posting both ways: the base URL returned
# 4015 chars of full content (About/Role/Responsibilities/Qualifications),
# the /application URL returned 1099 chars of bare form fields only ("Upload
# your resume", "LinkedIn Profile", reCAPTCHA, no JD prose whatsoever). Not
# an extraction bug — the fetched page genuinely never had the content.
_ASHBY_APPLICATION_SUFFIX_RE = re.compile(r"/application/?$")


def _content_fetch_url(url: str) -> str:
    """The URL to actually fetch for posting content — strips an Ashby
    application-form suffix so the fetch lands on the real posting page.
    listing.url itself (used for display/apply) is never touched, only the
    URL passed to Firecrawl here."""
    parsed = urlparse(url)
    if parsed.netloc == "jobs.ashbyhq.com" and _ASHBY_APPLICATION_SUFFIX_RE.search(parsed.path):
        return url[: url.rindex("/application")]
    return url

# Built from the actual exclusion language found on live posting pages
# 2026-07-18 (Anduril: "U.S. Person status is required as this position needs
# to access export controlled data") plus the Phase 6 note's two other named
# signals. Deliberately NOT matched: EEO boilerplate ("without regard to ...
# citizenship status"), veteran definitions, and Palantir's conditional
# "willingness to undergo a background investigation".
#
# The export-control/ITAR branch below was added 2026-07-25 against real,
# measured evidence, not a guess: cross-checked all 22 live postings zshah101
# tags `sponsorship: citizens-only` against this regex — only 6 of 22 (27%)
# were caught. Reading the real fetched text for the misses showed a second,
# very common phrasing this regex never covered: defense/ITAR-adjacent
# companies (Saronic, Hermeus, Varda Space, in addition to the already-caught
# Anduril) state the requirement as export-control boilerplate ("requires
# access to export-controlled information or items that require 'U.S.
# Person' status" / "must either be a 'U.S. person' as defined by 22 C.F.R. §
# 120.62") rather than a direct imperative — the existing patterns above
# never match that shape. Adding it raised the measured catch rate to 13/22
# (59%); the remaining misses are not a regex problem — see the Improvement
# Plan note for why (a tagging false positive, a company-level inference not
# stated on that specific posting, and postings where the signal lives in an
# application-form screening question Firecrawl's page scrape never sees).
OPT_EXCLUSION_RE = re.compile(
    r"(u\.?s\.? person (status )?(is )?required"
    r"|must be a u\.?s\.? (citizen|person)"
    r"|u\.?s\.? citizenship (is )?required"
    r"|requires? u\.?s\.? citizenship"
    r"|(active|current) (u\.?s\.? )?(security )?clearance (is )?required"
    r"|must (hold|possess|have) (an? )?(active |current )?(u\.?s\.? )?security clearance"
    r"|(opt|cpt)( candidates?| students?)? (are |is )?not (accepted|eligible|supported)"
    r"|export.control.{0,150}u\.?s\.?\s*person"
    r"|u\.?s\.?\s*person.{0,150}export.control)",
    re.I | re.S,
)


def opt_exclusion(text: str):
    """The matched exclusion phrase, or None if the posting shows no explicit
    negative signal (permissive default, like every other filter here)."""
    m = OPT_EXCLUSION_RE.search(text)
    return m.group(0) if m else None


# Built from the real Optiver "Quantitative Research Intern, PhD (Summer
# 2027)" posting (Greenhouse job id 8451781002 — the same posting manually
# deleted from the vault once already, then resurfaced, 2026-07-29): its
# structured degrees field is empty (Greenhouse carries none), so
# core/filter.py's degrees_eligible() waved it through on missing-data
# permissiveness. Its real content states the requirement as "Currently
# enrolled in a PhD program in Statistics, Computer Science, ..." rather than
# a blunt "PhD required" — the enrolled-in/pursuing-a-phd-program phrasing is
# the literal shape this real posting uses, so it's included as an explicit
# equivalent alongside "PhD required"/"PhD only"/"doctoral candidates only".
# Permissive by default like every other gate here: never fires on "PhD
# preferred", and the window guard below never fires when a Bachelor's/
# Master's is also named nearby (checked against the real Aquatic Capital
# Management, Appian, and Manhattan Associates postings, all of which list
# PhD only as one of several acceptable degrees and must keep passing).
_PHD_ONLY_RE = re.compile(
    r"\bphd\s+(?:is\s+)?(?:required|only)\b"
    r"|\bdoctoral candidates?\s+only\b"
    r"|\b(?:currently\s+)?(?:enrolled in|pursuing)\s+an?\s+(?:phd|doctoral)\s+(?:program|degree)\b",
    re.I,
)


def phd_only_exclusion(text: str):
    """The matched PhD-exclusivity phrase, or None if the posting shows no
    explicit signal that only PhD candidates are eligible. Never fires when a
    Bachelor's/Master's is also named near the match — that's a posting
    listing PhD as one of several acceptable degrees, not a PhD-only one."""
    m = _PHD_ONLY_RE.search(text)
    if not m:
        return None
    window = text[max(0, m.start() - 80): m.end() + 80]
    if re.search(r"bachelor|master|\bbs\b|\bms\b", window, re.I):
        return None
    return m.group(0)


def fetch_posting_markdown(url: str, api_key: str, http_post=None) -> str:
    """Page markdown via Firecrawl (JS-rendered — ATS pages are SPAs).
    Raises requests exceptions on failure; callers treat any failure as
    'no data' and fail open."""
    resp = (http_post or requests.post)(
        FIRECRAWL_SCRAPE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"url": _content_fetch_url(url), "formats": ["markdown"], "waitFor": 8000},
        timeout=FETCH_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("data", {}).get("markdown", "")


_CUT_MARKERS = re.compile(
    r"^(#+\s*)?(submit your application|apply for this job|autofill.*application|create a job alert"
    r"|equal (employment )?opportunity|eeo|voluntary self.identification|privacy (policy|notice)"
    r"|u\.s\. equal employment|by applying.*you (agree|acknowledge))", re.I)
_NOISE = re.compile(
    r"^(\[?!\[|\[back to jobs|\[apply\]|apply\b|select\.\.\.|✱|.*✱\s*$|resume/cv|full name|email\b"
    r"|phone\b|current location|current company|linkedin url|github url|portfolio url|loading$"
    r"|no location found|couldn't auto-read|analyzing resume|success!$|file exceeds|-{3,}$"
    r"|cookie|jobs powered by|©|powered by\s|\[.*\]\(https?://[^)]*\)\s*$|read more$)", re.I)

# Real, distinct bug from the Ashby application-URL one — confirmed 2026-07-26
# on both Google dossiers sourced via Freehire (BS and MS tracks): Google's
# careers site returns a *search-results listing page* shell (~20 unrelated
# job titles, "Back to jobs search" nav, "N jobs matched", pagination) ahead
# of the specific posting's own content in the SAME fetched markdown — not a
# wrong-URL problem like Ashby's /application suffix, the real posting text is
# right there further down. classify() fired on an unrelated listed job's
# title as a result. Whenever one of these listing-shell markers appears,
# everything gathered so far is shell noise — reset and wait for the next
# real heading, which lands on the actual posting content once the shell ends.
_LISTING_SHELL_RESET_RE = re.compile(
    r"^(_arrow_back_|back to jobs search|##?\s*jobs search results|[\d,]+\s+jobs matched"
    r"|showing \d+ to \d+ of|_navigate_next_)", re.I,
)

# ATS UI labels jammed against their values with no separator, real examples
# from the Conagra Brands fixture (List/Dossiers/Other/Demand Science
# Rotational Analyst - Conagra Brands.md): "locationsChicago, Illinois",
# "time typeFull time", "posted onPosted Today", "job requisition idReq-039400".
_ATS_LABEL_RUN_ON_RE = re.compile(
    r"^(locations|time type|posted on|job requisition id|time left to apply)(?=\S)", re.M,
)

# A posting's own section names, real shape confirmed against the Appian
# ("**Basic Qualifications**", "**Benefits**") and Conagra ("**Compensation**",
# "**Our Benefits**") fixtures: a fully-bolded standalone line naming one of
# these sections. Deliberately narrow — only fires when the *whole* line is
# one bold span ending in a real section keyword, so inline bold emphasis
# ("our values of **Intensity** and **Excellence**...") and non-section bold
# lines ("**Why should you kick off your career with Conagra?**") are left as
# flattened prose, per the "don't invent section boundaries" rule.
_BOLD_SECTION_RE = re.compile(r"^\*\*([^*]+?)\*\*:?$")
_SECTION_KEYWORD_RE = re.compile(r"(responsibilities|qualifications|requirements|benefits|compensation)$", re.I)

# Real, from the Manhattan Associates fixture (List/Dossiers/1 - AI & ML/A.I.
# Developer Co-Op (Boston, MA) - Manhattan Associates.md): a "Follow Us"
# heading followed by a bulleted LinkedIn/X/Facebook link list, pure chrome.
_FOLLOW_US_HEADING_RE = re.compile(r"^#{1,6}\s*follow us\s*$", re.I)
# Real Manhattan Associates link shape includes a markdown title after the
# URL ('[LinkedIn](https://...4376?trk=tyah "LinkedIn")') — the optional
# quoted-title group handles that, not just a bare '(url)'.
_LINK_BULLET_RE = re.compile(r'^-\s*\[.+\]\(https?://\S+?(?:\s+"[^"]*")?\)\s*$')


def _dedupe_paragraphs(markdown: str, min_len: int = 40) -> str:
    """Drops a paragraph line that repeats verbatim later in the same fetch,
    keeping the first occurrence — real example: the Conagra fixture's whole
    'About Us' paragraph appears twice. Real fetched markdown from this
    pipeline's sources renders each prose paragraph as one continuous line
    (confirmed against the Manhattan Associates/Appian/Optiver fixtures), so
    line-level comparison catches this without needing blank-line block
    boundaries the source markdown may not consistently have. min_len guards
    against deduping short, legitimately-repeated lines (labels, headings)
    that aren't real paragraph content."""
    seen, kept = set(), []
    for line in markdown.splitlines():
        key = line.strip()
        if len(key) >= min_len:
            if key in seen:
                continue
            seen.add(key)
        kept.append(line)
    return "\n".join(kept)


def _strip_trailing_social_chrome(lines: list) -> list:
    out, skip_links = [], False
    for line in lines:
        if _FOLLOW_US_HEADING_RE.match(line.strip()):
            skip_links = True
            continue
        if skip_links and _LINK_BULLET_RE.match(line.strip()):
            continue
        skip_links = False
        out.append(line)
    return out


def extract_content(markdown: str, limit: int = CONTENT_LIMIT) -> str:
    """The posting's substantive text: from the first real heading up to the
    application-form/EEO chrome, minus nav/form/boilerplate lines. Verbatim
    lines, never a summary — but deduped (no repeated paragraph), chrome-split
    (ATS UI labels get their own line), and structured (a source's own bolded
    section names become real '###' headings) per the Internship Notes
    Standard §2. Blank lines and '---' rules dropped to satisfy the vault's
    format conventions (see validate.check_format_compliance)."""
    markdown = _dedupe_paragraphs(markdown)
    markdown = _ATS_LABEL_RUN_ON_RE.sub(lambda m: m.group(1) + "\n", markdown)

    out, started = [], False
    for line in markdown.splitlines():
        s = line.strip()
        if _CUT_MARKERS.match(s):
            break
        if _LISTING_SHELL_RESET_RE.match(s):
            started, out = False, []
            continue
        if not started:
            if s.startswith("#") and len(s) > 4:
                started = True
            else:
                continue
        if not s or _NOISE.match(s):
            continue
        section = _BOLD_SECTION_RE.match(s)
        if section and _SECTION_KEYWORD_RE.search(section.group(1).strip()):
            s = f"### {section.group(1).strip()}"
        out.append(s)
        if len("\n".join(out)) > limit:
            break
    return "\n".join(_strip_trailing_social_chrome(out))
