"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useCustomerAuth } from "@/lib/customer-auth-context";
import { customerPortalApi, CustomerProfileResponse } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

export default function PortalProfilePage({ params }: { params: Promise<{ shopId: string }> }) {
  const { customer, ready } = useCustomerAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<CustomerProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    mobile: "",
    address: "",
  });

  useEffect(() => {
    if (ready && !customer) {
      router.push(`/portal/login`);
    }
  }, [ready, customer, router]);

  useEffect(() => {
    if (customer) {
      loadProfile();
    }
  }, [customer]);

  async function loadProfile() {
    try {
      setLoading(true);
      const data = await customerPortalApi.getProfile(customer!.shop_id);
      setProfile(data);
      setFormData({
        name: data.name,
        email: data.email || "",
        mobile: data.mobile,
        address: data.address || "",
      });
    } catch (err) {
      setError("Failed to load profile");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      await customerPortalApi.updateProfile(customer!.shop_id, formData);
      setSuccess("Profile updated successfully");
      // Reload profile to get latest data
      const data = await customerPortalApi.getProfile(customer!.shop_id);
      setProfile(data);
      setFormData({
        name: data.name,
        email: data.email || "",
        mobile: data.mobile,
        address: data.address || "",
      });
    } catch (err) {
      setError("Failed to update profile");
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  if (!ready || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-2xl space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold">My Profile</h1>
            <p className="mt-1 text-sm text-muted-foreground">Loading…</p>
          </div>
        </div>
      </div>
    );
  }

  if (!customer || !profile) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">My Profile</h1>
            <p className="text-muted-foreground">Manage your personal information</p>
          </div>
          <Badge variant="secondary" className="capitalize">{customer.status}</Badge>
        </div>

        {/* Profile Info */}
        <Card>
          <CardHeader>
            <CardTitle>Profile Information</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  disabled={saving}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  disabled={saving}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="mobile">Mobile Number</Label>
                <Input
                  id="mobile"
                  type="tel"
                  value={formData.mobile}
                  onChange={(e) => setFormData({ ...formData, mobile: e.target.value })}
                  required
                  disabled={saving}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="address">Address</Label>
                <Input
                  id="address"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  disabled={saving}
                />
              </div>

              {error && <p className="text-sm font-medium text-destructive">{error}</p>}
              {success && <p className="text-sm font-medium text-green-600">{success}</p>}

              <Button type="submit" disabled={saving}>
                {saving ? "Saving…" : "Save Changes"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Account Info (Read-only) */}
        <Card>
          <CardHeader>
            <CardTitle>Account Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium text-muted-foreground">Customer ID</label>
                <p className="font-mono">{customer.customer_id}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Shop ID</label>
                <p className="font-mono">{customer.shop_id}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Account Status</label>
                <Badge variant={customer.status === "active" ? "success" : "secondary"}>
                  {customer.status}
                </Badge>
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Last Login</label>
                <p>{customer.last_login_at ? new Date(customer.last_login_at).toLocaleString() : "Never"}</p>
              </div>
              <div className="md:col-span-2">
                <label className="text-sm font-medium text-muted-foreground">Account Created</label>
                <p>{new Date(customer.created_at).toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Navigation */}
        <div className="flex gap-4">
          <Link href={`/portal/${String(customer.shop_id)}/settings`}>
            <Button variant="outline">Change Password</Button>
          </Link>
          <Link href={`/portal/${String(customer.shop_id)}/dashboard`}>
            <Button variant="ghost">Back to Dashboard</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}