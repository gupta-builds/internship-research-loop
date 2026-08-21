"""Layer 3.5 — the "debate": a deterministic pairwise comparator that decides
which of two candidates ranks first when both compete for this run's
per-bucket write budget (Prompt 5 Task L). Zero-LLM by design, same rule as
everywhere else in this codebase's unattended path (see the repo's own
CLAUDE.md) — "debating between two internships" is a real comparator
function, not a model call. Used via functools.cmp_to_key() to produce a
full deterministic ranking in one efficient sort: mathematically the same
outcome as running every pairwise comparison, without the wasted O(n^2)
redundant comparisons a literal round-robin would do.

Three priority stages, each only breaking ties left by the stage above it —
kept as separable comparison stages rather than one blended numeric score,
so a human reading debate_compare can see exactly why any two candidates
were ordered the way they were:
  1. Preferred-company tier (core.identity.company_matches_preference)
  2. Bucket fill-need (cross-bucket only — see the note on bucket_urgency
     below for why this stage has no live effect in the current call site)
  3. Recency (most-recently-posted-first, the pre-existing rule)
"""
from core.classify import classify
from core.identity import company_matches_preference

_TIER_RANK = {"high": 0}


def _preference_rank(company: str, preferred_companies: dict) -> int:
    tier = company_matches_preference(company, preferred_companies)
    return _TIER_RANK.get(tier, 1) if tier else 1


def debate_compare(a, b, preferred_companies: dict, bucket_urgency: dict = None) -> int:
    """Standard cmp semantics: negative if a should rank first, positive if
    b should, 0 if the next stage must decide. a and b are (uid, listing)
    tuples, the same shape _prioritize_and_cap already sorts.

    bucket_urgency (optional): {bucket_name: shortfall_score}, precomputed
    once per run as max(0, budget[bucket] - candidate_count[bucket]) — a
    higher score means that bucket has fewer real candidates this run than
    its budget, i.e. it's at risk of going unfilled even taking every
    candidate it has. Only consulted when a and b are headed for DIFFERENT
    buckets; a same-bucket comparison skips stage 2 entirely, per spec.

    Note on reachability: _prioritize_and_cap (run_pipeline.py) partitions
    candidates by bucket before sorting, so every debate_compare call it
    makes is already same-bucket — stage 2 never actually fires through that
    call path today. It's implemented and tested here as a real, correct,
    independently-callable stage (per Task L's explicit spec and test
    requirements), not dead code: a future architecture change that compares
    candidates across buckets directly would exercise it immediately, and no
    second mechanism would need to be built to support that."""
    uid_a, listing_a = a
    uid_b, listing_b = b

    rank_a = _preference_rank(listing_a.company, preferred_companies)
    rank_b = _preference_rank(listing_b.company, preferred_companies)
    if rank_a != rank_b:
        return rank_a - rank_b

    if bucket_urgency is not None:
        bucket_a, _ = classify(listing_a.title, listing_a.category, "")
        bucket_b, _ = classify(listing_b.title, listing_b.category, "")
        if bucket_a != bucket_b:
            urgency_a = bucket_urgency.get(bucket_a, 0)
            urgency_b = bucket_urgency.get(bucket_b, 0)
            if urgency_a != urgency_b:
                return urgency_b - urgency_a  # higher urgency ranks first

    date_a = listing_a.date_posted or 0
    date_b = listing_b.date_posted or 0
    return date_b - date_a  # more recent ranks first


def compute_bucket_urgency(candidates: list, budget: dict) -> dict:
    """{bucket: max(0, budget[bucket] - candidate_count[bucket])} for every
    bucket present in budget — precomputed once per run from the full
    candidate pool (before any per-bucket slicing), since "at risk of going
    unfilled" is a property of how many real candidates exist this run
    relative to budget, not a running fill-count that changes mid-sort."""
    counts = {}
    for _uid, listing in candidates:
        bucket, _ = classify(listing.title, listing.category, "")
        counts[bucket] = counts.get(bucket, 0) + 1
    return {bucket: max(0, cap - counts.get(bucket, 0)) for bucket, cap in budget.items()}
