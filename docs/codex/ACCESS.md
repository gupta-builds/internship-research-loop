# Access and tooling memory

Verified on 2026-10-03. “Exposed” is not the same as “safe” or “tested.” Re-check connectivity at the start of any operation that depends on external state.

## Local repository

- Workspace write access: this repository and `/tmp`.
- Git remote: `https://github.com/gupta-builds/internship-research-loop.git`.
- Current branch at audit: `master`, clean, aligned with `origin/master` at `a3664ca`.
- The repository is public. Never commit Jarvis personal data, contacts, secret values, or private application material.
- Local test command: `.venv/bin/python -m pytest -q`; audit baseline was 499 passed.
- The tracked pre-push hook runs tests only when `.venv/bin/python` exists; it fails open otherwise.

## Jarvis MCP

Live read access was verified with root listing, note reads, document maps, simple/structured search, tags, command listing, active-file lookup, and opening a known existing note.

Exposed tools also include binary reads, signed downloads, writes, appends, patches, copies, moves, uploads, and command execution. These mutation paths were deliberately not tested. No `vault_delete` tool and no `jarvis-fs` tool are exposed in the current Codex session even though Claude settings mention them.

Safety boundary: MCP availability is not write authorization. Program/Contact/Tracker/Applying writes require the calling skill or agent’s explicit human-consent gate. Never use `open_file` on an unknown path merely to test access because it can create a note. Never use `command_execute` without inspecting the exact command and obtaining any required authority.

Canonical live template paths include `30_Order/Templates/Career/Internship/Program Template.md`, `Contact Template.md`, `Tracking Template.md`, and `Applying Template.md`. Repository summaries currently disagree with parts of the live Program/Contact templates; re-read both before a vault write.

## GitHub

- GitHub MCP authentication was verified as `gupta-builds`; repository reads and branch listing work.
- The MCP surface exposes broad repository, issue, PR, review, release, and mutation operations. Mutation was not tested and is never implied by read access.
- Local `gh` CLI authentication was invalid at audit time. Workflows that depend on `gh issue create` or `gh workflow disable` may still work in Actions through `github.token`, but local CLI operations must be re-authenticated or use the GitHub MCP where appropriate.
- Branch `master` was reported unprotected by GitHub MCP. Treat direct pushes as publication.

## Secrets and remote writes

Only secret names are known: `JARVIS_PUSH_TOKEN` and `FIRECRAWL_API_KEY`; never print or retrieve values. `github.token` is supplied inside Actions. Secret validity/expiry and Firecrawl quota are not programmatically verified here.

Do not test write capability by mutating Jarvis, GitHub issues, workflows, branches, or files. Verify writes only when a real user-authorized task requires them, with exact targets and a reviewable preview.

## Codex/Claude configuration reality

- Codex policy: `AGENTS.md`.
- Codex-discovered skills: `.agents/skills/`.
- Codex agent definitions: `.codex/agents/*.toml` are available in the current multi-agent runtime.
- `.claude/settings*.json`, `.claude/rules/`, and `.claude/skills/` are Claude compatibility material, not Codex permissions.
- Codex `hooks` and `memories` features were disabled in the audited CLI. `.codex/hooks.json` is therefore advisory/inactive in this environment; safety must live in instructions and consent gates.
- Do not add a project `.codex/config.toml` speculatively. The installed CLI documents user configuration at `~/.codex/config.toml`; use a repository config only after current official/local support is verified.
