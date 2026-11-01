"""
main.py
AI Job Search Agent — Main orchestrator and scheduler.
Runs all modules in a scheduled loop and keeps the dashboard alive.
"""

import os
import sys
import threading
import yaml
from pathlib import Path
from datetime import datetime
from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# ── Load environment ────────────────────────────────────────────────────────
load_dotenv()

# ── Project imports ─────────────────────────────────────────────────────────
from tracker.database import init_db, insert_job, update_job_ai, increment_stat, get_stats_summary
from scraper import scrape_all_platforms
from filter import filter_jobs
from ai_engine import OllamaClient, score_job, generate_cover_letter, generate_daily_summary
from applicator import run_applications
from notifier import send_job_alert, send_daily_summary, send_daily_email
from resume.resume_parser import extract_resume_text


# ── Setup logging ────────────────────────────────────────────────────────────
log_path = Path("logs")
log_path.mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}")
logger.add("logs/agent.log", rotation="10 MB", retention="14 days", level="DEBUG")


def load_config() -> dict:
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


def run_job_cycle(config: dict, ai_client: OllamaClient, resume_text: str):
    """
    One full cycle: scrape → filter → score → generate cover letters → queue applications.
    """
    logger.info("═══════════════════════════════════════")
    logger.info("  JOB CYCLE STARTED — {}", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("═══════════════════════════════════════")

    threshold = config["ai"].get("score_threshold", 65)
    notify_cfg = config.get("notifications", {})

    # ── 1. Scrape ────────────────────────────────────────────────────────────
    raw_jobs = scrape_all_platforms(config)
    if not raw_jobs:
        logger.warning("No jobs scraped this cycle.")
        return

    # ── 2. Filter ────────────────────────────────────────────────────────────
    filtered = filter_jobs(raw_jobs, config)

    # ── 3. Dedup & save to DB ────────────────────────────────────────────────
    new_jobs = []
    for job in filtered:
        job_id = insert_job(job)
        if job_id:
            job["_id"] = job_id
            new_jobs.append(job)
            increment_stat("jobs_found")

    logger.info("New unique jobs saved: {}", len(new_jobs))

    # ── 4. AI Scoring & Cover Letter Generation ──────────────────────────────
    if not ai_client.is_available():
        logger.info("Ollama offline — using built-in intelligent QA/SDET heuristic scoring engine.")
    
    logger.info("AI scoring {} new jobs...", len(new_jobs))
    for i, job in enumerate(new_jobs, 1):
        logger.info("  [{}/{}] Scoring: {} @ {}", i, len(new_jobs), job.get("title"), job.get("company"))
        result = score_job(ai_client, resume_text, job)
        score = result["score"]
        summary = result.get("summary", "")


            cover_letter = ""
            if score >= threshold:
                cover_letter = generate_cover_letter(
                    ai_client, resume_text, job,
                    max_words=config["ai"].get("cover_letter_max_words", 300)
                )

            update_job_ai(job["_id"], score, summary, cover_letter)
            increment_stat("jobs_scored")

            # Instant notification for high-score jobs
            if score >= threshold and notify_cfg.get("notify_on_new_match", True):
                job["ai_score"] = score
                job["ai_summary"] = summary
                send_job_alert(job)

    # ── 5. Auto-apply ────────────────────────────────────────────────────────
    if config.get("apply", {}).get("auto_apply") or config.get("apply", {}).get("require_approval"):
        run_applications(config, config["resume"]["path"])

    logger.success("Job cycle complete.")


def run_daily_summary(config: dict, ai_client: OllamaClient):
    """Generate and send the daily summary report."""
    logger.info("Generating daily summary...")
    stats = get_stats_summary()

    summary = generate_daily_summary(ai_client)
    notify_cfg = config.get("notifications", {})

    if notify_cfg.get("telegram"):
        send_daily_summary(summary, stats)

    if notify_cfg.get("email"):
        from tracker.database import get_jobs
        all_jobs = get_jobs(limit=100)
        send_daily_email(summary, all_jobs, stats)

    logger.success("Daily summary sent.")


def start_dashboard():
    """Run Flask dashboard in a background thread."""
    try:
        sys.path.insert(0, str(Path("dashboard").absolute()))
        from dashboard.app import app
        port = int(os.getenv("DASHBOARD_PORT", 5000))
        logger.info("Dashboard starting at http://localhost:{}", port)
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error("Dashboard failed to start: {}", e)


def main():
    logger.info("🤖 AI Job Search Agent starting...")

    # ── Init DB ──────────────────────────────────────────────────────────────
    init_db()

    # ── Load config ──────────────────────────────────────────────────────────
    config = load_config()

    # ── Parse resume ─────────────────────────────────────────────────────────
    resume_path = config.get("resume", {}).get("path", "resume/resume.pdf")
    resume_text = extract_resume_text(resume_path)
    if not resume_text:
        logger.warning("No resume text found! Add your resume.pdf to resume/resume.pdf")
        resume_text = "No resume provided."

    # ── Init AI client ───────────────────────────────────────────────────────
    ai_config = config.get("ai", {})
    ai_client = OllamaClient(
        base_url=ai_config.get("ollama_url", "http://localhost:11434"),
        model=ai_config.get("model", "llama3"),
    )

    if ai_client.is_available():
        logger.success("✅ Ollama is running with model: {}", ai_config.get("model", "llama3"))
    else:
        logger.warning("⚠️  Ollama not detected. AI features will be skipped.")
        logger.warning("   Install: https://ollama.com | Then run: ollama pull llama3")

    # ── Start Dashboard ──────────────────────────────────────────────────────
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()

    # ── Scheduler ─────────────────────────────────────────────────────────────
    scheduler = BackgroundScheduler(timezone=config["scheduler"].get("timezone", "Asia/Kolkata"))

    # Job cycle every N hours
    interval_hours = config["scheduler"].get("scrape_interval_hours", 6)
    scheduler.add_job(
        func=lambda: run_job_cycle(config, ai_client, resume_text),
        trigger="interval",
        hours=interval_hours,
        id="job_cycle",
        next_run_time=datetime.now(),  # Run immediately on start
    )

    # Daily summary at configured time
    summary_time = config["scheduler"].get("daily_summary_time", "08:00")
    h, m = summary_time.split(":")
    scheduler.add_job(
        func=lambda: run_daily_summary(config, ai_client),
        trigger=CronTrigger(hour=int(h), minute=int(m)),
        id="daily_summary",
    )

    scheduler.start()

    logger.success("═══════════════════════════════════════════════")
    logger.success("  ✅ Agent is running!")
    logger.success("  📊 Dashboard: http://localhost:{}", os.getenv("DASHBOARD_PORT", 5000))
    logger.success("  🔄 Scrape interval: every {} hours", interval_hours)
    logger.success("  📬 Daily summary: {}".format(summary_time))
    logger.success("═══════════════════════════════════════════════")

    # Keep main thread alive
    try:
        while True:
            import time
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Agent shutting down...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
