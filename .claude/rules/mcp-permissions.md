# Jarvis MCP permission model

`.claude/settings.json` pre-approves every `jarvis` and `jarvis-fs` call
**except one**: `mcp__jarvis__vault_delete` stays in the `ask` list. Read,
write, patch, move, and edit calls on both servers are auto-allowed.

This is deliberate, not lax: the MCP-level permission was never the safety
mechanism here. Every skill or agent that actually calls a write/patch/move
tool ([[program-writer]], [[tracking]], `promotion`, `applying`,
`/promote-dossier`, `/promote-manual-find`) already enforces its own human
consent gate *before* making that call — see [[jarvis]]'s "the write itself
is always consent-gated" section. Gating the MCP call a second time would
just be the same approval asked twice.

`vault_delete` is different: **no skill or agent in this repo has a
legitimate reason to call it.** Nothing in the promotion/tracking/applying
flows ever deletes a vault note — an unexpected `vault_delete` call is
itself the signal something's wrong (a bad path, a hallucinated cleanup
step), which is exactly the case where an interactive approval prompt earns
its cost. If a future skill genuinely needs to delete a vault note on
purpose, that's a reason to design its own explicit consent step for that
action — not a reason to move `vault_delete` into `allow`.

[[hooks]]'s `vault-write-guard.sh` adds one line of context on every one of
these calls; it does not change what's gated — that's this file and
`settings.json` alone.
