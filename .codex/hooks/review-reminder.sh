#!/bin/bash
# PostToolUse reminder for internship-research-loop.
# Fires after Write/Edit/MultiEdit; a no-op for anything outside the
# four-convention-sensitive files this repo's own CLAUDE.md names.
# Never blocks (PostToolUse can only inform, not deny) - purely a
# just-in-time pointer to /review-loop-change and which of the four
# load-bearing conventions is most relevant to the file just touched.
# Fails open on any parse problem.

set -u
input="$(cat)"

tool_name="$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null)"
case "$tool_name" in
  Write|Edit|MultiEdit) ;;
  *) exit 0 ;;
esac

file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
[ -z "$file_path" ] && exit 0

repo_root="/home/anant_gupta/projects/work/internship-research-loop"
case "$file_path" in
  "$repo_root"/*) rel="${file_path#"$repo_root"/}" ;;
  *) exit 0 ;;
esac

reason=""
case "$rel" in
  core/filter.py)
    reason="permissive-by-default (§2): ambiguous/missing data must still pass; only an affirmative negative signal rejects."
    ;;
  core/relevance.py|core/classify.py)
    reason="permissive-by-default (§2) and cited-real-data (§4): every new pattern/threshold needs a comment naming the real company/posting/fixture it was checked against."
    ;;
  vault_writer/validate.py)
    reason="fail-closed write-gate ordering (§3): validate()'s five checks run in a specific cost order (required_fields → not_duplicate → cross_source_duplicate → url_liveness → format_compliance) - don't reorder without restating the cost reasoning."
    ;;
  run_pipeline.py|recheck.py)
    reason="zero-LLM in the unattended path (§1): this file runs hourly/daily via GitHub Actions with no human in the loop."
    ;;
  ingestion/*.py)
    reason="zero-LLM in the unattended path (§1) and cited-real-data (§4) for any new source-specific pattern."
    ;;
  *)
    exit 0
    ;;
esac

msg="review-reminder: '$rel' is one of this repo's convention-sensitive files ($reason). Run /review-loop-change against this diff before committing/pushing - see CLAUDE.md's \"Conventions this codebase enforces\" section for the full list."

jq -n --arg msg "$msg" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $msg}}'
exit 0
