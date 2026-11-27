# Limits of the script
`evidence_check.py` matches values, not sentences. A pass means nothing was invented. It does not mean every sentence is accurate. This file says how to read each finding, what the script cannot catch and what the reader checks instead.

## How the sources are cleaned
- Sections titled Logged Gaps, Tailoring Notes, positioning, preferences, legacy and similar are dropped from the sources. A gap logged in `Main Resume.md` never counts as evidence.
- Pass every source the draft draws on after `--facts`. A project note that is not passed is a source the script cannot see, so its facts show up as findings.
- `--jd` is refused for a resume (exit 2). For a letter or message it supplies only the company and role names, and a number only when the letter sentence shares a word of four or more letters with the posting sentence that holds it and the counted noun matches. It never supplies a skill or a tool.

## Reading each finding
Each line is `path:line [kind] token | context`.

| Kind | What it means | What to do |
|---|---|---|
| number | No source number has this value and counted noun (for example "12" bound to "intern"). Magnitudes are folded, so 2.3M equals 2.3 million. "45m" reads as 45 million. | Find the source number. If the value or the noun differs, it is a gap. |
| date | A month, year or range end is not in the sources. Both ends of a range are checked, and `Present` equals `Current`. | Check each end against the source role. A wrong end is a gap. |
| entity | A company, title, degree or tool name is missing from the sources, or the parts of one heading do not sit together in one source section (an employer joined to another role's title). | Read the source section for that role. Mixed parts from two roles are a gap. |
| skill | A Skills section item is not in the sources. | Look for a synonym (see `--allow` below). Otherwise it is a gap. A skill never used in a project stays out. |
| url | A link is not in the sources and its host is not allowed. | Find the link in a source. A link nobody approved is a gap. |
| coverage | The script could not read a section it expected, so it checked nothing there. | Read that section by hand. Coverage is never a pass. |

## What the script cannot catch
- A true number placed on the wrong role, in prose.
- A stronger verb than the source supports ("contributed" to "led").
- A sentence that is false though every token matches.
- A sentence-initial capitalized word, which is not checked as an entity.
- An ambiguous English word (go, react, rust, swift, spark, excel, unity, lambda), which is checked in a draft only in a Skills section or when capitalized, and traced only where a source capitalizes it ("learned to react" is not React).
- A posting number used as past work. The script lets a number through when the letter sentence shares a word with the posting sentence, and prints a `note:` line for each one. Read every note and confirm the letter states a plan, not past work.

For each, the reader compares the draft with the source sentence by sentence, using the ledger. A quote that does not carry the claim's verb, role and number together is a gap.

## When to use `--allow`
`--allow FILE` takes one entry per line. `a = b` adds an alias for this run. A line that looks like a domain allows URLs on that host. Any other line is a token accepted as traced.
- Use it for a real synonym the script missed, after you found the source line. Example: the draft says PG and the source says PostgreSQL, so the allow file holds `postgresql = pg`.
- Use it for a host Anant owns and a source names.
- Say every entry aloud in the report, with the source line that justifies it.
- Do not use it to silence a gap, to accept a number you cannot find, or to pass a draft. If no source line exists, the finding stays.
- Every acceptance is counted in the last line, aliases included (`N accepted by --allow`). Still name each entry in the report, because the count says how many were accepted but not which.
