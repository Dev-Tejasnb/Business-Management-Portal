"use client";

/**
 * Customer Portal Auth context — provides the authenticated customer, loading state,
 * login/logout actions and automatic silent refresh to all descendant components.
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
  type CustomerAuthUser,
  clearCustomerAccessToken,
  customerLogin as apiCustomerLogin,
  customerLogout as apiCustomerLogout,
  customerRefreshToken,
} from "@/lib/api";

interface CustomerAuthState {
  customer: CustomerAuthUser | null;
  loading: boolean;
  /** True after the initial silent-refresh attempt has resolved. */
  ready: boolean;
  login: (email: string, password: string, shopId: string) => Promise<void>;
  logout: () => Promise<void>;
}

const CustomerAuthContext = createContext<CustomerAuthState | undefined>(undefined);

export function CustomerAuthProvider({ children, shopId }: { children: ReactNode; shopId: string }) {
  const [customer, setCustomer] = useState<CustomerAuthUser | null>(null);
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
        const data = await customerRefreshToken(shopId);
        if (data) {
          setCustomer(data.customer);
          scheduleRefresh(data.expires_in);
        } else {
          // Session gone.
          setCustomer(null);
          clearCustomerAccessToken();
        }
      } catch {
        setCustomer(null);
        clearCustomerAccessToken();
      }
    }, delay);
  }, [shopId]);

  /** Attempt silent refresh on mount (page load / SPA navigation). */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await customerRefreshToken(shopId);
        if (!cancelled && data) {
          setCustomer(data.customer);
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
  }, [scheduleRefresh, shopId]);

  const login = useCallback(
    async (email: string, password: string, shopIdParam: string) => {
      setLoading(true);
      try {
        const data = await apiCustomerLogin(email, password, shopIdParam);
        setCustomer(data.customer);
        scheduleRefresh(data.expires_in);
      } finally {
        setLoading(false);
      }
    },
    [scheduleRefresh]
  );

  const logout = useCallback(async () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    await apiCustomerLogout();
    setCustomer(null);
  }, []);

  const value = useMemo<CustomerAuthState>(
    () => ({ customer, loading, ready, login, logout }),
    [customer, loading, ready, login, logout]
  );

  return <CustomerAuthContext.Provider value={value}>{children}</CustomerAuthContext.Provider>;
}

export function useCustomerAuth(): CustomerAuthState {
  const ctx = useContext(CustomerAuthContext);
  if (!ctx) throw new Error("useCustomerAuth must be used within <CustomerAuthProvider>");
  return ctx;
}