"""
scraper/jobspy_scraper.py
Uses python-jobspy to scrape LinkedIn, Indeed, Glassdoor simultaneously.
"""

import time
from loguru import logger

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False
    logger.warning("jobspy not installed. Run: pip install python-jobspy")


def scrape_with_jobspy(config: dict) -> list[dict]:
    """Scrape jobs from LinkedIn, Indeed, Glassdoor using jobspy."""
    if not JOBSPY_AVAILABLE:
        return []

    roles = config["job_search"]["roles"]
    locations_raw = config["job_search"]["locations"]
    results_wanted = config["job_search"].get("results_per_platform", 30)

    platforms_cfg = config.get("platforms", {})
    site_names = []
    if platforms_cfg.get("linkedin", True):
        site_names.append("linkedin")
    if platforms_cfg.get("indeed", True):
        site_names.append("indeed")
    if platforms_cfg.get("glassdoor", True):
        site_names.append("glassdoor")

    if not site_names:
        return []

    all_jobs = []
    locations = [l for l in locations_raw if l.lower() not in ("remote", "hybrid")]
    if not locations:
        locations = ["India"]

    for role in roles:
        for location in locations[:2]:  # Limit to 2 locations per role to avoid rate limits
            logger.info("jobspy → Searching '{}' in '{}'", role, location)
            try:
                df = scrape_jobs(
                    site_name=site_names,
                    search_term=role,
                    location=location,
                    results_wanted=results_wanted,
                    hours_old=72,
                    country_indeed="India",
                )
                if df is None or df.empty:
                    continue

                for _, row in df.iterrows():
                    job = {
                        "title": str(row.get("title", "")),
                        "company": str(row.get("company", "")),
                        "location": str(row.get("location", "")),
                        "platform": str(row.get("site", "unknown")),
                        "job_url": str(row.get("job_url", "")),
                        "description": str(row.get("description", ""))[:5000],
                        "salary": str(row.get("min_amount", "")) or "",
                        "date_posted": str(row.get("date_posted", "")),
                    }
                    all_jobs.append(job)

                time.sleep(2)  # Polite delay between searches
            except Exception as e:
                logger.error("jobspy error for '{}' in '{}': {}", role, location, e)
                continue

    logger.info("jobspy found {} raw jobs total", len(all_jobs))
    return all_jobs
