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

interface ServiceData {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  base_price: number;
  estimated_processing_days: number | null;
  status: string;
}

function EditServiceContent() {
  const { user } = useAuth();
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    slug: "",
    description: "",
    base_price: "",
    estimated_processing_days: "",
    status: "active",
  });

  const [originalName, setOriginalName] = useState("");
  const [slugManuallyEdited, setSlugManuallyEdited] = useState(false);

  const shopIdParam = searchParams?.get("shop_id");
  const [shopId, setShopId] = useState<number | null>(shopIdParam ? parseInt(shopIdParam, 10) : null);
  const serviceId = params?.serviceId;

  useEffect(() => {
    if (!shopId || !serviceId) return;

    const fetchService = async () => {
      setLoading(true);
      setError(null);
      try {
        const resp = await fetch(`/api/v1/shops/${shopId}/services/${serviceId}`, {
          headers: {
            "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
          },
        });
        if (!resp.ok) throw new Error("Service not found");
        const data: ServiceData = await resp.json();
        setFormData({
          name: data.name,
          slug: data.slug,
          description: data.description || "",
          base_price: data.base_price.toString(),
          estimated_processing_days: data.estimated_processing_days?.toString() || "",
          status: data.status,
        });
        setOriginalName(data.name);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error fetching service");
      } finally {
        setLoading(false);
      }
    };

    fetchService();
  }, [shopId, serviceId]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
      // Auto-generate slug from name if slug hasn't been manually edited
      ...(name === "name" && !slugManuallyEdited && !prev.slug
        ? {
            slug: value
              .toLowerCase()
              .replace(/[^a-z0-9]+/g, "-")
              .replace(/(^-|-$)+/g, ""),
          }
        : {}),
    }));
  };

  const handleSlugChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSlugManuallyEdited(true);
    setFormData((prev) => ({ ...prev, slug: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopId || !serviceId) return;

    setSaving(true);
    setError(null);

    try {
      const payload = {
        name: formData.name,
        slug: formData.slug,
        description: formData.description || null,
        base_price: parseFloat(formData.base_price),
        estimated_processing_days: formData.estimated_processing_days
          ? parseInt(formData.estimated_processing_days, 10)
          : null,
        status: formData.status,
      };

      const resp = await fetch(`/api/v1/shops/${shopId}/services/${serviceId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.detail || "Failed to update service");
      }

      router.push(`/dashboard/services/${serviceId}`);
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

  if (error) {
    return (
      <div className="container mx-auto py-8">
        <div className="p-4 rounded-lg bg-destructive/10 text-destructive mb-4">
          {error}
        </div>
        <Button variant="outline" asChild>
          <Link href="/dashboard/services">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Services
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <div className="flex items-center gap-4 mb-6">
        <Button variant="outline" size="icon" asChild>
          <Link href={`/dashboard/services/${serviceId}`}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Edit Service</h1>
          <p className="text-muted-foreground mt-1">Update service details</p>
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
            <CardTitle>Service Details</CardTitle>
            <CardDescription>Update the basic information for the service</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Service Name *</Label>
              <Input
                id="name"
                name="name"
                required
                placeholder="e.g. Passport Application"
                value={formData.name}
                onChange={handleChange}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="slug">Slug *</Label>
              <Input
                id="slug"
                name="slug"
                required
                placeholder="e.g. passport-application"
                value={formData.slug}
                onChange={handleSlugChange}
              />
              <p className="text-xs text-muted-foreground">Unique URL-friendly identifier</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                name="description"
                placeholder="Describe the service..."
                rows={3}
                value={formData.description}
                onChange={handleChange}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="base_price">Base Price ($) *</Label>
                <Input
                  id="base_price"
                  name="base_price"
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  placeholder="0.00"
                  value={formData.base_price}
                  onChange={handleChange}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="estimated_processing_days">Est. Processing Days</Label>
                <Input
                  id="estimated_processing_days"
                  name="estimated_processing_days"
                  type="number"
                  min="0"
                  placeholder="e.g. 5"
                  value={formData.estimated_processing_days}
                  onChange={handleChange}
                />
              </div>
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
                <Link href={`/dashboard/services/${serviceId}`}>Cancel</Link>
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

export default function EditServicePage() {
  return (
    <ProtectedRoute>
      <EditServiceContent />
    </ProtectedRoute>
  );
}