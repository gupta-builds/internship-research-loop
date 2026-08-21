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
    r"|cookie|jobs powered by|©|powered by\s|\[.*\]\(https?://[^)]*\)\s*$)", re.I)


def extract_content(markdown: str, limit: int = CONTENT_LIMIT) -> str:
    """The posting's substantive text: from the first real heading up to the
    application-form/EEO chrome, minus nav/form/boilerplate lines. Verbatim
    lines, never a summary. Blank lines and '---' rules dropped to satisfy
    the vault's format conventions (see validate.check_format_compliance)."""
    out, started = [], False
    for line in markdown.splitlines():
        s = line.strip()
        if _CUT_MARKERS.match(s):
            break
        if not started:
            if s.startswith("#") and len(s) > 4:
                started = True
            else:
                continue
        if not s or _NOISE.match(s):
            continue
        out.append(s)
        if len("\n".join(out)) > limit:
            break
    return "\n".join(out)
