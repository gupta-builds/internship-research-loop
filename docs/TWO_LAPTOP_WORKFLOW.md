# Two-laptop Git workflow

`origin/master` is the canonical shared state. A laptop checkout is a cache of that state, never another source of truth. Human work reaches `master` only through a pull request; scheduled GitHub Actions may still commit their owned `state/` and `logs/` updates directly.

## One-time setup on each laptop

```bash
git switch master
git pull --ff-only origin master
scripts/setup-two-laptop-git.sh
```

The setup installs the tracked pre-push hook and makes ordinary pulls fast-forward-only. The hook blocks direct pushes to `master` and fails closed if it cannot run the test suite.

## Branch names

Name the task, not the machine:

- `feature/<short-topic>`
- `fix/<short-topic>`
- `docs/<short-topic>`
- `chore/<short-topic>`

Examples: `fix/recheck-partial-source-failure`, `chore/uv-environment`, `docs/two-laptop-workflow`.

Laptop identity does not belong in the branch name. Branch ownership is temporary and recorded by who is actively working on it.

## Start every task

First require a clean checkout:

```bash
git status --short
```

If this prints anything, stop. Commit the current task on its branch, stash it intentionally with a descriptive message, or finish the handoff procedure below. Never pull or switch branches merely to make uncommitted work disappear.

Then synchronize and branch:

```bash
git fetch origin --prune
git switch master
git pull --ff-only origin master
git switch -c <type>/<short-topic>
```

The fetch matters because Actions and the other laptop can advance `master` between sessions. `--ff-only` turns unexpected divergence into a visible stop instead of an automatic merge commit.

## While working

- One task per branch and one owning laptop per branch.
- Never work on the same branch from both laptops concurrently.
- Commit only files belonging to the task; inspect `git status` and `git diff --staged` before every commit.
- Push the branch at useful checkpoints so it is backed up remotely.
- Do not use `git add -A` in a checkout containing unrelated work.

Before opening or updating the PR:

```bash
git fetch origin --prune
git rebase origin/master
python -m pytest -q
git push --force-with-lease
```

Use `.venv/bin/python -m pytest -q` when the project virtual environment is active. `--force-with-lease` is permitted only on the task branch after its rebase; never use plain `--force`, and never force-push `master`.

## Pull request and merge

The PR targets `master`. It must describe the change, verification, and anything intentionally deferred. Confirm CI passes and the branch is based on current `origin/master`, then use a rebase merge to preserve the repository's linear history. Delete the remote task branch after merge.

Immediately synchronize the merging laptop:

```bash
git switch master
git pull --ff-only origin master
git branch -d <type>/<short-topic>
git fetch origin --prune
```

The other laptop runs the same `master` synchronization before its next task.

## Move an unfinished task to the other laptop

This is a handoff, not concurrent collaboration.

On the current owner:

```bash
git status --short
git push -u origin <type>/<short-topic>
```

The worktree must be clean after the push. Tell the other laptop that ownership is transferred and do not make further commits there.

On the receiving laptop:

```bash
git fetch origin --prune
git switch --track origin/<type>/<short-topic>
git status --short
```

Confirm the expected latest commit before editing. To hand it back, repeat the same clean-push-transfer sequence.

## Recovery rules

- Dirty `master`: create a correctly named task branch immediately (`git switch -c <type>/<topic>`); do not commit the work on `master`.
- `master` diverged from `origin/master`: stop and inspect both histories. Do not reset, rebase, or force-push until the unique commits are identified.
- Same branch edited on both laptops: stop both writers. Push neither side. Compare commits and working-tree patches, choose one owner, then integrate deliberately on that branch.
- Accidental direct push to `master`: stop new work, inspect the pushed commit, let CI finish, and synchronize both laptops. Never “repair” it with a force-push.
- Unclear ownership or unexplained local changes: preserve them and ask. Unknown changes are evidence, not clutter.

## Why `master` is not server-protected

`run.yml`, `recheck.yml`, and related scheduled automation commit pipeline-owned state/log updates directly to `master`. A blanket “PR required” rule would block those jobs unless a reliable bot bypass were configured. Until that is available and tested, the tracked local hook is the human-write guard and PR review is the integration gate.

Emergency bypass exists as `ALLOW_MASTER_PUSH=1 git push ...`, but it is for an explicitly reviewed recovery operation only—not ordinary development.
