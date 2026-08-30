# promote-dossier note templates

These are the **only** three note shapes `promote-dossier` is allowed to write. They are strict contracts, not starting points — every field listed as required below must be present on every note this skill writes, even when the value is genuinely empty (use `null` / `[]`, never omit the key). This mirrors `vault_writer/validate.py`'s `REQUIRED_FRONTMATTER_FIELDS` fail-closed pattern in this repo: a missing required field is a bug, not a stylistic choice.

Field names below are copied verbatim from the vault's own templates — `30_Order/Templates/Career/Program Template.md` and `30_Order/Templates/Career/Contact Template.md` — read directly from the Jarvis vault on 2026-07-26. **Tracker/Each One has no pre-existing template in the vault** (only `Tracker/Internship - Dashboard.md` and `Tracker/Tracker.md` exist, both roll-up views, not per-item notes); its shape below is authored from `30_Order/Workflows/Internship Pipeline.md`'s own field description ("noted/researched/created/applied/result, deadline, contact link, related notes, url") since there was nothing existing to copy. If a real Tracker/Each One template later gets added to the vault, this skill should switch to it instead of its own.

**Filename convention**, all three note types: `<Role> - <Company>.md`, same sanitization as `vault_writer/writer.py`'s `dossier_filename()` (strip `\/:*?"<>|` and control chars — the vault lives on a Windows-mounted drive) and the real hand-renamed example already in the vault, `Programs/Serious/Software Engineer - Ellipsis Labs.md`'s dossier counterpart. Collision handling: append ` (2)`, ` (3)`, ... same as dossiers.

**Folder existence as of 2026-07-26** (checked live via the vault's MCP tools): `Programs/Serious/` exists (1 note in it). `Programs/Considering/`, `Contacts/Each One/`, and `Tracker/Each One/` do **not** exist yet — nothing has ever promoted into them. Creating a missing folder is part of the write step itself (it happens only after explicit go-ahead, same as the notes) — never create it speculatively before the human has said yes.

## Backfill structured fields from the same content the body prose is drawn from — don't default to null

Found live in the first real run of this skill (Appian dossier, 2026-07-26): the body sections below (`Program Overview`, `Eligibility`, `Traps & Gotchas`) are written from the dossier's fetched posting content, and it is very easy to write a fact into that prose while leaving the frontmatter field that same fact belongs in untouched at its template default (`null`/`[]`). That's a real defect, not a cosmetic one — `10_Areas/Career/Internships/Programs/Programs MOC.md` sorts and filters on `deadline_real` and `eligible_classes`; a fact that only exists in prose is invisible to that view.

Before finalizing the Program note, re-read the Eligibility and Traps paragraphs you just drafted and check each one against the frontmatter fields below. If a fact you're about to narrate in prose maps to one of these fields, write it into both places — never only the prose:

- **`eligible_classes`**: whatever concrete class-year or degree-level signal the posting actually states — e.g. `["Bachelor's", "Master's"]` if the posting says "currently pursuing a Bachelor's or Master's degree", or `["Sophomore"]` if it names a class year directly (matching the real `Programs/Serious/2026-HRT-Sophomore.md` example in the vault). Use whatever's literally stated; never invent a class year the posting doesn't name.
- **`grad_year`**: only a literal year the posting states directly (e.g. "Class of 2028", "graduating May 2028"). A constraint like "must return to school after this internship" tells you the candidate ISN'T graduating in the internship's own year — that's a fact for `eligible_classes` or the Eligibility prose, not license to compute a specific `grad_year` the posting never states. Leave `grad_year` null in that case rather than guess a number.
- **`opens_date` / `deadline_posted` / `deadline_real`**: use whichever of these three literally matches what the posting states — an application-open date, a stated/official deadline, or a confirmed-different real deadline, respectively. A vaguer timeline signal (e.g. "applications won't be reviewed until August 2026") is real and worth keeping, but if it doesn't literally match any of the three concepts, don't force it into the closest-sounding field — a wrong date in `deadline_real` is worse than a null one, since the MOC would sort/filter on a value that isn't actually a deadline. Put it in the Traps & Gotchas prose (as this skill already does) and, if only a month/year is known and not a day, it's fine to write a coarser `YYYY-MM` value into whichever field it does genuinely match rather than defaulting to null just because the day is unknown.
- This same check applies to the Tracker note's `deadline` field (mirrors Program's `deadline_real`) and to `careers_page` (often stated or discoverable in the same contact-research pass, not just the dossier).

---

## 1. Program note

Path: `10_Areas/Career/Internships/Programs/Serious/<Role> - <Company>.md` or `.../Considering/<Role> - <Company>.md` (per the human's answer to question (a)).

```yaml
---
name:                # "<Role> at <Company>" — human-readable, not the filename
company:
program_type:        # e.g. "Software", "Quant", "Research" — from the dossier's category/classification bucket
eligible_classes: []  # from dossier target_year, or from the fetched posting content — see "Backfill" rule above, don't leave [] if the Eligibility prose states one
grad_year:            # only a literal year the posting states — see "Backfill" rule above, don't infer one from a "must return to school" style constraint
role_type: internship
wave:                 # null unless known
opens_date:           # see "Backfill" rule above — only if the posting literally states an open date
deadline_posted:      # from dossier content if stated — see "Backfill" rule above
deadline_real:        # null unless independently confirmed — never assume posted == real; see "Backfill" rule above
pay_per_week:         # null unless stated
pay_currency: USD
duration_weeks:       # null unless stated
benefits: []
application_url:      # dossier's url field
careers_page:         # null unless found during contact research
list_origin: "[[10_Areas/Career/Internships/List/Dossiers/<bucket-folder>/<dossier-filename>]]"
applying_note: null   # Step 4 hasn't happened yet — this skill never creates an Applying note
recruiter_contact: "[[10_Areas/Career/Internships/Contacts/Each One/<Role> - <Company>]]"
tags:
  - internship
  - program
---
```

Required fields, always present: every key listed above. Body sections, verbatim structure from the vault's own `Program Template.md` (do not invent new headings):

```markdown
# <Role> — <Company>
Static research only — comp, eligibility, deadlines, traps, prep. Live status (applied, interview, offer) lives on the matching note in `20_Progress/Internship/Applying/`, linked via `applying_note` above.
## Program Overview
What the role is, who runs it, what makes it worth the hours to prepare for. (pull from the dossier's posting content)
## Eligibility
Who can apply, what year/major requirement, and anything that disqualifies you before you start.
## Traps & Gotchas
> [!WARNING]
> The thing most applicants get wrong about this program. (only include real traps found in the dossier/enrichment — never invent one)
## Prep Checklist
- [ ] <3-5 real items, generated from this posting's own stated requirements/duties — see below>
## Related Resources
- [[<dossier note>]] (List/Dossiers origin)
```

**Do not** write a `status` or `next` field on the Program note — the pipeline doc is explicit that Program notes are durable/static and only change when a fact about the program itself changes; funnel status belongs on the (not-yet-created) Applying note or the Tracker note.

**Prep Checklist: the skill fills this, not a blank template.** `30_Order/Templates/Career/Program Template.md` itself (the vault's generic template, used when someone creates a Program note by hand) is correctly left as a bare `- [ ]` — a blank scaffold is the right contract for a template a human fills in from scratch. But `promote-dossier` isn't starting from scratch: it already has the dossier's fetched posting content in hand, the same content it's already turning into the Eligibility and Traps prose above. Leaving the checklist bare when that source material is right there is the same class of bug as the frontmatter-backfill issue — known, derivable content going unused. Generate 3-5 concrete items straight from the posting's own "What You'll Do" / "Qualifications" / "Basic Qualifications" sections (e.g. Appian's real posting → "Review data structures, algorithms, and OOP fundamentals", "Prepare to discuss using AI coding tools critically, not just as autocomplete", "Have a portfolio example of full-stack work ready to discuss" — each traceable to a specific line in the fetched content, never generic interview-prep advice that isn't grounded in this specific JD).

---

## 2. Contact note

Path: `10_Areas/Career/Internships/Contacts/Each One/<Role> - <Company>.md` — company-level research, filed under the same `<Role> - <Company>` name as the Program note it's paired with (not the contact person's own name — one company can have several people found, the note is about the company relationship, matching the pipeline doc's "company-level contact research").

```yaml
---
type: contact
name:                 # the PRIMARY contact person's name, if contact-researcher found exactly one strong hit — else null
role:                 # that person's title (e.g. "Senior Recruiter") — else null
company:
linkedin_url:         # only if contact-researcher returned a linkedin.com URL as a source — else null
email:                # only a contact-researcher/enrich.py-inferred address with a real MX record — else null
how_found:            # cite the actual query/source, e.g. "linkedin search snippet: site:linkedin.com <company> recruiter"
relationship: cold
related_programs:
  - "[[10_Areas/Career/Internships/Programs/<Serious|Considering>/<Role> - <Company>]]"
last_contact_date: null
tags:
  - contact
next: null
---
```

Required fields, always present: every key listed above (`null`/`cold`/`[]` are valid values, omission is not). Body, verbatim structure from `Contact Template.md`:

```markdown
# <Role> — <Company>
## Facts
Everything contact-researcher actually returned, with its source cited per item — see "How this section gets filled" below. If it found nothing, say so explicitly: "No public contact signal found as of <date>." Never pad this section with a guess.
## Current Draft
The live, unsent message to this person right now. Build it from [[Mimic]] and edit until it sounds like you, not the template. Leave this section empty (just the heading) if no contact was found — there is no one to draft to yet.
## Conversation Log
Dated entries, newest at the bottom.
- **<today's date, YYYY-MM-DD>:** Note created via promote-dossier.
## Next Action
The single next move — send, follow up, or wait. If nothing was found: "Recheck contact research once <company>'s public presence changes, or apply cold through the portal."
```

**How this section gets filled**: paste the contact-researcher subagent's structured output (recruiter/university-recruiting hits, engineering-blog byline, GitHub org member, LinkedIn search-snippet — each with its source) into Facts verbatim, one bullet per finding, source in parentheses. Do not summarize away the source citation — the whole point of this note is that every claim in it traces back to something real.

---

## 3. Tracker/Each One note

Path: `10_Areas/Career/Internships/Tracker/Each One/<Role> - <Company>.md`. Created only once the Program note exists (same commit/sitting), per pipeline Step 3.

```yaml
---
type: tracker
program: "[[10_Areas/Career/Internships/Programs/<Serious|Considering>/<Role> - <Company>]]"
contact: "[[10_Areas/Career/Internships/Contacts/Each One/<Role> - <Company>]]"
company:
url:                  # dossier's application_url, duplicated here per the pipeline doc's explicit field list
date_noted:           # the dossier's own date_found field
date_researched:       # today — the date this promotion actually happened
date_created:         # ALSO today — this is the day the Program/Contact/Tracker notes themselves were created, not the (much later, Step 4) Applying note. Fixed 2026-07-26: an earlier version of this template wrongly deferred this to Applying-note creation, which isn't even one of the pipeline doc's five listed Tracker milestones (noted/researched/created/applied/result) — "created" in that list means these three notes, written in one sitting, same day as date_researched.
date_applied: null
date_result: null
result: null
deadline: null         # mirrors Program note's deadline_real once known; null until then
related_notes:
  - "[[10_Areas/Career/Internships/List/Dossiers/<bucket-folder>/<dossier-filename>]]"
tags:
  - internship
  - tracker
next: null
---
```

Required fields, always present: every key listed above. Body:

```markdown
# <Role> — <Company>
The dated index for this internship — source of truth for "where does this stand" until an Applying note exists (see [[30_Order/Workflows/Internship Pipeline]] Step 8).
## Timeline
- **Noted:** <date_noted>
- **Researched:** <date_researched>
- **Created:** <date_created — same day as Researched, not left blank>
- **Applied:** —
- **Result:** —
## Next Action
The single next move. Mirrors `next:` above.
```

Do not add a Dataview query or dashboard block to this note — those already exist at `Tracker/Internship - Dashboard.md` and `Tracker/Tracker.md`; duplicating them here is exactly the kind of redundant note the pipeline doc's Step 8 explicitly warns against ("not a replacement for the Dashboard or Kanban").

---

## Cross-linking summary (all three notes, written together, in one sitting)

- Program `list_origin` → dossier note
- Program `recruiter_contact` → Contact note
- Contact `related_programs` → Program note (back-link)
- Tracker `program` → Program note
- Tracker `contact` → Contact note
- Tracker `related_notes` → dossier note

No other cross-link fields exist in the vault's current templates for this step — don't invent a `tracker_note` field on the Program note or a `program` field on the dossier; if a future session needs one, that's a vault-template change to propose explicitly, not something this skill should add silently.
