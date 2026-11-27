# Skill evaluation prompts

Description tests for each procedure skill: two prompts that should load it and one near-miss that should not, as the Implementation Plan's Tests and evaluations section asks. A command skill needs none. Each row is run in a fresh `claude -p --model sonnet` session launched inside a worktree of this repo, with only `Skill` and `Read` allowed, and the transcript is read for a `Skill` tool call. A session that reads `SKILL.md` directly picked the skill but did not load it, and counts as a miss. Paths point at synthetic fixtures.

C7 adds the transcript audit and the Haiku run; this file is where each phase records its rows and results.

## humanizing-writing (C3, 2026-11-27)
| Id | Prompt | Expected | Result |
|---|---|---|---|
| hw-t1 | "Here's my cover letter draft for the tier 1 role: tests/claude_layer/fixtures/humanizer/cover-pass.md. Check it before I approve it." | loads | loaded |
| hw-t2 | "Does this follow-up read like a person wrote it? It's tests/claude_layer/fixtures/humanizer/email-pass.md." | loads | loaded |
| hw-n1 | "Fix the AI-sounding prose in my weekly review note in the vault." | does not load | not loaded |
| hw-t3 | "I finished the cover letter draft for the tier 1 platform role last night (.../cover-pass.md) and I'm meeting my advisor tomorrow. Before I approve it, check it against my writing rules and tell me which lines to fix." | loads | loaded |
| hw-t4 | "The drafter wrote a follow-up for the recruiter, 8 days after I applied (.../email-pass.md). Does this read like a person wrote it, or like a template?" | loads | before the description tune: 1 of 3 runs loaded, 1 read `SKILL.md` directly, 1 loaded nothing; after adding "letter, message or follow-up ... or like a template": 3 of 3 loaded |
| hw-n2 | "My weekly review note in the vault sounds like ChatGPT wrote it. Can you strip the AI-sounding prose out of it?" | does not load | not loaded (twice, before and after the tune) |

## checking-evidence (C3, 2026-11-27)
| Id | Prompt | Expected | Result |
|---|---|---|---|
| ce-t1 | "Check that every number and skill in this resume plan (tests/claude_layer/fixtures/evidence/noun-fail.md) is in my Main Resume (use .../source.md as the resume for now)." | loads | loaded |
| ce-t2 | "Did the drafter invent anything in this letter? .../posting-letter-pass.md, sources .../source.md, posting .../posting.md." | loads | loaded |
| ce-n1 | "Is this email too long? tests/claude_layer/fixtures/humanizer/email-pass.md" | does not load | not loaded |
| ce-t3 | "The drafter just produced a resume plan for the robotics intern role (.../number-fail.md), and it has a 40% latency number I don't remember. Check that every number and skill is actually in my Main Resume (.../source.md) before I approve it." | loads | loaded |
| ce-t4 | "I'm sending the cover letter for the tier 1 role tonight (.../posting-number-pass.md, posting .../posting.md, my sources .../source.md). Did the drafter invent anything in it?" | loads | loaded |
| ce-n2 | "This follow-up email to the recruiter feels long and a bit stiff (.../email-pass.md). Is it too long, and does it sound okay?" | does not load | not loaded (twice; the second run read humanizing-writing's `SKILL.md`, the right neighbour) |
