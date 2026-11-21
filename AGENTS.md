# internship-research-loop — Codex guidance

This repo is small (~1,500 lines) with a ~1:1 test-to-code ratio (`tests/` mirrors `core/`, `ingestion/`, `vault_writer/` file-for-file). See `README.md` for what it does and `PRD.md` for the full spec/status. This file is about how a Codex session should work in it.

## Conventions this codebase enforces — read before touching core/, ingestion/, vault_writer/, run_pipeline.py, or recheck.py

These are load-bearing design decisions, not style preferences. `/review-loop-change` checks a diff against all four before it ships — but know them regardless of whether you run that skill.

1. **Zero-LLM in the unattended path.** `run_pipeline.py`, `recheck.py`, `core/filter.py`, `core/relevance.py`, `core/classify.py`, everything under `ingestion/`, and `vault_writer/` run hourly/daily via GitHub Actions with no human in the loop, and must never call an LLM, however elaborate the logic gets (see `core/relevance.py`'s two-stage design for "elaborate but still zero-LLM"). `enrich.py` is the one manual-CLI exception — a human runs it on demand — and even it stays zero-LLM by its own docstring's rule.
2. **Permissive-by-default / explicit-negative-signal filtering.** Every eligibility gate in `core/filter.py` (`location_eligible`, `degrees_eligible`, the term/season matchers) lets ambiguous or missing data pass; only an affirmative negative signal (a denylist token, an explicit exclusion string) rejects. A false negative here silently kills a real, eligible posting before a human ever sees it — worse than a false positive, which a human screens out at Step 2 of the pipeline anyway.
3. **Fail-closed write-gate ordering.** `vault_writer/validate.py`'s `validate()` runs five checks in a specific cost order — `required_fields` → `not_duplicate` → `cross_source_duplicate` → `url_liveness` → `format_compliance` — free checks before ones that cost a network call, first failure wins. Don't reorder without restating the cost reasoning.
4. **Every new rule cites the real live data it was built from, in a comment.** A new regex, keyword, denylist entry, or threshold names the actual company/posting/fixture it was checked against and the date, right next to the code (see `core/filter.py`'s `_NON_US` denylist or `core/relevance.py`'s stage1/stage2 patterns for the expected shape). "Seems right" is not a citation.

## Note-template contracts (for `/promote-dossier`, `promotion`, and any future vault-writing code)

When writing Program, Contact, or Tracker/Each One notes into the Jarvis vault, every field below is **required and must always be present**, even as `null`/`[]` — same fail-closed-on-missing-fields discipline as `vault_writer/validate.py`'s `REQUIRED_FRONTMATTER_FIELDS` for dossiers. Full field-by-field templates with body structure live in `.codex/skills/promote-dossier/reference/note-templates.md`; this is the contract summary.

**Program note** (`Programs/Serious/` or `Programs/Considering/`) — repository contract; compare it with the live `30_Order/Templates/Career/Internship/Program Template.md` before writing because the two currently drift:
`name, company, program_type, eligible_classes, grad_year, role_type, wave, opens_date, deadline_posted, deadline_real, pay_per_week, pay_currency, duration_weeks, benefits, application_url, careers_page, list_origin, applying_note, recruiter_contact, tags`. No `status`/`next` field — Program notes are durable/static, they change only when a fact about the program itself changes.

**Contact note** (`Contacts/Each One/`) — repository contract; compare it with the live `30_Order/Templates/Career/Internship/Contact Template.md` before writing because the live template currently omits `related_programs`:
`type: contact, name, role, company, linkedin_url, email, how_found, relationship, related_programs, last_contact_date, tags, next`.

**Tracker/Each One note** (`Tracker/Each One/`) — matches the vault's `30_Order/Standards/Internship/Internship Tracker Standard.md` and `Tracking Template.md`:
`type: tracker, program, contact, company, url, date_noted, date_researched, date_created, date_applied, date_result, result, deadline, related_notes, tags, next`.

**Applying note** (`20_Progress/Internship/Applying/`, created by the `applying` agent's caller, not written by this repo's own automation) — matches the vault's `30_Order/Standards/Internship/Applying Standard.md` and `Applying Template.md`:
`type: project, status, program, tracker, company, job_url, date_applied, date_response, next_deadline, resume_version, cover_letter, contacts, interview_note, related_progress, tags, next`.

Cross-links: Program `list_origin` → dossier, Program `recruiter_contact` ↔ Contact `related_programs`, Tracker `program`/`contact`/`related_notes` → the other three notes, Applying `program`/`tracker`/`contacts` → their respective notes. Don't invent new cross-link fields (e.g. a `tracker_note` field on Program) — propose a vault-template change explicitly if one's ever needed instead of adding it silently from a skill or agent.

## Skills and agents available in this repo

| Name | Kind | Use when |
|---|---|---|
| `/promote-dossier` | skill | Promoting one dossier from `List/Dossiers/` into the real pipeline (`Programs/` + `Contacts/Each One/` + `Tracker/Each One/`) — Internship Pipeline Step 3. Human-in-the-loop, needs the Jarvis vault reachable — see the skill's own prerequisite section. |
| `/promote-manual-find` | skill | The same Step 3 commit, for a lead found by hand (career fair, referral, LinkedIn) with no dossier. Thin wrapper over the `promotion` agent — added 2026-09-04 to close a real gap: 3 of the 4 real promotions to date (Uber, Western Digital, Deepgram) never got a paired Contact/Tracker note because no skill existed for this path before now. |
| `/tailoring-application` | skill | Drafting the resume/cover-letter content plan for a real application, once `Main Resume.md`/`Main Cover Letter.md` are real (they aren't yet — the skill checks this first and stops if not). Thin wrapper over the `applying` agent. |
| `/review-loop-change` | skill | Before committing/pushing a change to `core/`, `ingestion/`, `vault_writer/`, `run_pipeline.py`, or `recheck.py` — checks the diff against the four conventions above. Not a substitute for `/code-review` (correctness/security/style) — this one's repo-specific. |
| `contact-researcher` | agent | Invoked by `/promote-dossier` and `promotion` to find real, sourced contact signal for one company. Can also be launched standalone. Never fabricates — reports "nothing found" honestly. |
| `program-writer` | agent | Writes or updates exactly one Program note, from a dossier or a manual lead. Invoked by `promotion` and by `/promote-dossier`'s own logic — never write a Program note's frontmatter free-hand, the backfill/Prep-Checklist rules are easy to skip otherwise. |
| `tracking` | agent | Writes a new Tracker/Each One note at promotion time, or updates an existing one at one of its four real maintenance touch-points (deadline change, Tailor start, submission, outcome) — per the vault's `Internship Tracking Workflow`. |
| `promotion` | agent | Orchestrates the manual-lead path: consent gate, `contact-researcher`, `program-writer`, and `tracking`, in order. Invoked by `/promote-manual-find`. |
| `applying` | agent | The `draft`/`plan` half of the Tailor sequence (Application Document Preparation). Currently blocked on `Main Resume.md`/`Main Cover Letter.md` not being real — the agent itself checks this and refuses to draft against filler content. |
| `testing-tools` | agent | Runs and interprets `pytest`, checks new tests/fixtures cite real data, and drafts a new source's test following the existing (unparametrized, as of this writing) `test_schema_drift.py` pattern rather than inventing a new shape. |
| `loop-verifier` | agent | Standalone health check of the whole pipeline — tests, scheduled-run history, vault-vs-log agreement, seen_ids divergence, auto-filed issues. Run it when you need to know if the pipeline is *actually* healthy, not just whether the code looks right. |

## Agent vs. more Python — the actual judgment call for each

The instinct in this codebase has consistently been "write a deterministic script" (`core/filter.py`, `core/relevance.py`, `core/classify.py` are all zero-LLM by design, and rightly so — they run unattended). That instinct stops being right exactly where a human has to look at something novel and judge it, which is genuinely different work:

- **Contact research** → agent (`contact-researcher`), not a script. Finding a real recruiter/byline/GitHub member for an arbitrary company is exploratory search with an unbounded input space and a real cost to getting it wrong (see the "wrong guess is worse than empty" rule in the agent file) — not something a fixed set of regexes can do safely. `enrich.py`'s functions are still the right *tools* for this; the agent decides *how* to use them for a given company, a script can't.
- **Promotion** (`/promote-dossier`, `/promote-manual-find`) → skills with a human consent gate, not automation. This step already involves a judgment call the pipeline doc is explicit is not automatable (Serious vs. Considering, whether the auto-classified bucket still holds, or — for a manual lead — the bucket itself) — the point of Step 2/3 being manual by design. A skill structures the human's own workflow; it doesn't remove the human.
- **Program-writing and Tracker-writing** (`program-writer`, `tracking`) → agents, not scripts, for a reason that has nothing to do with judgment: both need live tool access to a *different* repository (the Jarvis vault), reachable only via a sibling git checkout or the `jarvis` MCP tools — neither is available to a headless script running under GitHub Actions CI. `tracking`'s own internal logic is deliberately low-freedom (mostly copying already-known fields, per its own file) — it's an agent because of *where* it has to run, not because the task itself needs much judgment. `program-writer` genuinely does need judgment (the Backfill rule, grounding Prep Checklist items in real posting content), so it earns the agent shape on both counts.
- **The manual-lead orchestrator** (`promotion`) → agent, invoked by a skill rather than being a skill itself, because it's reused by exactly one entry point today (`/promote-manual-find`) but is written to be callable the same way if `/promote-dossier` is ever refactored to share it — an orchestrator that sequences three other agents behind one consent gate is exactly the kind of side task that would flood a skill's own inline prose if written there directly.
- **Application tailoring** (`applying`) → agent, same reasoning as contact research: JD-to-evidence matching is exploratory judgment with a real cost to getting it wrong (an invented claim on a real application), not a fixed script's job.
- **Verification** (`loop-verifier`) → agent, not a cron script, specifically because it cross-references several independently-drifting sources (test results, GitHub Actions history, live vault state, local state files) and has to *notice* when they disagree in a way that wasn't anticipated in advance — a fixed script would need to enumerate every possible mismatch up front, which is exactly the kind of audit this project has so far only done by hand (2026-07-19, 2026-07-25).
- **Testing** (`testing-tools`) → agent, narrowly. Running `pytest` itself is mechanical, but interpreting *why* a failure happened (a logic bug vs. a convention violation) and judging whether a new fixture is genuinely real data both need reading comprehension a lint rule doesn't have — same reasoning `/review-loop-change` already established for reviewing production code, applied here to tests specifically.
- **Review** (`/review-loop-change`) → skill, not an agent, and not more Python. The checklist is fixed and known in advance (four conventions, unlikely to grow much), and the repo's small diff size doesn't need an isolated agent context — see that skill's own "why a skill" section. A script *could* grep for some of this (e.g. flagging LLM imports in unattended-path files), but "does this new regex cite real data" needs actual reading comprehension a lint rule doesn't have.

If a new piece of recurring toil shows up and it's mechanical/deterministic (another source feed, another filter rule), it's still Python first, same as everything in `core/` and `ingestion/` today — don't reach for an agent out of habit once a human's judgment isn't actually the bottleneck.

## Codex-local durable context

Codex loads this `AGENTS.md` and discovers skills from `.codex/skills/`. Do not assume Claude's `.claude/rules/` or `.claude/settings*.json` are Codex policy, and do not create a parallel `.Codex/` tree (case matters on Linux).

Three concise, repository-specific references live under `docs/codex/`:
- **`ARCHITECTURE.md`** — authored-code map, runtime data flow, state ownership, and high-risk boundaries.
- **`ACCESS.md`** — verified tool/repository/vault access versus exposed-but-unverified operations.
- **`BUILD_PLAYBOOK.md`** — the mandatory read/implement/verify sequence for future heavy builds.

These files summarize orientation; they do not override this file, live code, tests, or the Jarvis standards/templates. If a summary conflicts with live evidence, re-verify and update the summary in the same change.

## Auto-mode classifier notes (this repo only)

These notes used to live in global Codex configuration, where they didn't belong; they were pulled back here since they only make sense for this repo:

- **Repository visibility**: PUBLIC — gupta-builds/internship-research-loop (github.com) — any push here is publishing; confidential material must not be committed.
- **Secrets management**: CI secrets `FIRECRAWL_API_KEY` and `JARVIS_PUSH_TOKEN` referenced by name only in CI config — no values known here, never print/echo them.
- **Default / protected branches**: default branch is `master`; it remains unprotected because scheduled workflows commit owned state/log files directly. Human work never pushes directly to `master`. Follow `docs/TWO_LAPTOP_WORKFLOW.md`; use task-based branch names, not laptop names.
- **CI/CD deploy targets**: GitHub Actions (`.github/workflows`) — `run.yml` (hourly), `recheck.yml` (daily), `test.yml` — writes to the gupta-builds/Jarvis vault repo via a scoped PAT (`JARVIS_PUSH_TOKEN`).
- **Source control**: this repo (gupta-builds/internship-research-loop, public) and its origin remote only.
- **Key internal services**: `freehire.me` and `boards-api.greenhouse.io` (hosts contacted by this project's ingestion) — job-posting data sources, not credentialed internal infra.
- **Sensitive data locations & audiences**: the Jarvis Obsidian vault (gupta-builds/Jarvis, reached via sibling git checkout or `jarvis` MCP tools) holds personal career/job-search data (contacts, applications, personal notes) — share only with the user; `contact-researcher` findings must be sourced, never fabricated.
- **Soft-deny for this repo**: auto-filed issues from `run_pipeline.py`/`recheck.py` failure paths (`gh issue create` here) should be reviewed, not silently created by an agent session; Write/Edit under a sibling Jarvis vault checkout outside the two-consent-gated flows documented above (`/promote-dossier`, `/promote-manual-find`) needs the same human-in-the-loop gate.
