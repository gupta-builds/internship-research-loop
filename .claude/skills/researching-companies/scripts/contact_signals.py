#!/usr/bin/env python3
"""
internship-research-loop: contact signals
Topic: public GitHub organization members and a mail-domain check for one company.
Ported from the retired contact-research agent; it reuses enrich.py and adds no search surface.

Usage: uv run python .claude/skills/researching-companies/scripts/contact_signals.py "<company>" [--domain example.com]
Prints one finding per line, then a count line. Exit 0 the lookup ran, 2 it could not run.
Reads no secret and prints no value: GITHUB_TOKEN is reported only as set or unset.
A GitHub org is the best search match, not a verified employer: fetch its page before you cite it.
"""
import argparse
import os
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]   # .claude/skills/<skill>/scripts/ -> repo root


#### lookup

def lookup(company, domain, enrich, env):
    """return a list of finding lines for one company, using the enrich module passed in."""
    out = []
    token = "set" if env.get("GITHUB_TOKEN") else "unset (unauthenticated, 60 requests an hour)"
    out.append(f"[github-token] {token}")
    org, members = enrich.github_org_members(company)
    if org is None:
        out.append("[github-org] nothing found")
    else:
        out.append(f"[github-org] https://github.com/{org} | best search match, verify before citing")
        for name, url in members:                          # up to 5 public members, as enrich returns them
            out.append(f"[github-member] {name} | {url}")
        if not members:
            out.append("[github-member] nothing found")
    if domain:
        verdict = "accepts mail" if enrich.mx_ok(domain) else "no MX record found"
        out.append(f"[mx] {domain} | {verdict}")
    return out


#### driver

def main(argv=None, enrich=None, env=None):
    """print findings and return the exit code."""
    ap = argparse.ArgumentParser(description="public GitHub org members and an MX check for one company")
    ap.add_argument("company")
    ap.add_argument("--domain", default=None, help="a company domain to MX-check, such as example.com")
    args = ap.parse_args(argv)
    env = os.environ if env is None else env
    if enrich is None:
        sys.path.insert(0, str(REPO_ROOT))
        try:
            import enrich                                   # needs requests and pyyaml: run with uv run python
        except ImportError as e:
            print(f"contact_signals could not run: {e}", file=sys.stderr)
            return 2
    try:
        lines = lookup(args.company, args.domain, enrich, env)
    except Exception as e:                                  # network, API or JSON failure: say so, never return a guess
        print(f"contact_signals could not run: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    for line in lines:
        print(line)
    print(f"{len(lines)} line(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
