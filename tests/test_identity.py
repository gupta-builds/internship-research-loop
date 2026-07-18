import json
from pathlib import Path

import pytest

from core.identity import compute_uid, cross_source_key
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
