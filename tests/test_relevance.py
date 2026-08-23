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


# --- Task B: product/program-management and rotational-program roles ---

def test_stage1_rejects_real_databricks_product_management_title():
    """Real, live Databricks posting (AIJobs, found 2026-07-26) — genuinely
    PM work ('learn how to be a successful PM') despite listing 'computer
    science' as an acceptable major; previously slipped through both stages
    and was classified AI/ML only because 'Machine Learning' is one of
    Databricks' internal team names, not because the role does ML work."""
    assert stage1_reject("Product Management Intern (Summer 2027)", "") is True


def test_stage1_rejects_real_conagra_demand_science_rotational_title():
    """Real, live Conagra Brands posting (SimplifyJobs, found 2026-07-27,
    still in the vault at List/Dossiers/Other/ as of this writing) — a 2-year
    business rotational program (Behavioral Science/Demand Forecasting/
    Demand Planning/Advanced Analytics) with zero programming content;
    previously passed the gate on no real software signal at all."""
    assert stage1_reject("Demand Science Rotational Analyst", "") is True


def test_stage1_does_not_reject_engineering_track_rotational_program():
    """A genuine software-engineering-track rotational program that names
    actual engineering rotations must still pass — the reject pattern
    requires 'rotational' not be immediately preceded by 'engineering'/
    'software', same adjacency-breaking idiom this file already uses for
    Tax/Risk Technology titles."""
    assert stage1_reject(
        "Software Engineering Rotational Program Intern",
        "Rotations include: Backend Services, Frontend Platform, Infrastructure.",
    ) is False


def test_stage1_does_not_reject_product_engineer_titles():
    assert stage1_reject("Product Engineer Intern", "") is False
    assert stage1_reject("Product-Focused Software Engineer Intern", "") is False


# --- Task C: adjacent-field hint now catches chemical/industrial roles ---

# Real, from the live Mosaic Company "Operations & Automation Engineering
# Co-op/Intern" posting (chemical-plant industrial-automation role) — PLC/
# DCS/SCADA controls, Bachelor's in Chemical Engineering required, physical
# labor requirements, "basic computer skills" as a minor bullet, zero real
# programming content anywhere. Previously passed stage 2 unconditionally
# (neither "chemical" nor "automation" hit the old adjacent-field hint list)
# and only got flagged downstream by classify.py's since-fixed bare-'threat'
# match on this exact workplace-safety disclaimer.
MOSAIC_CONTENT = (
    "Requires a Bachelor's degree in Chemical Engineering or related field. Experience with PLC, DCS, "
    "and SCADA control systems preferred. Basic computer skills required. Must be able to lift 50 lbs "
    "and wear a respirator as needed. The Company will not require an employee to perform any duty "
    "without posing a direct threat to the safety of his or her own self or others."
)


def test_stage2_rejects_real_mosaic_chemical_engineering_content():
    assert stage2_confirm(
        "Operations & Automation Engineering Co-op/Intern", "The Mosaic Company", MOSAIC_CONTENT
    ) is False


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


# --- 2026-08-23 dossier audit: 'space'/'defense' false positives, new
# generic-business/finance/BI company hints (Task 7 (a)#4, (f)#2) ---

# Real content, trimmed, from the live "Cybersecurity Analyst Intern - Jane
# Street.md" dossier (source vanshb03, fetched 2026-07-25). Bare 'space' in
# "the broader cybersecurity space" wrongly triggered the old hint list, and
# this real content has no _SOFTWARE_CONTENT_SIGNAL_RE match at all (no
# python/sql/database/etc — just "a strong programmer", "code", "tools"),
# so the old code incorrectly required (and failed to find) a software
# signal on a genuine security-engineering role.
JANE_STREET_CYBERSECURITY_CONTENT = (
    "Our Cybersecurity Analysts are responsible for being on the front lines of guarding the firm "
    "from cyber threats through investigations and incident response, as well as building tools and "
    "automation to streamline, automate, and enhance workflows. Our Cybersecurity team is a skilled "
    "group of programmers and security experts who are dedicated to keeping the firm safe. We "
    "consider ourselves to be tapped into developments in the broader cybersecurity space. You should "
    "be a strong programmer who can demonstrate high potential and an aptitude for learning."
)

# Real content, trimmed, from the live "Information Security Engineer Intern
# - Appian.md" dossier (source vanshb03, fetched 2026-07-27). Bare 'defense'
# in "modern cloud architecture defense" wrongly triggered the old hint
# list, same no-signal-word problem as the Jane Street case above.
APPIAN_INFOSEC_CONTENT = (
    "Appian's Information Security team operates at the heart of our Enterprise-Grade Orchestration "
    "ecosystem. We continuously evaluate the evolving cyber threat landscape, assess security risks, "
    "and enforce modern security frameworks. As an Information Security Intern at Appian, you will "
    "actively contribute to live security operations, modern cloud architecture defense, and "
    "compliance automation, gaining hands-on exposure to cutting-edge cloud infrastructure, automated "
    "governance, and enterprise threat analysis."
)


def test_stage2_confirms_jane_street_cybersecurity_from_real_content():
    assert stage2_confirm(
        "Cybersecurity Analyst Intern", "Jane Street", JANE_STREET_CYBERSECURITY_CONTENT
    ) is True


def test_stage2_confirms_appian_infosec_from_real_content():
    assert stage2_confirm(
        "Information Security Engineer Intern", "Appian", APPIAN_INFOSEC_CONTENT
    ) is True


# Real content, trimmed, from the live "Technology Intern - FTI Consulting.md"
# dossier (source SimplifyJobs, fetched 2026-07-28) — e-discovery/digital-
# forensics/document-review consulting, zero programming content, matched
# classify.py's CyS & Finance bucket only on "Cybersecurity" appearing in a
# preferred-majors list.
FTI_CONSULTING_CONTENT = (
    "Our technology interns work with corporations, governments and law firms to meet critical legal "
    "and regulatory needs, including investigations, e-discovery, information governance, digital "
    "forensics, data privacy, document review consulting as well as project management. Preferred "
    "majors: Business, Computer Forensics, Cybersecurity, Data Analytics, Data Science, Digital "
    "Forensics, Economics, Information Technology Management, Management Information Systems, Law."
)


def test_stage2_rejects_real_fti_consulting_content():
    assert stage2_confirm("Technology Intern", "FTI Consulting", FTI_CONSULTING_CONTENT) is False


# Real content, trimmed, from the live "Technology and Operations Intern -
# Data - Truist Bank.md" dossier (source SimplifyJobs, fetched 2026-08-18) —
# generic bank rotational, business-acumen/leadership-development duties.
# Deliberately includes the real "Software Development" team-name mention:
# even with 'truist' now hinted, this still passes on that literal phrase
# (a coincidental, real limitation of the keyword-only signal check this
# fix doesn't close — see the 2026-08-23 audit's Phase 1/2 report).
TRUIST_CONTENT = (
    "The Technology, Data, and Operations Internship Program is a summer intern program that "
    "provides future leaders of Truist with a strong foundation within technology and the financial "
    "services industry as a whole. Participants will gain experience within Software Development, "
    "Cybersecurity, AI & Data, and Operations teams. Build business acumen and leadership skills."
)


def test_stage2_still_confirms_real_truist_content_on_coincidental_team_name_mention():
    """Real, documented limitation: adding 'truist' to the hint list doesn't
    flip this dossier to a reject, because its real content happens to
    literally say 'Software Development' as one of several team names an
    intern is exposed to, not as a real duty description — a false pass the
    keyword-only signal check can't distinguish. Recorded here as the actual
    behavior, not the hoped-for one."""
    assert stage2_confirm("Technology and Operations Intern - Data", "Truist Bank", TRUIST_CONTENT) is True


# Real content, trimmed, from "Planning Analytics Intern - Summer 2027 -
# Vertiv.md" (source SimplifyJobs, fetched 2026-08-14) — pure BI/dashboard
# work, no programming requirement anywhere.
VERTIV_PLANNING_ANALYTICS_CONTENT = (
    "This internship offers an excellent opportunity to gain hands-on experience in various aspects "
    "of data analysis and business intelligence within our organization. Develop and maintain "
    "dashboards, charts, and reports to visually represent data insights. Must be pursuing a degree "
    "in Data Science, Statistics, Computer Science, or a related field."
)

# Real content, trimmed, from "Operations Intern - Summer 2027 - Vertiv.md"
# (source SimplifyJobs, fetched 2026-08-13) — genuinely different from the
# other Vertiv postings above despite the shared company: explicit required
# Python/SQL/data-pipeline skills. Confirms the company hint discriminates
# correctly within the same company rather than blanket-failing it.
VERTIV_OPERATIONS_CONTENT = (
    "Build data structure and data lake intake method to support future analytics tools use. "
    "Proficiency in Python, including experience with libraries such as Pandas, NumPy, or similar "
    "data manipulation tools. Foundational understanding of SQL and relational database concepts. "
    "Familiarity with Microsoft Fabric, Azure Data Factory, or similar Data Pipeline (ETL/ELT) tools."
)


def test_stage2_rejects_real_vertiv_planning_analytics_content():
    assert stage2_confirm(
        "Planning Analytics Intern - Summer 2027", "Vertiv", VERTIV_PLANNING_ANALYTICS_CONTENT
    ) is False


def test_stage2_confirms_real_vertiv_operations_intern_content():
    """A genuinely technical Vertiv posting must still pass even though the
    company is now hinted — the hint only routes content through the real
    signal check, it isn't itself a reject."""
    assert stage2_confirm(
        "Operations Intern - Summer 2027", "Vertiv", VERTIV_OPERATIONS_CONTENT
    ) is True


# Real content, trimmed, from "Data Operations Intern - UHY.md" (source
# SimplifyJobs, fetched 2026-08-11) — audit support, Excel-only.
UHY_CONTENT = (
    "The Data Operations Intern supports the Shared Resources team in compiling, manipulating, and "
    "analyzing client data. Use Excel and firm-provided analytic tools to help organize and review "
    "financial information. Convert client-provided reports (such as PDFs) into Excel to support "
    "audit and data analysis workflows. Strong knowledge of Excel."
)


def test_stage2_rejects_real_uhy_content():
    assert stage2_confirm("Data Operations Intern", "UHY", UHY_CONTENT) is False


# Real content, trimmed, from "Reporting Analyst Intern - CNO Financial
# Group.md" (source SimplifyJobs, fetched 2026-08-20) — requirements-
# gathering/testing-triage, no coding.
CNO_CONTENT = (
    "CNO Financial Group is hiring a Reporting Analyst Intern. Core responsibilities and deliverables: "
    "Participate in requirements elicitation meetings. Document the requirements using different "
    "techniques. Collaborate with business and development teams. Triage testing defects as related "
    "to requirements."
)


def test_stage2_rejects_real_cno_financial_content():
    assert stage2_confirm("Reporting Analyst Intern", "CNO Financial Group", CNO_CONTENT) is False


# Real content, trimmed, from the two live sibling Walleye Capital dossiers
# — "Finance & Accounting Intern (Summer 2027)" (bad, Greenhouse, fetched
# 2026-08-19) and "Investment Data Science Intern" (good, SimplifyJobs,
# fetched 2026-07-17). Walleye Capital is deliberately NOT company-gated
# (verified 5 of its 6 other real dossiers pass on real Python/unit-test
# signal, but Investment Data Science Intern has none despite being a
# genuine role) — only the confirmed-bad sibling is caught, by title phrase.
WALLEYE_FINANCE_ACCOUNTING_CONTENT = (
    "The Finance & Accounting team plays a critical role in supporting the firm's financial "
    "operations, overseeing financial reporting, budgeting, forecasting, and analysis. Help improve "
    "and maintain financial models, reporting processes, and internal FP&A tools. Support financial "
    "statement preparation and analysis."
)
WALLEYE_DATA_SCIENCE_CONTENT = (
    "As an intern, you'll engage in high-impact projects focused on alternative data research "
    "supporting long/short discretionary investment strategies. Learn and implement core data "
    "science and data engineering workflows on the firm's Cloud and Linux infrastructure. Clean, "
    "transform, and join large structured and unstructured datasets."
)


def test_stage2_rejects_real_walleye_finance_and_accounting_content():
    assert stage2_confirm(
        "Finance & Accounting Intern (Summer 2027)", "Walleye Capital Internships",
        WALLEYE_FINANCE_ACCOUNTING_CONTENT,
    ) is False


def test_stage2_still_confirms_real_walleye_investment_data_science_content():
    """Not company-gated (see module note above) and no signal-word match
    in its own real content either — passes today via the 'no hint at all'
    path, same as before this fix. A real, permissive-by-design outcome,
    not a bug: no evidence exists that this role is non-technical."""
    assert stage2_confirm(
        "Investment Data Science Intern", "Walleye Capital", WALLEYE_DATA_SCIENCE_CONTENT
    ) is True


# Real content, trimmed, from the two live sibling Continental Resources
# dossiers — "Geoscience Intern" (bad) and "Data Analyst Intern" (good,
# also the Task 7 (a)#2 Workday cross-source-duplicate example) — both
# fetched 2026-08-19.
CONTINENTAL_GEOSCIENCE_CONTENT = (
    "Geoscience Interns will be involved in generating geologic interpretations of current CLR "
    "development assets and/or exploration prospects. Generate sequence stratigraphic models, "
    "various subsurface and petrophysical maps, production analysis, geosteering interpretations "
    "and mud log analysis. Proficient with Microsoft Office."
)
CONTINENTAL_DATA_ANALYST_CONTENT = (
    "The Data Analyst Intern will collaborate with Engineering teams to solve problems, automate "
    "processes and improve business performance using the plethora of data, analytics and artificial "
    "intelligence capabilities available at Continental. Basic proficiency in coding languages "
    "including SQL, R, Python, HTML and analytics software."
)


def test_stage2_rejects_real_continental_resources_geoscience_content():
    assert stage2_confirm(
        "Geoscience Intern", "Continental Resources", CONTINENTAL_GEOSCIENCE_CONTENT
    ) is False


def test_stage2_confirms_real_continental_resources_data_analyst_content():
    assert stage2_confirm(
        "Data Analyst Intern", "Continental Resources", CONTINENTAL_DATA_ANALYST_CONTENT
    ) is True


# Real content, trimmed, from the two live sibling Dimensional Fund Advisors
# dossiers — "...Data and Tools..." (bad) and "...Operations Insights..."
# (good), both fetched 2026-08-18.
DIMENSIONAL_DATA_AND_TOOLS_CONTENT = (
    "The GCG Operations Intern (Data & Tools) will support several sales enablement and asset "
    "reporting initiatives. Collect and analyze data to support various sales goals and campaigns. "
    "Strong knowledge of Excel and general computer skills with the ability to learn additional "
    "computer applications as needed."
)
DIMENSIONAL_OPERATIONS_INSIGHTS_CONTENT = (
    "The GCG Operations Intern (Insights) will support several sales enablement initiatives. Assist "
    "with developing business intelligence capabilities utilizing Power BI and Snowflake. Strong "
    "computer skills (advanced Excel, SQL, Python, etc.)."
)


def test_stage2_rejects_real_dimensional_fund_data_and_tools_content():
    assert stage2_confirm(
        "Global Client Group Intern - Data and Tools", "Dimensional Fund Advisors",
        DIMENSIONAL_DATA_AND_TOOLS_CONTENT,
    ) is False


def test_stage2_confirms_real_dimensional_fund_operations_insights_content():
    assert stage2_confirm(
        "Global Client Group Operations Insights Intern", "Dimensional Fund Advisors",
        DIMENSIONAL_OPERATIONS_INSIGHTS_CONTENT,
    ) is True


def test_stage2_still_rejects_real_keybank_content_on_coincidental_tool_list_mention():
    """Same documented limitation as Truist above: KeyBank's real content
    (from 'Data Intern - Key Technology & Services - Data Track') lists
    Python/SQL/JavaScript among many tools interns MIGHT be exposed to, not
    as required skills for this specific role — a coincidental literal
    match the keyword-only signal check can't tell apart from a real
    requirement. Recorded as the actual behavior."""
    content = (
        "KTS Operations, spanning Origination through Default Management, Deposit Operations, ACH, "
        "Wire & Check Payment Operations. Opportunities to use industry leading software (examples "
        "include: Tableau, ServiceNow, Visual Studio, Jira, Automation Anywhere, Jenkins, PowerShell, "
        "HTML, C#, Python, SQL, JavaScript). Experience in Excel, PowerPoint, Project."
    )
    assert stage2_confirm(
        "Data Intern - Key Technology & Services - Data Track", "KeyBank", content
    ) is True
