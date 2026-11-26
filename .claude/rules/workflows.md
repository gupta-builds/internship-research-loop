---
paths:
  - ".github/workflows/**"
---
# GitHub Actions workflows
Applies when you edit a workflow. Adds to CLAUDE.md.

## Do
- Keep every workflow free of model calls. The scheduled runs are the unattended path.
- Pass secrets only through `secrets.*`, by name. Never echo one.
- Declare `permissions:` in every workflow, with the least access the job needs. Every workflow here does today.
- Concurrency groups exist only in `test.yml`, `pr-gates.yml` and `dependency-review.yml`. If you add one elsewhere, say why in a comment.
- `python3 scripts/ci/pr_gates.py --pr N` runs the workflow lint the PR gate runs.

## Never
- Never edit `state/` or `logs/` by hand. The scheduled workflows commit them as the bot.
- Never interpolate `github.event.*` or `github.head_ref` straight into a `run:` line. Pass it through `env:`.
