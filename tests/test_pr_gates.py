"""Unit tests for scripts/ci/pr_gates.py, fixtures from real repo data (2026-11-21)."""
import importlib.util
import pathlib

spec = importlib.util.spec_from_file_location(
    "pr_gates", pathlib.Path(__file__).resolve().parents[1] / "scripts/ci/pr_gates.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

GOOD = {"sha": "a" * 40, "subject": "Scrub GIT_* env in pre-push so worktree pushes cannot leak into tests",
        "parents": 1, "author_name": "Anant Gupta", "author_email": "anantmahi721@gmail.com",
        "committer_name": "Anant Gupta", "committer_email": "anantmahi721@gmail.com"}

# PR #17 real body shape: both sections present, boxes ticked.
BODY_OK = """## What changed
- x
## Verification
- [x] Branch is based on current `origin/master`
- [x] No secrets: N/A
## Repository conventions
- [x] No LLM was added to the unattended path
## Deferred or unverified
- [ ] not required
"""


def test_branch_name():
    assert g.branch_name("chore/pr-gates-and-ruleset") == []
    assert g.branch_name("fix/deadline-quota-and-reseed") == []
    assert g.branch_name("dependabot/pip/requests-2.35") == []
    # retired machine-prefixed form (PRs #12, #13)
    assert g.branch_name("dell-latitude/repo-cleanup-and-migration-prep")
    assert g.branch_name("acer-predator/repo-environment-setup")
    assert g.branch_name("fix/Under_Score")


def test_pr_title_real_titles():
    assert g.pr_title("Deadline stamping, quota-shortfall debate fix, reseed hardening") == []
    # PR #12, longest real title (79 chars) must pass
    assert g.pr_title("Pre-migration cleanup: land pending skills/agents, start two-laptop PR workflow") == []
    assert g.pr_title("Add things.")
    assert g.pr_title("WIP: add things")
    assert g.pr_title("[Draft] add things")
    assert g.pr_title("x" * 91)


def test_commits_real_incident_identity():
    bad = dict(GOOD, author_name="Test", author_email="test@example.com",
               committer_name="Test", committer_email="test@example.com")
    v = g.commits([bad])
    assert len(v) == 2 and all("identity" in x for x in v)
    assert g.commits([GOOD]) == []


def test_commits_other_violations():
    assert g.commits([dict(GOOD, parents=2)])
    assert g.commits([dict(GOOD, parents=0)])
    assert g.commits([dict(GOOD, subject="fixup! thing")])
    assert g.commits([dict(GOOD, subject="squash! thing")])
    assert g.commits([dict(GOOD, subject="wip save point")])
    assert g.commits([dict(GOOD, subject="x" * 101)])
    # real 88-char subject from master must pass
    assert g.commits([dict(GOOD, subject="dossier_uids.json: repoint 3 dossiers moved to Viewed/ by the 2026-10-04 freshness sweep"[:88])]) == []
    # the Actions bot identity is not a test identity
    bot = dict(GOOD, author_name="internship-research-loop bot", author_email="actions@users.noreply.github.com")
    assert g.commits([bot]) == []


def test_forbidden_paths():
    assert g.forbidden_paths(["Cover Letters/x.md"])
    for p in (".env", "a/.env.local", "prod.env", ".mcp.env", "k.pem", "k.key", "graphify-out/graph.json",
              ".worktrees/x/y", "a.orig", "a.rej", "x.bundle", "state/recovery-2026.json",
              ".claude/settings.local.json"):
        assert g.forbidden_paths([p]), p
    for p in ("core/filter.py", "docs/environment.md", "tests/test_pr_gates.py", ".claude/settings.json",
              "state/seen_ids.json", ".github/workflows/test.yml"):
        assert g.forbidden_paths([p]) == [], p


def test_template_sections():
    assert g.template_sections(BODY_OK) == []
    assert g.template_sections("")  # missing both
    assert len(g.template_sections(BODY_OK.replace("[x] No LLM", "[ ] No LLM"))) == 1
    # unchecked box outside the two required sections does not matter
    assert g.template_sections(BODY_OK.replace("## Repository conventions", "## Repository conventions\n")) == []
    assert g.template_sections(BODY_OK.replace("## Verification", "## Verify"))


def test_size_real_prs():
    assert g.size(15, 437 + 74, set()) == []      # PR #17 real size
    assert g.size(24, 541, set()) == []           # PR #13, largest legitimate
    assert g.size(95, 6469 + 192, set())          # PR #12 one-off
    assert g.size(95, 6469 + 192, {"large-ok"}) == []


def test_wip_limit():
    # 2026-11-21: #15 non-draft, #16 and #17 drafts
    opens = [{"number": 15, "draft": False}, {"number": 16, "draft": True}, {"number": 17, "draft": False}]
    assert g.wip_limit(17, opens, set())
    assert g.wip_limit(17, opens, {"parallel-ok"}) == []
    assert g.wip_limit(15, opens, set()) == []
    assert g.wip_limit(17, [{"number": 16, "draft": True}], set()) == []


def test_linked_issue_and_enforce_flag():
    assert g.linked_issue("Closes #12", set()) == []
    assert g.linked_issue("refs #3", set()) == []
    assert g.linked_issue("nothing", {"no-issue"}) == []
    assert g.linked_issue("nothing", set())
    assert "linked_issue" not in g.GATES_ENFORCE  # warn mode until P1.5b


def test_draft_gate_subset():
    assert g.DRAFT_GATES == {"branch_name", "pr_title", "commits", "forbidden_paths", "linked_issue"}
    assert "linked_issue" in g.ALL_GATES and len(g.ALL_GATES) == 8


def test_escape_blocks_command_injection():
    assert "\n" not in g.esc("a\n::error::pwn") and "%0A" in g.esc("a\n::error::pwn")
