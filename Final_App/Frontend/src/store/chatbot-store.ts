import { create } from "zustand";
import type { ChatMessage } from "@/types/chatbot";
import { askAssistant } from "@/services/chatbot";

interface ChatbotState {
  open: boolean;
  messages: ChatMessage[];
  pending: boolean;
  toggle: () => void;
  setOpen: (v: boolean) => void;
  send: (prompt: string) => Promise<void>;
  reset: () => void;
}

const greeting: ChatMessage = {
  id: "welcome",
  role: "assistant",
  createdAt: new Date().toISOString(),
  content:
    "Hi — I answer from retrieved operational records. Ask about forecasts, inventory, supplier risk, or shipments; include a SKU, site, or timeframe for the strongest result.",
};

export const useChatbotStore = create<ChatbotState>((set, get) => ({
  open: false,
  messages: [greeting],
  pending: false,
  toggle: () => set((s) => ({ open: !s.open })),
  setOpen: (v) => set({ open: v }),
  reset: () => set({ messages: [greeting] }),
  send: async (prompt) => {
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: prompt,
      createdAt: new Date().toISOString(),
    };
    set({ messages: [...get().messages, userMsg], pending: true });
    try {
      const reply = await askAssistant(prompt);
      set({ messages: [...get().messages, reply], pending: false });
    } catch {
      set({ pending: false });
    }
  },
}));
