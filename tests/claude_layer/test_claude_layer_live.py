"""Runs scripts/lint_claude_layer.py on this repo's real Claude layer; CI and pre-push run it this way."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("lint_claude_layer", ROOT / "scripts/lint_claude_layer.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)


def test_claude_layer_lint_passes():
    findings = L.lint(ROOT)
    assert findings == [], "\n".join(f"{r}:{n} [{c}] {m}" for r, n, c, m in findings)
