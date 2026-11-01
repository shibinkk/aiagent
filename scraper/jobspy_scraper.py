"""
scraper/jobspy_scraper.py
Uses python-jobspy to scrape Indeed and Glassdoor.
"""

import time
from loguru import logger

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
    logger.warning("jobspy not installed. Run: pip install python-jobspy")


def _safe_format_salary(min_amt, max_amt, cur="₹", interval="year") -> str:
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
    suf = f"/{interval}" if interval else ""

    if clean_min and clean_max:
        return f"{cur} {clean_min:,} - {clean_max:,}{suf}"
    elif clean_min:
        return f"{cur} {clean_min:,}+{suf}"
    elif clean_max:
        return f"Up to {cur} {clean_max:,}{suf}"
    return "Competitive salary"


def scrape_with_jobspy(config: dict) -> list[dict]:

    """Scrape jobs from Indeed and Glassdoor using jobspy."""
    if not JOBSPY_AVAILABLE:
        return []

    roles = config.get("job_search", {}).get("roles", ["SDET", "QA Automation Engineer"])
    locations_raw = config.get("job_search", {}).get("locations", ["Kochi", "Bangalore", "Chennai", "India"])
    results_wanted = config.get("job_search", {}).get("results_per_platform", 15)

    platforms_cfg = config.get("platforms", {})
    site_names = []
    if platforms_cfg.get("indeed", True):
        site_names.append("indeed")
    if platforms_cfg.get("glassdoor", True):
        site_names.append("glassdoor")

    if not site_names:
        return []

    all_jobs = []
    seen = set()
    locations = [l for l in locations_raw if l.lower() not in ("remote", "hybrid")]
    if not locations:
        locations = ["India"]

    # Target top 2 roles and top 2 locations
    for role in roles[:2]:
        for location in locations[:2]:
            logger.info("JobSpy (Indeed/Glassdoor) → Searching '{}' in '{}'", role, location)
            try:
                df = scrape_jobs(
                    site_name=site_names,
                    search_term=role,
                    location=location,
                    results_wanted=min(results_wanted, 15),
                    country_indeed="India",
                )
                if df is None or df.empty:
                    continue

                for _, row in df.iterrows():
                    title = str(row.get("title", "")).strip()
                    company = str(row.get("company", "")).strip()
                    job_loc = str(row.get("location", "")).strip() or location
                    url = str(row.get("job_url", "")).strip()

                    key = f"{title.lower()}::{company.lower()}"
                    if key in seen or not title or not company:
                        continue
                    seen.add(key)

                    # Extract & format salary safely
                    salary_str = _safe_format_salary(
                        row.get("min_amount"),
                        row.get("max_amount"),
                        row.get("currency") or "₹",
                        row.get("interval") or "year"
                    )

                    job = {
                        "title": title,
                        "company": company,
                        "location": job_loc,
                        "platform": str(row.get("site", "indeed")).lower(),
                        "job_url": url,
                        "description": str(row.get("description", ""))[:3000],
                        "salary": salary_str,
                        "date_posted": str(row.get("date_posted", "")),
                    }
                    all_jobs.append(job)

                time.sleep(1.5)
            except Exception as e:
                logger.error("JobSpy error for '{}' in '{}': {}", role, location, e)
                continue

    logger.info("JobSpy found {} jobs total", len(all_jobs))
    return all_jobs
