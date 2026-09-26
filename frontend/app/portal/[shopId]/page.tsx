"use client";

import { use } from "react";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useCustomerAuth } from "@/lib/customer-auth-context";

export default function PortalDashboardPage({ params }: { params: Promise<{ shopId: string }> }) {
  const { customer, ready } = useCustomerAuth();
  const router = useRouter();
  const resolvedParams = use(params);

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Customer Portal</h1>
          <p className="mt-1 text-sm text-muted-foreground">Loading…</p>
        </div>
      </div>
    </main>
  );
}