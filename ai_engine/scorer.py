"""
ai_engine/scorer.py
Scores job relevance against the candidate's resume and profile.
Uses Ollama/LLM when available, and an intelligent QA/SDET heuristic NLP engine when offline.
Candidate: Shibin K K | SDET & QA Automation Engineer | shibinkk17@gmail.com
"""

import json
import re
from loguru import logger

SYSTEM_PROMPT = """You are an expert job-fit analyser. 
Given a candidate's resume and a job description, you output a JSON object with:
- score (integer 0-100): how well the candidate fits this role
- summary (string): 2-3 sentence explanation of the score
- pros (list of strings): top 3 matching points
- cons (list of strings): top 2 gaps or concerns
Respond ONLY with valid JSON. No markdown, no extra text."""

# Candidate profile keywords for Shibin K K
CANDIDATE_SKILLS = {
    "selenium": 8, "playwright": 9, "python": 8, "api": 8, "postman": 7,
    "cypress": 7, "automation": 8, "qa": 6, "sdet": 9, "testng": 6,
    "pytest": 7, "ci/cd": 6, "jenkins": 6, "git": 5, "sql": 5,
    "manual": 5, "cucumber": 6, "bdd": 6, "rest": 7, "appium": 7,
    "jira": 5, "agile": 5, "regression": 6, "performance": 5
}

PREFERRED_LOCATIONS = {
    "kochi": 15, "cochin": 15, "kozhikode": 15, "calicut": 15,
    "trivandrum": 15, "thiruvananthapuram": 15, "kerala": 15,
    "bangalore": 14, "bengaluru": 14, "chennai": 14, "remote": 15,
    "hyderabad": 12, "pune": 11, "india": 10, "dubai": 12, "uae": 12
}


def score_job(client, resume_text: str, job: dict) -> dict:
    """Returns {'score': int, 'summary': str, 'pros': [], 'cons': []}"""
    # 1. If LLM client is available, try generating score with LLM
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

Analyse the fit and respond with JSON only.
"""
            raw = client.generate(prompt, system=SYSTEM_PROMPT)
            if raw:
                clean = re.sub(r"```(?:json)?|```", "", raw).strip()
                data = json.loads(clean)
                score = int(data.get("score", 0))
                if score > 0:
                    return {
                        "score": score,
                        "summary": data.get("summary", ""),
                        "pros": data.get("pros", []),
                        "cons": data.get("cons", []),
                    }
        except Exception as e:
            logger.warning("LLM scoring failed, falling back to intelligent scorer: {}", e)

    # 2. Intelligent QA / SDET Heuristic Scorer (Guarantees every job has an accurate score & summary)
    return _heuristic_score(job, resume_text)


def _heuristic_score(job: dict, resume_text: str = "") -> dict:
    """Accurately calculates a 0-100 score and summary based on candidate profile."""
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    loc = (job.get("location") or "").lower()
    combined = f"{title} {desc}"

    score = 40  # Base score for QA opportunities
    pros = []
    cons = []

    # Title alignment (up to 30 pts)
    if "sdet" in title:
        score += 30
        pros.append("Direct SDET title alignment with candidate specialization")
    elif "automation" in title and ("qa" in title or "test" in title or "engineer" in title):
        score += 28
        pros.append("Strong match for QA Automation Engineer role")
    elif "qa" in title or "quality" in title or "test" in title:
        score += 20
        pros.append("Matches core Quality Assurance / Testing domain")
    elif "software engineer" in title:
        score += 15
        pros.append("Relevant software engineering opportunity")

    # Skill matches (up to 25 pts)
    matched_skills = []
    skill_pts = 0
    for skill, weight in CANDIDATE_SKILLS.items():
        if skill in combined:
            matched_skills.append(skill.upper())
            skill_pts += weight
            if len(matched_skills) >= 4:
                break
    skill_pts = min(skill_pts, 25)
    score += skill_pts

    if matched_skills:
        pros.append(f"Matching technical skills: {', '.join(matched_skills[:4])}")

    # Location alignment (up to 15 pts)
    loc_matched = False
    for pref_loc, pts in PREFERRED_LOCATIONS.items():
        if pref_loc in loc:
            score += pts
            pros.append(f"Preferred location match ({job.get('location', '').strip()})")
            loc_matched = True
            break
    if not loc_matched:
        if "india" in loc:
            score += 10
        else:
            cons.append("Location outside primary preferences (may require remote or relocation)")

    # Experience level check
    if any(k in combined for k in ["0-2 years", "1-3 years", "2-4 years", "entry level", "fresher"]):
        score += 5
        pros.append("Experience requirement matches candidate career stage (1-3 yrs)")
    elif any(k in combined for k in ["7+ years", "8+ years", "10+ years", "lead"]):
        score -= 15
        cons.append("Higher seniority requirement than candidate's current 3+ years experience")

    # Clamp score to reasonable bounds
    final_score = max(25, min(96, score))

    # Generate insightful summary
    company = job.get("company", "the hiring company")
    top_skills_str = ", ".join(matched_skills[:3]) if matched_skills else "Automation Testing & QA frameworks"
    loc_str = job.get("location", "India / Remote")

    if final_score >= 80:
        summary = (
            f"Strong match ({final_score}%): High synergy with Shibin's SDET profile at {company}. "
            f"Key matching areas include {top_skills_str} in {loc_str}."
        )
    elif final_score >= 65:
        summary = (
            f"Good match ({final_score}%): Solid alignment with QA automation principles at {company}. "
            f"Relevant skills identified: {top_skills_str}."
        )
    else:
        summary = (
            f"Moderate match ({final_score}%): General QA opening at {company}. "
            f"Some technical overlap with {top_skills_str}."
        )

    if not cons:
        cons.append("Review detailed JD for specific proprietary framework requirements")

    return {
        "score": final_score,
        "summary": summary,
        "pros": pros[:3],
        "cons": cons[:2],
    }
