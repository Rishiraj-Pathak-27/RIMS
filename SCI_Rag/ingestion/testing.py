from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.upload_pinecone import build_and_upload


if __name__ == "__main__":
    result = build_and_upload()
    print("Chunks stored in Pinecone successfully!")
    print(result)