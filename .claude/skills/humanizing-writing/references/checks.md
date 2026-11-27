# The 12 checks: script or reviewer
The wording of each check, and its pass condition, is in the Human Writing Standard (vault: `30_Order/Standards/Enrich/Human Writing Standard.md`, the check table and the Application documents table). This file only says who runs each check and what to look for. The pass and fail contract is the vault note Humanizer.

The script is `humanizer_check.py`. It prints findings as `path:line [tier/kind] token | context`. The tiers are block and warn. The kinds are phrase, dash, structure, length, ask, greeting, subject, placeholder and char.

| # | Check | Run by | What the reviewer looks for |
|---|---|---|---|
| 1 | Delete test | reviewer | Read each sentence and ask whether it could sit in a generic productivity blog. Flag a sentence that carries no mechanism, example, contrast or decision. |
| 2 | Section job | reviewer | Name the job of each section or paragraph (define, show how, give an example, say what is unclear). Flag a section with no job, such as a paragraph that only restates the one before. |
| 3 | Suspicious words | script, kind phrase | The script finds the words. The reviewer decides the exception the Standard allows: a word stays only where it is the most accurate word. A hit in a letter or message blocks; in a resume it warns. |
| 4 | No em dash | script, kind dash | Nothing for the reviewer unless a dash sits in a range the script missed. A range between years is allowed. |
| 5 | Structural tells | script, kind structure (warn only) | The script finds negative parallelism, three adjacent openers and a three-part list in every paragraph. The reviewer decides whether the pattern repeats (a tell) or happens once (style). Also look for uniform sentence length, which the script does not measure. |
| 6 | Tone against fact | reviewer | Compare each claim's loudness with the fact behind it in the source. Flag "led" over "helped", or a superlative over a small number, even when the fact is true. |
| 7 | Honest uncertainty | reviewer | Inferred material is marked inferred, missing material says what is missing, a weak source is called weak. Flag a confident sentence over partial knowledge. |
| 8 | Evidence survives the pass | reviewer, then checking-evidence | After any rewrite, compare each claim with the source it had before. A claim that drifted is a regression. The factual comparison is the checking-evidence skill's job. |
| 9 | Thin thinking | reviewer | Flag a section that is thin because the thinking is thin and has been dressed in better wording. List it under "Still thin". |
| 10 | One person | reviewer | Read the whole draft for one consistent voice. Flag a template with the company name swapped in, or a section that reads as a different writer. |
| 11 | Boilerplate | reviewer | Ask whether a reader would recognize it at once as AI boilerplate even if each line looks fine alone. The script's placeholder and chat-residue findings count here. |
| 12 | Evidence after tone | reviewer, then checking-evidence | Check 8 applied again before a draft becomes a DOCX. Every claim traces to the evidence it had before the tone pass. |

## Findings with no check number
The script also enforces limits and hygiene that are not numbered checks. Write the flag as `breaks limit (<kind>)`:
- length, ask, greeting and subject: see `limits.md`.
- placeholder (an unfilled `[Company]`, `{{team}}`, `XYZ`, `TODO`): flag it as check 11, boilerplate, because a letter that still holds a template slot fails at once.
- char (a zero-width character blocks, a curly quote warns): a hygiene flag, `breaks limit (char)`.

## Script limits
The script matches words and patterns. It cannot read meaning, so a clean script run does not mean checks 1, 2, 6, 7, 9, 10 or 11 pass. Run them by reading. It does not check facts.

## Synthetic example of a flag report
Synthetic example, invented text:
```text
FAIL
3: "passionate about scalable systems" breaks check 3 (Suspicious words). Suggested fix: name the project and the number instead.
7: "I led the whole migration" breaks check 6 (Tone against fact). Suggested fix: match the verb to the source, which says the work was shared.
Still thin: the closing paragraph says nothing about this team.
```
