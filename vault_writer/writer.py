"""Renders the fixed dossier template and writes it into a vault checkout.

Rendering is pure (no I/O) so validate.py can check format compliance on the
same markdown before anything touches disk. write_dossier() itself does not
re-run the write gate — callers are expected to have already gotten a passing
ValidationResult from validate.validate() before calling it.
"""
import re
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"
DOSSIER_SUBPATH = Path("10_Areas/Career/Internships/List/Dossiers")

_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
_template = _env.get_template("dossier.md.j2")


class _FrontmatterDumper(yaml.SafeDumper):
    """Dumps None as a blank scalar (matching the plan's `field:` empty style
    instead of PyYAML's default literal `null`) and indents list items under
    their parent key (matching the vault's own `tags:\n  - x` convention)."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def _represent_none(dumper, _):
    return dumper.represent_scalar("tag:yaml.org,2002:null", "")


_FrontmatterDumper.add_representer(type(None), _represent_none)


def _yaml_list(items) -> list:
    return list(items) if items else []


def build_frontmatter(listing, uid: str, date_found: str, matched_reason: str) -> dict:
    """The exact field set from the plan's Dossier Note Shape, in order."""
    return {
        "uid": uid,
        "company": listing.company,
        "title": listing.title,
        "url": listing.url,
        "source": listing.source,
        "category": listing.category or None,
        "terms": _yaml_list(listing.terms),
        "locations": _yaml_list(listing.locations),
        "target_year": _yaml_list(listing.target_year),
        "date_posted": listing.date_posted,
        "date_found": date_found,
        "matched_reason": matched_reason,
        "status": "unreviewed",
        "promoted": None,
        "tags": ["internship", "auto-discovered"],
    }


def render_dossier(listing, uid: str, date_found: str, matched_reason: str) -> str:
    frontmatter = build_frontmatter(listing, uid, date_found, matched_reason)
    frontmatter_yaml = yaml.dump(
        frontmatter, Dumper=_FrontmatterDumper, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    markdown = _template.render(
        frontmatter_yaml=frontmatter_yaml,
        company=listing.company,
        title=listing.title,
        date_found=date_found,
        source=listing.source,
    )
    return markdown.rstrip("\n") + "\n"


def slugify_uid(uid: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", uid).strip("-").lower()
    return slug


def scan_dossiers(vault_root) -> list:
    """Frontmatter dicts of every dossier file actually present in the vault
    checkout. File existence is the truth here, deliberately not
    seen_ids.json — the two diverged permanently after the 2026-07-18 manual
    vault cleanup (110 dossiers deleted outside the pipeline, uids kept)."""
    dossiers_dir = Path(vault_root) / DOSSIER_SUBPATH
    out = []
    for path in sorted(dossiers_dir.glob("*.md")) if dossiers_dir.is_dir() else []:
        m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.DOTALL)
        fm = yaml.safe_load(m.group(1)) if m else None
        if isinstance(fm, dict) and fm.get("uid"):
            fm["_path"] = path
            out.append(fm)
    return out


def write_dossier(vault_root, uid: str, markdown: str) -> Path:
    """Writes an already-rendered, already-validated dossier. Idempotent on uid:
    re-writing the same uid overwrites the same file rather than creating a new one."""
    dossiers_dir = Path(vault_root) / DOSSIER_SUBPATH
    dossiers_dir.mkdir(parents=True, exist_ok=True)
    path = dossiers_dir / f"{slugify_uid(uid)}.md"
    path.write_text(markdown)
    return path
