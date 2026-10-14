"""Grounded, operations-safe answer generation for the RIMS RAG assistant."""

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
                self._build_system_prompt(grounded, self._is_emergency_query(query)),
                self._build_user_prompt(query, context or []),
                temperature=0.2,
                max_tokens=max_tokens,
            )
            if response:
                return {
                    "response": self._ensure_response_format(response),
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

    def _build_system_prompt(self, grounded: bool, emergency: bool) -> str:
        if grounded:
            emergency_rules = (
                "\n\nThis is an emergency-sensitive operations question. Lead with the verified "
                "condition, scope, and impact from the records. Then give a numbered 'Immediate "
                "actions' list only when the records explicitly support those actions. If no "
                "escalation owner, threshold, or procedure is in the records, say that it is not "
                "specified; do not invent a runbook or claim the situation is safe."
                if emergency
                else ""
            )
            return (
                "You are RIMS, a supply-chain analytics assistant. Answer ONLY from the "
                "retrieved records supplied by the user. Do not use outside knowledge or "
                "invent forecasts, calculations, dates, quantities, or order IDs. "
                "If the records do not contain enough data to answer, state that clearly and "
                "name the missing data. Cite every factual claim with [Record N].\n\n"
                "Use this Markdown response structure exactly, in this order:\n"
                "## Detailed answer\n"
                "Give the full explanation first. Synthesize the relevant top records, explain "
                "the evidence and uncertainty, then include useful evidence bullets. Cite every "
                "factual claim with [Record N]. Do not treat a single chunk as a complete data set.\n\n"
                "### Summary\n"
                "- End with 2-4 short operational takeaway bullets.\n"
                "- Do not repeat detailed evidence or introduce facts not stated above.\n\n"
                "Omit a section only when the records cannot support it. Never add facts, "
                "calculations, forecasts, recommendations, owners, or deadlines that are not "
                "supported by the records."
                + emergency_rules
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
        # Reserve comparable space for each top-K chunk so one long match cannot
        # crowd out the rest of the retrieved evidence.
        sections: List[str] = []
        total_budget = 12_000
        per_record_budget = max(1_000, total_budget // max(1, len(context)))
        remaining = total_budget
        for index, document in enumerate(context, 1):
            content = str(document.get("content", "")).strip()
            if not content or remaining <= 0:
                continue
            source = str(document.get("source", "Knowledge Base"))
            allowed = min(per_record_budget, remaining)
            section = f"[Record {index} | Source: {source}]\n{content}"
            if len(section) > allowed:
                section = section[:allowed].rsplit(" ", 1)[0] + "…"
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
    def _is_emergency_query(query: str) -> bool:
        terms = {
            "emergency", "urgent", "critical", "severe", "incident", "outage",
            "stockout", "stock out", "blocked", "failure", "disruption", "delay",
        }
        normalized = query.lower()
        return any(term in normalized for term in terms)

    @staticmethod
    def _ensure_response_format(response: str) -> str:
        """Guarantee detailed-answer then concise-summary ordering for small local models."""
        formatted = response.strip()
        if not formatted.lower().startswith("## detailed answer"):
            formatted = f"## Detailed answer\n{formatted}"
        if "summary" in formatted.lower():
            return formatted

        for line in formatted.splitlines():
            candidate = line.strip().lstrip("- ")
            if candidate and not candidate.startswith("#"):
                summary = " ".join(candidate.split()[:25])
                return f"{formatted}\n\n### Summary\n- {summary}"
        return f"{formatted}\n\n### Summary\n- No concise summary was generated."
