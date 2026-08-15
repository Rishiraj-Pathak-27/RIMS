import { cn } from "@/lib/utils";
import type { ChatMessage as Msg } from "@/types/chatbot";
import { AIResponseCard } from "./ai-response-card";
import { MarkdownContent } from "./markdown-content";
import { Sparkles, User } from "lucide-react";

export function ChatMessage({ msg }: { msg: Msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-foreground text-background" : "bg-gradient-primary text-primary-foreground",
        )}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
      </div>
      <div className={cn("max-w-[85%] space-y-2", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-md px-3.5 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-primary text-primary-foreground rounded-tr-sm"
              : "bg-surface-muted text-foreground rounded-tl-sm",
          )}
        >
          {isUser ? msg.content : <MarkdownContent content={msg.content} />}
        </div>
        {msg.insight && <AIResponseCard insight={msg.insight} />}
      </div>
    </div>
  );
}
