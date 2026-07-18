#!/usr/bin/env python3
"""Layer 5 — on-demand company/contact enrichment for one promoted dossier.

Run manually at Step 2 (Commit) of the vault's Internship Pipeline workflow —
deliberately NOT called from run_pipeline.py and never automatic on dossiers
the discovery loop writes:

    FIRECRAWL_API_KEY=... python enrich.py "<path to dossier .md>"

Public sources only: company site/blog scraped via Firecrawl, GitHub org
public members, blog author bylines, pattern-inferred first.last@domain
checked against the domain's MX records (DNS-over-HTTPS — no new dependency).
Hard line per the plan: no LinkedIn, no CAPTCHA bypass, no cookie injection,
no stealth browsing, no login walls. Anything behind one gets skipped.

No LLM call anywhere — scraped text is trimmed verbatim, never summarized.
"""
import os
import re
import sys
from datetime import date
from urllib.parse import urlparse

import requests
import yaml

FIRECRAWL = "https://api.firecrawl.dev/v1"
TIMEOUT = 30


def read_dossier(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        raise ValueError("no YAML frontmatter found — is this a dossier file?")
    return yaml.safe_load(m.group(1))


def replace_enrichment(text: str, section: str) -> str:
    """Idempotent: a re-run replaces the previous Enrichment section."""
    base = re.split(r"\n## Enrichment\b", text)[0].rstrip("\n")
    return base + "\n\n" + section


def _fc(path: str, payload: dict, key: str) -> dict:
    r = requests.post(f"{FIRECRAWL}/{path}", json=payload, timeout=TIMEOUT,
                      headers={"Authorization": f"Bearer {key}"})
    r.raise_for_status()
    return r.json()


def fc_search(query: str, key: str) -> list:
    return _fc("search", {"query": query, "limit": 5}, key).get("data", [])


def fc_scrape(url: str, key: str) -> str:
    data = _fc("scrape", {"url": url, "formats": ["markdown"]}, key).get("data", {})
    return data.get("markdown", "")


def trim(md: str, limit: int = 800) -> str:
    # ponytail: naive trim keeps nav/link junk at the top of some pages —
    # good enough to orient a human; add a boilerplate stripper if it annoys.
    return re.sub(r"\s+", " ", md).strip()[:limit]


BYLINE_RE = re.compile(r"\b[Bb]y[: ]+\[?([A-Z][a-z]+ [A-Z][a-z]+(?:-[A-Z][a-z]+)?)\]?")


def extract_bylines(md: str) -> list:
    return sorted(set(BYLINE_RE.findall(md)))


def github_org_members(company: str) -> tuple:
    """Best-match public GitHub org and up to 5 public members. Unauthenticated
    (60 req/hr is plenty for an on-demand tool); uses GITHUB_TOKEN if set."""
    h = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    r = requests.get("https://api.github.com/search/users",
                     params={"q": f"{company} type:org", "per_page": 1},
                     headers=h, timeout=TIMEOUT)
    if r.status_code != 200 or not r.json().get("items"):
        return None, []
    org = r.json()["items"][0]["login"]
    r = requests.get(f"https://api.github.com/orgs/{org}/public_members",
                     params={"per_page": 5}, headers=h, timeout=TIMEOUT)
    members = []
    for m in (r.json() if r.status_code == 200 else []):
        detail = requests.get(m["url"], headers=h, timeout=TIMEOUT).json()
        members.append((detail.get("name") or m["login"], m["html_url"]))
    return org, members


def mx_ok(domain: str) -> bool:
    """MX lookup via DNS-over-HTTPS — validates the domain accepts mail,
    not that the specific inferred address exists."""
    try:
        r = requests.get("https://dns.google/resolve",
                         params={"name": domain, "type": "MX"}, timeout=TIMEOUT)
        return bool(r.json().get("Answer"))
    except requests.RequestException:
        return False


def infer_email(name: str, domain: str):
    parts = re.sub(r"[^a-z \-]", "", name.lower()).replace("-", "").split()
    if len(parts) < 2 or not domain:
        return None
    return f"{parts[0]}.{parts[-1]}@{domain}"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        sys.exit("FIRECRAWL_API_KEY is not set — get one at firecrawl.dev and "
                 "export it before running.")
    path = sys.argv[1]
    text = open(path, encoding="utf-8").read()
    company = read_dossier(text)["company"]
    print(f"Enriching {company} …")

    sources, contacts = [], []
    site_url = about = blog_url = ""
    hits = fc_search(f"{company} official site", key)
    if hits:
        site_url = hits[0]["url"]
        sources.append(site_url)
        about = trim(fc_scrape(site_url, key))
    domain = urlparse(site_url).netloc.removeprefix("www.") if site_url else ""

    for hit in fc_search(f"{company} engineering blog", key):
        if re.search(r"blog|engineering|tech", hit["url"], re.I):
            blog_url = hit["url"]
            sources.append(blog_url)
            for name in extract_bylines(fc_scrape(blog_url, key)):
                contacts.append((name, f"blog byline ({blog_url})"))
            break

    org, members = github_org_members(company)
    if org:
        sources.append(f"https://github.com/orgs/{org}/people")
        contacts += [(n, u) for n, u in members]

    mx = mx_ok(domain) if domain else False
    rows = []
    for name, src in contacts:
        email = infer_email(name, domain)
        rows.append(f"| {name} | {src} | {email or '—'} | "
                    f"{'✓' if email and mx else '—'} |")

    today = date.today().isoformat()
    section = "\n".join(
        [f"## Enrichment ({today})",
         f"- **Site:** {site_url or 'not found'}",
         f"- **About (scraped, verbatim):** {about or '—'}",
         f"- **Engineering blog:** {blog_url or 'not found'}",
         f"- **GitHub org:** {f'https://github.com/{org}' if org else 'not found'}",
         f"- **Email domain MX:** {'valid' if mx else 'no MX record found — inferred emails unvalidated'}",
         "", "### Contacts (public sources only — verify before sending anything)",
         "| Name | Source | Inferred email | MX |", "| --- | --- | --- | --- |"]
        + (rows or ["| — | none found | — | — |"])
        + ["", "### Sources"] + [f"- {s}" for s in sources]) + "\n"

    open(path, "w", encoding="utf-8").write(replace_enrichment(text, section))
    print(f"Wrote Enrichment section: {len(contacts)} contact(s), "
          f"{len(sources)} source(s) → {path}")


if __name__ == "__main__":
    main()
