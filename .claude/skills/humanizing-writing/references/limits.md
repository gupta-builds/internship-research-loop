# Limits by kind
`humanizer_check.py` reads its limits from `scripts/data/limits.json`, inside the skill folder. Each kind has an `owner` key that says where its numbers come from. This file says which key holds each limit, who owns it, and what the script does. It does not restate a number a Standard owns: read the Standard for it.

| Kind | Keys in limits.json | Owner | What the script does |
|---|---|---|---|
| resume | `owner` only, no number | The Application Documents Standard and the DOCX generator | Nothing about length. Phrase, dash, structure and character checks still run. |
| cover | `min_words`, `max_words` | The Application Documents Standard, Letter bank (a Standard) | Blocks a letter below the minimum or above the maximum. A plan may state why not, and then the reviewer decides. |
| outreach | `max_words`, `max_asks`, `greeting_with_name`, `subject_for_email` | Working heuristic, not a Standard | Blocks a message over the word limit, more than one ask, a greeting with no personal name, and an email with no subject line. |
| followup | `max_words`, `max_asks`, `greeting_with_name`, `subject_for_email` | Working heuristic from the Implementation Plan, drafting-outreach rules | Same checks as outreach. |

## Resume length
Resume length is not checked by this script. It is checked on the DOCX by `.claude/skills/generating-resume-docx/scripts/verify_docx.py`, against the one-page word ceiling in the resume generator. Do not report a resume as too long or short from this skill.

## Where each working heuristic comes from
- **Outreach:** Handshake and WayUp advice (one specific purpose, one small ask, something real about the recipient), and one unattributed reply-rate analysis. It has no peer-reviewed study behind it, so treat the numbers as a hypothesis. The sources are recorded in the Claude System Design note, Writing and outreach evidence.
- **Follow-up:** the first follow-up stays short, from the Implementation Plan. It is a working heuristic too. The outreach word limit was set to the same figure on purpose.

## What the script counts
- Word count skips the frontmatter, HTML comments and, for outreach and follow-up, the `Subject:` line.
- An ask is a sentence that ends in a question mark or holds a request phrase. More than the allowed count flags every ask.
- A greeting passes when it opens with `Hi`, `Hello`, `Hey` or `Dear` and then a personal name. A role or team in place of a name fails.
- A subject is required only for an email. Pass `--channel message` for a direct message and the check is skipped.

## When a limit finding is not the end
A limit finding is a flag. If the drafter's plan states a reason to differ (a letter that is short on purpose), pass the flag on with that note and leave the decision to Anant. Never edit `limits.json` to make a draft pass.
