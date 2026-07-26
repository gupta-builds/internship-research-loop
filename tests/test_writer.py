import json
import shutil
from pathlib import Path

import pytest

from ingestion.normalize import normalize_simplify
from vault_writer.writer import dossier_filename, load_dossier_uids, render_dossier, write_dossier

FIXTURES = Path(__file__).parent / "fixtures"
THROWAWAY_VAULT = FIXTURES / "throwaway_vault"
DOSSIERS_SUBPATH = Path("10_Areas/Career/Internships/List/Dossiers")


@pytest.fixture
def vault_root(tmp_path):
    """Copy of the committed throwaway_vault skeleton in a scratch dir per test,
    so tests never write into (and dirty) the git-tracked fixture."""
    dest = tmp_path / "vault"
    shutil.copytree(THROWAWAY_VAULT, dest)
    return dest


@pytest.fixture
def state_dir(tmp_path):
    return tmp_path / "state"


@pytest.fixture
def listing():
    raw = json.loads((FIXTURES / "simplifyjobs.json").read_text())[0]
    return normalize_simplify(raw)


def test_dossier_filename_sanitizes_illegal_chars():
    name = dossier_filename("Software Engineer", 'Fussball Club Cincinnati LLC ("FC Cincinnati")', set())
    assert name == "Software Engineer - Fussball Club Cincinnati LLC (FC Cincinnati).md"
    assert '"' not in name


def test_dossier_filename_collision_appends_number():
    existing = {"Software Engineer - Acme.md"}
    assert dossier_filename("Software Engineer", "Acme", existing) == "Software Engineer - Acme (2).md"


def test_dossier_filename_collision_increments_past_multiple():
    existing = {"Software Engineer - Acme.md", "Software Engineer - Acme (2).md"}
    assert dossier_filename("Software Engineer", "Acme", existing) == "Software Engineer - Acme (3).md"


def test_write_dossier_writes_expected_file(vault_root, listing):
    uid = f"{listing.source}:{listing.raw_id}"
    md = render_dossier(listing, uid, "2026-07-17", "Junior-eligible, Summer 2027, Software Engineering")

    path = write_dossier(vault_root, uid, md, listing.title, listing.company, "Other")

    expected_name = dossier_filename(listing.title, listing.company, set())
    expected_path = vault_root / DOSSIERS_SUBPATH / "Other" / expected_name
    assert path == expected_path
    assert path.read_text() == md


def test_write_dossier_routes_into_bucket_subfolder(vault_root, listing):
    uid = f"{listing.source}:{listing.raw_id}"
    md = render_dossier(listing, uid, "2026-07-17", "reason")

    path = write_dossier(vault_root, uid, md, listing.title, listing.company, "1 - AI & ML")

    assert path.parent == vault_root / DOSSIERS_SUBPATH / "1 - AI & ML"
    assert path.exists()


def test_write_dossier_is_idempotent_on_uid(vault_root, listing, state_dir):
    uid = f"{listing.source}:{listing.raw_id}"
    md_v1 = render_dossier(listing, uid, "2026-07-17", "first pass")
    write_dossier(vault_root, uid, md_v1, listing.title, listing.company, "Other", state_dir=state_dir)

    md_v2 = render_dossier(listing, uid, "2026-07-18", "second pass, re-run same day")
    write_dossier(vault_root, uid, md_v2, listing.title, listing.company, "Other", state_dir=state_dir)

    dossiers_dir = vault_root / DOSSIERS_SUBPATH / "Other"
    files = [f for f in dossiers_dir.iterdir() if f.suffix == ".md"]
    assert len(files) == 1
    assert files[0].read_text() == md_v2


def test_write_dossier_different_uid_same_role_company_gets_collision_suffix(vault_root, listing, state_dir):
    """Same role+company but a genuinely different uid must not overwrite —
    only a re-write of the SAME uid is idempotent."""
    uid1 = f"{listing.source}:{listing.raw_id}"
    write_dossier(vault_root, uid1, render_dossier(listing, uid1, "2026-07-17", "r1"),
                  listing.title, listing.company, "Other", state_dir=state_dir)

    uid2 = f"{listing.source}:some-other-id"
    write_dossier(vault_root, uid2, render_dossier(listing, uid2, "2026-07-17", "r2"),
                  listing.title, listing.company, "Other", state_dir=state_dir)

    dossiers_dir = vault_root / DOSSIERS_SUBPATH / "Other"
    files = sorted(f.name for f in dossiers_dir.iterdir() if f.suffix == ".md")
    assert len(files) == 2


def test_write_dossier_creates_missing_dossiers_dir(tmp_path, listing):
    """vault_root with no pre-existing Dossiers/ folder at all still works."""
    bare_vault = tmp_path / "bare_vault"
    bare_vault.mkdir()
    uid = f"{listing.source}:{listing.raw_id}"
    md = render_dossier(listing, uid, "2026-07-17", "reason")

    path = write_dossier(bare_vault, uid, md, listing.title, listing.company, "Other")

    assert path.exists()


def test_write_dossier_records_uid_manifest(vault_root, listing, state_dir):
    uid = f"{listing.source}:{listing.raw_id}"
    md = render_dossier(listing, uid, "2026-07-17", "reason")

    path = write_dossier(vault_root, uid, md, listing.title, listing.company, "Other", state_dir=state_dir)

    manifest = load_dossier_uids(state_dir)
    assert manifest[str(path.relative_to(vault_root))] == uid


def test_write_dossier_without_state_dir_records_no_manifest(vault_root, listing, tmp_path):
    uid = f"{listing.source}:{listing.raw_id}"
    md = render_dossier(listing, uid, "2026-07-17", "reason")

    write_dossier(vault_root, uid, md, listing.title, listing.company, "Other")

    assert not (tmp_path / "state" / "dossier_uids.json").exists()
