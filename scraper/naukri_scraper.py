"""
scraper/naukri_scraper.py
Scrapes Naukri.com for QA / SDET job listings using python-jobspy.
"""

import time
from loguru import logger

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False


def _safe_format_salary(min_amt, max_amt, cur="₹") -> str:
    def _to_clean_int(val):
        if val is None:
            return None
        try:
            import math
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return None
            return int(f)
        except (ValueError, TypeError):
            return None

    clean_min = _to_clean_int(min_amt)
    clean_max = _to_clean_int(max_amt)
    cur = cur or "₹"

    if clean_min and clean_max:
        return f"{cur} {clean_min:,} - {clean_max:,}"
    elif clean_min:
        return f"{cur} {clean_min:,}+"
    elif clean_max:
        return f"Up to {cur} {clean_max:,}"
    return "Not Disclosed"


def scrape_naukri(config: dict) -> list[dict]:

    """Scrape job listings from Naukri.com using JobSpy."""
    if not config.get("platforms", {}).get("naukri", True):
        return []

    if not JOBSPY_AVAILABLE:
        logger.warning("JobSpy not available for Naukri scraper.")
        return []

    roles = config.get("job_search", {}).get("roles", ["SDET", "QA Automation Engineer"])
    locations_raw = config.get("job_search", {}).get("locations", ["Kochi", "Bangalore", "Chennai", "India"])
    results_wanted = config.get("job_search", {}).get("results_per_platform", 15)

    clean_locations = [l for l in locations_raw if l.lower() not in ("remote", "hybrid")]
    if not clean_locations:
        clean_locations = ["India"]

    all_jobs = []
    seen = set()

    # Search top 2 roles across top 2 locations
    for role in roles[:2]:
        for loc in clean_locations[:2]:
            logger.info("Naukri (JobSpy) → Searching '{}' in '{}'", role, loc)
            try:
                df = scrape_jobs(
                    site_name=["naukri"],
                    search_term=role,
                    location=loc,
                    results_wanted=min(results_wanted, 15),
                )
                if df is None or df.empty:
                    continue

                for _, row in df.iterrows():
                    title = str(row.get("title", "")).strip()
                    company = str(row.get("company", "")).strip()
                    job_loc = str(row.get("location", "")).strip() or loc
                    url = str(row.get("job_url", "")).strip()

                    key = f"{title.lower()}::{company.lower()}"
                    if key in seen or not title or not company:
                        continue
                    seen.add(key)

                    # Extract salary safely
                    salary_str = _safe_format_salary(
                        row.get("min_amount"),
                        row.get("max_amount"),
                        row.get("currency") or "₹"
                    )

                    all_jobs.append({
                        "title": title,
                        "company": company,
                        "location": job_loc,
                        "platform": "naukri",
                        "job_url": url,
                        "description": str(row.get("description", ""))[:3000],
                        "salary": salary_str,
                        "date_posted": str(row.get("date_posted", "")),
                    })

                time.sleep(1.5)
            except Exception as e:
                logger.error("Naukri scrape error for '{}' in '{}': {}", role, loc, e)
                continue

    logger.info("Naukri found {} jobs total", len(all_jobs))
    return all_jobs
