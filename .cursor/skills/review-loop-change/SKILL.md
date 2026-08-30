---
name: review-loop-change
description: >-
  Reviews a proposed change to internship-research-loop against this repo's own
  established conventions (zero-LLM in the unattended path, permissive-by-default
  filtering, fail-closed write-gate ordering, cited-real-data rule comments) before
  it ships. Use before committing/pushing a change to core/, ingestion/,
  vault_writer/, run_pipeline.py, recheck.py, or revalidate.py.
disable-model-invocation: true
---

# review-loop-change

A repo-scoped convention check, not a general code review (use a general code-review pass for correctness/security/style). This exists because this repo has a small number of load-bearing design decisions that are easy to accidentally violate one file at a time without ever being wrong in isolation — a new filter rule that's individually correct but calls an LLM, or a new check that's individually correct but inserted before a cheaper one in the write gate. Catching that needs to compare the diff against the repo's conventions specifically, not against general best practice.

## Why a skill, not a subagent, for this repo

This repo is ~1,500 lines with a ~1:1 test-to-code ratio (`tests/` mirrors `core/`, `ingestion/`, `vault_writer/` almost file-for-file) and changes land as small, individually-reviewable diffs (see `git log` — commits like "Four new discovery sources" or a single-file bloat fix, not sprawling multi-file rewrites). A diff this size doesn't need an isolated subagent context to protect the main conversation's window, and the checklist below is fixed and specific rather than open-ended — both are exactly the case where a lightweight, inline skill beats spinning up a separate agent. If this repo ever grows enough that a single diff regularly spans dozens of files, revisit this choice; the checklist would still apply, only the delivery mechanism would need to change.

## What to check

Run against the actual diff — `git diff` (unstaged), `git diff --cached` (staged), or a specific file/range if the user names one. This is a **reports-only** check: never modify code as part of this skill; if a violation should be fixed, say so and let the user (or a follow-up edit) do it.

### 1. Zero-LLM in the unattended path
`run_pipeline.py`, `recheck.py`, `revalidate.py`, `core/filter.py`, `core/relevance.py`, `core/classify.py`, everything under `ingestion/`, and `vault_writer/` all run unattended (hourly/daily/weekly via GitHub Actions, no human in the loop) and must never call an LLM API, however indirectly. `enrich.py`/`grade_resume.py` are the explicit exceptions — manual CLI tools a human runs on demand at promotion/grading time (see their own docstrings) — and even they say "No LLM call anywhere" in their own headers; a diff that adds LLM-backed logic to either still fails this check, since the zero-LLM property is about content generation, not about being unattended specifically.
- Flag: any new `import` of an LLM/AI SDK, any new HTTP call to an LLM provider endpoint, any prompt-shaped string literal, in any of the unattended-path files above.
- Pass: keyword/regex/structural logic, however elaborate (see `core/relevance.py`'s two-stage design for what "elaborate but still zero-LLM" looks like).

### 2. Permissive-by-default / explicit-negative-signal design
Every eligibility check in this repo (`location_eligible`, `degrees_eligible`, the term/season matchers in `core/filter.py`) follows one shape: **ambiguous or missing data passes; only an affirmative negative signal rejects.** This is a deliberate, load-bearing choice (see `core/filter.py`'s own comments — "a false negative here silently kills a listing before it's ever fetched") and the opposite instinct (a new allowlist that rejects anything not explicitly matched) is the single most likely way a new rule in this codebase quietly starts throwing away real, eligible postings.
- Flag: a new gate/check where missing or unrecognized data causes rejection by default (an implicit `else: return False` / `if not X: reject` on data the source doesn't reliably provide).
- Pass: a new gate that only rejects on a specific, named affirmative signal (a denylist token, an explicit exclusion string), same shape as the existing ones.
- This rule is about *eligibility/relevance* gates specifically (Layer 2/2.5). It does not apply to the Layer 4 write gate (`vault_writer/validate.py`) — that one is intentionally fail-closed on missing required fields; don't flag it for being "not permissive," that's a different, also-intentional design (see check 3).

### 3. Fail-closed write-gate ordering
`vault_writer/validate.py`'s `validate()` runs five checks in a specific, deliberate order: `required_fields` → `not_duplicate` → `cross_source_duplicate` → `url_liveness` → `format_compliance`, short-circuiting on the first failure. The order is cost-based (free/cheap checks before ones that cost a network call) — `cross_source_duplicate` runs before `url_liveness` specifically because "it's free, the HEAD request isn't" (the function's own docstring). A change that reorders these, or inserts a new check in the wrong position relative to cost, silently makes the gate slower or changes which check's rejection reason gets reported for the same bad item.
- Flag: any diff touching `validate()`'s check sequence, or adding a new check, without an explicit note on where in the cost order it belongs and why.
- Flag: any write path (`write_dossier`, or a new one) that writes to the vault before `validate()` has been called and returned `passed=True` for that exact item.
- Pass: a new check inserted with a stated reason for its position, consistent with "free checks first."

### 4. Every new rule cites the real live data it was built from
Look through this repo's existing rule comments — `core/filter.py`'s `_NON_US` denylist ("Every foreign token actually observed in live data..."), `core/relevance.py`'s stage1/stage2 regexes ("Real examples confirmed against seeded Greenhouse boards 2026-07-26..."), `core/profile.yaml`'s `terms_weight` comment. The convention is explicit: a new keyword, regex, denylist entry, or threshold is never justified by "this seems right" — it cites the actual company/posting/fixture it was checked against and the date it was checked.
- Flag: a new regex pattern, keyword list, or magic threshold/constant added to any filter/classify/relevance/validate module with no comment tracing it to real data (a fixture file, a specific company/posting example, a date).
- Pass: a new rule with a comment naming the real evidence — doesn't need to be exhaustive, but it needs to be real and specific, not "handles edge cases."

## Output format

Keep it short — this is a fast pre-ship check, not an essay:

```
## review-loop-change: <file(s) reviewed>

[PASS]  <check name> — <one line, or omit detail entirely if clean>
[FLAG]  <check name> — file:line — <what's wrong, what the convention actually requires, one line each>
...

Ship / Fix first: <one line>
```

If the diff doesn't touch any of the conventions above (e.g. it's a test-only change, or a docs/comment-only change), say so in one line and stop — don't force a finding.
