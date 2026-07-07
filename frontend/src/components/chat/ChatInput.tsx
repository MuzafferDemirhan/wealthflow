"use client";

import { type FormEvent, useRef } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const val = inputRef.current?.value.trim();
    if (!val || disabled) return;
    onSend(val);
    if (inputRef.current) inputRef.current.value = "";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-3 border-t border-outline-variant bg-surface p-4"
    >
      <textarea
        ref={inputRef}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your finances..."
        rows={1}
        disabled={disabled}
        className="min-h-[44px] flex-1 resize-none rounded-xl border border-outline-variant bg-surface-container-low px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/50 outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled}
        className="flex h-[44px] w-[44px] shrink-0 items-center justify-center rounded-xl bg-primary text-on-primary transition-colors hover:bg-primary-hover disabled:opacity-50"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </button>
    </form>
  );
}
