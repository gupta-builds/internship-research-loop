---
paths:
  - "tests/**"
---
# Tests
Applies when you edit or add a test or fixture. Adds to CLAUDE.md.

## Do
- A pipeline fixture is a recorded public page or response, such as `tests/fixtures/posting_*.md` or a source's saved JSON. Name where and when it was recorded.
- A fixture with application content (a resume, a letter, a message) is synthetic and says so in a comment. No real resume text enters this public repo.
- Patch the network, never call it: patch `requests.get` as `tests/test_sources.py` does, or pass a fake `http_head`.
- A test for a new source follows the existing pattern in `tests/test_schema_drift.py` until that file is parametrized in its own change.
- Run the file you changed with `uv run pytest -q tests/<file>.py`, then the full suite with `uv run pytest -q`.

## Never
- Never weaken an assertion or delete a case to make a test pass. Fix the code, or stop and say which case fails and why.
- Never pipe pytest output into `head`, `tail` or `grep`. Read the whole result.
