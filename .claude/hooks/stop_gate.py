"""
internship-research-loop: Stop hook
Topic: run the test suite before a session stops, when Python or test files changed.

Exit 0 when stop_hook_active is set (Claude is already continuing because of this
hook) or when no .py file and no tests/ path is dirty. Otherwise run
`uv run pytest -q` in the repo root; on failure exit 2 with the tail of the output,
so Claude keeps working. A run that cannot start or times out exits 0 with a
warning (hook convention: a broken hook must not trap the session).
"""
import json
import os
import subprocess
import sys

TEST_CMD = ["uv", "run", "pytest", "-q"]
TEST_TIMEOUT = 540                                    # seconds; settings give the hook 600
TAIL = 3000                                           # characters of output sent back


def changed_paths(root):
    """return the paths git status reports as changed or untracked."""
    r = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, timeout=10)
    paths = []
    for line in r.stdout.splitlines():
        paths.append(line[3:].split(" -> ")[-1].strip('"'))   # a rename lists old -> new
    return paths


def needs_tests(paths):
    """return True if any changed path is Python or under tests/."""
    return any(p.endswith(".py") or p.startswith("tests/") for p in paths)


def main():
    """read the payload, run the tests if needed and return the exit code."""
    try:
        data = json.load(sys.stdin)
    # Source: https://docs.python.org/3/library/json.html (JSONDecodeError subclasses ValueError)
    except ValueError:
        print("stop_gate: unreadable payload, tests not run", file=sys.stderr)
        return 0
    if not isinstance(data, dict) or data.get("stop_hook_active"):
        return 0
    cwd = data.get("cwd") or os.getcwd()
    try:
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd,
                              capture_output=True, text=True, timeout=10).stdout.strip() or cwd
        if not needs_tests(changed_paths(root)):
            return 0
        r = subprocess.run(TEST_CMD, cwd=root, capture_output=True, text=True, timeout=TEST_TIMEOUT)
    # Source: https://docs.python.org/3/library/subprocess.html (run raises TimeoutExpired)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"stop_gate: tests not run ({type(e).__name__}); say so in your report", file=sys.stderr)
        return 0
    if r.returncode != 0:
        out = (r.stdout + r.stderr)[-TAIL:]
        print(f"BLOCKED by stop_gate: `{' '.join(TEST_CMD)}` failed. Instead: fix the failure, "
              f"then stop.\n{out}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
