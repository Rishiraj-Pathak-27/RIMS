from __future__ import annotations

import math
import os
import re
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

try:
    import ollama
except ImportError:  # pragma: no cover - optional dependency
    ollama = None

try:
    from pinecone import Pinecone
except ImportError:  # pragma: no cover - optional dependency
    Pinecone = None

from ingestion.create_chunks import create_chunks
from ingestion.load_data import load_data


@lru_cache(maxsize=32)
def _load_settings() -> dict[str, str | None]:
    load_dotenv()
    return {
        "pinecone_api_key": os.getenv("PINECONE_API_KEY"),
        "pinecone_index": os.getenv("PINECONE_INDEX_NAME") or os.getenv("PINECONE_INDEX"),
        "pinecone_namespace": os.getenv("PINECONE_NAMESPACE"),
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "embedding_model": os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
    }


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0

    numerator = sum(l_value * r_value for l_value, r_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    if left_norm == 0 or right_norm == 0:
        return 0.0

    return numerator / (left_norm * right_norm)


def _embed_text(text: str) -> list[float] | None:
    settings = _load_settings()

    if ollama is None:
        return None

    try:
        client = ollama.Client(host=settings["ollama_host"])
        response = client.embeddings(model=settings["embedding_model"], prompt=text)
        return response["embedding"]
    except Exception:
        return None


def _keyword_score(query: str, text: str) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    text_tokens = _tokenize(text)
    overlap = len(query_tokens & text_tokens)
    return overlap / len(query_tokens)


def _format_match(match: dict[str, Any], source: str) -> dict[str, Any]:
    metadata = match.get("metadata") or {}
    text = metadata.get("text") or match.get("text") or ""

    return {
        "id": match.get("id"),
        "score": float(match.get("score", 0.0)),
        "text": text,
        "metadata": metadata,
        "source": source,
    }


def search_pinecone(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    settings = _load_settings()
    if not settings["pinecone_api_key"] or not settings["pinecone_index"]:
        return []
    if Pinecone is None:
        return []

    query_embedding = _embed_text(query)
    if query_embedding is None:
        return []

    pc = Pinecone(api_key=settings["pinecone_api_key"])
    index = pc.Index(settings["pinecone_index"])
    response = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=settings["pinecone_namespace"],
    )

    matches = response.get("matches", []) if isinstance(response, dict) else getattr(response, "matches", [])
    return [_format_match(match, source="pinecone") for match in matches]


def search_local(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    dataframe = load_data()
    chunks = create_chunks(dataframe)

    query_embedding = _embed_text(query)
    scored_chunks: list[dict[str, Any]] = []

    for chunk in chunks:
        if query_embedding is not None:
            chunk_embedding = _embed_text(chunk["text"])
            score = _cosine_similarity(query_embedding, chunk_embedding or [])
        else:
            score = _keyword_score(query, chunk["text"])

        scored_chunks.append(
            {
                "id": chunk["id"],
                "score": score,
                "text": chunk["text"],
                "metadata": chunk.get("metadata", {}),
                "source": "local",
            }
        )

    scored_chunks.sort(key=lambda item: item["score"], reverse=True)
    return scored_chunks[:top_k]


def search(query: str, top_k: int = 5, prefer_pinecone: bool = True) -> list[dict[str, Any]]:
    if prefer_pinecone:
        pinecone_matches = search_pinecone(query, top_k=top_k)
        if pinecone_matches:
            return pinecone_matches

    return search_local(query, top_k=top_k)