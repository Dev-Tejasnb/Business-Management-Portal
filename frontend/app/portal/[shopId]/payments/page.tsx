"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/lib/customer-auth-context";
import { customerPortalApi, CustomerPaymentResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const paymentMethodLabels: Record<string, string> = {
  cash: "Cash",
  upi: "UPI",
  card: "Card",
  bank_transfer: "Bank Transfer",
  other: "Other",
};

export default function PortalPaymentsPage({ params }: { params: Promise<{ shopId: string }> }) {
  const { customer, ready } = useCustomerAuth();
  const router = useRouter();
  const [payments, setPayments] = useState<CustomerPaymentResponse[]>([]);
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
      loadPayments();
    }
  }, [customer, pagination.page]);

  async function loadPayments() {
    try {
      setLoading(true);
      const response = await customerPortalApi.listPayments(customer!.shop_id, {
        page: pagination.page,
        page_size: pagination.page_size,
      });
      setPayments(response.items);
      setPagination({
        page: response.page,
        page_size: response.page_size,
        total: response.total,
        total_pages: response.total_pages,
      });
    } catch (error) {
      console.error("Failed to load payments:", error);
    } finally {
      setLoading(false);
    }
  }

  if (!ready || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-4xl space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold">My Payments</h1>
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
            <h1 className="text-3xl font-bold">My Payments</h1>
            <p className="text-muted-foreground">View your payment history</p>
          </div>
        </div>

        {/* Payments Table */}
        <Card>
          <CardHeader>
            <CardTitle>Payments ({pagination.total})</CardTitle>
          </CardHeader>
          <CardContent>
            {payments.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No payments found.</p>
              </div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Amount</TableHead>
                        <TableHead>Method</TableHead>
                        <TableHead>Reference</TableHead>
                        <TableHead>Recorded By</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {payments.map((payment) => (
                        <TableRow key={payment.id}>
                          <TableCell>{new Date(payment.paid_at).toLocaleDateString()}</TableCell>
                          <TableCell className="font-mono">₹{payment.amount.toFixed(2)}</TableCell>
                          <TableCell>
                            <Badge variant="secondary">
                              {paymentMethodLabels[payment.payment_method] || payment.payment_method}
                            </Badge>
                          </TableCell>
                          <TableCell>{payment.reference_number || "—"}</TableCell>
                          <TableCell>{payment.recorder_name || "—"}</TableCell>
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