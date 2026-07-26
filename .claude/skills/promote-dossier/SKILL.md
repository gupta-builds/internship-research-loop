---
name: promote-dossier
description: "Turns one internship-research-loop dossier into a Program note + Contacts/Each One note + Tracker/Each One note in the Jarvis vault, with manual consent required before any write. Use when the user wants to promote/commit a dossier from List/Dossiers into the real pipeline (Internship Pipeline.md Step 3)."
trigger: /promote-dossier
---

# /promote-dossier

Promotes one dossier from `List/Dossiers/` (auto-written by this repo's discovery loop) into `Programs/`, `Contacts/Each One/`, and `Tracker/Each One/` — Step 3 ("Commit") of the Jarvis vault's `30_Order/Workflows/Internship Pipeline.md`. This is a human-in-the-loop step: it never writes anything without an explicit go-ahead, and it never invents a fact it can't source.

## Prerequisite — read this before running

**This skill needs a session with both this repo and the Jarvis vault (`gupta-builds/Jarvis`) present in the same working environment.** This repo's own automation (`run_pipeline.py`, `recheck.py`) never touches the vault interactively — it writes once, non-interactively, via a scoped PAT in CI. This skill is the opposite shape: a human reviewing real findings before a write happens, which means it needs to actually read and write vault files directly, not through a second automated writer.

Two ways that access can exist, and this skill works with either — but do not assume either one silently, check first:

1. **Git checkout, sibling to this repo** — the layout this repo's own code already expects (`run_pipeline.py`'s `JARVIS_DIR` env var, same pattern as `jarvis-checkout/` in CI). Expected layout:
   ```
   internship-research-loop/     <- this repo
   Jarvis/                       <- gupta-builds/Jarvis, checked out alongside it
   ```
   If this is how the vault is reachable, use plain `Read`/`Edit`/`Write` on paths under `../Jarvis/` (or wherever it's actually checked out — ask if it's not obviously sibling), and use `git status`/`git diff` in that checkout before committing so the human can see exactly what's about to be written, same review discipline as any other repo.
2. **Obsidian MCP tools** (`jarvis`, `jarvis-fs` in this session's `.claude/settings.json` — confirmed connected in this repo as of 2026-07-26) — if Obsidian is running locally with its Local REST API plugin enabled, `mcp__jarvis__vault_read` / `vault_write` / `vault_patch` reach the live vault directly. This is what was actually used to verify this skill's templates against the real vault. It does not require a separate git checkout, but it does require Obsidian to actually be open with that plugin active — don't assume it's connected just because the tools are listed; call `mcp__jarvis__vault_list` first and confirm it returns real vault content before proceeding.

If neither is available, **stop and tell the user** — don't guess at paths or fabricate vault content from memory of what this document says the vault contains.

**Do not attempt to write across the two repos via the GitHub API** (`mcp__github__create_or_update_file` etc.) as a substitute for either path above. `core/git_ops.py` in this repo exists specifically to solve the two-writer collision problem (this pipeline's own CI + the vault's own independent auto-commit cycle) for the one automated writer this pipeline has. Adding a second interactive writer that pushes through a different mechanism (the API instead of a local checkout + normal git) reintroduces exactly that race with no equivalent retry/rebase handling. If you find yourself reaching for the GitHub API here, stop — that's a sign this prerequisite isn't actually met, not a reason to route around it.

## Note templates

Read `reference/note-templates.md` before writing anything — it has the exact, required frontmatter for all three note types (Program, Contact, Tracker/Each One), copied from the vault's own `Program Template.md` / `Contact Template.md` where those exist, and authored from `Internship Pipeline.md`'s own field description where (Tracker/Each One) no template exists yet. These are enforced contracts, not loose guidance — every required field must be present on every note, even as `null`.

## Steps

### 1. Take the input
Accept a dossier file path, or a company/title to search for under `List/Dossiers/` (recursively — dossiers are sorted into priority-bucket subfolders `1 - AI & ML/`, `2 - Fullstack/`, `3 - CyS & Finance/`, `Other/`, per `core/classify.py`'s `BUCKET_FOLDERS`). Read the dossier's frontmatter and body, including its classification callout (the `> [!NOTE] <bucket>: ...` line in the body — dossiers don't carry a `category` frontmatter field, per `vault_writer/writer.py`'s `build_frontmatter()`, so the callout text and the folder it's filed under are the only record of the auto-assigned bucket).

### 2. Ask two concrete questions
Use `AskUserQuestion` with exactly these two questions — not open-ended prose:

- **(a) Target folder**: `Programs/Serious/` or `Programs/Considering/`. Per the pipeline doc, this is a preference/timing split only, never a rigor split — don't imply one is a lesser commitment than the other in how you phrase it. No default is auto-derivable here (nothing upstream computes "serious vs. considering"), so present both options on equal footing.
- **(b) Priority/category override**: state the dossier's auto-assigned bucket (from the classification callout / folder) as the **default answer**, and offer "keep as classified" alongside an explicit override option (with the three other buckets as alternatives, or "Other"). Don't force the human to retype the bucket name if they're keeping it — "keep as classified" should be a single selectable option, not something they have to spell out.

### 3. Invoke contact research and show findings — before writing anything
Launch the `contact-researcher` subagent (`.claude/agents/contact-researcher.md`) with the dossier's company name. Its job is exploratory — real, sourced findings or an honest "nothing found," never a guess — which is exactly why it's a subagent here rather than a script (see that file's own docstring for why). Do not call `enrich.py`'s `main()` CLI directly from this skill: that function writes an "## Enrichment" section straight into the dossier file as a side effect the moment it runs, which would be exactly the silent, pre-consent write this skill exists to avoid. The subagent uses `enrich.py`'s underlying functions (`fc_search`, `github_org_members`, `linkedin_recruiter_snippet`, etc.) without that write.

Show the subagent's full structured output to the human as-is — company info, contacts found (with source), LinkedIn search-snippet hits, or the honest "nothing found" for any category that came up empty. This is a checkpoint, not a formality: the human needs to actually see this before deciding to proceed.

### 4. On explicit go-ahead only, write all three notes together
Ask plainly: "Write the Program, Contact, and Tracker notes now?" A yes/no, not implied by silence or by having answered the two questions in step 2 — answering those questions is not the same as authorizing the write.

On yes:
1. Create any missing folder (`Programs/Considering/`, `Contacts/Each One/`, `Tracker/Each One/` — as of 2026-07-26 none of these three exist in the vault yet, only `Programs/Serious/` does) as part of this same write, not speculatively beforehand.
2. Write the Program note, Contact note, and Tracker/Each One note per `reference/note-templates.md`, cross-linked as documented there (`list_origin`, `recruiter_contact`, `related_programs`, `program`, `contact`, `related_notes`). Before finalizing, run the "Backfill structured fields from the same content the body prose is drawn from" check in `reference/note-templates.md` — a fact narrated in the Eligibility/Traps prose (class year, degree level, a stated date) must also land in its matching frontmatter field, not just the prose; `Programs/Programs MOC.md` sorts and filters on `deadline_real`/`eligible_classes`, so a fact that's only in prose is invisible to it. Fill the Prep Checklist with 3-5 real items grounded in the posting's own stated requirements/duties, not a bare checkbox. Tracker's `date_created` is today, same as `date_researched` — not deferred to a later Applying note.
3. Fold the contact-researcher subagent's real findings (with sources) into the Contact note's Facts section verbatim — don't paraphrase away the citations.
4. Report back the three paths written and a one-line summary of what's now true that wasn't before.

On no (or if the human wants changes): go back to step 2/3 as needed. Never write partial output — if any of the three notes can't be completed (e.g. a required cross-link target doesn't exist yet), stop and say so rather than writing two of three and leaving the third for later.

## What this skill does not do

- Does not create an Applying note (`Internship Pipeline.md` Step 4) — that happens later, only once real application activity starts, and is out of scope here.
- Does not run `enrich.py`'s CLI to append an Enrichment section to the dossier itself. If the human wants that too, tell them it's a separate, optional manual step (`FIRECRAWL_API_KEY=... python enrich.py "<dossier path>"`) — not something this skill does on their behalf, since that's a second write path with its own idempotency story already documented in `enrich.py`.
- Does not push/commit the vault changes. Leave that to the human (or to whatever the vault's own auto-commit cycle already does) unless explicitly asked to, and if asked, follow the same git-safety discipline as anywhere else — show the diff before committing.
