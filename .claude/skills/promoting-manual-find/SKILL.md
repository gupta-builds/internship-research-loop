---
name: promoting-manual-find
description: Promotes a manually-found internship lead (career fair, referral, LinkedIn — never went through the discovery loop, no dossier exists) into a real Program + Contact + Tracker note trio in the Jarvis vault. Use when the user has a real lead they found themselves and wants it committed at Internship Pipeline Step 3, the same rigor a loop-discovered dossier gets.
---

# /promoting-manual-find

Thin entry point. All of the actual orchestration — the consent gate, contact research, and writing the three notes — lives in the `promotion` subagent (`.claude/agents/promotion.md`). This skill exists only to collect the lead's raw facts from the user and hand them off; it does not duplicate `promotion`'s logic.

## Why a separate skill from `/promote-dossier`

`/promote-dossier` starts from a dossier — a file that already exists, already fetched and screened. A manual lead starts from nothing but what the user remembers or has seen. The inputs are different enough (no auto-classified bucket, no `list_origin` to link, source material that might be a screenshot or just a conversation) that forcing a manual lead through `/promote-dossier`'s dossier-shaped input step would mean guessing at fields that were never real. Two thin skills sharing one orchestrator agent (`promotion`) is the "lesser the merrier" version of this — not two full copies of the same three-note-writing logic.

## Steps

### 1. Collect the lead
Ask (or use whatever the user already stated): company, role/title, URL if one exists, where it came from (career fair, referral, LinkedIn, a named person), and any real source material — a web clipping already captured under `60_Claude/05_Clippings/Web/Internships/`, a screenshot's transcribed text, or just what the person remembers. Do not invent a URL or posting content that wasn't actually given.

### 2. Confirm Step 2 (the fit test) already happened
Per `Internship Pipeline.md`, a manual lead passes the same goal-push/personal-fit/contact-reachability test as any dossier before being committed. If the user hasn't actually made that call yet, ask them to make it now — don't assume a lead they're asking to promote has automatically passed.

### 3. Hand off to `promotion`
Invoke the `promotion` subagent with everything collected above. It owns the rest: the folder/priority questions, the contact-research checkpoint, the explicit go-ahead, and invoking `program-writer`/`tracking` to write the three notes.

### 4. Report back
Relay `promotion`'s final report (the three note paths, the cross-links now in place) to the user as-is — don't paraphrase away specifics like which fields were backfilled.

## What this skill does not do

- Does not decide anything itself — see `promotion` for the actual decision points.
- Does not handle a dossier — use `/promote-dossier` for that path, unchanged.
