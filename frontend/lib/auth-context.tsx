"use client";

/**
 * Auth context — provides the authenticated user, loading state, login/logout
 * actions and automatic silent refresh to all descendant components.
 *
 * Access tokens live **only in memory** (set/cleared by `lib/api.ts`).
 * Refresh tokens are HTTP-only cookies managed by the backend through the
 * Next.js auth proxy.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  type AuthUser,
  clearAccessToken,
  login as apiLogin,
  logout as apiLogout,
  refreshToken,
} from "@/lib/api";

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  /** True after the initial silent-refresh attempt has resolved. */
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Schedule a silent token refresh slightly before the access token expires. */
  const scheduleRefresh = useCallback((expiresIn: number) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    // Refresh 60 s before expiry (minimum 10 s).
    const delay = Math.max((expiresIn - 60) * 1000, 10_000);
    refreshTimerRef.current = setTimeout(async () => {
      try {
        const data = await refreshToken();
        if (data) {
          setUser(data.user);
          scheduleRefresh(data.expires_in);
        } else {
          // Session gone.
          setUser(null);
          clearAccessToken();
        }
      } catch {
        setUser(null);
        clearAccessToken();
      }
    }, delay);
  }, []);

  /** Attempt silent refresh on mount (page load / SPA navigation). */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await refreshToken();
        if (!cancelled && data) {
          setUser(data.user);
          scheduleRefresh(data.expires_in);
        }
      } catch {
        /* not authenticated — that's fine */
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, [scheduleRefresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      setLoading(true);
      try {
        const data = await apiLogin(email, password);
        setUser(data.user);
        scheduleRefresh(data.expires_in);
      } finally {
        setLoading(false);
      }
    },
    [scheduleRefresh]
  );

  const logout = useCallback(async () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    await apiLogout();
    setUser(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, loading, ready, login, logout }),
    [user, loading, ready, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
