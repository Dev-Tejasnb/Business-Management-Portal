"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { use } from "react";
import { useCustomerAuth } from "@/lib/customer-auth-context";
import { customerPortalApi, CustomerApplicationResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  applied: "default",
  in_progress: "warning",
  under_review: "warning",
  approved: "success",
  rejected: "destructive",
  completed: "success",
  cancelled: "secondary",
};

export default function PortalApplicationDetailPage({ params }: { params: Promise<{ shopId: string; id: string }> }) {
  const { customer, ready } = useCustomerAuth();
  const router = useRouter();
  const resolvedParams = use(params);
  const [application, setApplication] = useState<CustomerApplicationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ready && !customer) {
      router.push(`/portal/login`);
    }
  }, [ready, customer, router]);

  useEffect(() => {
    if (customer && resolvedParams) {
      loadApplication(resolvedParams);
    }
  }, [customer, resolvedParams]);

  async function loadApplication(resolvedParams: { shopId: string; id: string }) {
    try {
      setLoading(true);
      const data = await customerPortalApi.getApplication(customer!.shop_id, parseInt(resolvedParams.id));
      setApplication(data);
    } catch (err) {
      setError("Failed to load application");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  if (!ready || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-4xl space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Application Details</h1>
            <p className="mt-1 text-sm text-muted-foreground">Loading…</p>
          </div>
        </div>
      </div>
    );
  }

  if (!customer || !application) {
    if (error) {
      return (
        <div className="min-h-screen bg-background p-6">
          <div className="max-w-6xl mx-auto">
            <Card>
              <CardContent className="pt-6 text-center">
                <h2 className="text-xl font-semibold text-destructive">Application Not Found</h2>
                <p className="text-muted-foreground mt-2">{error}</p>
                <Link href={`/portal/${resolvedParams.shopId}/applications`}>
                  <Button variant="outline" className="mt-4">Back to Applications</Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      );
    }
    return null;
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Link href={`/portal/${resolvedParams.shopId}/applications`}>
              <Button variant="ghost" size="sm">← Back to Applications</Button>
            </Link>
            <h1 className="text-3xl font-bold mt-2">Application {application.application_number}</h1>
          </div>
          <Badge variant={statusColors[application.status] || "default"}>
            {application.status.replace("_", " ")}
          </Badge>
        </div>

        {/* Application Details */}
        <Card>
          <CardHeader>
            <CardTitle>Application Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-muted-foreground">Application Number</label>
                <p className="font-mono">{application.application_number}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Service</label>
                <p>{application.service_name || application.service_slug || "Unknown"}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Status</label>
                <Badge variant={statusColors[application.status] || "default"}>
                  {application.status.replace("_", " ")}
                </Badge>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Submitted On</label>
                <p>{new Date(application.created_at).toLocaleDateString()}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Last Updated</label>
                <p>{new Date(application.updated_at).toLocaleDateString()}</p>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-muted-foreground">Form Data</label>
              <pre className="mt-2 p-4 bg-muted rounded-lg text-sm overflow-x-auto">
                {JSON.stringify(application.form_data, null, 2)}
              </pre>
            </div>
          </CardContent>
        </Card>

        {/* Related Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Related Actions</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-4 flex-wrap">
            <Link href={`/portal/${resolvedParams.shopId}/documents`}>
              <Button variant="outline">View Documents</Button>
            </Link>
            <Link href={`/portal/${resolvedParams.shopId}/payments`}>
              <Button variant="outline">View Payments</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}