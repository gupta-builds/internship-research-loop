"""
internship-research-loop: PreToolUse hook for Edit, Write, MultiEdit and NotebookEdit
Topic: block edits to rule files, hooks, settings and bot-owned folders.

The path is resolved against the git repo that holds the file, so a session that
edits another worktree by absolute path is still checked. A path outside any repo
passes. RULES_UNLOCK=1 in the session's environment allows every edit; Anant sets
it when he launches a session to change the rules. Exit 2 blocks; an unreadable
payload exits 0 with a warning (hook convention).
"""
import json
import os
import pathlib
import subprocess
import sys

PROTECTED_FILES = {"CLAUDE.md", "AGENTS.md", ".claude/settings.json",
                   ".claude/skills/humanizing-writing/scripts/data/banned_phrases.txt"}
PROTECTED_DIRS = (".claude/rules/", ".claude/hooks/", "state/", "logs/", "graphify-out/")


def repo_root(path):
    """return the top folder of the git repo holding path, or None."""
    folder = path.parent
    while not folder.is_dir() and folder != folder.parent:
        folder = folder.parent                         # a new file's folder may not exist yet
    try:
        r = subprocess.run(["git", "-C", str(folder), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=5)
    # Source: https://docs.python.org/3/library/subprocess.html (run raises TimeoutExpired)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return pathlib.Path(r.stdout.strip()).resolve() if r.returncode == 0 else None


def protected(rel):
    """return True if a repo-relative posix path is protected."""
    return rel in PROTECTED_FILES or rel.startswith(PROTECTED_DIRS)


def check(data):
    """return the repo-relative path if the edit must be blocked, else None."""
    tool_input = data.get("tool_input") or {}
    raw = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not raw:
        return None
    path = pathlib.Path(data.get("cwd") or ".", raw).resolve()   # an absolute raw path wins the join
    root = repo_root(path)
    if root is None or not path.is_relative_to(root):
        return None
    rel = path.relative_to(root).as_posix()
    return rel if protected(rel) else None


def main():
    """read the payload, print the block to stderr and return the exit code."""
    if os.environ.get("RULES_UNLOCK") == "1":
        return 0
    try:
        data = json.load(sys.stdin)
    # Source: https://docs.python.org/3/library/json.html (JSONDecodeError subclasses ValueError)
    except ValueError:
        print("protect_files: unreadable payload, not checked", file=sys.stderr)
        return 0
    if not isinstance(data, dict):
        print("protect_files: payload is not an object, not checked", file=sys.stderr)
        return 0
    rel = check(data)
    if rel:
        print(f"BLOCKED by protect_files: {rel} is a rule, hook or settings file, or bot-owned. "
              "Instead: fix the draft, not the rule; Anant changes these in a session he "
              "launches with RULES_UNLOCK=1.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
