"""Tests for .claude/skills/humanizing-writing/scripts/humanizer_check.py.
Every fixture under fixtures/humanizer is synthetic and says so in a comment."""
import importlib.util
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
    """block phrase fails in a letter."""
    code, out, _ = check("block-phrase-fail.md", "cover")
    assert code == 1 and "block/phrase" in kinds(out) and "passionate about" in out


def test_block_phrase_pass_has_no_phrase_finding():
    """block phrase pass has no phrase finding."""
    _, out, _ = check("block-phrase-pass.md", "cover")
    assert not {"block/phrase", "warn/phrase"} & kinds(out)


def test_hws_word_is_warn_in_a_resume_and_block_in_a_letter():
    """hws word is warn in a resume and block in a letter."""
    code, out, _ = check("resume-tier.md", "resume")
    assert code == 0 and "warn/phrase" in kinds(out) and "robust" in out
    code, out, _ = check("resume-tier.md", "cover")
    assert "block/phrase" in kinds(out)


def test_inflated_verb_carries_a_swap_hint(tmp_path):
    """inflated verb carries a swap hint."""
    draft = tmp_path / "d.md"
    draft.write_text("<!-- synthetic -->\n- Leveraged Redis to cache results.\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(draft), "--kind", "resume"], capture_output=True, text=True)
    assert r.returncode == 1 and "(swap: used)" in r.stdout


def test_phrase_across_a_line_break_and_hyphen_is_found(tmp_path):
    """phrase across a line break and hyphen is found."""
    draft = tmp_path / "d.md"
    draft.write_text("<!-- synthetic -->\nI am\npassionate   about data driven work.\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(draft), "--kind", "cover"], capture_output=True, text=True)
    assert "passionate" in r.stdout and "data driven" in r.stdout


def test_own_words_exemption():
    """own words exemption."""
    _, out, _ = check("own-words-draft.md", "resume", "--sources", str(FIX / "own-words-source.md"))
    assert "best practices" not in out
    code, out, _ = check("own-words-draft.md", "resume")
    assert code == 1 and "best practices" in out


#### check 4: dashes

def test_dashes_fail():
    """dashes fail."""
    code, out, _ = check("dash-fail.md", "resume")
    assert code == 1 and out.count("[block/dash]") == 4


def test_year_ranges_and_hyphens_pass():
    """year ranges and hyphens pass."""
    _, out, _ = check("dash-pass.md", "resume")
    assert "dash" not in out


#### check 5: structural tells (warn only)

def test_structure_patterns_warn():
    """structure patterns warn."""
    code, out, _ = check("structure-fail.md", "resume")
    assert code == 0
    for name in ("not only X but also Y", "it's not just X, it's Y", "this isn't X, this is Y", "three openers 'built'"):
        assert name in out


def test_triplet_in_every_paragraph_warns():
    """triplet in every paragraph warns."""
    _, out, _ = check("triplet-fail.md", "cover")
    assert "a three-part list in every paragraph" in out


def test_structure_pass_is_clean():
    """structure pass is clean."""
    assert check("structure-pass.md", "resume")[1].startswith("0 blocking, 0 warning")


#### length, asks, greeting, subject

@pytest.mark.parametrize("name,kind,code,needle", [
    ("cover-short-fail.md", "cover", 1, "needs at least 250"),
    ("email-long-fail.md", "outreach", 1, "allows at most 149"),
])
def test_length_fails(name, kind, code, needle):
    """length fails."""
    got, out, _ = check(name, kind)
    assert got == code and "block/length" in kinds(out) and needle in out


@pytest.mark.parametrize("name,kind", [("cover-pass.md", "cover"), ("email-pass.md", "outreach"),
                                       ("email-pass.md", "followup")])
def test_clean_letter_and_email_pass(name, kind):
    """clean letter and email pass."""
    assert check(name, kind) == (0, "0 blocking, 0 warning finding(s)\n", "")


def test_two_asks_fail():
    """two asks fail."""
    code, out, _ = check("email-two-asks-fail.md", "outreach")
    assert code == 1 and out.count("[block/ask]") == 2


def test_greeting_without_a_name_fails():
    """greeting without a name fails."""
    code, out, _ = check("greeting-fail.md", "outreach")
    assert code == 1 and "block/greeting" in kinds(out)


def test_missing_subject_fails_for_email_only():
    """missing subject fails for email only."""
    code, out, _ = check("subject-fail.md", "followup")
    assert code == 1 and "block/subject" in kinds(out)
    assert check("subject-fail.md", "followup", "--channel", "message")[0] == 0


#### placeholders, chat residue, characters

def test_placeholders_fail_and_markdown_links_pass():
    """placeholders fail and markdown links pass."""
    code, out, _ = check("placeholder-fail.md", "resume")
    assert code == 1 and all(t in out for t in ("[Company]", "{{", "XYZ"))
    assert check("placeholder-pass.md", "resume")[0] == 0


def test_chat_residue_fails():
    """chat residue fails."""
    code, out, _ = check("chat-residue-fail.md", "resume")
    assert code == 1 and "Certainly!" in out and "I hope this helps" in out


def test_zero_width_blocks_and_curly_quotes_warn():
    """zero width blocks and curly quotes warn."""
    code, out, _ = check("chars-fail.md", "resume")
    assert code == 1 and "U+200C" in out and "warn/char" in kinds(out)
    assert check("chars-pass.md", "resume")[0] == 0


#### misses the C3 red team found, kept as fixtures

def test_inflected_banned_word_blocks():
    """inflected banned word blocks."""
    code, out, _ = check("redteam-inflection-fail.md", "followup", "--channel", "message")
    assert code == 1 and "delved" in out


def test_spaced_hyphen_used_as_a_dash_blocks():
    """spaced hyphen used as a dash blocks."""
    code, out, _ = check("redteam-spaced-hyphen-fail.md", "resume")
    assert code == 1 and "[block/dash]" in out


def test_two_asks_in_one_sentence_block():
    """two asks in one sentence block."""
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
    """missing input is validator not run."""
    args = [str(FIX / a) if a.endswith(".md") else a for a in args]
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr.startswith("VALIDATOR NOT RUN")


def test_empty_draft_is_validator_not_run(tmp_path):
    """empty draft is validator not run."""
    draft = tmp_path / "empty.md"
    draft.write_text("<!-- synthetic, empty -->\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPT), str(draft), "--kind", "cover"], capture_output=True, text=True)
    assert r.returncode == 2 and "has no text" in r.stderr


#### findings from the C3 independent review, kept as tests

def write(tmp_path, name, text):
    """write a synthetic file in tmp_path and return its path as a string."""
    path = tmp_path / name
    path.write_text("<!-- synthetic -->\n" + text, encoding="utf-8")
    return str(path)


def run_on(path, *args):
    """return (exit code, stdout, stderr) of the check on a path."""
    r = subprocess.run([sys.executable, str(SCRIPT), path, *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def test_byte_order_mark_does_not_hide_frontmatter(tmp_path):
    """byte order mark does not hide frontmatter."""
    path = tmp_path / "bom.md"
    path.write_text("﻿---\ntags: passionate about\n---\nBuilt a queue in Go.\n", encoding="utf-8")
    assert run_on(str(path), "--kind", "cover")[1].count("[block/phrase]") == 0


def test_guidance_sections_in_sources_are_not_own_words(tmp_path):
    """guidance sections in sources are not own words."""
    sources = write(tmp_path, "s.md", "## Tailoring Notes\n- Avoid saying passionate about.\n")
    draft = write(tmp_path, "d.md", "I am passionate about queues.\n")
    code, out, _ = run_on(draft, "--kind", "resume", "--sources", sources)
    assert code == 0 and "[warn/phrase] passionate about" in out      # still flagged: a note is not his words


@pytest.mark.parametrize("greeting,code", [("Hi Platform Team,", 1), ("Hello Recruiters,", 1), ("Hi, Priya,", 0)])
def test_greeting_names_a_person(tmp_path, greeting, code):
    """greeting names a person."""
    draft = write(tmp_path, "d.md", f"{greeting}\n\nI applied last week. Would you have ten minutes?\n\nThanks,\nJordan\n")
    assert run_on(draft, "--kind", "outreach", "--channel", "message")[0] == code


def test_html_tags_and_checkboxes_are_not_placeholders(tmp_path):
    """html tags and checkboxes are not placeholders."""
    assert run_on(write(tmp_path, "d.md", "See <br> and [x] done and [a] note.\n"), "--kind", "resume")[0] == 0


def test_season_and_numeric_month_ranges_are_exempt(tmp_path):
    """season and numeric month ranges are exempt."""
    draft = write(tmp_path, "d.md", "Intern, Summer 2023 – Fall 2023.\nTutor, 05/2023 – 08/2023.\n")
    assert "dash" not in run_on(draft, "--kind", "resume")[1]


def test_one_finding_per_word_with_the_stronger_tier(tmp_path):
    """one finding per word with the stronger tier."""
    out = run_on(write(tmp_path, "d.md", "- Leveraged Redis.\n"), "--kind", "resume")[1]
    assert out.count("[block/phrase]") == 1 and "[warn/phrase]" not in out


def test_cover_over_the_maximum_fails(tmp_path):
    """cover over the maximum fails."""
    text = (FIX / "cover-pass.md").read_text(encoding="utf-8").replace("Thanks for reading,", "The lab ran it every night. " * 15 + "\n\nThanks for reading,")
    path = tmp_path / "long.md"
    path.write_text(text, encoding="utf-8")
    code, out, _ = run_on(str(path), "--kind", "cover")
    assert code == 1 and "allows at most 350" in out


def test_followup_needs_a_greeting_too():
    """followup needs a greeting too."""
    code, out, _ = check("greeting-fail.md", "followup")
    assert code == 1 and "block/greeting" in kinds(out)


def test_missing_limits_or_phrases_is_validator_not_run(tmp_path, monkeypatch, capsys):
    """missing limits or phrases is validator not run."""
    spec = importlib.util.spec_from_file_location("humanizer_check", SCRIPT)
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    data = tmp_path / "data"
    data.mkdir()
    (data / "banned_phrases.txt").write_text("block\tcircling back\n", encoding="utf-8")
    (data / "limits.json").write_text('{"cover": {"min_words": 250}}', encoding="utf-8")
    monkeypatch.setattr(h, "DATA", data)
    assert h.main([str(FIX / "email-pass.md"), "--kind", "outreach"]) == 2
    assert "no entry for outreach" in capsys.readouterr().err
    (data / "banned_phrases.txt").write_text("# comments only\n", encoding="utf-8")
    assert h.main([str(FIX / "chat-residue-fail.md"), "--kind", "cover"]) == 2
    assert "no phrase rows" in capsys.readouterr().err
