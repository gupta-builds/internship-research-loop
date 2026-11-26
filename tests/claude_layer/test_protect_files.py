"""Tests for .claude/hooks/protect_files.py: pipe a payload, check the exit code and stderr."""
import json
import os
import pathlib
import subprocess
import sys

import pytest

HOOK = pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/protect_files.py"
ENV = {k: v for k, v in os.environ.items() if k != "RULES_UNLOCK"}

BLOCKED = ["CLAUDE.md", "AGENTS.md", ".claude/settings.json", ".claude/rules/conventions.md",
           ".claude/hooks/bash_guard.py", "state/seen_ids.json", "logs/runs.jsonl",
           "graphify-out/graph.json",
           ".claude/skills/humanizing-writing/scripts/data/banned_phrases.txt"]
# The first five were blocked by the substring draft on 2026-11-26 (C1 Execution Map).
ALLOWED = ["tests/claude_layer/fixtures/settings.json", "tests/fixtures/logs/x.json",
           "vault_writer/state/x.py", ".vscode/settings.json", ".claude/settings.local.json",
           "core/filter.py", "docs/HANDOFF.md", "tests/claude_layer/test_protect_files.py",
           ".codex/hooks.json"]


def run_hook(payload, env=ENV):
    """return (exit code, stderr) of the hook fed payload on stdin."""
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    r = subprocess.run([sys.executable, str(HOOK)], input=raw, capture_output=True, text=True, env=env)
    return r.returncode, r.stderr


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    """a scratch git repo standing in for a worktree."""
    path = tmp_path_factory.mktemp("repo")
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


@pytest.mark.parametrize("rel", BLOCKED)
def test_protected_path_blocks(repo, rel):
    code, err = run_hook({"tool_name": "Edit", "cwd": str(repo), "tool_input": {"file_path": str(repo / rel)}})
    assert code == 2 and "BLOCKED by protect_files" in err and "RULES_UNLOCK=1" in err


@pytest.mark.parametrize("rel", ALLOWED)
def test_other_path_passes(repo, rel):
    code, err = run_hook({"tool_name": "Write", "cwd": str(repo), "tool_input": {"file_path": str(repo / rel)}})
    assert code == 0, err


def test_relative_path_resolves_against_cwd(repo):
    code, _ = run_hook({"tool_name": "Edit", "cwd": str(repo), "tool_input": {"file_path": "state/x.json"}})
    assert code == 2


def test_other_repo_checked_by_its_own_root(repo, tmp_path):
    code, _ = run_hook({"tool_name": "Edit", "cwd": str(tmp_path), "tool_input": {"file_path": str(repo / "CLAUDE.md")}})
    assert code == 2


def test_path_outside_any_repo_passes(tmp_path):
    code, _ = run_hook({"tool_name": "Edit", "cwd": str(tmp_path),
                        "tool_input": {"file_path": str(tmp_path / ".claude/settings.json")}})
    assert code == 0


def test_notebook_edit_checked(repo):
    code, _ = run_hook({"tool_name": "NotebookEdit", "cwd": str(repo),
                        "tool_input": {"notebook_path": str(repo / "logs/x.ipynb")}})
    assert code == 2


def test_unlock_allows(repo):
    code, _ = run_hook({"tool_name": "Edit", "cwd": str(repo), "tool_input": {"file_path": str(repo / "CLAUDE.md")}},
                       env={**ENV, "RULES_UNLOCK": "1"})
    assert code == 0


def test_unreadable_payload_passes_with_warning():
    code, err = run_hook("{bad")
    assert code == 0 and "unreadable payload" in err
