"""Exercises commit_and_push_with_retry against real local git repos (a bare
'remote' plus two independent clones) rather than mocked subprocess calls —
the whole point of this module is real rebase/push semantics under a race,
which a mock can't actually verify.
"""
import subprocess

import pytest

from core import git_ops
from core.git_ops import GitPushError, commit_and_push_with_retry


def _run(cwd, *args):
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {args} failed in {cwd}: {result.stderr}")
    return result


def _configure_identity(path):
    _run(path, "config", "user.email", "test@example.com")
    _run(path, "config", "user.name", "Test")


@pytest.fixture
def remote_and_clones(tmp_path):
    """A bare 'remote' repo plus two independent clones (ours/theirs),
    simulating our scheduled workflow and Jarvis's own auto-commit cycle
    both writing to the same origin/master."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _run(bare, "init", "--bare", "-b", "master")

    seed = tmp_path / "seed"
    seed.mkdir()
    _run(seed, "init", "-b", "master")
    _configure_identity(seed)
    (seed / "README.md").write_text("seed\n")
    _run(seed, "add", "-A")
    _run(seed, "commit", "-m", "seed")
    _run(seed, "remote", "add", "origin", str(bare))
    _run(seed, "push", "origin", "master")

    ours = tmp_path / "ours"
    _run(tmp_path, "clone", str(bare), str(ours))
    _configure_identity(ours)

    theirs = tmp_path / "theirs"
    _run(tmp_path, "clone", str(bare), str(theirs))
    _configure_identity(theirs)

    return bare, ours, theirs


def _log_messages(repo_dir):
    result = _run(repo_dir, "log", "--format=%s", "origin/master")
    return result.stdout.strip().splitlines()


def test_nothing_to_commit_returns_false(remote_and_clones):
    _bare, ours, _theirs = remote_and_clones
    assert commit_and_push_with_retry(ours, "no-op") is False


def test_simple_push_succeeds_without_race(remote_and_clones):
    bare, ours, _theirs = remote_and_clones
    (ours / "ours-file.txt").write_text("from ours\n")

    assert commit_and_push_with_retry(ours, "add ours-file") is True

    _run(ours, "fetch", "origin")
    assert "add ours-file" in _log_messages(ours)


def test_retries_once_on_rejected_push_and_succeeds(remote_and_clones, monkeypatch):
    """The actual scenario this module exists for: 'theirs' (the vault's own
    auto-commit cycle) pushes to origin in the window between our pull and
    our push. Our first push attempt should get rejected; the retry (pull
    --rebase again, push again) should then succeed, and both commits should
    land on the remote."""
    bare, ours, theirs = remote_and_clones
    (ours / "ours-file.txt").write_text("from ours\n")

    real_git = git_ops._git
    injected = {"done": False}

    def racing_git(repo_dir, *args, check=True):
        result = real_git(repo_dir, *args, check=check)
        if not injected["done"] and args[:2] == ("pull", "--rebase"):
            injected["done"] = True
            (theirs / "theirs-file.txt").write_text("from theirs\n")
            real_git(theirs, "add", "-A")
            real_git(theirs, "commit", "-m", "theirs commit")
            real_git(theirs, "push", "origin", "master")
        return result

    monkeypatch.setattr(git_ops, "_git", racing_git)

    assert commit_and_push_with_retry(ours, "add ours-file") is True
    assert injected["done"] is True  # confirms the race was actually injected, not a no-op test

    _run(ours, "fetch", "origin")
    messages = _log_messages(ours)
    assert "add ours-file" in messages
    assert "theirs commit" in messages


def test_raises_after_exhausting_retries_on_persistent_conflict(remote_and_clones):
    """Both sides edit the same line of the same file — pull --rebase can
    never cleanly resolve this, so both attempts fail and the function must
    raise rather than silently give up or push a broken state."""
    bare, ours, theirs = remote_and_clones

    (ours / "README.md").write_text("ours' conflicting edit\n")
    _run(ours, "add", "-A")
    _run(ours, "commit", "-m", "ours edits README")

    (theirs / "README.md").write_text("theirs' conflicting edit\n")
    _run(theirs, "add", "-A")
    _run(theirs, "commit", "-m", "theirs edits README")
    _run(theirs, "push", "origin", "master")

    (ours / "unrelated.txt").write_text("trigger a commit in the helper\n")

    with pytest.raises(GitPushError):
        commit_and_push_with_retry(ours, "add unrelated file")

    # the remote must be untouched by our failed attempt
    _run(ours, "fetch", "origin")
    assert "add unrelated file" not in _log_messages(ours)
