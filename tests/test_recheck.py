"""plan_removals is the recheck's whole decision surface — pure, tested offline."""
from pathlib import Path

from recheck import plan_removals

JARVIS_DIR = "/fake"


def _fm(uid):
    return {"_path": Path(f"/fake/{uid.replace(':', '-')}.md")}


DOSSIERS = [
    _fm("SimplifyJobs:aaa"),
    _fm("SimplifyJobs:bbb"),
    _fm("Jose-Gael-Cruz-Lopez:ccc"),
]

UID_BY_PATH = {
    "SimplifyJobs-aaa.md": "SimplifyJobs:aaa",
    "SimplifyJobs-bbb.md": "SimplifyJobs:bbb",
    "Jose-Gael-Cruz-Lopez-ccc.md": "Jose-Gael-Cruz-Lopez:ccc",
}


def test_active_false_upstream_is_removed():
    feeds = {"SimplifyJobs": {"aaa": False, "bbb": True}, "Jose-Gael-Cruz-Lopez": {"ccc": True}}
    removals = plan_removals(DOSSIERS, feeds, UID_BY_PATH, JARVIS_DIR)
    assert [r["uid"] for r in removals] == ["SimplifyJobs:aaa"]
    assert removals[0]["reason"] == "active: false upstream"


def test_absent_from_feed_is_removed():
    feeds = {"SimplifyJobs": {"bbb": True}, "Jose-Gael-Cruz-Lopez": {"ccc": True}}
    removals = plan_removals(DOSSIERS, feeds, UID_BY_PATH, JARVIS_DIR)
    assert [r["uid"] for r in removals] == ["SimplifyJobs:aaa"]
    assert removals[0]["reason"] == "absent from live feed"


def test_failed_fetch_skips_that_sources_dossiers_entirely():
    """A source missing from feeds_by_source means its fetch failed — its
    dossiers must never be read as 'absent from feed' and mass-removed."""
    feeds = {"Jose-Gael-Cruz-Lopez": {"ccc": False}}
    removals = plan_removals(DOSSIERS, feeds, UID_BY_PATH, JARVIS_DIR)
    assert [r["uid"] for r in removals] == ["Jose-Gael-Cruz-Lopez:ccc"]


def test_all_active_removes_nothing():
    feeds = {"SimplifyJobs": {"aaa": True, "bbb": True}, "Jose-Gael-Cruz-Lopez": {"ccc": True}}
    assert plan_removals(DOSSIERS, feeds, UID_BY_PATH, JARVIS_DIR) == []


def test_dossier_with_no_manifest_entry_is_skipped_not_removed():
    """A dossier written before dossier_uids.json existed (or hand-edited into
    the vault) has no manifest entry — unknown means leave alone."""
    orphan = _fm("SimplifyJobs:orphan")
    feeds = {"SimplifyJobs": {"aaa": True, "bbb": True}, "Jose-Gael-Cruz-Lopez": {"ccc": True}}
    assert plan_removals(DOSSIERS + [orphan], feeds, UID_BY_PATH, JARVIS_DIR) == []


def test_already_removed_dossier_is_not_re_swept():
    """Real, reproducible bug found 2026-08-23: scan_dossiers() globs Viewed/
    along with every live bucket, so a dossier that stayed closed across
    multiple daily recheck runs kept getting re-moved — move_dossier_to_viewed
    found the base filename already taken (by itself) and wrote a spurious
    '(2)', '(3)', ... suffixed copy each time. All 4 real dossiers in Viewed/
    as of 2026-08-23 already carried a '(2)' suffix from this. A dossier
    already carrying status: removed must be skipped entirely, same as an
    unknown-manifest dossier."""
    already_removed = _fm("SimplifyJobs:aaa")
    already_removed["status"] = "removed"
    dossiers = [already_removed, _fm("SimplifyJobs:bbb"), _fm("Jose-Gael-Cruz-Lopez:ccc")]
    feeds = {"SimplifyJobs": {"bbb": True}, "Jose-Gael-Cruz-Lopez": {"ccc": True}}
    removals = plan_removals(dossiers, feeds, UID_BY_PATH, JARVIS_DIR)
    assert removals == []
