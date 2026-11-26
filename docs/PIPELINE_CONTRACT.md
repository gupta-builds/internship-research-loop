# Pipeline contract

One-page reference for the data shapes and CI wiring this pipeline depends
on. Every fact below is a direct citation (file+line, or an actual workflow
file's content) — no paraphrase, no guessing. For note-template contracts
(what a Program/Contact/Tracker/Applying note must contain), see the Standards
in the Jarvis vault's `30_Order/Standards/Internship/` and
`.claude/skills/promote-dossier/reference/note-templates.md`; not repeated here.

## `core/profile.yaml` schema

One line per top-level field, as it exists in the file today:

- `grad_year` — int, the candidate's graduation year (`2028`).
- `class_year` — string, current class year (`junior`).
- `eligible_class_tags` — list of strings matched as case-insensitive substrings against a posting's `target_year` entries.
- `accept_unrestricted` — bool; `true` means a posting with no class-year field at all still matches.
- `terms` — list of wanted term/cycle strings (`"Summer 2027"`, `"Winter 2027"`, `"Spring 2027"`), the Timing gate in `core/filter.py`.
- `terms_weight` — dict mapping each `terms` entry to `"high"`/`"low"`, a priority weight for `core/debate.py`, not a second pass/fail gate.
- `categories` — list of SimplifyJobs-taxonomy category strings accepted by the CS/software category gate.
- `exclude_terms` — list of term strings that reject a listing outright even alongside an allowed term.
- `locations_allow` — string, the location policy name (`us_remote`) `core/filter.py`'s `location_eligible()` implements.
- `degrees_allow` — list of degree strings (`["Bachelor's"]`); empty/missing degree data still passes (permissive-by-default).
- `preferred_companies` — dict mapping company name to tier (`"high"`), consumed by `core/debate.py`'s comparator and `core/company_registry.py`'s `TIER_RANK` — a priority weight, not a filter gate.

## `core/company_registry.py`

Added by Prompt 1 as the single source of truth for company-level
facts previously hand-duplicated across `core/classify.py`, `core/debate.py`,
and `core/relevance.py`. Data only — makes no eligibility/bucket/tier decision
itself:

- `is_quant_finance_company(company)` — true for 8 named quant-trading/quant-finance firms (Optiver, IMC, Chicago Trading Company, Jane Street, Jump Trading, Aquatic Capital Management, Walleye Capital, Millennium) whose engineering postings are finance-adjacent regardless of which keyword classify.py's regexes matched.
- `ADJACENT_FIELD_COMPANIES` — tuple of 8 lowercased company names (fti consulting, truist, vertiv, uhy, cno financial, dimensional fund, keybank, continental resources) moved verbatim from `core/relevance.py`'s old `_ADJACENT_FIELD_COMPANY_HINT_RE`, routing their postings through the real-content relevance check instead of passing unconditionally.
- `TIER_RANK` — dict mapping a `core/profile.yaml` `preferred_companies` tier name to a sort rank for `core/debate.py`'s Stage 1 comparator (`{"high": 0}` today — one grade exists).

## GitHub Actions workflows (`.github/workflows/`)

| Workflow | Trigger | Purpose | Secrets used |
|---|---|---|---|
| `run.yml` | `cron: '0 * * * *'` (hourly) + `workflow_dispatch` | Runs `run_pipeline.py` — discovery, filter, write gate, commit+push new dossiers to the Jarvis checkout. | `JARVIS_PUSH_TOKEN` (checkout+push the Jarvis vault repo), `FIRECRAWL_API_KEY` (posting-page fetch; absent degrades to thin dossiers, never fails the run). Uses `github.token` for `gh issue create`. |
| `recheck.yml` | `cron: '30 6 * * *'` (daily) + `workflow_dispatch` | Runs `recheck.py` — sweeps already-written dossiers for closed/stale postings, moves them to `Viewed/`. | `JARVIS_PUSH_TOKEN`. Uses `github.token` for `gh issue create` (mass-deletion brake / push failure). |
| `revalidate.yml` | `cron: '0 8 * * 1'` (weekly, Monday) + `workflow_dispatch` | Runs `revalidate.py` — re-checks every live dossier's own stored content against current `core/filter.py`/`core/relevance.py` rules; read-only, never moves/deletes, files one digest issue per run. | `JARVIS_PUSH_TOKEN` (checkout only — `permissions.contents: read`, no push). Uses `github.token` for `gh issue create`. |
| `test.yml` | `push`, `pull_request` | Runs `python -m pytest tests/ -v`. | None — no Jarvis checkout, no secrets. |

`run.yml`/`recheck.yml` request `permissions.contents: write` (they commit
state/logs back to this repo); `revalidate.yml` requests `contents: read`
(it never writes). All three non-test workflows request `issues: write`.

## `vault_writer/validate.py`

`REQUIRED_FRONTMATTER_FIELDS` (line 13): `company`, `title`, `url`, `source`,
`terms`, `locations`, `target_year`, `date_posted`, `date_found`,
`matched_reason`, `status`, `next`, `notes`, `preference_tier`, `tags`.

`validate()` runs five checks in cost order — `required_fields` →
`not_duplicate` → `cross_source_duplicate` → `url_liveness` →
`format_compliance`, first failure wins — see `.claude/rules/conventions.md`
for the cost reasoning; not restated here.
