#!/usr/bin/env python3
"""
internship-research-loop: vault reachability check
Topic: which of the three ways to reach the Jarvis vault exist on this machine.

Usage: python3 .claude/skills/finding-resources/scripts/check_vault_reachability.py
Prints one line per way (POSSIBLE or NOT FOUND) and a recommendation.
Exit 0 if at least one way is possible, 1 if none is, 2 if the check could not run.

It cannot prove a live MCP connection, which is session state. After it reports the
MCP way as possible, call mcp__jarvis__vault_list and confirm real notes come back.
No secret is read: the MCP check only looks for a server name in a config file.
"""
import json
import os
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]   # .claude/skills/<skill>/scripts/ -> repo root
SIBLINGS = ("Jarvis", "jarvis-checkout")                  # folder names next to the repo, from run_pipeline.py and CI
VAULT_MARKER = "30_Order"                                 # a folder every vault root holds


#### the three ways

def check_env(env):
    """return (ok, detail) for the JARVIS_DIR environment variable."""
    value = env.get("JARVIS_DIR")
    if not value:
        return False, "JARVIS_DIR is not set"
    path = pathlib.Path(value)
    if not (path / VAULT_MARKER).is_dir():
        return False, f"JARVIS_DIR={value} has no {VAULT_MARKER} folder"
    return True, f"JARVIS_DIR={value} is a vault root"


def check_siblings(repo_root):
    """return (ok, detail) for a git checkout of the vault next to this repo."""
    names = []
    for name in SIBLINGS:
        folder = repo_root.parent / name
        names.append(str(folder))
        if folder.is_dir() and (folder / ".git").exists():
            result = subprocess.run(["git", "-C", str(folder), "remote", "get-url", "origin"],
                                    capture_output=True, text=True, check=False)
            remote = result.stdout.strip() if result.returncode == 0 else "(remote unknown)"
            return True, f"git checkout at {folder} (origin: {remote})"
    return False, "no checkout at " + " or ".join(names)


def check_mcp(home, repo_root):
    """return (ok, detail) for a jarvis MCP server named in a config file; config presence only."""
    found = []
    for path in (home / ".claude.json", home / ".claude" / ".mcp.json",
                 repo_root / ".mcp.json", repo_root / ".claude" / "settings.json"):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):                     # unreadable or not JSON: skip it
            continue
        servers = data.get("mcpServers", {})
        if isinstance(servers, dict) and ("jarvis" in servers or "jarvis-fs" in servers):
            found.append(str(path))
    if found:
        return True, "jarvis MCP server named in " + ", ".join(found) + " (config only)"
    return False, "no jarvis MCP server named in any checked config file"


#### driver

def main(env=None, home=None, repo_root=None):
    """print the report and return the exit code."""
    env = os.environ if env is None else env
    home = pathlib.Path.home() if home is None else home
    repo_root = REPO_ROOT if repo_root is None else repo_root
    ways = [("JARVIS_DIR", check_env(env)),
            ("Sibling git checkout", check_siblings(repo_root)),
            ("MCP registration", check_mcp(home, repo_root))]
    print("## Vault reachability")
    for label, (ok, detail) in ways:
        print(f"{label + ':':<22}{'POSSIBLE' if ok else 'NOT FOUND'} -- {detail}")
    if not any(ok for _, (ok, _) in ways):
        print("NO way to reach the vault. Stop and tell Anant. Do not guess paths or write through the GitHub API.")
        return 1
    if ways[0][1][0]:
        print("Use: Read on paths under $JARVIS_DIR. Vault writes still go through the jarvis MCP tools or a checkout, never the GitHub API.")
    elif ways[1][1][0]:
        print("Use: Read, Edit and Write on the checkout, and read git status and git diff there before any commit.")
    else:
        print("Use: the jarvis MCP tools, after mcp__jarvis__vault_list returns real notes. Config presence is not a live connection.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
