import { useEffect, useRef, useState } from "react";
import { Send, X, Sparkles, RotateCcw } from "lucide-react";
import { useChatbotStore } from "@/store/chatbot-store";
import { ChatMessage } from "./chat-message";
import { TypingIndicator } from "./typing-indicator";
import { SuggestionChips } from "./suggestion-chips";

interface Props {
  embedded?: boolean;
}

export function ChatWindow({ embedded = false }: Props) {
  const { open, setOpen, messages, pending, send, reset } = useChatbotStore();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  if (!embedded && !open) return null;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = input.trim();
    if (!v || pending) return;
    setInput("");
    send(v);
  }

  const wrapperClass = embedded
    ? "flex h-full flex-col rounded-md border border-border bg-surface overflow-hidden"
    : "fixed bottom-6 right-6 z-40 flex h-[560px] w-[380px] flex-col rounded-md border border-border bg-surface overflow-hidden";

  return (
    <div className={wrapperClass}>
      <header className="flex items-center justify-between border-b border-border bg-gradient-surface px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gradient-primary shadow-glow">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-foreground">RIMS Copilot</p>
            <p className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <span className="live-dot" /> Online
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={reset}
            className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            title="New chat"
          >
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
          {!embedded && (
            <button
              onClick={() => setOpen(false)}
              className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </header>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.map((m) => (
          <ChatMessage key={m.id} msg={m} />
        ))}
        {pending && <TypingIndicator />}
      </div>

      <div className="border-t border-border bg-surface p-3 space-y-2.5">
        <SuggestionChips />
        <form onSubmit={submit} className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about forecasts, risks, inventory…"
            className="flex-1 rounded-lg border border-border bg-surface-muted px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:bg-surface focus:outline-none"
          />
          <button
            type="submit"
            disabled={!input.trim() || pending}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-primary text-primary-foreground transition disabled:opacity-50 hover:shadow-glow"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
