"use client";

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { api, __registerTokenStore, ApiError } from "@/lib/api-client";
import type { UserRead, TokenPair } from "@/lib/types";

// ──────────────────────────────────────────────
// Storage keys
// ──────────────────────────────────────────────

const ACCESS_KEY = "wf_access_token";
const REFRESH_KEY = "wf_refresh_token";

function loadTokens(): { access: string | null; refresh: string | null } {
  if (typeof window === "undefined") return { access: null, refresh: null };
  return {
    access: localStorage.getItem(ACCESS_KEY),
    refresh: localStorage.getItem(REFRESH_KEY),
  };
}

function saveTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// ──────────────────────────────────────────────
// Context
// ──────────────────────────────────────────────

interface AuthState {
  user: UserRead | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mutable refs for token storage (passed to api-client)
  const [tokens, setTokens] = useState<{ access: string | null; refresh: string | null }>({ access: null, refresh: null });

  const handleTokenRefreshed = useCallback((access: string, refresh: string) => {
    saveTokens(access, refresh);
    setTokens({ access, refresh });
  }, []);

  const handleLogout = useCallback(() => {
    clearTokens();
    setTokens({ access: null, refresh: null });
    setUser(null);
  }, []);

  // Register token store with api-client on mount
  useEffect(() => {
    const stored = loadTokens();
    setTokens(stored);

    __registerTokenStore({
      getAccessToken: () => tokens.access ?? loadTokens().access,
      getRefreshToken: () => tokens.refresh ?? loadTokens().refresh,
      onTokenRefreshed: handleTokenRefreshed,
      onLogout: handleLogout,
    });
    // only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Validate session on mount if tokens exist
  useEffect(() => {
    const stored = loadTokens();
    if (!stored.access) {
      setIsLoading(false);
      return;
    }

    api
      .get<UserRead>("/auth/me")
      .then((u) => {
        setUser(u);
        setTokens(stored);
      })
      .catch(() => {
        clearTokens();
      })
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.set("username", email);
    formData.set("password", password);

    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/login`,
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
      },
    );

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new ApiError(res.status, err.detail ?? "Login failed");
    }

    const data: TokenPair = await res.json();
    saveTokens(data.access_token, data.refresh_token);
    setTokens({ access: data.access_token, refresh: data.refresh_token });

    const me = await api.get<UserRead>("/auth/me");
    setUser(me);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    await api.post<UserRead>("/auth/register", { email, password, full_name: fullName });
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = tokens.refresh ?? loadTokens().refresh;
    if (refreshToken) {
      try {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      } catch {
        // ignore errors — clear local state regardless
      }
    }
    handleLogout();
  }, [tokens.refresh, handleLogout]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
