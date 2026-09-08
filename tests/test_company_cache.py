"""core/company_cache.py — the per-company enrichment cache alongside
enrich.py. All tests use tmp_path as cache_dir, never the real
state/company_cache/, same isolation convention as test_run_pipeline.py's
own load_/save_ state-file tests."""
from datetime import date, timedelta

from core.company_cache import is_expired, load, save

_REAL_ENRICHMENT = {
    "site_url": "https://www.optiver.com",
    "about": "Optiver is a leading technology- and research-driven trading firm.",
    "blog_url": "",
    "github_org": None,
    "github_members": [],
    "mx_valid": True,
    "contacts": [
        {"name": "Jane Recruiter", "source": "university recruiting search: https://example.test/1",
         "inferred_email": "jane.recruiter@optiver.com", "mx_ok": True},
    ],
    "sources": ["https://www.optiver.com"],
}


def test_save_load_round_trip_preserves_every_field(tmp_path):
    save("Optiver", _REAL_ENRICHMENT, cache_dir=tmp_path)
    loaded = load("Optiver", cache_dir=tmp_path)

    assert loaded is not None
    for key, value in _REAL_ENRICHMENT.items():
        assert loaded[key] == value
    assert loaded["company"] == "Optiver"
    assert loaded["checked"] == date.today().isoformat()


def test_save_uses_normalized_company_as_filename(tmp_path):
    """Optiver/OPTIVER must share one file, not silently duplicate — same
    normalization core/identity._norm_company already uses for company
    matching elsewhere."""
    save("Optiver", _REAL_ENRICHMENT, cache_dir=tmp_path)
    save("OPTIVER", {**_REAL_ENRICHMENT, "about": "second write"}, cache_dir=tmp_path)

    assert list(tmp_path.glob("*.json")) == [tmp_path / "optiver.json"]
    assert load("optiver", cache_dir=tmp_path)["about"] == "second write"


def test_save_creates_cache_dir_if_missing(tmp_path):
    cache_dir = tmp_path / "company_cache"
    assert not cache_dir.exists()
    save("D.E. Shaw", _REAL_ENRICHMENT, cache_dir=cache_dir)
    assert cache_dir.exists()
    assert load("D.E. Shaw", cache_dir=cache_dir) is not None


def test_load_missing_file_returns_none(tmp_path):
    assert load("Nonexistent Co", cache_dir=tmp_path) is None


def test_load_corrupt_json_returns_none_not_raise(tmp_path):
    save("Optiver", _REAL_ENRICHMENT, cache_dir=tmp_path)
    (tmp_path / "optiver.json").write_text("{not valid json at all")

    assert load("Optiver", cache_dir=tmp_path) is None


def test_load_non_dict_json_returns_none(tmp_path):
    (tmp_path / "optiver.json").write_text("[1, 2, 3]")
    assert load("Optiver", cache_dir=tmp_path) is None


def test_load_expired_entry_returns_none(tmp_path):
    save("Optiver", _REAL_ENRICHMENT, cache_dir=tmp_path)
    stale = date.today() - timedelta(days=45)
    raw = (tmp_path / "optiver.json").read_text()
    (tmp_path / "optiver.json").write_text(raw.replace(date.today().isoformat(), stale.isoformat()))

    assert load("Optiver", cache_dir=tmp_path) is None


def test_load_within_ttl_still_returns_data(tmp_path):
    save("Optiver", _REAL_ENRICHMENT, cache_dir=tmp_path)
    assert load("Optiver", cache_dir=tmp_path) is not None


# --- is_expired: pure, boundary-tested against date.today() computed once
# per test rather than depending on real wall-clock time passing ---

def test_is_expired_false_exactly_at_ttl_boundary():
    checked = (date.today() - timedelta(days=30)).isoformat()
    assert is_expired(checked, ttl_days=30) is False


def test_is_expired_true_one_day_past_ttl_boundary():
    checked = (date.today() - timedelta(days=31)).isoformat()
    assert is_expired(checked, ttl_days=30) is True


def test_is_expired_false_for_todays_date():
    assert is_expired(date.today().isoformat(), ttl_days=30) is False


def test_is_expired_true_for_unparseable_date():
    assert is_expired("not-a-date", ttl_days=30) is True
