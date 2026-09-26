"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/lib/customer-auth-context";
import { customerPortalApi, CustomerProfileResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function PortalDashboardPage({ params }: { params: Promise<{ shopId: string }> }) {
  const { customer, ready } = useCustomerAuth();
  const router = useRouter();
  const resolvedParams = use(params);
  const [profile, setProfile] = useState<CustomerProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    applications: 0,
    documents: 0,
    payments: 0,
    pendingBalance: "0.00",
  });

  useEffect(() => {
    if (ready && !customer) {
      router.push(`/portal/login`);
    }
  }, [ready, customer, router]);

  useEffect(() => {
    if (customer && resolvedParams) {
      loadDashboardData();
    }
  }, [customer, resolvedParams]);

  async function loadDashboardData() {
    try {
      setLoading(true);
      const [profileData, applications, documents, payments] = await Promise.all([
        customerPortalApi.getProfile(customer!.shop_id),
        customerPortalApi.listApplications(customer!.shop_id, { page_size: 1 }),
        customerPortalApi.listDocuments(customer!.shop_id, { page_size: 1 }),
        customerPortalApi.listPayments(customer!.shop_id, { page_size: 1 }),
      ]);
      setProfile(profileData);
      setStats({
        applications: applications.total,
        documents: documents.total,
        payments: payments.total,
        pendingBalance: "0.00", // TODO: Calculate from billing
      });
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
    } finally {
      setLoading(false);
    }
  }

  if (!ready || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-4xl space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Customer Portal</h1>
            <p className="mt-1 text-sm text-muted-foreground">Loading dashboard…</p>
          </div>
        </div>
      </div>
    );
  }

  if (!customer) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Dashboard</h1>
            <p className="text-muted-foreground">Welcome back, {profile?.name || customer.email}</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">Shop ID: {resolvedParams.shopId}</span>
            <Badge variant="secondary" className="capitalize">{customer.status}</Badge>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Applications</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.applications}</div>
              <p className="text-xs text-muted-foreground">Total applications</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Documents</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.documents}</div>
              <p className="text-xs text-muted-foreground">Total documents</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Payments</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.payments}</div>
              <p className="text-xs text-muted-foreground">Total payments made</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Balance</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">₹{stats.pendingBalance}</div>
              <p className="text-xs text-muted-foreground">Outstanding amount</p>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Link href={`/portal/${resolvedParams.shopId}/applications`}>
            <Card className="hover:bg-accent cursor-pointer transition-colors">
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                    <svg className="h-6 w-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 002-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium">My Applications</h3>
                    <p className="text-sm text-muted-foreground">View and track your applications</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href={`/portal/${resolvedParams.shopId}/documents`}>
            <Card className="hover:bg-accent cursor-pointer transition-colors">
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                    <svg className="h-6 w-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium">My Documents</h3>
                    <p className="text-sm text-muted-foreground">Manage your documents</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href={`/portal/${resolvedParams.shopId}/payments`}>
            <Card className="hover:bg-accent cursor-pointer transition-colors">
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                    <svg className="h-6 w-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium">My Payments</h3>
                    <p className="text-sm text-muted-foreground">View payment history</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href={`/portal/${resolvedParams.shopId}/profile`}>
            <Card className="hover:bg-accent cursor-pointer transition-colors">
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                    <svg className="h-6 w-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-medium">My Profile</h3>
                    <p className="text-sm text-muted-foreground">View and edit your profile</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Applications</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Click "My Applications" to view and manage your applications.
              </p>
              <Link href={`/portal/${resolvedParams.shopId}/applications`}>
                <Button variant="outline">View All Applications</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}