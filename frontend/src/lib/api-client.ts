const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ──────────────────────────────────────────────
// Token storage - set by AuthProvider on mount
// ──────────────────────────────────────────────

let _getAccessToken: () => string | null = () => null;
let _getRefreshToken: () => string | null = () => null;
let _onTokenRefreshed: (access: string, refresh: string) => void = () => {};
let _onLogout: () => void = () => {};

export function __registerTokenStore(opts: {
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  onTokenRefreshed: (access: string, refresh: string) => void;
  onLogout: () => void;
}) {
  _getAccessToken = opts.getAccessToken;
  _getRefreshToken = opts.getRefreshToken;
  _onTokenRefreshed = opts.onTokenRefreshed;
  _onLogout = opts.onLogout;
}

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = _getRefreshToken();
  if (!refreshToken) return false;

  const res = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!res.ok) return false;

  const data = await res.json();
  _onTokenRefreshed(data.access_token, data.refresh_token);
  return true;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  let url = `${BASE_URL}${path}`;

  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value));
      }
    }
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {};
  const token = _getAccessToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  if (body !== undefined && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (err) {
    throw new ApiError(0, `Unable to connect to the server. Make sure the backend is running at ${BASE_URL}. (${err instanceof Error ? err.message : "Network error"})`);
  }

  // 401 → try refresh once, then retry
  if (res.status === 401 && _getRefreshToken()) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${_getAccessToken()}`;
      try {
        const retryRes = await fetch(url, { method, headers, body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined });
        if (retryRes.ok) return retryRes.json();
        if (retryRes.status === 401) _onLogout();
        const retryErr = await parseError(retryRes);
        throw new ApiError(retryErr.status, retryErr.detail);
      } catch (e) {
        if (e instanceof ApiError) throw e;
        throw new ApiError(0, "Network error during retry");
      }
    } else {
      _onLogout();
    }
  }

  if (!res.ok) {
    const err = await parseError(res);
    throw new ApiError(err.status, err.detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

async function parseError(res: Response): Promise<{ status: number; detail: string }> {
  try {
    const json = await res.json();
    return { status: res.status, detail: json.detail ?? res.statusText };
  } catch {
    return { status: res.status, detail: res.statusText };
  }
}

// ──────────────────────────────────────────────
// Public API
// ──────────────────────────────────────────────

export const api = {
  get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
    return request<T>("GET", path, undefined, params);
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("POST", path, body);
  },

  put<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PUT", path, body);
  },

  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PATCH", path, body);
  },

  del<T = void>(path: string): Promise<T> {
    return request<T>("DELETE", path);
  },
};
