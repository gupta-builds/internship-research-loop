"""core/relevance.py's two-stage gate — real examples throughout, no
synthetic non-software/adjacent-field text. Stage-1 titles confirmed live
against seeded Greenhouse boards 2026-07-26 (FC Cincinnati, Walleye Capital);
stage-2 content copied verbatim from real vault dossiers already fetched by
this pipeline."""
import json
from pathlib import Path

import pytest

from core.relevance import stage1_reject, stage2_confirm
from ingestion.normalize import normalize_simplify

FIXTURES = Path(__file__).parent / "fixtures"


def _simplify_titled(title_substr):
    raw = json.loads((FIXTURES / "simplifyjobs.json").read_text())
    return next(r for r in raw if title_substr.lower() in r["title"].lower())


# --- stage1_reject ---

def test_stage1_rejects_real_academy_performance_analyst_title():
    """Real, live FC Cincinnati Greenhouse posting (fccincinnati board,
    2026-07-26) — pure sports video coding/KPI labeling, the task's named
    'sports performance analytics' reject example."""
    assert stage1_reject("Academy Performance Analyst Intern - Academy Performance Analysis", "") is True


def test_stage1_rejects_real_investor_relations_title():
    """Real, live Walleye Capital Greenhouse posting (walleyecapital-external-students board, 2026-07-26)."""
    assert stage1_reject("Investor Relations Intern (Summer 2027)", "") is True


def test_stage1_does_not_reject_real_tax_technology_intern():
    """Real committed fixture (tests/fixtures/simplifyjobs.json) — Grant
    Thornton 'Tax Technology Intern', category AI/ML/Data, genuinely
    technology-consulting content. Must NOT be caught by the bare-'tax'
    reject — the non-software noun ('associate'/'preparer'/'accountant')
    must be adjacent to 'tax', not a 'Technology' qualifier."""
    raw = _simplify_titled("Tax Technology Intern")
    listing = normalize_simplify(raw)
    assert stage1_reject(listing.title, "") is False


def test_stage1_does_not_reject_real_risk_technology_analyst_title():
    """Real, live Walleye Capital Greenhouse posting — 'Risk Technology
    Analyst Intern' must not match the 'risk analyst' pattern since
    'Technology' breaks the adjacency, same nuance as Tax Technology above."""
    assert stage1_reject("Risk Technology Analyst Intern (Summer 2027)", "") is False


def test_stage1_does_not_reject_plain_software_titles():
    assert stage1_reject("Software Engineer Intern", "") is False
    assert stage1_reject("Machine Learning Engineer Intern", "") is False


# --- stage2_confirm ---

# Real content, copied verbatim from the vault dossier
# zshah101-smartrecruiters-boschgroup-744000139649345.md (Bosch "Autonomous
# Driving – Internship in Machine Learning", fetched 2026-07-25).
BOSCH_CONTENT = (
    "We are looking for an accomplished student in the ML space with strong technical skills to work "
    "with us on the design, implementation, training and roll-out the next generation of AI-enabled "
    "robotics test system, a core component of the realization of self-driving vehicles. "
    "Strong coding skills in python. Hands-on experience with Pytorch for model development, training "
    "and testing in a Linux environment. Experience with state-of-the-art model architectures, "
    "including transformers, CNNs, LSTMs, RAG…"
)

# Real content, copied verbatim from the vault dossier
# zshah101-workday-magna-job-troy-michigan-us-r-d-computer-vision-engineering-intern-r00253444-1.md
# (Magna "R&D- Computer Vision Engineering Intern", fetched 2026-07-25).
MAGNA_CONTENT = (
    "Knowledge of Python programming languages is expected. Additionally, knowledge of relevant "
    "mathematics, statistics, machine learning techniques, data pipelines, and software development "
    "workflows is essential. Create data/machine learning pipeline in one of the popular cloud "
    "platforms. Familiarity with Deep Learning (TensorFlow or PyTorch) required."
)

# Real content, copied verbatim from the vault dossier
# vanshb03-c6e7a7e2-7ba2-4e42-b50c-2b0b80496640.md (Jane Street "Hardware
# Engineer (FPGA/ASIC) Intern", fetched 2026-07-25).
JANE_STREET_HARDWARE_CONTENT = (
    "you'll learn how we use tools to make programming faster, more pleasant, and more reliable. "
    "We use Hardcaml, an OCaml library for succinctly describing hardware in RTL. You should be: "
    "Comfortable with a software programming language. Experienced with a Hardware Description "
    "(or Construction) language (VHDL, Verilog, Chisel, Pymtl, or other)."
)


def test_stage2_confirms_bosch_ml_internship_from_real_content():
    assert stage2_confirm(
        "Autonomous Driving – Internship in Machine Learning", "Robert Bosch Venture Capital", BOSCH_CONTENT
    ) is True


def test_stage2_confirms_magna_computer_vision_from_real_content():
    assert stage2_confirm(
        "R&D- Computer Vision Engineering Intern", "Magna International", MAGNA_CONTENT
    ) is True


def test_stage2_confirms_jane_street_hardware_role_from_real_content():
    """Hardware is not auto-excluded — Jane Street's FPGA/ASIC internship is
    a real hardware role that passes on genuine software/PL content."""
    assert stage2_confirm(
        "Hardware Engineer (FPGA/ASIC) Intern", "Jane Street", JANE_STREET_HARDWARE_CONTENT
    ) is True


def test_stage2_rejects_adjacent_field_with_no_software_signal():
    """A hardware-adjacent title/company with content that never mentions
    any real software work — e.g. a pure manufacturing-floor internship."""
    content = (
        "You will assist on the production floor with component assembly, quality inspection, and "
        "packaging of finished hardware units. Prior manufacturing or mechanical assembly experience "
        "preferred. Must be able to lift 30 lbs and stand for extended periods."
    )
    assert stage2_confirm("Hardware Assembly Intern", "Acme Aerospace Manufacturing", content) is False


def test_stage2_passes_through_non_adjacent_titles_without_content_check():
    """No adjacent-field hint at all — already cleared stage 1, content
    (even empty) never gates it."""
    assert stage2_confirm("Software Engineer Intern", "Acme Corp", "") is True
