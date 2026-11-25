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

## The loop: issue, branch, PR, merge

1. **Issue first.** Every unit of work is a Task issue (form in `.github/ISSUE_TEMPLATE/`) in the milestone for the current build. Phases are parent issues labelled `phase`; tasks are their sub-issues.
2. **Worktree and branch** named for the task (see above), created from a fresh `origin/master`.
3. **Draft PR early**, body from the template with `Closes #N`. Commit small and often; push the branch.
4. **Gates run on every push** (below). Fix red before asking for a review.
5. **Ready for review** only when `pytest`, `pr-gates` and `dependency-review` are green. That is the one moment Copilot reviews (once; not on each push). Its instructions are in `.github/copilot-instructions.md` and `.github/instructions/`.
6. **Rebase-merge**, branch auto-deleted, issue auto-closed by `Closes #N`, Project item moves to Done by the built-in workflows. Then remove the worktree.

Only one non-draft PR is open at a time. If two phases truly must overlap, label the later one `parallel-ok` and say why in its body.

## PR gates

`.github/workflows/pr-gates.yml` runs `scripts/ci/pr_gates.py` (stdlib + `gh`, no LLM) on every PR; `python3 scripts/ci/pr_gates.py --pr N` runs the same checks locally. Limits and their source data are in comments next to each rule in the script. Gates marked "warn" annotate but do not fail.

| Gate | Checks | Draft PRs |
|---|---|---|
| `branch_name` | `feature/`, `fix/`, `docs/` or `chore/` + kebab-case (or `dependabot/*`); the old `<machine>/<topic>` form fails | checked |
| `pr_title` | at most 90 chars, no trailing period, no WIP/Draft prefix | checked |
| `commits` | one parent each, subject at most 100 chars, no `fixup!`/`squash!`/WIP, no `Test <test@example.com>` identity | checked |
| `forbidden_paths` | `Cover Letters/`, `.env*`, keys, `graphify-out/`, `.worktrees/`, `*.orig`, `*.rej`, `*.bundle`, `recovery-*`, `.claude/settings.local.json` | checked |
| `linked_issue` | `Closes/Fixes/Resolves/Refs #N` in the body (Dependabot exempt) | checked |
| `tests_with_code` | a change to `core/`, `ingestion/`, `vault_writer/`, `run_pipeline.py` or `recheck.py` also changes `tests/` (35 of 35 real commits did) | checked |
| `workflow_lint` | each changed workflow: `pull_request_target` never checks out an explicit ref, has `permissions:`, no `${{ github.event.* }}` in a `run:` script, actions pinned (third-party by SHA) | checked |
| `conventions` | `check_conventions.py` check 1: no LLM import or API call in the unattended path | checked |
| `conventions_advisory` | `check_conventions.py` checks 2-4 (warn only, heuristic) | checked |
| `template_sections` | `Verification` and `Repository conventions` present, no unchecked box (tick N/A boxes and write N/A) | skipped |
| `size` | at most 36 files and 800 added+deleted lines | skipped |
| `wip_limit` | no older open non-draft PR | skipped |

Override labels (defined in `.github/labels.yml`, explain each use in the PR body): `large-ok`, `parallel-ok`, `no-issue`, `no-tests-ok`.

Tamper-proofing: `pr-gates.yml` uses `pull_request_target`, so GitHub runs the workflow and gate script from `master`, never from the PR. It is safe because nothing checks out PR code (the script reads the PR through the API) and `workflow_lint` rejects an explicit `ref:` checkout under that trigger. A change to the gate takes effect only after it merges. `dependency-review` and `pytest` need the PR's own code, so they stay on `pull_request`.

## Copilot review and the review record

Copilot is the one LLM step, and it runs once per PR, on the ready-for-review transition, never on every push. Everything it can be asked to check mechanically is a zero-LLM gate instead, so its comments are limited to judgment: behavior bugs, the four conventions, public-repo leaks, workflow safety, scope, and AI slop (code or prose that does not serve the mission). Its instructions are `.github/copilot-instructions.md` plus the path-scoped files in `.github/instructions/`; Copilot reads them from the PR's base branch, so a change to them takes effect after it merges.

Per PR, the loop is: draft PR, gates green, mark ready, request Copilot as reviewer, fix or decline each comment, reply on the thread with the commit that fixed it (or the reason it was declined), resolve the thread, merge. Before merging, post one **review record** comment so the PR documents what the review changed:

```
Review record
- Copilot findings: N (blocker B, should-fix S, nit T), fixed F, declined D
- Declined: <finding> because <reason> (tracked in #issue if deferred)
- Gates: 12/12 pass; extra checks run: <list>
- Slop rating: 0-5 (0 = nothing found; 5 = review changed the design). Evidence: <commit shas>
```

Sprint proof is the board: Status moves Todo, In Progress, Done as the PR merges (the linked issue closes with `Closes #N`), and each merged PR carries its review record.

## Rulesets and tokens (owner steps)

Both rulesets in `.github/rulesets/` are applied and active (`master-protection` id 27867647, `copilot-review` id 27867648; checked 2026-11-25), and the secrets `FIRECRAWL_API_KEY`, `JARVIS_PUSH_TOKEN` and `REPO_BOT_TOKEN` exist. They are importable and **never applied by CI or by any agent**. To reproduce them on a fresh repo, the owner runs, in this order:

1. Create two fine-grained PATs: one for `gupta-builds/Jarvis` only, one for this repo only (Contents RW, Issues RW, Metadata R). Store them with `gh secret set JARVIS_PUSH_TOKEN` and `gh secret set REPO_BOT_TOKEN` (hidden prompt; never paste a value into a chat or file). Workflows push this repo with `REPO_BOT_TOKEN` and fall back to the default token while it is unset. The owner's global agent PAT is never used by a workflow.
2. Verify the bot path with one manual run of `recheck.yml` (`workflow_dispatch`) before protecting `master`.
3. `gh api -X POST repos/gupta-builds/internship-research-loop/rulesets --input .github/rulesets/master.json`
4. `gh api -X POST repos/gupta-builds/internship-research-loop/rulesets --input .github/rulesets/copilot-review.json` (untested rule type; if the API returns 422, request Copilot per PR instead: `gh pr edit N --add-reviewer @copilot`).

Why the ruleset bypasses the Repository admin role: on a user-owned repo the Actions app cannot be a bypass actor and the default `GITHUB_TOKEN` is rejected (probe 2026-11-21). A PAT acts as its owner, so the admin bypass lets the bot's `state/` and `logs/` commits through. The cost: any token of the owner can also push to `master`, including the agent PAT. The guards for that are the local `pre-push` hook and the agents' rules, not GitHub. The only design with no bypass at all is the bot writing to a separate `bot-state` branch.

`branch_name_pattern` rules are not available on this plan, so branch names are enforced by the `branch_name` gate.

## Reusing this in another repo

1. Copy `.github/{labels.yml,pull_request_template.md,ISSUE_TEMPLATE/,workflows/pr-gates.yml,workflows/sync-labels.yml,dependabot.yml,copilot-instructions.md,instructions/,rulesets/}`, `scripts/ci/pr_gates.py`, `scripts/github/sync_labels.py` and the matching tests.
2. Per-repo knobs, each re-measured from that repo's own history: the `CODE_RE` source paths and `tests/` rule, `SIZE_MAX_*`, `TITLE_MAX`, `SUBJECT_MAX`, `FORBIDDEN_RES`, the `CONVENTIONS_PATH` checker (drop `conventions` if there is none), the required check names in the ruleset, and the repo facts in `copilot-instructions.md`.
3. `python3 scripts/github/sync_labels.py`, create the milestone and Project, then apply the rulesets.
4. Run `python3 scripts/ci/pr_gates.py --pr N` on a few real PRs and calibrate with data before enforcing.

## Why `master` is protected by ruleset, not by trust

`run.yml`, `recheck.yml` and `reseed.yml` commit pipeline-owned state and logs directly to `master`. That is why protection waited for a tested bot path: the repo-scoped `REPO_BOT_TOKEN` plus the admin-role bypass above. The tracked local `pre-push` hook still blocks human pushes to `master` on every checkout.

Emergency bypass exists as `ALLOW_MASTER_PUSH=1 git push ...`, but it is for an explicitly reviewed recovery operation only, not ordinary development.
