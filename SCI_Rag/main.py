from __future__ import annotations

import argparse

from agent.agent import RAGAgent, render_markdown, result_to_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the SCI_Rag assistant over the CSV dataset.")
    parser.add_argument("question", nargs="?", help="Question to ask the RAG agent.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of retrieved rows to pass to the LLM.")
    parser.add_argument(
        "--no-pinecone",
        action="store_true",
        help="Force local retrieval instead of Pinecone.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the structured response as JSON.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    question = args.question or input("Ask a question about the dataset: ").strip()
    if not question:
        parser.error("A question is required.")

    agent = RAGAgent()
    result = agent.ask(question, top_k=args.top_k, prefer_pinecone=not args.no_pinecone)

    if args.json:
        print(result_to_json(result))
    else:
        print(render_markdown(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())