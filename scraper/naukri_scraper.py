"""
scraper/naukri_scraper.py
Scrapes Naukri.com for job listings using requests + BeautifulSoup.
Note: Naukri uses JavaScript-rendered content; Selenium fallback is used.
"""

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
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_naukri(config: dict) -> list[dict]:
    """Scrape job listings from Naukri.com."""
    if not config.get("platforms", {}).get("naukri", True):
        return []

    roles = config["job_search"]["roles"]
    results_wanted = config["job_search"].get("results_per_platform", 30)
    all_jobs = []

    for role in roles[:3]:  # Limit roles to avoid rate limits
        jobs = _search_naukri(role, results_wanted)
        all_jobs.extend(jobs)
        time.sleep(3)

    logger.info("Naukri found {} jobs", len(all_jobs))
    return all_jobs


def _search_naukri(query: str, limit: int = 30) -> list[dict]:
    safe_query = query.replace(" ", "-").lower()
    url = f"https://www.naukri.com/{safe_query}-jobs"
    jobs = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning("Naukri returned status {} for '{}'", resp.status_code, query)
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        # Naukri article cards
        cards = soup.select("article.jobTuple") or soup.select("div.jobTupleHeader")
        if not cards:
            # Try newer layout
            cards = soup.select("div.srp-jobtuple-wrapper")

        for card in cards[:limit]:
            try:
                title_el = card.select_one("a.title") or card.select_one("a.jobTitle")
                company_el = card.select_one("a.subTitle") or card.select_one("a.companyName")
                location_el = card.select_one("li.location span") or card.select_one("span.locWdth")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                location = location_el.get_text(strip=True) if location_el else "India"
                job_url = title_el.get("href", "") if title_el else ""

                if title and company:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "platform": "naukri",
                        "job_url": job_url,
                        "description": "",
                        "salary": "",
                        "date_posted": "",
                    })
            except Exception:
                continue

    except requests.RequestException as e:
        logger.error("Naukri scrape error for '{}': {}", query, e)

    return jobs
