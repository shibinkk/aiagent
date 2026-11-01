"""
ai_engine/cover_letter.py
Generates a tailored cover letter for a specific job using Ollama.
Candidate: Shibin K K | SDET | shibinkk17@gmail.com | 9072765136
"""

from loguru import logger
from .ollama_client import OllamaClient


SYSTEM_PROMPT = """You are an expert career coach who writes compelling, concise cover letters.
Write a professional cover letter that:
- Is 200-300 words max
- Opens with a strong hook (not "I am writing to apply for...")
- Highlights 2-3 specific relevant skills from the resume
- Shows genuine enthusiasm for the company
- Ends with a clear call to action
- Uses professional but warm tone
Output ONLY the cover letter text. No subject line, no date, no address blocks."""


def generate_cover_letter(
    client: OllamaClient, resume_text: str, job: dict, max_words: int = 300
) -> str:
    """Returns a tailored cover letter as plain text."""
    prompt = f"""
CANDIDATE RESUME:
{resume_text[:3000]}

---

JOB TITLE: {job.get('title', '')}
COMPANY: {job.get('company', '')}
JOB DESCRIPTION:
{(job.get('description') or '')[:2000]}

---

Write a tailored cover letter (max {max_words} words) for this specific role and company.
"""
    letter = client.generate(prompt, system=SYSTEM_PROMPT)
    if not letter:
        logger.warning("Cover letter generation failed for job: {}", job.get("title"))
        return ""
    return letter
