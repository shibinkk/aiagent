"""
applicator/linkedin_apply.py
Automates LinkedIn Easy Apply using Selenium.
"""

import time
from loguru import logger

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

import os


def _get_driver(headless: bool = False):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        driver = webdriver.Chrome(options=options)
    except Exception:
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            logger.error("Failed to launch Chrome driver: {}", e)
            raise e
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def linkedin_login(driver, email: str, password: str) -> bool:
    """Log into LinkedIn."""
    try:
        driver.get("https://www.linkedin.com/login")
        wait = WebDriverWait(driver, 15)

        wait.until(EC.presence_of_element_located((By.ID, "username")))
        driver.find_element(By.ID, "username").send_keys(email)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        time.sleep(3)
        if "feed" in driver.current_url or "checkpoint" not in driver.current_url:
            logger.success("LinkedIn login successful")
            return True
        else:
            logger.error("LinkedIn login may require 2FA or CAPTCHA")
            return False
    except Exception as e:
        logger.error("LinkedIn login error: {}", e)
        return False


def apply_to_job(job: dict, resume_path: str, cover_letter: str) -> bool:
    """
    Attempt LinkedIn Easy Apply on a job URL.
    Returns True if application was submitted successfully.
    """
    if not SELENIUM_AVAILABLE:
        logger.warning("Selenium not installed. Cannot auto-apply.")
        return False

    email = os.getenv("LINKEDIN_EMAIL", "")
    password = os.getenv("LINKEDIN_PASSWORD", "")
    if not email or not password:
        logger.warning("LinkedIn credentials not set in .env")
        return False

    job_url = job.get("job_url", "")
    if not job_url or "linkedin.com" not in job_url:
        return False

    driver = _get_driver(headless=False)  # Keep visible for safety
    try:
        if not linkedin_login(driver, email, password):
            return False

        driver.get(job_url)
        time.sleep(3)

        wait = WebDriverWait(driver, 10)

        # Click Easy Apply button
        try:
            easy_apply_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.jobs-apply-button")
                )
            )
            easy_apply_btn.click()
            time.sleep(2)
        except TimeoutException:
            logger.warning("No Easy Apply button found for: {}", job.get("title"))
            return False

        # Navigate through application steps
        max_steps = 10
        for step in range(max_steps):
            time.sleep(1.5)

            # Upload resume if prompted
            try:
                file_input = driver.find_element(
                    By.CSS_SELECTOR, "input[type='file']"
                )
                file_input.send_keys(str(resume_path))
                time.sleep(1)
            except NoSuchElementException:
                pass

            # Fill cover letter textarea if visible
            try:
                textareas = driver.find_elements(By.TAG_NAME, "textarea")
                for ta in textareas:
                    if ta.is_displayed() and not ta.get_attribute("value"):
                        ta.send_keys(cover_letter[:2000])
            except Exception:
                pass

            # Check for Submit button
            try:
                submit_btn = driver.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Submit application']"
                )
                submit_btn.click()
                logger.success(
                    "✅ Applied to: {} @ {}", job.get("title"), job.get("company")
                )
                return True
            except NoSuchElementException:
                pass

            # Click Next/Continue
            try:
                next_btn = driver.find_element(
                    By.CSS_SELECTOR,
                    "button[aria-label='Continue to next step']"
                )
                next_btn.click()
            except NoSuchElementException:
                try:
                    review_btn = driver.find_element(
                        By.CSS_SELECTOR, "button[aria-label='Review your application']"
                    )
                    review_btn.click()
                except NoSuchElementException:
                    break

        logger.warning("Could not complete application for: {}", job.get("title"))
        return False

    except Exception as e:
        logger.error("LinkedIn apply error for {}: {}", job.get("title"), e)
        return False
    finally:
        driver.quit()
