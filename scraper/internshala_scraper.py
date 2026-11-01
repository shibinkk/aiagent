"""
scraper/internshala_scraper.py
Scrapes Internshala for jobs and internships.
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
}


def scrape_internshala(config: dict) -> list[dict]:
    """Scrape jobs from Internshala."""
    if not config.get("platforms", {}).get("internshala", True):
        return []

    roles = config["job_search"]["roles"]
    all_jobs = []

    for role in roles[:3]:
        jobs = _search_internshala(role)
        all_jobs.extend(jobs)
        time.sleep(2)

    logger.info("Internshala found {} jobs", len(all_jobs))
    return all_jobs


def _search_internshala(query: str) -> list[dict]:
    safe_query = query.replace(" ", "-").lower()
    url = f"https://internshala.com/jobs/{safe_query}-jobs/"
    jobs = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("div.individual_internship")

        for card in cards[:30]:
            try:
                title_el = card.select_one("h3.job-internship-name a") or card.select_one("a.job-title-href")
                company_el = card.select_one("p.company-name") or card.select_one("a.link-container")
                location_el = card.select_one("div.row-1-item span") or card.select_one("a.location_link")

                title = title_el.get_text(strip=True) if title_el else query
                company = company_el.get_text(strip=True) if company_el else ""
                location = location_el.get_text(strip=True) if location_el else "India"
                job_url = ("https://internshala.com" + title_el.get("href", "")) if title_el else ""

                if title and company:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "platform": "internshala",
                        "job_url": job_url,
                        "description": "",
                        "salary": "",
                        "date_posted": "",
                    })
            except Exception:
                continue

    except requests.RequestException as e:
        logger.error("Internshala error for '{}': {}", query, e)

    return jobs
