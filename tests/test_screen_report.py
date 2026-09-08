"""build_report is screen_report.py's whole decision surface: which dossiers
get grouped where, in what order, and which get excluded. Synthetic dossiers
built with the real vault_writer.writer.dump_frontmatter() so the frontmatter
shape (quoted date strings, blank-scalar nulls) matches production exactly."""
from pathlib import Path

from screen_report import build_report
from vault_writer.writer import DOSSIER_SUBPATH, dump_frontmatter, scan_dossiers


def _write_dossier(vault_root, bucket_folder, filename, *, company, title, url,
                   preference_tier=None, date_posted=None):
    folder = Path(vault_root) / DOSSIER_SUBPATH / bucket_folder
    folder.mkdir(parents=True, exist_ok=True)
    frontmatter = {
        "company": company, "title": title, "url": url,
        "preference_tier": preference_tier, "date_posted": date_posted,
    }
    (folder / filename).write_text(f"---\n{dump_frontmatter(frontmatter)}---\n\n# {title}\nbody\n")


def test_build_report_ranks_preferred_first_then_recency_and_excludes_viewed(tmp_path):
    _write_dossier(tmp_path, "1 - AI & ML", "a.md", company="Google", title="SWE Intern A",
                   url="https://x/a", preference_tier="high", date_posted="2026-01-01")
    _write_dossier(tmp_path, "1 - AI & ML", "b.md", company="Beta Corp", title="SWE Intern B",
                   url="https://x/b", date_posted="2026-09-01")
    _write_dossier(tmp_path, "1 - AI & ML", "c.md", company="Alpha Corp", title="SWE Intern C",
                   url="https://x/c", date_posted="2026-01-01")
    _write_dossier(tmp_path, "Other", "d.md", company="Other Co", title="Other Intern D",
                   url="https://x/d", date_posted="2026-05-01")
    _write_dossier(tmp_path, "Viewed", "e.md", company="Closed Co", title="Closed Intern E",
                   url="https://x/e", preference_tier="high", date_posted="2026-08-01")

    report = build_report(scan_dossiers(tmp_path), top_n=15)

    assert "Closed Co" not in report  # Viewed/ excluded entirely

    ai_ml_pos = report.index("## AI/ML")
    fullstack_pos = report.index("## Fullstack")
    ai_ml_section = report[ai_ml_pos:fullstack_pos]

    # Google (tier=high) ranks first despite the oldest date of the three
    assert ai_ml_section.index("Google") < ai_ml_section.index("Beta Corp")
    assert ai_ml_section.index("Google") < ai_ml_section.index("Alpha Corp")
    # among the two untiered companies, the more recent (Beta, 09-01) ranks before the older (Alpha, 01-01)
    assert ai_ml_section.index("Beta Corp") < ai_ml_section.index("Alpha Corp")

    assert "(3 total, showing top 3)" in ai_ml_section
    assert "Other Co" in report
    other_pos = report.index("## Other")
    assert "Other Co" in report[other_pos:]


def test_build_report_caps_at_top_n_but_reports_real_total(tmp_path):
    for i in range(5):
        _write_dossier(tmp_path, "Other", f"o{i}.md", company=f"Co{i}", title=f"Intern {i}",
                       url=f"https://x/{i}", date_posted=f"2026-01-0{i + 1}")

    report = build_report(scan_dossiers(tmp_path), top_n=2)

    other_pos = report.index("## Other")
    other_section = report[other_pos:]
    assert "(5 total, showing top 2)" in other_section
    # only the 2 most recent (Co4: 01-05, Co3: 01-04) should be listed
    assert "Co4" in other_section and "Co3" in other_section
    assert "Co0" not in other_section
