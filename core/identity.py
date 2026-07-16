"""Layer 3 — compute a stable dedup key for a Listing.

JSON sources (SimplifyJobs, Jose-Gael-Cruz-Lopez) carry a stable upstream id;
use it directly as the primary key. zapplyjobs has no id, so its key falls
back to a content hash of normalized company+role+link.
"""
import hashlib


def compute_uid(listing) -> str:
    if listing.raw_id:
        return f"{listing.source}:{listing.raw_id}"
    key = f"{listing.company.strip().lower()}|{listing.title.strip().lower()}|{listing.url.strip().lower()}"
    return f"{listing.source}:" + hashlib.sha256(key.encode()).hexdigest()[:16]
