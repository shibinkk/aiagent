"""
ai_engine/scorer.py
Scores job relevance against the candidate's resume using Ollama.
"""

import json
import re
from loguru import logger
from .ollama_client import OllamaClient


SYSTEM_PROMPT = """You are an expert job-fit analyser. 
Given a candidate's resume and a job description, you output a JSON object with:
- score (integer 0-100): how well the candidate fits this role
- summary (string): 2-3 sentence explanation of the score
- pros (list of strings): top 3 matching points
- cons (list of strings): top 2 gaps or concerns
Respond ONLY with valid JSON. No markdown, no extra text."""


def score_job(client: OllamaClient, resume_text: str, job: dict) -> dict:
    """Returns {'score': int, 'summary': str, 'pros': [], 'cons': []}"""
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
    if not raw:
        return {"score": 0, "summary": "AI unavailable", "pros": [], "cons": []}

    try:
        # Strip potential markdown fences
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        data = json.loads(clean)
        return {
            "score": int(data.get("score", 0)),
            "summary": data.get("summary", ""),
            "pros": data.get("pros", []),
            "cons": data.get("cons", []),
        }
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Could not parse AI score JSON: {} | raw={}", e, raw[:200])
        # Try to extract score with regex as fallback
        m = re.search(r'"score"\s*:\s*(\d+)', raw)
        score = int(m.group(1)) if m else 0
        return {"score": score, "summary": raw[:300], "pros": [], "cons": []}
