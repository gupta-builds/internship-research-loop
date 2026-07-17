"""Commit-and-push with a retry-once-on-rejected-push loop.

The Jarvis vault has its own independent auto-commit-and-push cycle running
locally every ~2 hours against the same origin/master this workflow pushes
to. Two independent writers on one branch will eventually collide — this
handles that explicitly instead of letting the run fail outright or, worse,
force-overwriting the other writer's commits.
"""
import subprocess
from pathlib import Path


class GitPushError(Exception):
    pass


def _git(repo_dir, *args, check=True):
    return subprocess.run(
        ["git", "-C", str(repo_dir), *args], capture_output=True, text=True, check=check
    )


def commit_and_push_with_retry(repo_dir, message: str, remote: str = "origin", branch: str = "master") -> bool:
    """Stages everything under repo_dir, commits, and pushes. On a rejected
    push (someone else moved the branch first), retries exactly once: pull
    --rebase to bring in their commits, then push again.

    Returns False if there was nothing to commit (working tree clean —
    caller should treat this as a no-op, not an error). Returns True on a
    successful push. Raises GitPushError if the push still fails after the
    retry — callers must not mark anything as seen/done in that case, since
    nothing actually landed.
    """
    repo_dir = Path(repo_dir)
    _git(repo_dir, "add", "-A")
    staged = _git(repo_dir, "diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        return False  # nothing changed this run

    _git(repo_dir, "commit", "-m", message)

    max_attempts = 2  # initial attempt + one retry
    for attempt in range(1, max_attempts + 1):
        pull = _git(repo_dir, "pull", "--rebase", remote, branch, check=False)
        if pull.returncode != 0:
            _git(repo_dir, "rebase", "--abort", check=False)
            if attempt == max_attempts:
                raise GitPushError(f"git pull --rebase failed on attempt {attempt}: {pull.stderr.strip()}")
            continue

        push = _git(repo_dir, "push", remote, f"HEAD:{branch}", check=False)
        if push.returncode == 0:
            return True
        if attempt == max_attempts:
            raise GitPushError(f"git push rejected after {max_attempts} attempts: {push.stderr.strip()}")

    raise GitPushError("git push failed: exhausted retries")  # unreachable, satisfies static analysis
