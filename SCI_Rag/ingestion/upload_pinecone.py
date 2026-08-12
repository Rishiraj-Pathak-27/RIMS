from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

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


@dataclass(frozen=True)
class PineconeSettings:
    api_key: str | None
    index_name: str | None
    namespace: str | None
    ollama_host: str
    embedding_model: str


def get_settings() -> PineconeSettings:
    load_dotenv()
    return PineconeSettings(
        api_key=os.getenv("PINECONE_API_KEY"),
        index_name=os.getenv("PINECONE_INDEX_NAME") or os.getenv("PINECONE_INDEX"),
        namespace=os.getenv("PINECONE_NAMESPACE"),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        embedding_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
    )


def embed_text(text: str, settings: PineconeSettings | None = None) -> list[float]:
    active_settings = settings or get_settings()
    if ollama is None:
        raise RuntimeError("Install the ollama package before uploading vectors.")

    client = ollama.Client(host=active_settings.ollama_host)
    response = client.embeddings(model=active_settings.embedding_model, prompt=text)
    return response["embedding"]


def upsert_chunks_to_pinecone(
    chunks: Iterable[dict],
    settings: PineconeSettings | None = None,
) -> dict[str, int | str | None]:
    active_settings = settings or get_settings()

    if not active_settings.api_key:
        raise ValueError("Missing PINECONE_API_KEY in your environment.")
    if not active_settings.index_name:
        raise ValueError("Missing PINECONE_INDEX_NAME or PINECONE_INDEX in your environment.")
    if Pinecone is None:
        raise RuntimeError("Install the pinecone package before uploading vectors.")

    pc = Pinecone(api_key=active_settings.api_key)
    index = pc.Index(active_settings.index_name)

    vector_batch = []
    for chunk in chunks:
        vector_batch.append(
            {
                "id": chunk["id"],
                "values": embed_text(chunk["text"], active_settings),
                "metadata": {
                    **chunk.get("metadata", {}),
                    "text": chunk["text"],
                },
            }
        )

    if vector_batch:
        index.upsert(vectors=vector_batch, namespace=active_settings.namespace)

    return {
        "upserted_count": len(vector_batch),
        "index_name": active_settings.index_name,
        "namespace": active_settings.namespace,
    }


def build_and_upload() -> dict[str, int | str | None]:
    dataframe = load_data()
    chunks = create_chunks(dataframe)
    return upsert_chunks_to_pinecone(chunks)


if __name__ == "__main__":
    print(build_and_upload())