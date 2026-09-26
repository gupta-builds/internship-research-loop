#!/usr/bin/env python3
"""Mechanical check for /promote-dossier's Prerequisite section: is the Jarvis
vault actually reachable, and by which of the two documented paths?

This turns a prose "check first, don't assume" instruction into something a
model doesn't have to reason its way through each time. It CANNOT check whether
the Obsidian MCP tools are actually live-connected in the current session --
that's session state, not something visible to a standalone script -- so it
checks the one thing it honestly can: whether this machine's Claude Code config
registers the jarvis/jarvis-fs MCP servers at all. A real connection still has
to be confirmed the documented way (call mcp__jarvis__vault_list and check it
returns real content) -- this script narrows "which path is even possible,"
it does not replace that live confirmation.

Usage:
    python3 check_vault_reachability.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]  # .claude/skills/promote-dossier/scripts/ -> repo root
SIBLING_JARVIS_CANDIDATES = [
    REPO_ROOT.parent / "Jarvis",
    REPO_ROOT.parent / "jarvis-checkout",
]


def check_sibling_checkout() -> tuple[bool, str]:
    for candidate in SIBLING_JARVIS_CANDIDATES:
        if candidate.is_dir() and (candidate / ".git").exists():
            result = subprocess.run(
                ["git", "-C", str(candidate), "remote", "get-url", "origin"],
                capture_output=True, text=True, check=False,
            )
            remote = result.stdout.strip() if result.returncode == 0 else "(remote unknown)"
            return True, f"found real git checkout at {candidate} (origin: {remote})"
    return False, f"no sibling checkout found at any of: {', '.join(str(c) for c in SIBLING_JARVIS_CANDIDATES)}"


def check_mcp_registration() -> tuple[bool, str]:
    """Best-effort, config-existence check only -- see module docstring for why
    this can't confirm a live connection."""
    candidates = [
        Path.home() / ".claude.json",
        Path.home() / ".claude" / ".mcp.json",
        REPO_ROOT / ".mcp.json",
        REPO_ROOT / ".claude" / "settings.json",
    ]
    found_in = []
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        servers = data.get("mcpServers", {})
        if isinstance(servers, dict) and ("jarvis" in servers or "jarvis-fs" in servers):
            found_in.append(str(path))
    if found_in:
        return True, f"jarvis/jarvis-fs MCP server registered in: {', '.join(found_in)} (config presence only -- confirm the live connection with mcp__jarvis__vault_list before trusting it)"
    return False, "jarvis/jarvis-fs MCP server not found registered in any checked config file"


def main() -> None:
    sibling_ok, sibling_detail = check_sibling_checkout()
    mcp_ok, mcp_detail = check_mcp_registration()

    print("## Vault reachability check")
    print()
    print(f"Sibling git checkout: {'POSSIBLE' if sibling_ok else 'NOT FOUND'} -- {sibling_detail}")
    print(f"MCP registration:     {'POSSIBLE' if mcp_ok else 'NOT FOUND'} -- {mcp_detail}")
    print()

    if not sibling_ok and not mcp_ok:
        print("NEITHER path is available. Per this skill's own Prerequisite section: stop and")
        print("tell the user -- do not guess at vault paths or fabricate content from memory.")
        sys.exit(1)

    if sibling_ok:
        print(f"Recommended path: git checkout at the location above. Use Read/Edit/Write on")
        print("its real paths, and git status/git diff before any commit, same review discipline")
        print("as any other repo.")
    elif mcp_ok:
        print("Recommended path: Obsidian MCP tools. Before proceeding, actually call")
        print("mcp__jarvis__vault_list and confirm it returns real vault content -- config")
        print("presence alone (what this script checked) is not the same as a live connection.")


if __name__ == "__main__":
    main()
