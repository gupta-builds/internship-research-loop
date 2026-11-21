---
applyTo: ".github/workflows/**,.github/rulesets/**,scripts/ci/**,scripts/hooks/**"
---
The mechanical rules (no `pull_request_target`, a `permissions:` block, no PR-controlled text interpolated into `run:`, third-party actions pinned to a SHA) are enforced by the `workflow_lint` gate. Review only what a linter cannot:

- **Least privilege.** Is each `permissions:` scope actually needed by that job? A write scope on a job that only reads is a finding.
- **Which token.** This repo's bot pushes with `REPO_BOT_TOKEN` (repo-scoped fine-grained PAT), the Jarvis vault with `JARVIS_PUSH_TOKEN`. The owner's global agent PAT must never be referenced by a workflow. Secrets are named, never echoed.
- **Required check names.** The ruleset requires the contexts `pytest` and `pr-gates`. Renaming a job or workflow that produces them silently removes the protection.
- **Bot safety.** A scheduled workflow that commits to `master` must not loop (its own push must not retrigger it) and must keep the retry-once-on-rejection behavior in `core/git_ops.py`.
- **Cost.** Flag a trigger that would run on every push to every branch, or a schedule more frequent than the data changes.
