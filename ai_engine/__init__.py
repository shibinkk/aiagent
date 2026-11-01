"""
ai_engine/__init__.py
"""
from .ollama_client import OllamaClient
from .scorer import score_job
from .cover_letter import generate_cover_letter
from .summarizer import generate_daily_summary

__all__ = ["OllamaClient", "score_job", "generate_cover_letter", "generate_daily_summary"]
