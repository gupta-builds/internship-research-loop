# Graph Report - internship-research-loop  (2026-08-28)

## Corpus Check
- 71 files · ~67,455 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 877 nodes · 1838 edges · 40 communities (37 shown, 3 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 51 edges (avg confidence: 0.69)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `778f5317`
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
- [[_COMMUNITY_normalize_simplify|normalize_simplify]]
- [[_COMMUNITY_test_freehire.py|test_freehire.py]]
- [[_COMMUNITY_validate.py|validate.py]]
- [[_COMMUNITY_interndock.py|interndock.py]]
- [[_COMMUNITY__listing_with_date|_listing_with_date]]
- [[_COMMUNITY_build_frontmatter|build_frontmatter]]
- [[_COMMUNITY_test_debate_losses.py|test_debate_losses.py]]
- [[_COMMUNITY__fake_http_get|_fake_http_get]]
- [[_COMMUNITY__fake_http_get_only_interndock|_fake_http_get_only_interndock]]
- [[_COMMUNITY_dump_frontmatter|dump_frontmatter]]
- [[_COMMUNITY_650+ Summer 2027 Internships Open Now (Apply Links)|650+ Summer 2027 Internships Open Now (Apply Links)]]
- [[_COMMUNITY_posting_zipline_open_roles|posting_zipline_open_roles.md]]
- [[_COMMUNITY_vault_root|vault_root]]
- [[_COMMUNITY_stage1_reject|stage1_reject]]

## God Nodes (most connected - your core abstractions)
1. `matches()` - 47 edges
2. `normalize_simplify()` - 36 edges
3. `Listing` - 34 edges
4. `run_once()` - 34 edges
5. `render_dossier()` - 32 edges
6. `compute_uid()` - 28 edges
7. `stage2_confirm()` - 28 edges
8. `_json_response()` - 21 edges
9. `_run_once_kwargs()` - 19 edges
10. `normalize_josegael()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `listing()` --calls--> `normalize_simplify()`  [EXTRACTED]
  tests/test_validate.py → ingestion/normalize.py
- `listing()` --calls--> `normalize_simplify()`  [EXTRACTED]
  tests/test_writer.py → ingestion/normalize.py
- `test_render_dossier_frontmatter_contains_moc_link_and_company_tag()` --calls--> `render_dossier()`  [EXTRACTED]
  tests/test_writer.py → vault_writer/writer.py
- `validate_and_write()` --calls--> `classify()`  [EXTRACTED]
  run_pipeline.py → core/classify.py
- `test_classify_ai_ml_from_real_bosch_content()` --calls--> `classify()`  [EXTRACTED]
  tests/test_classify.py → core/classify.py

## Import Cycles
- None detected.

## Communities (40 total, 3 thin omitted)

### Community 0 - "build_frontmatter"
Cohesion: 0.07
Nodes (48): listing(), vault_root with no pre-existing Dossiers/ folder at all still works., Two dossiers for the same company (varying casing/whitespace) must     produce t, listing's real company is 'Palantir' (tests/fixtures/simplifyjobs.json)     — no, Real rendered frontmatter (not just the dict) — confirms preference_tier     act, Fix 2, Prompt 5 review (2026-07-30): two dossiers with the identical     filenam, Copy of the committed throwaway_vault skeleton in a scratch dir per test,     so, Same role+company but a genuinely different uid must not overwrite —     only a (+40 more)

### Community 1 - "write_dossier"
Cohesion: 0.06
Nodes (86): degrees_eligible(), location_eligible(), matches(), _matches_josegael(), Permissive like locations: no degrees data passes; non-empty data must     inclu, Listing, normalize_ai_jobs(), normalize_applyguy() (+78 more)

### Community 2 - "test_writer.py"
Cohesion: 0.11
Nodes (26): _fake_http_get_only_interndock(), _fake_interndock_sitemap_get(), The core guarantee: a deferred item is not marked seen, so it's neither     lost, The critical ordering guarantee: a validated, written dossier whose     push fai, A source going offline (DNS failure, deleted repo, 5xx) must produce a     logge, Real fixture set writes exactly 1 'Other'-bucket item per run under the     defa, 150/170 stay informational-only (logged via dossier_total, no issue);     190/20, Same 'absence means off' convention as fetch_page_fn. (+18 more)

### Community 3 - "recheck.py"
Cohesion: 0.08
Nodes (54): load_profile(), append_excluded_log(), _append_markdown_line(), append_run_log(), append_weekly_rollup(), append_write_gate_excluded_log(), format_weekly_rollup(), load_recent_runs() (+46 more)

### Community 4 - "writer.py"
Cohesion: 0.11
Nodes (18): extract_content(), The posting's substantive text: from the first real heading up to the     applic, Real fetched content, verbatim from three separate live Zipline     dossiers ('A, Real bug, confirmed 2026-07-26 on both Google dossiers sourced via     Freehire, Real bug: the Conagra Brands 'Demand Science Rotational Analyst'     fixture has, Real shape from the Appian/Conagra fixtures: a fully-bolded standalone     line, Real: the Manhattan Associates 'A.I. Developer Co-Op' fixture ends     with a 'R, A posting with no stated section names at all must not have section     boundari (+10 more)

### Community 5 - "render_dossier"
Cohesion: 0.06
Nodes (60): cross_source_key(), build_matched_reason(), Renders + validates each new listing; writes the ones that pass into     the Jar, validate_and_write(), Real American Express duplicate: the Oracle Cloud HCM job URL doesn't     embed, Real, confirmed 2026-07-29 — a genuine TRIPLE duplicate: three     different tit, Real Google BS vs MS title-string variant, same numeric job id., Real Palantir 'Intel' FDSE duplicate across two different buckets     (SimplifyJ (+52 more)

### Community 6 - "test_write_dossier_creates_missing_dossiers_dir"
Cohesion: 0.07
Nodes (46): classification_callout(), classify(), Layer 2.5b — priority-bucket classification for listings that already passed cor, Returns (bucket_name, signal) — signal is the specific real phrase     that drov, No numeric label ('Priority 1/2/3') — the folder location already     encodes th, compute_bucket_urgency(), debate_compare(), _preference_rank() (+38 more)

### Community 7 - "test_render_dossier_shows_real_rendered_frontmatter_with_preference_match"
Cohesion: 0.11
Nodes (26): extract_ats_job_id(), Layer 3 — stable dedup keys for a Listing.  Both remaining sources carry a stabl, The ATS-native job id embedded in url, or None if url is from a     source/ATS w, _load(), Real Google BS/MS Summer 2027 SWE intern duplicate: vanshb03 and     Freehire bo, Real American Express board URL shape from the 2026-08-23     excluded-log audit, Fix 1, Prompt 5 review (2026-07-30): the Google pattern used to have no     doma, Both remaining sources guarantee an id; a listing without one is a bug     (the (+18 more)

### Community 8 - "vault_root"
Cohesion: 0.11
Nodes (43): check_all(), check_applyguy_schema(), check_josegael_schema(), _check_json_source(), check_simplify_schema(), check_vanshb03_schema(), check_zshah101_schema(), Schema-drift check. Runs before the scheduled pipeline touches feeds for real: f (+35 more)

### Community 9 - "test_write_dossier_different_uid_same_role_company_gets_collision_suffix"
Cohesion: 0.06
Nodes (51): Layer 2.5 — CS/software-relevance gate. Runs after matches() passes, before the, Called only when posting_content is non-empty. True = passes (either     not adj, True if this listing's title/raw_text is unambiguously non-software —     reject, stage1_reject(), stage2_confirm(), core/relevance.py's two-stage gate — real examples throughout, no synthetic non-, Hardware is not auto-excluded — Jane Street's FPGA/ASIC internship is     a real, A hardware-adjacent title/company with content that never mentions     any real (+43 more)

### Community 10 - "test_enrich.py"
Cohesion: 0.14
Nodes (25): extract_bylines(), _fc(), fc_scrape(), fc_search(), github_org_members(), infer_email(), linkedin_recruiter_snippet(), main() (+17 more)

### Community 11 - "commit_and_push_with_retry"
Cohesion: 0.07
Nodes (43): commit_and_push_with_retry(), _git(), GitPushError, Commit-and-push with a retry-once-on-rejected-push loop.  The Jarvis vault has i, Stages everything under repo_dir, commits, and pushes. On a rejected     push (s, Exception, _commit_log(), main() (+35 more)

### Community 12 - "test_sources.py"
Cohesion: 0.09
Nodes (7): Covers the fetch->normalize wiring in ingestion/sources.py. requests.get is mock, One company's board 404ing/renaming must not halt discovery for the     other se, zshah101's data/jobs.json is a dict keyed by id, not a list — the only     sourc, ApplyGuy's real feed shape: {"updatedAt": ..., "jobs": [...]} — a bare     list, test_fetch_applyguy_calls_correct_url_and_normalizes(), test_fetch_greenhouse_skips_a_dead_company_board_without_crashing(), test_fetch_zshah101_handles_dict_shape_and_normalizes()

### Community 13 - "Internship Research Loop — PRD"
Cohesion: 0.15
Nodes (12): Architecture (Summary), Current Status (verified 2026-08-22), Explicitly Out Of Scope, Goal, In Scope — Built (Phases 1–6, complete and live), Internship Research Loop — PRD, Open Backlog, Problem (+4 more)

### Community 14 - "Software Engineering Intern (Summer 2027)"
Cohesion: 0.15
Nodes (12): **About CTGT & The Mission**, Compensation, Department, Employment Type, Location, Location Type, **Logistics**, Software Engineering Intern (Summer 2027) (+4 more)

### Community 15 - "plan_removals"
Cohesion: 0.19
Nodes (15): _content_fetch_url(), opt_exclusion(), The matched exclusion phrase, or None if the posting shows no explicit     negat, The URL to actually fetch for posting content — rewrites known     board-index-o, OPT signals and content extraction — every eligibility string below marked 'real, Real bug, confirmed live 2026-07-26: the same CTGT posting returned     4015 cha, Real listing.url shape stored on every AIJobs-sourced Zipline dossier     ('Aero, test_content_fetch_url_leaves_ashby_non_application_urls_alone() (+7 more)

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
Cohesion: 0.29
Nodes (6): Agent vs. more Python — the actual judgment call for each, Auto-mode classifier notes (this repo only), Conventions this codebase enforces — read before touching core/, ingestion/, vault_writer/, run_pipeline.py, or recheck.py, internship-research-loop — Claude Code guidance, Note-template contracts (for `/promote-dossier` and any future vault-writing code), Skills and agents available in this repo

### Community 22 - "contact-researcher.md"
Cohesion: 0.33
Nodes (5): Hard line (non-negotiable, inherited from enrich.py's own docstring), Output format, The one rule that overrides everything else, What to look for, and how to report each, What you have available

### Community 23 - "internship-research-loop"
Cohesion: 0.50
Nodes (3): internship-research-loop, Local dev, Status

### Community 24 - "job details"
Cohesion: 0.50
Nodes (3): job details, Jobs search results, Software Engineering Intern, MS, Summer 2027

### Community 26 - "normalize_simplify"
Cohesion: 0.22
Nodes (22): compute_uid(), normalize_simplify(), Pre-seed state/excluded_uids.json with a real candidate's uid already     at the, test_dedup_new_skips_excluded_uid(), test_fetch_and_filter_skips_excluded_uid(), test_run_once_never_fetches_an_already_excluded_uid(), _fake_http_head_all_live(), _page_with() (+14 more)

### Community 27 - "test_freehire.py"
Cohesion: 0.12
Nodes (29): _entry_is_us_or_remote(), _has_wrong_cycle_season(), _matches_applyguy(), _matches_free_text_source(), _matches_simplify(), _matches_vanshb03(), _matches_zshah101(), _norm() (+21 more)

### Community 28 - "validate.py"
Cohesion: 0.18
Nodes (14): _dead_link_listing(), Task (Prompt 20) — write_gate_failures.json: a uid that keeps winning its bucket, validate_and_write itself never knows about write_gate_failures.json     (that b, End-to-end via run_once: pre-seed write_gate_failures.json with the     real cit, required_fields/format_compliance (systemic, our own bug) and     not_duplicate, A URL that was dead can come back alive — a win must wipe the slate,     same se, _rejection(), test_a_different_check_restarts_the_streak_instead_of_accumulating() (+6 more)

### Community 29 - "interndock.py"
Cohesion: 0.18
Nodes (16): fetch_interndock_drop(), fetch_interndock_drop_candidates(), parse_interndock_postings(), InternDock (interndock.com) — periodic "drop" guide posts, not a JSON feed.  Che, [{title, url, company, location}, ...] from a fetched drop page's     markdown., Firecrawl-fetches one candidate URL and parses it. Returns [] both on     fetch, Real, live guide URLs from the sitemap whose slug loosely looks     drop-shaped., Real, live-verified InternDock fixtures (2026-08-24, Task 3) — no live network c (+8 more)

### Community 30 - "_listing_with_date"
Cohesion: 0.13
Nodes (15): _listing_with_date(), Task L integration: two 'Other'-bucket candidates, non-preferred one     posted, preferred_companies=None (the default) must reproduce the exact     pre-Task-L r, A bucket with 0 eligible candidates this run must not let another     bucket's i, Task A (2026-08-23): two preferred companies compete for a 1-slot     budget — s, A bucket with zero preferred candidates this run behaves exactly as     before —, Three preferred companies competing for a 1-slot budget + 1 reserved     slot —, test_prioritize_and_cap_grants_reserved_slot_to_preferred_company_losing_the_debate() (+7 more)

### Community 31 - "build_frontmatter"
Cohesion: 0.12
Nodes (10): Task 3 (Prompt 19, 2026-08-28) — per-source zero-match-rate alert.  Same "pure f, A source that has never once produced a match isn't drifting, it's     just stru, A single fetch hiccup (fetch_count == 0, e.g. a swallowed     RequestException), Pins the real, concrete incident this task was built from (Prompt 19     Task 1), Integration-level confirmation that run_once actually calls issue_fn     once th, test_run_once_does_not_alert_below_threshold(), test_run_once_files_issue_and_persists_state_on_zero_match_streak(), test_zero_match_streak_never_alerts_if_source_never_matched() (+2 more)

### Community 32 - "test_debate_losses.py"
Cohesion: 0.19
Nodes (12): _candidate(), Task N (Prompt 5) — consecutive-loss tracking and the excluded-uid list.  update, Integration-level confirmation that run_once actually wires     should_alert_on_, Loses twice (deferred), then wins (written) on the third attempt —     its loss, Real incident, 2026-08-21: 287 of 304 total excluded-log entries     (94%) were, A uid that wins without ever having lost before (the common case)     must not e, test_deferred_nth_time_excludes_and_removes_from_losses(), test_deferred_up_to_threshold_minus_one_still_in_pool_not_excluded() (+4 more)

### Community 33 - "_fake_http_get"
Cohesion: 0.39
Nodes (8): _applyguy_raw(), _fake_http_get(), _josegael_raw(), _strip_case_keys(), test_dedup_new_splits_new_vs_already_seen(), test_fetch_and_filter_counts_and_matches(), _vanshb03_raw(), _zshah101_raw()

### Community 34 - "_fake_http_get_only_interndock"
Cohesion: 0.23
Nodes (13): plan_removals(), [{uid, path, reason}] for dossiers whose posting closed. A source that     faile, _fm(), plan_removals is the recheck's whole decision surface — pure, tested offline., A source missing from feeds_by_source means its fetch failed — its     dossiers, A dossier written before dossier_uids.json existed (or hand-edited into     the, Real, reproducible bug found 2026-08-23: scan_dossiers() globs Viewed/     along, test_absent_from_feed_is_removed() (+5 more)

### Community 35 - "dump_frontmatter"
Cohesion: 0.33
Nodes (6): phd_only_exclusion(), The matched PhD-exclusivity phrase, or None if the posting shows no     explicit, Real Optiver 'Quantitative Research Intern, PhD (Summer 2027)'     (Greenhouse j, test_phd_only_exclusion_does_not_reject_bachelors_masters_eligible_real_text(), test_phd_only_exclusion_rejects_explicit_equivalent_phrasing(), test_phd_only_exclusion_rejects_real_optiver_text()

### Community 38 - "vault_root"
Cohesion: 0.40
Nodes (4): _dedupe_paragraphs(), Discovery-time posting-page fetch: one Firecrawl call per NEW match serves both, Drops a paragraph line that repeats verbatim later in the same fetch,     keepin, _strip_trailing_social_chrome()

### Community 39 - "stage1_reject"
Cohesion: 0.50
Nodes (4): fetch_posting_markdown(), Page markdown via Firecrawl (JS-rendered — ATS pages are SPAs).     Raises reque, test_fetch_posting_markdown_calls_firecrawl(), test_fetch_posting_markdown_strips_ashby_application_suffix_before_calling_firecrawl()

## Knowledge Gaps
- **64 isolated node(s):** `The one rule that overrides everything else`, `What you have available`, `Hard line (non-negotiable, inherited from enrich.py's own docstring)`, `What to look for, and how to report each`, `Output format` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `normalize_simplify()` connect `normalize_simplify` to `test_debate_losses.py`, `write_dossier`, `test_writer.py`, `build_frontmatter`, `render_dossier`, `test_render_dossier_shows_real_rendered_frontmatter_with_preference_match`, `test_write_dossier_different_uid_same_role_company_gets_collision_suffix`, `_listing_with_date`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `matches()` connect `write_dossier` to `recheck.py`, `test_freehire.py`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `stage2_confirm()` connect `test_write_dossier_different_uid_same_role_company_gets_collision_suffix` to `recheck.py`, `commit_and_push_with_retry`, `render_dossier`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `Layer 2.5b — priority-bucket classification for listings that already passed cor`, `Returns (bucket_name, signal) — signal is the specific real phrase     that drov`, `No numeric label ('Priority 1/2/3') — the folder location already     encodes th` to the rest of the system?**
  _267 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `build_frontmatter` be split into smaller, more focused modules?**
  _Cohesion score 0.06821480406386067 - nodes in this community are weakly interconnected._
- **Should `write_dossier` be split into smaller, more focused modules?**
  _Cohesion score 0.05616605616605617 - nodes in this community are weakly interconnected._
- **Should `test_writer.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1053763440860215 - nodes in this community are weakly interconnected._