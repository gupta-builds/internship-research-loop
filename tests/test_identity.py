import json
from pathlib import Path

from core.identity import compute_uid
from ingestion.normalize import normalize_josegael, normalize_simplify, parse_zapply_readme

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


def test_zapply_uid_is_content_hash_and_stable():
    text = (FIXTURES / "zapply_readme.md").read_text()
    listings = parse_zapply_readme(text)
    uid1 = compute_uid(listings[0])
    uid2 = compute_uid(listings[0])
    assert uid1 == uid2
    assert uid1.startswith("zapplyjobs:")


def test_zapply_uid_changes_if_content_changes():
    text = (FIXTURES / "zapply_readme.md").read_text()
    listings = parse_zapply_readme(text)
    by_company = {l.company: l for l in listings}
    uid_nasa = compute_uid(by_company["NASA"])
    uid_dropbox = compute_uid(by_company["Dropbox SWE intern"])
    assert uid_nasa != uid_dropbox


def test_zapply_uid_collides_only_on_same_content():
    """Same company+title+url (case/whitespace-insensitive) must produce the same uid —
    this is the collision behavior the dedup layer relies on."""
    from ingestion.normalize import Listing

    a = Listing(company="Acme Corp", title="SWE Intern", url="https://acme.example/apply", source="zapplyjobs")
    b = Listing(company="  acme corp  ", title="swe intern", url="HTTPS://ACME.EXAMPLE/apply", source="zapplyjobs")
    assert compute_uid(a) == compute_uid(b)
