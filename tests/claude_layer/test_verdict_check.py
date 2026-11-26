"""Tests for .claude/hooks/verdict_check.py, through the hook payload and through --file."""
import json
import pathlib
import subprocess
import sys

import pytest

HOOK = pathlib.Path(__file__).resolve().parents[2] / ".claude/hooks/verdict_check.py"


def run_hook(stdin="", args=()):
    """return (exit code, stderr) of the check."""
    r = subprocess.run([sys.executable, str(HOOK), *args], input=stdin, capture_output=True, text=True)
    return r.returncode, r.stderr


def payload(message):
    """return a hook payload carrying message."""
    return json.dumps({"tool_input": {"message": message}})


@pytest.mark.parametrize("message", ["VERDICT: PASS\nNo findings.", "\n  VERDICT: REVISE\n- one",
                                     "VERDICT: BLOCK"])
def test_verdict_first_line_passes(message):
    assert run_hook(payload(message)) == (0, "")


@pytest.mark.parametrize("message", ["Looks good.\nVERDICT: PASS", "VERDICT: MAYBE", "verdict: pass"])
def test_missing_verdict_blocks(message):
    code, err = run_hook(payload(message))
    assert code == 2 and "Report rejected" in err


def test_empty_message_is_validator_not_run():
    code, err = run_hook(payload(""))
    assert code == 2 and err.startswith("VALIDATOR NOT RUN")


def test_file_mode(tmp_path):
    good, bad = tmp_path / "good.md", tmp_path / "bad.md"
    good.write_text("VERDICT: PASS\n", encoding="utf-8")
    bad.write_text("Findings first.\n", encoding="utf-8")
    assert run_hook(args=["--file", str(good)])[0] == 0
    assert run_hook(args=["--file", str(bad)])[0] == 2


def test_missing_file_is_validator_not_run(tmp_path):
    code, err = run_hook(args=["--file", str(tmp_path / "absent.md")])
    assert code == 2 and err.startswith("VALIDATOR NOT RUN")


def test_unreadable_payload_passes_with_warning():
    code, err = run_hook("{bad")
    assert code == 0 and "unreadable payload" in err
