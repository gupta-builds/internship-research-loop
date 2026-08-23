"""Layer 2.5 — CS/software-relevance gate. Runs after matches() passes, before
the write gate. Two-stage, zero-LLM, same keyword-heuristic style as
core/filter.py:

  stage1_reject: cheap, title/raw_text only, no fetch. Called in
  fetch_and_filter alongside matches() — catches the unambiguous
  non-software cases for free before a Firecrawl credit is ever spent.

  stage2_confirm: content-based, called only once posting_content has
  actually been fetched (same point the OPT-eligibility check already uses
  it). Adjacent fields (hardware, robotics, astrophysics, space,
  embedded/firmware) are not auto-excluded by stage 1 — they pass stage 2
  only if the posting's real content shows genuine software/CS work.

Persona bar: BS Computer Science, full-stack + AI/ML + backend/systems
skillset (Main Resume.md: Python/Rust/TS/JS/React/Java/C, RAG/embeddings/LLM
APIs/data pipelines, Next.js/full-stack, Postgres/Docker/infra; Engineer Edge
Roadmap.md: "systems-minded AI engineer" — full-stack products + backend
systems + observability + AI workflows). A posting passes if its real duties
involve software/CS work, even at a company in an adjacent industry (space,
robotics, astrophysics, automotive/hardware). A posting fails if it's
fundamentally non-technical (financial/risk analyst, tax preparer, sports
performance analytics) regardless of company.
"""
import re


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


# Real live examples confirmed against seeded Greenhouse boards 2026-07-26:
# FC Cincinnati "Academy Performance Analyst Intern" / "FCC2 Performance
# Analyst Intern" (pure sports video coding/KPI labeling, zero software —
# see tests/fixtures/relevance for the real fetched content), Walleye
# Capital "Investor Relations Intern". Deliberately narrow — a false
# positive here silently kills a listing before it's ever fetched, so only
# unambiguous non-software role nouns go here, and each pattern requires the
# non-software noun to be the role itself, not a qualifier ahead of a
# software-shaped word: "Tax Technology Intern" (real SimplifyJobs fixture,
# category AI/ML/Data, genuinely technology-consulting work) must NOT match
# "tax accountant"/"tax preparer", and "Risk Technology Analyst Intern"
# (real Walleye Capital title) must NOT match "risk analyst" — "Technology"
# sits between the two words in both real titles, breaking the adjacency
# these patterns require.
# Product/program-management and business-rotational patterns added 2026-07-29
# from two real recurring incidents: Databricks "Product Management Intern
# (Summer 2027)" (AIJobs, found 2026-07-26 — explicitly PM work, "learn how to
# be a successful PM," despite listing "computer science" as an acceptable
# major, and classified AI/ML only because "Machine Learning" is one of
# Databricks' internal team names, not because the role does ML work) and
# Conagra Brands "Demand Science Rotational Analyst" (SimplifyJobs,
# 2026-07-27, still live at List/Dossiers/Other/ as of this writing — a 2-year
# business rotational program across Behavioral Science/Demand
# Forecasting/Demand Planning/Advanced Analytics with zero programming
# content; its own stated requirement is "a general understanding of
# business, financial concepts, and theory behind processes"). The rotational
# pattern requires "rotational" not be immediately preceded by "engineering "/
# "software " so a genuine software-engineering-track rotational program still
# passes (checked explicitly in tests/test_relevance.py).
_ROTATIONAL_ANALYST_RE = re.compile(
    r"(?<!engineering )(?<!software )\brotational (analyst|program)\b", re.I,
)
_STAGE1_REJECT_RE = re.compile(
    r"\b(financial analyst|risk analyst|performance analyst"
    r"|tax (associate|preparer|accountant)"
    r"|investor relations"
    r"|sports performance (analyst|analytics)|academy performance (analyst|analysis)"
    r"|human resources intern|hr intern|marketing intern|business development intern"
    r"|product management intern|product manager intern"
    r"|program management intern|technical program manager intern"
    r"|demand (planning|science) (analyst|rotational)"
    r"|business analyst intern)\b",
    re.I,
)


def stage1_reject(title: str, raw_text: str) -> bool:
    """True if this listing's title/raw_text is unambiguously non-software —
    reject without ever fetching the page."""
    haystack = f"{title} {raw_text}"
    return bool(_STAGE1_REJECT_RE.search(haystack)) or bool(_ROTATIONAL_ANALYST_RE.search(haystack))


# Adjacent-field company/title hint — NOT a reject signal on its own (Jane
# Street "Hardware Engineer (FPGA/ASIC) Intern" and Bosch/Magna's automotive
# ML roles all pass real content checks below). Only postings that hit this
# hint need their fetched content checked at all; everything else already
# cleared stage 1 and passes through unconditionally.
# chemical/plant/PLC-DCS-SCADA added 2026-07-29: real false-positive, Mosaic
# (The Mosaic Company, agricultural/mining) "Operations & Automation
# Engineering Co-op/Intern" — a chemical-plant industrial-automation role
# (PLC/DCS/SCADA controls, Bachelor's in Chemical Engineering required,
# physical labor requirements, "basic computer skills" as a minor bullet)
# passed stage 2 unconditionally because neither "chemical" nor "automation"
# hit the old hint list, so its content (no Python/Java/C++/git/algorithm
# anywhere) was never checked at all — it only got flagged downstream by
# classify.py's now-fixed bare-'threat' match on an unrelated workplace-safety
# disclaimer. Adding these hints routes it through the real software-signal
# content check below, which correctly rejects it.
#
# 'space'/'defense' dropped 2026-08-23 (dossier audit): both were confirmed
# real false positives on ordinary English, not industry usage — Jane
# Street "Cybersecurity Analyst Intern" ("we consider ourselves to be tapped
# into developments in the broader cybersecurity **space**") and Appian
# "Information Security Engineer Intern" ("modern cloud architecture
# **defense**") both wrongly required a software-signal match on real,
# genuine security-engineering content. Unlike 'threat' (tightened with a
# co-occurrence window built from real cited phrasing —
# threat.{0,30}(model|actor|intelligence|detection)), no real dossier in the
# current vault has a genuine space- or defense-industry posting with
# fetched content to build an equally evidence-based replacement pattern
# from (Varda Space Industries/Astranis postings never reached the fetch
# stage — they lost the debate first, per the same audit's Task 4 finding).
# Dropped rather than guessed at a plausible-looking pattern with no
# citation; 'aerospace'/'satellite'/'astro' below still catch genuine
# space-adjacent postings by company/title. Add 'space'/'defense' back with
# a real citation if a genuine live false-negative ever surfaces.
#
# Company hints added 2026-08-23 (dossier audit, Task 7 (a)#4): each of
# these companies had a real dossier pass stage2_confirm unconditionally
# despite genuinely non-technical content (Excel/PowerPoint/BI/consulting
# work, zero real programming), because none of their industries hit any
# existing hint word — KeyBank "Data Intern - Key Technology & Services -
# Data Track" (matched classify.py on a bare "Vulnerability" team-name
# mention), FTI Consulting "Technology Intern" x2 (matched on "Cybersecurity"
# inside a preferred-majors list; real duties are e-discovery/digital-
# forensics consulting), Truist Bank "Technology and Operations Intern -
# Data" (same "Cybersecurity"-in-majors-list pattern), Vertiv (Product
# Management/Planning Analytics/Sales Data Analytics/Thermal Application
# Engineer interns — pure BI/PM, Excel/PowerPoint only), UHY "Data
# Operations Intern" (audit support, Excel only), CNO Financial Group
# "Reporting Analyst Intern" (requirements-gathering/testing-triage, no
# coding), Dimensional Fund Advisors (its "...Data and Tools..." posting is
# Excel-only — verified its sibling "...Operations Insights..." posting
# still passes on real "SQL, Python" content, so gating the whole company is
# safe), Continental Resources "Geoscience Intern" (Excel-only geology role
# — verified the company's other posting, "Data Analyst Intern", still
# passes on real "SQL, R, Python" content). Walleye Capital is deliberately
# NOT company-gated: verified 5 of its 6 other real dossiers pass on real
# signal (Python/unit-test mentions), but "Investment Data Science Intern"
# has none in its fetched content despite being a genuine role — gating the
# whole company would have wrongly failed it, so only its one confirmed-bad
# sibling is caught below by title phrase instead.
_ADJACENT_FIELD_COMPANY_HINT_RE = re.compile(
    r"\b(aerospace|robotics|astro|satellite|automotive|firmware"
    r"|embedded|hardware|chemical|industrial|plant operations|\bplc\b|\bdcs\b|\bscada\b"
    r"|fti consulting|truist|vertiv|\buhy\b|cno financial|dimensional fund"
    r"|keybank|continental resources|finance\s*&\s*accounting|finance and accounting)\b", re.I,
)

# Real content signals confirmed against live vault dossiers 2026-07-26: Bosch
# "Autonomous Driving – Internship in ML" (Python, data pipelines, model
# training, robotics test framework built in software) and Magna "R&D-
# Computer Vision Engineering Intern" (Python, TensorFlow/PyTorch, ML data
# pipeline, cloud platforms) both pass on these signals despite being
# automotive/hardware companies. Jane Street's "Hardware Engineer (FPGA/ASIC)
# Intern" passes on "programming language"/"software" signals despite being a
# genuine hardware role.
_SOFTWARE_CONTENT_SIGNAL_RE = re.compile(
    r"\b(python|java|c\+\+|rust|typescript|javascript|ocaml|api|apis|rest api"
    r"|software (development|engineering)|programming language|data pipeline"
    r"|machine learning|deep learning|tensorflow|pytorch|full.?stack|backend"
    r"|frontend|front.end|database|\bsql\b|\bgit\b|ci/cd|microservice"
    r"|algorithm|codebase|debug|unit test|source code)\b", re.I,
)


def stage2_confirm(title: str, company: str, posting_content: str) -> bool:
    """Called only when posting_content is non-empty. True = passes (either
    not adjacent-field at all, or adjacent-field AND content shows real
    software work). False = adjacent-field with no software signal in the
    actual content — genuinely non-technical despite passing stage 1 (e.g. a
    hardware-manufacturing floor role at a space company).

    The hint check also scans posting_content, not just title+company: real
    bug, Mosaic Company's "Operations & Automation Engineering Co-op/Intern"
    (2026-07-29) — its chemical-plant/PLC-DCS-SCADA signal appears only in
    the fetched content ("Bachelor's degree in Chemical Engineering",
    "PLC, DCS, and SCADA control systems"), never in the title or company
    name, so a title+company-only hint check never routed it through the
    software-signal confirmation below at all."""
    if not _ADJACENT_FIELD_COMPANY_HINT_RE.search(f"{title} {company} {posting_content}"):
        return True
    return bool(_SOFTWARE_CONTENT_SIGNAL_RE.search(posting_content))
