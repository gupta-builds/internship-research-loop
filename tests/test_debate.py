"""Task L — the deterministic pairwise 'debate' comparator. Each stage is
tested in isolation first (a pairwise case where every stage above it ties,
so the stage under test is what actually decides), then the full per-bucket
sort is tested via run_pipeline._prioritize_and_cap."""
from ingestion.normalize import Listing

from core.debate import compute_bucket_urgency, debate_compare
from core.filter import load_profile

PROFILE = load_profile()
PREFERRED = PROFILE["preferred_companies"]


def _candidate(uid, company, title="Software Engineer Intern", category="Software",
               date_posted=1700000000):
    listing = Listing(company=company, title=title, url=f"https://example.com/{uid}",
                      source="SimplifyJobs", category=category, date_posted=date_posted, raw_id=uid)
    return (f"SimplifyJobs:{uid}", listing)


# --- Stage 1: preferred-company tier (identical dates, same bucket) ---

def test_debate_compare_prefers_preferred_company_with_identical_dates():
    preferred = _candidate("a", "Google", date_posted=1700000000)
    non_preferred = _candidate("b", "Random Startup Inc", date_posted=1700000000)
    assert debate_compare(preferred, non_preferred, PREFERRED) < 0
    assert debate_compare(non_preferred, preferred, PREFERRED) > 0


def test_debate_compare_ties_between_two_preferred_companies_falls_through():
    """Two preferred companies with different dates — stage 1 ties (both
    'high'), recency (stage 3) decides."""
    older = _candidate("a", "Google", date_posted=1600000000)
    newer = _candidate("b", "Microsoft", date_posted=1700000000)
    assert debate_compare(newer, older, PREFERRED) < 0


# --- Stage 2: bucket fill-need (cross-bucket only, same preference tier) ---

def test_debate_compare_prefers_bucket_at_risk_of_going_unfilled():
    """Two non-preferred candidates (stage 1 ties), different buckets, one
    bucket's real candidate pool is smaller than its budget (at risk of
    going unfilled even taking every candidate) — that bucket's candidate
    ranks first despite an identical/older date, since bucket_urgency is
    consulted before recency."""
    other_bucket_candidate = _candidate(
        "a", "Random Startup Inc", title="Demand Planning Analyst Intern",
        category="Other", date_posted=1600000000,
    )  # classifies to 'Other' via no bucket-specific signal
    ai_ml_candidate = _candidate(
        "b", "Random Startup Inc", title="Machine Learning Engineer Intern",
        category="AI/ML", date_posted=1700000000,
    )  # classifies to 'AI/ML', more recent
    # 'Other' bucket: budget 1, only 1 real candidate this run -> urgency 0
    # (not actually short) — construct a genuine shortfall instead: budget
    # exceeds the real candidate count for that bucket.
    budget = {"Other": 3, "AI/ML": 3}
    pool = [other_bucket_candidate]  # only 1 candidate for a 3-slot 'Other' budget -> urgency 2
    urgency = compute_bucket_urgency(pool + [ai_ml_candidate], budget)
    assert urgency["Other"] == 2  # 3 budget - 1 real candidate
    assert urgency["AI/ML"] == 2  # 3 budget - 1 real candidate — tied urgency, won't decide this case

    # Make it a genuine, unambiguous case: 'Other' has 1 real candidate
    # against a 3-slot budget (urgency 2); 'AI/ML' has 3 real candidates
    # against its own 3-slot budget (urgency 0, ample supply).
    ai_ml_candidate_2 = _candidate("c", "Random Startup Inc", title="Machine Learning Engineer Intern",
                                   category="AI/ML", date_posted=1650000000)
    ai_ml_candidate_3 = _candidate("d", "Random Startup Inc", title="Machine Learning Engineer Intern",
                                   category="AI/ML", date_posted=1550000000)
    full_pool = [other_bucket_candidate, ai_ml_candidate, ai_ml_candidate_2, ai_ml_candidate_3]
    urgency = compute_bucket_urgency(full_pool, budget)
    assert urgency["Other"] == 2  # 3 - 1
    assert urgency["AI/ML"] == 0  # 3 - 3, ample supply

    # ai_ml_candidate is more recently posted, but 'Other' is at real risk of
    # going unfilled — its candidate must still rank first.
    assert debate_compare(other_bucket_candidate, ai_ml_candidate, PREFERRED, bucket_urgency=urgency) < 0


def test_debate_compare_skips_bucket_fill_need_for_same_bucket_pair():
    """Same bucket for both candidates — stage 2 is explicitly a no-op here
    per spec, so an artificially lopsided urgency dict must not override
    recency."""
    a = _candidate("a", "Random Startup Inc", date_posted=1600000000)  # both 'Other'
    b = _candidate("b", "Random Startup Inc", date_posted=1700000000)  # both 'Other', more recent
    urgency = {"Other": 999}  # would dominate if (incorrectly) applied same-bucket
    assert debate_compare(b, a, PREFERRED, bucket_urgency=urgency) < 0  # recency still decides


def test_debate_compare_without_bucket_urgency_skips_stage_2():
    """bucket_urgency=None (the default) skips stage 2 entirely, falling
    straight through to recency — this is what every pre-Task-L caller gets."""
    other_bucket_candidate = _candidate("a", "Random Startup Inc", title="Demand Planning Analyst Intern",
                                        category="Other", date_posted=1600000000)
    ai_ml_candidate = _candidate("b", "Random Startup Inc", title="Machine Learning Engineer Intern",
                                 category="AI/ML", date_posted=1700000000)
    assert debate_compare(ai_ml_candidate, other_bucket_candidate, PREFERRED) < 0  # recency wins, no urgency info


# --- Stage 3: recency (everything else equal) ---

def test_debate_compare_recency_is_final_tiebreak():
    older = _candidate("a", "Random Startup Inc", date_posted=1600000000)
    newer = _candidate("b", "Random Startup Inc", date_posted=1700000000)
    assert debate_compare(newer, older, PREFERRED) < 0
    assert debate_compare(older, newer, PREFERRED) > 0


def test_debate_compare_missing_date_posted_sorts_last():
    known = _candidate("a", "Random Startup Inc", date_posted=1700000000)
    unknown = _candidate("b", "Random Startup Inc", date_posted=None)
    assert debate_compare(known, unknown, PREFERRED) < 0
