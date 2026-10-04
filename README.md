# internship-research-loop

Hourly, zero-LLM internship discovery. Polls 11 public sources, filters against a
profile (`core/profile.yaml`), dedups (per-source uid + cross-source ATS-job-id /
company+title key), runs a five-check write gate, and writes content-carrying
dossier notes into an Obsidian vault (the separate `gupta-builds/Jarvis` repo).
Discovery is the only automated half — promotion, outreach, tailoring and
applying stay manual by design (see `CLAUDE.md` for the conventions and the
skills/agents that help with those steps; see `PRD.md` for scope and status).

## Sources

Ten fetched hourly through `run_pipeline.py`'s `SOURCES`: SimplifyJobs,
Jose-Gael-Cruz-Lopez, vanshb03, zshah101, ApplyGuy, Greenhouse, Ashby, Lever,
Freehire, AIJobs. An eleventh, InternDock, is sitemap-detected (a new drop is
fetched once, via Firecrawl, then remembered in `state/interndock_seen_guides.json`).

## What a run does

fetch → schema-drift check → filter (term, category, class year, `active`,
`degrees`, US location, CS relevance) → dedup → pick this run's writes (exact
per-bucket quota, `QUOTA_PER_RUN`, all-or-nothing) → write gate (required fields,
uid dedup, cross-source dedup, URL liveness, format) → Firecrawl the posting
(fail-open to a thin dossier) → OPT / PhD-only / relevance content checks →
write the dossier into its priority folder (`1 - AI & ML`, `2 - Fullstack`,
`3 - CyS & Finance`, `Other`) → push to the vault → mark seen only after the push.

Every dossier carries `deadline_posted` (the posting's own stated deadline, when
one can be read from the fetched text) or, failing that, `own_deadline` =
`date_found` + 7 days — exactly one of the two, enforced by the write gate.

At 300 live dossiers (excluding `Viewed/`) the run disables itself
(`HARD_PAUSE_TOTAL_THRESHOLD`). Re-enabling is a human decision:
`gh workflow enable run`.

## Workflows (`.github/workflows/`)

| Workflow | Trigger | Does |
|---|---|---|
| `run.yml` | hourly cron + manual | the pipeline above; opens a `dossier-ready` issue when it wrote anything |
| `recheck.yml` | daily 06:30 UTC + manual | moves dossiers whose posting closed to `Dossiers/Viewed/` (never deletes) |
| `revalidate.yml` | weekly Monday 08:00 UTC + manual | re-checks live dossiers against current rules, files one digest issue; moves nothing |
| `reseed.yml` | manual only (confirm string) | one large cold-start pull for an empty or relaunched vault |
| `test.yml` | push / PR | `pytest` |

Secrets: `FIRECRAWL_API_KEY`, `JARVIS_PUSH_TOKEN` (fine-grained PAT for the vault repo).

## Manual tools

- `enrich.py` — company / contact research for a promoted dossier (Firecrawl + public sources).
- `grade_resume.py` — keyword-overlap ranking of `Main Resume.md` bullets against a pasted JD.
  Reads `$JARVIS_DIR/20_Progress/Internship/Resumes/Main Resume.md` unless `--resume PATH` is given.
- `screen_report.py` — read-only "ready to screen" list per bucket (`JARVIS_DIR=... python screen_report.py`).
- `revalidate.py`, `recheck.py`, `reseed.py` — the scripts behind the workflows; each takes `JARVIS_DIR`.

## Local dev

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -v
```

One-time per clone: `cp scripts/hooks/pre-push .git/hooks/pre-push` — this repo has no PR gate, so this local hook is what blocks a `git push` with a failing suite.

For either laptop, run `scripts/setup-two-laptop-git.sh` once instead of installing the hook by hand. Then follow [the two-laptop workflow](docs/TWO_LAPTOP_WORKFLOW.md): update `master` with a fast-forward-only pull, create a task-named branch, and merge through a PR. Never work on the same branch from both laptops at once.
