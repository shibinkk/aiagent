"""
notifier/telegram_bot.py
Sends job alerts and daily summaries via Telegram Bot API.
"""

import os
import asyncio
import requests
from loguru import logger


def _get_bot_config() -> tuple[str, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    return token, chat_id


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Send a plain text message via Telegram."""
    token, chat_id = _get_bot_config()
    if not token or not chat_id:
        logger.warning("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.ok:
            return True
        else:
            logger.warning("Telegram send failed: {}", resp.text)
            return False
    except Exception as e:
        logger.error("Telegram error: {}", e)
        return False


def send_job_alert(job: dict) -> bool:
    """Send an instant alert for a high-score job match."""
    score = job.get("ai_score", 0)
    title = job.get("title", "Unknown")
    company = job.get("company", "Unknown")
    location = job.get("location", "")
    platform = job.get("platform", "")
    url = job.get("job_url", "")
    summary = job.get("ai_summary", "")

    emoji = "🔥" if score >= 85 else "✅" if score >= 70 else "📋"

    msg = (
        f"{emoji} <b>New Job Match!</b>\n\n"
        f"<b>{title}</b>\n"
        f"🏢 {company}\n"
        f"📍 {location}\n"
        f"🌐 {platform.title()}\n"
        f"🎯 AI Score: <b>{score:.0f}/100</b>\n\n"
    )
    if summary:
        msg += f"<i>{summary[:200]}</i>\n\n"
    if url:
        msg += f'<a href="{url}">View Job →</a>'

    return send_message(msg)


def send_daily_summary(summary_text: str, stats: dict) -> bool:
    """Send the daily summary report."""
    msg = (
        f"📊 <b>Daily Job Search Report</b>\n\n"
        f"🔍 Found: {stats.get('found', 0)} | "
        f"✅ Applied: {stats.get('applied', 0)} | "
        f"💼 Interview: {stats.get('interview', 0)}\n\n"
        f"{summary_text[:3000]}\n\n"
        f"🖥️ <a href='http://localhost:5000'>Open Dashboard</a>"
    )
    return send_message(msg)


def send_applied_notification(job: dict) -> bool:
    """Notify when an application is submitted."""
    msg = (
        f"📨 <b>Application Submitted!</b>\n\n"
        f"<b>{job.get('title', '')}</b> @ {job.get('company', '')}\n"
        f"Platform: {job.get('platform', '').title()}\n"
        f"Score: {job.get('ai_score', 0):.0f}/100"
    )
    return send_message(msg)
