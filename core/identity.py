"""Layer 3 — stable dedup keys for a Listing.

Both remaining sources carry a stable upstream id, so the uid is simply
source:raw_id. (The content-hash fallback existed only for zapplyjobs,
removed as a source 2026-07-18.)

cross_source_key() is the secondary dedup identity: the same program listed
by two different sources gets two different uids but one cross-source key.
"""
import re

# Real, confirmed 2026-07-29 — four real duplicate incidents the old
# normalized-company+title key missed because either string varied across
# sources: Aquatic vs Aquatic Capital Management (company-name variant),
# Google BS/MS Summer 2027 SWE intern (title-string variant, same numeric job
# id in both URLs), Virtu Financial's genuine triple duplicate (three
# different title strings, identical greenhouse.io/virtu/jobs/8624410002 URL
# across SimplifyJobs/zshah101/vanshb03), and Palantir's "Intel" FDSE role
# duplicated across two different buckets (same Lever job id via SimplifyJobs
# and zshah101). A URL-embedded ATS job id is a stronger identity signal than
# company+title text in every one of these — extract it when present, fall
# back to the normalized-text key only when the URL carries no recognizable id.
_ATS_JOB_ID_PATTERNS = (
    re.compile(r"greenhouse\.io/[^/]+/jobs/(\d+)", re.I),
    re.compile(r"lever\.co/[^/]+/([0-9a-f-]{36})", re.I),
    re.compile(r"ashbyhq\.com/[^/]+/([0-9a-f-]{36})", re.I),
    # Google's own careers site embeds a long numeric id after .../jobs/results/
    # — anchored to google.com (real examples: www.google.com/about/careers/
    # applications/jobs/results/...), matching the domain-scoping discipline
    # the other three patterns already follow. Real bug, confirmed 2026-07-30:
    # without the domain anchor, this pattern matched the same path shape on
    # ANY domain (e.g. a random unrelated company's own careers page happening
    # to use a numeric job id at .../careers/jobs/results/<id>), which would
    # silently collapse an unrelated posting into the same cross_source_key
    # as a real Google posting and reject it as a duplicate.
    re.compile(r"google\.com/.*?careers/(?:applications/)?jobs/results/(\d+)", re.I),
    # Workday requisition id, added 2026-08-23 (dossier audit) — real
    # confirmed duplicate pairs: FTI Consulting "Technology Intern" (same
    # requisition JR260339, one URL under the ...FTIConsultingCareers site,
    # the other under ...FTIConsultingCareersPrivate, one with a trailing
    # -1), Medtronic "Software Engineer(ing) Intern" (same requisition
    # R73630, one under ...medtroniccareers, the other under
    # ...redeploymentmedtroniccareers, one with -1), Continental Resources
    # "Data Analyst Intern" (same requisition R02591, identical URL apart
    # from the trailing -1). The id is always the last underscore-delimited
    # path segment, sometimes followed by a '-N' variant suffix — greedy
    # '.+_' lands on that last underscore regardless of earlier underscores
    # in the site-path segment (e.g. 'CLR_Careers'), and '-N' is captured
    # separately so it's excluded from the id, unifying both variants.
    re.compile(r"myworkdayjobs\.com/.+_([A-Za-z]+\d+)(?:-\d+)?/?$", re.I),
)


def extract_ats_job_id(url: str) -> str:
    """The ATS-native job id embedded in url, or None if url is from a
    source/ATS with no recognizable id in its URL shape (e.g. Freehire's
    Telegram links, Workday's slug-only URLs)."""
    for pattern in _ATS_JOB_ID_PATTERNS:
        m = pattern.search(url or "")
        if m:
            return m.group(1)
    return None


def compute_uid(listing) -> str:
    if not listing.raw_id:
        raise ValueError(f"listing from {listing.source} has no upstream id: {listing.company!r}")
    return f"{listing.source}:{listing.raw_id}"


# Not cross_source_key()'s space-preserving norm() reused verbatim: that one
# collapses punctuation to a single space (needed to keep title text
# word-tokenized — "Intern Co-op" vs "Intern/Co-op" must still split into the
# same words). A company name is a short identifier, not sentence-shaped
# text, and the real case this needs to catch ("D.E. Shaw" vs "DE Shaw")
# fails under that space-preserving version — "d e shaw" != "de shaw". Fold
# out all non-alphanumeric characters entirely instead, so both collapse to
# the identical "deshaw".
def _norm_company(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def cross_source_key(company: str, title: str, url: str = "") -> str:
    job_id = extract_ats_job_id(url)
    if job_id:
        return f"jobid:{job_id}"
    # Punctuation-insensitive: "Intern Co-op" and "Intern/Co-op" are the same
    # posting (real Marmon dup that slipped past a whitespace-only key,
    # caught in the 2026-07-18 dossier audit).
    norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return f"{norm(company)}|{norm(title)}"


def company_matches_preference(company: str, preferred: dict) -> str:
    """The matched preference tier (e.g. 'high'), or None if company isn't in
    preferred. Same punctuation/case-insensitive normalization as
    cross_source_key()'s norm(), so 'D.E. Shaw' and 'DE Shaw' both match —
    preferred_companies (core/profile.yaml) is a human-maintained config dict,
    not derived from live data, so this is a pure string match with no new
    network call or source to verify (Prompt 5 Task K)."""
    target = _norm_company(company)
    for name, tier in (preferred or {}).items():
        if _norm_company(name) == target:
            return tier
    return None
