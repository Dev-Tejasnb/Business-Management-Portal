"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/lib/customer-auth-context";
import { customerPortalApi, CustomerApplicationResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  applied: "default",
  in_progress: "warning",
  under_review: "warning",
  approved: "success",
  rejected: "destructive",
  completed: "success",
  cancelled: "secondary",
};

export default function PortalApplicationsPage({ params }: { params: Promise<{ shopId: string }> }) {
  const { customer, ready } = useCustomerAuth();
  const router = useRouter();
  const [applications, setApplications] = useState<CustomerApplicationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 10,
    total: 0,
    total_pages: 0,
  });

  useEffect(() => {
    if (ready && !customer) {
      router.push(`/portal/login`);
    }
  }, [ready, customer, router]);

  useEffect(() => {
    if (customer) {
      loadApplications();
    }
  }, [customer, pagination.page]);

  async function loadApplications() {
    try {
      setLoading(true);
      const response = await customerPortalApi.listApplications(customer!.shop_id, {
        page: pagination.page,
        page_size: pagination.page_size,
      });
      setApplications(response.items);
      setPagination({
        page: response.page,
        page_size: response.page_size,
        total: response.total,
        total_pages: response.total_pages,
      });
    } catch (error) {
      console.error("Failed to load applications:", error);
    } finally {
      setLoading(false);
    }
  }

  if (!ready || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-4xl space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold">My Applications</h1>
            <p className="mt-1 text-sm text-muted-foreground">Loading…</p>
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
            <h1 className="text-3xl font-bold">My Applications</h1>
            <p className="text-sm text-muted-foreground">Track the status of your service applications</p>
          </div>
        </div>

        {/* Applications Table */}
        <Card>
          <CardHeader>
            <CardTitle>Applications ({pagination.total})</CardTitle>
          </CardHeader>
          <CardContent>
            {applications.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No applications found.</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Contact your service provider to submit a new application.
                </p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Application #</TableHead>
                        <TableHead>Service</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Submitted</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {applications.map((app) => (
                        <TableRow key={app.id}>
                          <TableCell className="font-mono">{app.application_number}</TableCell>
                          <TableCell>{app.service_name || app.service_slug || "Unknown"}</TableCell>
                          <TableCell>
                            <Badge variant={statusColors[app.status] || "default"}>
                              {app.status.replace("_", " ")}
                            </Badge>
                          </TableCell>
                          <TableCell>{new Date(app.created_at).toLocaleDateString()}</TableCell>
                          <TableCell>
                            <Link href={`/portal/${String(customer.shop_id)}/applications/${app.id}`}>
                              <Button variant="ghost" size="sm">View</Button>
                            </Link>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Pagination */}
                {pagination.total_pages > 1 && (
                  <div className="flex items-center justify-between mt-4">
                    <p className="text-sm text-muted-foreground">
                      Page {pagination.page} of {pagination.total_pages}
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPagination((p) => ({ ...p, page: p.page - 1 }))}
                        disabled={pagination.page === 1}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPagination((p) => ({ ...p, page: p.page + 1 }))}
                        disabled={pagination.page === pagination.total_pages}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}