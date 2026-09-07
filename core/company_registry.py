"""Single source of truth for company-level facts used by core/classify.py,
core/debate.py, and core/relevance.py — those three files used to hand-
maintain independent company lists that could (and did) drift apart. Data
only: this module makes no eligibility/bucket/tier decisions itself, it just
answers "what's true about this company" for callers to act on.
"""
from core.identity import _norm_company

# Quant-trading/quant-finance firms whose engineering postings are
# finance-adjacent regardless of which keyword classify.py's regexes happen
# to match. Real confirmed vault split (2026-09-06, direct mcp__jarvis__
# vault_list on both '1 - AI & ML' and '3 - CyS & Finance'): each of these
# 8 companies has real dossiers in BOTH folders for the same kind of role
# (e.g. Optiver's "Software Engineer Intern - Optiver.md" in AI/ML vs.
# "Software Engineer Intern (Summer 2027 - Austin) - Optiver.md" in CyS &
# Finance) purely because of which keyword the fetched content tripped.
# Optiver/IMC/Chicago Trading Company were the ones cited in the vault's own
# "Dossier Corrections" note §2; Jane Street/Jump Trading/Aquatic Capital
# Management/Walleye Capital/Millennium were found by directly listing both
# folders — not previously cited anywhere.
_QUANT_FINANCE_COMPANIES = {
    _norm_company(c) for c in (
        "Optiver", "IMC", "Chicago Trading Company",
        "Jane Street", "Jump Trading", "Aquatic Capital Management",
        "Walleye Capital", "Millennium",
    )
}


def is_quant_finance_company(company: str) -> bool:
    return _norm_company(company) in _QUANT_FINANCE_COMPANIES


# Moved verbatim from core/relevance.py's _ADJACENT_FIELD_COMPANY_HINT_RE
# (2026-08-23 dossier audit, Task 7(a)#4) — same 8 companies, same original
# per-company citations, which stay in relevance.py's own comment block
# rather than being duplicated here.
ADJACENT_FIELD_COMPANIES = (
    "fti consulting", "truist", "vertiv", "uhy", "cno financial",
    "dimensional fund", "keybank", "continental resources",
)

# Tier name -> sort rank for core/debate.py's Stage 1 preference comparator.
# Only one grade exists today (every company in core/profile.yaml's
# human-maintained preferred_companies is "high") — this relocates the
# rank-ordering table itself, it does not re-tier any company.
TIER_RANK = {"high": 0}
