# Copilot review instructions: internship-research-loop

This file wins over `CLAUDE.md` and `AGENTS.md`, which are guidance for other coding agents. Review once per PR, only judgment calls. Be brief.

## What is already checked (do not comment on these)
Deterministic CI (`pr-gates`, `pytest`, `dependency-review`) already enforces: branch name, PR title and size, commit hygiene (no merge, fixup or WIP commits, no `Test` identity), forbidden paths, linked issue, tests changed with code, workflow security lint, zero-LLM imports in the unattended path, and the PR template. Do not repeat a failing check; do not comment on formatting, style or naming.

## What to review
1. **Behavior**: bugs, wrong edge cases, silently swallowed errors, data loss. Show the failing input and the wrong output.
2. **The four conventions** (details in `.github/instructions/unattended-path.instructions.md`):
   zero LLM in the unattended path; permissive-by-default filtering (a false negative kills a real posting); fail-closed write-gate order `required_fields -> not_duplicate -> cross_source_duplicate -> url_liveness -> format_compliance`; every new rule cites real data and a date next to the code.
3. **Public repo**: this repository is public. Flag anything that looks like personal career data, contact details, cover-letter content, tokens or machine-local paths. Cover letters are never published.
4. **Workflow safety**: see `.github/instructions/workflows.instructions.md`.
5. **Scope**: one PR is one phase. Flag unrelated changes smuggled in, and flag a PR whose description claims something the diff does not do.

## Context to keep in mind
- One host (the Dell WSL) holds every checkout; the Acer connects over Tailscale SSH. Branches are `feature|fix|docs|chore/<topic>` made in a `git worktree`; never machine-named. Work may have been done from either laptop; do not comment on authorship or machine.
- GitHub Actions commit `state/` and `logs/` to `master` as the bot. `dossier_uids.json`, `state/`, `logs/` and `graphify-out/` are generated: do not review their contents line by line.
- Every PR closes an issue; phase issues live in the milestone `Weekend Build 2026-11-21`.

## How to comment
- Label each comment `blocker`, `should-fix` or `nit`. Skip nits entirely unless there are no blockers.
- Maximum 5 comments per review. Cite `file:line`. One concrete suggestion each, no restating the diff.
- If you find nothing that matters, say so in one line. Never invent a problem to fill the review.
