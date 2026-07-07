"use client";

import { clsx } from "clsx";
import type { ChatMessageRead } from "@/lib/types";

interface ChatMessageProps {
  message: ChatMessageRead;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={clsx(
        "flex",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={clsx(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-on-primary rounded-br-md"
            : "bg-surface-container-high text-on-surface rounded-bl-md"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}
