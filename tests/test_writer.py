import json
import shutil
from pathlib import Path

import pytest

from ingestion.normalize import normalize_simplify
from vault_writer.writer import render_dossier, slugify_uid, write_dossier

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
def listing():
    raw = json.loads((FIXTURES / "simplifyjobs.json").read_text())[0]
    return normalize_simplify(raw)


def test_slugify_uid_is_filesystem_safe():
    assert slugify_uid("SimplifyJobs:ada5c220-536e-454a-8ba0-1f7629d949e6") == \
        "simplifyjobs-ada5c220-536e-454a-8ba0-1f7629d949e6"


def test_write_dossier_writes_expected_file(vault_root, listing):
    uid = f"{listing.source}:{listing.raw_id}"
    md = render_dossier(listing, uid, "2026-07-17", "Junior-eligible, Summer 2027, Software Engineering")

    path = write_dossier(vault_root, uid, md)

    expected_path = vault_root / DOSSIERS_SUBPATH / f"{slugify_uid(uid)}.md"
    assert path == expected_path
    assert path.read_text() == md


def test_write_dossier_is_idempotent_on_uid(vault_root, listing):
    uid = f"{listing.source}:{listing.raw_id}"
    md_v1 = render_dossier(listing, uid, "2026-07-17", "first pass")
    write_dossier(vault_root, uid, md_v1)

    md_v2 = render_dossier(listing, uid, "2026-07-18", "second pass, re-run same day")
    write_dossier(vault_root, uid, md_v2)

    dossiers_dir = vault_root / DOSSIERS_SUBPATH
    files = [f for f in dossiers_dir.iterdir() if f.suffix == ".md"]
    assert len(files) == 1
    assert files[0].read_text() == md_v2


def test_write_dossier_creates_missing_dossiers_dir(tmp_path, listing):
    """vault_root with no pre-existing Dossiers/ folder at all still works."""
    bare_vault = tmp_path / "bare_vault"
    bare_vault.mkdir()
    uid = f"{listing.source}:{listing.raw_id}"
    md = render_dossier(listing, uid, "2026-07-17", "reason")

    path = write_dossier(bare_vault, uid, md)

    assert path.exists()
