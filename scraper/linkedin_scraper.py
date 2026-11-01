"""
scraper/linkedin_scraper.py
Scrapes live LinkedIn job postings using LinkedIn's public guest search API.
Fast, reliable, and does not require credentials or proxies.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from loguru import logger

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_linkedin(config: dict) -> list[dict]:
    """Scrape live LinkedIn jobs using public guest search."""
    if not config.get("platforms", {}).get("linkedin", True):
        return []

    roles = config.get("job_search", {}).get("roles", ["SDET", "QA Automation Engineer"])
    locations = config.get("job_search", {}).get("locations", ["Kochi", "Bangalore", "Kerala", "India"])
    results_wanted = config.get("job_search", {}).get("results_per_platform", 20)

    # Filter out purely non-geographic locations
    clean_locations = [l for l in locations if l.lower() not in ("remote", "hybrid")]
    if not clean_locations:
        clean_locations = ["India"]

    all_jobs = []
    seen_urls = set()

    # Search top 2 roles across top 2 locations to keep requests fast and focused
    target_roles = roles[:2] if len(roles) >= 2 else roles
    target_locs = clean_locations[:3]

    for role in target_roles:
        for loc in target_locs:
            logger.info("LinkedIn Guest API → Searching '{}' in '{}'", role, loc)
            try:
                jobs = _search_linkedin_guest(role, loc, limit=min(results_wanted, 15))
                for j in jobs:
                    if j["job_url"] not in seen_urls:
                        seen_urls.add(j["job_url"])
                        all_jobs.append(j)
                time.sleep(1.5)  # Polite delay
            except Exception as e:
                logger.error("LinkedIn guest error for '{}' in '{}': {}", role, loc, e)

    logger.info("LinkedIn guest API found {} jobs total", len(all_jobs))
    return all_jobs


def _search_linkedin_guest(role: str, location: str, limit: int = 15) -> list[dict]:
    """Fetch search results from LinkedIn guest API."""
    params = {
        "keywords": role,
        "location": location,
        "start": 0,
    }
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    jobs = []

    resp = requests.get(url, params=params, headers=HEADERS, timeout=12)
    if resp.status_code != 200:
        logger.warning("LinkedIn guest returned status {} for '{}' in '{}'", resp.status_code, role, location)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    cards = soup.select("li")

    for card in cards[:limit]:
        try:
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle a") or card.select_one("h4.base-search-card__subtitle")
            loc_el = card.select_one("span.job-search-card__location")
            link_el = card.select_one("a.base-card__full-link") or card.select_one("a")
            time_el = card.select_one("time")

            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            job_loc = loc_el.get_text(strip=True) if loc_el else location
            job_url = link_el.get("href", "") if link_el else ""
            date_posted = time_el.get("datetime", "") if time_el else ""

            # Clean job URL
            if job_url and "?" in job_url:
                job_url = job_url.split("?")[0]

            if title and company:
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": job_loc,
                    "platform": "linkedin",
                    "job_url": job_url,
                    "description": f"{title} opportunity at {company} in {job_loc}. Relevant for QA Automation and SDET professionals.",
                    "salary": "As per company standard",
                    "date_posted": date_posted,
                })
        except Exception:
            continue

    return jobs
