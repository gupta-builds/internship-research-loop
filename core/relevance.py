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
_STAGE1_REJECT_RE = re.compile(
    r"\b(financial analyst|risk analyst|performance analyst"
    r"|tax (associate|preparer|accountant)"
    r"|investor relations"
    r"|sports performance (analyst|analytics)|academy performance (analyst|analysis)"
    r"|human resources intern|hr intern|marketing intern|business development intern)\b",
    re.I,
)


def stage1_reject(title: str, raw_text: str) -> bool:
    """True if this listing's title/raw_text is unambiguously non-software —
    reject without ever fetching the page."""
    return bool(_STAGE1_REJECT_RE.search(f"{title} {raw_text}"))


# Adjacent-field company/title hint — NOT a reject signal on its own (Jane
# Street "Hardware Engineer (FPGA/ASIC) Intern" and Bosch/Magna's automotive
# ML roles all pass real content checks below). Only postings that hit this
# hint need their fetched content checked at all; everything else already
# cleared stage 1 and passes through unconditionally.
_ADJACENT_FIELD_COMPANY_HINT_RE = re.compile(
    r"\b(space|aerospace|robotics|astro|satellite|defense|automotive|firmware"
    r"|embedded|hardware)\b", re.I,
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
    software work). False = adjacent-field company/title with no software
    signal in the actual content — genuinely non-technical despite passing
    stage 1 (e.g. a hardware-manufacturing floor role at a space company)."""
    if not _ADJACENT_FIELD_COMPANY_HINT_RE.search(f"{title} {company}"):
        return True
    return bool(_SOFTWARE_CONTENT_SIGNAL_RE.search(posting_content))
