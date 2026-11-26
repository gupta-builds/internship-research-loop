"""
internship-research-loop: SessionStart hook
Topic: print the git and run facts a session needs first, plus HANDOFF's Next section.

Facts only: it states the last scheduled run's time and conclusion, never whether
the loop is healthy. It says whether JARVIS_DIR is set, never its value. Output is
JSON hookSpecificOutput, kept under OUTPUT_MAX characters because the docs cut
SessionStart output over 10,000 characters to a short preview.
"""
import datetime
import json
import os
import subprocess
import sys

OUTPUT_MAX = 2000
GH_TIMEOUT = 8                                        # seconds per gh call; the hook gets 30


def run(cmd, cwd, timeout=5):
    """return a command's stripped stdout, or None if it failed or timed out."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    # Source: https://docs.python.org/3/library/subprocess.html (run raises TimeoutExpired)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def next_section(root):
    """return the text of docs/HANDOFF.md's Next section, or a short note."""
    path = os.path.join(root, "docs", "HANDOFF.md")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return "docs/HANDOFF.md not found"
    if "## Next" not in text:
        return "docs/HANDOFF.md has no Next section"
    body = text.split("## Next", 1)[1]
    return body.split("\n## ", 1)[0].strip() or "(empty)"


def facts(cwd):
    """return the context lines for a session starting in cwd."""
    root = run(["git", "rev-parse", "--show-toplevel"], cwd) or cwd
    dirty = run(["git", "status", "--porcelain"], root)
    dirty_n = len(dirty.splitlines()) if dirty else 0
    counts = run(["git", "rev-list", "--left-right", "--count", "HEAD...origin/master"], root)
    ahead, behind = counts.split() if counts else ("unknown", "unknown")
    last = run(["gh", "run", "list", "--workflow=run.yml", "--limit", "1", "--json", "createdAt,conclusion",
                "--jq", '.[0] | "\\(.createdAt), conclusion \\(.conclusion)"'], root, GH_TIMEOUT)
    prs = run(["gh", "pr", "list", "--state", "open", "--json", "number", "--jq", "length"], root, GH_TIMEOUT)
    lines = [
        f"date: {datetime.date.today().isoformat()}",
        f"worktree: {root}",
        f"branch: {run(['git', 'branch', '--show-current'], root) or 'unknown (detached or not a repo)'}",
        f"dirty files: {dirty_n}" + (" (dirty at session start, not made by this session)" if dirty_n else ""),
        f"commits ahead of origin/master: {ahead}; behind: {behind}",
        f"JARVIS_DIR set: {'yes' if os.environ.get('JARVIS_DIR') else 'no'}",
        f"last run.yml run: {last or 'unknown'}",
        f"open PRs: {prs or 'unknown'}",
        "HANDOFF Next:",
    ]
    head = "\n".join(lines)
    room = OUTPUT_MAX - len(head) - 200                # leave room for the JSON wrapper
    nxt = next_section(root)
    if len(nxt) > room:
        nxt = nxt[:room] + "\n(cut; read docs/HANDOFF.md)"
    return head + "\n" + nxt


def main():
    """print the SessionStart JSON and return 0."""
    try:
        data = json.load(sys.stdin)
    # Source: https://docs.python.org/3/library/json.html (JSONDecodeError subclasses ValueError)
    except ValueError:
        data = {}
    cwd = data.get("cwd") if isinstance(data, dict) and data.get("cwd") else os.getcwd()
    out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": facts(cwd)}}
    try:
        print(json.dumps(out))
    except BrokenPipeError:                            # the reader went away; nothing to report
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
