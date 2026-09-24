"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

// Force dynamic rendering for home page (uses AuthProvider context)
export const dynamic = "force-dynamic";

interface HealthDependency {
  name: string;
  ok: boolean;
  detail: string | null;
}

interface HealthResponse {
  status: string;
  version: string;
  dependencies?: HealthDependency[];
}

export default function HomePage() {
  const { user, ready } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const checkHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/health", { cache: "no-store" });
      const body = (await res.json()) as HealthResponse;
      if (!res.ok) {
        throw new Error(body.status || "Backend health check failed");
      }
      setHealth(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the backend");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (mounted) {
      void checkHealth();
    }
  }, [checkHealth, mounted]);

  if (!mounted) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
        <div className="max-w-xl text-center">
          <h1 className="text-4xl font-bold tracking-tight">
            Business Management Portal
          </h1>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <div className="max-w-xl text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          Business Management Portal
        </h1>
        <p className="mt-3 text-muted-foreground">
          An all-in-one platform for service-based businesses: CSC centers,
          GramaOne centers, xerox/printing shops, cyber cafes and digital
          service centers.
        </p>
        <p className="mt-2 text-xs uppercase tracking-widest text-muted-foreground/70">
          Phase 2 · Auth & Tenancy
        </p>

        <div className="mt-4 flex justify-center gap-3">
          {user ? (
            <Button asChild>
              <Link href="/dashboard">Go to Dashboard</Link>
            </Button>
          ) : (
            <Button asChild>
              <Link href="/login">Sign In</Link>
            </Button>
          )}
        </div>
      </div>

      <div className="w-full max-w-md rounded-lg border bg-card p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Backend Connectivity</h2>

        {loading && <p className="text-sm text-muted-foreground">Checking…</p>}

        {error && (
          <p className="text-sm font-medium text-destructive">{error}</p>
        )}

        {health && (
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "h-2.5 w-2.5 rounded-full",
                  health.status === "ok" ? "bg-green-500" : "bg-amber-500"
                )}
              />
              <span className="font-medium capitalize">{health.status}</span>
              <span className="ml-auto text-muted-foreground">
                v{health.version}
              </span>
            </div>
            {health.dependencies?.map((dep) => (
              <div
                key={dep.name}
                className="flex items-center justify-between border-t pt-2"
              >
                <span className="capitalize">{dep.name}</span>
                <span
                  className={cn(
                    "font-medium",
                    dep.ok ? "text-green-600" : "text-red-600"
                  )}
                >
                  {dep.ok ? "ok" : "unreachable"}
                </span>
              </div>
            ))}
          </div>
        )}

        <Button
          className="mt-4 w-full"
          onClick={() => void checkHealth()}
          disabled={loading}
        >
          {loading ? "Checking…" : "Check health"}
        </Button>
      </div>
    </main>
  );
}