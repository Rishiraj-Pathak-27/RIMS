"""Ollama-only answer generation for the RIMS RAG assistant."""

from typing import Any, Dict, List, Optional, Tuple

from ollama_handler import OllamaHandler


class AIHandler:
    """Generate grounded responses with the local ``gemma:2b`` Ollama model only."""

    def __init__(self) -> None:
        self.ollama = OllamaHandler()

    def generate_response(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 700,
    ) -> Tuple[str, float]:
        result = self.generate(query, context, temperature, max_tokens)
        return result["response"], result["confidence"]

    def generate(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 700,
    ) -> Dict[str, Any]:
        """Answer from retrieved context, or explicitly report that none is available."""
        grounded = bool(context)
        confidence = self._calculate_confidence(context or [])

        # Ollama may be started after the FastAPI process. Recheck before giving up
        # so gemma:2b remains the sole, usable fallback rather than a stale failure.
        if not self.ollama.available and not self.ollama.refresh_availability():
            return {
                "response": (
                    "I can't answer this right now because the local Ollama model "
                    f"`{self.ollama.model}` is unavailable. Start Ollama and run "
                    f"`ollama pull {self.ollama.model}`."
                ),
                "confidence": 0.0,
                "provider": "ollama",
                "model": self.ollama.model,
                "grounded": False,
            }

        try:
            response = self.ollama.chat(
                self._build_system_prompt(grounded),
                self._build_user_prompt(query, context or []),
                temperature=0.2,
                max_tokens=max_tokens,
            )
            if response:
                return {
                    "response": self._ensure_summary(response),
                    "confidence": confidence,
                    "provider": "ollama",
                    "model": self.ollama.model,
                    "grounded": grounded,
                }
        except Exception as error:
            print(f"[ai] Ollama generation failed: {error}")

        return {
            "response": "I couldn't generate an answer with the local Ollama model. Please try again.",
            "confidence": 0.0,
            "provider": "ollama",
            "model": self.ollama.model,
            "grounded": False,
        }

    def get_status(self) -> Dict[str, Any]:
        return {"provider": "ollama", "generation": self.ollama.get_status()}

    def _build_system_prompt(self, grounded: bool) -> str:
        if grounded:
            return (
                "You are RIMS, a supply-chain analytics assistant. Answer ONLY from the "
                "retrieved records supplied by the user. Do not use outside knowledge or "
                "invent forecasts, calculations, dates, quantities, or order IDs. "
                "If the records do not contain enough data to answer, state that clearly and "
                "name the missing data. Cite every factual claim with [Record N].\n\n"
                "Use this Markdown response structure exactly, in this order:\n"
                "## Detailed answer\n"
                "Give the full explanation first: 2-4 sentences, followed by useful evidence "
                "bullets with record values and citations. This is the only detailed section.\n\n"
                "### Summary\n"
                "- End with exactly 1-2 short takeaway bullets (maximum 25 words total).\n"
                "- Do not repeat the detailed evidence, list record fields, or add new facts here.\n\n"
                "Omit a section only when the records cannot support it. Never add facts, "
                "calculations, forecasts, or recommendations that are not supported by the records."
            )
        return (
            "You are RIMS, a supply-chain analytics assistant. No relevant internal records "
            "were retrieved for this question. Do not guess or provide a general answer. "
            "Briefly state that the knowledge base does not contain sufficient relevant data "
            "and say what records would be needed."
        )

    def _build_user_prompt(self, query: str, context: List[Dict[str, Any]]) -> str:
        if not context:
            return f"Question: {query}"
        return (
            f"Question: {query}\n\n"
            f"Retrieved records:\n{self._format_context(context)}\n\n"
            "Answer only from these records and cite record numbers."
        )

    @staticmethod
    def _format_context(context: List[Dict[str, Any]]) -> str:
        # Keep the prompt small enough for gemma:2b while preserving the best evidence.
        sections: List[str] = []
        remaining = 12_000
        for index, document in enumerate(context, 1):
            content = str(document.get("content", "")).strip()
            if not content or remaining <= 0:
                continue
            source = str(document.get("source", "Knowledge Base"))
            section = f"[Record {index} | Source: {source}]\n{content}"
            if len(section) > remaining:
                section = section[:remaining].rsplit(" ", 1)[0] + "…"
            sections.append(section)
            remaining -= len(section)
        return "\n\n---\n\n".join(sections)

    @staticmethod
    def _calculate_confidence(context: List[Dict[str, Any]]) -> float:
        if not context:
            return 0.0
        average = sum(float(document.get("similarity", 0.0)) for document in context) / len(context)
        return round(max(0.0, min(average, 1.0)), 2)

    @staticmethod
    def _ensure_summary(response: str) -> str:
        """Guarantee a compact final summary when gemma omits the requested heading."""
        if "summary" in response.lower():
            return response

        for line in response.splitlines():
            candidate = line.strip().lstrip("- ")
            if candidate and not candidate.startswith("#"):
                summary = " ".join(candidate.split()[:25])
                return f"{response.rstrip()}\n\n### Summary\n- {summary}"
        return f"{response.rstrip()}\n\n### Summary\n- No concise summary was generated."
