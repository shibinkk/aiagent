"""
scraper/__init__.py
Orchestrates all scrapers and returns a unified list of jobs.
"""

from .jobspy_scraper import scrape_with_jobspy
from .naukri_scraper import scrape_naukri
from .internshala_scraper import scrape_internshala
from loguru import logger


def scrape_all_platforms(config: dict) -> list[dict]:
    """Run all scrapers and combine results."""
    all_jobs = []

    logger.info("═══ Starting job scrape across all platforms ═══")

    # jobspy handles LinkedIn, Indeed, Glassdoor
    try:
        jobs = scrape_with_jobspy(config)
        all_jobs.extend(jobs)
        logger.success("jobspy (LinkedIn/Indeed/Glassdoor): {} jobs", len(jobs))
    except Exception as e:
        logger.error("jobspy scraper failed: {}", e)

    # Naukri
    try:
        jobs = scrape_naukri(config)
        all_jobs.extend(jobs)
        logger.success("Naukri: {} jobs", len(jobs))
    except Exception as e:
        logger.error("Naukri scraper failed: {}", e)

    # Internshala
    try:
        jobs = scrape_internshala(config)
        all_jobs.extend(jobs)
        logger.success("Internshala: {} jobs", len(jobs))
    except Exception as e:
        logger.error("Internshala scraper failed: {}", e)

    logger.info("═══ Total raw jobs collected: {} ═══", len(all_jobs))
    return all_jobs
