"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ProtectedRoute } from "@/components/protected-route";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import Link from "next/link";
import { ArrowLeft, Edit, Plus, FileText, CheckSquare, Clock, DollarSign, Trash2, X, Save, RotateCcw, Archive } from "lucide-react";

interface Customer {
  id: number;
  name: string;
  mobile: string;
  email: string | null;
  address: string | null;
  notes: string | null;
  status: string;
  primary_staff_id: number | null;
  primary_staff_name: string | null;
  shop_id: number;
  created_at: string;
  updated_at: string;
}

function CustomerDetailContent() {
  const { user } = useAuth();
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const shopIdParam = searchParams?.get("shop_id");
  const [shopId, setShopId] = useState<number | null>(shopIdParam ? parseInt(shopIdParam, 10) : null);
  const customerId = params?.customerId;

  const fetchCustomer = useCallback(async () => {
    if (!shopId || !customerId) return;

    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/v1/shops/${shopId}/customers/${customerId}`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      if (!resp.ok) throw new Error("Customer not found");
      const data = await resp.json();
      setCustomer(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error fetching customer");
    } finally {
      setLoading(false);
    }
  }, [shopId, customerId]);

  useEffect(() => {
    fetchCustomer();
  }, [fetchCustomer]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div className="container mx-auto py-8">
        <div className="p-4 rounded-lg bg-destructive/10 text-destructive mb-4">
          {error || "Customer not found"}
        </div>
        <Button variant="outline" asChild>
          <Link href="/dashboard/customers">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Customers
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" asChild>
            <Link href="/dashboard/customers">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{customer.name}</h1>
            <p className="text-sm text-muted-foreground mt-1">Mobile: {customer.mobile}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link href={`/dashboard/customers/${customer.id}/edit`}>
              <Edit className="mr-2 h-4 w-4" />
              Edit Customer
            </Link>
          </Button>
          {customer.status !== "archived" && (
            <Button
              variant="ghost"
              size="icon"
              onClick={async () => {
                if (!confirm("Archive this customer?")) return;
                const resp = await fetch(`/api/v1/shops/${shopId}/customers/${customer.id}/archive`, {
                  method: "PATCH",
                  headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
                });
                if (resp.ok) router.push(`/dashboard/customers`);
              }}
            >
              <Archive className="h-4 w-4" />
            </Button>
          )}
          {customer.status === "archived" && (
            <Button
              variant="ghost"
              size="icon"
              onClick={async () => {
                if (!confirm("Restore this customer?")) return;
                const resp = await fetch(`/api/v1/shops/${shopId}/customers/${customer.id}/restore`, {
                  method: "PATCH",
                  headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
                });
                if (resp.ok) router.push(`/dashboard/customers`);
              }}
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Contact Information</CardTitle>
            <CardDescription>Primary contact details for the customer</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-muted-foreground">Mobile Number</h4>
              <p className="mt-1 font-mono text-lg">{customer.mobile}</p>
            </div>
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-muted-foreground">Email Address</h4>
              <p className="mt-1">{customer.email || "—"}</p>
            </div>
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-muted-foreground">Address</h4>
              <p className="mt-1">{customer.address || "—"}</p>
            </div>
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-muted-foreground">Notes</h4>
              <p className="mt-1">{customer.notes || "—"}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Account Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-muted-foreground">Primary Staff</h4>
              <p className="mt-1">{customer.primary_staff_name || "—"}</p>
            </div>
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-muted-foreground">Status</h4>
              <Badge className="mt-1 capitalize">{customer.status}</Badge>
            </div>
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-muted-foreground">Created At</h4>
              <p className="mt-1 text-sm">{new Date(customer.created_at).toLocaleDateString()}</p>
            </div>
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-muted-foreground">Updated At</h4>
              <p className="mt-1 text-sm">{new Date(customer.updated_at).toLocaleDateString()}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function CustomerDetailPage() {
  return (
    <ProtectedRoute>
      <CustomerDetailContent />
    </ProtectedRoute>
  );
}