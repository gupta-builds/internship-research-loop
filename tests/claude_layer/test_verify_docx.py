"""Tests for .claude/skills/generating-resume-docx/scripts/verify_docx.py.
Every DOCX is built in tmp_path from synthetic text; no real resume enters the repo."""
import base64
import importlib.util
import pathlib
import subprocess
import sys

import pytest
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".claude/skills/generating-resume-docx/scripts/verify_docx.py"
GEN = ROOT / ".claude/skills/generating-resume-docx/scripts/generate_resume_docx.py"
# a 1x1 transparent PNG, synthetic
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
BODY = ("Jordan Lee", "jordan.lee@example.edu | github.com/jlee-example",
        "Built a print queue in Go that cut the lab wait from nine minutes to two.")   # synthetic


def load(name, path):
    """return a module loaded from a file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify(path, kind="resume"):
    """return (exit code, stdout, stderr) of the check."""
    r = subprocess.run([sys.executable, str(SCRIPT), str(path), "--kind", kind], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def plain_doc(lines=BODY, font="Times New Roman"):
    """return a one-column Document holding the given lines in one font."""
    doc = Document()
    doc.styles["Normal"].font.name = font
    for line in lines:
        doc.add_paragraph(line)
    return doc


def save(doc, tmp_path, name="d.docx"):
    """save a Document and return its path."""
    path = tmp_path / name
    doc.save(str(path))
    return path


#### the proof: a DOCX the existing generator wrote from a synthetic plan passes

def test_generator_output_passes(tmp_path):
    gen = load("generate_resume_docx", GEN)
    plan = gen.ResumePlan(
        name="Jordan Lee", contact_line="612-555-0143 | jordan.lee@example.edu | github.com/jlee-example",
        education="B.S. Computer Science, Example State University. Expected May 2027.",
        skills=[("Languages", "Python, Go, TypeScript"), ("Data", "PostgreSQL, Redis")],
        experience=[gen.Entry(header="Software Engineering Intern, Acme Robotics Inc., Jun 2024 to Aug 2024",
                              bullets=["Reduced telemetry API latency by 4 percent.", "Mentored 3 interns."])],
        projects=[gen.Entry(header="Print Queue", bullets=["Built a print queue in Go."])],
    )
    path = tmp_path / "resume.docx"
    assert gen.build_resume(plan, str(path)) == []
    code, out, _ = verify(path)
    assert code == 0 and out == "0 finding(s)\npage count not verified\n"


def test_plain_letter_passes_as_cover(tmp_path):
    assert verify(save(plain_doc(), tmp_path), "cover")[0] == 0


#### one failing DOCX per check

def test_contact_in_header_fails(tmp_path):
    doc = plain_doc(lines=(BODY[0], BODY[2]))
    doc.sections[0].header.paragraphs[0].text = BODY[1]
    code, out, _ = verify(save(doc, tmp_path))
    assert code == 1 and "[contact] jordan.lee@example.edu" in out and "(none)" in out


def test_table_fails(tmp_path):
    doc = plain_doc()
    doc.add_table(rows=1, cols=2).cell(0, 0).text = "Skills"
    code, out, _ = verify(save(doc, tmp_path))
    assert code == 1 and "[table]" in out


def test_image_fails(tmp_path):
    (tmp_path / "dot.png").write_bytes(PNG)
    doc = plain_doc()
    doc.add_picture(str(tmp_path / "dot.png"))
    code, out, _ = verify(save(doc, tmp_path))
    assert code == 1 and "[image]" in out


def test_text_box_fails(tmp_path):
    doc = plain_doc()
    box = parse_xml(f'<w:r {nsdecls("w")}><w:pict><w:txbxContent><w:p><w:r><w:t>{BODY[1]}</w:t></w:r></w:p>'
                    "</w:txbxContent></w:pict></w:r>")
    doc.paragraphs[0]._p.append(box)
    code, out, _ = verify(save(doc, tmp_path))
    assert code == 1 and "[textbox]" in out


def test_two_columns_fail(tmp_path):
    doc = plain_doc()
    doc.sections[0]._sectPr.append(parse_xml(f'<w:cols {nsdecls("w")} w:num="2"/>'))
    code, out, _ = verify(save(doc, tmp_path))
    assert code == 1 and "[columns] 2 columns" in out


def test_font_outside_allowlist_fails(tmp_path):
    code, out, _ = verify(save(plain_doc(font="Comic Sans MS"), tmp_path))
    assert code == 1 and "[font] Comic Sans MS" in out


def test_run_level_font_fails(tmp_path):
    doc = plain_doc()
    doc.add_paragraph().add_run("Go, Python").font.name = "Papyrus"
    code, out, _ = verify(save(doc, tmp_path))
    assert code == 1 and "[font] Papyrus" in out


def test_resume_over_the_word_ceiling_fails_and_a_cover_has_no_ceiling(tmp_path):
    path = save(plain_doc(lines=BODY + ("word " * 560,)), tmp_path)
    code, out, _ = verify(path)
    assert code == 1 and "[length]" in out
    assert "[length]" not in verify(path, "cover")[1]


def test_empty_text_layer_fails(tmp_path):
    code, out, _ = verify(save(plain_doc(lines=("Jordan",)), tmp_path))
    assert code == 1 and "[text]" in out and "[contact] (none)" in out


def test_file_over_size_limit_fails(tmp_path, monkeypatch):
    v = load("verify_docx", SCRIPT)
    monkeypatch.setattr(v, "MAX_BYTES", 100)
    kinds = [f[0] for f in v.run(save(plain_doc(), tmp_path), "resume")]
    assert kinds == ["size"]


#### could not run

@pytest.mark.parametrize("make", ["missing", "not-a-docx"])
def test_unreadable_input_is_validator_not_run(tmp_path, make):
    path = tmp_path / "x.docx"
    if make == "not-a-docx":
        path.write_text("synthetic, not a zip", encoding="utf-8")
    code, _, err = verify(path)
    assert code == 2 and err.startswith("VALIDATOR NOT RUN")


def test_missing_kind_is_validator_not_run(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPT), str(save(plain_doc(), tmp_path))], capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr.startswith("VALIDATOR NOT RUN")
