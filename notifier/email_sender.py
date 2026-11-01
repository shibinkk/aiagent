"""
notifier/email_sender.py
Sends a beautiful HTML email digest of job search activity.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from loguru import logger


def send_daily_email(summary_text: str, jobs: list[dict], stats: dict) -> bool:
    """Send the daily HTML email digest."""
    sender = os.getenv("EMAIL_SENDER", "")
    password = os.getenv("EMAIL_PASSWORD", "")
    recipient = os.getenv("EMAIL_RECIPIENT", sender)

    if not sender or not password:
        logger.warning("Email not configured. Set EMAIL_SENDER and EMAIL_PASSWORD in .env")
        return False

    subject = f"🤖 Job Search Report — {datetime.now().strftime('%B %d, %Y')}"
    html = _build_html(summary_text, jobs, stats)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        logger.success("Daily email sent to {}", recipient)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Email auth failed. Use Gmail App Password (not regular password).")
        return False
    except Exception as e:
        logger.error("Email send error: {}", e)
        return False


def _build_html(summary: str, jobs: list[dict], stats: dict) -> str:
    top_jobs_html = ""
    sorted_jobs = sorted(jobs, key=lambda j: j.get("ai_score", 0), reverse=True)[:10]
    for j in sorted_jobs:
        score = j.get("ai_score", 0)
        color = "#22c55e" if score >= 80 else "#f59e0b" if score >= 60 else "#6b7280"
        badge = "🔥 Hot" if score >= 85 else "✅ Good" if score >= 70 else "📋 Ok"
        url = j.get("job_url", "#")
        top_jobs_html += f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">
            <a href="{url}" style="color:#3b82f6;font-weight:600;text-decoration:none;">{j.get('title','')}</a>
          </td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{j.get('company','')}</td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">{j.get('platform','').title()}</td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">
            <span style="background:{color};color:white;padding:3px 8px;border-radius:9999px;font-size:12px;font-weight:600;">
              {score:.0f} {badge}
            </span>
          </td>
          <td style="padding:10px;border-bottom:1px solid #e5e7eb;">
            <span style="text-transform:capitalize;">{j.get('status','')}</span>
          </td>
        </tr>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Job Search Report</title>
</head>
<body style="font-family:Inter,Arial,sans-serif;background:#f8fafc;margin:0;padding:20px;">
  <div style="max-width:700px;margin:0 auto;background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
    
    <!-- Header -->
    <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:32px;text-align:center;">
      <h1 style="color:white;margin:0;font-size:24px;">🤖 AI Job Search Agent</h1>
      <p style="color:rgba(255,255,255,0.8);margin:8px 0 0;">Daily Report — {datetime.now().strftime('%A, %B %d %Y')}</p>
    </div>

    <!-- Stats -->
    <div style="display:flex;gap:16px;padding:24px;background:#f8fafc;">
      {_stat_card('🔍 Found', stats.get('found',0), '#3b82f6')}
      {_stat_card('✅ Applied', stats.get('applied',0), '#22c55e')}
      {_stat_card('💼 Interview', stats.get('interview',0), '#f59e0b')}
      {_stat_card('❌ Rejected', stats.get('rejected',0), '#ef4444')}
    </div>

    <!-- AI Summary -->
    <div style="padding:24px;">
      <h2 style="color:#1e293b;font-size:18px;margin-top:0;">📝 AI Summary</h2>
      <p style="color:#475569;line-height:1.7;white-space:pre-line;">{summary[:1500]}</p>
    </div>

    <!-- Top Jobs Table -->
    <div style="padding:0 24px 24px;">
      <h2 style="color:#1e293b;font-size:18px;">🏆 Top Matching Jobs</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">
        <thead>
          <tr style="background:#f1f5f9;">
            <th style="padding:10px;text-align:left;color:#64748b;">Title</th>
            <th style="padding:10px;text-align:left;color:#64748b;">Company</th>
            <th style="padding:10px;text-align:left;color:#64748b;">Platform</th>
            <th style="padding:10px;text-align:left;color:#64748b;">Score</th>
            <th style="padding:10px;text-align:left;color:#64748b;">Status</th>
          </tr>
        </thead>
        <tbody>{top_jobs_html}</tbody>
      </table>
    </div>

    <!-- Footer -->
    <div style="background:#f1f5f9;padding:20px;text-align:center;">
      <a href="http://localhost:5000" style="color:#6366f1;font-weight:600;">Open Full Dashboard →</a>
      <p style="color:#94a3b8;font-size:12px;margin:8px 0 0;">Powered by AI Job Search Agent • Running locally on your machine</p>
    </div>
  </div>
</body>
</html>
"""


def _stat_card(label: str, value: int, color: str) -> str:
    return f"""
    <div style="flex:1;background:white;border-radius:12px;padding:16px;text-align:center;border-left:4px solid {color};">
      <div style="font-size:28px;font-weight:700;color:{color};">{value}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px;">{label}</div>
    </div>
    """
