'use client';

import { use } from "react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useCustomerAuth } from "@/lib/customer-auth-context";
import { customerPortalApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Link from "next/link";

export default function PortalSettingsPage({ params }: { params: Promise<{ shopId: string }> }) {
  const { customer, ready } = useCustomerAuth();
  const router = useRouter();
  const resolvedParams = use(params);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });

  useEffect(() => {
    if (ready && !customer) {
      router.push(`/portal/login`);
    }
  }, [ready, customer, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Basic validation
    if (formData.newPassword !== formData.confirmPassword) {
      setError("New passwords do not match");
      return;
    }

    if (formData.newPassword.length < 8) {
      setError("New password must be at least 8 characters long");
      return;
    }

    if (!customer) {
      setError("Customer not authenticated");
      return;
    }

    setLoading(true);
    try {
      await customerPortalApi.changePassword(
        customer.shop_id,
        {
          current_password: formData.currentPassword,
          new_password: formData.newPassword,
        }
      );
      setSuccess("Password changed successfully");
      // Clear form after successful password change
      setFormData({
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      });
    } catch (err) {
      setError("Failed to change password. Please check your current password.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  if (!ready || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-2xl space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold">Settings</h1>
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
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Settings</h1>
            <p className="text-muted-foreground">Manage your account settings</p>
          </div>
          <Link href={`/portal/${resolvedParams?.shopId}/profile`}>
            <Button variant="ghost">Back to Profile</Button>
          </Link>
        </div>

        {/* Password Change Form */}
        <Card>
          <CardHeader>
            <CardTitle>Change Password</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="currentPassword">Current Password</Label>
                <Input
                  id="currentPassword"
                  type="password"
                  value={formData.currentPassword}
                  onChange={(e) => setFormData({ ...formData, currentPassword: e.target.value })}
                  required
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="newPassword">New Password</Label>
                <Input
                  id="newPassword"
                  type="password"
                  value={formData.newPassword}
                  onChange={(e) => setFormData({ ...formData, newPassword: e.target.value })}
                  required
                  minLength={8}
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                  required
                  disabled={loading}
                />
              </div>

              {error && <p className="text-sm font-medium text-destructive">{error}</p>}
              {success && <p className="text-sm font-medium text-green-600">{success}</p>}

              <Button type="submit" disabled={loading}>
                {loading ? "Saving…" : "Change Password"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Info Section */}
        <Card>
          <CardHeader>
            <CardTitle>Password Requirements</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Your password must be at least 8 characters long and contain a mix of letters, numbers, and special characters.
            </p>
            <p className="text-sm text-muted-foreground">
              For security reasons, we recommend changing your password periodically and not reusing passwords from other sites.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}