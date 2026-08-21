"""Renders the fixed dossier template and writes it into a vault checkout.

Rendering is pure (no I/O) so validate.py can check format compliance on the
same markdown before anything touches disk. write_dossier() itself does not
re-run the write gate — callers are expected to have already gotten a passing
ValidationResult from validate.validate() before calling it.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from core.identity import company_matches_preference

TEMPLATE_DIR = Path(__file__).parent / "templates"
DOSSIER_SUBPATH = Path("10_Areas/Career/Internships/List/Dossiers")
DOSSIER_UIDS_FILENAME = "dossier_uids.json"

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


def _iso_date(epoch) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).date().isoformat() if epoch else None


DOSSIERS_MOC_LINK = "[[10_Areas/Career/Internships/List/Dossiers MOC]]"

_TAG_ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|]')


def company_slug(company: str) -> str:
    """Same slugification as dossier_filename(): lowercase, spaces to
    hyphens, illegal chars stripped — so 'Aquatic Capital Management' and
    ' aquatic capital management ' both produce company/aquatic-capital-management,
    per the Standard's same-company clustering rule (§1)."""
    s = _TAG_ILLEGAL_CHARS.sub("", company).strip().lower()
    return re.sub(r"\s+", "-", s)


def build_frontmatter(listing, uid: str, date_found: str, matched_reason: str,
                      preferred_companies: dict = None) -> dict:
    """uid and category are deliberately not rendered — uid stays available
    internally via the dossier_uids.json manifest (see write_dossier), and
    category was never surfaced to the reader anywhere else in the note.
    `next:` (not `promoted:`) matches every other note type's convention
    across the vault. `notes:` (always the Dossiers MOC link) and the
    `company/<slug>` tag are the Internship Notes Standard §1 interlinking
    requirement — `notes` sits right after `next`, right before `tags`.
    `preference_tier` (Prompt 5 Task O) is the matched core/profile.yaml
    preferred_companies tier, or null — required like every other field
    here, not omitted when there's no match (fail-closed, same discipline
    as REQUIRED_FRONTMATTER_FIELDS everywhere else in this file)."""
    return {
        "company": listing.company,
        "title": listing.title,
        "url": listing.url,
        "source": listing.source,
        "terms": _yaml_list(listing.terms),
        "locations": _yaml_list(listing.locations),
        "target_year": _yaml_list(listing.target_year),
        "date_posted": _iso_date(listing.date_posted),
        "date_found": date_found,
        "matched_reason": matched_reason,
        "status": "unreviewed",
        "next": None,
        "notes": [DOSSIERS_MOC_LINK],
        "preference_tier": company_matches_preference(listing.company, preferred_companies or {}),
        "tags": ["internship", "auto-discovered", f"company/{company_slug(listing.company)}"],
    }


def dump_frontmatter(frontmatter: dict) -> str:
    """Shared YAML rendering (None as blank scalar, indented list items) so
    every dossier-writing code path — including recheck.py's removal-time
    frontmatter patch — serializes identically."""
    return yaml.dump(
        frontmatter, Dumper=_FrontmatterDumper, sort_keys=False, default_flow_style=False, allow_unicode=True
    )


def render_dossier(listing, uid: str, date_found: str, matched_reason: str, posting_content: str = "",
                   classification_callout: str = "", preferred_companies: dict = None) -> str:
    frontmatter = build_frontmatter(listing, uid, date_found, matched_reason, preferred_companies)
    frontmatter_yaml = dump_frontmatter(frontmatter)
    markdown = _template.render(
        frontmatter_yaml=frontmatter_yaml,
        company=listing.company,
        title=listing.title,
        date_found=date_found,
        source=listing.source,
        posting_content=posting_content,
        classification_callout=classification_callout,
    )
    return markdown.rstrip("\n") + "\n"


_ILLEGAL_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\n\r\t]')


def dossier_filename(role: str, company: str, existing_names) -> str:
    """'[Role] - [Company].md', Windows-unsafe chars stripped (the vault lives
    on a Windows-mounted drive), collision tie-broken with ' (2)', ' (3)', ...
    matching the candidate's own hand-renamed 'Software Engineer -
    Ellipsis Labs.md'. existing_names is scoped to wherever the collision
    check should happen (the target bucket subfolder)."""

    def sanitize(s: str) -> str:
        return _ILLEGAL_FILENAME_CHARS.sub("", s).strip()

    base = f"{sanitize(role)} - {sanitize(company)}"
    existing = set(existing_names)
    name = f"{base}.md"
    n = 2
    while name in existing:
        name = f"{base} ({n}).md"
        n += 1
    return name


def load_dossier_uids(state_dir) -> dict:
    path = Path(state_dir) / DOSSIER_UIDS_FILENAME
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_dossier_uids(state_dir, manifest: dict) -> None:
    path = Path(state_dir) / DOSSIER_UIDS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def scan_dossiers(vault_root) -> list:
    """Frontmatter dicts of every dossier file actually present in the vault
    checkout — recursively, across the flat legacy root and every priority-
    bucket subfolder (Viewed/ included if anything's ever there; nothing in
    this pipeline ever writes into it, but its contents still count for
    cross-source dedup). File existence is the truth here, deliberately not
    seen_ids.json — the two diverged permanently after the 2026-07-18 manual
    vault cleanup (110 dossiers deleted outside the pipeline, uids kept)."""
    dossiers_dir = Path(vault_root) / DOSSIER_SUBPATH
    out = []
    for path in sorted(dossiers_dir.glob("**/*.md")) if dossiers_dir.is_dir() else []:
        m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.DOTALL)
        fm = yaml.safe_load(m.group(1)) if m else None
        if isinstance(fm, dict) and fm.get("company"):
            fm["_path"] = path
            out.append(fm)
    return out


def write_dossier(vault_root, uid: str, markdown: str, role: str, company: str, bucket_folder: str,
                  state_dir=None) -> Path:
    """Writes an already-rendered, already-validated dossier into its
    priority-bucket subfolder. Idempotent on uid: if state_dir's manifest
    already maps this uid to a path, that exact file is overwritten instead
    of a new collision-suffixed one being created — re-rendering the same
    uid (e.g. a same-day re-run with enriched content) must not duplicate the
    note. uid itself is never rendered into the note; state_dir (if given) is
    where it's recorded instead, for recheck.py's removal-checking."""
    vault_root = Path(vault_root)
    manifest = load_dossier_uids(state_dir) if state_dir is not None else {}
    existing_rel_path = next((rel for rel, u in manifest.items() if u == uid), None)

    if existing_rel_path is not None:
        path = vault_root / existing_rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        dossiers_dir = vault_root / DOSSIER_SUBPATH / bucket_folder
        dossiers_dir.mkdir(parents=True, exist_ok=True)
        existing_names = {p.name for p in dossiers_dir.glob("*.md")}
        path = dossiers_dir / dossier_filename(role, company, existing_names)

    path.write_text(markdown)
    if state_dir is not None:
        manifest[str(path.relative_to(vault_root))] = uid
        save_dossier_uids(state_dir, manifest)
    return path
