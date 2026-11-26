"""Tests for .claude/hooks/bash_guard.py: pipe a payload, check the exit code and stderr."""
import json
import os
import pathlib
import subprocess
import sys

import pytest

HOOK = pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/bash_guard.py"
ENV = {k: v for k, v in os.environ.items() if k != "RULES_UNLOCK"}

# The 55 command strings measured against the raw-regex draft on 2026-11-26 (C1 Execution
# Map, which miscounts them as 57); that draft got 17 wrong. B must block, P must pass.
MEASURED_2026_11_26 = [
    ("B", "git add -A"),
    ("B", "git add ."),
    ("B", "git add --all"),
    ("B", "cd /x && git add -A && git commit -m y"),
    ("P", "git add .claude/hooks/bash_guard.py tests/claude_layer/test_bash_guard.py"),
    ("P", "git add ./core/filter.py"),
    ("B", "git add -- ."),
    ("B", "git add :/"),
    ("B", 'git commit -am "msg"'),
    ("B", "git push origin master"),
    ("B", "git push origin HEAD:master"),
    ("B", "git push -u origin main"),
    ("B", "git push origin +master"),
    ("B", "git push origin refs/heads/master"),
    ("P", "git push -u origin chore/claude-foundation"),
    ("P", "git push origin chore/maintenance-fix"),
    ("P", "git push -u origin feature/domain-check"),
    ("B", "git push --force"),
    ("B", "git push -f origin chore/x"),
    ("P", "git push --force-with-lease"),
    ("P", "git push --force-with-lease origin chore/claude-foundation"),
    ("B", "git push --force-if-includes --force origin chore/x"),
    ("B", "git commit --no-verify -m x"),
    ("B", "git commit -n -m x"),
    ("B", "git push --no-verify"),
    ("B", "rm -rf build"),
    ("B", "rm -fr build"),
    ("B", "rm -r -f build"),
    ("B", "rm --recursive --force build"),
    ("P", "rm tests/tmp_file.txt"),
    ("B", "pip install requests"),
    ("B", "python3 -m pip install requests"),
    ("B", "uv pip install requests"),
    ("B", "cat .env"),
    ("B", "cat .env.local"),
    ("P", "cat .env.example"),
    ("B", "head -5 ~/.mcp.env"),
    ("B", "source ~/.mcp.env"),
    ("B", "grep KEY .env"),
    ("B", "python3 -c \"print(open('.env').read())\""),
    ("B", "uv run --no-project --with-requirements requirements.txt python -m pytest -q | tail -5"),
    ("B", "uv run pytest -q 2>&1 | tail -5"),
    ("P", "uv run --no-project --with-requirements requirements.txt python -m pytest -q"),
    ("B", "cat graphify-out/GRAPH_REPORT.md"),
    ("P", 'graphify query "where is validate called"'),
    ("B", "graphify query x && cat graphify-out/graph.json"),
    ("B", "git config core.hooksPath /tmp/x"),
    ("B", "git config --global user.email x@y"),
    ("B", "git -c core.hooksPath=/dev/null commit -m x"),
    ("P", "git config --get remote.origin.url"),
    ("P", "git config --list"),
    ("P", 'echo "git add -A is blocked"'),
    ("P", 'gh pr create --title "Block git add -A" --body "x"'),
    ("P", "git log --oneline -5 2>&1"),
    ("P", "ls -la state/"),
]

# Commands from docs/TWO_LAPTOP_WORKFLOW.md (placeholders filled in) and from this build.
WORKFLOW_DOC = [
    "git pull --ff-only origin master",
    "export GRAPHIFY_SKIP_HOOK=1",
    "git fetch origin --prune",
    "git worktree add ~/w/repo-chore-x -b chore/x origin/master",
    'git worktree lock --reason "owner: C1 2026-11-26" ~/w/repo-chore-x',
    "git push -u origin chore/x",
    "git push",
    "git worktree unlock ~/w/repo-chore-x",
    "git worktree remove ~/w/repo-chore-x",
    "git branch -d chore/x",
    "git cherry -v origin/master chore/x",
    "git worktree prune",
    "uv sync",
    "uv run pytest -q",
    "uv run python scripts/lint_claude_layer.py",
    "python3 scripts/ci/pr_gates.py --pr 77",
    'git commit -m "Block reading .env files in bash_guard"',
    "gh pr view 77 --json state",
    "gh api repos/o/r/pulls/77",
]

ADDED = [
    ("B", "gh pr merge 77 --squash"),
    ("B", "gh api -X PUT repos/o/r/pulls/77/merge"),
    ("B", "gh api --method=PATCH repos/o/r/git/refs/heads/master -f sha=abc"),
    ("B", "git add .env"),
    ("B", "git commit --all -m x"),
    ("B", "git push --mirror origin"),
    ("B", "echo hi; $(git add -A)"),
    ("B", "FOO=1 git add -A"),
    ("B", "git -C /tmp/x add -A"),
    ("B", 'bash -c "rm -rf build"'),
    ("B", "sh -c 'git add -A && git commit -m x'"),
    ("P", 'bash -c "uv run pytest -q"'),
    ("P", 'git commit -m "Mention graphify-out in the message only"'),
    ("P", "git config user.email"),
]


def run_hook(payload, env=ENV):
    """return (exit code, stderr) of the hook fed payload on stdin."""
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    r = subprocess.run([sys.executable, str(HOOK)], input=raw, capture_output=True, text=True, env=env)
    return r.returncode, r.stderr


@pytest.fixture(scope="module")
def branch_repo(tmp_path_factory):
    """a scratch git repo with a feature branch checked out."""
    path = tmp_path_factory.mktemp("repo")
    subprocess.run(["git", "init", "-q", "-b", "chore/x", str(path)], check=True)
    return str(path)


@pytest.mark.parametrize("want, command", MEASURED_2026_11_26 + ADDED + [("P", c) for c in WORKFLOW_DOC])
def test_command(branch_repo, want, command):
    code, err = run_hook({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": branch_repo})
    assert code == (2 if want == "B" else 0), err
    if want == "B":
        assert "BLOCKED by bash_guard" in err and "Instead:" in err


def test_measured_set_is_complete():
    assert len(MEASURED_2026_11_26) == 55


def test_bare_push_from_master_blocks(tmp_path):
    subprocess.run(["git", "init", "-q", "-b", "master", str(tmp_path)], check=True)
    code, err = run_hook({"tool_input": {"command": "git push"}, "cwd": str(tmp_path)})
    assert code == 2 and "bare git push" in err


def test_unreadable_payload_passes_with_warning():
    code, err = run_hook("{bad")
    assert code == 0 and "unreadable payload" in err


def test_unclosed_quote_still_checked(branch_repo):
    code, _ = run_hook({"tool_input": {"command": 'git add -A "oops'}, "cwd": branch_repo})
    assert code == 2
