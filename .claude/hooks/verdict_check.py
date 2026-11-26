"""
internship-research-loop: reviewer verdict check (built in C1, wired into the reviewer agents in C4)
Topic: reject a review report whose first line is not a verdict.

Input: the hook payload's tool_input.message on stdin, or `--file <path>` for a
saved report. A missing file or an empty message prints `VALIDATOR NOT RUN:
<reason>` and exits 2. An unreadable payload exits 0 with a warning (hook
convention). Otherwise the first non-empty line must be `VERDICT: PASS`,
`VERDICT: REVISE` or `VERDICT: BLOCK`, or the check exits 2.
"""
import argparse
import json
import re
import sys

VERDICT_RE = re.compile(r"^VERDICT: (PASS|REVISE|BLOCK)\b")


def read_message(argv):
    """return (message, None), or (None, exit code) when the check cannot go on."""
    ap = argparse.ArgumentParser(description="check that a review report starts with a verdict")
    ap.add_argument("--file", help="a saved report to check instead of the hook payload")
    args = ap.parse_args(argv)
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as f:
                return f.read(), None
        except OSError as e:
            print(f"VALIDATOR NOT RUN: cannot read {args.file} ({e.strerror})", file=sys.stderr)
            return None, 2
    try:
        data = json.load(sys.stdin)
    # Source: https://docs.python.org/3/library/json.html (JSONDecodeError subclasses ValueError)
    except ValueError:
        print("verdict_check: unreadable payload, not checked", file=sys.stderr)
        return None, 0
    tool_input = data.get("tool_input") if isinstance(data, dict) else None
    return str((tool_input or {}).get("message") or ""), None


def main(argv=None):
    """check the report and return the exit code."""
    msg, code = read_message(argv)
    if msg is None:
        return code
    lines = [line for line in msg.splitlines() if line.strip()]
    if not lines:
        print("VALIDATOR NOT RUN: the report is empty", file=sys.stderr)
        return 2
    if not VERDICT_RE.match(lines[0].strip()):
        print("Report rejected. The first line must be 'VERDICT: PASS', 'VERDICT: REVISE' or "
              "'VERDICT: BLOCK', then the findings. Return it again in that shape.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
