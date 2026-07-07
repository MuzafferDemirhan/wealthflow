"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api-client";
import type { NotificationRead } from "@/lib/types";

export function useNotifications() {
  const [notifications, setNotifications] = useState<NotificationRead[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const fetchNotifications = useCallback(async () => {
    try {
      const [list, unread] = await Promise.all([
        api.get<NotificationRead[]>("/notifications"),
        api.get<{ count: number }>("/notifications/unread-count"),
      ]);
      setNotifications(list);
      setUnreadCount(unread.count);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { fetchNotifications(); }, [fetchNotifications]);

  const markAsRead = useCallback(
    async (ids: string[]) => {
      try {
        await api.patch("/notifications/mark-read", { notification_ids: ids });
        setNotifications((prev) =>
          prev.map((n) => (ids.includes(n.id) ? { ...n, is_read: true } : n)),
        );
        setUnreadCount((prev) => Math.max(0, prev - ids.length));
      } catch {
        // silently fail
      }
    },
    [],
  );

  const addNotification = useCallback((n: NotificationRead) => {
    setNotifications((prev) => [n, ...prev]);
    if (!n.is_read) {
      setUnreadCount((prev) => prev + 1);
    }
  }, []);

  return {
    notifications,
    unreadCount,
    loading,
    fetchNotifications,
    markAsRead,
    addNotification,
  };
}
