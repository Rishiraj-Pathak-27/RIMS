from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

try:
    import ollama
except ImportError:  # pragma: no cover - optional dependency
    ollama = None

from retrieval.search import search


@dataclass(frozen=True)
class RagSettings:
    ollama_host: str
    llm_model: str
    top_k: int


def get_settings() -> RagSettings:
    load_dotenv()
    return RagSettings(
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        llm_model=os.getenv("OLLAMA_LLM_MODEL", os.getenv("OLLAMA_MODEL", "llama3.1")),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
    )


def build_context_block(matches: list[dict[str, Any]]) -> str:
    if not matches:
        return "No retrieval context was found."

    sections = []
    for index, match in enumerate(matches, start=1):
        sections.append(
            "\n".join(
                [
                    f"Record {index}",
                    f"ID: {match.get('id', 'unknown')}",
                    f"Score: {match.get('score', 0.0):.4f}",
                    match.get("text", ""),
                ]
            )
        )
    return "\n\n---\n\n".join(sections)


class RAGAgent:
    def __init__(self, settings: RagSettings | None = None) -> None:
        self.settings = settings or get_settings()

    def _client(self) -> ollama.Client:
        if ollama is None:
            raise RuntimeError("Install the ollama package before generating answers.")
        return ollama.Client(host=self.settings.ollama_host)

    def build_prompt(self, question: str, context: str) -> str:
        return (
            "You are a retrieval-augmented assistant for a structured order dataset. "
            "Answer strictly from the provided context. If the context does not contain enough information, "
            "say what is missing instead of guessing.\n\n"
            "Return the answer in this exact format:\n"
            "Answer:\n"
            "<direct response>\n\n"
            "Evidence:\n"
            "- <supporting fact>\n\n"
            "Notes:\n"
            "- <assumptions or caveats>\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context}"
        )

    def ask(self, question: str, top_k: int | None = None, prefer_pinecone: bool = True) -> dict[str, Any]:
        effective_top_k = top_k or self.settings.top_k
        matches = search(question, top_k=effective_top_k, prefer_pinecone=prefer_pinecone)
        context = build_context_block(matches)
        prompt = self.build_prompt(question, context)

        try:
            response = self._client().chat(
                model=self.settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You format RAG answers clearly and do not invent facts.",
                    },
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.2},
            )
            answer_text = response["message"]["content"].strip()
            generation_source = "ollama"
        except Exception as exc:
            if ollama is None:
                exc = "ollama package is not installed"
            answer_text = (
                "Answer:\n"
                "The Ollama generation step is not available right now.\n\n"
                "Evidence:\n"
                "- The retrieval layer still returned context from the dataset.\n\n"
                f"Notes:\n- Generation error: {exc}"
            )
            generation_source = "fallback"

        return {
            "question": question,
            "answer": answer_text,
            "sources": matches,
            "retrieval_context": context,
            "generation_source": generation_source,
        }


def render_markdown(result: dict[str, Any]) -> str:
    sources = result.get("sources", [])
    lines = [
        "# RAG Result",
        "",
        result.get("answer", ""),
        "",
        "## Retrieved Records",
    ]

    if not sources:
        lines.append("No records were retrieved.")
    else:
        for index, source in enumerate(sources, start=1):
            lines.append(
                f"{index}. {source.get('id', 'unknown')} | score={source.get('score', 0.0):.4f} | source={source.get('source', 'unknown')}"
            )

    return "\n".join(lines)


def result_to_json(result: dict[str, Any]) -> str:
    return json.dumps(result, indent=2, ensure_ascii=True, default=str)