"use client";

import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth-context";
import { ToastProvider } from "@/components/ui/Toast";
import { useTheme } from "@/hooks/useTheme";

function ThemeInitializer() {
  useTheme();
  return null;
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <ToastProvider>
        <ThemeInitializer />
        {children}
      </ToastProvider>
    </AuthProvider>
  );
}
