"""
filter/__init__.py
Filters raw job listings based on config rules.
"""

import re
from loguru import logger


def filter_jobs(raw_jobs: list[dict], config: dict) -> list[dict]:
    """Apply keyword, location, and level filters to raw jobs."""
    cfg = config["job_search"]
    must_have = [k.lower() for k in cfg.get("keywords_must_have", [])]
    exclude = [k.lower() for k in cfg.get("keywords_exclude", [])]
    locations = [l.lower() for l in cfg.get("locations", [])]
    roles = [r.lower() for r in cfg.get("roles", [])]

    filtered = []
    skipped = 0

    for job in raw_jobs:
        title = (job.get("title") or "").lower()
        desc = (job.get("description") or "").lower()
        location = (job.get("location") or "").lower()
        combined = title + " " + desc

        # 1. Exclude keywords check
        if any(kw in combined for kw in exclude):
            skipped += 1
            continue

        # 2. Role relevance check (title must partially match at least one role)
        role_match = any(
            _fuzzy_match(r, title) for r in roles
        )
        if not role_match:
            skipped += 1
            continue

        # 3. Must-have keywords (if configured)
        if must_have and not any(kw in combined for kw in must_have):
            skipped += 1
            continue

        # 4. Location check (if locations configured)
        if locations:
            loc_match = (
                "remote" in locations
                or "hybrid" in location
                or any(l in location for l in locations if l not in ("remote", "hybrid"))
            )
            if not loc_match:
                skipped += 1
                continue

        filtered.append(job)

    logger.info(
        "Filter: {} kept, {} skipped (from {} raw)",
        len(filtered), skipped, len(raw_jobs)
    )
    return filtered


def _fuzzy_match(role: str, title: str) -> bool:
    """Check if any significant word in role appears in title."""
    role_words = [w for w in role.split() if len(w) > 3]
    return any(w in title for w in role_words) if role_words else role in title
