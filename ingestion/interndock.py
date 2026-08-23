"""InternDock (interndock.com) — periodic "drop" guide posts, not a JSON feed.

Checked live 2026-08-24 (Task 3, Phase 4 sourcing round): interndock.com/tracker/guides/*
pages are client-rendered (a bare `<div id="root">` SPA shell — `requests.get`
returns ~6.5KB of no-content HTML), so real posting content needs the same
JS-rendering Firecrawl fetch already used for individual ATS posting pages
elsewhere in this pipeline (ingestion/posting_page.py's fetch_posting_markdown,
reused here rather than duplicated).

The index precondition Task 3 required IS met: interndock.com/sitemap.xml is a
real, live, plain-HTTP-fetchable XML file (no JS needed) listing every
published page, confirmed live 2026-08-24 with 67 real <loc> entries — several
more "drop"-shaped guide slugs than the two originally found by hand
(summer-2027-internship-drop-august-2026, fresh-internship-drop-summer-2027-fall-2026),
meaning InternDock publishes these periodically, not once. This makes InternDock
a real ongoing source, not a one-time snapshot.

The slug alone is NOT a reliable classifier, though — checked live 2026-08-24:
"summer-2027-internship-programs-open-now" reads exactly like a drop by its
name but is actually a prose career-advice article naming nine companies with
zero structured postings. "summer-2027-internships-mega-drop-257-roles" (also
checked live) IS a real 257+-posting drop. So CANDIDATE_SLUG_RE below is
deliberately loose (just enough to avoid Firecrawl-fetching obviously
unrelated pages like /pricing or a resume-template guide) — the real gate is
structural: parse_interndock_postings()'s match count against
MIN_POSTINGS_FOR_DROP, checked on the actually-fetched content, same
"mechanical filter on real structure, not the URL/title" pattern this
pipeline already uses for Ashby's employmentType and Greenhouse's title text.

POSTING_LINE_RE is built from real, verbatim text (WebFetch, 2026-08-24) of
interndock.com/tracker/guides/summer-2027-internship-drop-august-2026's first
15 real entries, e.g.:
  - Summer 2027 Software Developer Internship — RQ225450 — [Apply](https://gdit.wd5.myworkdayjobs.com/external_career_site/job/USA-MD-Annapolis-Junction/Summer-2027-Software-Developer-Internship_RQ225450-1) *GDIT, Annapolis Junction, MD*
  - Software Engineer Intern — Summer 2027 — [Apply](https://jobs.lever.co/belvederetrading/10746b3d-1760-4573-9b63-b93f5a5e4fc0) *Belvedere Trading, Chicago, IL*
  - Summer 2027 Software Engineering Intern — [Apply](https://job-boards.greenhouse.io/thenuclearcompany/jobs/5383236008) *The Nuclear Company, See posting*
Not the "- [Title](URL) *Company, Location*" shape a prior session's summary
guessed — the real link text is always the literal word "Apply", and the
posting title (which may itself contain an em-dash-separated requisition id)
sits before it. "*Company, See posting*" is InternDock's own placeholder for
a posting with no location — mapped to no location data, same permissive-by-
default convention as every other source's missing-location case.

Scope of this module: detect candidate drop pages and parse their postings
into plain dicts. Deliberately NOT wired into run_pipeline.py's SOURCES/FEEDS
yet — that needs its own design pass (a raw_id strategy for postings with no
first-party id at all, a "seen guide URLs" state file, and a cadence decision
the way recheck.py earned its own daily cron instead of running hourly) —
flagged as the explicit next step, not assumed here.
"""
import re

import requests

from ingestion.posting_page import fetch_posting_markdown

INTERNDOCK_SITEMAP_URL = "https://www.interndock.com/sitemap.xml"
TIMEOUT = 30

_LOC_RE = re.compile(r"<loc>([^<]*/tracker/guides/[^<]+)</loc>")

# Loose pre-filter only — cost control against Firecrawl-fetching every guide
# (most are plain career-advice content, not posting dumps). The real
# classifier is structural, applied to the fetched content by
# fetch_interndock_drop() below.
CANDIDATE_SLUG_RE = re.compile(r"intern.*(drop|list|open-now)", re.I)

# The company field is "Company, Location" or InternDock's own "Company, See
# posting" placeholder when no location is stated. Title may itself contain
# an em-dash-separated requisition id (real case: "... — RQ225450 —"), so the
# title capture is non-greedy up to the literal "— [Apply](" anchor, which
# appears exactly once per line.
POSTING_LINE_RE = re.compile(
    r"^-\s+(?P<title>.+?)\s+—\s+\[Apply\]\((?P<url>https?://[^\s)]+)\)\s+"
    r"\*(?P<company>[^,*]+)(?:,\s*(?P<location>[^*]+))?\*",
    re.MULTILINE,
)

# Three real confirmed drops ran 257-720 real postings; the one real false
# positive checked (a career-advice article sharing a drop-shaped slug) had
# zero structural matches — this threshold only needs to sit above fixture-
# scale noise, not tuned tight against the real gap.
MIN_POSTINGS_FOR_DROP = 10


def fetch_interndock_drop_candidates(http_get=None) -> list:
    """Real, live guide URLs from the sitemap whose slug loosely looks
    drop-shaped. Zero-Firecrawl — sitemap.xml is plain, server-rendered XML."""
    get = http_get or requests.get
    resp = get(INTERNDOCK_SITEMAP_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    urls = _LOC_RE.findall(resp.text)
    return [u for u in urls if CANDIDATE_SLUG_RE.search(u)]


def parse_interndock_postings(markdown: str) -> list:
    """[{title, url, company, location}, ...] from a fetched drop page's
    markdown. location is "" when InternDock's own text says no location
    (the literal "See posting" placeholder) — permissive-by-default, same as
    every other source's missing-location case, not a real location string."""
    postings = []
    for m in POSTING_LINE_RE.finditer(markdown):
        loc = (m.group("location") or "").strip()
        if loc.lower() == "see posting":
            loc = ""
        postings.append({
            "title": m.group("title").strip(),
            "url": m.group("url").strip(),
            "company": m.group("company").strip(),
            "location": loc,
        })
    return postings


def fetch_interndock_drop(url: str, api_key: str, http_post=None) -> list:
    """Firecrawl-fetches one candidate URL and parses it. Returns [] both on
    fetch failure (fail-open, same as every other Firecrawl call in this
    pipeline) and when the page structurally isn't a real drop (below
    MIN_POSTINGS_FOR_DROP matches) — callers can't tell the two apart from
    the return value alone, same as every other "no data" case here."""
    try:
        markdown = fetch_posting_markdown(url, api_key, http_post=http_post)
    except requests.RequestException:
        return []
    postings = parse_interndock_postings(markdown)
    if len(postings) < MIN_POSTINGS_FOR_DROP:
        return []
    return postings
