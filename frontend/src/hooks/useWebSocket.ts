"use client";

import { useEffect, useRef } from "react";

type MessageHandler = (data: Record<string, unknown>) => void;

const BASE_WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ??
  process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, "ws") ??
  "ws://localhost:8000/api/v1";

export function useWebSocket(
  token: string | null,
  onMessage: MessageHandler,
) {
  const onMessageRef = useRef<MessageHandler>(onMessage);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    onMessageRef.current = onMessage;
  });

  useEffect(() => {
    if (!token) return;

    let ws: WebSocket | null = null;
    let isUnmounted = false;

    function connect() {
      if (isUnmounted) return;

      const url = `${BASE_WS_URL}/ws?token=${encodeURIComponent(token!)}`;

      try {
        ws = new WebSocket(url);
      } catch {
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
        return;
      }

      ws.onopen = () => {
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current(data);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!isUnmounted) {
          reconnectTimeoutRef.current = setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        ws?.close();
      };
    }

    connect();

    return () => {
      isUnmounted = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      ws?.close();
    };
  }, [token]);
}
