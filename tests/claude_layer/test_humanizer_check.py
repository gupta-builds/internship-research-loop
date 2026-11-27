"""Tests for .claude/skills/humanizing-writing/scripts/humanizer_check.py.
Every fixture under fixtures/humanizer is synthetic and says so in a comment."""
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".claude/skills/humanizing-writing/scripts/humanizer_check.py"
FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "humanizer"


def check(name, kind, *extra):
    """return (exit code, stdout, stderr) of the check on one fixture."""
    r = subprocess.run([sys.executable, str(SCRIPT), str(FIX / name), "--kind", kind, *extra],
                       capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def kinds(out):
    """return the set of tier/kind tags printed in the findings."""
    return {line.split("[", 1)[1].split("]", 1)[0] for line in out.splitlines() if " [" in line}


#### check 3: phrases, tiers and the own-words exemption

def test_block_phrase_fails_in_a_letter():
    code, out, _ = check("block-phrase-fail.md", "cover")
    assert code == 1 and "block/phrase" in kinds(out) and "passionate about" in out


def test_block_phrase_pass_has_no_phrase_finding():
    _, out, _ = check("block-phrase-pass.md", "cover")
    assert not {"block/phrase", "warn/phrase"} & kinds(out)


def test_hws_word_is_warn_in_a_resume_and_block_in_a_letter():
    code, out, _ = check("resume-tier.md", "resume")
    assert code == 0 and "warn/phrase" in kinds(out) and "robust" in out
    code, out, _ = check("resume-tier.md", "cover")
    assert "block/phrase" in kinds(out)


def test_inflated_verb_carries_a_swap_hint(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("<!-- synthetic -->\n- Leveraged Redis to cache results.\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(draft), "--kind", "resume"], capture_output=True, text=True)
    assert r.returncode == 1 and "(swap: used)" in r.stdout


def test_phrase_across_a_line_break_and_hyphen_is_found(tmp_path):
    draft = tmp_path / "d.md"
    draft.write_text("<!-- synthetic -->\nI am\npassionate   about data driven work.\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(draft), "--kind", "cover"], capture_output=True, text=True)
    assert "passionate" in r.stdout and "data driven" in r.stdout


def test_own_words_exemption():
    _, out, _ = check("own-words-draft.md", "resume", "--sources", str(FIX / "own-words-source.md"))
    assert "best practices" not in out
    code, out, _ = check("own-words-draft.md", "resume")
    assert code == 1 and "best practices" in out


#### check 4: dashes

def test_dashes_fail():
    code, out, _ = check("dash-fail.md", "resume")
    assert code == 1 and out.count("[block/dash]") == 3


def test_year_ranges_and_hyphens_pass():
    _, out, _ = check("dash-pass.md", "resume")
    assert "dash" not in out


#### check 5: structural tells (warn only)

def test_structure_patterns_warn():
    code, out, _ = check("structure-fail.md", "resume")
    assert code == 0
    for name in ("not only X but also Y", "it's not just X, it's Y", "this isn't X, this is Y", "three openers 'built'"):
        assert name in out


def test_triplet_in_every_paragraph_warns():
    _, out, _ = check("triplet-fail.md", "cover")
    assert "a three-part list in every paragraph" in out


def test_structure_pass_is_clean():
    assert check("structure-pass.md", "resume")[1].startswith("0 blocking, 0 warning")


#### length, asks, greeting, subject

@pytest.mark.parametrize("name,kind,code,needle", [
    ("cover-short-fail.md", "cover", 1, "needs at least 250"),
    ("email-long-fail.md", "outreach", 1, "allows at most 149"),
])
def test_length_fails(name, kind, code, needle):
    got, out, _ = check(name, kind)
    assert got == code and "block/length" in kinds(out) and needle in out


@pytest.mark.parametrize("name,kind", [("cover-pass.md", "cover"), ("email-pass.md", "outreach"),
                                       ("email-pass.md", "followup")])
def test_clean_letter_and_email_pass(name, kind):
    assert check(name, kind) == (0, "0 blocking, 0 warning finding(s)\n", "")


def test_two_asks_fail():
    code, out, _ = check("email-two-asks-fail.md", "outreach")
    assert code == 1 and out.count("[block/ask]") == 2


def test_greeting_without_a_name_fails():
    code, out, _ = check("greeting-fail.md", "outreach")
    assert code == 1 and "block/greeting" in kinds(out)


def test_missing_subject_fails_for_email_only():
    code, out, _ = check("subject-fail.md", "followup")
    assert code == 1 and "block/subject" in kinds(out)
    assert check("subject-fail.md", "followup", "--channel", "message")[0] == 0


#### placeholders, chat residue, characters

def test_placeholders_fail_and_markdown_links_pass():
    code, out, _ = check("placeholder-fail.md", "resume")
    assert code == 1 and all(t in out for t in ("[Company]", "{{", "XYZ"))
    assert check("placeholder-pass.md", "resume")[0] == 0


def test_chat_residue_fails():
    code, out, _ = check("chat-residue-fail.md", "resume")
    assert code == 1 and "Certainly!" in out and "I hope this helps" in out


def test_zero_width_blocks_and_curly_quotes_warn():
    code, out, _ = check("chars-fail.md", "resume")
    assert code == 1 and "U+200C" in out and "warn/char" in kinds(out)
    assert check("chars-pass.md", "resume")[0] == 0


#### misses the C3 red team found, kept as fixtures

def test_inflected_banned_word_blocks():
    code, out, _ = check("redteam-inflection-fail.md", "followup", "--channel", "message")
    assert code == 1 and "delved" in out


def test_spaced_hyphen_used_as_a_dash_blocks():
    code, out, _ = check("redteam-spaced-hyphen-fail.md", "resume")
    assert code == 1 and "[block/dash]" in out


def test_two_asks_in_one_sentence_block():
    code, out, _ = check("redteam-two-asks-one-sentence-fail.md", "followup")
    assert code == 1 and "2 asks" in out


#### could not run

@pytest.mark.parametrize("args", [
    ["missing.md", "--kind", "resume"],
    ["block-phrase-pass.md"],
    ["block-phrase-pass.md", "--kind", "poem"],
    ["block-phrase-pass.md", "--kind", "resume", "--sources", "missing-source.md"],
])
def test_missing_input_is_validator_not_run(args):
    args = [str(FIX / a) if a.endswith(".md") else a for a in args]
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr.startswith("VALIDATOR NOT RUN")


def test_empty_draft_is_validator_not_run(tmp_path):
    draft = tmp_path / "empty.md"
    draft.write_text("<!-- synthetic, empty -->\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(draft), "--kind", "cover"], capture_output=True, text=True)
    assert r.returncode == 2 and "has no text" in r.stderr
