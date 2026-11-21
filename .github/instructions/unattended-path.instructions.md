---
applyTo: "core/**,ingestion/**,vault_writer/**,run_pipeline.py,recheck.py"
---
These files run hourly or daily in GitHub Actions with no human present. Review them against the four conventions in `CLAUDE.md`:

1. **Zero LLM.** No model call of any kind, however elaborate the logic (`enrich.py` is the one manual-CLI exception and also stays zero-LLM).
2. **Permissive by default.** An eligibility gate lets ambiguous or missing data pass; only an explicit negative signal (a denylist token, an explicit exclusion string) rejects. Flag any new rule that rejects on missing data: a false negative silently drops a real posting.
3. **Fail-closed write gate.** `vault_writer/validate.py` order is `required_fields`, `not_duplicate`, `cross_source_duplicate`, `url_liveness`, `format_compliance`: free checks before network checks, first failure wins. Flag a reorder that does not restate the cost reasoning.
4. **Cited real data.** A new regex, keyword, denylist entry or threshold must name the real company, posting or fixture it was checked against, and the date, in a comment beside it.

Also check: a changed constant such as `QUOTA_PER_RUN`, `HARD_PAUSE_TOTAL_THRESHOLD`, `BUCKET_CAPACITY` or `GLOBAL_*_THRESHOLDS` has a test that exercises the new value; a push or commit path cannot run in a dry-run or test context; no new failure path files an issue silently.
