"""Layer 2.5b — priority-bucket classification for listings that already
passed core/relevance.py's gate. Deterministic keyword matching against
title + category + fetched posting content (empty content degrades
gracefully — title/category alone still register). Zero-LLM, same style as
core/filter.py and core/relevance.py.

Exactly one bucket, checked in this order (first match wins — a posting can
show signals for more than one, e.g. AI infra at a fintech should read
AI/ML, not CyS & Finance):
  1. AI/ML       — LLM, RAG, agents, ML infra, applied AI, deep learning
  2. CyS & Finance — security or finance-adjacent software engineering
  3. Fullstack   — product/frontend/backend/systems engineering
  4. Other       — genuine software engineering (relevance gate already
                   confirmed this), matching none of the above
"""
import re

BUCKET_FOLDERS = {
    "AI/ML": "1 - AI & ML",
    "Fullstack": "2 - Fullstack",
    "CyS & Finance": "3 - CyS & Finance",
    "Other": "Other",
}

# Real examples: Bosch "Autonomous Driving – Internship in ML" (model
# training, AI-enabled robotics test system, PyTorch) and Magna "R&D-
# Computer Vision Engineering Intern" (TensorFlow or PyTorch, ML data
# pipeline) both match here despite being automotive companies.
_AI_ML_RE = re.compile(
    r"\b(llm|large language models?|\brag\b|retrieval.augmented|agentic|ai agent"
    r"|machine learning|deep learning|ml infra|applied ai|generative ai"
    r"|computer vision|\bnlp\b|natural language|embeddings?|pytorch|tensorflow"
    r"|neural network|data scientist|ml engineer|ai engineer|ai.enabled)\b", re.I,
)
# 'threat' narrowed 2026-07-29: real false positive, Mosaic Company
# "Operations & Automation Engineering Co-op/Intern" (chemical-plant
# PLC/DCS/SCADA role, zero cybersecurity content) matched bare 'threat' on a
# workplace-safety disclaimer ("without posing a direct threat to the safety
# of his or her own self"). Requiring co-occurrence with a real
# security-context word within 30 chars catches genuine cybersecurity usage
# ("threat model", "threat actor", "threat intelligence", "threat detection")
# without matching safety-boilerplate/weather/insider-threat-to-unrelated-
# things mentions of the bare word.
_CYS_FINANCE_RE = re.compile(
    r"\b(security engineer|cybersecurity|application security|appsec"
    r"|penetration test|infosec|threat.{0,30}(model|actor|intelligence|detection)|vulnerability"
    r"|quant(itative)? developer"
    r"|quantitative (research|trading)|trading systems?|fintech|risk engine"
    r"|payments? (engineer|infrastructure)|blockchain|crypto|defi)\b", re.I,
)
_FULLSTACK_RE = re.compile(
    r"\b(full.?stack|frontend|front.end|backend|back.end|\breact\b|next\.?js"
    r"|web (developer|engineer)|product engineer|api (design|development)"
    r"|systems? engineer|infrastructure engineer|platform engineer|devops"
    r"|mobile (developer|engineer)|\bios\b|\bandroid\b)\b", re.I,
)


def classify(title: str, category: str, posting_content: str) -> tuple:
    """Returns (bucket_name, signal) — signal is the specific real phrase
    that drove the classification (empty string for the Other bucket, since
    there's nothing bucket-specific to point at)."""
    haystack = f"{title} {category} {posting_content}"
    for bucket, pattern in (("AI/ML", _AI_ML_RE), ("CyS & Finance", _CYS_FINANCE_RE), ("Fullstack", _FULLSTACK_RE)):
        m = pattern.search(haystack)
        if m:
            return bucket, m.group(0)
    return "Other", ""


def classification_callout(bucket: str, signal: str) -> str:
    """No numeric label ('Priority 1/2/3') — the folder location already
    encodes the category; a number in the callout text was explicitly
    rejected in design review."""
    if not signal:
        return f"> [!NOTE] {bucket}: genuine software engineering role, no bucket-specific signal matched."
    return f'> [!NOTE] {bucket}: matched on "{signal}".'
