"""core/company_registry.py — the shared company-fact lookup used by
core/classify.py, core/debate.py, and core/relevance.py."""
from core.company_registry import ADJACENT_FIELD_COMPANIES, TIER_RANK, is_quant_finance_company

# The 8 companies with real dossiers confirmed (2026-09-06, direct
# mcp__jarvis__vault_list) in BOTH "1 - AI & ML" and "3 - CyS & Finance" —
# Optiver/IMC/Chicago Trading Company cited in the vault's own "Dossier
# Corrections" note §2; the other 5 found directly, not previously cited.
_QUANT_FINANCE_NAMES = (
    "Optiver", "IMC", "Chicago Trading Company", "Jane Street", "Jump Trading",
    "Aquatic Capital Management", "Walleye Capital", "Millennium",
)


def test_is_quant_finance_company_true_for_all_8_confirmed_companies():
    for name in _QUANT_FINANCE_NAMES:
        assert is_quant_finance_company(name), name


def test_is_quant_finance_company_punctuation_insensitive():
    """Real dossiers store company as 'Optiver ' (trailing space); other
    sources vary punctuation the same way core.identity.company_matches_
    preference already tolerates ('D.E. Shaw' vs 'DE Shaw')."""
    assert is_quant_finance_company("Optiver ")
    assert is_quant_finance_company("jane street")


def test_is_quant_finance_company_false_for_unrelated_company():
    assert not is_quant_finance_company("Random Startup Inc")


def test_adjacent_field_companies_unchanged_from_relevance_py_original():
    assert set(ADJACENT_FIELD_COMPANIES) == {
        "fti consulting", "truist", "vertiv", "uhy", "cno financial",
        "dimensional fund", "keybank", "continental resources",
    }


def test_tier_rank_not_re_tiered():
    """Pins the 'don't re-tier the 11 preferred_companies' decision — only
    one grade exists, same as the flat dict this replaced."""
    assert TIER_RANK == {"high": 0}
