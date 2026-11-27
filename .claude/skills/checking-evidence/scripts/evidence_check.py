"""
internship-research-loop: checking-evidence skill
Topic: trace every number, date, entity, skill and URL in a draft to Anant's approved sources.

Usage: python3 evidence_check.py DRAFT --kind resume|cover|outreach|followup --facts FILE [FILE ...]
       [--jd POSTING] [--allow FILE]
Prints one finding per line as `path:line [kind] token | context`, then a count line.
Kinds: number, date, entity, skill, url, coverage.
Exit 0 every token traced, 1 findings, 2 the check could not run (`VALIDATOR NOT RUN: <reason>`).
Spec: Claude System Implementation Plan, Script specs, the evidence_check.py algorithm,
adapted from ats-resume-agent's validate.ts.
"""
import argparse
import pathlib
import re
import sys

KINDS = ("resume", "cover", "outreach", "followup")

LIMITS_TEXT = """what a pass means, and what this check cannot catch:
  It matches values, not sentences. A pass means nothing was invented; it does not
  mean every sentence is accurate. It does not catch a true number placed on the
  wrong role in prose, a stronger verb than the source supports ("contributed" to
  "led"), or a sentence that is false though every token matches. "45m" reads as
  45 million. A sentence-initial capitalized word is not checked as an entity, and
  an ambiguous English word (go, react, rust, swift) is checked as a skill only in a
  Skills section or when capitalized. Those are for a reviewer to read.
  --jd is a source only for company and role names, and for a number in a letter
  or message when the sentence shares a word of four or more letters with the
  posting sentence that holds it. It is never a source for a resume.
  --allow FILE: one entry per line. "a = b" adds an alias for this run; a line
  that looks like a domain allows URLs on that host; any other line is a token
  accepted as traced. Every acceptance is counted in the last line."""

#### vocabulary

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8,
          "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
MONTH_RE = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
            r"sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
SEASONS = ("spring", "summer", "fall", "autumn", "winter")
PRESENT = ("present", "current", "now", "ongoing")
SPELLED = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
           "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
           "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
           "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
           "eighty": 80, "ninety": 90, "hundred": 100, "dozen": 12}
# unit word or suffix: (class, factor); magnitudes fold into one value per class
UNITS = {"%": ("percent", 1), "percent": ("percent", 1), "pct": ("percent", 1),
         "k": ("count", 1e3), "thousand": ("count", 1e3), "m": ("count", 1e6), "million": ("count", 1e6),
         "mm": ("count", 1e6), "b": ("count", 1e9), "bn": ("count", 1e9), "billion": ("count", 1e9),
         "x": ("times", 1), "times": ("times", 1),
         "ms": ("time", 1), "millisecond": ("time", 1), "milliseconds": ("time", 1),
         "s": ("time", 1e3), "sec": ("time", 1e3), "secs": ("time", 1e3), "second": ("time", 1e3),
         "seconds": ("time", 1e3), "min": ("time", 6e4), "mins": ("time", 6e4), "minute": ("time", 6e4),
         "minutes": ("time", 6e4), "kb": ("size", 1e3), "mb": ("size", 1e6), "gb": ("size", 1e9),
         "tb": ("size", 1e12)}
CURRENCY = {"$": "usd", "€": "eur", "£": "gbp"}
STOP = {"a", "an", "the", "of", "to", "in", "for", "by", "on", "with", "and", "or", "at", "from",
        "across", "over", "under", "per", "than", "more", "less", "into", "as", "about", "after",
        "before", "within", "while", "that", "this", "these", "those", "is", "was", "were", "are",
        "be", "been", "it", "its", "my", "our", "their", "your", "i", "we", "you", "they", "so",
        "then", "up", "down", "out", "via", "using", "each", "every", "all", "some", "most", "would",
        "will", "have", "has", "had", "which", "what", "when", "where", "who", "how", "also", "just"}
SECTION_NAMES = {"header", "summary", "objective", "education", "skills", "technical skills", "experience",
                 "work experience", "relevant experience", "projects", "selected projects", "certifications",
                 "leadership", "activities", "awards", "publications", "coursework", "contact", "languages"}
DROP_SECTION = re.compile(r"legacy|deprecated|outdated|retired|positioning|preferences|customi[sz]ation|"
                          r"tailoring notes|logged gaps|\bgaps\b|\barchive", re.IGNORECASE)
ALIASES = [
    {"postgres", "postgresql", "psql"}, {"javascript", "js"}, {"typescript", "ts"}, {"kubernetes", "k8s"},
    {"golang", "go"}, {"node.js", "nodejs", "node"}, {"react", "react.js", "reactjs"},
    {"next.js", "nextjs", "next"}, {"vue", "vue.js", "vuejs"}, {"c++", "cpp"}, {"c#", "csharp"},
    {"aws", "amazon web services"}, {"gcp", "google cloud", "google cloud platform"},
    {"ml", "machine learning"}, {"llm", "llms", "large language model", "large language models"},
    {"tailwind", "tailwind css", "tailwindcss"}, {"mongodb", "mongo"}, {"scikit-learn", "sklearn"},
    {"rest", "rest api", "rest apis", "restful"}, {"ci/cd", "continuous integration"},
    {"github actions", "gh actions"}, {"sql server", "mssql"}, {"tensorflow", "tf"}, {"pytorch", "torch"},
]
# tech terms checked anywhere in a draft; ambiguous English words are checked only in a Skills
# section or when capitalized (see LIMITS_TEXT)
TECH = {"python", "java", "javascript", "typescript", "kotlin", "scala", "haskell", "elixir", "erlang",
        "c++", "c#", "php", "perl", "matlab", "julia", "golang", "postgres", "postgresql", "mysql",
        "sqlite", "mongodb", "redis", "cassandra", "dynamodb", "elasticsearch", "kafka", "rabbitmq",
        "kubernetes", "k8s", "docker", "terraform", "ansible", "jenkins", "aws", "gcp", "azure",
        "lambda", "graphql", "grpc", "fastapi", "django", "flask", "spring boot", "node.js", "nodejs",
        "react.js", "next.js", "vue.js", "angular", "svelte", "tailwind", "pytorch", "tensorflow",
        "keras", "scikit-learn", "pandas", "numpy", "spark", "hadoop", "airflow", "snowflake",
        "databricks", "llm", "llms", "rag", "langchain", "openai", "huggingface", "cuda", "opencv",
        "linux", "bash", "git", "github actions", "ci/cd", "webassembly", "wasm", "solidity", "unity",
        "unreal", "figma", "tableau", "power bi", "excel", "selenium", "playwright", "cypress", "jest",
        "pytest", "junit", "nginx", "prometheus", "grafana", "datadog", "splunk", "supabase", "firebase",
        "vercel", "heroku", "netlify", "stripe", "twilio", "strapi", "websocket", "websockets", "oauth",
        "jwt", "html", "css", "sass", "rust", "ruby on rails", "express.js", ".net", "embeddings",
        "computer vision", "nlp", "reinforcement learning", "transformers", "ros", "verilog", "vhdl",
        "fpga", "arduino", "raspberry pi", "embedded c", "rtos", "mqtt", "kotlin multiplatform"}
TLDS = ("com", "org", "net", "io", "dev", "edu", "ai", "app", "co", "me", "xyz", "gov", "us", "uk", "ca",
        "in", "tech", "site", "page", "info")
COUNTED_NOUN_WINDOW = 4                                # words after a source number that may hold the noun

#### patterns

DASH_CHARS = "‐‑‒–—―−"
SEP = r"\s*(?:-|to|through|until|thru)\s*"
DATE_ATOM = (rf"(?:{MONTH_RE}\.?,?\s+'?\d{{2,4}}|\d{{1,2}}/\d{{4}}|\d{{4}}-\d{{2}}(?!\d)|"
             rf"(?:{'|'.join(SEASONS)})\s+\d{{4}}|(?<![\d.,$])(?:19|20)\d\d(?![\d,]|\.\d))")
DATE_ANY = re.compile(rf"(?P<a>{DATE_ATOM})(?:{SEP}(?P<b>{DATE_ATOM}|{'|'.join(PRESENT)}))?", re.IGNORECASE)
NUMBER = re.compile(r"(?<![\w.])(?P<cur>[$€£])?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
                    r"(?P<glued>[a-z%]+)?", re.IGNORECASE)
SPELLED_RE = re.compile(r"\b(" + "|".join(SPELLED) + r")\b", re.IGNORECASE)
UNIT_WORD = re.compile(r"\s*(%|percent|per cent|pct|thousand|million|billion|times|x|ms|milliseconds?|"
                       r"seconds?|secs?|minutes?|mins?|kb|mb|gb|tb)(?![\w])", re.IGNORECASE)
URL = re.compile(r"(?:https?://)?(?:www\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:" + "|".join(TLDS) +
                 r")(?![a-z0-9-])(?:/[^\s)\]>,;\"']*)?", re.IGNORECASE)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
NAME_WORD = r"[A-Z](?:[\w+#&'-]|\.(?=\w))*"           # a dot only inside a name (Node.js), never at its end
CAPITALIZED = re.compile(rf"(?<![\w.]){NAME_WORD}(?:\s+(?:(?:of|and|&|for|de)\s+)?{NAME_WORD})*")
WORD = re.compile(r"[a-z][a-z'-]+")


#### error type and argument parser

class NotRun(Exception):
    """raised when an input is missing or unreadable, so the check cannot run."""


class Parser(argparse.ArgumentParser):
    """an argument parser whose usage errors print VALIDATOR NOT RUN and exit 2."""

    def error(self, message):
        """print the not-run line and exit 2."""
        print(f"VALIDATOR NOT RUN: {message}", file=sys.stderr)
        sys.exit(2)


#### cleaning (algorithm step 1)

def read_text(path):
    """return the text of a file, or raise NotRun."""
    try:
        return pathlib.Path(path).read_text(encoding="utf-8")
    # Source: https://docs.python.org/3/library/pathlib.html (read_text raises OSError; bad bytes raise UnicodeDecodeError)
    except (OSError, UnicodeDecodeError) as e:
        raise NotRun(f"cannot read {path}: {e}") from e


def keep_lines(match):
    """return as many newlines as the matched span holds."""
    return "\n" * match.group(0).count("\n")


def normalize(text):
    """return text with frontmatter and comments blanked, dashes, quotes and spaces made plain."""
    text = re.sub(r"\A---\n.*?\n---[ \t]*\n", keep_lines, text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", keep_lines, text, flags=re.DOTALL)
    for ch in DASH_CHARS:
        text = text.replace(ch, "-")
    for curly, plain in (("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'")):
        text = text.replace(curly, plain)
    return text.replace(" ", " ").replace("​", "")


def source_sections(text):
    """return the kept (title path, body) sections of a source, dropping guidance and legacy ones."""
    sections, path, drop_below = [], [], None
    current = ["", []]
    for line in normalize(text).splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not m:
            if drop_below is None:
                current[1].append(line)
            continue
        level, title = len(m.group(1)), m.group(2).strip()
        sections.append((current[0], "\n".join(current[1])))
        if drop_below is not None and level <= drop_below:
            drop_below = None                          # a sibling or parent heading ends the dropped span
        path = [p for p in path if p[0] < level] + [(level, title)]
        if drop_below is None and DROP_SECTION.search(title):
            drop_below = level
        current = [" / ".join(t for _, t in path), [line] if drop_below is None else []]
    sections.append((current[0], "\n".join(current[1])))
    return [(title.lower(), (title + "\n" + body).lower()) for title, body in sections
            if body.strip() or title]


#### extraction (algorithm step 2)

def unit_after(text, end):
    """return (unit class, factor, end offset) of a unit word right after offset end, or None."""
    m = UNIT_WORD.match(text, end)
    if not m:
        return None
    word = m.group(1).lower().replace("per cent", "percent")
    cls, factor = UNITS.get(word, UNITS.get(word.rstrip("s"), ("count", 1)))
    return cls, factor, m.end()


def noun_after(text, end):
    """return the word right after offset end, singular, unless it is a stop word."""
    m = re.match(r"\s+([a-z][a-z-]+)", text[end:].lower())
    if not m or m.group(1) in STOP or m.group(1) in UNITS:
        return None
    return singular(m.group(1))


def singular(word):
    """return a crude singular form, the same for draft and source."""
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def numbers(text, spelled_need_noun=True):
    """return (value, class, raw, noun, start) for each number in text."""
    out = []
    for m in NUMBER.finditer(text):
        value = float(m.group("num").replace(",", ""))
        cls, end, glued = "count", m.end(), (m.group("glued") or "").lower()
        if glued:
            if glued not in UNITS:
                continue                               # glued to a word (3d, 4th, 2fa): not a metric
            cls, factor = UNITS[glued]
            value *= factor
        else:
            unit = unit_after(text, m.end())
            if unit:
                cls, factor, end = unit
                value *= factor
        if m.group("cur"):
            cls = "currency:" + CURRENCY[m.group("cur")]
        out.append((value, cls, text[m.start():end].strip(), noun_after(text, end), m.start()))
    for m in SPELLED_RE.finditer(text):
        value, cls, end = SPELLED[m.group(1).lower()], "count", m.end()
        unit = unit_after(text, end)
        if unit:
            cls, factor, end = unit
            value *= factor
        noun = noun_after(text, end)
        if noun or unit or not spelled_need_noun:
            out.append((value, cls, text[m.start():end].strip(), noun, m.start()))
    return out


def date_canon(token):
    """return a canonical tuple for one date token."""
    t = token.lower().strip(" .,")
    if t in PRESENT:
        return ("present",)
    m = re.match(rf"({MONTH_RE})\.?,?\s+'?(\d{{2,4}})$", t)
    if m:
        year = int(m.group(2)) + (2000 if len(m.group(2)) == 2 else 0)
        return ("ym", year, MONTHS[m.group(1)[:4].rstrip("t") if m.group(1).startswith("sept") else m.group(1)[:3]])
    m = re.match(r"(\d{1,2})/(\d{4})$", t) or re.match(r"(\d{4})-(\d{2})$", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return ("ym", b, a) if a <= 12 and b > 12 else ("ym", a, b)
    m = re.match(rf"({'|'.join(SEASONS)})\s+(\d{{4}})$", t)
    if m:
        return ("season", int(m.group(2)), "fall" if m.group(1) == "autumn" else m.group(1))
    return ("y", int(t))


def dates(text):
    """return (start canon, end canon or None, raw, span) for each date or date range in text."""
    out = []
    for m in DATE_ANY.finditer(text):
        end = date_canon(m.group("b")) if m.group("b") else None
        out.append((date_canon(m.group("a")), end, m.group(0), m.span()))
    return out


def mask(text, spans):
    """return text with each span replaced by spaces."""
    for a, b in spans:
        text = text[:a] + " " * (b - a) + text[b:]
    return text


#### matching (algorithm steps 3 to 7)

def term_pattern(term):
    """return a boundary-aware pattern for a term, so go does not match google."""
    body = r"[\s-]+".join(re.escape(w) for w in term.lower().split())
    return re.compile(r"(?<![\w+#])" + body + r"(?![\w+#])")


def term_in(term, text, aliases):
    """return True if the term or one of its aliases appears in text."""
    names = {term.lower()}
    for group in aliases:
        if term.lower() in group:
            names |= group
    return any(term_pattern(n).search(text) for n in names)


def same_value(a, b):
    """return True if two folded values are equal."""
    return abs(a - b) <= 1e-9 * max(abs(a), abs(b), 1)


def number_traced(num, source_nums, source_text):
    """return True if a draft number has a source number of the same value, class and bound noun."""
    value, cls, _, noun, _ = num
    for s_value, s_cls, _, _, s_start in source_nums:
        if s_cls != cls or not same_value(value, s_value):
            continue
        if noun is None:
            return True
        window = [singular(w) for w in WORD.findall(source_text[s_start:s_start + 120])[:COUNTED_NOUN_WINDOW + 1]]
        if noun in window:
            return True
    return False


def date_matches(d, s):
    """return True if draft date canon d is supported by source date canon s."""
    if d[0] == "y":
        return s[0] in ("y", "ym", "season") and s[1] == d[1]
    return d == s


def date_traced(start, end, source_dates):
    """return (ok, reason) for a draft date or range against the source dates."""
    singles = [x for s in source_dates for x in (s[0], s[1]) if x]
    for point in [p for p in (start, end) if p]:
        if not any(date_matches(point, s) for s in singles):
            return False, f"{point_text(point)} is not in the sources"
    if end and not any(s[1] and date_matches(start, s[0]) and date_matches(end, s[1]) for s in source_dates):
        return False, "the sources hold both ends but not as one range"
    return True, ""


def point_text(point):
    """return a readable form of a date canon."""
    if point[0] == "ym":
        return f"{point[1]}-{point[2]:02d}"
    return " ".join(str(p) for p in point[1:]) or point[0]


def shared_words(text):
    """return the words of four or more letters that can tie a letter sentence to a posting sentence."""
    return {w for w in WORD.findall(text.lower())
            if len(w) >= 4 and w not in STOP and w not in UNITS and w not in SPELLED}


def normalize_url(url):
    """return a URL without scheme, www, case or trailing slash."""
    url = re.sub(r"^https?://", "", url.lower())
    return re.sub(r"^www\.", "", url).rstrip("/.")


#### the check

class Check:
    """holds the inputs and counters for one run."""

    def __init__(self, draft, kind, facts, jd, allow):
        """read and clean every input, or raise NotRun."""
        self.path = draft
        self.kind = kind
        raw = read_text(draft)
        self.lines = normalize(raw).splitlines()
        if not any(re.search(r"\w", line) for line in self.lines):
            raise NotRun(f"{draft} has no text")
        self.sections = []
        for path in facts:
            self.sections += source_sections(read_text(path))
        self.source = "\n".join(body for _, body in self.sections)
        if not re.search(r"\w", self.source):
            raise NotRun("the --facts files hold no source text after cleaning")
        if jd and kind == "resume":
            raise NotRun("--jd is never a source for a resume")
        self.jd = normalize(read_text(jd)).lower() if jd else ""
        self.aliases = [set(g) for g in ALIASES]
        self.allow_aliases = []
        self.allow_terms, self.allow_hosts = set(), set()
        for line in (read_text(allow).splitlines() if allow else []):
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                self.allow_aliases.append({p.strip() for p in line.split("=") if p.strip()})
            elif re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+(/\S*)?", line):
                self.allow_hosts.add(normalize_url(line))
            else:
                self.allow_terms.add(line)
        self.source_nums = numbers(self.source, spelled_need_noun=False)
        self.source_dates = dates(self.source)
        self.source_urls = {normalize_url(m.group(0)) for m in URL.finditer(self.source)}
        self.source_urls |= {m.group(0).lower() for m in EMAIL.finditer(self.source)}
        self.counts = dict.fromkeys(("number", "date", "entity", "skill", "url"), 0)
        self.allowed = self.by_jd = 0
        self.date_failed = False
        self.findings = []

    def find(self, n, kind, token, ctx):
        """record one finding."""
        self.findings.append((n, kind, token, re.sub(r"\s+", " ", ctx).strip()[:80]))

    def traced(self, term, text):
        """return True if a term is in text; an alias from --allow counts as an acceptance."""
        if term_in(term, text, self.aliases):
            return True
        if self.allow_aliases and term_in(term, text, self.aliases + self.allow_aliases):
            self.allowed += 1
            return True
        return False

    def allowed_term(self, token):
        """return True, and count it, if --allow accepts the token."""
        if token.lower().strip() in self.allow_terms:
            self.allowed += 1
            return True
        return False

    #### per-line checks

    def check_urls(self, n, line):
        """trace each URL and email on a line; return the line with them masked."""
        spans = []
        for m in list(EMAIL.finditer(line)) + list(URL.finditer(line)):
            if any(a <= m.start() < b for a, b in spans):
                continue                               # the host part of an email already checked
            spans.append(m.span())
            self.counts["url"] += 1
            token = m.group(0)
            norm = token.lower() if "@" in token else normalize_url(token)
            host_ok = any(norm == h or norm.startswith(h.rstrip("/") + "/") for h in self.allow_hosts)
            if host_ok:
                self.allowed += 1
            elif norm not in self.source_urls and not self.allowed_term(token):
                self.find(n, "url", token, "not in the sources or the --allow hosts")
        return mask(line, spans)

    def check_dates(self, n, line):
        """trace each date and range on a line; return the found dates and the line with them masked."""
        found = dates(line)
        self.date_failed = False
        for start, end, raw, _ in found:
            self.counts["date"] += 1
            ok, reason = date_traced(start, end, self.source_dates)
            if not ok and not self.allowed_term(raw):
                self.find(n, "date", raw, reason)
                self.date_failed = True
        stray = re.search(rf"\b{MONTH_RE}\b(?!\s+(?:\d|'))", mask(line, [d[3] for d in found]), re.IGNORECASE)
        if stray and self.is_heading_unit(line):
            self.find(n, "coverage", stray.group(0), "a date on this line could not be parsed")
        return found, mask(line, [d[3] for d in found])

    def check_numbers(self, n, line):
        """trace each number on a line (dates and URLs already masked)."""
        for num in numbers(line.lower()):
            self.counts["number"] += 1
            if number_traced(num, self.source_nums, self.source):
                continue
            if self.allowed_term(num[2]) or self.jd_supports(num, line):
                continue
            noun = f" bound to '{num[3]}'" if num[3] else ""
            self.find(n, "number", num[2], f"no source number with this value{noun} | {line}")

    def jd_supports(self, num, line):
        """return True if a letter's number is held by a posting sentence sharing a long word."""
        if not self.jd or self.kind == "resume":
            return False
        words = shared_words(line)
        for sentence in re.split(r"[.!?\n]+", self.jd):
            if number_traced(num, numbers(sentence, False), sentence):
                if words & shared_words(sentence):
                    self.by_jd += 1
                    return True
        return False

    def entity_known(self, entity):
        """return True if an entity is in the sources, or in the posting for a letter or message."""
        if self.traced(entity, self.source):
            return True
        if self.is_tech(entity):
            return False                               # the posting never supplies a skill or tool
        if self.jd and self.kind != "resume" and term_in(entity, self.jd, []):
            self.by_jd += 1
            return True
        return False

    def is_tech(self, term):
        """return True if a term names a tool or skill: a TECH term or an alias."""
        low = term.lower()
        return low in TECH or any(low in group for group in self.aliases + self.allow_aliases)

    def is_heading_unit(self, line):
        """return True if a line is a role or entry header: a heading, a bold line or one with a date range."""
        text = line.strip()
        if re.match(r"^#{1,6}\s", text):
            return text.lstrip("#").strip().lower() not in SECTION_NAMES
        return bool(re.match(r"^\*\*[^*]+\*\*", text)) or any(d[1] for d in dates(text))

    def check_heading_unit(self, n, line, found_dates):
        """trace each part of a header line, then require all parts in one source section (step 6)."""
        text = mask(line, [d[3] for d in found_dates])
        text = re.sub(r"[#*_`]", " ", text)
        parts = [p.strip(" .()") for p in re.split(r"\s[|@\-,]\s|\s+at\s+|[|,·•]", text)]
        parts = [p for p in parts if re.search(r"[A-Za-z]", p) and p.lower() not in PRESENT]
        missing = False
        for part in parts:
            self.counts["entity"] += 1
            if not self.entity_known(part) and not self.allowed_term(part):
                self.find(n, "entity", part, line)
                missing = True
        if missing or not parts or self.date_failed:
            return                                     # a part already failed on its own
        for _, body in self.sections:
            if all(term_in(p, body, self.aliases + self.allow_aliases) for p in parts) and \
                    all(date_traced(d[0], d[1], dates(body))[0] for d in found_dates):
                return
        self.find(n, "entity", " + ".join(parts), "these parts do not sit together in one source section")

    def check_prose(self, n, line):
        """trace capitalized names that are not at a sentence start, and tech terms anywhere."""
        body = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", line)
        body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)     # a markdown link keeps its text
        checked = set()
        for m in CAPITALIZED.finditer(body):
            before = body[:m.start()].rstrip()
            if not before or before[-1] in ".!?:;\"(" or m.group(0) in ("I", "I'm", "I've", "I'd"):
                continue                               # sentence-initial: not checked (see LIMITS_TEXT)
            entity = m.group(0).strip(" .'")
            first = entity.split()[0].lower()
            if first in MONTHS or first[:3] in MONTHS and len(entity.split()) == 1 or first in PRESENT:
                continue
            checked.add(entity.lower())
            self.counts["entity"] += 1
            if not self.entity_known(entity) and not self.allowed_term(entity):
                self.find(n, "entity", entity, line)
        low = body.lower()
        for term in sorted(TECH):
            if term in checked or not term_pattern(term).search(low):
                continue
            self.counts["skill"] += 1
            if not self.traced(term, self.source) and not self.allowed_term(term):
                self.find(n, "skill", term, line)

    def check_skills(self, n, line):
        """trace each item on a Skills section line; return how many items were read."""
        text = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", line)
        text = re.sub(r"[*_`]", "", text)
        text = text.split(":", 1)[1] if ":" in text else text            # drop a category label
        items = [i.strip(" .") for i in re.split(r"[,;|·•]|\s+and\s+", text) if i.strip(" .")]
        for item in items:
            self.counts["skill"] += 1
            if not self.traced(item, self.source) and not self.allowed_term(item):
                self.find(n, "skill", item, line)
        return len(items)

    #### driver

    def run(self):
        """run every check over the draft lines and return the findings."""
        in_skills, skills_line, skills_items = False, 0, 0
        for n, line in enumerate(self.lines, 1):
            if not line.strip():
                continue
            heading = re.match(r"^#{1,6}\s+(.*)$", line.strip())
            if heading:
                if in_skills and skills_items == 0:
                    self.find(skills_line, "coverage", "Skills", "the Skills section has no items it could read")
                in_skills = "skill" in heading.group(1).lower()
                skills_line, skills_items = n, 0
                if heading.group(1).strip().lower() in SECTION_NAMES:
                    continue
            line_left = self.check_urls(n, line)
            found_dates, line_left = self.check_dates(n, line_left)
            self.check_numbers(n, line_left)
            if in_skills and not heading:
                skills_items += self.check_skills(n, line_left)
            elif self.is_heading_unit(line):
                self.check_heading_unit(n, line_left, found_dates)
            else:
                self.check_prose(n, line_left)
        if in_skills and skills_items == 0:
            self.find(skills_line, "coverage", "Skills", "the Skills section has no items it could read")
        if not any(self.counts.values()):
            self.find(1, "coverage", "(draft)", "no number, date, entity, skill or URL was found to check")
        return sorted(self.findings)


def main(argv=None):
    """print findings and return the exit code."""
    ap = Parser(description="trace the facts in a draft to Anant's approved sources",
                epilog=LIMITS_TEXT, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft", help="the draft file (markdown or plain text)")
    ap.add_argument("--kind", required=True, choices=KINDS, help="the kind of draft; --jd is refused for a resume")
    ap.add_argument("--facts", required=True, nargs="+", metavar="FILE",
                    help="the approved source files: Main Resume.md, Main Cover Letter.md, linked project notes, "
                         "Program and Contact notes")
    ap.add_argument("--jd", metavar="POSTING", help="the posting, for a letter or message only")
    ap.add_argument("--allow", metavar="FILE", help="aliases, allowed hosts and accepted tokens for this run")
    args = ap.parse_args(argv)
    try:
        check = Check(args.draft, args.kind, args.facts, args.jd, args.allow)
        findings = check.run()
    except NotRun as e:
        print(f"VALIDATOR NOT RUN: {e}", file=sys.stderr)
        return 2
    for n, kind, token, ctx in findings:
        print(f"{args.draft}:{n} [{kind}] {token} | {ctx}")
    c = check.counts
    print(f"{len(findings)} finding(s); checked {c['number']} numbers, {c['date']} dates, {c['entity']} entities, "
          f"{c['skill']} skills, {c['url']} urls; {check.allowed} accepted by --allow, {check.by_jd} by --jd")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
