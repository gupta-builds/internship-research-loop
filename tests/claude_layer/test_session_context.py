"""Tests for .claude/hooks/session_context.py. gh is replaced by a stub, so no test calls GitHub."""
import json
import os
import pathlib
import subprocess
import sys

import pytest

HOOK = pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/session_context.py"


def make_gh(folder, script):
    """write a stub gh into folder and return the folder."""
    folder.mkdir()
    gh = folder / "gh"
    gh.write_text("#!/bin/sh\n" + script + "\n", encoding="utf-8")
    gh.chmod(0o755)
    return folder


@pytest.fixture
def repo(tmp_path):
    """a scratch repo on branch chore/x with one commit."""
    path = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", "-b", "chore/x", str(path)], check=True)
    for args in (["config", "user.email", "t@example.invalid"], ["config", "user.name", "T"],
                 ["commit", "-q", "--allow-empty", "-m", "init"]):
        subprocess.run(["git", "-C", str(path)] + args, check=True)
    return path


def run_hook(cwd, gh_dir, jarvis=None):
    """return the hook's parsed JSON output for a session in cwd."""
    env = {k: v for k, v in os.environ.items() if k != "JARVIS_DIR"}
    env["PATH"] = f"{gh_dir}:{env['PATH']}"
    if jarvis:
        env["JARVIS_DIR"] = jarvis
    payload = json.dumps({"hook_event_name": "SessionStart", "source": "startup", "cwd": str(cwd)})
    r = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]


def test_facts_with_gh_working(repo, tmp_path):
    gh = make_gh(tmp_path / "bin1", 'case "$1" in run) echo "2026-11-26T05:53:03Z, conclusion success";; '
                                    'pr) echo 2;; esac')
    out = run_hook(repo, gh)
    text = out["additionalContext"]
    assert out["hookEventName"] == "SessionStart"
    assert "branch: chore/x" in text and "dirty files: 0\n" in text
    assert "last run.yml run: 2026-11-26T05:53:03Z, conclusion success" in text
    assert "open PRs: 2" in text and "healthy" not in text.lower()


def test_gh_failing_prints_unknown(repo, tmp_path):
    out = run_hook(repo, make_gh(tmp_path / "bin2", "exit 1"))
    assert "last run.yml run: unknown" in out["additionalContext"]
    assert "open PRs: unknown" in out["additionalContext"]


def test_dirty_tree_is_flagged(repo, tmp_path):
    (repo / "x.txt").write_text("x", encoding="utf-8")
    text = run_hook(repo, make_gh(tmp_path / "bin3", "exit 1"))["additionalContext"]
    assert "dirty files: 1 (dirty at session start, not made by this session)" in text


def test_jarvis_dir_reported_without_value(repo, tmp_path):
    gh = make_gh(tmp_path / "bin4", "exit 1")
    assert "JARVIS_DIR set: no" in run_hook(repo, gh)["additionalContext"]
    text = run_hook(repo, gh, jarvis="/synthetic/vault/path")["additionalContext"]
    assert "JARVIS_DIR set: yes" in text and "/synthetic/vault/path" not in text


def test_handoff_next_section_printed(repo, tmp_path):
    (repo / "docs").mkdir()
    (repo / "docs/HANDOFF.md").write_text("# Handoff\n## Done\n- a\n## Next\n1. Run the lint.\n## Decisions\n- d\n",
                                          encoding="utf-8")
    text = run_hook(repo, make_gh(tmp_path / "bin5", "exit 1"))["additionalContext"]
    assert text.endswith("HANDOFF Next:\n1. Run the lint.")


def test_output_stays_under_limit(repo, tmp_path):
    (repo / "docs").mkdir()
    (repo / "docs/HANDOFF.md").write_text("## Next\n" + "word " * 5000, encoding="utf-8")
    out = run_hook(repo, make_gh(tmp_path / "bin6", "exit 1"))
    assert len(json.dumps({"hookSpecificOutput": out})) < 2000
    assert "(cut; read docs/HANDOFF.md)" in out["additionalContext"]


def test_unreadable_payload_still_prints(repo):
    r = subprocess.run([sys.executable, str(HOOK)], input="{bad", capture_output=True, text=True, cwd=repo)
    assert r.returncode == 0 and "hookSpecificOutput" in r.stdout
