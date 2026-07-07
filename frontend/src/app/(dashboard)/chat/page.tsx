"use client";

import { useEffect, useRef } from "react";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { ChatInput } from "@/components/chat/ChatInput";
import { Spinner } from "@/components/ui/Spinner";
import { useChat } from "@/hooks/useChat";

const suggestedPrompts = [
  "How am I spending this month?",
  "Check my budgets",
  "Portfolio performance",
  "Net worth summary",
];

export default function ChatPage() {
  const {
    messages,
    isLoading,
    error,
    sendMessage,
    clearHistory,
    reset,
  } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <div className="flex items-center justify-between border-b border-outline-variant px-6 py-4">
        <div>
          <h1 className="text-xl font-medium text-on-surface">AI Advisor</h1>
          <p className="text-xs text-on-surface-variant">Ask anything about your finances</p>
        </div>
        {hasMessages && (
          <button
            onClick={() => {
              clearHistory();
              reset();
            }}
            className="rounded-lg px-3 py-1.5 text-xs text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors"
          >
            Clear chat
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {!hasMessages && !isLoading && (
          <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
              </svg>
            </div>
            <div>
              <p className="text-lg font-medium text-on-surface">How can I help you?</p>
              <p className="mt-1 text-sm text-on-surface-variant">
                Ask about your spending, budgets, portfolio, or net worth
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {suggestedPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => sendMessage(prompt)}
                  className="rounded-full border border-outline-variant px-4 py-2 text-sm text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {hasMessages && (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
          </div>
        )}

        {isLoading && (
          <div className="flex justify-center py-4">
            <Spinner size="sm" />
          </div>
        )}

        {error && (
          <div className="mx-auto mt-4 max-w-3xl rounded-xl bg-error/10 px-4 py-3 text-sm text-error">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="mx-auto w-full max-w-3xl">
        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}
