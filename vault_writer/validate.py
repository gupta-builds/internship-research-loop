"""Layer 4 — the five-check write gate. Fail any check -> item is rejected and
never touches the vault (fail-closed). Each check is independently callable so
run.yml can log which specific check rejected an item and why.
"""
from dataclasses import dataclass

import requests
import yaml

from core.identity import cross_source_key

REQUIRED_LISTING_FIELDS = ("company", "title", "url", "source", "uid")
REQUIRED_FRONTMATTER_FIELDS = (
    "uid", "company", "title", "url", "source", "category", "terms", "locations",
    "target_year", "date_posted", "date_found", "matched_reason", "status", "promoted", "tags",
)


@dataclass
class ValidationResult:
    passed: bool
    check: str = ""
    reason: str = ""


class _DupeKeyLoader(yaml.SafeLoader):
    """Like SafeLoader, but raises on duplicate mapping keys instead of
    silently keeping the last one — plain safe_load can't detect this."""


def _construct_mapping_no_dupes(loader, node, deep=False):
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise ValueError(f"duplicate frontmatter key: {key!r}")
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


_DupeKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping_no_dupes
)


def check_required_fields(listing, uid: str) -> ValidationResult:
    values = {"uid": uid, **{f: getattr(listing, f) for f in REQUIRED_LISTING_FIELDS if f != "uid"}}
    missing = [name for name in REQUIRED_LISTING_FIELDS if not values[name]]
    if missing:
        return ValidationResult(False, "required_fields", f"missing/empty: {', '.join(missing)}")
    return ValidationResult(True, "required_fields")


def check_url_live(url: str, http_head=None, timeout: int = 10) -> ValidationResult:
    try:
        resp = (http_head or requests.head)(url, timeout=timeout, allow_redirects=True)
    except requests.RequestException as exc:
        return ValidationResult(False, "url_liveness", f"request failed: {exc}")
    if 200 <= resp.status_code < 400:
        return ValidationResult(True, "url_liveness")
    return ValidationResult(False, "url_liveness", f"HTTP {resp.status_code}")


def check_not_duplicate(uid: str, seen_ids) -> ValidationResult:
    if uid in seen_ids:
        return ValidationResult(False, "not_duplicate", f"uid already seen: {uid}")
    return ValidationResult(True, "not_duplicate")


def check_cross_source_duplicate(listing, dossier_keys) -> ValidationResult:
    """Same program via two sources = two different uids but one normalized
    company+title key (MLH Fellowship landed twice pre-cleanup). Routine
    rejection, not systemic — first source in write order wins."""
    key = cross_source_key(listing.company, listing.title)
    if key in dossier_keys:
        return ValidationResult(False, "cross_source_duplicate", f"company+title already in vault: {key}")
    return ValidationResult(True, "cross_source_duplicate")


def check_format_compliance(markdown: str) -> ValidationResult:
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return ValidationResult(False, "format_compliance", "does not start with frontmatter '---'")

    try:
        closing_idx = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return ValidationResult(False, "format_compliance", "no closing frontmatter '---' found")

    frontmatter_text = "\n".join(lines[1:closing_idx])
    try:
        frontmatter = yaml.load(frontmatter_text, Loader=_DupeKeyLoader) or {}
    except ValueError as exc:
        return ValidationResult(False, "format_compliance", str(exc))
    except yaml.YAMLError as exc:
        return ValidationResult(False, "format_compliance", f"frontmatter is not valid YAML: {exc}")

    missing = [f for f in REQUIRED_FRONTMATTER_FIELDS if f not in frontmatter]
    if missing:
        return ValidationResult(False, "format_compliance", f"frontmatter missing fields: {', '.join(missing)}")

    body_lines = lines[closing_idx + 1:]
    if not body_lines or body_lines[0].strip() == "":
        return ValidationResult(False, "format_compliance", "blank line between frontmatter close and title")
    if not body_lines[0].lstrip().startswith("#"):
        return ValidationResult(False, "format_compliance", "no '#' title immediately after frontmatter")

    for i, line in enumerate(body_lines):
        if line.strip() == "---":
            return ValidationResult(False, "format_compliance", "'---' used as a body separator")
        if line.strip() == "":
            prev = body_lines[i - 1].strip() if i > 0 else ""
            if not (prev.startswith(">")):
                return ValidationResult(False, "format_compliance", f"disallowed blank line at body line {i}")

    if body_lines and body_lines[-1].strip() == "":
        return ValidationResult(False, "format_compliance", "trailing blank line at end of file")

    return ValidationResult(True, "format_compliance")


def validate(listing, uid: str, markdown: str, seen_ids, http_head=None, dossier_keys=frozenset()) -> ValidationResult:
    """Runs all checks in the plan's order, fail-closed on the first failure.
    Short-circuits for real (no HEAD request if required fields are already
    missing) — each check only runs once the previous one has passed.
    cross_source_duplicate runs before url_liveness: it's free, the HEAD
    request isn't."""
    result = check_required_fields(listing, uid)
    if not result.passed:
        return result
    result = check_not_duplicate(uid, seen_ids)
    if not result.passed:
        return result
    result = check_cross_source_duplicate(listing, dossier_keys)
    if not result.passed:
        return result
    result = check_url_live(listing.url, http_head=http_head)
    if not result.passed:
        return result
    result = check_format_compliance(markdown)
    if not result.passed:
        return result
    return ValidationResult(True)
