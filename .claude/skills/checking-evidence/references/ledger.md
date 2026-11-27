# Claim ledger
One row per factual sentence in the draft. A factual sentence names a number, a date, an employer, a title, a tool, a project, a link or something Anant did.

## Format
| Claim | Source path | Quote |
|---|---|---|
| The sentence or clause from the draft, copied exactly | The file and line, or the vault path of the note | A short run of words from the source, copied exactly |

- Quote the source, not the draft. If the quote does not contain the claim's number, name and verb, the row is wrong.
- Several claims in one sentence get several rows, so a gap in one cannot hide behind a match in another.
- A claim Anant stated in this session: the source path says "stated in session" with the date, and the quote is his words.
- A claim with no source goes in the Gaps table, never in the ledger.

## Two synthetic examples
Both rows below are a synthetic example. The names, numbers and files are invented.

| Claim | Source path | Quote |
|---|---|---|
| Cut build time from 14 minutes to 6 (resume bullet, synthetic example) | `Main Resume.md:41` | "reduced CI build time from 14 min to 6 min" |
| I maintained the lab's print queue for two semesters (letter sentence, synthetic example) | `Main Cover Letter.md:18` | "kept the lab print queue running for the 2024-25 school year" |

## One gap row
| Claim | Why there is no source | What Anant would have to state |
|---|---|---|
| Led a team of 5 (synthetic example) | The sources say "contributed to a team"; no line gives a team size or a lead role | Whether he led, and the real team size |

## Reading the table
- A claim whose quote only half matches (the number matches, the verb is stronger) is a gap. Put it in the Gaps table and name the difference.
- The ledger is the proof that the reading check ran. A report with a ledger that skips a factual sentence is incomplete.
