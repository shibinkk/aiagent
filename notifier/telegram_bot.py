"""
notifier/telegram_bot.py
Sends job alerts via Telegram Bot API with inline Apply buttons.
Also runs a background polling loop to handle Apply callbacks.
"""

import os
import threading
import time
import requests
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ── Polling state ────────────────────────────────────────────────────────────
_polling_active = False
_last_update_id = 0
_polling_thread: threading.Thread | None = None


def _get_bot_config() -> tuple[str, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    return token, chat_id


# ── Core send helpers ────────────────────────────────────────────────────────

def send_message(text: str, parse_mode: str = "HTML",
                 reply_markup: dict | None = None) -> bool:
    """Send a plain text (or keyboard) message via Telegram."""
    token, chat_id = _get_bot_config()
    if not token or not chat_id:
        logger.warning("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.ok:
            return True
        logger.warning("Telegram send failed: {}", resp.text)
        return False
    except Exception as e:
        logger.error("Telegram error: {}", e)
        return False


def _answer_callback(token: str, callback_query_id: str, text: str = ""):
    """Acknowledge a callback so the spinner on the button stops."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/answerCallbackQuery",
            json={"callback_query_id": callback_query_id, "text": text},
            timeout=5,
        )
    except Exception:
        pass


def _edit_message_text(token: str, chat_id: str, message_id: int, text: str):
    """Edit an existing message in-place (used to update Apply button result)."""
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
    except Exception:
        pass


# ── Job alert with inline Apply button ──────────────────────────────────────

def send_job_alert(job: dict) -> bool:
    """
    Send an instant alert for a high-score job match.
    Includes an inline [✅ Apply Now] button that triggers auto-apply when tapped.
    """
    score = job.get("ai_score", 0)
    title = job.get("title", "Unknown")
    company = job.get("company", "Unknown")
    location = job.get("location", "")
    platform = job.get("platform", "")
    url = job.get("job_url", "")
    summary = job.get("ai_summary", "")
    job_id = job.get("id", 0)

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

    # Build inline keyboard
    buttons: list[list[dict]] = []
    row: list[dict] = []

    # Apply button (only for LinkedIn — that's what our Selenium handles)
    if job_id and ("linkedin" in (platform or "").lower() or "linkedin.com" in (url or "")):
        row.append({
            "text": "✅ Apply Now",
            "callback_data": f"apply_{job_id}"
        })

    # View job link button (opens URL directly)
    if url:
        row.append({"text": "🔗 View Job", "url": url})

    if row:
        buttons.append(row)

    reply_markup = {"inline_keyboard": buttons} if buttons else None

    return send_message(msg, reply_markup=reply_markup)


# ── Callback handler (called from polling loop) ──────────────────────────────

def _handle_apply_callback(token: str, chat_id: str,
                            callback_query_id: str, message_id: int,
                            job_id: int):
    """
    Triggered when user taps [✅ Apply Now] in Telegram.
    Runs linkedin_apply in a thread and updates the message with the result.
    """
    _answer_callback(token, callback_query_id, "⏳ Starting application…")

    def _do():
        try:
            # Import here to avoid circular imports at module load
            import sys
            import os as _os
            # Ensure project root on path (this module lives in notifier/)
            project_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)

            from tracker.database import get_job_by_id, update_job_status, increment_stat
            from applicator.linkedin_apply import apply_to_job
            from notifier.telegram_bot import send_message as _send

            job = get_job_by_id(job_id)
            if not job:
                _edit_message_text(token, chat_id, message_id,
                                   f"❌ Job #{job_id} not found in database.")
                return

            resume_path = _os.path.join(project_root, "resume", "resume.pdf")
            cover_letter = job.get("cover_letter") or ""
            if not cover_letter:
                try:
                    from ai_engine.cover_letter import generate_cover_letter
                    cover_letter = generate_cover_letter(None, "", job)
                except Exception:
                    cover_letter = ""

            success = apply_to_job(
                job,
                resume_path=resume_path,
                cover_letter=cover_letter,
            )

            if success:
                update_job_status(job_id, "applied")
                increment_stat("jobs_applied")
                result_text = (
                    f"📨 <b>Application Submitted!</b>\n\n"
                    f"<b>{job.get('title')}</b> @ {job.get('company')}\n"
                    f"Platform: {job.get('platform', '').title()}\n"
                    f"Score: {job.get('ai_score', 0):.0f}/100\n\n"
                    f"✅ Applied via LinkedIn Easy Apply"
                )
            else:
                result_text = (
                    f"⚠️ <b>Auto-apply failed</b>\n\n"
                    f"<b>{job.get('title')}</b> @ {job.get('company')}\n\n"
                    f"Possible reasons: not an Easy Apply job, CAPTCHA, or login issue.\n"
                    f"<a href=\"{job.get('job_url', '')}\">Apply manually →</a>"
                )

            _edit_message_text(token, chat_id, message_id, result_text)

        except Exception as e:
            logger.error("Telegram apply callback error: {}", e)
            _edit_message_text(token, chat_id, message_id,
                               f"❌ Error during auto-apply: {e}")

    threading.Thread(target=_do, daemon=True).start()


# ── Long-polling loop ────────────────────────────────────────────────────────

def _poll_loop():
    """
    Runs in a background daemon thread.
    Calls getUpdates in long-poll mode (timeout=30s) and handles callbacks.
    """
    global _last_update_id, _polling_active

    token, chat_id = _get_bot_config()
    if not token:
        logger.warning("Telegram polling skipped — no BOT_TOKEN configured.")
        return

    logger.info("📡 Telegram bot polling started (listening for Apply callbacks)…")
    _polling_active = True

    while _polling_active:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"offset": _last_update_id + 1, "timeout": 30, "allowed_updates": ["callback_query"]},
                timeout=35,
            )
            if not resp.ok:
                time.sleep(5)
                continue

            updates = resp.json().get("result", [])
            for update in updates:
                _last_update_id = update["update_id"]
                cq = update.get("callback_query")
                if not cq:
                    continue

                data: str = cq.get("data", "")
                cq_id: str = cq["id"]
                msg = cq.get("message", {})
                msg_id: int = msg.get("message_id", 0)
                cq_chat_id: str = str(msg.get("chat", {}).get("id", chat_id))

                if data.startswith("apply_"):
                    try:
                        job_id = int(data.split("_", 1)[1])
                        _handle_apply_callback(token, cq_chat_id, cq_id, msg_id, job_id)
                    except (ValueError, IndexError):
                        _answer_callback(token, cq_id, "❌ Invalid job ID")

        except requests.exceptions.ReadTimeout:
            # Normal for long-polling — just loop again
            continue
        except Exception as e:
            logger.error("Telegram poll error: {}", e)
            time.sleep(10)


def start_polling():
    """
    Start the Telegram callback polling loop in a background daemon thread.
    Safe to call multiple times — only one thread runs at a time.
    """
    global _polling_thread, _polling_active
    if _polling_thread and _polling_thread.is_alive():
        return  # Already running
    _polling_active = True
    _polling_thread = threading.Thread(target=_poll_loop, daemon=True, name="telegram-poll")
    _polling_thread.start()


def stop_polling():
    """Signal the polling loop to stop."""
    global _polling_active
    _polling_active = False


# ── Notification helpers ─────────────────────────────────────────────────────

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
