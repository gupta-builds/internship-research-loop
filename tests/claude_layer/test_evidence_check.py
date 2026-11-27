"""Tests for .claude/skills/checking-evidence/scripts/evidence_check.py.
Every fixture under fixtures/evidence is synthetic and says so in a comment."""
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".claude/skills/checking-evidence/scripts/evidence_check.py"
FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "evidence"


def check(draft, kind="resume", facts="source.md", *extra):
    """return (exit code, stdout, stderr) of the check on one fixture draft."""
    r = subprocess.run([sys.executable, str(SCRIPT), str(FIX / draft), "--kind", kind,
                        "--facts", str(FIX / facts), *extra], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def tags(out):
    """return the set of finding kinds printed."""
    return {line.split(" [", 1)[1].split("]", 1)[0] for line in out.splitlines() if " [" in line}


#### one failing and one passing fixture per check (Plan, Tests and evaluations)

@pytest.mark.parametrize("draft,facts,kind,needle", [
    ("number-fail.md", "source.md", "number", "40%"),                  # number by value
    ("magnitude-fail.md", "magnitude-source.md", "number", "2.3m"),    # magnitude folded
    ("noun-fail.md", "source.md", "number", "bound to 'intern'"),      # metric bound to its noun
    ("daterange-fail.md", "source.md", "date", "2025-08"),             # range endpoint
    ("section-fail.md", "source.md", "entity", "one source section"),  # parts of two roles mixed
    ("skill-fail.md", "source.md", "skill", "Kubernetes"),             # skill not in the source
    ("gap-fail.md", "source.md", "entity", "Kubernetes"),              # a Logged Gaps line is not a source
    ("url-fail.md", "source.md", "url", "fleet-sim"),                  # repo the source never names
    ("coverage-fail.md", "source.md", "coverage", "Skills"),           # a section it cannot read
])
def test_failing_fixture(draft, facts, kind, needle):
    """failing fixture."""
    code, out, _ = check(draft, facts=facts)
    assert code == 1 and kind in tags(out) and needle in out


@pytest.mark.parametrize("draft", ["number-pass.md", "magnitude-pass.md", "noun-pass.md", "daterange-pass.md",
                                   "section-pass.md", "skill-pass.md", "url-pass.md"])
def test_passing_fixture(draft):
    """passing fixture."""
    code, out, _ = check(draft)
    assert code == 0 and out.startswith("0 finding(s)")


def test_value_on_another_noun_fails():
    # 120 is in the source, but bound to lab reports, not interns
    """value on another noun fails."""
    code, out, _ = check("noun-moved-fail.md")
    assert code == 1 and "bound to 'intern'" in out


def test_range_ends_from_two_roles_fail():
    # Jun 2024 starts one role and Current ends another; the range is in no source section
    """range ends from two roles fail."""
    code, out, _ = check("range-pair-fail.md")
    assert code == 1 and "not as one range" in out


def test_ambiguous_english_words_in_prose_pass():
    # C3 red team case 20: rust, react, go and swift are English words in lowercase prose
    """ambiguous english words in prose pass."""
    code, out, _ = check("redteam-ambiguous-pass.md", "followup")
    assert code == 0, out
    code, out, _ = check("skill-ambiguous-fail.md")
    assert code == 1 and "[skill] Rust" in out                     # in a Skills section it is still checked


#### the posting as a source

def test_posting_never_supplies_a_skill():
    """posting never supplies a skill."""
    code, out, _ = check("posting-resume-fail.md", "cover", "source.md", "--jd", str(FIX / "posting.md"))
    assert code == 1 and "Kafka" in out


def test_posting_supplies_company_and_role_names_for_a_letter():
    """posting supplies company and role names for a letter."""
    code, out, _ = check("posting-letter-pass.md", "cover", "source.md", "--jd", str(FIX / "posting.md"))
    assert code == 0 and "2 by --jd" in out
    code, out, _ = check("posting-letter-pass.md", "cover")
    assert code == 1 and "Northwind Labs" in out                    # without --jd the names are untraced


def test_posting_tool_in_letter_prose_fails():
    """posting tool in letter prose fails."""
    code, out, _ = check("posting-letter-fail.md", "cover", "source.md", "--jd", str(FIX / "posting.md"))
    assert code == 1 and "Kafka" in out


def test_posting_number_needs_a_shared_word_and_noun():
    """posting number needs a shared word and noun."""
    assert check("posting-number-pass.md", "cover", "source.md", "--jd", str(FIX / "posting.md"))[0] == 0
    code, out, _ = check("posting-number-fail.md", "cover", "source.md", "--jd", str(FIX / "posting.md"))
    assert code == 1 and "40 million" in out


#### --allow

def test_allow_file_adds_alias_host_and_term(tmp_path):
    """allow file adds alias host and term."""
    allow = tmp_path / "allow.txt"
    allow.write_text("# synthetic allow list\nkubernetes = kube-ish\nexample.org\n40%\n", encoding="utf-8")
    for draft in ("url-fail.md", "number-fail.md"):
        assert check(draft)[0] == 1                                 # without --allow both fail
    draft = tmp_path / "d.md"
    draft.write_text("<!-- synthetic -->\n- Cut latency by 40% (see example.org/notes).\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(draft), "--kind", "resume", "--facts",
                        str(FIX / "source.md"), "--allow", str(allow)], capture_output=True, text=True)
    assert r.returncode == 0 and "2 accepted by --allow" in r.stdout


def test_allow_alias_is_counted(tmp_path):
    """allow alias is counted."""
    allow = tmp_path / "allow.txt"
    allow.write_text("postgresql = pg\n", encoding="utf-8")
    draft = tmp_path / "d.md"
    draft.write_text("<!-- synthetic -->\n## Skills\n- Python, PG\n", encoding="utf-8")
    base = [sys.executable, str(SCRIPT), str(draft), "--kind", "resume", "--facts", str(FIX / "source.md")]
    assert subprocess.run(base, capture_output=True, text=True).returncode == 1
    r = subprocess.run(base + ["--allow", str(allow)], capture_output=True, text=True)
    assert r.returncode == 0 and "1 accepted by --allow" in r.stdout


#### could not run: VALIDATOR NOT RUN and exit 2

@pytest.mark.parametrize("args", [
    ["missing.md", "--kind", "resume", "--facts", "source.md"],
    ["number-pass.md", "--kind", "resume", "--facts", "empty-source.md"],
    ["number-pass.md", "--kind", "resume", "--facts", "missing-source.md"],
    ["number-pass.md", "--kind", "resume"],
    ["number-pass.md", "--facts", "source.md"],
    ["number-pass.md", "--kind", "resume", "--facts", "source.md", "--jd", "posting.md"],
])
def test_missing_input_is_validator_not_run(args):
    """missing input is validator not run."""
    args = [str(FIX / a) if a.endswith(".md") else a for a in args]
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr.startswith("VALIDATOR NOT RUN")


def test_help_states_the_limits():
    """help states the limits."""
    r = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "A pass means nothing was invented" in r.stdout


#### findings from the C3 independent review, kept as tests

def write(tmp_path, name, text):
    """write a synthetic file in tmp_path and return its path as a string."""
    path = tmp_path / name
    path.write_text("<!-- synthetic -->\n" + text, encoding="utf-8")
    return str(path)


def run_on(draft, facts, *extra, kind="resume"):
    """return (exit code, stdout) of the check on a draft against one facts file."""
    r = subprocess.run([sys.executable, str(SCRIPT), draft, "--kind", kind, "--facts", facts, *extra],
                       capture_output=True, text=True)
    return r.returncode, r.stdout


def test_counted_noun_must_sit_on_the_number_line(tmp_path):
    """counted noun must sit on the number line."""
    facts = write(tmp_path, "s.md", "- Led a team of 5.\n- Interns were onboarded by me.\n")
    assert run_on(write(tmp_path, "d.md", "- Mentored 5 interns.\n"), facts)[0] == 1


def test_english_words_in_the_sources_do_not_trace_a_tool(tmp_path):
    """english words in the sources do not trace a tool."""
    facts = write(tmp_path, "s.md", "I learned to react to feedback and excel at demos; a go-to-market plan.\n")
    code, out = run_on(write(tmp_path, "d.md", "## Skills\n- Go, React, Excel\n"), facts)
    assert code == 1 and all(f"[skill] {s}" in out for s in ("Go", "React", "Excel"))
    facts = write(tmp_path, "s2.md", "## Skills\n- Go, React, Excel\n")
    assert run_on(write(tmp_path, "d2.md", "## Skills\n- Go, React, Excel\n"), facts)[0] == 0


def test_byte_order_mark_does_not_hide_source_frontmatter(tmp_path):
    """byte order mark does not hide source frontmatter."""
    facts = tmp_path / "s.md"
    facts.write_text("﻿---\ntags: kubernetes\n---\n## Skills\n- Python\n", encoding="utf-8")
    code, out = run_on(write(tmp_path, "d.md", "## Skills\n- Python, Kubernetes\n"), str(facts))
    assert code == 1 and "Kubernetes" in out


def test_allow_entry_that_is_a_tool_is_a_term_not_a_host(tmp_path):
    """allow entry that is a tool is a term not a host."""
    allow = tmp_path / "allow.txt"
    allow.write_text("next.js\n", encoding="utf-8")
    code, out = run_on(write(tmp_path, "d.md", "## Skills\n- Python, Next.js, ASP.NET\n"), str(FIX / "source.md"),
                       "--allow", str(allow))
    assert "1 accepted by --allow" in out and "[skill] ASP.NET" in out and "[url]" not in out


def test_two_known_names_joined_by_and_pass(tmp_path):
    """two known names joined by and pass."""
    assert run_on(write(tmp_path, "d.md", "- Built it with Python and Docker.\n"), str(FIX / "source.md"))[0] == 0


def test_posting_number_needs_a_shared_word_when_no_noun(tmp_path):
    """posting number needs a shared word when no noun."""
    jd = str(FIX / "posting.md")
    ok = write(tmp_path, "ok.md", "I would like to learn how the team deploys 12 times a day.\n")
    code, out = run_on(ok, str(FIX / "source.md"), "--jd", jd, kind="cover")
    assert code == 0 and "note: 12 times was accepted from --jd" in out
    bad = write(tmp_path, "bad.md", "I sped up my builds 12 times.\n")
    assert run_on(bad, str(FIX / "source.md"), "--jd", jd, kind="cover")[0] == 1


def test_email_in_a_draft_is_traced(tmp_path):
    """email in a draft is traced."""
    code, out = run_on(write(tmp_path, "d.md", "Reach me at jordan.lee@example.com.\n"), str(FIX / "source.md"),
                       kind="outreach")
    assert code == 1 and "[url] jordan.lee@example.com" in out
    assert run_on(write(tmp_path, "ok.md", "Reach me at jordan.lee@example.edu.\n"), str(FIX / "source.md"),
                  kind="outreach")[0] == 0


def test_counted_noun_beyond_the_window_does_not_bind(tmp_path):
    """counted noun beyond the window does not bind."""
    facts = write(tmp_path, "s.md", "- 5 people joined the lab that year, and later I hired some interns.\n")
    assert run_on(write(tmp_path, "d.md", "- Mentored 5 interns.\n"), facts)[0] == 1
