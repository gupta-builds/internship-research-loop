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
    code, out, _ = check(draft, facts=facts)
    assert code == 1 and kind in tags(out) and needle in out


@pytest.mark.parametrize("draft", ["number-pass.md", "magnitude-pass.md", "noun-pass.md", "daterange-pass.md",
                                   "section-pass.md", "skill-pass.md", "url-pass.md"])
def test_passing_fixture(draft):
    code, out, _ = check(draft)
    assert code == 0 and out.startswith("0 finding(s)")


def test_value_on_another_noun_fails():
    # 120 is in the source, but bound to lab reports, not interns
    code, out, _ = check("noun-moved-fail.md")
    assert code == 1 and "bound to 'intern'" in out


def test_range_ends_from_two_roles_fail():
    # Jun 2024 starts one role and Current ends another; the range is in no source section
    code, out, _ = check("range-pair-fail.md")
    assert code == 1 and "not as one range" in out


def test_ambiguous_english_words_in_prose_pass():
    # C3 red team case 20: rust, react, go and swift are English words in lowercase prose
    code, out, _ = check("redteam-ambiguous-pass.md", "followup")
    assert code == 0, out
    code, out, _ = check("skill-ambiguous-fail.md")
    assert code == 1 and "[skill] Rust" in out                     # in a Skills section it is still checked


#### the posting as a source

def test_posting_never_supplies_a_skill():
    code, out, _ = check("posting-resume-fail.md", "cover", "source.md", "--jd", str(FIX / "posting.md"))
    assert code == 1 and "Kafka" in out


def test_posting_supplies_company_and_role_names_for_a_letter():
    code, out, _ = check("posting-letter-pass.md", "cover", "source.md", "--jd", str(FIX / "posting.md"))
    assert code == 0 and "2 by --jd" in out
    code, out, _ = check("posting-letter-pass.md", "cover")
    assert code == 1 and "Northwind Labs" in out                    # without --jd the names are untraced


def test_posting_tool_in_letter_prose_fails():
    code, out, _ = check("posting-letter-fail.md", "cover", "source.md", "--jd", str(FIX / "posting.md"))
    assert code == 1 and "Kafka" in out


def test_posting_number_needs_a_shared_word_and_noun():
    assert check("posting-number-pass.md", "cover", "source.md", "--jd", str(FIX / "posting.md"))[0] == 0
    code, out, _ = check("posting-number-fail.md", "cover", "source.md", "--jd", str(FIX / "posting.md"))
    assert code == 1 and "40 million" in out


#### --allow

def test_allow_file_adds_alias_host_and_term(tmp_path):
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
    args = [str(FIX / a) if a.endswith(".md") else a for a in args]
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr.startswith("VALIDATOR NOT RUN")


def test_help_states_the_limits():
    r = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "A pass means nothing was invented" in r.stdout
