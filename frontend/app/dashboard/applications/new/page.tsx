"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ProtectedRoute } from "@/components/protected-route";
import Link from "next/link";
import { ArrowLeft, Save, ChevronLeft, ChevronRight, Check } from "lucide-react";
import { Service, ServiceField, Customer, User } from "@/src/types/application";

type Step = 1 | 2 | 3 | 4;

interface FormData {
  customer_id: number | "";
  service_id: number | "";
  assigned_staff_id: number | "";
  application_data: Record<string, any>;
  notes: string;
}

function NewApplicationContent() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<Step>(1);
  const [currentStepErrors, setCurrentStepErrors] = useState<Record<string, string>>({});

  const [formData, setFormData] = useState<FormData>({
    customer_id: "",
    service_id: "",
    assigned_staff_id: "",
    application_data: {},
    notes: "",
  });

  // Data fetched from API
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [staff, setStaff] = useState<User[]>([]);
  const [selectedServiceFields, setSelectedServiceFields] = useState<ServiceField[]>([]);

  const shopIdParam = searchParams?.get("shop_id");
  const [shopId, setShopId] = useState<number | null>(shopIdParam ? parseInt(shopIdParam, 10) : null);

  // Fetch customers for step 1
  const fetchCustomers = useCallback(async () => {
    if (!shopId) return;
    try {
      const response = await fetch(`/api/v1/shops/${shopId}/customers?page_size=100`, {
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
      });
      if (response.ok) {
        const data = await response.json();
        setCustomers(data.items || data);
      }
    } catch (err) {
      console.error("Failed to fetch customers:", err);
    }
  }, [shopId]);

  // Fetch services for step 2
  const fetchServices = useCallback(async () => {
    if (!shopId) return;
    try {
      const response = await fetch(`/api/v1/shops/${shopId}/services?page_size=100`, {
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
      });
      if (response.ok) {
        const data = await response.json();
        const items = data.items || data;
        setServices(items.filter((s: Service) => s.status === "active"));
      }
    } catch (err) {
      console.error("Failed to fetch services:", err);
    }
  }, [shopId]);

  // Fetch staff for step 3
  const fetchStaff = useCallback(async () => {
    if (!shopId) return;
    try {
      const response = await fetch(`/api/v1/shops/${shopId}/staff?page_size=100`, {
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
      });
      if (response.ok) {
        const data = await response.json();
        setStaff(data.items || data);
      }
    } catch (err) {
      console.error("Failed to fetch staff:", err);
    }
  }, [shopId]);

  // Load initial data
  useEffect(() => {
    if (shopId) {
      fetchCustomers();
      fetchServices();
      fetchStaff();
    }
  }, [shopId, fetchCustomers, fetchServices, fetchStaff]);

  // Update selected service fields when service changes
  useEffect(() => {
    const service = services.find(s => s.id === formData.service_id);
    if (service) {
      setSelectedServiceFields(service.fields || []);
    } else {
      setSelectedServiceFields([]);
    }
  }, [formData.service_id, services]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;

    if (currentStepErrors[name]) {
      setCurrentStepErrors(prev => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }

    if (name === "application_data") return;

    const newValue = type === "checkbox" ? (e.target as HTMLInputElement).checked : value;

    if (name === "customer_id" || name === "service_id" || name === "assigned_staff_id") {
      // These are always select elements with string values
      const stringValue = value as string;
      setFormData(prev => ({ ...prev, [name]: stringValue === "" ? "" : parseInt(stringValue, 10) }));
    } else {
      setFormData(prev => ({ ...prev, [name]: newValue }));
    }
  };

  const handleDynamicFieldChange = (fieldName: string, value: any) => {
    if (currentStepErrors[fieldName]) {
      setCurrentStepErrors(prev => {
        const next = { ...prev };
        delete next[fieldName];
        return next;
      });
    }
    setFormData(prev => ({
      ...prev,
      application_data: { ...prev.application_data, [fieldName]: value },
    }));
  };

  const validateStep = (stepNum: Step): boolean => {
    const errors: Record<string, string> = {};

    if (stepNum === 1) {
      if (!formData.customer_id) errors.customer_id = "Customer is required";
      if (!formData.service_id) errors.service_id = "Service is required";
    }

    if (stepNum === 2) {
      for (const field of selectedServiceFields) {
        if (field.is_required) {
          const value = formData.application_data[field.name];
          if (value === undefined || value === null || value === "") {
            errors[field.name] = `${field.label} is required`;
          }
        }
      }
    }

    setCurrentStepErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(step)) {
      if (step < 4) setStep((step + 1) as Step);
    }
  };

  const handleBack = () => {
    if (step > 1) setStep((step - 1) as Step);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateStep(4)) return;
    if (!shopId) return;

    setLoading(true);
    setError(null);

    try {
      const payload = {
        customer_id: formData.customer_id,
        service_id: formData.service_id,
        assigned_staff_id: formData.assigned_staff_id || null,
        application_data: formData.application_data,
        notes: formData.notes || null,
      };

      const resp = await fetch(`/api/v1/shops/${shopId}/applications`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const data = await resp.json();
        throw new Error(data.detail || "Failed to create application");
      }

      const created = await resp.json();
      router.push(`/dashboard/applications/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const renderStep1 = () => (
    <Card>
      <CardHeader>
        <CardTitle>Step 1: Select Customer & Service</CardTitle>
        <CardDescription>Choose the customer and service for this application</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="customer_id">Customer *</Label>
          <Select
            value={formData.customer_id === "" ? "" : String(formData.customer_id)}
            onValueChange={(v) => handleChange({ target: { name: "customer_id", value: v } } as any)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a customer" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Select a customer</SelectItem>
              {customers.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>
                  {c.name} ({c.mobile})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {currentStepErrors.customer_id && (
            <p className="text-sm text-destructive">{currentStepErrors.customer_id}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="service_id">Service *</Label>
          <Select
            value={formData.service_id === "" ? "" : String(formData.service_id)}
            onValueChange={(v) => handleChange({ target: { name: "service_id", value: v } } as any)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a service" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Select a service</SelectItem>
              {services.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>
                  {s.name} {s.base_price ? `- ${new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(s.base_price)}` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {currentStepErrors.service_id && (
            <p className="text-sm text-destructive">{currentStepErrors.service_id}</p>
          )}
        </div>
      </CardContent>
    </Card>
  );

  const renderStep2 = () => (
    <Card>
      <CardHeader>
        <CardTitle>Step 2: Service Details</CardTitle>
        <CardDescription>Fill in the dynamic fields for the selected service</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {selectedServiceFields.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>No dynamic fields defined for this service.</p>
            <p className="text-sm mt-1">You can proceed to the next step.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {selectedServiceFields.map((field) => (
              <div key={field.id} className="space-y-2">
                <Label htmlFor={field.name}>
                  {field.label} {field.is_required && <span className="text-destructive">*</span>}
                </Label>
                {field.help_text && <p className="text-xs text-muted-foreground">{field.help_text}</p>}

                {field.field_type === "select" && field.options && field.options.length > 0 ? (
                  <Select
                    value={formData.application_data[field.name] === undefined ? "" : String(formData.application_data[field.name])}
                    onValueChange={(v) => handleDynamicFieldChange(field.name, v === "" ? undefined : v)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={`Select ${field.label}`} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Select...</SelectItem>
                      {field.options.map((opt) => (
                        <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : field.field_type === "boolean" ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      id={field.name}
                      checked={formData.application_data[field.name] === true}
                      onChange={(e) => handleDynamicFieldChange(field.name, e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    />
                    <Label htmlFor={field.name} className="cursor-pointer mb-0">
                      {field.label === "Yes" ? "Yes" : "Enabled"}
                    </Label>
                  </div>
                ) : field.field_type === "textarea" ? (
                  <Textarea
                    id={field.name}
                    placeholder={`Enter ${field.label.toLowerCase()}`}
                    value={formData.application_data[field.name] || ""}
                    onChange={(e) => handleDynamicFieldChange(field.name, e.target.value)}
                    rows={3}
                  />
                ) : field.field_type === "number" ? (
                  <Input
                    id={field.name}
                    type="number"
                    placeholder={`Enter ${field.label.toLowerCase()}`}
                    value={formData.application_data[field.name] === undefined ? "" : String(formData.application_data[field.name])}
                    onChange={(e) => handleDynamicFieldChange(field.name, e.target.value === "" ? undefined : parseFloat(e.target.value))}
                  />
                ) : field.field_type === "date" ? (
                  <Input
                    id={field.name}
                    type="date"
                    value={formData.application_data[field.name] || ""}
                    onChange={(e) => handleDynamicFieldChange(field.name, e.target.value || undefined)}
                  />
                ) : (
                  <Input
                    id={field.name}
                    type="text"
                    placeholder={`Enter ${field.label.toLowerCase()}`}
                    value={formData.application_data[field.name] || ""}
                    onChange={(e) => handleDynamicFieldChange(field.name, e.target.value || undefined)}
                  />
                )}

                {currentStepErrors[field.name] && (
                  <p className="text-sm text-destructive">{currentStepErrors[field.name]}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );

  const renderStep3 = () => (
    <Card>
      <CardHeader>
        <CardTitle>Step 3: Assign Staff</CardTitle>
        <CardDescription>Optionally assign a staff member to handle this application</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="assigned_staff_id">Assigned Staff</Label>
          <Select
            value={formData.assigned_staff_id === "" ? "" : String(formData.assigned_staff_id)}
            onValueChange={(v) => handleChange({ target: { name: "assigned_staff_id", value: v } } as any)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select staff member (optional)" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Unassigned</SelectItem>
              {staff.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>
                  {s.full_name} ({s.email})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );

  const renderStep4 = () => (
    <Card>
      <CardHeader>
        <CardTitle>Step 4: Notes</CardTitle>
        <CardDescription>Add any internal notes for this application (optional)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-2">
          <Label htmlFor="notes">Internal Notes</Label>
          <Textarea
            id="notes"
            name="notes"
            placeholder="Any special remarks or background notes..."
            rows={4}
            value={formData.notes}
            onChange={handleChange}
          />
        </div>
      </CardContent>
    </Card>
  );

  const steps = [
    { number: 1, title: "Customer & Service", component: renderStep1() },
    { number: 2, title: "Service Details", component: renderStep2() },
    { number: 3, title: "Assign Staff", component: renderStep3() },
    { number: 4, title: "Notes", component: renderStep4() },
  ];

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-3xl">
      {/* Progress Indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {steps.map((s, i) => (
            <div key={s.number} className="flex flex-col items-center">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-medium transition-colors ${
                  i + 1 < step
                    ? "bg-primary border-primary text-primary-foreground"
                    : i + 1 === step
                    ? "border-primary text-primary bg-background"
                    : "border-muted text-muted-foreground bg-background"
                }`}
              >
                {i + 1 < step ? <Check className="h-5 w-5" /> : s.number}
              </div>
              <span className={`mt-2 text-xs text-center font-medium ${
                i + 1 <= step ? "text-foreground" : "text-muted-foreground"
              }`}>
                {s.title}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4 mb-6">
        <Button variant="outline" size="icon" asChild>
          <Link href="/dashboard/applications">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">New Application</h1>
          <p className="text-muted-foreground mt-1">Create a new customer application</p>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-lg bg-destructive/10 text-destructive">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {steps[step - 1].component}

        <div className="mt-6 flex justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={handleBack}
            disabled={step === 1}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          {step < 4 ? (
            <Button type="button" onClick={handleNext}>
              Next
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <Button type="submit" disabled={loading}>
              <Save className="mr-2 h-4 w-4" />
              {loading ? "Creating..." : "Create Application"}
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}

export default function NewApplicationPage() {
  return (
    <ProtectedRoute>
      <NewApplicationContent />
    </ProtectedRoute>
  );
}