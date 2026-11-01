"""
filter/__init__.py
Filters raw job listings based on config rules and strict QA relevance.
"""

import re
from loguru import logger

QA_CORE_TERMS = {
    "test", "qa", "sdet", "quality", "automation", "testing",
    "tester", "selenium", "playwright", "cypress", "validation", "verification"
}

GENERIC_DISQUALIFIERS = {
    "civil", "mechanical", "electrical", "chemical", "construction",
    "sales", "marketing", "business development", "accountant", "nursing",
    "physician", "graphic designer", "recruiter", "hr manager"
}


def filter_jobs(raw_jobs: list[dict], config: dict) -> list[dict]:
    """Apply keyword, location, and level filters to raw jobs."""
    cfg = config.get("job_search", {})
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

        # 1. Reject obvious non-QA generic professions
        if any(bad in title for bad in GENERIC_DISQUALIFIERS):
            skipped += 1
            continue

        # 2. Exclude keywords check
        if any(kw in combined for kw in exclude):
            skipped += 1
            continue

        # 3. Role relevance check: title MUST relate to QA / SDET / Software Testing
        has_qa_core = any(term in title for term in QA_CORE_TERMS)
        role_match = has_qa_core or any(_fuzzy_role_match(r, title) for r in roles)
        if not role_match:
            skipped += 1
            continue

        # 4. Must-have keywords (if configured)
        if must_have and not any(kw in combined for kw in must_have):
            skipped += 1
            continue

        # 5. Location check (if locations configured)
        if locations:
            loc_match = (
                "remote" in locations
                or "hybrid" in location
                or "india" in location
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


def _fuzzy_role_match(role: str, title: str) -> bool:
    """Check if title matches specific role keywords without false positives on 'engineer'."""
    role = role.lower()
    title = title.lower()

    if role in title or title in role:
        return True

    # Check significant words excluding generic words like 'engineer', 'lead', 'specialist'
    generic = {"engineer", "lead", "specialist", "associate", "developer", "senior", "junior"}
    role_words = [w for w in role.split() if len(w) > 3 and w not in generic]

    if role_words:
        return any(w in title for w in role_words)
    return False
