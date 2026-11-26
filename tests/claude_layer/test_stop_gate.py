"""Tests for .claude/hooks/stop_gate.py. uv is replaced by a stub that records each call."""
import json
import os
import pathlib
import subprocess
import sys

import pytest

HOOK = pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/stop_gate.py"


@pytest.fixture
def repo(tmp_path):
    """a scratch repo with one committed file."""
    path = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "README.md").write_text("x\n", encoding="utf-8")
    for args in (["config", "user.email", "t@example.invalid"], ["config", "user.name", "T"],
                 ["add", "README.md"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-C", str(path)] + args, check=True)
    return path


def run_hook(repo, tmp_path, payload, uv_exit=0):
    """return (exit code, stderr, whether uv ran) with a stub uv on PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    marker = tmp_path / "uv_ran"
    uv = bin_dir / "uv"
    uv.write_text(f"#!/bin/sh\ntouch {marker}\necho '1 failed, 3 passed'\nexit {uv_exit}\n", encoding="utf-8")
    uv.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    raw = payload if isinstance(payload, str) else json.dumps({"cwd": str(repo), **payload})
    r = subprocess.run([sys.executable, str(HOOK)], input=raw, capture_output=True, text=True, env=env)
    return r.returncode, r.stderr, marker.exists()


def test_clean_tree_skips_tests(repo, tmp_path):
    assert run_hook(repo, tmp_path, {}) == (0, "", False)


def test_docs_only_change_skips_tests(repo, tmp_path):
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    assert run_hook(repo, tmp_path, {})[2] is False


def test_python_change_failing_tests_blocks(repo, tmp_path):
    (repo / "x.py").write_text("x = 1\n", encoding="utf-8")
    code, err, ran = run_hook(repo, tmp_path, {}, uv_exit=1)
    assert (code, ran) == (2, True)
    assert "BLOCKED by stop_gate" in err and "1 failed, 3 passed" in err


def test_tests_path_change_passing_tests_allows(repo, tmp_path):
    (repo / "tests").mkdir()
    (repo / "tests/fixture.json").write_text("{}", encoding="utf-8")
    assert run_hook(repo, tmp_path, {}, uv_exit=0)[:2] + (True,) == (0, "", True)


def test_stop_hook_active_exits_without_running(repo, tmp_path):
    (repo / "x.py").write_text("x = 1\n", encoding="utf-8")
    assert run_hook(repo, tmp_path, {"stop_hook_active": True}, uv_exit=1) == (0, "", False)


def test_unreadable_payload_passes_with_warning(repo, tmp_path):
    code, err, ran = run_hook(repo, tmp_path, "{bad")
    assert code == 0 and "unreadable payload" in err and not ran
