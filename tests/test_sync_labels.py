"""labels.yml is valid and defines every label that pr_gates.py or the issue forms refer to."""
import importlib.util
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync_labels", ROOT / "scripts/github/sync_labels.py")
sl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sl)


def test_labels_valid_and_unique():
    names = [lb["name"] for lb in sl.load()]
    assert len(names) == len(set(names))
    assert all(re.fullmatch(r"[0-9a-f]{6}", lb["color"]) for lb in sl.load())


def test_gate_override_labels_and_form_labels_are_defined():
    names = {lb["name"] for lb in sl.load()}
    gates = (ROOT / "scripts/ci/pr_gates.py").read_text()
    overrides = set(re.findall(r'"([a-z-]+-ok|no-issue)" (?:in|not in) labels', gates))
    assert {"large-ok", "parallel-ok", "no-issue", "no-tests-ok"} <= overrides
    assert overrides <= names
    for form in (ROOT / ".github/ISSUE_TEMPLATE").glob("[bt]*.yml"):
        assert set(yaml.safe_load(form.read_text())["labels"]) <= names, form.name
