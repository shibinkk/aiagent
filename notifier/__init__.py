"""
notifier/__init__.py
"""
from .telegram_bot import send_message, send_job_alert, send_daily_summary, send_applied_notification
from .email_sender import send_daily_email

__all__ = [
    "send_message",
    "send_job_alert",
    "send_daily_summary",
    "send_applied_notification",
    "send_daily_email",
]
