# What can run without asking, in this repo

This repo has two very different classes of agent, and it's easy to conflate them once there are seven of them. Sorted by what they're actually allowed to do unattended:

## Safe to run fully autonomously — read-only, no vault write, no repo write
- **`loop-verifier`** — read-only by its own explicit rule: "never modify code, never write to the vault, never delete state files, never file or comment on issues." Reports; a human or a separate task acts on it.
- **`testing-tools`** — read-only against application code (`core/`, `ingestion/`, `vault_writer/`); never commits a drafted test itself.
- **`contact-researcher`** — writes nothing; only searches public sources and reports findings (or "nothing found," honestly). Its *output* still has to be shown to a human before it becomes part of a Contact note — that gate lives in `promotion`/`promote-dossier`, not in this agent itself.

## Never autonomous — always gated behind explicit human consent
- **`program-writer`, `tracking`** — write real notes into a personal Jarvis vault (job-search data, contacts, application status). Both are invoked only after their caller (`promotion` or `/promote-dossier`) has already gotten an explicit yes/no from the human — never invoke either directly against a vault write without that gate already having happened.
- **`promotion`** — the consent gate itself lives inside this agent (step 4's explicit "write the three notes now?" ask). Do not skip that ask because the two prior questions were already answered — answering "which folder" is not the same as authorizing the write.
- **`applying`** — additionally self-gates on `Main Resume.md`/`Main Cover Letter.md` not being real yet (see the agent's own "Not runnable yet" section) — refuses to draft against filler content even if asked to proceed.

## Why this split, not a single rule
The read-only/write split above is the same "procedural code owns the environment; the agent owns content" principle the Jarvis vault's own build standard states for its `.claude/` layer — applied here to *which agents may act without a human in the loop* rather than to code-vs-prose. A read-only agent's worst-case failure is a wrong report, which a human catches on the next real check; a write-capable agent's worst-case failure is a fabricated fact landing in a personal record that gets acted on (an application sent off evidence that was never real). The asymmetry is why the second group's gate is non-negotiable and the first group's isn't.

## Secrets and repo-level boundaries
See `CLAUDE.md`'s "Auto-mode classifier notes" section (repo visibility, secrets, protected branches, soft-deny list) — not restated here; this file is about agent-level autonomy, that section is about repo-level operational boundaries.
