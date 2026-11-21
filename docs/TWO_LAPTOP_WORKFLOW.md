# Two-laptop Git workflow (single host, one worktree per task)

`origin/master` is the canonical shared state. Human work reaches `master` only through a pull request; scheduled GitHub Actions may still commit their owned `state/` and `logs/` updates directly.

This document supersedes the earlier two-independent-clones design and the `<machine>/<topic>` branch naming that older notes still mention.

## Topology

- The **Dell** (`DESKTOP-3VBG0JH`, WSL, Tailscale node `dell-wsl`) is the single canonical host. The only clone of this repo lives there, under `~/projects/work/internship-research-loop`.
- The **Acer** (`gupta-builds`) is a display: it reaches the Dell with `ssh dell-wsl` over Tailscale SSH. **Nothing is cloned on the Acer**, including its WSL.
- Identify the session you are in before touching anything:
  ```bash
  hostname                          # DESKTOP-3VBG0JH on the Dell, always, even over SSH
  echo "${SSH_CONNECTION:-local}"   # "local" at the Dell, or the Acer's Tailscale IP (100.84.91.11) when remote
  ```
  Both laptops therefore work on the same filesystem and the same Git state. Two sessions are kept apart by task, using `git worktree`. No lock enforces this except the convention below.

## The main checkout is the hub

`~/projects/work/internship-research-loop` stays on `master`, is never edited, and is only updated with:

```bash
git pull --ff-only origin master
```

It is where worktrees are created from and where the shared `.git/hooks` live. A dirty main checkout is a bug: see Recovery rules.

## Worktree lifecycle

One worktree per task, under `~/projects/work/.worktrees/`, named `internship-research-loop-<slug>`, where the slug is the branch's type and topic joined by a hyphen (`fix/recheck-partial-source-failure` becomes `internship-research-loop-fix-recheck-partial-source-failure`).

```bash
export GRAPHIFY_SKIP_HOOK=1
cd ~/projects/work/internship-research-loop
git fetch origin --prune
W=~/projects/work/.worktrees
git worktree add $W/internship-research-loop-<type>-<topic> -b <type>/<topic> origin/master
git worktree lock --reason "owner: <session/phase> <date>" $W/internship-research-loop-<type>-<topic>

# work, commit, test (see below)
git push -u origin <type>/<topic>      # first push; plain `git push` afterwards

# when the PR is merged, or the work is handed off:
git worktree unlock $W/internship-research-loop-<type>-<topic>
git worktree remove $W/internship-research-loop-<type>-<topic>
git branch -d <type>/<topic>           # -D if a rebase merge hides the ancestry; check first that `git cherry -v origin/master <branch>` shows only "-" lines
git fetch --prune
git worktree prune
```

## Branch names

Name the task, never the machine:

- `feature/<short-topic>`
- `fix/<short-topic>`
- `docs/<short-topic>`
- `chore/<short-topic>`

Examples: `fix/recheck-partial-source-failure`, `chore/uv-environment`, `docs/codex-agent-memory`. Laptop identity does not belong in the branch name; the `<machine>/<topic>` form (for example `dell-latitude/...`) is retired.

## Per-worktree setup

Git hooks live in the shared `.git/hooks` (installed once from the tracked `scripts/hooks/pre-push` by `scripts/setup-two-laptop-git.sh`, run in the main checkout) and apply to every worktree. The pre-push hook blocks pushes to `master`, then runs the test suite, falling back to `uv run` when a worktree has no `.venv`. Three graphify hooks also write into the vault on commit, checkout and merge.

In every new worktree:

```bash
export GRAPHIFY_SKIP_HOOK=1   # keeps commits from rebuilding graphify or writing into the vault
uv sync
uv run pytest -q
```

`uv`'s cache and the worktree root share a filesystem, so each `uv sync` is cheap.

## Commit cadence

- One coherent change per commit, imperative subject, a body that says why.
- Tests green at each commit.
- Add explicit paths. Never `git add -A` or `git add .`. Read `git diff --staged` before every commit.
- Run `git diff --check` before committing.
- Push at every checkpoint so the branch is backed up on origin.

## One phase = one branch = one PR

Open the PR when the phase's done condition holds, using `.github/pull_request_template.md`. Describe the change, the verification and anything deferred. Confirm CI passes and the branch is based on current `origin/master`, then **rebase-merge** it (`gh pr merge <n> --rebase`) to keep the history linear. After the merge:

1. Remove the worktree, delete the local branch and `git fetch --prune` (see the lifecycle above).
2. Update the main checkout: `git pull --ff-only origin master`.
3. Rebase **every other open worktree** onto the new master:
   ```bash
   git fetch origin --prune && git rebase origin/master && git push --force-with-lease
   ```
   `--force-with-lease` is allowed only on your own task branch and only after its remote exists. Never use plain `--force`, and never force-push `master`.

## State and logs are bot-owned

`state/` and `logs/` are tracked paths owned by the scheduled Actions. A feature branch does not edit them unless the task is a deliberate state repair. Any run of a pipeline script inside a worktree must use `--dry-run` or temporary paths, and must leave `git status` clean.

## Ownership

Ownership of a worktree is `git worktree lock`, and nothing else:

- Never run two sessions in one worktree.
- A session ends by pushing, confirming a clean tree (`git status --short` prints nothing) and unlocking the worktree.
- Before using an existing worktree, check `git worktree list` for `locked`. A locked worktree belongs to another session: do not edit, unlock or remove it.
- To switch displays, end the session as above and start a new one. The worktree stays on the Dell.

## Recovery rules

- Dirty `master` (main checkout): preserve the changes first (copy or patch outside the repo), then move them to a correctly named task branch in its own worktree. Do not commit on `master`.
- `master` diverged from `origin/master`: stop and inspect both histories. Do not reset, rebase, or force-push until the unique commits are identified.
- Same worktree used by two sessions: stop both writers. Push neither side. Compare commits and working-tree patches, choose one owner, then integrate deliberately on that branch.
- Accidental direct push to `master`: stop new work, inspect the pushed commit, let CI finish, and update the main checkout. Never "repair" it with a force-push.
- Unclear ownership or unexplained local changes: preserve them and ask. Unknown changes are evidence, not clutter.

## PR gates

`.github/workflows/pr-gates.yml` runs `scripts/ci/pr_gates.py` (stdlib + `gh`, no LLM) on every PR; `python3 scripts/ci/pr_gates.py --pr N` runs the same checks locally. Limits and their source data are in comments next to each rule in the script.

| Gate | Checks | Draft PRs |
|---|---|---|
| `branch_name` | `feature/`, `fix/`, `docs/` or `chore/` + kebab-case (or `dependabot/*`); the old `<machine>/<topic>` form fails | checked |
| `pr_title` | at most 90 chars, no trailing period, no WIP/Draft prefix | checked |
| `commits` | one parent each, subject at most 100 chars, no `fixup!`/`squash!`/WIP, no `Test <test@example.com>` identity | checked |
| `forbidden_paths` | `Cover Letters/`, `.env*`, keys, `graphify-out/`, `.worktrees/`, `*.orig`, `*.rej`, `*.bundle`, `recovery-*`, `.claude/settings.local.json` | checked |
| `linked_issue` | `Closes/Fixes/Resolves/Refs #N` in the body | warn only until P1.5b; flip it by adding it to `GATES_ENFORCE` |
| `template_sections` | `Verification` and `Repository conventions` present, no unchecked box (tick N/A boxes and write N/A) | skipped |
| `size` | at most 36 files and 800 added+deleted lines | skipped |
| `wip_limit` | no older open non-draft PR | skipped |

Rules of use: one open PR at a time; open it as a draft and mark it ready only when `pytest` and `pr-gates` are green. Override labels: `large-ok` (size), `parallel-ok` (wip_limit), `no-issue` (linked_issue).

The rulesets in `.github/rulesets/` are importable and **not applied**. The owner applies them: `gh api -X POST repos/gupta-builds/internship-research-loop/rulesets --input .github/rulesets/master.json`. Do this only after the bot-bypass decision below is made: on a user-owned repo the Actions app cannot be a bypass actor (probe 2026-11-21), so a ruleset with no bypass blocks the scheduled workflows' direct state/log commits to `master`. `branch_name_pattern` is not available on this plan, so branch names are enforced by the `branch_name` gate instead.

## Why `master` is not server-protected

`run.yml`, `recheck.yml`, and related scheduled automation commit pipeline-owned state/log updates directly to `master`. A blanket "PR required" rule would block those jobs unless a reliable bot bypass were configured. Until that is available and tested, the tracked local hook is the human-write guard and PR review is the integration gate.

Emergency bypass exists as `ALLOW_MASTER_PUSH=1 git push ...`, but it is for an explicitly reviewed recovery operation only, not ordinary development.
