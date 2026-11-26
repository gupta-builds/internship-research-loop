"""
internship-research-loop: PreToolUse hook for Bash
Topic: block the git, rm, pip, secret-file and graphify-out commands the repo rules forbid.

Reads the hook payload from stdin. Splits the command into segments at ; && || | &
and parentheses, then matches each segment's argv, never the raw text, so a quoted
message that mentions a blocked command passes. Exit 2 blocks and the stderr text
reaches Claude; an unreadable payload exits 0 with a warning (hook convention).
"""
import json
import os
import re
import shlex
import subprocess
import sys

SEPARATORS = {";", "&&", "||", "|", "|&", "&", "(", ")", ";;"}
PIPES = {"|", "|&"}
WRAPPERS = {"env", "sudo", "command", "nohup", "time", "exec"}
PAGERS = {"head", "tail", "grep", "sed", "awk", "less", "more"}
PROTECTED_BRANCHES = {"master", "main"}
MESSAGE_FLAGS = {"-m", "--message", "--title", "--body", "-t", "-b"}   # values are prose, not paths
ENV_RE = re.compile(r"(?:^|[^\w.])(\.mcp\.env|\.env(?:\.(?!example\b)[\w-]+)*)(?![\w.-])")
GH_WRITE_PATH_RE = re.compile(r"pulls/[^/]+/merge|git/refs")


#### parsing

def segments(command):
    """return a list of (argv, piped_into_next) for each simple command in the line."""
    out = []
    for line in command.splitlines():
        # Source: https://docs.python.org/3/library/shlex.html (punctuation_chars returns
        # runs of ();<>|& as single tokens; use with posix and whitespace_split)
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        try:
            tokens = list(lexer)
        except ValueError:                                   # unclosed quote: fall back to words
            tokens = line.split()
        # shortcut: text inside $(...) and backticks is matched as words only, not as a
        # nested command line; upgrade if a real bypass through them shows up.
        tokens = [t.strip("`") for t in tokens if t.strip("`")]
        argv = []
        for tok in tokens:
            if tok in SEPARATORS:
                if argv:
                    out.append((argv, tok in PIPES))
                argv = []
            elif tok == "$":
                continue                                     # the $ of $( before its (
            else:
                argv.append(tok)
        if argv:
            out.append((argv, False))
    return out


def strip_wrappers(argv):
    """return argv without leading VAR=value assignments and wrappers like env or sudo."""
    i = 0
    while i < len(argv) and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[i]) or argv[i] in WRAPPERS):
        i += 1
    return argv[i:]


def short_flags(args):
    """return the set of letters in single-dash flag clusters such as -am."""
    letters = set()
    for a in args:
        if re.match(r"^-[A-Za-z]+$", a):
            letters.update(a[1:])
    return letters


def current_branch(cwd):
    """return the branch checked out in cwd, or '' if unknown."""
    try:
        r = subprocess.run(["git", "-C", cwd or ".", "branch", "--show-current"],
                           capture_output=True, text=True, timeout=5)
    # Source: https://docs.python.org/3/library/subprocess.html (run raises TimeoutExpired)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip()


#### git rules

def git_parts(args):
    """return (-c values, subcommand, its arguments) from git's arguments."""
    configs, i = [], 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] in ("-c", "-C") and i + 1 < len(args):
            if args[i] == "-c":
                configs.append(args[i + 1])
            i += 2
        else:
            i += 1
    if i >= len(args):
        return configs, "", []
    return configs, args[i], args[i + 1:]


def check_git_add(args):
    """return a problem if git add stages everything."""
    after_dashdash = args[args.index("--") + 1:] if "--" in args else []
    wide = {"-A", "--all", ".", "./", ":/", ":"}
    if wide & set(args) or wide & set(after_dashdash) or "A" in short_flags(args):
        return ("git add -A, --all or . stages everything", "add files by name")
    return None


def check_git_commit(args):
    """return a problem if git commit stages everything or skips hooks."""
    flags = short_flags(args)
    if "--all" in args or "a" in flags:
        return ("git commit -a stages every tracked change", "git add the files by name, then commit")
    if "--no-verify" in args or "n" in flags:
        return ("--no-verify and -n skip the hooks", "fix what the hook reports")
    return None


def check_git_push(args, cwd):
    """return a problem if git push forces, skips hooks or targets master or main."""
    if "--no-verify" in args:
        return ("--no-verify skips the pre-push hook", "fix what the hook reports")
    lease = any(a.startswith("--force-with-lease") for a in args)
    if "--force" in args or "f" in short_flags(args):
        return ("a plain force push is blocked", "use --force-with-lease on your own branch")
    if "--all" in args or "--mirror" in args:
        return ("--all and --mirror push master too", "push your branch by name")
    positional = [a for a in args if not a.startswith("-")]
    for ref in positional[1:]:
        if ref.startswith("+") and not lease:
            return ("a + refspec force-pushes", "use --force-with-lease on your own branch")
        dst = ref.lstrip("+").split(":")[-1].removeprefix("refs/heads/")
        if dst in PROTECTED_BRANCHES:
            return (f"a push to {dst} is blocked", "push your branch; Anant merges the PR")
    if len(positional) < 2 and current_branch(cwd) in PROTECTED_BRANCHES:
        return ("a bare git push from master or main pushes it", "push from your worktree's branch")
    return None


def check_git_config(configs, args):
    """return a problem if git config writes, or -c sets core.hooksPath."""
    if any(c.lower().startswith("core.hookspath") for c in configs):
        return ("git -c core.hooksPath bypasses the hooks", "run the command without it")
    if args[:1] in (["get"], ["list"]):
        return None
    writes = {"--unset", "--unset-all", "--add", "--replace-all", "--rename-section",
              "--remove-section", "--edit", "-e", "set", "unset"}
    positional, i = [], 0
    while i < len(args):
        if args[i] in ("-f", "--file", "--blob", "--type", "--default"):
            i += 2
            continue
        if not args[i].startswith("-"):
            positional.append(args[i])
        i += 1
    if writes & set(args) or len(positional) >= 2:
        return ("writing git config is blocked", "ask Anant to change the config")
    return None


#### whole-segment rules

def check_segment(argv, piped, next_argv, cwd):
    """return a list of (rule, alternative) problems for one simple command."""
    argv = strip_wrappers(argv)
    if not argv:
        return []
    prog, args = os.path.basename(argv[0]), argv[1:]
    problems = []
    if prog in ("bash", "sh", "zsh") and "-c" in args[:-1]:
        problems.extend(check_command(args[args.index("-c") + 1], cwd))   # the -c string is a command line
    if prog == "git":
        configs, sub, rest = git_parts(args)
        checks = {"add": lambda: check_git_add(rest),
                  "commit": lambda: check_git_commit(rest),
                  "push": lambda: check_git_push(rest, cwd),
                  "config": lambda: check_git_config([], rest)}
        for rule in (check_git_config(configs, ["get"]), checks.get(sub, lambda: None)()):
            if rule:
                problems.append(rule)
    if prog == "rm":
        flags = short_flags(args)
        recursive = {"-r", "-R", "--recursive"} & set(args) or flags & {"r", "R"}
        force = "--force" in args or "f" in flags
        if recursive and force:
            problems.append(("rm with recursive and force is blocked", "name the exact files"))
    if (prog in ("pip", "pip3") and "install" in args) or (prog == "uv" and args[:2] == ["pip", "install"]) \
            or (prog.startswith("python") and "-m" in args and "pip" in args):
        problems.append(("pip is blocked", "use uv (uv add, uv sync)"))
    if prog == "gh" and args[:2] == ["pr", "merge"]:
        problems.append(("gh pr merge is blocked", "Anant merges the PR"))
    if prog == "gh" and args[:1] == ["api"]:
        method = next((args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-X", "--method")), "")
        method = method or next((a.split("=", 1)[1] for a in args if a.startswith("--method=")), "GET")
        if method.upper() != "GET" and any(GH_WRITE_PATH_RE.search(a) for a in args):
            problems.append(("gh api writes to a merge or ref path", "Anant merges and moves branches"))
    if piped and "pytest" in " ".join(argv) and next_argv and os.path.basename(next_argv[0]) in PAGERS:
        problems.append(("piping pytest output hides failures", "run pytest without a pipe"))
    if prog not in ("echo", "printf"):
        words = [a for i, a in enumerate(args) if not (i and args[i - 1] in MESSAGE_FLAGS)]
        if prog in (".", "source") or prog not in ("git", "gh"):
            words = [prog] + words
        if any(ENV_RE.search(w) for w in words):
            problems.append(("reading or naming a secret env file is blocked",
                             "check that it exists, or run the action that uses it"))
        if prog != "graphify" and any("graphify-out" in w for w in words):
            problems.append(("graphify-out/ is off limits", 'run graphify query "<question>"'))
    return problems


def check_command(command, cwd=""):
    """return the list of problems for a full Bash command line."""
    segs = segments(command)
    problems = []
    for i, (argv, piped) in enumerate(segs):
        next_argv = segs[i + 1][0] if i + 1 < len(segs) else []
        problems.extend(check_segment(argv, piped, next_argv, cwd))
    return problems


def main():
    """read the payload, print problems to stderr and return the exit code."""
    try:
        data = json.load(sys.stdin)
    # Source: https://docs.python.org/3/library/json.html (JSONDecodeError subclasses ValueError)
    except ValueError:
        print("bash_guard: unreadable payload, not checked", file=sys.stderr)
        return 0
    if not isinstance(data, dict):
        print("bash_guard: payload is not an object, not checked", file=sys.stderr)
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    problems = check_command(command, data.get("cwd", ""))
    for rule, alt in problems:
        print(f"BLOCKED by bash_guard: {rule}. Instead: {alt}.", file=sys.stderr)
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
