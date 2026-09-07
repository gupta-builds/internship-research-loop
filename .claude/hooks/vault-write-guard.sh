#!/bin/bash
# PreToolUse guard for internship-research-loop's Jarvis-vault write calls.
# Fires before mcp__jarvis__vault_write/patch/move/delete and the
# jarvis-fs write/edit/move tools - a no-op for anything else.
# Advisory only - never denies (PreToolUse *can* block, this one doesn't).
# The "ask" entry for vault_delete in settings.json is the real gate; this
# hook only adds context, it doesn't duplicate that gate.
# Fails open on any parse problem.

set -u
input="$(cat)"

tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null)"
[ -z "$tool_name" ] && exit 0

case "$tool_name" in
  mcp__jarvis__vault_delete)
    msg="vault-write-guard: vault_delete is the one Jarvis call this repo always asks approval for (see .claude/rules/mcp-permissions.md) - confirm this is a single, human-approved deletion, not part of a batch or automated action."
    ;;
  mcp__jarvis__vault_write|mcp__jarvis__vault_patch|mcp__jarvis__vault_move|mcp__jarvis-fs__write_file|mcp__jarvis-fs__edit_file|mcp__jarvis-fs__move_file)
    msg="vault-write-guard: writing to the live Jarvis vault - confirm the human consent gate already happened (.claude/rules/jarvis.md) and the note shape matches CLAUDE.md's \"Note-template contracts\" section before this lands."
    ;;
  *)
    exit 0
    ;;
esac

jq -n --arg msg "$msg" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $msg}}'
exit 0
