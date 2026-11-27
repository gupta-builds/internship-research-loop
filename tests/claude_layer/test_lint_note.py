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

    def __init__(self, code=0, out="fit 1/1", err=""):
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
        return Done(0, "all notes fit")
    assert N.main([str(note)], env={"JARVIS_DIR": str(vault)}, runner=runner) == 0
    out = capsys.readouterr().out
    assert "all notes fit" in out and "vault-lint exit code: 0" in out
    assert seen["cmd"][-2:] == ["--path", "10_Areas/Programs/Serious/Example.md"]   # vault-relative, not absolute
    assert seen["kw"]["timeout"] == N.TIMEOUT


def test_relative_note_path_is_accepted(tmp_path):
    vault, _ = make_vault(tmp_path)
    got = []
    N.main(["10_Areas/Programs/Serious/Example.md"], env={"JARVIS_DIR": str(vault)},
           runner=lambda cmd, **kw: got.append(cmd) or Done())
    assert got and got[0][-1] == "10_Areas/Programs/Serious/Example.md"


def test_nonzero_linter_exit_is_exit_1(tmp_path, capsys):
    vault, note = make_vault(tmp_path)
    code = N.main([str(note)], env={"JARVIS_DIR": str(vault)}, runner=lambda cmd, **kw: Done(1, "missing-key: type"))
    assert code == 1
    assert "missing-key: type" in capsys.readouterr().out


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
