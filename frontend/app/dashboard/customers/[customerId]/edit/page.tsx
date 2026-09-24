"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ProtectedRoute } from "@/components/protected-route";
import Link from "next/link";
import { ArrowLeft, Save } from "lucide-react";

interface CustomerData {
  id: number;
  name: string;
  mobile: string;
  email: string | null;
  address: string | null;
  notes: string | null;
  status: string;
  primary_staff_id: number | null;
}

function EditCustomerContent() {
  const { user } = useAuth();
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    mobile: "",
    email: "",
    address: "",
    notes: "",
    primary_staff_id: "",
    status: "active",
  });

  const shopIdParam = searchParams?.get("shop_id");
  const [shopId, setShopId] = useState<number | null>(shopIdParam ? parseInt(shopIdParam, 10) : null);
  const customerId = params?.customerId;

  useEffect(() => {
    if (!shopId || !customerId) return;

    const fetchCustomer = async () => {
      setLoading(true);
      setError(null);
      try {
        const resp = await fetch(`/api/v1/shops/${shopId}/customers/${customerId}`, {
          headers: {
            "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
          },
        });
        if (!resp.ok) throw new Error("Customer not found");
        const data: CustomerData = await resp.json();
        setFormData({
          name: data.name,
          mobile: data.mobile,
          email: data.email || "",
          address: data.address || "",
          notes: data.notes || "",
          primary_staff_id: data.primary_staff_id ? data.primary_staff_id.toString() : "",
          status: data.status,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error fetching customer");
      } finally {
        setLoading(false);
      }
    };

    fetchCustomer();
  }, [shopId, customerId]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopId || !customerId) return;

    setSaving(true);
    setError(null);

    try {
      const payload = {
        name: formData.name,
        mobile: formData.mobile,
        email: formData.email || null,
        address: formData.address || null,
        notes: formData.notes || null,
        primary_staff_id: formData.primary_staff_id
          ? parseInt(formData.primary_staff_id, 10)
          : null,
        status: formData.status,
      };

      const resp = await fetch(`/api/v1/shops/${shopId}/customers/${customerId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.detail || "Failed to update customer");
      }

      router.push(`/dashboard/customers/${customerId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <div className="flex items-center gap-4 mb-6">
        <Button variant="outline" size="icon" asChild>
          <Link href={`/dashboard/customers/${customerId}`}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Edit Customer</h1>
          <p className="text-muted-foreground mt-1">Update customer details</p>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-destructive/10 text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>Customer Information</CardTitle>
            <CardDescription>Update contact information and settings</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Full Name *</Label>
              <Input
                id="name"
                name="name"
                required
                placeholder="e.g. John Doe"
                value={formData.name}
                onChange={handleChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="mobile">Mobile Number *</Label>
              <Input
                id="mobile"
                name="mobile"
                required
                placeholder="e.g. 9876543210"
                value={formData.mobile}
                onChange={handleChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email Address</Label>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="e.g. john@example.com"
                value={formData.email}
                onChange={handleChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="address">Address</Label>
              <Textarea
                id="address"
                name="address"
                placeholder="Customer's physical address..."
                rows={3}
                value={formData.address}
                onChange={handleChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="primary_staff_id">Primary Staff Assignment</Label>
              <Input
                id="primary_staff_id"
                name="primary_staff_id"
                placeholder="Staff User ID (optional)"
                value={formData.primary_staff_id}
                onChange={handleChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">Internal Notes</Label>
              <Textarea
                id="notes"
                name="notes"
                placeholder="Any special remarks or background notes..."
                rows={3}
                value={formData.notes}
                onChange={handleChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="status">Status *</Label>
              <select
                id="status"
                name="status"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={formData.status}
                onChange={handleChange}
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="archived">Archived</option>
              </select>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button variant="outline" type="button" asChild>
                <Link href={`/dashboard/customers/${customerId}`}>Cancel</Link>
              </Button>
              <Button type="submit" disabled={saving}>
                <Save className="mr-2 h-4 w-4" />
                {saving ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}

export default function EditCustomerPage() {
  return (
    <ProtectedRoute>
      <EditCustomerContent />
    </ProtectedRoute>
  );
}