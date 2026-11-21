---
applyTo: "tests/**"
---
`tests/` mirrors `core/`, `ingestion/` and `vault_writer/` file for file. Review:

- A new fixture is real data (an actual posting, company or incident) with its date, not an invented example. Convention 4 applies to tests too.
- A test fails for the right reason: it would fail if the behavior under test were broken, not only if the module cannot be imported.
- No test touches the network, the real vault, `state/` or `logs/`, and none modifies git config, because a throwaway repo created inside a hook once rewrote the real repo's config (2026-11-21).
- A new source follows the existing `test_schema_drift.py` pattern instead of a new shape.
