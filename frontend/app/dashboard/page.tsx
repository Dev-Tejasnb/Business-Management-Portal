"use client";

import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/components/protected-route";
import Link from "next/link";
import { Building2, Users, Shield, Settings, LogOut } from "lucide-react";

function DashboardContent() {
  const { user, logout } = useAuth();
  const isPlatformUser = user?.platform_role && ["platform_owner", "platform_admin", "platform_manager", "platform_financial_manager", "platform_support"].includes(user.platform_role);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <div className="max-w-4xl w-full text-center">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="mt-2 text-muted-foreground">
          Welcome, {user?.full_name ?? user?.email}
        </p>
        <p className="mt-1 text-xs text-muted-foreground/70">
          Phase 3 · Shop Management & Staff Management
        </p>
      </div>

      <div className="w-full max-w-4xl space-y-6">
        {/* Account Info */}
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Your Account
          </h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Email</dt>
              <dd className="font-medium">{user?.email}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Name</dt>
              <dd className="font-medium">{user?.full_name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Platform Role</dt>
              <dd className="font-medium">
                {user?.platform_role ?? "Shop User"}
              </dd>
            </div>
          </dl>

          <Button
            variant="outline"
            className="mt-6 w-full"
            onClick={() => void logout()}
          >
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </Button>
        </div>

        {/* Platform Management (for platform users) */}
        {isPlatformUser && (
          <div className="rounded-lg border bg-card p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Platform Management
            </h2>
            <div className="grid gap-4 md:grid-cols-2">
              <Link
                href="/platform/shops"
                className="flex items-center gap-3 p-4 rounded-lg border hover:bg-accent transition-colors"
              >
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                  <Building2 className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-medium">Platform Shops</h3>
                  <p className="text-sm text-muted-foreground">Create, manage, and configure shops</p>
                </div>
              </Link>
            </div>
          </div>
        )}

        {/* Shop Operations */}
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold flex items-center gap-2">
            <Users className="h-5 w-5" />
            Shop Operations
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            <Link
              href="/dashboard/staff"
              className="flex items-center gap-3 p-4 rounded-lg border hover:bg-accent transition-colors"
            >
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
                <Users className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-medium">Staff Management</h3>
                <p className="text-sm text-muted-foreground">Manage shop staff members and roles</p>
              </div>
            </Link>
          </div>
        </div>

        {/* Coming Soon */}
        <div className="rounded-lg border bg-card p-6 shadow-sm opacity-60">
          <h2 className="mb-4 text-lg font-semibold flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Coming Soon
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-center gap-3 p-4 rounded-lg border">
              <div className="p-2 rounded-lg bg-muted text-muted-foreground">
                <Users className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-medium">Customers</h3>
                <p className="text-sm text-muted-foreground">Customer management</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 rounded-lg border">
              <div className="p-2 rounded-lg bg-muted text-muted-foreground">
                <Settings className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-medium">Services</h3>
                <p className="text-sm text-muted-foreground">Service catalog</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 rounded-lg border">
              <div className="p-2 rounded-lg bg-muted text-muted-foreground">
                <Settings className="h-6 w-6" />
              </div>
              <div>
                <h3 className="font-medium">Billing</h3>
                <p className="text-sm text-muted-foreground">Billing & payments</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
