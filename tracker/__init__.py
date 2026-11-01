"""tracker/__init__.py"""
from .database import (
    init_db, insert_job, update_job_ai, update_job_status,
    get_jobs, get_stats_summary, get_pending_approvals,
    add_to_approval_queue, approve_job, reject_job,
    get_daily_stats, increment_stat, get_monthly_activity
)
