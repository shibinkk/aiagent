"""
scraper/__init__.py
Orchestrates scrapers across LinkedIn, Indeed, Naukri, Glassdoor, and Internshala.
Returns a unified list of jobs with clean location, salary, and metadata.
"""

from .linkedin_scraper import scrape_linkedin
from .jobspy_scraper import scrape_with_jobspy
from .naukri_scraper import scrape_naukri
from .internshala_scraper import scrape_internshala
from loguru import logger


def scrape_all_platforms(config: dict) -> list[dict]:
    """Run all scrapers and combine results."""
    all_jobs = []
    seen = set()

    logger.info("═══ Starting job scrape across all platforms ═══")

    # 1. LinkedIn (Dedicated fast guest API + rich data)
    try:
        jobs = scrape_linkedin(config)
        for j in jobs:
            key = f"{j['title'].lower()}::{j['company'].lower()}"
            if key not in seen:
                seen.add(key)
                all_jobs.append(j)
        logger.success("LinkedIn: {} jobs", len(jobs))
    except Exception as e:
        logger.error("LinkedIn scraper failed: {}", e)

    # 2. Indeed & Glassdoor (via JobSpy)
    try:
        jobs = scrape_with_jobspy(config)
        for j in jobs:
            key = f"{j['title'].lower()}::{j['company'].lower()}"
            if key not in seen:
                seen.add(key)
                all_jobs.append(j)
        logger.success("JobSpy (Indeed/Glassdoor): {} jobs", len(jobs))
    except Exception as e:
        logger.error("JobSpy scraper failed: {}", e)

    # 3. Naukri (via JobSpy Naukri provider)
    try:
        jobs = scrape_naukri(config)
        for j in jobs:
            key = f"{j['title'].lower()}::{j['company'].lower()}"
            if key not in seen:
                seen.add(key)
                all_jobs.append(j)
        logger.success("Naukri: {} jobs", len(jobs))
    except Exception as e:
        logger.error("Naukri scraper failed: {}", e)

    # 4. Internshala
    try:
        jobs = scrape_internshala(config)
        for j in jobs:
            key = f"{j['title'].lower()}::{j['company'].lower()}"
            if key not in seen:
                seen.add(key)
                all_jobs.append(j)
        logger.success("Internshala: {} jobs", len(jobs))
    except Exception as e:
        logger.error("Internshala scraper failed: {}", e)

    logger.info("═══ Total raw jobs collected: {} ═══", len(all_jobs))
    return all_jobs
