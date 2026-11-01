"""
ai_engine/cover_letter.py
Generates a tailored cover letter for a specific job using Ollama or personalized templates.
Candidate: Shibin K K | SDET | shibinkk17@gmail.com | 9072765136
"""

from loguru import logger

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
    client, resume_text: str, job: dict, max_words: int = 300
) -> str:
    """Returns a tailored cover letter as plain text."""
    if client and hasattr(client, "is_available") and client.is_available():
        try:
            prompt = f"""
CANDIDATE RESUME:
{resume_text[:3000]}

---

JOB TITLE: {job.get('title', '')}
COMPANY: {job.get('company', '')}
LOCATION: {job.get('location', '')}
JOB DESCRIPTION:
{(job.get('description') or '')[:2000]}

---

Write a tailored cover letter (max {max_words} words) for this specific role and company.
"""
            letter = client.generate(prompt, system=SYSTEM_PROMPT)
            if letter:
                return letter.strip()
        except Exception as e:
            logger.warning("LLM cover letter generation error: {}", e)

    # High-quality personalized fallback cover letter for Shibin K K
    title = job.get("title", "SDET / QA Automation Engineer")
    company = job.get("company", "your team")
    loc = job.get("location", "your office")

    return (
        f"Dear Hiring Team at {company},\n\n"
        f"With over 3 years of hands-on experience in test automation frameworks, API testing, and continuous integration, "
        f"I am eager to contribute as a {title} on your team. Having closely followed {company}'s engineering journey, "
        f"I am confident that my technical background in Selenium, Playwright, Python, and robust CI/CD test pipelines "
        f"will help elevate your software quality and release velocity.\n\n"
        f"In my recent projects, I designed modular test automation suites reducing regression execution times by 40%, "
        f"built end-to-end API validations using Postman and Python, and collaborated closely with cross-functional "
        f"agile teams to catch critical defects early in the sprint lifecycle. I bring a proactive testing mindset, "
        f"ensuring both flawless user experiences and bulletproof backend reliability.\n\n"
        f"I would welcome the opportunity to discuss how my automation expertise can deliver immediate value to {company}. "
        f"Thank you for your time and consideration.\n\n"
        f"Sincerely,\n"
        f"Shibin K K\n"
        f"SDET / QA Automation Engineer\n"
        f"Phone: +91 9072765136 | Email: shibinkk17@gmail.com"
    )
