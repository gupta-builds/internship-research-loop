# internship-research-loop — Claude Code guidance

This repo is small (~1,500 lines) with a ~1:1 test-to-code ratio (`tests/` mirrors `core/`, `ingestion/`, `vault_writer/` file-for-file). See `README.md` for what it does and `PRD.md` for the full spec/status. This file is about how a Claude Code session should work in it.

## Conventions this codebase enforces — read before touching core/, ingestion/, vault_writer/, run_pipeline.py, or recheck.py

These are load-bearing design decisions, not style preferences. `/review-loop-change` checks a diff against all four before it ships — but know them regardless of whether you run that skill.

1. **Zero-LLM in the unattended path.** `run_pipeline.py`, `recheck.py`, `core/filter.py`, `core/relevance.py`, `core/classify.py`, everything under `ingestion/`, and `vault_writer/` run hourly/daily via GitHub Actions with no human in the loop, and must never call an LLM, however elaborate the logic gets (see `core/relevance.py`'s two-stage design for "elaborate but still zero-LLM"). `enrich.py` is the one manual-CLI exception — a human runs it on demand — and even it stays zero-LLM by its own docstring's rule.
2. **Permissive-by-default / explicit-negative-signal filtering.** Every eligibility gate in `core/filter.py` (`location_eligible`, `degrees_eligible`, the term/season matchers) lets ambiguous or missing data pass; only an affirmative negative signal (a denylist token, an explicit exclusion string) rejects. A false negative here silently kills a real, eligible posting before a human ever sees it — worse than a false positive, which a human screens out at Step 2 of the pipeline anyway.
3. **Fail-closed write-gate ordering.** `vault_writer/validate.py`'s `validate()` runs five checks in a specific cost order — `required_fields` → `not_duplicate` → `cross_source_duplicate` → `url_liveness` → `format_compliance` — free checks before ones that cost a network call, first failure wins. Don't reorder without restating the cost reasoning.
4. **Every new rule cites the real live data it was built from, in a comment.** A new regex, keyword, denylist entry, or threshold names the actual company/posting/fixture it was checked against and the date, right next to the code (see `core/filter.py`'s `_NON_US` denylist or `core/relevance.py`'s stage1/stage2 patterns for the expected shape). "Seems right" is not a citation.

## Note-template contracts (for `/promote-dossier` and any future vault-writing code)

When writing Program, Contact, or Tracker/Each One notes into the Jarvis vault, every field below is **required and must always be present**, even as `null`/`[]` — same fail-closed-on-missing-fields discipline as `vault_writer/validate.py`'s `REQUIRED_FRONTMATTER_FIELDS` for dossiers. Full field-by-field templates with body structure live in `.claude/skills/promote-dossier/reference/note-templates.md`; this is the contract summary.

**Program note** (`Programs/Serious/` or `Programs/Considering/`) — copied from the vault's own `30_Order/Templates/Career/Program Template.md`:
`name, company, program_type, eligible_classes, grad_year, role_type, wave, opens_date, deadline_posted, deadline_real, pay_per_week, pay_currency, duration_weeks, benefits, application_url, careers_page, list_origin, applying_note, recruiter_contact, tags`. No `status`/`next` field — Program notes are durable/static, they change only when a fact about the program itself changes.

**Contact note** (`Contacts/Each One/`) — copied from `30_Order/Templates/Career/Contact Template.md`:
`type: contact, name, role, company, linkedin_url, email, how_found, relationship, related_programs, last_contact_date, tags, next`.

**Tracker/Each One note** (`Tracker/Each One/`) — the vault has **no pre-existing template** for this one (only roll-up views `Tracker/Internship - Dashboard.md` and `Tracker/Tracker.md` exist); this shape is authored from `30_Order/Workflows/Internship Pipeline.md`'s own field description:
`type: tracker, program, contact, company, url, date_noted, date_researched, date_created, date_applied, date_result, result, deadline, related_notes, tags, next`. If a real template later gets added to the vault, switch to it instead.

Cross-links: Program `list_origin` → dossier, Program `recruiter_contact` ↔ Contact `related_programs`, Tracker `program`/`contact`/`related_notes` → the other three notes. Don't invent new cross-link fields (e.g. a `tracker_note` field on Program) — propose a vault-template change explicitly if one's ever needed instead of adding it silently from a skill.

## Skills and agents available in this repo

| Name | Kind | Use when |
|---|---|---|
| `/promote-dossier` | skill | Promoting one dossier from `List/Dossiers/` into the real pipeline (`Programs/` + `Contacts/Each One/` + `Tracker/Each One/`) — Internship Pipeline Step 3. Human-in-the-loop, needs the Jarvis vault reachable (git checkout sibling to this repo, or the `jarvis` MCP tools if Obsidian's running) — see the skill's own prerequisite section. |
| `contact-researcher` | agent | Invoked by `/promote-dossier` (step 3) to find real, sourced contact signal for one company. Can also be launched standalone for a single company. Never fabricates — reports "nothing found" honestly. |
| `loop-verifier` | agent | Standalone health check of the whole pipeline — tests, scheduled-run history, vault-vs-log agreement, seen_ids divergence, auto-filed issues. Run it when you need to know if the pipeline is *actually* healthy, not just whether the code looks right. |
| `/review-loop-change` | skill | Before committing/pushing a change to `core/`, `ingestion/`, `vault_writer/`, `run_pipeline.py`, or `recheck.py` — checks the diff against the four conventions above. Not a substitute for `/code-review` (correctness/security/style) — this one's repo-specific. |

## Agent vs. more Python — the actual judgment call for each

The instinct in this codebase has consistently been "write a deterministic script" (`core/filter.py`, `core/relevance.py`, `core/classify.py` are all zero-LLM by design, and rightly so — they run unattended). That instinct stops being right exactly where a human has to look at something novel and judge it, which is genuinely different work:

- **Contact research** → agent (`contact-researcher`), not a script. Finding a real recruiter/byline/GitHub member for an arbitrary company is exploratory search with an unbounded input space and a real cost to getting it wrong (see the "wrong guess is worse than empty" rule in the agent file) — not something a fixed set of regexes can do safely. `enrich.py`'s functions are still the right *tools* for this; the agent decides *how* to use them for a given company, a script can't.
- **Promotion** (`/promote-dossier`) → skill with a human consent gate, not automation. This step already involves a judgment call the pipeline doc is explicit is not automatable (Serious vs. Considering, whether the auto-classified bucket still holds) — the point of Step 2/3 being manual by design. A skill structures the human's own workflow; it doesn't remove the human.
- **Verification** (`loop-verifier`) → agent, not a cron script, specifically because it cross-references several independently-drifting sources (test results, GitHub Actions history, live vault state, local state files) and has to *notice* when they disagree in a way that wasn't anticipated in advance — a fixed script would need to enumerate every possible mismatch up front, which is exactly the kind of audit this project has so far only done by hand (2026-07-19, 2026-07-25).
- **Review** (`/review-loop-change`) → skill, not an agent, and not more Python. The checklist is fixed and known in advance (four conventions, unlikely to grow much), and the repo's small diff size doesn't need an isolated agent context — see that skill's own "why a skill" section. A script *could* grep for some of this (e.g. flagging LLM imports in unattended-path files), but "does this new regex cite real data" needs actual reading comprehension a lint rule doesn't have.

If a new piece of recurring toil shows up and it's mechanical/deterministic (another source feed, another filter rule), it's still Python first, same as everything in `core/` and `ingestion/` today — don't reach for an agent out of habit once a human's judgment isn't actually the bottleneck.
