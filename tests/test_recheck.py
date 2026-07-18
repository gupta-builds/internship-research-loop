"""plan_removals is the recheck's whole decision surface — pure, tested offline."""
from recheck import plan_removals


def _fm(uid):
    return {"uid": uid, "_path": f"/fake/{uid}.md"}


DOSSIERS = [
    _fm("SimplifyJobs:aaa"),
    _fm("SimplifyJobs:bbb"),
    _fm("Jose-Gael-Cruz-Lopez:ccc"),
]


def test_active_false_upstream_is_removed():
    feeds = {"SimplifyJobs": {"aaa": False, "bbb": True}, "Jose-Gael-Cruz-Lopez": {"ccc": True}}
    removals = plan_removals(DOSSIERS, feeds)
    assert [r["uid"] for r in removals] == ["SimplifyJobs:aaa"]
    assert removals[0]["reason"] == "active: false upstream"


def test_absent_from_feed_is_removed():
    feeds = {"SimplifyJobs": {"bbb": True}, "Jose-Gael-Cruz-Lopez": {"ccc": True}}
    removals = plan_removals(DOSSIERS, feeds)
    assert [r["uid"] for r in removals] == ["SimplifyJobs:aaa"]
    assert removals[0]["reason"] == "absent from live feed"


def test_failed_fetch_skips_that_sources_dossiers_entirely():
    """A source missing from feeds_by_source means its fetch failed — its
    dossiers must never be read as 'absent from feed' and mass-removed."""
    feeds = {"Jose-Gael-Cruz-Lopez": {"ccc": False}}
    removals = plan_removals(DOSSIERS, feeds)
    assert [r["uid"] for r in removals] == ["Jose-Gael-Cruz-Lopez:ccc"]


def test_all_active_removes_nothing():
    feeds = {"SimplifyJobs": {"aaa": True, "bbb": True}, "Jose-Gael-Cruz-Lopez": {"ccc": True}}
    assert plan_removals(DOSSIERS, feeds) == []
