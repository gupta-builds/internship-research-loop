"""requirements.txt, pyproject.toml and uv.lock must pin the same direct dependencies.

Real data: Dependabot PR #45 (opened 2026-11-22) bumped pytest 9.1.1 to 9.2.0 in
requirements.txt and pyproject.toml only. uv.lock kept 9.1.1, so any uv sync in a
worktree rewrote the lock and left a dirty tree. The fix was one extra uv.lock commit.
"""
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]  # repo root

FIX = ("run `uv lock` on the PR branch, set `revision = 3` back if uv "
       "changed it, and commit uv.lock")


def split_pin(spec):
    """returns (name, version) for a 'name==version' string"""
    name, version = spec.strip().split("==")
    return name.strip().lower(), version.strip()


def requirements_pins():
    """returns {name: version} read from requirements.txt"""
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return dict(split_pin(l) for l in lines if l.strip() and not l.startswith("#"))  # skip blanks, comments


def pyproject_pins():
    """returns {name: version} read from the dependencies list in pyproject.toml"""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return dict(split_pin(s) for s in data["project"]["dependencies"])


def lock_versions():
    """returns {name: version} for every package in uv.lock"""
    data = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    return {p["name"].lower(): p["version"] for p in data["package"]}


def test_requirements_match_pyproject():
    """the CI file and the project file pin the same direct dependencies"""
    assert requirements_pins() == pyproject_pins()


def test_lock_matches_pyproject():
    """uv.lock holds the version pyproject.toml pins for each direct dependency"""
    locked = lock_versions()
    stale = {n: (v, locked.get(n)) for n, v in pyproject_pins().items() if locked.get(n) != v}
    assert not stale, f"uv.lock is stale for {stale} (pinned, locked); {FIX}"
