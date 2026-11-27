#!/usr/bin/env python3
"""
internship-research-loop: vault note lint
Topic: run the vault's own linter on one note and print what it says.

Usage: python3 .claude/skills/writing-internship-notes/scripts/lint_note.py NOTE [--timeout SECONDS]
NOTE is a path under $JARVIS_DIR, absolute or relative to it.
Prints the linter's output as it came, then a line `vault-lint exit code: N`.
Exit 0 the note fits its Standard, 1 it does not, 2 the check could not run (a line
`VALIDATOR NOT RUN: <reason>` says why). No LLM call, no secret, no write to the vault.

The linter exits 0 even when a note fails, so the verdict comes from its `FIT: a/b`
line, not from its exit code. It reads every note in the vault, so a run took 10 to 16
minutes on 2026-11-26. Run it once per finished note, in the background, never
after each edit.
"""
import argparse
import os
import pathlib
import re
import subprocess
import sys

LINTER = pathlib.Path("30_Order/System/vault-lint/vault-lint.js")   # relative to the vault root
TIMEOUT = 1800                                                       # seconds; runs took 9 min 55 s and 16 min 25 s on 2026-11-26
FIT_RE = re.compile(r"^FIT: (\d+)/(\d+)", re.M)                       # the linter's summary line


#### helpers

def not_run(reason):
    """print the standard refusal line and return exit code 2."""
    print(f"VALIDATOR NOT RUN: {reason}")
    return 2


def vault_relative(note, vault):
    """return the note path relative to the vault root, or None if it lies outside."""
    path = pathlib.Path(note)
    path = path if path.is_absolute() else vault / path
    try:
        return path.resolve().relative_to(vault.resolve())
    except ValueError:                                     # the note is not under the vault
        return None


#### driver

def main(argv=None, env=None, runner=subprocess.run):
    """lint one note and return the exit code; runner is injectable so tests need no node."""
    ap = argparse.ArgumentParser(description="run the vault linter on one note")
    ap.add_argument("note")
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    args = ap.parse_args(argv)
    env = os.environ if env is None else env
    if not env.get("JARVIS_DIR"):
        return not_run("JARVIS_DIR is not set")
    vault = pathlib.Path(env["JARVIS_DIR"])
    if not (vault / LINTER).is_file():
        return not_run(f"{LINTER} not found under {vault}")
    rel = vault_relative(args.note, vault)
    if rel is None:
        return not_run(f"{args.note} is not under {vault}")
    if not (vault / rel).is_file():
        return not_run(f"no such note: {rel}")
    cmd = ["node", str(vault / LINTER), "--path", rel.as_posix(), "--list", "5"]   # --list names the failing keys per note
    try:
        # Source: https://docs.python.org/3/library/subprocess.html#subprocess.run (timeout kills the child and raises TimeoutExpired)
        done = runner(cmd, cwd=vault, capture_output=True, text=True, timeout=args.timeout, check=False)
    except FileNotFoundError:                              # node is not on PATH
        return not_run("node is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        return not_run(f"the linter did not finish in {args.timeout} seconds")
    print(done.stdout.rstrip())
    if done.stderr.strip():
        print(done.stderr.rstrip(), file=sys.stderr)
    print(f"vault-lint exit code: {done.returncode}")
    fit = FIT_RE.search(done.stdout)
    if done.returncode != 0 or fit is None:                # a crash, or output with no verdict, is not a pass
        return not_run(f"the linter exited {done.returncode} and printed no FIT line")
    return 0 if fit.group(1) == fit.group(2) else 1


if __name__ == "__main__":
    sys.exit(main())
