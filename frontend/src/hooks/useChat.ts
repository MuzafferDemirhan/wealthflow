"use client";

import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/api-client";
import type { ChatMessageRead, ChatResponse } from "@/lib/types";

interface UseChatReturn {
  messages: ChatMessageRead[];
  isLoading: boolean;
  error: string | null;
  conversationId: string | null;
  sendMessage: (message: string) => Promise<void>;
  loadHistory: (conversationId: string) => Promise<void>;
  clearHistory: () => Promise<void>;
  reset: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessageRead[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const convIdRef = useRef<string | null>(null);

  const sendMessage = useCallback(async (message: string) => {
    setIsLoading(true);
    setError(null);

    const optId = convIdRef.current ?? undefined;

    const tempUserMsg: ChatMessageRead = {
      id: crypto.randomUUID(),
      conversation_id: optId ?? "",
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const data: ChatResponse = await api.post<ChatResponse>("/chat/messages", {
        message,
        conversation_id: optId,
      });

      convIdRef.current = data.conversation_id;
      setConversationId(data.conversation_id);

      const assistantMsg: ChatMessageRead = {
        id: data.message_id,
        conversation_id: data.conversation_id,
        role: "assistant",
        content: data.reply,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to send message";
      setError(msg);
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async (convId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<ChatMessageRead[]>(`/chat/messages`, {
        conversation_id: convId,
        limit: 50,
      } as Record<string, string | number | undefined>);
      setMessages(data);
      convIdRef.current = convId;
      setConversationId(convId);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load history";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearHistory = useCallback(async () => {
    const cid = convIdRef.current;
    if (!cid) return;
    try {
      await api.del(`/chat/messages/${cid}`);
      setMessages([]);
      setConversationId(null);
      convIdRef.current = null;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to clear history";
      setError(msg);
    }
  }, []);

  const reset = useCallback(() => {
    setMessages([]);
    setError(null);
    setConversationId(null);
    convIdRef.current = null;
  }, []);

  return {
    messages,
    isLoading,
    error,
    conversationId,
    sendMessage,
    loadHistory,
    clearHistory,
    reset,
  };
}
