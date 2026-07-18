"""Layer 3 — stable dedup keys for a Listing.

Both remaining sources carry a stable upstream id, so the uid is simply
source:raw_id. (The content-hash fallback existed only for zapplyjobs,
removed as a source 2026-07-18.)

cross_source_key() is the secondary dedup identity: the same program listed
by two different sources gets two different uids but one company+title key.
"""
import re


def compute_uid(listing) -> str:
    if not listing.raw_id:
        raise ValueError(f"listing from {listing.source} has no upstream id: {listing.company!r}")
    return f"{listing.source}:{listing.raw_id}"


def cross_source_key(company: str, title: str) -> str:
    norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
    return f"{norm(company)}|{norm(title)}"
