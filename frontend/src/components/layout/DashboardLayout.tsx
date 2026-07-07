"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { AuthGuard } from "@/components/layout/AuthGuard";
import { Sidebar } from "@/components/layout/Sidebar";
import { NotificationBell } from "@/components/notifications/NotificationBell";
import { useAuth } from "@/lib/auth-context";
import { useNotifications } from "@/hooks/useNotifications";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useToast } from "@/components/ui/Toast";
import type { NotificationRead } from "@/lib/types";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const { isAuthenticated } = useAuth();
  const { toast } = useToast();
  const {
    notifications,
    unreadCount,
    markAsRead,
    addNotification,
    fetchNotifications,
  } = useNotifications();

  const lastTokenRef = useRef<string | null>(null);
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("wf_access_token")
      : null;

  useEffect(() => {
    if (isAuthenticated && token !== lastTokenRef.current) {
      lastTokenRef.current = token;
      fetchNotifications();
    }
  }, [isAuthenticated, token, fetchNotifications]);

  const handleWsMessage = useCallback(
    (data: Record<string, unknown>) => {
      if (data.type === "notification" && data.notification_type) {
        const n: NotificationRead = {
          id: (data.payload as Record<string, unknown>)?.export_id as string ?? crypto.randomUUID(),
          type: data.notification_type as string,
          title: data.title as string,
          body: data.body as string | undefined,
          payload: data.payload as Record<string, unknown> | undefined,
          is_read: false,
          created_at: new Date().toISOString(),
        };
        addNotification(n);
        toast(n.title, "info");
      }
    },
    [addNotification, toast],
  );

  useWebSocket(isAuthenticated ? token : null, handleWsMessage);

  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden bg-background text-on-surface">
        {/* Desktop sidebar */}
        <div className="hidden md:flex md:flex-shrink-0">
          <Sidebar isOpen={sidebarOpen} />
        </div>

        {/* Mobile sidebar overlay */}
        {mobileSidebarOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <div
              className="fixed inset-0 bg-surface/80 backdrop-blur-sm"
              onClick={() => setMobileSidebarOpen(false)}
            />
            <div className="fixed inset-y-0 left-0 z-50">
              <Sidebar isOpen={true} onNav={() => setMobileSidebarOpen(false)} />
            </div>
          </div>
        )}

        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Header */}
          <header className="flex h-16 shrink-0 items-center gap-3 border-b border-outline-variant bg-surface px-4">
            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="text-on-surface-variant hover:text-on-surface transition-colors md:hidden"
              aria-label="Open sidebar"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Desktop sidebar toggle */}
            <button
              onClick={() => setSidebarOpen((prev) => !prev)}
              className="hidden md:flex text-on-surface-variant hover:text-on-surface transition-colors"
              aria-label="Toggle sidebar"
            >
              {sidebarOpen ? (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                </svg>
              ) : (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                </svg>
              )}
            </button>

            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary md:hidden">
              <svg className="h-3.5 w-3.5 text-on-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <span className="text-base font-semibold text-on-surface md:hidden">WealthFlow</span>

            <div className="ml-auto flex items-center gap-1">
              <NotificationBell
                notifications={notifications}
                unreadCount={unreadCount}
                onMarkRead={markAsRead}
              />
            </div>
          </header>

          {/* Page content */}
          <main className="flex-1 overflow-y-auto bg-background p-6 sm:p-8 lg:p-10">
            <div className="mx-auto w-full max-w-7xl">
              {children}
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
