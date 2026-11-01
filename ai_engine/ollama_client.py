"""
ai_engine/ollama_client.py
Wrapper around Ollama's local REST API.
"""

import httpx
import json
from loguru import logger


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _chat(self, prompt: str, system: str = "", temperature: float = 0.3) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "options": {"temperature": temperature},
                    "stream": False,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            return response.json()["message"]["content"].strip()
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama. Is it running? Run: ollama serve")
            return ""
        except Exception as e:
            logger.error("Ollama error: {}", e)
            return ""

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, system: str = "") -> str:
        return self._chat(prompt, system)
