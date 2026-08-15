import type { ChatMessage } from "@/types/chatbot";
import { fetchJson } from "@/services/api";

// ---------------------------------------------------------------------------
// Backend response shape (matches FastAPI QueryResponse model)
// ---------------------------------------------------------------------------
interface QueryResponse {
  response: string;
  sources?: string[];
  confidence?: number;
  provider?: string;
  model?: string;
  grounded?: boolean;
  retrieved_count?: number;
}

// ---------------------------------------------------------------------------
// Public API — signature unchanged so the store needs zero changes
// ---------------------------------------------------------------------------
export async function askAssistant(prompt: string): Promise<ChatMessage> {
  try {
    const result = await fetchJson<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify({
        query: prompt,
        use_rag: true,
        top_k: 5,
      }),
    });

    const retrieved = result.retrieved_count ?? result.sources?.length ?? 0;
    const title = result.grounded
      ? `Grounded on ${retrieved} record${retrieved === 1 ? "" : "s"} · ${result.model ?? result.provider ?? "local model"}`
      : "Answered without retrieved records";

    return {
      id: crypto.randomUUID(),
      role: "assistant",
      createdAt: new Date().toISOString(),
      content: result.response,
      insight:
        result.confidence !== undefined
          ? {
              title,
              points: result.sources ?? [],
              confidence: Math.round(result.confidence * 100),
            }
          : undefined,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : "The backend request failed.";
    return {
      id: crypto.randomUUID(),
      role: "assistant",
      createdAt: new Date().toISOString(),
      content: `I couldn't reach the live backend for "${prompt}". ${message}`,
    };
  }
}
