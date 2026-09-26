"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/lib/customer-auth-context";
import { customerPortalApi, CustomerDocumentResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline" | "success" | "warning"> = {
  uploaded: "default",
  verified: "success",
  rejected: "destructive",
  pending: "warning",
  missing: "destructive",
};

export default function PortalDocumentsPage({ params }: { params: Promise<{ shopId: string }> }) {
  const { customer, ready } = useCustomerAuth();
  const router = useRouter();
  const [documents, setDocuments] = useState<CustomerDocumentResponse[]>([]);
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
      loadDocuments();
    }
  }, [customer, pagination.page]);

  async function loadDocuments() {
    try {
      setLoading(true);
      const response = await customerPortalApi.listDocuments(customer!.shop_id, {
        page: pagination.page,
        page_size: pagination.page_size,
      });
      setDocuments(response.items);
      setPagination({
        page: response.page,
        page_size: response.page_size,
        total: response.total,
        total_pages: response.total_pages,
      });
    } catch (error) {
      console.error("Failed to load documents:", error);
    } finally {
      setLoading(false);
    }
  }

  if (!ready || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-4xl space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold">My Documents</h1>
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
            <h1 className="text-3xl font-bold">My Documents</h1>
            <p className="text-muted-foreground">Manage your uploaded documents</p>
          </div>
        </div>

        {/* Documents Table */}
        <Card>
          <CardHeader>
            <CardTitle>Documents ({pagination.total})</CardTitle>
          </CardHeader>
          <CardContent>
            {documents.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No documents found.</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>File Name</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Size</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Uploaded</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {documents.map((doc) => (
                        <TableRow key={doc.id}>
                          <TableCell className="font-mono">{doc.file_name}</TableCell>
                          <TableCell>{doc.mime_type}</TableCell>
                          <TableCell>{formatFileSize(doc.file_size)}</TableCell>
                          <TableCell>
                            <Badge variant={statusColors[doc.status] || "default"}>
                              {doc.status}
                            </Badge>
                          </TableCell>
                          <TableCell>{new Date(doc.created_at).toLocaleDateString()}</TableCell>
                          <TableCell>
                            {doc.status === "verified" && (
                              <a
                                href={`/api/documents/${doc.id}/download`}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                <Button variant="ghost" size="sm">Download</Button>
                              </a>
                            )}
                            {doc.rejection_reason && (
                              <span className="text-sm text-destructive" title={doc.rejection_reason}>
                                Rejected
                              </span>
                            )}
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

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}