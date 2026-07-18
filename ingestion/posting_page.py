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

import requests

FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"
FETCH_TIMEOUT = 120
CONTENT_LIMIT = 7000

# Built from the actual exclusion language found on live posting pages
# 2026-07-18 (Anduril: "U.S. Person status is required as this position needs
# to access export controlled data") plus the Phase 6 note's two other named
# signals. Deliberately NOT matched: EEO boilerplate ("without regard to ...
# citizenship status"), veteran definitions, and Palantir's conditional
# "willingness to undergo a background investigation".
OPT_EXCLUSION_RE = re.compile(
    r"(u\.?s\.? person (status )?(is )?required"
    r"|must be a u\.?s\.? (citizen|person)"
    r"|u\.?s\.? citizenship (is )?required"
    r"|requires? u\.?s\.? citizenship"
    r"|(active|current) (u\.?s\.? )?(security )?clearance (is )?required"
    r"|must (hold|possess|have) (an? )?(active |current )?(u\.?s\.? )?security clearance"
    r"|(opt|cpt)( candidates?| students?)? (are |is )?not (accepted|eligible|supported))",
    re.I,
)


def opt_exclusion(text: str):
    """The matched exclusion phrase, or None if the posting shows no explicit
    negative signal (permissive default, like every other filter here)."""
    m = OPT_EXCLUSION_RE.search(text)
    return m.group(0) if m else None


def fetch_posting_markdown(url: str, api_key: str, http_post=None) -> str:
    """Page markdown via Firecrawl (JS-rendered — ATS pages are SPAs).
    Raises requests exceptions on failure; callers treat any failure as
    'no data' and fail open."""
    resp = (http_post or requests.post)(
        FIRECRAWL_SCRAPE_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"url": url, "formats": ["markdown"], "waitFor": 8000},
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
