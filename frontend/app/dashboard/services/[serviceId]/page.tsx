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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import Link from "next/link";
import { ArrowLeft, Edit, Plus, FileText, CheckSquare, Clock, DollarSign, Trash2, X, Save } from "lucide-react";

interface RequiredDocument {
  id: number;
  name: string;
  description: string | null;
  is_mandatory: boolean;
  allowed_file_types: string[] | null;
  max_file_size_mb: number | null;
  service_id: number;
  created_at: string;
  updated_at: string;
}

interface ServiceField {
  id: number;
  name: string;
  label: string;
  field_type: string;
  is_required: boolean;
  options: string[] | null;
  validation_rules: Record<string, any> | null;
  sort_order: number;
  service_id: number;
  created_at: string;
  updated_at: string;
}

interface ServiceDetail {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  base_price: number;
  estimated_processing_days: number | null;
  status: string;
  category_name: string | null;
  created_at: string;
  updated_at: string;
  required_documents: RequiredDocument[];
  fields: ServiceField[];
}

const FIELD_TYPES = ["text", "number", "date", "select", "textarea", "boolean"] as const;

function ServiceDetailContent() {
  const { user } = useAuth();
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [service, setService] = useState<ServiceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Required Documents modals
  const [docModalOpen, setDocModalOpen] = useState(false);
  const [editingDoc, setEditingDoc] = useState<RequiredDocument | null>(null);
  const [docForm, setDocForm] = useState({
    name: "",
    description: "",
    is_mandatory: true,
    allowed_file_types: "",
    max_file_size_mb: "",
  });

  // Service Fields modals
  const [fieldModalOpen, setFieldModalOpen] = useState(false);
  const [editingField, setEditingField] = useState<ServiceField | null>(null);
  const [fieldForm, setFieldForm] = useState({
    name: "",
    label: "",
    field_type: "text" as typeof FIELD_TYPES[number],
    is_required: false,
    options: "",
    validation_rules: "",
    sort_order: 0,
  });

  const shopIdParam = searchParams?.get("shop_id");
  const [shopId, setShopId] = useState<number | null>(shopIdParam ? parseInt(shopIdParam, 10) : null);
  const serviceId = params?.serviceId;

  const fetchService = useCallback(async () => {
    if (!shopId || !serviceId) return;

    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/v1/shops/${shopId}/services/${serviceId}`, {
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      if (!resp.ok) throw new Error("Service not found");
      const data = await resp.json();
      setService(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error fetching service");
    } finally {
      setLoading(false);
    }
  }, [shopId, serviceId]);

  useEffect(() => {
    fetchService();
  }, [fetchService]);

  // Document form handlers
  const handleDocChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    if (type === "checkbox") {
      setDocForm((prev) => ({ ...prev, [name]: (e.target as HTMLInputElement).checked }));
    } else {
      setDocForm((prev) => ({ ...prev, [name]: value }));
    }
  };

  const openAddDocModal = () => {
    setEditingDoc(null);
    setDocForm({ name: "", description: "", is_mandatory: true, allowed_file_types: "", max_file_size_mb: "" });
    setDocModalOpen(true);
  };

  const openEditDocModal = (doc: RequiredDocument) => {
    setEditingDoc(doc);
    setDocForm({
      name: doc.name,
      description: doc.description || "",
      is_mandatory: doc.is_mandatory,
      allowed_file_types: doc.allowed_file_types?.join(", ") || "",
      max_file_size_mb: doc.max_file_size_mb?.toString() || "",
    });
    setDocModalOpen(true);
  };

  const handleDocSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopId || !serviceId) return;

    const payload = {
      name: docForm.name,
      description: docForm.description || null,
      is_mandatory: docForm.is_mandatory,
      allowed_file_types: docForm.allowed_file_types ? docForm.allowed_file_types.split(",").map(s => s.trim()) : null,
      max_file_size_mb: docForm.max_file_size_mb ? parseInt(docForm.max_file_size_mb, 10) : null,
    };

    try {
      let resp;
      if (editingDoc) {
        resp = await fetch(`/api/v1/shops/${shopId}/services/${serviceId}/required-documents/${editingDoc.id}`, {
          method: "PATCH",
        });
      } else {
        resp = await fetch(`/api/v1/shops/${shopId}/services/${serviceId}/required-documents`, {
          method: "POST",
        });
      }

      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.detail || "Failed to save document");
      }

      setDocModalOpen(false);
      fetchService();
    } catch (err) {
      alert(err instanceof Error ? err.message : "An error occurred");
    }
  };

  const handleDocDelete = async (docId: number) => {
    if (!confirm("Delete this required document?")) return;
    if (!shopId || !serviceId) return;

    try {
      const resp = await fetch(`/api/v1/shops/${shopId}/services/${serviceId}/required-documents/${docId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
      });
      if (!resp.ok) throw new Error("Failed to delete document");
      fetchService();
    } catch (err) {
      alert(err instanceof Error ? err.message : "An error occurred");
    }
  };

  // Field form handlers
  const handleFieldChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    if (type === "checkbox") {
      setFieldForm((prev) => ({ ...prev, [name]: (e.target as HTMLInputElement).checked }));
    } else {
      setFieldForm((prev) => ({ ...prev, [name]: value }));
    }
  };

  const openAddFieldModal = () => {
    setEditingField(null);
    setFieldForm({ name: "", label: "", field_type: "text", is_required: false, options: "", validation_rules: "", sort_order: 0 });
    setFieldModalOpen(true);
  };

  const openEditFieldModal = (field: ServiceField) => {
    setEditingField(field);
    setFieldForm({
      name: field.name,
      label: field.label,
      field_type: field.field_type as typeof FIELD_TYPES[number],
      is_required: field.is_required,
      options: field.options?.join(", ") || "",
      validation_rules: field.validation_rules ? JSON.stringify(field.validation_rules, null, 2) : "",
      sort_order: field.sort_order,
    });
    setFieldModalOpen(true);
  };

  const handleFieldSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopId || !serviceId) return;

    let validationRules = null;
    if (fieldForm.validation_rules) {
      try {
        validationRules = JSON.parse(fieldForm.validation_rules);
      } catch {
        alert("Invalid JSON in validation rules");
        return;
      }
    }

    const payload = {
      name: fieldForm.name,
      label: fieldForm.label,
      field_type: fieldForm.field_type,
      is_required: fieldForm.is_required,
      options: fieldForm.options ? fieldForm.options.split(",").map(s => s.trim()) : null,
      validation_rules: validationRules,
      sort_order: fieldForm.sort_order,
    };

    try {
      let resp;
      if (editingField) {
        resp = await fetch(`/api/v1/shops/${shopId}/services/${serviceId}/fields/${editingField.id}`, {
          method: "PATCH",
        });
      } else {
        resp = await fetch(`/api/v1/shops/${shopId}/services/${serviceId}/fields`, {
          method: "POST",
        });
      }

      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.detail || "Failed to save field");
      }

      setFieldModalOpen(false);
      fetchService();
    } catch (err) {
      alert(err instanceof Error ? err.message : "An error occurred");
    }
  };

  const handleFieldDelete = async (fieldId: number) => {
    if (!confirm("Delete this custom field?")) return;
    if (!shopId || !serviceId) return;

    try {
      const resp = await fetch(`/api/v1/shops/${shopId}/services/${serviceId}/fields/${fieldId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
      });
      if (!resp.ok) throw new Error("Failed to delete field");
      fetchService();
    } catch (err) {
      alert(err instanceof Error ? err.message : "An error occurred");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (error || !service) {
    return (
      <div className="container mx-auto py-8">
        <div className="p-4 rounded-lg bg-destructive/10 text-destructive mb-4">
          {error || "Service not found"}
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
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" asChild>
            <Link href="/dashboard/services">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{service.name}</h1>
            <p className="text-sm text-muted-foreground mt-1">Slug: {service.slug}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link href={`/dashboard/services/${service.id}/edit`}>
              <Edit className="mr-2 h-4 w-4" />
              Edit Service
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Overview</CardTitle>
            <CardDescription>Basic service details and pricing</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground">Description</h4>
              <p className="mt-1 text-sm">{service.description || "No description provided."}</p>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-4 border-t">
              <div>
                <h4 className="text-sm font-medium text-muted-foreground">Base Price</h4>
                <p className="mt-1 text-2xl font-bold font-mono">
                  ${service.base_price.toFixed(2)}
                </p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-muted-foreground">Estimated Processing</h4>
                <p className="mt-1 text-2xl font-bold">
                  {service.estimated_processing_days ? `${service.estimated_processing_days} days` : "Not specified"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Status & Categorization</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-muted-foreground">Status</h4>
              <Badge className="mt-1 capitalize">{service.status}</Badge>
            </div>
            <div>
              <h4 className="text-sm font-medium text-muted-foreground">Category</h4>
              <p className="mt-1 text-sm font-medium">{service.category_name || "Uncategorized"}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Required Documents Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Required Documents
            </CardTitle>
            <CardDescription>Documents required from the customer for this service</CardDescription>
          </div>
          <Button size="sm" onClick={openAddDocModal}>
            <Plus className="mr-2 h-4 w-4" />
            Add Document
          </Button>
        </CardHeader>
        <CardContent>
          {service.required_documents?.length === 0 ? (
            <p className="text-sm text-muted-foreground">No required documents configured.</p>
          ) : (
            <div className="divide-y">
              {service.required_documents?.map((doc) => (
                <div key={doc.id} className="py-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{doc.name}</span>
                      {doc.is_mandatory && <Badge variant="secondary" className="text-xs">Mandatory</Badge>}
                    </div>
                    {doc.description && <p className="text-xs text-muted-foreground mt-0.5">{doc.description}</p>}
                    {doc.allowed_file_types && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Allowed types: {doc.allowed_file_types.join(", ")}
                      </p>
                    )}
                    {doc.max_file_size_mb && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Max size: {doc.max_file_size_mb} MB
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="icon" onClick={() => openEditDocModal(doc)}>
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={() => handleDocDelete(doc.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Required Document Modal */}
      <Dialog open={docModalOpen} onOpenChange={setDocModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingDoc ? "Edit Required Document" : "Add Required Document"}</DialogTitle>
            <DialogDescription>Configure document requirements for this service</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleDocSubmit}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Document Name *</Label>
                <Input id="name" name="name" required value={docForm.name} onChange={handleDocChange} placeholder="e.g. Passport Copy" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" name="description" value={docForm.description} onChange={handleDocChange} rows={2} placeholder="Optional description" />
              </div>
              <div className="flex items-center gap-2">
                <Switch id="is_mandatory" name="is_mandatory" checked={docForm.is_mandatory} onCheckedChange={(checked) => setDocForm(prev => ({ ...prev, is_mandatory: checked }))} />
                <Label htmlFor="is_mandatory" className="text-sm font-medium">Mandatory</Label>
              </div>
              <div className="space-y-2">
                <Label htmlFor="allowed_file_types">Allowed File Types</Label>
                <Input id="allowed_file_types" name="allowed_file_types" value={docForm.allowed_file_types} onChange={handleDocChange} placeholder="pdf, jpg, png (comma-separated)" />
                <p className="text-xs text-muted-foreground">Comma-separated list of file extensions</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="max_file_size_mb">Max File Size (MB)</Label>
                <Input id="max_file_size_mb" name="max_file_size_mb" type="number" min="1" max="100" value={docForm.max_file_size_mb} onChange={handleDocChange} placeholder="e.g. 10" />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDocModalOpen(false)}>Cancel</Button>
              <Button type="submit"><Save className="mr-2 h-4 w-4" />{editingDoc ? "Save Changes" : "Add Document"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Dynamic Fields Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <CheckSquare className="h-5 w-5" />
              Intake Fields
            </CardTitle>
            <CardDescription>Custom form fields required for customer intake</CardDescription>
          </div>
          <Button size="sm" onClick={openAddFieldModal}>
            <Plus className="mr-2 h-4 w-4" />
            Add Field
          </Button>
        </CardHeader>
        <CardContent>
          {service.fields?.length === 0 ? (
            <p className="text-sm text-muted-foreground">No custom fields configured.</p>
          ) : (
            <div className="divide-y">
              {service.fields?.map((field) => (
                <div key={field.id} className="py-3 flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{field.label}</span>
                      <Badge variant="outline" className="text-xs font-mono">{field.field_type}</Badge>
                      {field.is_required && <Badge variant="secondary" className="text-xs">Required</Badge>}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">Field Key: {field.name}</p>
                    {field.options && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Options: {field.options.join(", ")}
                      </p>
                    )}
                    {field.sort_order !== 0 && (
                      <p className="text-xs text-muted-foreground mt-0.5">Sort Order: {field.sort_order}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="icon" onClick={() => openEditFieldModal(field)}>
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="text-destructive hover:text-destructive" onClick={() => handleFieldDelete(field.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Service Field Modal */}
      <Dialog open={fieldModalOpen} onOpenChange={setFieldModalOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingField ? "Edit Custom Field" : "Add Custom Field"}</DialogTitle>
            <DialogDescription>Configure a custom form field for customer intake</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleFieldSubmit}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Field Name *</Label>
                  <Input id="name" name="name" required value={fieldForm.name} onChange={handleFieldChange} placeholder="e.g. passport_number" />
                  <p className="text-xs text-muted-foreground">Unique identifier (snake_case)</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="label">Label *</Label>
                  <Input id="label" name="label" required value={fieldForm.label} onChange={handleFieldChange} placeholder="e.g. Passport Number" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="field_type">Field Type *</Label>
                <Select value={fieldForm.field_type} onValueChange={(v) => setFieldForm(prev => ({ ...prev, field_type: v as typeof FIELD_TYPES[number] }))}>
                  <SelectTrigger id="field_type">
                    <SelectValue placeholder="Select field type" />
                  </SelectTrigger>
                  <SelectContent>
                    {FIELD_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center gap-2">
                <Switch id="is_required" name="is_required" checked={fieldForm.is_required} onCheckedChange={(checked) => setFieldForm(prev => ({ ...prev, is_required: checked }))} />
                <Label htmlFor="is_required" className="text-sm font-medium">Required</Label>
              </div>
              <div className="space-y-2">
                <Label htmlFor="options">Options (for select type)</Label>
                <Input id="options" name="options" value={fieldForm.options} onChange={handleFieldChange} placeholder="Option 1, Option 2, Option 3 (comma-separated)" />
                <p className="text-xs text-muted-foreground">Comma-separated list. Only used for 'select' field type.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="validation_rules">Validation Rules (JSON)</Label>
                <Textarea id="validation_rules" name="validation_rules" value={fieldForm.validation_rules} onChange={handleFieldChange} rows={3} placeholder='{"min": 5, "max": 20, "pattern": "^[A-Z0-9]+$"}' />
                <p className="text-xs text-muted-foreground">JSON object for validation. E.g., min/max for numbers, pattern for text.</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="sort_order">Sort Order</Label>
                <Input id="sort_order" name="sort_order" type="number" min="0" value={fieldForm.sort_order} onChange={(e) => setFieldForm(prev => ({ ...prev, sort_order: parseInt(e.target.value, 10) }))} placeholder="0" />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setFieldModalOpen(false)}>Cancel</Button>
              <Button type="submit"><Save className="mr-2 h-4 w-4" />{editingField ? "Save Changes" : "Add Field"}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function ServiceDetailPage() {
  return (
    <ProtectedRoute>
      <ServiceDetailContent />
    </ProtectedRoute>
  );
}