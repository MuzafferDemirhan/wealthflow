"use client";

import { useState, useRef, useEffect } from "react";
import { clsx } from "clsx";
import type { NotificationRead } from "@/lib/types";

interface NotificationBellProps {
  notifications: NotificationRead[];
  unreadCount: number;
  onMarkRead: (ids: string[]) => void;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function NotificationBell({ notifications, unreadCount, onMarkRead }: NotificationBellProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const handleMarkRead = (id: string) => {
    onMarkRead([id]);
  };

  const handleMarkAllRead = () => {
    const unreadIds = notifications.filter((n) => !n.is_read).map((n) => n.id);
    if (unreadIds.length > 0) {
      onMarkRead(unreadIds);
    }
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="relative rounded-lg p-2 text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface transition-colors"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute right-1.5 top-1.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-error px-1 text-[10px] font-bold text-on-error leading-none">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-outline-variant bg-surface shadow-lg">
          <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant">
            <span className="text-sm font-semibold text-on-surface">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs font-medium text-primary hover:text-primary/80 transition-colors"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center text-sm text-on-surface-variant">
                No notifications yet
              </div>
            ) : (
              notifications.slice(0, 20).map((n) => (
                <button
                  key={n.id}
                  onClick={() => handleMarkRead(n.id)}
                  className={clsx(
                    "w-full text-left px-4 py-3 transition-colors hover:bg-surface-container-low border-b border-outline-variant/50 last:border-b-0",
                    !n.is_read && "bg-primary/5",
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className={clsx("text-sm", n.is_read ? "text-on-surface" : "font-medium text-on-surface")}>
                      {n.title}
                    </span>
                    <span className="shrink-0 text-[11px] text-on-surface-variant">{formatDate(n.created_at)}</span>
                  </div>
                  {n.body && (
                    <p className="mt-0.5 text-xs text-on-surface-variant line-clamp-2">{n.body}</p>
                  )}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
