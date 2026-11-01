"""
scraper/internshala_scraper.py
Scrapes Internshala for QA / SDET and software testing jobs.
Accurately parses location vs salary / CTC into their distinct fields.
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
}

QA_KEYWORDS = ["test", "qa", "quality", "sdet", "automation", "selenium", "playwright", "cypress"]


def scrape_internshala(config: dict) -> list[dict]:
    """Scrape jobs from Internshala for QA and software testing roles."""
    if not config.get("platforms", {}).get("internshala", True):
        return []

    # Dedicated queries for testing on Internshala
    queries = ["software-testing", "qa", "automation-testing"]
    all_jobs = []
    seen = set()

    for q in queries[:2]:
        jobs = _search_internshala(q)
        for j in jobs:
            key = f"{j['title'].lower()}::{j['company'].lower()}"
            if key not in seen:
                seen.add(key)
                all_jobs.append(j)
        time.sleep(1.5)

    logger.info("Internshala found {} jobs", len(all_jobs))
    return all_jobs


def _search_internshala(query: str) -> list[dict]:
    safe_query = query.replace(" ", "-").lower()
    url = f"https://internshala.com/jobs/{safe_query}-jobs/"
    jobs = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("div.individual_internship")

        for card in cards[:25]:
            try:
                title_el = card.select_one("h2.job-internship-name a") or card.select_one("a.job-title-href") or card.select_one("h3.job-internship-name a")
                company_el = card.select_one("p.company-name") or card.select_one("div.company_name") or card.select_one("a.link-container")
                
                # ── Location Selector ──
                # On Internshala, location is in p.locations / a.location_link / span inside p.row-1-item.locations
                loc_el = (
                    card.select_one("p.row-1-item.locations a")
                    or card.select_one("p.row-1-item.locations span")
                    or card.select_one("a.location_link")
                    or card.select_one("p.locations")
                )
                
                # ── Salary Selector ──
                # Salary is in div.salary / div.row-1-item with money icon / text with currency symbol
                salary_el = (
                    card.select_one("div.salary")
                    or card.select_one("div.row-1-item span.desktop")
                    or card.select_one("div.row-1-item i.ic-16-money + span")
                )

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                
                # If title doesn't match QA/testing keywords, skip completely!
                title_lower = title.lower()
                if not any(k in title_lower for k in QA_KEYWORDS):
                    continue

                raw_loc = loc_el.get_text(strip=True) if loc_el else "India / Remote"
                raw_salary = ""

                # If no direct salary_el, look through items for currency symbol
                if salary_el:
                    raw_salary = salary_el.get_text(strip=True)
                else:
                    for item in card.select("div.row-1-item"):
                        txt = item.get_text(strip=True)
                        if "₹" in txt or "lac" in txt.lower() or "lpa" in txt.lower() or "cpa" in txt.lower():
                            raw_salary = txt
                            break

                # Safety check: if raw_loc accidentally picked up salary text (e.g. contains ₹ or salary)
                if "₹" in raw_loc or "salary" in raw_loc.lower() or "lac" in raw_loc.lower() or "lpa" in raw_loc.lower():
                    if not raw_salary:
                        raw_salary = raw_loc
                    raw_loc = "India / Remote"

                # Clean up duplicated salary strings like "₹ 2,00,000 - 3,00,000₹ 2,00,000 - 3,00,000 /year"
                if raw_salary:
                    match = re.search(r"(₹\s*[\d,]+\s*-\s*[\d,]+(?:\s*/\s*year)?)", raw_salary)
                    if match:
                        raw_salary = match.group(1)
                    else:
                        raw_salary = raw_salary.replace("\n", " ").strip()
                else:
                    raw_salary = "Competitive salary"

                job_url = ("https://internshala.com" + title_el.get("href", "")) if title_el else ""

                if title and company:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": raw_loc,
                        "platform": "internshala",
                        "job_url": job_url,
                        "description": f"{title} position at {company} ({raw_loc}). Focus on software quality assurance and testing.",
                        "salary": raw_salary,
                        "date_posted": "Recent",
                    })
            except Exception:
                continue

    except requests.RequestException as e:
        logger.error("Internshala error for '{}': {}", query, e)

    return jobs
