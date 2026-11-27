"""
internship-research-loop: generating-resume-docx skill
Topic: check a generated resume or cover letter DOCX against the ATS baseline before it is used.

Usage: python3 verify_docx.py FILE.docx --kind resume|cover
Prints one finding per line as `path:0 [kind] token | context`, then a count line and
the line "page count not verified".
Exit 0 pass, 1 findings, 2 the check could not run (`VALIDATOR NOT RUN: <reason>`).
Spec: Claude System Implementation Plan, Script specs; ATS baseline in the
Application Documents Standard. Fonts and the resume word ceiling come from the two
generators, so each number has one copy.
"""
import argparse
import importlib.util
import pathlib
import re
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
COVER_GENERATOR = HERE.parents[1] / "generating-cover-letter-docx" / "scripts" / "generate_cover_letter_docx.py"
MAX_BYTES = 2_500_000                                  # Greenhouse: files over 2.5 MB fail to parse
MIN_TEXT_CHARS = 50                                    # less than this means the text layer is missing
CONTACT = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\+?\d[\d\s().-]{7,}\d|linkedin\.com|github\.com|https?://",
                     re.IGNORECASE)
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
OBJECTS = (("table", "w:tbl"), ("image", "w:drawing"), ("image", "w:pict"), ("textbox", "w:txbxContent"),
           ("image", "w:object"))


#### error type and argument parser

class NotRun(Exception):
    """raised when the file or a generator cannot be read, so the check cannot run."""


class Parser(argparse.ArgumentParser):
    """an argument parser whose usage errors print VALIDATOR NOT RUN and exit 2."""

    def error(self, message):
        """print the not-run line and exit 2."""
        print(f"VALIDATOR NOT RUN: {message}", file=sys.stderr)
        sys.exit(2)


#### loading

def load_module(name, path):
    """return a module loaded from a file path, or raise NotRun."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise NotRun(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module                         # a dataclass looks its module up while it is built
    try:
        spec.loader.exec_module(module)
    # Source: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly (register in sys.modules, then exec_module)
    except (OSError, ImportError) as e:
        raise NotRun(f"cannot load {path}: {e}") from e
    return module


def rules_for(kind):
    """return (font allowlist, word ceiling or None) for a kind, read from its generator."""
    if kind == "resume":
        gen = load_module("generate_resume_docx", HERE / "generate_resume_docx.py")
        return gen.APPROVED_FONTS, gen.ONE_PAGE_WORD_CEILING
    gen = load_module("generate_cover_letter_docx", COVER_GENERATOR)
    return gen.APPROVED_FONTS, None                    # the Plan sets a word limit for a resume only


def open_docx(path):
    """return a python-docx Document, or raise NotRun."""
    from docx import Document
    from docx.opc.exceptions import PackageNotFoundError
    try:
        return Document(str(path))
    # Source: https://python-docx.readthedocs.io/en/latest/api/document.html (Document() opens a .docx path)
    except (PackageNotFoundError, zipfile.BadZipFile, OSError, KeyError, ValueError) as e:
        raise NotRun(f"cannot open {path} as a DOCX: {e}") from e


#### checks: each returns a list of (kind, token, context)

def body_text(doc):
    """return the text of every body paragraph and table cell, one line each."""
    lines = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            lines.extend(cell.text for cell in row.cells)
    return "\n".join(lines)


def check_contact(doc, text):
    """return findings for contact details in a header or footer, or missing from the body."""
    out = []
    for i, section in enumerate(doc.sections):
        for name in ("header", "first_page_header", "even_page_header",
                     "footer", "first_page_footer", "even_page_footer"):
            part = getattr(section, name)
            if part.is_linked_to_previous:
                continue                               # no definition of its own
            hf_text = "\n".join(p.text for p in part.paragraphs)
            hf_text += "\n".join(c.text for t in part.tables for r in t.rows for c in r.cells)
            m = CONTACT.search(hf_text)
            if m:
                out.append(("contact", m.group(0), f"section {i + 1} {name.replace('_', ' ')}: a parser drops it"))
    if not CONTACT.search(text):
        out.append(("contact", "(none)", "no email, phone or profile link in the body"))
    return out


def check_objects(doc):
    """return findings for tables, images, text boxes and embedded objects in the body."""
    out = []
    body = doc.element.body
    for kind, tag in OBJECTS:
        count = len(body.xpath(f".//{tag}"))
        if count:
            out.append((kind, f"{count} {tag}", "the ATS baseline allows plain paragraphs only"))
    return out


def check_columns(doc):
    """return a finding for any section laid out in more than one column."""
    out = []
    for cols in doc.element.body.xpath(".//w:sectPr/w:cols"):
        num = cols.get(f"{W}num")
        if num and int(num) > 1:
            out.append(("columns", f"{num} columns", "the ATS baseline is one column"))
    return out


def style_fonts(style):
    """return the explicit font names along a style's base-style chain."""
    names = []
    while style is not None:
        if style.font.name:
            names.append(style.font.name)
        style = style.base_style
    return names


def check_fonts(doc, allowed):
    """return a finding for each font used that is not in the generator's allowlist."""
    used = set()
    for p in doc.paragraphs:
        used.update(style_fonts(p.style))
        for run in p.runs:
            if run.font.name:
                used.add(run.font.name)
            used.update(style_fonts(run.style))
    for rfonts in doc.element.body.xpath(".//w:rFonts"):
        for attr in ("ascii", "hAnsi"):
            if rfonts.get(f"{W}{attr}"):
                used.add(rfonts.get(f"{W}{attr}"))
    return [("font", name, f"allowed: {', '.join(sorted(allowed))}") for name in sorted(used - set(allowed))]


def check_size_and_text(path, text, ceiling):
    """return findings for file size, an empty text layer and the resume word ceiling."""
    out = []
    size = path.stat().st_size
    if size > MAX_BYTES:
        out.append(("size", f"{size} bytes", f"over {MAX_BYTES} bytes"))
    if len(text.strip()) < MIN_TEXT_CHARS:
        out.append(("text", f"{len(text.strip())} characters", "the text layer extracts almost nothing"))
    words = len(text.split())
    if ceiling is not None and words > ceiling:
        out.append(("length", f"{words} words", f"a one-page resume is at most {ceiling} words"))
    return out


#### driver

def run(path, kind):
    """return the findings for one DOCX, or raise NotRun."""
    path = pathlib.Path(path)
    if not path.is_file():
        raise NotRun(f"{path} does not exist")
    allowed, ceiling = rules_for(kind)
    doc = open_docx(path)
    text = body_text(doc)
    return (check_contact(doc, text) + check_objects(doc) + check_columns(doc)
            + check_fonts(doc, allowed) + check_size_and_text(path, text, ceiling))


def main(argv=None):
    """print findings and return the exit code."""
    ap = Parser(description="check a generated resume or cover letter DOCX against the ATS baseline")
    ap.add_argument("docx", help="the generated .docx file")
    ap.add_argument("--kind", required=True, choices=("resume", "cover"), help="which generator's rules apply")
    args = ap.parse_args(argv)
    try:
        findings = run(args.docx, args.kind)
    except NotRun as e:
        print(f"VALIDATOR NOT RUN: {e}", file=sys.stderr)
        return 2
    for kind, token, ctx in findings:
        print(f"{args.docx}:0 [{kind}] {token} | {ctx}")
    print(f"{len(findings)} finding(s)")
    # shortcut: page count is never measured (LibreOffice is not installed on the Dell); add a
    # LibreOffice render and count when a machine that runs this has it
    print("page count not verified")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
