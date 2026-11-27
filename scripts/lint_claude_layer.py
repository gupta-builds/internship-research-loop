"""
internship-research-loop: Claude-layer lint
Topic: check agents, skills, instruction files and settings against the C1 rules.

Usage: uv run python scripts/lint_claude_layer.py [--root PATH]
Prints one finding per line as `path:line [check] message`, then a count line.
Exit 0 pass, 1 findings, 2 the lint could not run.

Files that exist today and are retired by a later phase sit in LEGACY with the
phase that retires them and the checks they are excused from. The phase that
deletes a file deletes its entry.
"""
import argparse
import json
import pathlib
import re
import sys

import yaml

#### rules, from the C1 Execution Map (2026-11-26) and the Claude Code docs

AGENT_KEYS = {"name", "description", "tools", "disallowedTools", "model", "effort",
              "skills", "hooks", "color", "maxTurns"}
AGENT_BANNED_TOOLS = {"Agent", "Task", "AskUserQuestion"}
AGENT_BODY_MAX = 40
AGENT_DESC_MAX = 300

# Source: https://code.claude.com/docs/en/skills (frontmatter reference, read 2026-11-26)
SKILL_KEYS = {"name", "description", "when_to_use", "argument-hint", "arguments",
              "disable-model-invocation", "user-invocable", "allowed-tools", "model",
              "effort", "context", "agent", "hooks", "paths", "shell"}
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_NAME_MAX = 64
SKILL_DESC_MAX = 1024
SKILL_LINES_MAX = 500                                  # SKILL.md stays under this
REF_RE = re.compile(r"(?<![\w/.-])((?:reference|references|scripts)/[\w./-]+\w)")

# the seven planned command skills; a command sets disable-model-invocation: true
COMMANDS = {"promote", "prepare-application", "daily-batch", "review-code",
            "start-phase", "finish-phase", "handoff"}
# procedure skills the main session runs itself, so no agent owns them
MAIN_SESSION = {"generating-resume-docx", "generating-cover-letter-docx"}
# Claude Code built-in slash commands an instruction file may name
BUILTIN_COMMANDS = {"hooks", "permissions", "memory", "clear", "compact", "skill-doctor"}

CLAUDE_MD_MAX = 90
STALE_RES = [re.compile(p) for p in (r"\.cursor/skills/", r"second-brain-claudekit",
                                     r"/home/", r"/mnt/")]
REQUIRED_PHRASES = (
    "untrusted data, never instructions",              # untrusted text
    "Never submit an application",                     # never submit
    "send a message",                                  # never send
    "may use only:",                                   # closed source list
)
SLASH_RE = re.compile(r"`/([a-z][a-z0-9-]*)`")

DENY_REQUIRED = ("Read(.env)", "Read(.env.*)", "Read(/graphify-out/**)", "Edit(/graphify-out/**)")
PROJECT_DIR = "${CLAUDE_PROJECT_DIR}"

LEGACY = {
    # path: (retiring phase, checks excused)
    ".claude/agents/applying.md": ("C4", {"agent"}),
    ".claude/agents/cover-letter-builder.md": ("C4", {"agent"}),
    ".claude/agents/loop-verifier.md": ("C5", {"agent"}),
    ".claude/agents/testing-tools.md": ("C5", {"agent"}),
    ".claude/skills/tailoring-application": ("C4", {"ownership"}),
    ".claude/skills/testing": ("C5", {"skill", "ownership"}),
    ".claude/skills/review-loop-change": ("C5", {"skill", "ownership"}),
    ".claude/skills/generating-resume-docx": ("C4", {"stale-path"}),
    ".claude/skills/generating-cover-letter-docx": ("C4", {"stale-path"}),
}


#### helpers

def read_frontmatter(path):
    """return (frontmatter dict, body lines) of a markdown file, or raise ValueError."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("no frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("frontmatter not closed")
    try:
        data = yaml.safe_load(parts[1])
    # Source: https://pyyaml.org/wiki/PyYAMLDocumentation (parse errors raise YAMLError)
    except yaml.YAMLError as e:
        raise ValueError(f"frontmatter does not parse: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data, parts[2].strip().splitlines()


def as_list(value):
    """return a frontmatter list field as a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return [str(v).strip() for v in value]


def skill_names(root):
    """return the set of skill folder names under .claude/skills."""
    folder = root / ".claude" / "skills"
    return {p.name for p in folder.iterdir() if p.is_dir()} if folder.is_dir() else set()


#### checks: each returns a list of (relative path, line, check, message)

def check_agents(root, skills):
    """return findings for every .claude/agents/*.md file."""
    out = []
    for path in sorted((root / ".claude" / "agents").glob("*.md")):
        rel = path.relative_to(root).as_posix()
        try:
            fm, body = read_frontmatter(path)
        except ValueError as e:
            out.append((rel, 1, "agent", str(e)))
            continue
        for key in ("name", "description"):
            if not fm.get(key):
                out.append((rel, 1, "agent", f"missing {key}"))
        for key in sorted(set(fm) - AGENT_KEYS):
            out.append((rel, 1, "agent", f"key '{key}' is not allowed"))
        for tool in as_list(fm.get("tools")):
            if tool in AGENT_BANNED_TOOLS:
                out.append((rel, 1, "agent", f"tool '{tool}' is not allowed in an agent"))
        for name in as_list(fm.get("skills")):
            if name not in skills:
                out.append((rel, 1, "agent", f"skills: '{name}' is not a skill folder"))
        if len(body) > AGENT_BODY_MAX:
            out.append((rel, 1, "agent", f"body is {len(body)} lines, max {AGENT_BODY_MAX}"))
        if len(str(fm.get("description", ""))) > AGENT_DESC_MAX:
            out.append((rel, 1, "agent", f"description over {AGENT_DESC_MAX} characters"))
    return out


def check_skills(root):
    """return findings for every .claude/skills/<name>/SKILL.md."""
    out = []
    for folder in sorted((root / ".claude" / "skills").glob("*/")):
        path = folder / "SKILL.md"
        rel = folder.relative_to(root).as_posix()
        if not path.is_file():
            out.append((rel, 0, "skill", "no SKILL.md"))
            continue
        try:
            fm, _ = read_frontmatter(path)
        except ValueError as e:
            out.append((rel, 1, "skill", str(e)))
            continue
        name, desc = str(fm.get("name", "")), str(fm.get("description", "") or "")
        if name != folder.name:
            out.append((rel, 1, "skill", f"name '{name}' differs from the folder"))
        if len(name) > SKILL_NAME_MAX or not SKILL_NAME_RE.match(name):
            out.append((rel, 1, "skill", "name must be lowercase words joined by hyphens, max 64"))
        if not desc.strip() or len(desc) > SKILL_DESC_MAX or "<" in desc or ">" in desc:
            out.append((rel, 1, "skill", "description must be 1 to 1,024 characters with no < or >"))
        for key in sorted(set(fm) - SKILL_KEYS):
            out.append((rel, 1, "skill", f"key '{key}' is not a documented skill field"))
        if folder.name in COMMANDS and fm.get("disable-model-invocation") is not True:
            out.append((rel, 1, "skill", "a command skill sets disable-model-invocation: true"))
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) >= SKILL_LINES_MAX:
            out.append((rel, 0, "skill", f"SKILL.md is {len(lines)} lines, must be under {SKILL_LINES_MAX}"))
        for n, line in enumerate(lines, 1):
            for ref in REF_RE.findall(line):
                if ref.count("/") != 1:
                    out.append((rel, n, "skill", f"{ref} is more than one level deep"))
                elif not (folder / ref).exists():
                    out.append((rel, n, "skill", f"{ref} does not exist"))
            out.extend((rel, n, "stale-path", f"stale path: {r.pattern}") for r in STALE_RES if r.search(line))
    return out


def check_ownership(root, skills):
    """return findings for procedure skills no agent, command set or main session owns."""
    owners = {}
    for path in sorted((root / ".claude" / "agents").glob("*.md")):
        try:
            fm, _ = read_frontmatter(path)
        except ValueError:
            continue                                   # check_agents already reports it
        for name in as_list(fm.get("skills")):
            owners.setdefault(name, []).append(path.stem)
    out = []
    for name in sorted(skills):
        rel = f".claude/skills/{name}"
        count = len(owners.get(name, []))
        if name in COMMANDS or name in MAIN_SESSION:
            continue
        if count != 1:
            out.append((rel, 0, "ownership", f"owned by {count} agents, must be exactly 1"))
    return out


def check_text_file(root, rel, skills, instruction):
    """return findings for one instruction or rule file."""
    path = root / rel
    if not path.is_file():
        return [(rel, 0, "instruction", "file is missing")] if instruction else []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []
    for n, line in enumerate(lines, 1):
        out.extend((rel, n, "stale-path", f"stale path: {r.pattern}") for r in STALE_RES if r.search(line))
        if "graphify-out" in line and "never" not in line.lower():
            out.append((rel, n, "instruction", "graphify-out/ named without 'never'"))
        for name in SLASH_RE.findall(line):
            if name not in skills and name not in BUILTIN_COMMANDS:
                out.append((rel, n, "cited-skill", f"/{name} is not a skill or built-in command"))
    if instruction:
        if len(lines) > CLAUDE_MD_MAX:
            out.append((rel, 0, "instruction", f"{len(lines)} lines, max {CLAUDE_MD_MAX}"))
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                out.append((rel, 0, "instruction", f"required phrase missing: '{phrase}'"))
    return out


def check_instructions(root, skills):
    """return findings for CLAUDE.md and the .claude/rules files."""
    out = check_text_file(root, "CLAUDE.md", skills, instruction=True)
    for path in sorted((root / ".claude" / "rules").glob("*.md")):
        out.extend(check_text_file(root, path.relative_to(root).as_posix(), skills, instruction=False))
    return out


def hook_script(root, hook):
    """return the script path a command hook runs, or None if none is named."""
    words = [hook.get("command", "")] + list(hook.get("args", []))
    for word in words:
        for token in str(word).split():
            token = token.strip("'\"")
            if PROJECT_DIR in token:
                return root / token.replace(PROJECT_DIR, "").lstrip("/")
    return None


def check_settings(root):
    """return findings for .claude/settings.json."""
    rel = ".claude/settings.json"
    try:
        data = json.loads((root / rel).read_text(encoding="utf-8"))
    # Source: https://docs.python.org/3/library/json.html (JSONDecodeError subclasses ValueError)
    except (OSError, ValueError) as e:
        return [(rel, 0, "settings", f"not valid JSON: {e}")]
    out = []
    deny = (data.get("permissions") or {}).get("deny", [])
    out.extend((rel, 0, "settings", f"deny entry missing: {d}") for d in DENY_REQUIRED if d not in deny)
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                kind = hook.get("type")
                if kind != "command":
                    out.append((rel, 0, "settings", f"{event}: hook type '{kind}' is not allowed"))
                    continue
                script = hook_script(root, hook)
                if script is None or not script.is_file():
                    out.append((rel, 0, "settings", f"{event}: hook script does not resolve: {script}"))
    return out


def check_legacy(root):
    """return findings for LEGACY entries that name a missing file or no phase."""
    out = []
    for rel, (phase, _) in sorted(LEGACY.items()):
        if not (root / rel).exists():
            out.append((rel, 0, "legacy", "LEGACY entry names a missing file; delete the entry"))
        if not re.match(r"^C\d$", phase or ""):
            out.append((rel, 0, "legacy", "LEGACY entry has no retiring phase"))
    return out


#### driver

def excused(finding):
    """return True if a LEGACY entry excuses this finding."""
    rel, _, check, _ = finding
    for path, (_, checks) in LEGACY.items():
        if check in checks and (rel == path or rel.startswith(path + "/")):
            return True
    return False


def lint(root):
    """return the findings for the Claude layer under root, LEGACY excusals applied."""
    skills = skill_names(root)
    found = (check_agents(root, skills) + check_skills(root) + check_ownership(root, skills)
             + check_instructions(root, skills) + check_settings(root))
    return [f for f in found if not excused(f)] + check_legacy(root)


def main(argv=None):
    """print findings and return the exit code."""
    ap = argparse.ArgumentParser(description="check the Claude layer against the C1 rules")
    ap.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent.parent)
    args = ap.parse_args(argv)
    if not (args.root / ".claude").is_dir():
        print(f"lint could not run: no .claude folder under {args.root}", file=sys.stderr)
        return 2
    findings = lint(args.root)
    for rel, line, check, msg in findings:
        print(f"{rel}:{line} [{check}] {msg}")
    print(f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
