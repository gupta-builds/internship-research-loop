"""Unit tests for .claude/skills/writing-internship-notes/scripts/lint_note.py.
The vault is a synthetic tmp_path folder and the runner is a fake, so node never runs."""
import importlib.util
import pathlib
import subprocess

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / ".claude/skills/writing-internship-notes/scripts/lint_note.py"
spec = importlib.util.spec_from_file_location("lint_note", SCRIPT)
N = importlib.util.module_from_spec(spec)
spec.loader.exec_module(N)


def make_vault(tmp_path):
    """build a synthetic vault with the linter file and one note; return (vault, note path)."""
    (tmp_path / "30_Order/System/vault-lint").mkdir(parents=True)
    (tmp_path / "30_Order/System/vault-lint/vault-lint.js").write_text("// synthetic", encoding="utf-8")
    note = tmp_path / "10_Areas/Programs/Serious/Example.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Example\n", encoding="utf-8")
    return tmp_path, note


class Done:
    """a fake CompletedProcess."""

    def __init__(self, code=0, out="FIT: 1/1 = 100.0%", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


def test_unset_jarvis_dir_is_not_run(capsys):
    assert N.main(["x.md"], env={}) == 2
    assert "VALIDATOR NOT RUN: JARVIS_DIR is not set" in capsys.readouterr().out


def test_missing_linter_is_not_run(tmp_path, capsys):
    assert N.main(["x.md"], env={"JARVIS_DIR": str(tmp_path)}) == 2
    assert "vault-lint.js not found" in capsys.readouterr().out


def test_note_outside_the_vault_is_not_run(tmp_path, capsys):
    vault, _ = make_vault(tmp_path / "vault")
    outside = tmp_path / "elsewhere.md"
    outside.write_text("x", encoding="utf-8")
    assert N.main([str(outside)], env={"JARVIS_DIR": str(vault)}) == 2
    assert "is not under" in capsys.readouterr().out


def test_missing_note_is_not_run(tmp_path, capsys):
    vault, _ = make_vault(tmp_path)
    assert N.main(["10_Areas/nope.md"], env={"JARVIS_DIR": str(vault)}) == 2
    assert "no such note" in capsys.readouterr().out


def test_clean_run_prints_output_and_exits_0(tmp_path, capsys):
    vault, note = make_vault(tmp_path)
    seen = {}

    def runner(cmd, **kw):
        seen["cmd"], seen["kw"] = cmd, kw
        return Done(0, "Scanned 1 notes\nFIT: 1/1 = 100.0%")
    assert N.main([str(note)], env={"JARVIS_DIR": str(vault)}, runner=runner) == 0
    out = capsys.readouterr().out
    assert "FIT: 1/1" in out and "vault-lint exit code: 0" in out
    assert seen["cmd"][-4:] == ["--path", "10_Areas/Programs/Serious/Example.md", "--list", "5"]   # vault-relative, not absolute
    assert seen["kw"]["timeout"] == N.TIMEOUT


def test_relative_note_path_is_accepted(tmp_path):
    vault, _ = make_vault(tmp_path)
    got = []
    N.main(["10_Areas/Programs/Serious/Example.md"], env={"JARVIS_DIR": str(vault)},
           runner=lambda cmd, **kw: got.append(cmd) or Done())
    assert got and got[0][-3] == "10_Areas/Programs/Serious/Example.md"


def test_failing_note_is_exit_1_even_though_the_linter_exits_0(tmp_path, capsys):
    vault, note = make_vault(tmp_path)      # real vault-lint exited 0 with FIT 0/1 on 2026-11-26
    out = "FIT: 0/1 = 0.0%\n      5  1:missing-key"
    code = N.main([str(note)], env={"JARVIS_DIR": str(vault)}, runner=lambda cmd, **kw: Done(0, out))
    assert code == 1
    assert "1:missing-key" in capsys.readouterr().out


def test_output_with_no_fit_line_is_not_run(tmp_path, capsys):
    vault, note = make_vault(tmp_path)
    assert N.main([str(note)], env={"JARVIS_DIR": str(vault)}, runner=lambda cmd, **kw: Done(0, "garbled")) == 2
    assert "VALIDATOR NOT RUN" in capsys.readouterr().out


def test_linter_crash_is_not_run(tmp_path, capsys):
    vault, note = make_vault(tmp_path)
    assert N.main([str(note)], env={"JARVIS_DIR": str(vault)}, runner=lambda cmd, **kw: Done(1, "", "boom")) == 2
    assert "exited 1" in capsys.readouterr().out


def test_missing_node_is_not_run(tmp_path, capsys):
    vault, note = make_vault(tmp_path)

    def runner(cmd, **kw):
        raise FileNotFoundError("node")
    assert N.main([str(note)], env={"JARVIS_DIR": str(vault)}, runner=runner) == 2
    assert "node is not installed" in capsys.readouterr().out


def test_timeout_is_not_run(tmp_path, capsys):
    vault, note = make_vault(tmp_path)

    def runner(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)
    assert N.main([str(note), "--timeout", "1"], env={"JARVIS_DIR": str(vault)}, runner=runner) == 2
    assert "did not finish in 1 seconds" in capsys.readouterr().out
