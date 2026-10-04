import pytest

from grade_resume import RESUME_RELPATH, grade, keywords, parse_bullets, resolve_resume_path

RESUME = """
## Skills
- *Programming:* Python, Rust, TypeScript `#skill/programming`
- untagged bullet that must be ignored
## Work Experience Bullets
- Built data pipelines with Postgres and Docker `#skill/infra #skill/ai`
- Lead campus tours, public speaking `#skill/soft`
"""


def test_parse_bullets_keeps_only_tagged():
    bullets = parse_bullets(RESUME)
    assert len(bullets) == 3
    assert bullets[1] == ("Built data pipelines with Postgres and Docker",
                          ["#skill/infra", "#skill/ai"])


def test_keywords_drops_stopwords_keeps_tech_tokens():
    ks = keywords("Experience with Python and node.js required")
    assert "python" in ks and "node.js" in ks
    assert "with" not in ks and "required" not in ks


def test_grade_ranks_matching_bullet_first():
    jd = "Looking for interns with Python, Postgres, Docker and data pipelines."
    ranked = grade(RESUME, jd)
    assert ranked[0][1].startswith("Built data pipelines")
    assert ranked[0][0] >= 3  # postgres, docker, data, pipelines
    assert ranked[-1][0] == 0  # the public-speaking bullet matches nothing


def test_resolve_resume_path_explicit_arg_wins_over_env():
    assert resolve_resume_path("/x/My Resume.md", environ={"JARVIS_DIR": "/vault"}) == "/x/My Resume.md"


def test_resolve_resume_path_defaults_under_jarvis_dir():
    path = resolve_resume_path(None, environ={"JARVIS_DIR": "/home/someone/Jarvis"})
    assert path == "/home/someone/Jarvis/" + RESUME_RELPATH
    assert "/mnt/d" not in path  # the old laptop-specific hardcode


def test_resolve_resume_path_exits_with_message_when_nothing_configured():
    with pytest.raises(SystemExit) as exc:
        resolve_resume_path(None, environ={})
    assert "JARVIS_DIR" in str(exc.value)
