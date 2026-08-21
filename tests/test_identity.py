import json
from pathlib import Path

import pytest

from core.filter import load_profile
from core.identity import company_matches_preference, compute_uid, cross_source_key, extract_ats_job_id
from ingestion.normalize import normalize_josegael, normalize_simplify

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIXTURES / name).read_text())


def test_simplify_uid_uses_upstream_id():
    raw = _load("simplifyjobs.json")[0]
    uid = compute_uid(normalize_simplify(raw))
    assert uid == f"SimplifyJobs:{raw['id']}"


def test_josegael_uid_uses_upstream_id():
    raw = _load("josegael.json")[0]
    uid = compute_uid(normalize_josegael(raw))
    assert uid == f"Jose-Gael-Cruz-Lopez:{raw['id']}"


def test_uids_stable_across_recomputation():
    raw = _load("simplifyjobs.json")[0]
    uid1 = compute_uid(normalize_simplify(raw))
    uid2 = compute_uid(normalize_simplify(raw))
    assert uid1 == uid2


def test_uids_unique_across_distinct_listings():
    raws = _load("simplifyjobs.json")
    uids = [compute_uid(normalize_simplify(r)) for r in raws]
    assert len(uids) == len(set(uids))


def test_missing_raw_id_raises():
    """Both remaining sources guarantee an id; a listing without one is a bug
    (the hash fallback left with zapplyjobs), not something to key silently."""
    from ingestion.normalize import Listing

    orphan = Listing(company="Acme", title="SWE Intern", url="https://acme.example", source="SimplifyJobs")
    with pytest.raises(ValueError, match="no upstream id"):
        compute_uid(orphan)


def test_cross_source_key_normalizes_case_and_whitespace():
    assert cross_source_key("MLH (Major League Hacking)", "MLH Fellowship") == \
        cross_source_key("  mlh (major league hacking)", "mlh   fellowship ")
    assert cross_source_key("MLH", "Fellowship") != cross_source_key("MLH", "Other Program")


# --- Task D: URL/job-id-based cross-source dedup — four real 2026-07-29 incidents ---

def test_extract_ats_job_id_greenhouse():
    assert extract_ats_job_id("https://job-boards.greenhouse.io/virtu/jobs/8624410002") == "8624410002"


def test_extract_ats_job_id_lever_ignores_apply_suffix():
    """Real Palantir 'Intel' FDSE duplicate: SimplifyJobs' URL carries a
    trailing /apply, zshah101's doesn't — same Lever job id either way."""
    with_apply = "https://jobs.lever.co/palantir/9e40d77f-b07c-437b-98e7-def9b0184d89/apply"
    without_apply = "https://jobs.lever.co/palantir/9e40d77f-b07c-437b-98e7-def9b0184d89"
    assert extract_ats_job_id(with_apply) == "9e40d77f-b07c-437b-98e7-def9b0184d89"
    assert extract_ats_job_id(with_apply) == extract_ats_job_id(without_apply)


def test_extract_ats_job_id_google_careers_results_url():
    """Real Google BS/MS Summer 2027 SWE intern duplicate: vanshb03 and
    Freehire both resolve to the identical numeric id embedded in
    .../jobs/results/85564713261245126."""
    url = "https://www.google.com/about/careers/applications/jobs/results/85564713261245126"
    assert extract_ats_job_id(url) == "85564713261245126"


def test_extract_ats_job_id_none_when_no_recognizable_id():
    assert extract_ats_job_id("https://t.me/getjobss/7795") is None


# --- Task K: preferred_companies matching ---

PROFILE = load_profile()


def test_company_matches_preference_punctuation_insensitive_real_de_shaw_case():
    """Real profile.yaml entry 'D.E. Shaw' must match the real vault dossier
    company string 'DE Shaw' (Software Developer Intern - DE Shaw.md)."""
    preferred = PROFILE["preferred_companies"]
    assert company_matches_preference("D.E. Shaw", preferred) == "high"
    assert company_matches_preference("DE Shaw", preferred) == "high"


def test_company_matches_preference_case_insensitive():
    preferred = PROFILE["preferred_companies"]
    assert company_matches_preference("google", preferred) == "high"
    assert company_matches_preference("GOOGLE", preferred) == "high"


def test_company_matches_preference_none_for_unlisted_company():
    preferred = PROFILE["preferred_companies"]
    assert company_matches_preference("Random Startup Inc", preferred) is None


def test_company_matches_preference_none_for_empty_preferred_dict():
    assert company_matches_preference("Google", {}) is None


def test_extract_ats_job_id_google_pattern_is_domain_anchored():
    """Fix 1, Prompt 5 review (2026-07-30): the Google pattern used to have no
    domain anchor, unlike the Greenhouse/Lever/Ashby patterns above — it
    matched the .../careers/jobs/results/<id> path shape on ANY domain, so an
    unrelated company's own careers page with a coincidentally-matching
    numeric id would collapse into the same cross_source_key as a real Google
    posting and get silently rejected as a duplicate."""
    assert extract_ats_job_id("https://random-startup.com/careers/jobs/results/12345") is None


def test_cross_source_key_prefers_job_id_over_text_real_virtu_triple():
    """Real, confirmed 2026-07-29 — a genuine TRIPLE duplicate: three
    different title strings (SimplifyJobs, zshah101, vanshb03), identical
    greenhouse.io/virtu/jobs/8624410002 URL. Company+title text alone would
    have produced three different keys; the job-id key collapses all three."""
    url = "https://job-boards.greenhouse.io/virtu/jobs/8624410002"
    keys = {
        cross_source_key("Virtu Financial", "2027 Internship - Software Engineer", url),
        cross_source_key("Virtu Financial", "Software Engineer Intern - Software Engineer", url),
        cross_source_key("Virtu Financial", "Software Engineer Intern", url),
    }
    assert len(keys) == 1


def test_cross_source_key_prefers_job_id_over_text_real_google_case():
    """Real Google BS vs MS title-string variant, same numeric job id."""
    url = "https://www.google.com/about/careers/applications/jobs/results/85564713261245126"
    assert cross_source_key("Google", "Software Engineering Intern", url) == \
        cross_source_key("Google", "Software Engineering Intern, BS, Summer 2027", url)


def test_cross_source_key_prefers_job_id_over_text_real_palantir_cross_bucket_case():
    """Real Palantir 'Intel' FDSE duplicate across two different buckets
    (SimplifyJobs landed it in AI/ML, zshah101 in Fullstack) — same Lever
    job id either way, distinct from the other three incidents in that the
    dossiers also disagreed with each other about classification."""
    assert cross_source_key(
        "Palantir", "Forward Deployed Software Engineer Intern - Intel",
        "https://jobs.lever.co/palantir/9e40d77f-b07c-437b-98e7-def9b0184d89/apply",
    ) == cross_source_key(
        "Palantir", "Forward Deployed Software Engineer, Internship - Intel",
        "https://jobs.lever.co/palantir/9e40d77f-b07c-437b-98e7-def9b0184d89",
    )


def test_cross_source_key_falls_back_to_text_for_company_name_variant_real_aquatic_case():
    """Real Aquatic vs Aquatic Capital Management: same Greenhouse posting,
    same URL — job id alone already collapses this one, but confirms the
    company-name-variant incident (the one case the original company-alias-
    map idea would have caught) is still covered."""
    url = "https://job-boards.greenhouse.io/aquaticcapitalmanagement/jobs/8489233002"
    assert cross_source_key("Aquatic", "Software Engineer Intern", url) == \
        cross_source_key("Aquatic Capital Management", "Software Engineer Intern", url)


def test_cross_source_key_falls_back_to_normalized_text_when_no_job_id():
    """A source/ATS with no recognizable job id in its URL shape (e.g.
    Freehire's Telegram links) must still fall back to the original
    normalized-company+title key rather than losing dedup entirely."""
    assert cross_source_key("MLH", "Fellowship", "https://t.me/getjobss/7795") == \
        cross_source_key("MLH", "Fellowship", "https://t.me/getjobss/9999")
