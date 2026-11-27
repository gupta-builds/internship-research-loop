# Banned and warned phrases: what the tiers mean
The list itself lives in `scripts/data/banned_phrases.txt`, inside the skill folder. Read that file for the exact phrases. This file does not copy it, so there is one copy to keep current. One row per line as tier, a tab, the phrase, and an optional swap hint. Matching ignores case, treats a space and a hyphen alike, and needs a word boundary at both ends.

## The three tiers
| Tier | Meaning | Effect |
|---|---|---|
| block | A phrase that is a finding in every kind of draft. | Exit 1 when it is not exempt. |
| warn | A word that is a prompt to look. | Printed, never fails the check. |
| hws | A word from check 3 of the Human Writing Standard. The Standard calls these suspicious, not banned forever. | Warn in a resume, block in a letter, outreach or follow-up. |

The hws split exists because a resume bullet is short and technical, so a stray word costs little, while a letter or message is read as one person talking and the same word sounds polished and generic.

## Why each group is on the list
- **Resume and letter cliches (block):** stock claims about oneself that name no project and carry no fact. A hiring reader meets them in every pile, so they say nothing.
- **Inflated verbs (block, with a swap hint):** a heavy verb for a plain act. The hint names the plain verb, which is also the truer one.
- **Stock vocabulary (warn):** words common in model-written prose. Common words, so a hit is weak evidence.
- **Outreach and follow-up (block):** filler openers and nudges that a recruiter reads as a mass message, plus the generic greeting that shows no one was named.
- **Chat residue (block):** text left over from the model that wrote the draft, such as an offer to revise it. It means the draft was pasted without a read.
- **Check 3 words (hws):** the Standard's own list, kept in the Standard's tiering.

Structure patterns and dashes are code in the script, not rows in the file: negative parallelism, three adjacent openers, a three-part list in every paragraph (all warn) and em or en dashes (block, except a range between years).

## Where the list comes from
Three source tiers, in order of weight:
1. The vault's own Human Writing Standard (check 3, the check 4 dash rule, check 5 structure). Anant's rule.
2. Two public repos whose lists were read in full: career-ops (its banned phrases, cover letter and follow-up bans) and ai-job-search (its cut list). Their lists come from practice, not from measurement.
3. Wikipedia, "Signs of AI writing": a field guide to puffery, "-ing" analysis phrases, negative parallelism, the rule of three, formulaic conclusions, letter-like openers, chat residue and vague attribution. The page calls its signs "observations, not rules". The ban on em dashes is stricter than the page.

None of the lists is a measured detector.

## A hit is a prompt to look, not proof
People cannot reliably tell AI text from human text, and a human writes these phrases too. So:
- Read the line. Ask whether the phrase is the most accurate word for the fact.
- A phrase that also appears in the `--sources` files is exempt: Anant's own approved words are not overridden.
- A swap hint is a direction. Check that the plain verb is still true to the source before you suggest it.
- A draft with no hit can still fail checks 1, 2, 6, 7, 9, 10 or 11. A clean script run is not a pass by itself.
