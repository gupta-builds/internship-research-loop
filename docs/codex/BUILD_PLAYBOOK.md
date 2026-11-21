# Heavy-build playbook

Use this sequence for changes that touch production behavior, CI, vault contracts, agents, or skills.

## 1. Establish current truth

Read `AGENTS.md`, `README.md`, `PRD.md`, and the affected source plus its matching tests. Treat dated counts/status in docs and Jarvis notes as snapshots. Inspect `git status` before editing and preserve unrelated work.

For vault-integrated work, verify Jarvis connectivity with a cheap read and read the current workflow, standard, and template paths involved. Resolve disagreements explicitly; do not silently choose whichever copy is convenient.

## 2. Classify the work

- Mechanical unattended behavior belongs in deterministic Python.
- Novel judgment belongs in a human-gated skill/agent.
- Cross-repository access alone does not justify “AI judgment”; keep writer agents low-freedom where the task is copying known facts.
- Do not duplicate rules across `AGENTS.md`, skills, agents, and context files. Put the rule in the narrowest canonical layer and point to it elsewhere.

## 3. Design against invariants

Before changing `core/`, `ingestion/`, `vault_writer/`, `run_pipeline.py`, or `recheck.py`, state how the change preserves zero-LLM operation, permissive filtering, validation order, and real-data citations. Identify state transitions and failure points across both repositories.

For a new source or rule, capture real observed data first. Do not create a clean synthetic fixture and present it as source evidence.

For Jarvis notes, use the live template and repository contract together, preserve required null/empty fields, preview exact paths/content, and obtain explicit consent before writing.

## 4. Implement narrowly

Keep unrelated refactors separate. Add or adjust the matching tests in the same change. Avoid broad `git add -A` in an interactive dirty checkout. Never force-push, silently file issues, disable workflows, or mutate the vault as a diagnostic.

## 5. Verify proportionally

Run focused tests during iteration and the full suite before handoff. For convention-sensitive production changes, use the `review-loop-change` skill before commit/push. Inspect the final diff, check for secrets/private vault content, and call out untested external behavior.

For workflow changes, validate YAML and reason through permissions, schedules, token sources, concurrency, retry behavior, and what happens before Python can log a failure. For stateful changes, test corruption, retries, partial failure, idempotency, and recovery—not only the happy path.

## 6. Handoff with evidence

Report files changed, tests and exact result, external operations performed, and remaining risks. Distinguish verified current facts from exposed capabilities and historical documentation. Do not claim a hook, agent, secret, workflow, or MCP mutation works merely because configuration mentions it.
