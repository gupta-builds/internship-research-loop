"""core/classify.py — real examples throughout, same fixtures as test_relevance.py
where applicable."""
import json
from pathlib import Path

import pytest

from core.classify import classification_callout, classify
from ingestion.normalize import normalize_vanshb03, normalize_zshah101

FIXTURES = Path(__file__).parent / "fixtures"

# Same real content used in test_relevance.py — Bosch dossier
# zshah101-smartrecruiters-boschgroup-744000139649345.md.
BOSCH_CONTENT = (
    "We are looking for an accomplished student in the ML space with strong technical skills to work "
    "with us on the design, implementation, training and roll-out the next generation of AI-enabled "
    "robotics test system, a core component of the realization of self-driving vehicles. "
    "Strong coding skills in python. Hands-on experience with Pytorch for model development."
)

# Magna dossier zshah101-workday-magna-job-...-r00253444-1.md.
MAGNA_CONTENT = (
    "Knowledge of Python programming languages is expected. Create data/machine learning pipeline in "
    "one of the popular cloud platforms. Familiarity with Deep Learning (TensorFlow or PyTorch) required."
)


def test_classify_ai_ml_from_real_bosch_content():
    bucket, signal = classify("Autonomous Driving – Internship in Machine Learning", "Data & ML/AI", BOSCH_CONTENT)
    assert bucket == "AI/ML"
    assert signal


def test_classify_ai_ml_from_real_magna_content():
    bucket, _ = classify("R&D- Computer Vision Engineering Intern", "Data & ML/AI", MAGNA_CONTENT)
    assert bucket == "AI/ML"


def test_classify_fullstack_from_real_vanshb03_fixture():
    """Real committed fixture: Poshmark 'Cloud Platform Engineer Intern,
    Growth' (tests/fixtures/vanshb03.json) — no raw_text on this source, so
    classification runs on title alone; 'platform engineer' is the
    fullstack signal."""
    raw = json.loads((FIXTURES / "vanshb03.json").read_text())
    entry = next(r for r in raw if "Cloud Platform" in r["title"])
    listing = normalize_vanshb03(entry)
    bucket, signal = classify(listing.title, listing.category, "")
    assert bucket == "Fullstack"
    assert "platform engineer" in signal.lower()


def test_classify_other_from_real_zshah101_fixture():
    """Real committed fixture: plain 'Software Engineer Intern', category
    Software (tests/fixtures/zshah101.json) — no AI/security/fullstack
    signal anywhere in title or category."""
    raw = json.loads((FIXTURES / "zshah101.json").read_text())
    entry = next(r for r in raw if r["title"] == "Software Engineer Intern" and r["category"] == "Software")
    listing = normalize_zshah101(entry)
    bucket, signal = classify(listing.title, listing.category, "")
    assert bucket == "Other"
    assert signal == ""


def test_classification_callout_format_has_no_numeric_label():
    callout = classification_callout("AI/ML", "rag")
    assert callout.startswith("> [!NOTE] AI/ML:")
    import re
    assert not re.search(r"priority\s*\d", callout, re.I)


def test_classification_callout_other_bucket_has_no_signal_but_still_no_number():
    callout = classification_callout("Other", "")
    assert callout.startswith("> [!NOTE] Other:")
    assert "Priority" not in callout


# --- Task C: bare 'threat' narrowed to require security context ---

def test_classify_does_not_match_bare_threat_real_mosaic_safety_disclaimer():
    """Real false positive: Mosaic Company 'Operations & Automation
    Engineering Co-op/Intern' (chemical-plant PLC/DCS/SCADA role, zero
    cybersecurity content) matched bare 'threat' on a workplace-safety
    disclaimer, nothing to do with cybersecurity."""
    content = (
        "The Company will not require an employee to perform any duty without posing a direct threat "
        "to the safety of his or her own self or others."
    )
    bucket, signal = classify("Operations & Automation Engineering Co-op/Intern", "", content)
    assert bucket != "CyS & Finance"
    assert signal != "threat"


def test_classify_still_matches_genuine_threat_intelligence_content():
    bucket, signal = classify("Security Engineering Intern", "", "You'll work on threat intelligence and detection.")
    assert bucket == "CyS & Finance"
    assert "threat" in signal.lower()
