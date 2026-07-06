"use client";

import { createContext, useContext, useEffect, useState, useCallback, useRef, type ReactNode } from "react";
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

  // Refs always hold the latest token values so __registerTokenStore closures stay fresh
  const accessRef = useRef<string | null>(null);
  const refreshRef = useRef<string | null>(null);

  const handleTokenRefreshed = useCallback((access: string, refresh: string) => {
    saveTokens(access, refresh);
    accessRef.current = access;
    refreshRef.current = refresh;
  }, []);

  const handleLogout = useCallback(() => {
    clearTokens();
    accessRef.current = null;
    refreshRef.current = null;
    setUser(null);
  }, []);

  // Register token store with api-client once on mount
  useEffect(() => {
    const stored = loadTokens();
    accessRef.current = stored.access;
    refreshRef.current = stored.refresh;

    __registerTokenStore({
      getAccessToken: () => accessRef.current ?? loadTokens().access,
      getRefreshToken: () => refreshRef.current ?? loadTokens().refresh,
      onTokenRefreshed: handleTokenRefreshed,
      onLogout: handleLogout,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Validate session on mount if tokens exist
  useEffect(() => {
    const stored = loadTokens();
    if (!stored.access) {
      setIsLoading(false); // eslint-disable-line react-hooks/set-state-in-effect
      return;
    }

    api
      .get<UserRead>("/auth/me")
      .then((u) => {
        setUser(u);
        accessRef.current = stored.access;
        refreshRef.current = stored.refresh;
      })
      .catch(() => {
        clearTokens();
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.set("username", email);
    formData.set("password", password);

    let res: Response;
    try {
      res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: formData,
        },
      );
    } catch {
      throw new ApiError(0, "Cannot reach the server.)");
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new ApiError(res.status, err.detail ?? "Login failed");
    }

    const data: TokenPair = await res.json();
    saveTokens(data.access_token, data.refresh_token);
    accessRef.current = data.access_token;
    refreshRef.current = data.refresh_token;

    const me = await api.get<UserRead>("/auth/me");
    setUser(me);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    await api.post<UserRead>("/auth/register", { email, password, full_name: fullName });
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = refreshRef.current ?? loadTokens().refresh;
    if (refreshToken) {
      try {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      } catch {
        // ignore errors
      }
    }
    handleLogout();
  }, [handleLogout]);

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
