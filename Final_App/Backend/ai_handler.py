import os
import time
from typing import Tuple, List, Dict, Any, Optional

from google import genai
from google.genai import types

from ollama_handler import OllamaHandler

# OpenAI is optional — imported lazily only when a real key is present
_openai_available = False
try:
    from openai import OpenAI
    _openai_available = True
except ImportError:
    pass


class AIHandler:
    """
    Multi-model AI handler for RAG response generation.

    Primary:  Local Ollama model (default: gemma:2b) — grounded on Pinecone context
    Fallback: Google Gemini  (via google-genai SDK)
    Fallback: OpenAI GPT     (via openai SDK, optional)

    The provider order is configurable via LLM_PROVIDER_ORDER
    (default: "ollama,gemini,openai"). If no provider answers, a static
    fallback message is returned.
    """

    # Placeholder values that mean "not configured"
    _PLACEHOLDER_KEYS = {
        "", "your_openai_api_key_here", "your_gemini_api_key_here",
        "sk-...", "your_key_here",
    }

    def __init__(self):
        """
        Initialize the multi-model AI handler.

        Reads API keys and model names from environment variables:
            GEMINI_API_KEY   – Google AI Studio / Vertex API key
            OPENAI_API_KEY   – OpenAI platform API key (optional)
            GEMINI_MODEL     – Gemini model name  (default: gemini-2.5-flash)
            OPENAI_MODEL     – OpenAI model name  (default: gpt-4o-mini)
        """
        # ── Gemini setup ─────────────────────────────────────────────
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.gemini_available = False

        if self.gemini_api_key and self.gemini_api_key not in self._PLACEHOLDER_KEYS:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                self.gemini_available = True
                print(f"✓ Gemini initialized  – model: {self.gemini_model_name}")
            except Exception as e:
                print(f"⚠ Gemini init failed: {e}")
        else:
            print("⚠ GEMINI_API_KEY not set – Gemini will be skipped.")

        # ── OpenAI setup (optional) ──────────────────────────────────
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_ready = False

        if (
            _openai_available
            and self.openai_api_key
            and self.openai_api_key not in self._PLACEHOLDER_KEYS
        ):
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                self.openai_ready = True
                print(f"✓ OpenAI initialized  – model: {self.openai_model_name}")
            except Exception as e:
                print(f"⚠ OpenAI init failed: {e}")
        else:
            print("ℹ OpenAI not configured – skipping the OpenAI fallback.")

        # ── Local Ollama setup (primary) ─────────────────────────────
        self.ollama = OllamaHandler()
        self.ollama_ready = self.ollama.available

        self.provider_order = [
            name.strip().lower()
            for name in os.getenv("LLM_PROVIDER_ORDER", "ollama,gemini,openai").split(",")
            if name.strip()
        ]

        if not self.ollama_ready and not self.gemini_available and not self.openai_ready:
            print(
                "⚠ No LLM provider is available! "
                "Start Ollama and run `ollama pull gemma:2b`, "
                "or set GEMINI_API_KEY in .env (OPENAI_API_KEY is optional)"
            )

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def generate_response(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> Tuple[str, float]:
        """
        Generate an AI response for the given query.

        Tries Gemini first (with automatic retry on 429 rate-limit).
        Falls back to OpenAI if configured. Otherwise returns a static
        fallback message.

        Args:
            query:       The user's query
            context:     Optional RAG context documents
            temperature: Sampling temperature (0-1)
            max_tokens:  Maximum tokens in the response

        Returns:
            Tuple of (response_text, confidence_score)
        """
        result = self.generate(query, context, temperature, max_tokens)
        return result["response"], result["confidence"]

    def generate(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        """
        Generate an answer and report which provider produced it.

        Providers are tried in LLM_PROVIDER_ORDER (default: Ollama, then
        Gemini, then OpenAI). When retrieval context is supplied the prompt
        forces the model to answer strictly from that context.

        Returns:
            Dict with keys: response, confidence, provider, model, grounded
        """
        grounded = bool(context)
        system_prompt = self._build_system_prompt(grounded=grounded)
        user_prompt = self._build_user_prompt(query, context)
        confidence = self._calculate_confidence(context) if context else 0.7
        # Grounded answers should stay close to the retrieved records.
        effective_temperature = 0.2 if grounded else temperature

        for provider in self.provider_order:
            if provider == "ollama" and self.ollama_ready:
                try:
                    response_text = self.ollama.chat(
                        system_prompt, user_prompt, effective_temperature, max_tokens
                    )
                    if response_text:
                        return {
                            "response": response_text,
                            "confidence": confidence,
                            "provider": "ollama",
                            "model": self.ollama.model,
                            "grounded": grounded,
                        }
                except Exception as e:
                    print(f"⚠ Ollama call failed: {e}")

            elif provider == "gemini" and self.gemini_available:
                try:
                    response_text = self._call_gemini_with_retry(
                        system_prompt, user_prompt, effective_temperature, max_tokens
                    )
                    if response_text:
                        return {
                            "response": response_text,
                            "confidence": confidence,
                            "provider": "gemini",
                            "model": self.gemini_model_name,
                            "grounded": grounded,
                        }
                except Exception as e:
                    print(f"⚠ Gemini call failed: {e}")

            elif provider == "openai" and self.openai_ready:
                try:
                    response_text = self._call_openai(
                        system_prompt, user_prompt, effective_temperature, max_tokens
                    )
                    if response_text:
                        return {
                            "response": response_text,
                            "confidence": confidence,
                            "provider": "openai",
                            "model": self.openai_model_name,
                            "grounded": grounded,
                        }
                except Exception as e:
                    print(f"⚠ OpenAI call failed: {e}")

        return {
            "response": self._get_fallback_response(query, context),
            "confidence": confidence,
            "provider": "fallback",
            "model": None,
            "grounded": False,
        }

    def get_status(self) -> Dict[str, Any]:
        """Report which generation providers are currently usable."""
        return {
            "provider_order": self.provider_order,
            "ollama": self.ollama.get_status(),
            "gemini": {
                "status": "active" if self.gemini_available else "unavailable",
                "model": self.gemini_model_name,
            },
            "openai": {
                "status": "active" if self.openai_ready else "unavailable",
                "model": self.openai_model_name,
            },
        }

    # ──────────────────────────────────────────────────────────────────
    # Provider calls
    # ──────────────────────────────────────────────────────────────────

    def _call_gemini_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        max_retries: int = 3,
    ) -> str:
        """
        Call Gemini with automatic retry on 429 rate-limit errors.

        Free-tier quotas reset quickly (per-minute), so a short backoff
        is usually enough.
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                return self._call_gemini(
                    system_prompt, user_prompt, temperature, max_tokens
                )
            except Exception as e:
                last_error = e
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                    print(
                        f"⏳ Gemini rate-limited (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    raise  # Non-rate-limit error — don't retry

        raise last_error  # All retries exhausted

    def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Google Gemini and return the response text."""
        response = self.gemini_client.models.generate_content(
            model=self.gemini_model_name,
            contents=f"{system_prompt}\n\n{user_prompt}",
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text.strip()

    def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call OpenAI ChatCompletion and return the response text."""
        completion = self.openai_client.chat.completions.create(
            model=self.openai_model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return completion.choices[0].message.content.strip()

    # ──────────────────────────────────────────────────────────────────
    # Prompt builders
    # ──────────────────────────────────────────────────────────────────

    def _build_system_prompt(self, grounded: bool = False) -> str:
        """Return the system-level instruction for the LLM."""
        if grounded:
            return (
                "You are a supply-chain analytics assistant for a logistics platform called RIMS.\n\n"
                "GROUNDING RULES (strict):\n"
                "- Answer ONLY using facts present in the retrieved records below the question.\n"
                "- Never invent order IDs, numbers, dates, or trends that are not in the records.\n"
                "- Cite the record numbers you used, e.g. (Record 2).\n"
                "- If the records do not answer the question, say exactly what is missing "
                "instead of guessing.\n"
                "- Do not mention embeddings, vector databases, or how the records were retrieved.\n\n"
                "RESPONSE FORMAT:\n"
                "- A one-line direct answer, then 2-5 bullet points of supporting evidence.\n"
                "- Bold key metrics and values.\n"
                "- Keep it concise; no filler."
            )
        return (
            "You are an expert supply-chain analytics assistant for a logistics platform called RIMS. "
            "You help users understand forecasts, inventory health, supplier risks, shipments, and demand intelligence.\n\n"
            "RESPONSE GUIDELINES:\n"
            "- Always provide a structured, well-formatted answer using bullet points, numbered lists, or tables where appropriate.\n"
            "- Use bold text for key metrics, KPIs, and important values.\n"
            "- If the retrieved context contains relevant data, analyze it and present actionable insights.\n"
            "- If the context contains tabular/row data, summarize the patterns and trends you observe.\n"
            "- If the context is insufficient for the question, clearly state what data would be needed and provide general supply-chain best practices instead.\n"
            "- Keep responses concise but thorough — aim for 3-6 bullet points or a short paragraph with key highlights.\n"
            "- Never mention internal system details like 'Pinecone', 'embeddings', or 'vector database'.\n"
            "- Speak as a knowledgeable supply-chain analyst, not as an AI."
        )

    def _build_user_prompt(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Build the user-level prompt, optionally including RAG context."""
        if context:
            context_text = self._format_context(context)
            return (
                f"Retrieved Records:\n{context_text}\n\n"
                f"User Question: {query}\n\n"
                f"Answer the question using only the retrieved records above, citing the "
                f"record numbers you relied on. If they are insufficient, say what is missing."
            )
        return (
            f"User Question: {query}\n\n"
            f"Provide a clear, well-structured answer with actionable insights. "
            f"Use formatting (bold, bullet points) to make the response easy to scan."
        )

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    def _format_context(self, context: List[Dict[str, Any]]) -> str:
        """Format context documents for the prompt."""
        formatted = []
        for i, doc in enumerate(context, 1):
            content = doc.get("content", "")
            source = doc.get("source", "Unknown")
            # Clean up source names for readability
            if "." in source:
                # e.g. "main.default.gold_all_features_combined" → "gold_all_features_combined"
                source = source.rsplit(".", 1)[-1]
            source = source.replace("_", " ").title()
            formatted.append(
                f"[Record {i}] (Source: {source})\n{content}"
            )
        return "\n\n".join(formatted)

    def _calculate_confidence(self, context: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence based on context relevance.
        Normalizes scores to a 0-1 range (handles negative cosine/dot-product scores).

        Returns:
            Confidence score (0-1)
        """
        if not context:
            return 0.5
        similarities = [doc.get("similarity", 0) for doc in context]
        avg = sum(similarities) / len(similarities)
        # Normalize: scores can range from -1 to 1 for cosine; map to 0-1
        normalized = (avg + 1) / 2
        return max(0.0, min(normalized, 1.0))

    def _get_fallback_response(
        self,
        query: str,
        context: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Generate a fallback response when no LLM provider is available.
        """
        if context:
            sources = [doc.get("source", "unknown") for doc in context]
            return (
                f"### System Notice: LLM Provider Unavailable\n\n"
                f"Based on the provided context from ({', '.join(set(sources))}), "
                f"I found some internal records matching your question: **'{query}'**.\n\n"
                f"> **Configuration Required**\n"
                f"> The Supply Chain Copilot is running in **fallback mode** because no LLM provider is reachable.\n"
                f"> Start Ollama and run `ollama pull gemma:2b`, or configure `GEMINI_API_KEY` in your `.env` file."
            )
        return (
            f"### System Notice: LLM Provider Unavailable\n\n"
            f"You asked: **'{query}'**\n\n"
            f"> **Configuration Required**\n"
            f"> The Supply Chain Copilot is running in **fallback mode** because no LLM provider is reachable.\n"
            f"> Start Ollama and run `ollama pull gemma:2b`, or configure `GEMINI_API_KEY` in your `.env` file."
        )
