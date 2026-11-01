"""
ai_engine/summarizer.py
Generates a daily summary report of all job activity.
"""

from datetime import datetime
from loguru import logger
from .ollama_client import OllamaClient
from tracker.database import get_jobs, get_stats_summary


SYSTEM_PROMPT = """You are an AI assistant providing a concise daily job search update.
Write a friendly, motivating summary in plain text (no markdown) that covers:
- How many jobs were found and scored today
- The top 3 most relevant jobs (title, company, score)
- Key trends or observations
- An encouraging closing note
Keep it under 250 words. Professional yet warm tone."""


def generate_daily_summary(client: OllamaClient) -> str:
    stats = get_stats_summary()
    scored_jobs = get_jobs(status="scored", limit=50)
    applied_jobs = get_jobs(status="applied", limit=20)

    top_jobs_text = "\n".join([
        f"- {j['title']} at {j['company']} ({j['platform']}) — Score: {j['ai_score']:.0f}/100"
        for j in sorted(scored_jobs, key=lambda x: x["ai_score"], reverse=True)[:5]
    ]) or "No scored jobs yet."

    applied_text = "\n".join([
        f"- {j['title']} at {j['company']} ({j['platform']})"
        for j in applied_jobs[:5]
    ]) or "No applications submitted yet."

    prompt = f"""
Today's Date: {datetime.now().strftime('%A, %B %d %Y')}

OVERALL STATS:
- Total jobs found: {stats.get('found', 0)}
- Total jobs scored: {stats.get('scored', 0)}
- Total applications sent: {stats.get('applied', 0)}
- Interviews/responses: {stats.get('interview', 0)}

TOP MATCHING JOBS TODAY:
{top_jobs_text}

RECENTLY APPLIED TO:
{applied_text}

Write a daily job search summary for the candidate.
"""
    summary = client.generate(prompt, system=SYSTEM_PROMPT)
    if not summary:
        return _fallback_summary(stats, scored_jobs, applied_jobs)
    return summary


def _fallback_summary(stats: dict, scored: list, applied: list) -> str:
    lines = [
        f"📊 Daily Job Search Summary — {datetime.now().strftime('%B %d, %Y')}",
        "",
        f"• Jobs found      : {stats.get('found', 0)}",
        f"• Jobs scored     : {stats.get('scored', 0)}",
        f"• Applications    : {stats.get('applied', 0)}",
        f"• Interviews      : {stats.get('interview', 0)}",
        "",
    ]
    if scored:
        lines.append("Top matches:")
        for j in sorted(scored, key=lambda x: x["ai_score"], reverse=True)[:3]:
            lines.append(f"  ✅ {j['title']} @ {j['company']} — {j['ai_score']:.0f}/100")
    return "\n".join(lines)
