# Jarvis map

Paths are from the vault root, `$JARVIS_DIR`. Each was listed in the vault on 2026-11-26. A folder the Standards name but that does not exist yet is marked "made by the first move" and is not an error. Dated state (what is missing today, what is git-ignored) is in `status.md`, not here.

| Kind | Path | Read when |
|---|---|---|
| Standards for the note families | `30_Order/Standards/Internship/`: `Program Standard`, `Contact Standard`, `Applying Standard`, `Internship Tracker Standard`, `Internship Notes Standard` (the dossier), `Application Documents Standard`, `Interview Prep Standard` | Before writing or checking any of those notes |
| The writing check | `30_Order/Standards/Enrich/Human Writing Standard.md` | Before any application text is shown |
| Templates | `30_Order/Templates/Career/Internship/` (`Internship Program Template`, `Internship Contact Template`, `Internship Applying Template`, `Internship Cover Letter Template`) and `30_Order/Templates/Career/Tracking/Internship Tracker Template.md` | Before filling a note |
| Workflows | `30_Order/Workflows/Internship/` (`Internship Pipeline`, `Application Document Preparation`, `Career Fair Intake`) and `30_Order/Workflows/System/Loop Contract Change.md` | To know which pipeline step you are in; before changing what the loop writes |
| The loop's System records | `30_Order/System/internship-loop/` | To learn what is built and what is by hand |
| The vault linter | `30_Order/System/vault-lint/vault-lint.js` and `Vault Lint.md` | After writing a note (see `status.md` for its run time) |
| Build notes | `20_Progress/Internship/Building System/`; `V0/` for the Plan, the Design and the rebuild notes; `Runs/` for phase reports | For limits, contracts and history |
| Dossiers | `10_Areas/Career/Internships/List/Dossiers/`: `1 - AI & ML`, `2 - Fullstack`, `3 - CyS & Finance`, `Other`, `Viewed`, `_Career Fair`, `_Today`; `Applied` and `Archived` are made by the first move | To find a posting |
| Program notes | `10_Areas/Career/Internships/Programs/Serious/` and `Considering/` | Company research already done |
| Contact notes and Mimic | `10_Areas/Career/Internships/Contacts/Each One/{Ongoing,Come Back,Ended}/` and `Contacts/Mimic.md` | Outreach |
| Tracker notes | `10_Areas/Career/Internships/Tracker/Each One/{Current,Applied,Result}/`; `Applied` and `Result` are made by the first move | The dated record, after submission only |
| Applying notes | `20_Progress/Internship/Applying/` | The live hub per application |
| Resumes and letters | `20_Progress/Internship/Resumes/` (`Main Resume.md`, `Altered/`) and `Cover Letters/` (`Main Cover Letter.md` when it exists, `Altered/`) | Evidence and drafts |
| Sent packets and interview prep | `20_Progress/Internship/Sent/<dossier file name>/` (made by the first move) and `20_Progress/Internship/Preperation/Interviews/` (the folder name is spelled that way in the vault) | After submission |
| Fit | `10_Areas/Career/Engineer Edge Roadmap.md` | Whether a role fits the goal |
| Vault write contract | `AGENTS.md` at the vault root | Before any vault write |
| Session continuity | `60_Claude/07_AI_Information/` (`AI_CONTEXT.md`, `Session Logs/log.md`) | Where the vault says state lives |
| Inbox | `60_Claude/00_Inbox/` | When unsure where a write belongs |
| PDF extraction | `30_Order/Workflows/Ingestion/PDF Extraction.md`; the local wrapper is `mineru-pdf` | Before reading any PDF |

## Privacy
Treat every folder in the table that holds a note about Anant's own applications as private: Programs, Contacts, Tracker, Applying, Cover Letters, Resumes and Sent. The vault is a public git repository, so a folder is safe only when `git -C "$JARVIS_DIR" check-ignore -q "<path>"` exits 0 for it. Read `status.md` for which ones were ignored when it was last checked.
