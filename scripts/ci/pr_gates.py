#!/usr/bin/env python3
"""Deterministic PR gates (P1.5a). Stdlib + `gh` only: zero LLM, zero cost.

CI:      python3 scripts/ci/pr_gates.py          (reads the PR from GITHUB_EVENT_PATH)
Offline: python3 scripts/ci/pr_gates.py --pr 17  (same checks against a real PR via gh)

Each gate is a pure function returning a list of violation strings (empty = pass).
Every limit below cites the measurement it came from (CLAUDE.md convention 4).
Measured 2026-11-21 from `gh pr list --state all` (PRs #12-#17 are the only PRs that
exist; #1-#11 were direct pushes) and `git log origin/master` (826 commits, 77 human).
"""
import argparse
import json
import os
import re
import subprocess
import sys

# Gates in GATES_ENFORCE fail the check; the rest only annotate. linked_issue is enforced since
# the issue system exists (labels, forms, phase issues #19-#27, 2026-11-21).
# conventions_advisory is a heuristic (check_conventions.py checks 2-4 say "needs human
# judgment"), so it warns; check 1 (zero-LLM) is a hard fail.
GATES_ENFORCE = {"branch_name", "pr_title", "commits", "forbidden_paths", "linked_issue",
                 "tests_with_code", "workflow_lint", "conventions",
                 "template_sections", "size", "wip_limit"}
ALL_GATES = ["branch_name", "pr_title", "commits", "forbidden_paths", "linked_issue",
             "tests_with_code", "workflow_lint", "conventions", "conventions_advisory",
             "template_sections", "size", "wip_limit"]
# Cheap and substantive: run on drafts too. Only the "is it ready" gates wait for ready-for-review.
DRAFT_GATES = set(ALL_GATES) - {"template_sections", "size", "wip_limit"}

# Real data: current branches chore/pr-gates-and-ruleset, fix/deadline-quota-and-reseed,
# docs/two-laptop-workflow pass. The retired machine-prefixed form of PR #12
# (dell-latitude/repo-cleanup-and-migration-prep) and PR #13
# (acer-predator/repo-environment-setup) must fail.
BRANCH_RE = re.compile(r"^(feature|fix|docs|chore)/[a-z0-9]+(-[a-z0-9]+)*$")

# PR titles #12-#17 measured 38-79 chars (79, 75, 38, 51, 61, 63): 90 leaves headroom
# over the longest real title without admitting essay-length ones.
TITLE_MAX = 90
# Human commit subjects (75 of 826, bot excluded): 73 of 75 are <= 100; the two over are
# 115 and 127 chars from before the PR workflow began (2026-07). Recent ones: 88, 81, 80, 76.
SUBJECT_MAX = 100
WIP_PREFIX_RE = re.compile(r"^\s*[\[(]?\s*(wip|draft)\b", re.I)
COMMIT_BAD_RE = re.compile(r"^(fixup!|squash!)|\bwip\b", re.I)
# Real incident 2026-11-21: a pre-push test fixture rewrote a worktree's identity and
# authored a junk commit as `Test <test@example.com>` (see scripts/hooks/pre-push).
BAD_IDENTITY_NAMES = {"test"}
BAD_IDENTITY_EMAILS = {"test@example.com"}

# Public repo: none of these may ever land. Checked 2026-11-21: `git ls-files` matches
# only graphify-out/.gitignore (added by PR #12, harmless, and the only tracked file there),
# so graphify-out/ is forbidden except that one file (recalibrated after `--pr 12` flagged it).
FORBIDDEN_RES = [re.compile(p) for p in (
    r"^Cover Letters/", r"(^|/)[^/]*\.env($|\.)", r"\.mcp\.env", r"\.(pem|key)$",
    r"^graphify-out/(?!\.gitignore$)", r"^\.worktrees/", r"\.(orig|rej|bundle)$", r"recovery-",
    r"^\.claude/settings\.local\.json$")]

# Legit PRs #13-#17: 4-24 files, 157-541 lines (max: #13 541 lines/24 files; #17 511 lines
# /15 files). #12 (95 files, 6661 lines, one-off migration cleanup) is the only outlier and
# is exactly what the `large-ok` label is for. Limits are ~1.5x the largest legit PR.
SIZE_MAX_FILES = 36
SIZE_MAX_LINES = 800

REQUIRED_SECTIONS = ("Verification", "Repository conventions")
ISSUE_RE = re.compile(r"\b(closes|fixes|resolves|refs)\s+#\d+", re.I)

# CLAUDE.md: tests/ mirrors core/, ingestion/, vault_writer/ file-for-file. Measured 2026-11-21:
# 35 of 35 human commits since 2026-07-01 that touched these files also touched tests/.
CODE_RE = re.compile(r"^(core|ingestion|vault_writer)/.+\.py$|^(run_pipeline|recheck)\.py$")
# Third-party actions must be pinned to a full SHA; actions/* and github/* may use version tags.
# Measured 2026-11-21: all 5 existing workflows use only actions/checkout@v4 and actions/setup-python@v5.
FIRST_PARTY_OWNERS = {"actions", "github"}
SHA_RE = re.compile(r"[0-9a-f]{40}")
# PR text must never reach a shell: same class of bug fixed in reseed.yml (e115db4).
UNSAFE_EXPR_RE = re.compile(r"\$\{\{\s*(github\.event\.|github\.head_ref)")
CONVENTIONS_PATH = ".claude/skills/review-loop-change/scripts/check_conventions.py"


def branch_name(branch):
    if branch.startswith("dependabot/") or BRANCH_RE.match(branch):
        return []
    return [f"branch '{branch}' must match {BRANCH_RE.pattern} (or dependabot/*)"]


def pr_title(title):
    out = []
    if not title.strip():
        out.append("title is empty")
    if len(title) > TITLE_MAX:
        out.append(f"title is {len(title)} chars, max {TITLE_MAX}")
    if title.rstrip().endswith("."):
        out.append("title ends with a period")
    if WIP_PREFIX_RE.match(title):
        out.append("title starts with WIP/Draft; use a draft PR instead")
    return out


def commits(commit_list):
    """commit_list items: {sha, subject, parents, author_name, author_email,
    committer_name, committer_email}."""
    out = []
    for c in commit_list:
        sha = c["sha"][:7]
        if c["parents"] != 1:
            out.append(f"{sha}: merge commit ({c['parents']} parents); rebase instead")
        if len(c["subject"]) > SUBJECT_MAX:
            out.append(f"{sha}: subject is {len(c['subject'])} chars, max {SUBJECT_MAX}")
        if COMMIT_BAD_RE.search(c["subject"]):
            out.append(f"{sha}: fixup!/squash!/WIP subject '{c['subject'][:40]}'")
        for role in ("author", "committer"):
            name, email = c[f"{role}_name"].strip().lower(), c[f"{role}_email"].strip().lower()
            if name in BAD_IDENTITY_NAMES or email in BAD_IDENTITY_EMAILS:
                out.append(f"{sha}: {role} identity is '{c[role + '_name']} <{c[role + '_email']}>'")
    return out


def forbidden_paths(paths):
    return [f"forbidden path: {p}" for p in paths if any(r.search(p) for r in FORBIDDEN_RES)]


def _section(body, title):
    m = re.search(rf"^#{{1,6}}[ \t]*{re.escape(title)}[ \t]*$", body, re.I | re.M)
    if not m:
        return None
    rest = body[m.end():]
    nxt = re.search(r"^#{1,6}[ \t]", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def template_sections(body):
    out = []
    for title in REQUIRED_SECTIONS:
        sec = _section(body or "", title)
        if sec is None:
            out.append(f"missing '## {title}' section")
        elif re.search(r"^\s*[-*] \[ \]", sec, re.M):
            n = len(re.findall(r"^\s*[-*] \[ \]", sec, re.M))
            out.append(f"'{title}' has {n} unchecked box(es); check them (N/A counts: tick and write N/A)")
    return out


def size(files, lines, labels):
    if "large-ok" in labels:
        return []
    out = []
    if files > SIZE_MAX_FILES:
        out.append(f"{files} changed files, max {SIZE_MAX_FILES} (label large-ok overrides)")
    if lines > SIZE_MAX_LINES:
        out.append(f"{lines} added+deleted lines, max {SIZE_MAX_LINES} (label large-ok overrides)")
    return out


def wip_limit(number, open_prs, labels):
    """open_prs: [{number, draft}]. Real data: #15-#17 were opened together 2026-11-21."""
    if "parallel-ok" in labels:
        return []
    older = sorted(p["number"] for p in open_prs if not p["draft"] and p["number"] < number)
    return [f"older open non-draft PR(s): {', '.join('#%d' % n for n in older)}; "
            "merge or draft them first (label parallel-ok overrides)"] if older else []


def linked_issue(body, labels):
    if "no-issue" in labels or ISSUE_RE.search(body or ""):
        return []
    return ["no 'Closes/Fixes/Resolves/Refs #N' in the body (label no-issue overrides)"]


def tests_with_code(paths, labels):
    if "no-tests-ok" in labels:
        return []
    if any(CODE_RE.match(p) for p in paths) and not any(p.startswith("tests/") for p in paths):
        return ["unattended-path code changed but nothing under tests/ did "
                "(tests mirror code; label no-tests-ok overrides)"]
    return []


def workflow_lint(path, text):
    """Static checks for one workflow file. shortcut: YAML + regex only, no expression
    evaluation; upgrade to actionlint if the workflows get complex."""
    import yaml
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        return [f"{path}: invalid YAML ({e})"]
    out = []
    on = doc.get(True, doc.get("on"))  # YAML 1.1 parses the key `on` as boolean True
    triggers = set(on) if isinstance(on, (dict, list)) else {on}
    jobs = doc.get("jobs") or {}
    if "pull_request_target" in triggers:  # runs the BASE workflow with a token; safe only if PR code is never checked out
        for jname, job in jobs.items():
            for step in (job or {}).get("steps") or []:
                if str(step.get("uses", "")).startswith("actions/checkout") and (step.get("with") or {}).get("ref"):
                    out.append(f"{path}: job {jname} checks out an explicit ref under pull_request_target (would run PR code with secrets)")
    if "permissions" not in doc and not all("permissions" in (j or {}) for j in jobs.values()):
        out.append(f"{path}: no `permissions:` block (default token is too broad)")
    for jname, job in jobs.items():
        for step in (job or {}).get("steps") or []:
            if UNSAFE_EXPR_RE.search(step.get("run") or ""):
                out.append(f"{path}: job {jname} interpolates PR-controlled text into a run script; use env:")
            uses = step.get("uses")
            if uses and not uses.startswith("./"):
                owner, ref = uses.split("/")[0], uses.rpartition("@")[2]
                if "@" not in uses or ref in ("main", "master"):
                    out.append(f"{path}: `{uses}` is unpinned")
                elif owner not in FIRST_PARTY_OWNERS and not SHA_RE.fullmatch(ref):
                    out.append(f"{path}: third-party action `{uses}` must be pinned to a full SHA")
    return out


def conventions(diff_text):
    """Mechanical CLAUDE.md conventions via the repo's own check_conventions.py (single
    source of truth). Returns (enforced, advisory): check 1 (zero-LLM) is a hard fail,
    checks 2-4 are heuristics."""
    import importlib.util
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    spec = importlib.util.spec_from_file_location("check_conventions", os.path.join(root, CONVENTIONS_PATH))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_conventions"] = mod  # dataclasses needs the module registered
    spec.loader.exec_module(mod)
    hunks = mod.parse_diff(diff_text)
    enforced = [f"{f.file}:{f.line_no} {f.detail}" for f in mod.check_1_zero_llm(hunks)]
    advisory = [f"{f.file}:{f.line_no} [{f.check}] {f.detail}"
                for f in mod.check_2_permissive_default(hunks) + mod.check_3_write_gate_order(hunks)
                + mod.check_4_cited_real_data(hunks)]
    return enforced, advisory


# ---- thin I/O layer ---------------------------------------------------------------

def gh_api(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def gh_text(path, accept="raw"):
    """Raw file contents (accept=raw) or a unified diff (accept=diff) from the API."""
    mime = "application/vnd.github.raw" if accept == "raw" else "application/vnd.github.diff"
    return subprocess.run(["gh", "api", "-H", f"Accept: {mime}", path],
                          capture_output=True, text=True, check=True).stdout


def gh_pages(path):
    out, page = [], 1
    sep = "&" if "?" in path else "?"
    while True:
        chunk = gh_api(f"{path}{sep}per_page=100&page={page}")
        out += chunk
        if len(chunk) < 100:
            return out
        page += 1


def load_commits(repo, n):
    res = []
    for c in gh_pages(f"repos/{repo}/pulls/{n}/commits"):
        k = c["commit"]
        res.append({"sha": c["sha"], "subject": k["message"].split("\n", 1)[0],
                    "parents": len(c["parents"]),
                    "author_name": k["author"]["name"], "author_email": k["author"]["email"],
                    "committer_name": k["committer"]["name"],
                    "committer_email": k["committer"]["email"]})
    return res


def esc(s):  # GitHub workflow-command escaping: user text can never start a new command
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def run(pr, repo):
    n, draft = pr["number"], bool(pr.get("draft"))
    labels = {l["name"] for l in pr.get("labels", [])}
    gates = [g for g in ALL_GATES if not draft or g in DRAFT_GATES]
    results = {}
    # Dependabot bodies are machine-generated: they can never carry the human checklist or
    # an issue link. No Dependabot PR exists yet (gh pr list, 2026-11-21): exemption is by design.
    bot = pr.get("user", {}).get("login") == "dependabot[bot]"
    files = gh_pages(f"repos/{repo}/pulls/{n}/files") if set(gates) & {
        "forbidden_paths", "tests_with_code", "workflow_lint"} else []
    live = [f["filename"] for f in files if f["status"] != "removed"]
    for g in gates:
        if g == "branch_name":
            results[g] = branch_name(pr["head"]["ref"])
        elif g == "pr_title":
            results[g] = pr_title(pr["title"])
        elif g == "commits":
            results[g] = commits(load_commits(repo, n))
        elif g == "forbidden_paths":
            results[g] = forbidden_paths(live)
        elif g == "tests_with_code":
            results[g] = tests_with_code(live, labels)
        elif g == "workflow_lint":
            results[g] = [v for p in live if re.match(r"^\.github/workflows/[^/]+\.ya?ml$", p)
                          for v in workflow_lint(p, gh_text(f"repos/{repo}/contents/{p}?ref={pr['head']['sha']}"))]
        elif g in ("conventions", "conventions_advisory"):
            if "_conv" not in results:
                results["_conv"] = conventions(gh_text(f"repos/{repo}/pulls/{n}", accept="diff"))
            results[g] = results["_conv"][0 if g == "conventions" else 1]
        elif g == "linked_issue":
            results[g] = [] if bot else linked_issue(pr.get("body"), labels)
        elif g == "template_sections":
            results[g] = [] if bot else template_sections(pr.get("body"))
        elif g == "size":
            results[g] = size(pr["changed_files"], pr["additions"] + pr["deletions"], labels)
        elif g == "wip_limit":
            opens = gh_pages(f"repos/{repo}/pulls?state=open")
            results[g] = wip_limit(n, [{"number": p["number"], "draft": p["draft"]} for p in opens], labels)
    results.pop("_conv", None)
    return results, draft


def report(n, results, draft):
    rows, failed = [], False
    for g in ALL_GATES:
        if g not in results:
            rows.append(f"| {g} | - | skipped (draft) | |")
            continue
        v, enforce = results[g], g in GATES_ENFORCE
        status = "pass" if not v else ("FAIL" if enforce else "warn")
        failed |= bool(v) and enforce
        rows.append(f"| {g} | {'enforce' if enforce else 'warn'} | {status} | "
                    f"{'; '.join(v).replace('|', '/').replace(chr(10), ' ')} |")
        for msg in v:
            print(f"::{'error' if enforce else 'warning'} title=pr-gates {g}::{esc(msg)}")
    table = (f"### PR gates for #{n}{' (draft)' if draft else ''}\n\n"
             "| Gate | Mode | Result | Details |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
    print(table)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(table)
    return failed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr", type=int, help="offline mode: check this real PR via gh")
    a = ap.parse_args(argv)
    repo = os.environ.get("GITHUB_REPOSITORY") or subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        capture_output=True, text=True, check=True).stdout.strip()
    if a.pr:
        pr = gh_api(f"repos/{repo}/pulls/{a.pr}")
    else:
        with open(os.environ["GITHUB_EVENT_PATH"]) as f:
            pr = json.load(f)["pull_request"]
    results, draft = run(pr, repo)
    return 1 if report(pr["number"], results, draft) else 0


if __name__ == "__main__":
    sys.exit(main())
