import os
from typing import Any, Dict, List, Optional

import requests


class OllamaHandler:
    """
    Local LLM provider backed by an Ollama server (default model: gemma:2b).

    Used as the primary generator for the RAG assistant so that grounded
    answers can be produced without any cloud API key.
    """

    def __init__(self):
        """
        Read configuration from environment variables:
            OLLAMA_BASE_URL  – Ollama server URL (default: http://localhost:11434)
            OLLAMA_LLM_MODEL – Chat model name  (default: gemma:2b)
            OLLAMA_TIMEOUT   – Request timeout in seconds (default: 120)
        """
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_LLM_MODEL", "gemma:2b")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", "120"))
        self.available = self._check_available()

    def _check_available(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            models = [model.get("name", "") for model in response.json().get("models", [])]
        except Exception as e:
            print(f"⚠ Ollama not reachable at {self.base_url}: {e}")
            print("  Start it with: ollama serve")
            return False

        base_name = self.model.split(":")[0]
        if any(name == self.model or name.startswith(f"{base_name}:") for name in models):
            print(f"✓ Ollama initialized – model: {self.model}")
            return True

        print(f"⚠ Ollama running but '{self.model}' not found. Available: {models}")
        print(f"  Run: ollama pull {self.model}")
        return False

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 500,
    ) -> str:
        """Send a chat completion request to Ollama and return the answer text."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        response.raise_for_status()
        message: Optional[Dict[str, Any]] = response.json().get("message")
        return (message or {}).get("content", "").strip()

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "active" if self.available else "unavailable",
            "base_url": self.base_url,
            "model": self.model,
        }

    def list_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return [model.get("name", "") for model in response.json().get("models", [])]
        except Exception:
            return []
