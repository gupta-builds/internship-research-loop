#!/usr/bin/env python3
"""Create or update the labels in .github/labels.yml via `gh label create --force`.

Idempotent and additive: never deletes a label. Zero LLM. Run from the repo root.
"""
import pathlib
import subprocess
import sys

import yaml

LABELS = pathlib.Path(__file__).resolve().parents[2] / ".github" / "labels.yml"


def load(path=LABELS):
    labels = yaml.safe_load(path.read_text())
    for lb in labels:
        if not {"name", "color", "description"} <= set(lb):
            raise ValueError(f"label missing a field: {lb}")
    return labels


def main():
    for lb in load():
        subprocess.run(["gh", "label", "create", lb["name"], "--color", lb["color"],
                        "--description", lb["description"], "--force"], check=True)
        print(f"synced {lb['name']}")


if __name__ == "__main__":
    sys.exit(main())
