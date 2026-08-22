# Graph Report - internship-research-loop  (2026-08-21)

## Corpus Check
- 57 files · ~52,429 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 697 nodes · 1491 edges · 26 communities (25 shown, 1 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 38 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f5b39375`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_build_frontmatter|build_frontmatter]]
- [[_COMMUNITY_write_dossier|write_dossier]]
- [[_COMMUNITY_test_writer.py|test_writer.py]]
- [[_COMMUNITY_recheck.py|recheck.py]]
- [[_COMMUNITY_writer.py|writer.py]]
- [[_COMMUNITY_render_dossier|render_dossier]]
- [[_COMMUNITY_test_write_dossier_creates_missing_dossiers_dir|test_write_dossier_creates_missing_dossiers_dir]]
- [[_COMMUNITY_test_render_dossier_shows_real_rendered_frontmatter_with_preference_match|test_render_dossier_shows_real_rendered_frontmatter_with_preference_match]]
- [[_COMMUNITY_vault_root|vault_root]]
- [[_COMMUNITY_test_write_dossier_different_uid_same_role_company_gets_collision_suffix|test_write_dossier_different_uid_same_role_company_gets_collision_suffix]]
- [[_COMMUNITY_test_enrich.py|test_enrich.py]]
- [[_COMMUNITY_commit_and_push_with_retry|commit_and_push_with_retry]]
- [[_COMMUNITY_test_sources.py|test_sources.py]]
- [[_COMMUNITY_Internship Research Loop — PRD|Internship Research Loop — PRD]]
- [[_COMMUNITY_Software Engineering Intern (Summer 2027)|Software Engineering Intern (Summer 2027)]]
- [[_COMMUNITY_plan_removals|plan_removals]]
- [[_COMMUNITY_grade|grade]]
- [[_COMMUNITY_promote-dossier|/promote-dossier]]
- [[_COMMUNITY_What to check|What to check]]
- [[_COMMUNITY_Checks to run, in this order|Checks to run, in this order]]
- [[_COMMUNITY_promote-dossier note templates|promote-dossier note templates]]
- [[_COMMUNITY_internship-research-loop — Claude Code guidance|internship-research-loop — Claude Code guidance]]
- [[_COMMUNITY_contact-researcher|contact-researcher.md]]
- [[_COMMUNITY_internship-research-loop|internship-research-loop]]
- [[_COMMUNITY_job details|job details]]
- [[_COMMUNITY_Summer Intern 2027 - Software Developer|Summer Intern 2027 - Software Developer]]

## God Nodes (most connected - your core abstractions)
1. `matches()` - 40 edges
2. `normalize_simplify()` - 36 edges
3. `render_dossier()` - 32 edges
4. `compute_uid()` - 25 edges
5. `run_once()` - 25 edges
6. `Listing` - 24 edges
7. `normalize_josegael()` - 18 edges
8. `_simplify_raw()` - 18 edges
9. `check_format_compliance()` - 18 edges
10. `write_dossier()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `listing()` --calls--> `normalize_simplify()`  [EXTRACTED]
  tests/test_validate.py → ingestion/normalize.py
- `listing()` --calls--> `normalize_simplify()`  [EXTRACTED]
  tests/test_writer.py → ingestion/normalize.py
- `test_render_dossier_frontmatter_contains_moc_link_and_company_tag()` --calls--> `render_dossier()`  [EXTRACTED]
  tests/test_writer.py → vault_writer/writer.py
- `_prioritize_and_cap()` --calls--> `classify()`  [EXTRACTED]
  run_pipeline.py → core/classify.py
- `validate_and_write()` --calls--> `classify()`  [EXTRACTED]
  run_pipeline.py → core/classify.py

## Import Cycles
- None detected.

## Communities (26 total, 1 thin omitted)

### Community 0 - "build_frontmatter"
Cohesion: 0.07
Nodes (48): listing(), vault_root with no pre-existing Dossiers/ folder at all still works., Two dossiers for the same company (varying casing/whitespace) must     produce t, listing's real company is 'Palantir' (tests/fixtures/simplifyjobs.json)     — no, Real rendered frontmatter (not just the dict) — confirms preference_tier     act, Fix 2, Prompt 5 review (2026-07-30): two dossiers with the identical     filenam, Copy of the committed throwaway_vault skeleton in a scratch dir per test,     so, Same role+company but a genuinely different uid must not overwrite —     only a (+40 more)

### Community 1 - "write_dossier"
Cohesion: 0.05
Nodes (88): degrees_eligible(), _entry_is_us_or_remote(), _has_wrong_cycle_season(), location_eligible(), matches(), _matches_free_text_source(), _matches_josegael(), _matches_simplify() (+80 more)

### Community 2 - "test_writer.py"
Cohesion: 0.06
Nodes (69): compute_uid(), normalize_simplify(), _candidate(), Task N (Prompt 5) — consecutive-loss tracking and the excluded-uid list.  update, Pre-seed state/excluded_uids.json with a real candidate's uid already     at the, Loses twice (deferred), then wins (written) on the third attempt —     its loss, A uid that wins without ever having lost before (the common case)     must not e, test_dedup_new_skips_excluded_uid() (+61 more)

### Community 3 - "recheck.py"
Cohesion: 0.08
Nodes (58): load_profile(), append_excluded_log(), _append_markdown_line(), append_run_log(), append_weekly_rollup(), format_weekly_rollup(), load_recent_runs(), datetime (+50 more)

### Community 4 - "writer.py"
Cohesion: 0.08
Nodes (41): _content_fetch_url(), _dedupe_paragraphs(), extract_content(), fetch_posting_markdown(), opt_exclusion(), phd_only_exclusion(), Discovery-time posting-page fetch: one Firecrawl call per NEW match serves both, The matched PhD-exclusivity phrase, or None if the posting shows no     explicit (+33 more)

### Community 5 - "render_dossier"
Cohesion: 0.10
Nodes (44): build_matched_reason(), Renders + validates each new listing; writes the ones that pass into     the Jar, validate_and_write(), listing(), _ok_response(), The mid-body loop explicitly allows a blank line after a callout — but not     w, required_fields runs before url_liveness — a missing field should reject     wit, Confirms REQUIRED_FRONTMATTER_FIELDS actually enforces notes: — adding     it to (+36 more)

### Community 6 - "test_write_dossier_creates_missing_dossiers_dir"
Cohesion: 0.09
Nodes (36): classification_callout(), classify(), Layer 2.5b — priority-bucket classification for listings that already passed cor, Returns (bucket_name, signal) — signal is the specific real phrase     that drov, No numeric label ('Priority 1/2/3') — the folder location already     encodes th, compute_bucket_urgency(), debate_compare(), _preference_rank() (+28 more)

### Community 7 - "test_render_dossier_shows_real_rendered_frontmatter_with_preference_match"
Cohesion: 0.08
Nodes (35): company_matches_preference(), cross_source_key(), extract_ats_job_id(), _norm_company(), Layer 3 — stable dedup keys for a Listing.  Both remaining sources carry a stabl, The ATS-native job id embedded in url, or None if url is from a     source/ATS w, The matched preference tier (e.g. 'high'), or None if company isn't in     prefe, Fix 1, Prompt 5 review (2026-07-30): the Google pattern used to have no     doma (+27 more)

### Community 8 - "vault_root"
Cohesion: 0.13
Nodes (34): check_all(), check_josegael_schema(), _check_json_source(), check_simplify_schema(), check_vanshb03_schema(), check_zshah101_schema(), Schema-drift check. Runs before the scheduled pipeline touches feeds for real: f, Runs every check in order; raises SchemaDriftError from whichever     fails firs (+26 more)

### Community 9 - "test_write_dossier_different_uid_same_role_company_gets_collision_suffix"
Cohesion: 0.09
Nodes (32): Layer 2.5 — CS/software-relevance gate. Runs after matches() passes, before the, Called only when posting_content is non-empty. True = passes (either     not adj, True if this listing's title/raw_text is unambiguously non-software —     reject, stage1_reject(), stage2_confirm(), core/relevance.py's two-stage gate — real examples throughout, no synthetic non-, Hardware is not auto-excluded — Jane Street's FPGA/ASIC internship is     a real, A hardware-adjacent title/company with content that never mentions     any real (+24 more)

### Community 10 - "test_enrich.py"
Cohesion: 0.14
Nodes (25): extract_bylines(), _fc(), fc_scrape(), fc_search(), github_org_members(), infer_email(), linkedin_recruiter_snippet(), main() (+17 more)

### Community 11 - "commit_and_push_with_retry"
Cohesion: 0.19
Nodes (18): commit_and_push_with_retry(), _git(), GitPushError, Commit-and-push with a retry-once-on-rejected-push loop.  The Jarvis vault has i, Stages everything under repo_dir, commits, and pushes. On a rejected     push (s, Exception, _configure_identity(), _log_messages() (+10 more)

### Community 12 - "test_sources.py"
Cohesion: 0.11
Nodes (5): Covers the fetch->normalize wiring in ingestion/sources.py. requests.get is mock, One company's board 404ing/renaming must not halt discovery for the     other se, zshah101's data/jobs.json is a dict keyed by id, not a list — the only     sourc, test_fetch_greenhouse_skips_a_dead_company_board_without_crashing(), test_fetch_zshah101_handles_dict_shape_and_normalizes()

### Community 13 - "Internship Research Loop — PRD"
Cohesion: 0.15
Nodes (12): Architecture (Summary), Current Status (verified 2026-07-18), Explicitly Out Of Scope, Goal, In Scope — Built (Phases 1–6, complete and live), Internship Research Loop — PRD, Open Backlog, Problem (+4 more)

### Community 14 - "Software Engineering Intern (Summer 2027)"
Cohesion: 0.15
Nodes (12): **About CTGT & The Mission**, Compensation, Department, Employment Type, Location, Location Type, **Logistics**, Software Engineering Intern (Summer 2027) (+4 more)

### Community 15 - "plan_removals"
Cohesion: 0.26
Nodes (11): plan_removals(), [{uid, path, reason}] for dossiers whose posting closed. A source that     faile, _fm(), plan_removals is the recheck's whole decision surface — pure, tested offline., A source missing from feeds_by_source means its fetch failed — its     dossiers, A dossier written before dossier_uids.json existed (or hand-edited into     the, test_absent_from_feed_is_removed(), test_active_false_upstream_is_removed() (+3 more)

### Community 16 - "grade"
Cohesion: 0.35
Nodes (9): grade(), keywords(), main(), parse_bullets(), (text, tags) for every '- ' line carrying at least one #skill tag., Bullets ranked by distinct-JD-keyword overlap: (score, text, tags, matched)., test_grade_ranks_matching_bullet_first(), test_keywords_drops_stopwords_keeps_tech_tokens() (+1 more)

### Community 17 - "/promote-dossier"
Cohesion: 0.20
Nodes (9): 1. Take the input, 2. Ask two concrete questions, 3. Invoke contact research and show findings — before writing anything, 4. On explicit go-ahead only, write all three notes together, Note templates, Prerequisite — read this before running, /promote-dossier, Steps (+1 more)

### Community 18 - "What to check"
Cohesion: 0.22
Nodes (8): 1. Zero-LLM in the unattended path, 2. Permissive-by-default / explicit-negative-signal design, 3. Fail-closed write-gate ordering, 4. Every new rule cites the real live data it was built from, Output format, /review-loop-change, What to check, Why a skill, not an agent, for this repo

### Community 19 - "Checks to run, in this order"
Cohesion: 0.25
Nodes (7): 1. Full test suite, 2. Scheduled workflow history (last N runs each), 3. Vault dossier counts vs. what run logs claim was written, 4. seen_ids.json / vault divergence, 5. Auto-filed GitHub issues, Checks to run, in this order, Output format

### Community 20 - "promote-dossier note templates"
Cohesion: 0.29
Nodes (6): 1. Program note, 2. Contact note, 3. Tracker/Each One note, Backfill structured fields from the same content the body prose is drawn from — don't default to null, Cross-linking summary (all three notes, written together, in one sitting), promote-dossier note templates

### Community 21 - "internship-research-loop — Claude Code guidance"
Cohesion: 0.33
Nodes (5): Agent vs. more Python — the actual judgment call for each, Conventions this codebase enforces — read before touching core/, ingestion/, vault_writer/, run_pipeline.py, or recheck.py, internship-research-loop — Claude Code guidance, Note-template contracts (for `/promote-dossier` and any future vault-writing code), Skills and agents available in this repo

### Community 22 - "contact-researcher.md"
Cohesion: 0.33
Nodes (5): Hard line (non-negotiable, inherited from enrich.py's own docstring), Output format, The one rule that overrides everything else, What to look for, and how to report each, What you have available

### Community 23 - "internship-research-loop"
Cohesion: 0.50
Nodes (3): internship-research-loop, Local dev, Status

### Community 24 - "job details"
Cohesion: 0.50
Nodes (3): job details, Jobs search results, Software Engineering Intern, MS, Summer 2027

## Knowledge Gaps
- **60 isolated node(s):** `The one rule that overrides everything else`, `What you have available`, `Hard line (non-negotiable, inherited from enrich.py's own docstring)`, `What to look for, and how to report each`, `Output format` (+55 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `normalize_simplify()` connect `test_writer.py` to `build_frontmatter`, `write_dossier`, `recheck.py`, `render_dossier`, `test_render_dossier_shows_real_rendered_frontmatter_with_preference_match`, `test_write_dossier_different_uid_same_role_company_gets_collision_suffix`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Why does `matches()` connect `write_dossier` to `recheck.py`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `extract_content()` connect `writer.py` to `recheck.py`, `render_dossier`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **What connects `Layer 2.5b — priority-bucket classification for listings that already passed cor`, `Returns (bucket_name, signal) — signal is the specific real phrase     that drov`, `No numeric label ('Priority 1/2/3') — the folder location already     encodes th` to the rest of the system?**
  _208 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `build_frontmatter` be split into smaller, more focused modules?**
  _Cohesion score 0.06821480406386067 - nodes in this community are weakly interconnected._
- **Should `write_dossier` be split into smaller, more focused modules?**
  _Cohesion score 0.05218365061590145 - nodes in this community are weakly interconnected._
- **Should `test_writer.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06293965198074787 - nodes in this community are weakly interconnected._