"""
applicator/__init__.py
Auto-apply orchestrator — respects approval queue and daily limits.
"""

import os
from pathlib import Path
from loguru import logger
from tracker.database import (
    get_jobs, update_job_status, add_to_approval_queue,
    get_pending_approvals, approve_job, get_daily_stats
)
from .linkedin_apply import apply_to_job as linkedin_apply


def run_applications(config: dict, resume_path: str):
    """
    Main entry point for auto-apply loop.
    Checks daily limit, approval mode, and applies to eligible jobs.
    """
    apply_cfg = config.get("apply", {})
    auto_apply = apply_cfg.get("auto_apply", False)
    require_approval = apply_cfg.get("require_approval", True)
    max_per_day = apply_cfg.get("max_applications_per_day", 15)
    platforms = apply_cfg.get("platforms_to_apply", ["linkedin"])

    # Check daily limit
    stats = get_daily_stats()
    applied_today = stats.get("jobs_applied", 0)
    if applied_today >= max_per_day:
        logger.info("Daily application limit reached ({}/{})", applied_today, max_per_day)
        return

    remaining = max_per_day - applied_today
    eligible_jobs = get_jobs(status="scored", limit=50)

    # Sort by AI score descending
    eligible_jobs.sort(key=lambda j: j.get("ai_score", 0), reverse=True)
    threshold = config["ai"].get("score_threshold", 65)
    eligible_jobs = [j for j in eligible_jobs if j.get("ai_score", 0) >= threshold]

    logger.info(
        "Applicator: {} eligible jobs above threshold {}, daily remaining: {}",
        len(eligible_jobs), threshold, remaining
    )

    applied_count = 0
    for job in eligible_jobs:
        if applied_count >= remaining:
            break

        platform = job.get("platform", "")

        if require_approval and not auto_apply:
            # Put in approval queue for manual review
            add_to_approval_queue(job["id"])
            update_job_status(job["id"], "pending_approval")
            logger.info("⏳ Added to approval queue: {} @ {}", job["title"], job["company"])
            continue

        # Auto-apply based on platform
        success = False
        if "linkedin" in platform and "linkedin" in platforms:
            success = linkedin_apply(
                job,
                resume_path=str(Path(resume_path).absolute()),
                cover_letter=job.get("cover_letter", ""),
            )

        if success:
            update_job_status(job["id"], "applied")
            applied_count += 1
            logger.success("Applied ({}/{}): {} @ {}", applied_count, remaining, job["title"], job["company"])
        else:
            # Can't auto-apply — mark for manual review
            add_to_approval_queue(job["id"])
            update_job_status(job["id"], "pending_approval")

    logger.info("Applicator done. Applied to {} jobs this run.", applied_count)
