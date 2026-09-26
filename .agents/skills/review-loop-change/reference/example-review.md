---
created: 2026-09-06
type: reference
tags: [internship-research-loop, review-loop-change, example]
---

# Worked example — `check_conventions.py` catching real violations

Fabricated diff, used only to show what the script actually catches and how to read its output. Run for real against `core/relevance.py` with two deliberately planted problems:

```diff
+# New rule, added without a citation
+SUSPICIOUS_TOKENS = {"contract-to-hire"}
+
+import openai
+
+def call_llm(prompt):
+    return openai.ChatCompletion.create(messages=[{"role": "user", "content": prompt}])
```

Real script output:

```
## check_conventions.py: core/relevance.py

[FLAG] 1. Zero-LLM in unattended path -- core/relevance.py:6 -- matches LLM-signal pattern `\bimport\s+openai\b`: import openai
[FLAG] 4. Cited real data -- core/relevance.py:4 -- new rule/constant with no nearby date or 'confirmed/observed/real' citation: SUSPICIOUS_TOKENS = {"contract-to-hire"}

2 FLAG (likely real violation, confirm before shipping), 0 NOTE (needs human judgment, not automatically a violation).
```

The same addition, fixed (cited, no LLM import):

```diff
+# Confirmed against 3 live postings 2026-09-06 (Acme, Beta Corp, Gamma Inc)
+SUSPICIOUS_TOKENS = {"contract-to-hire"}
```

```
## check_conventions.py: core/relevance.py

No mechanical findings across all four checks on the files touched.
```

## What this demonstrates

- **FLAG** means the script found a real pattern match — treat it as a likely violation to confirm, not a maybe.
- **NOTE** (checks 2 and 3) means the script found something *shaped like* a possible violation, or touched a file where a violation is possible, but genuinely needs a human/model to read the actual logic — the script narrows the search, it doesn't replace judgment there.
- **No findings** still ends with a reminder to manually confirm checks 2/3 where relevant — a clean run on checks 1/4 is real evidence for those two specifically, not a green light for all four.
