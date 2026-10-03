#!/usr/bin/env bash
set -eu

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [ ! -f scripts/hooks/pre-push ]; then
  echo "setup: run this from the internship-research-loop checkout" >&2
  exit 1
fi

git config --local pull.ff only
git config --local fetch.prune true
git config --local push.autoSetupRemote true
git config --local push.default simple

hooks_dir="$(git rev-parse --git-path hooks)"
mkdir -p "$hooks_dir"
cp scripts/hooks/pre-push "$hooks_dir/pre-push"
chmod +x "$hooks_dir/pre-push"

echo "Configured this checkout:"
echo "  pull.ff=only"
echo "  fetch.prune=true"
echo "  push.autoSetupRemote=true"
echo "  push.default=simple"
echo "  installed scripts/hooks/pre-push"
echo
echo "Next: read docs/TWO_LAPTOP_WORKFLOW.md before starting work."
